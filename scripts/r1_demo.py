"""Reproduce registered reusable-kernel financial results and review material."""
from __future__ import annotations

import argparse
from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cases.extensibility.build_modules import deadline_package
from cases.mechanisms.register_modules import build_package as mechanism_package, register as register_mechanism
from cases.r1.build_modules import angel_package, mqp_package
from cases.revision.build_modules import revision_package
from cases.waterfall.build_modules import waterfall_package
from oracles.r1 import angel_guild, mqp_ordered_fees, supplied_due_reserve
from oracles.revision import restate
from oracles.waterfall import waterfall as waterfall_oracle
from spl_compiler.codecs import exact, file_digest, read_json, write_json
from spl_compiler.modules import bind_module_package, run_module_package


def _cedar_package():
    path = ROOT / 'cases/modules/priority-rates/build_fixture.py'
    spec = importlib.util.spec_from_file_location('cedar_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    descriptor = path.parent / 'descriptor.json'
    write_json(descriptor, module.build_descriptor())
    package = bind_module_package(module.build_package(file_digest(descriptor)), ROOT)
    write_json(path.parent / 'package.json', package)
    return package


def _same(actual, expected, fields):
    for field in fields:
        if exact(actual[field]) != expected[field]:
            raise ValueError('Independent financial checkpoint failed: ' + field)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output', type=Path, default=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/r1-kernel'))
    cli.add_argument('--legacy', action='store_true', help='Also recreate six legacy cases and three standalone mechanism bundles')
    cli.add_argument('--refresh-snapshots', action='store_true')
    cli.add_argument('--derived-calendar', action='store_true', help='Use only after the E0 freeze and calendar API extension')
    args = cli.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.legacy:
        command = [sys.executable, str(ROOT / 'scripts/spl_demo.py'), '--output', str(args.output / 'legacy')]
        if args.refresh_snapshots:
            command.extend(['--refresh-snapshots', '--skip-baseline'])
        subprocess.run(command, cwd=ROOT, check=True)

    cases = [('priority-rates', _cedar_package(), None)]
    angel = read_json(ROOT / 'cases/r1/angel-guild.json')
    cases.append(('angel', angel_package(angel), ('angel', angel)))
    sensitivity = deepcopy(angel)
    sensitivity['usage'][1]['minutes'] = '1830'
    cases.append(('angel-other-usage', angel_package(sensitivity), ('angel', sensitivity)))
    mqp = read_json(ROOT / 'cases/r1/mqp-ordered.json')
    cases.append(('mqp', mqp_package(mqp), ('mqp', mqp)))
    actual_date = deepcopy(mqp)
    actual_date['policy']['trigger'] = 'actual_date'
    cases.append(('mqp-actual-date', mqp_package(actual_date), ('mqp', actual_date)))
    for name in ['advance-issues', 'reserve-vintage', 'correction-payments']:
        cases.append((name, mechanism_package(name, reference=register_mechanism(name)), None))
    for name in ['priority-120', 'pro-rata-120', 'roundlake-like-p1', 'roundlake-like-p2']:
        fixture = read_json(ROOT / 'cases/waterfall' / (name + '.json'))
        cases.append(('waterfall-' + name, waterfall_package(fixture), ('waterfall', fixture)))
    revision = read_json(ROOT / 'cases/revision/neutral.json')
    cases.append(('authorized-revision', revision_package(revision), ('revision', revision)))
    supplied = read_json(ROOT / 'cases/r1/supplied-due-reserve.json')
    cases.append(('supplied-deadline', deadline_package(supplied), ('supplied', supplied)))
    if args.derived_calendar:
        derived = deepcopy(supplied)
        derived.update(months=1, invalid_day_policy='clamp_day')
        cases.append(('derived-deadline', deadline_package(derived, derived=True), ('supplied', supplied)))

    summaries = []
    for name, package, oracle in cases:
        if name == 'waterfall-roundlake-like-p2':
            published = read_json(args.output / 'waterfall-roundlake-like-p1/closing-state.json')
            package['state_cells'] = [{key: value for key, value in cell.items() if key != 'movement'} for cell in published]
            package = bind_module_package(package, ROOT)
        result = run_module_package(package, ROOT, artifact_dir=args.output / name)
        if result['status'] != 'calculated' or result['diagnostics']:
            raise ValueError(name + ': ' + repr(result['diagnostics']))
        values = result['results']
        if oracle:
            kind, fixture = oracle
            if kind == 'angel':
                expected = angel_guild(fixture)
                _same(values['comparison'], expected, ['gross_guild', 'marketing', 'other_costs', 'net_guild', 'filmmaker_pool', 'qualified_minutes', 'focal_title_amount', 'other_titles_amount', 'allocation_residual'])
            elif kind == 'mqp':
                expected = mqp_ordered_fees(fixture)
                _same(values['comparison'], expected, ['eligible_receipts', 'fee', 'adjusted_receipts_before_RPPA', 'closing_actual_paid', 'closing_fee_available_paid'])
            elif kind == 'waterfall':
                expected = waterfall_oracle(fixture)['control']
                _same(values['control'], expected, ['gross', 'fee', 'deductions', 'available_funds', 'recovered', 'residual'])
            elif kind == 'revision':
                expected = restate(fixture)
                _same(values['comparison'], expected, ['original_issued', 'original_recomputed', 'revised_entitlement', 'correction_delta', 'actual_paid_asof', 'outstanding_asof'])
            else:
                expected = supplied_due_reserve(fixture)
                _same(values['reserve_ledger'], expected, ['available', 'released', 'closing_balance'])
        elif name == 'priority-rates':
            if sum(exact(row['earned']) for row in result['statements']) != 40:
                raise ValueError('Cedar independent 40 checkpoint')
        else:
            port, field, expected = {'advance-issues': ('advances', 'closing_balance', 5000),
                                     'reserve-vintage': ('reserve_ledger', 'closing_balance', 20),
                                     'correction-payments': ('obligation_reconciliation', 'remaining_obligation', 10)}[name]
            if exact(values[port][field]) != expected:
                raise ValueError('Independent mechanism checkpoint: ' + name)
        summary = {'case': name, 'status': result['status'], 'results': values,
                   'semantic_run_digest': result['semantic_run_digest'], 'result_digest': result['result_digest'],
                   'module_closure': result['module_closure'], 'artifact_subdirectory': name}
        summaries.append(summary)
        if args.refresh_snapshots:
            write_json(ROOT / 'cases/r1' / (name + '-canonical-package.json'), package)
        print(name + ': calculated; exact independent checkpoints passed', flush=True)
    write_json(args.output / 'summary.json', summaries)
    print('Review bundle: ' + str(args.output.resolve()))


if __name__ == '__main__':
    main()
