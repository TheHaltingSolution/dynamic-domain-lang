"""Execute registered ordinary-royalty methods against neutral-fact oracles."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cases.m1.build_modules import m1_package, register_m1
from oracles.ordinary_royalties import ordinary_royalties
from spl_compiler.codecs import exact, file_digest, read_json, write_json
from spl_compiler.modules import resolve_module, run_module_package
from spl_compiler.run import identities


def _exact_json_number(value):
    raise ValueError('Use exact strings for M1 neutral financial numbers: ' + value)


def _unique_keys(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError('Duplicate neutral fixture field: ' + name)
        result[name] = value
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--fixtures', type=Path, default=ROOT / 'cases/m1/fixtures')
    cli.add_argument('--output', type=Path,
                     default=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/m1-royalties'))
    cli.add_argument('--backend', choices=['compare', 'lean', 'reference'], default='compare')
    cli.add_argument('--reuse-registration', action='store_true',
                     help='Read existing pinned descriptors without regenerating source/interface registrations')
    args = cli.parse_args()
    paths = sorted(args.fixtures.glob('*.json'))
    if not paths:
        cli.error('No neutral fixtures found; select the fixtures directory, not the module registry')
    cases = []
    identities_seen = set()
    for path in paths:
        # Neutral bands use null for an unbounded upper edge; canonical inputs
        # subsequently use explicit typed Option values. Binary floats stay out.
        raw = path.read_bytes()
        fixture = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_keys,
                             parse_float=_exact_json_number, parse_constant=_exact_json_number)
        name = fixture.get('case_id', '')
        if (not isinstance(name, str) or
                not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9_.-]*[A-Za-z0-9])?', name) or
                name in identities_seen):
            cli.error('Each fixture requires a unique safe case_id: ' + str(path))
        identities_seen.add(name)
        cases.append((raw, hashlib.sha256(raw).hexdigest(), fixture, name))
    before = identities()
    if args.reuse_registration:
        path = ROOT / 'cases/m1/ordinary-module.json'
        descriptor = read_json(path)
        reference = {'id': descriptor['id'], 'revision': descriptor['revision'],
                     'locator': path.relative_to(ROOT).as_posix(), 'sha256': file_digest(path)}
        resolve_module(reference, ROOT)
    else:
        reference = register_m1()
    args.output.mkdir(parents=True, exist_ok=True)
    summaries = []
    for index, (raw, fixture_sha256, fixture, name) in enumerate(cases, 1):
        destination = args.output / (str(index).zfill(2) + '-' + name)
        expected = ordinary_royalties(fixture)
        package = m1_package(fixture, reference=reference)
        result = run_module_package(package, ROOT, backend=args.backend, artifact_dir=destination)
        if result['status'] != 'calculated' or result['diagnostics']:
            raise SystemExit(name + ': ' + repr(result['diagnostics']))
        actual = result['results']['comparison']
        for field in ['basis', 'uncapped', 'entitlement', 'closing_balance']:
            if exact(actual[field]) != expected[field]:
                raise SystemExit(name + ': independent checkpoint failed: ' + field)
        (destination / 'neutral-fixture.json').write_bytes(raw)
        write_json(destination / 'independent-oracle.json', expected)
        summary = {'case': name, 'method': fixture['policy']['method'],
                   'fixture_sha256': fixture_sha256, 'backend': args.backend,
                   'status': result['status'], 'independent_expected': expected,
                   'comparison': actual, 'result_digest': result['result_digest'],
                   'semantic_run_digest': result['semantic_run_digest'],
                   'module_closure': result['module_closure'],
                   'artifact_subdirectory': destination.name}
        summaries.append(summary)
        print(name + ': independent basis/uncapped/entitlement/carry checkpoints passed', flush=True)
    if identities() != before:
        raise SystemExit('Compiler/runtime changed during the demo; repeat in a stable workspace')
    write_json(args.output / 'summary.json', {'format': 'spl-m1-review/1',
        'compiler_build': before[0], 'runtime_build': before[1], 'backend': args.backend,
        'cases': summaries,
        'scope': 'Selected synthetic tiers, caps and separate guarantee; not all C04/C05 variants'})
    print('Review bundle: ' + str(args.output.resolve()))


if __name__ == '__main__':
    main()
