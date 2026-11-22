"""Execute the selected quantity contract, including actual serialized carry."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cases.quantities.adapter import quantity_package, register_quantities
from oracles.quantities import quantity_participation
from spl_compiler.codecs import exact, file_digest, read_json, write_json
from spl_compiler.modules import bind_module_package, run_module_package
from spl_compiler.run import identities


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--output', type=Path,
        default=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/quantity-0.4.3/quantity-review'))
    args = cli.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    fixture_path = ROOT / 'cases/quantities/neutral.json'
    fixture = read_json(fixture_path)
    fixture_pin = file_digest(fixture_path)
    before = identities()
    reference = register_quantities()
    summaries = []

    def calculate(name, data, carried=None):
        expected = quantity_participation(data)
        package = quantity_package(data, reference=reference)
        if carried is not None:
            package['state_cells'] = [{key: value for key, value in cell.items() if key != 'movement'}
                                      for cell in carried]
        package = bind_module_package(package, ROOT)
        folder = args.output / name
        result = run_module_package(package, ROOT, artifact_dir=folder)
        if result['status'] != 'calculated' or result['diagnostics']:
            raise SystemExit(name + ': ' + repr(result['diagnostics']))
        actual = result['results']
        observed = {'gross': exact(actual['gross']), 'earned': exact(actual['earned']),
                    'period_quantity': exact(actual['period_quantity']['value']),
                    'closing_quantity': exact(result['closing_state'][0]['quantity']['value'])}
        if any(observed[key] != expected[key] for key in observed):
            raise SystemExit(name + ': independent quantity/financial checkpoint failed')
        if actual['period_quantity']['unit'] != 'Download' or result['closing_state'][0]['quantity']['unit'] != 'Download':
            raise SystemExit(name + ': unit tags were not preserved')
        write_json(folder / 'neutral-fixture.json', data)
        write_json(folder / 'independent-oracle.json', expected)
        summaries.append({'case': name, 'status': result['status'], 'controls': observed,
            'result_digest': result['result_digest'], 'semantic_run_digest': result['semantic_run_digest'],
            'module_closure': result['module_closure'], 'artifact_subdirectory': name})
        print(name + ': exact independent money/quantity/carry checkpoints passed', flush=True)
        return result

    first = calculate('download-100', fixture)
    published = read_json(args.output / 'download-100/closing-state.json')
    successor = deepcopy(fixture)
    start = date.fromisoformat(fixture['period']['end'])
    end = start + timedelta(days=1)
    successor['period'] = {'start': start.isoformat(), 'end': end.isoformat()}
    successor['cutoff'] = (end + timedelta(days=1)).isoformat() + 'T00:00:00Z'
    observed = end.isoformat() + 'T00:00:00Z'
    successor['case_id'] = fixture['case_id'] + '-SUCCESSOR'
    successor['usage'] = [{'record_id': 'synthetic-successor-half', 'quantity': '0.5', 'unit': 'Download',
        'effective_date': start.isoformat(), 'observed_at': observed, 'evidence_ref': 'synthetic-successor-evidence'}]
    successor['evidence'] = [{'evidence_id': 'synthetic-successor-evidence', 'observed_at': observed}]
    successor['opening_state']['quantity'] = str(exact(first['closing_state'][0]['quantity']['value']))
    calculate('successor-half', successor, published)

    empty = deepcopy(fixture)
    empty['case_id'] += '-EMPTY'
    empty['usage'], empty['evidence'] = [], []
    calculate('empty-activity', empty)
    third = deepcopy(fixture)
    third['case_id'] += '-THIRD'
    third['usage'][0]['quantity'] = '1/3'
    calculate('third-download', third)
    if identities() != before or file_digest(fixture_path) != fixture_pin:
        raise SystemExit('Implementation or source fixture changed during the review')
    write_json(args.output / 'summary.json', {'format': 'spl-quantity-review/1',
        'compiler_build': before[0], 'runtime_build': before[1], 'neutral_fixture_sha256': fixture_pin,
        'backend': 'compare', 'cases': summaries,
        'scope': 'Synthetic Download/USD participation and adjacent quantity carry; no FX or payment execution'})
    print('Review bundle: ' + str(args.output.resolve()))


if __name__ == '__main__':
    main()
