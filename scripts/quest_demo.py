"""Run the proposed dated two-flow fixture against SPL and independent controls."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, timedelta
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cases.quest.build_modules import quest_package, register_quest
from oracles.quest import quest_two_flow
from spl_compiler.codecs import exact, file_digest, loads, read_json, write_json
from spl_compiler.modules import module_identities, resolve_module, run_module_package
from spl_compiler.run import identities


def scenarios(base):
    """Create disclosed original-fact variants; no financial answers are supplied."""
    yield 'baseline', deepcopy(base)
    variants = [
        ('tie-even-down', '0.01', '0.50', '2026-01-01', '2027-01-01'),
        ('tie-even-up', '0.03', '0.50', '2026-01-01', '2027-01-01'),
        ('near-tie-below', '0.01', '0.499999', '2026-01-01', '2027-01-01'),
        ('near-tie-above', '0.01', '0.500001', '2026-01-01', '2027-01-01'),
        ('zero-days', '1000', '0.20', '2026-01-01', '2026-01-01'),
        ('one-year', '1000', '0.20', '2026-01-01', '2027-01-01'),
        ('alternate', '500', '0.10', '2026-01-01', '2026-06-30'),
        ('non-origin-due', '1000', '0.20', '2026-06-30', '2026-07-02'),
    ]
    for name, principal, rate, due, paid in variants:
        data = deepcopy(base)
        data['case_id'] += '-' + name
        data['terms']['annual_target'] = rate
        for group in ['obligations', 'payments', 'applications']:
            data[group][0]['amount'] = principal
        data['obligations'][0]['due_date'] = due
        data['payments'][0]['paid_date'] = paid
        data['applications'][0]['effective_date'] = paid
        paid_day = date.fromisoformat(paid)
        available = (paid_day + timedelta(days=1)).isoformat() + 'T00:00:00Z'
        data['cutoff'] = (paid_day + timedelta(days=2)).isoformat() + 'T00:00:00Z'
        data['period'] = {'start': data['obligations'][0]['due_date'],
                          'end': (paid_day + timedelta(days=1)).isoformat()}
        for group in ['obligations', 'payments', 'applications', 'evidence']:
            for row in data[group]:
                row['observed_at'] = available
        due = data['obligations'][0]['due_date']
        template = data['calendar']['observations']
        rows = []
        for index, day in enumerate(dict.fromkeys([due, paid])):
            row = deepcopy(template[min(index, len(template) - 1)])
            row['date'] = day
            # Ordinary Gregorian normalization; elapsed days remain an SPL calculation.
            row['ordinal'] = str((date.fromisoformat(day) - date.fromisoformat(data['calendar']['origin'])).days)
            row['observed_at'] = available
            rows.append(row)
        data['calendar']['observations'] = rows
        yield name, data


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--fixture', type=Path, default=ROOT / 'cases/quest/neutral.json')
    cli.add_argument('--output', type=Path,
                     default=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/quest-two-flow/review'))
    cli.add_argument('--reuse-registration', action='store_true')
    cli.add_argument('--backend', choices=['compare', 'lean', 'reference'], default='compare')
    args = cli.parse_args()
    raw = args.fixture.read_bytes()
    base = loads(raw)
    fixture_pin = hashlib.sha256(raw).hexdigest()
    before, module_before = identities(), module_identities()
    if args.reuse_registration:
        path = ROOT / 'cases/quest/charge-module.json'
        descriptor = read_json(path)
        reference = {'id': descriptor['id'], 'revision': descriptor['revision'],
                     'locator': path.relative_to(ROOT).as_posix(), 'sha256': file_digest(path)}
        resolve_module(reference, ROOT)
    else:
        reference = register_quest()
    args.output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for name, data in scenarios(base):
        expected = quest_two_flow(data)
        package = quest_package(data, reference=reference)
        folder = args.output / name
        result = run_module_package(package, ROOT, backend=args.backend, artifact_dir=folder)
        if result['status'] != 'calculated' or result['diagnostics']:
            raise SystemExit(name + ': ' + repr(result['diagnostics']))
        actual = result['results']['comparison']
        certificate = result['results']['certificate']
        for field in ['additional_charge', 'actual_principal_paid', 'elapsed_days']:
            if exact(actual[field]) != expected[field]:
                raise SystemExit(name + ': independent checkpoint failed: ' + field)
        for field in ['target_power', 'chosen_index', 'lower_bound', 'upper_bound', 'lower_power', 'upper_power', 'minimum_charge']:
            if exact(certificate[field]) != expected[field]:
                raise SystemExit(name + ': independent certificate failed: ' + field)
        for field in ['index_even', 'lower_domain_boundary', 'lower_ok', 'upper_ok', 'minimum_ok', 'predecessor_ok']:
            if certificate[field] != expected[field]:
                raise SystemExit(name + ': independent certificate flag failed: ' + field)
        if result['closing_state'] or actual['monthly_status'] != 'not_computed' or actual['combined_status'] != 'unresolved_not_computed':
            raise SystemExit(name + ': unsupported state/combined-liability claim')
        if actual['additional_payment_status'] != 'no_event_supplied' or actual['scenario_status'] != 'calculated_unissued':
            raise SystemExit(name + ': unsupported payment/issuance claim')
        for key in ['obligation_id', 'payment_id', 'application_id']:
            if actual[key] != data['selected'][key]:
                raise SystemExit(name + ': economic identity lost: ' + key)
        if name == 'baseline':
            (folder / 'neutral-fixture.json').write_bytes(raw)
        else:
            write_json(folder / 'neutral-fixture.json', data)
        write_json(folder / 'independent-oracle.json', expected)
        summaries.append({'case': name, 'status': result['status'], 'additional_charge': expected['additional_charge'],
                          'actual_principal_paid': expected['actual_principal_paid'], 'elapsed_days': expected['elapsed_days'],
                          'neutral_fixture_sha256': file_digest(folder / 'neutral-fixture.json'),
                          'result_digest': result['result_digest'], 'semantic_run_digest': result['semantic_run_digest'],
                          'module_closure': result['module_closure'], 'artifact_subdirectory': name})
        cents = int(expected['additional_charge'] * 100)
        print(name + ': additional USD ' + str(cents // 100) + '.' + str(cents % 100).zfill(2) +
              '; dated inputs and exact independent certificates agree', flush=True)
    if identities() != before or module_identities() != module_before or file_digest(args.fixture) != fixture_pin:
        raise SystemExit('Implementation or fixture changed during review; repeat on stable sources')
    write_json(args.output / 'summary.json', {'format': 'spl-quest-two-flow-review/1',
        'compiler_build': before[0], 'runtime_build': before[1], 'module_build': module_before[0],
        'base_fixture_sha256': fixture_pin, 'backend': args.backend, 'cases': summaries,
        'policy': 'DYN02-QUEST-TWOFLOW-NEAREST-EVEN@1', 'review_status': 'proposed',
        'scope': 'Synthetic additional target-return component only; owner domain acceptance pending; monthly/combined liability and Excel equivalence unresolved'})
    print('Review bundle: ' + str(args.output.resolve()))


if __name__ == '__main__':
    main()
