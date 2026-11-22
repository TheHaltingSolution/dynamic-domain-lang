"""Neutral financial oracles versus registered, linked native SPL modules."""
from copy import deepcopy
from fractions import Fraction
import tempfile
import unittest

from cases.r1.build_modules import FOLDER, ROOT, angel_package, mqp_package, register_angel, register_mqp
from oracles.r1 import OracleError, angel_guild, mqp_ordered_fees
from spl_compiler.codecs import exact, read_json
from spl_compiler.modules import bind_module_package, run_module_package


class R1ModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.angel_ref = register_angel()
        cls.mqp_ref = register_mqp()

    def calculate(self, package, output=None):
        result = run_module_package(package, ROOT, artifact_dir=output)
        self.assertEqual(result['diagnostics'], [], result)
        self.assertEqual(result['status'], 'calculated')
        self.assertEqual(result['trace_origin'], 'native_ir_interpreter')
        return result

    def blocked(self, result, code=None):
        self.assertEqual(result['status'], 'blocked', result)
        self.assertEqual(result['statements'], [])
        self.assertEqual(result['closing_state'], [])
        self.assertEqual(result.get('results', {}), {})
        if code:
            self.assertEqual(result['diagnostics'][0]['code'], code)

    def compare_angel(self, fixture, result):
        expected = angel_guild(fixture)
        comparison = result['results']['comparison']
        for key in ['gross_guild', 'marketing', 'other_costs', 'net_guild', 'angel_share',
                    'filmmaker_pool', 'qualified_minutes', 'focal_title_amount', 'other_titles_amount', 'allocation_residual']:
            self.assertEqual(exact(comparison[key]), expected[key], key)
        actual = {row['asset_id']: exact(row['amount']) for row in result['results']['titles']}
        self.assertEqual(actual, expected['title_allocations'])
        self.assertEqual(sum(exact(row['payable']) for row in result['statements']), expected['filmmaker_pool'])

    def compare_mqp(self, fixture, result):
        expected = mqp_ordered_fees(fixture)
        comparison = result['results']['comparison']
        for key in ['eligible_receipts', 'fee', 'adjusted_receipts_before_RPPA', 'closing_actual_paid', 'closing_fee_available_paid']:
            self.assertEqual(exact(comparison[key]), expected[key], key)
        self.assertEqual([exact(row['fee']) for row in result['results']['receipt_lines']], [row['fee'] for row in expected['receipts']])
        self.assertEqual([row['id'] for row in result['results']['history']], [row['id'] for row in expected['history']])
        return expected

    def test_angel_full_platform_denominator_and_real_linked_function(self):
        fixture = read_json(FOLDER / 'angel-guild.json')
        package = angel_package(fixture, reference=self.angel_ref)
        with tempfile.TemporaryDirectory() as temporary:
            result = self.calculate(package, temporary)
            self.compare_angel(fixture, result)
            self.assertEqual(exact(result['results']['comparison']['focal_title_amount']), 85)
            self.assertEqual(len(result['statements']), 2)
            self.assertEqual(len({row['participant_id'] for row in result['statements']}), 2)
            self.assertEqual(len(result['module_closure']), 2)
            from pathlib import Path
            self.assertTrue((Path(temporary) / 'typed-ir.json').is_file())
            self.assertTrue((Path(temporary) / 'Settlement.lean').is_file())

    def test_angel_other_title_usage_changes_focal_entitlement(self):
        fixture = read_json(FOLDER / 'angel-guild.json')
        fixture['usage'][1]['minutes'] = '1830'
        result = self.calculate(angel_package(fixture, reference=self.angel_ref))
        self.compare_angel(fixture, result)
        self.assertEqual(exact(result['results']['comparison']['focal_title_amount']), Fraction(85, 2))

    def test_angel_incomplete_population_and_duplicate_identity_block(self):
        fixture = read_json(FOLDER / 'angel-guild.json')
        fixture['usage_population']['complete'] = False
        with self.assertRaises(OracleError):
            angel_guild(fixture)
        self.blocked(run_module_package(angel_package(fixture, reference=self.angel_ref), ROOT), 'ANGEL_INCOMPLETE_PLATFORM_POPULATION')
        fixture = read_json(FOLDER / 'angel-guild.json')
        fixture['usage'].append(deepcopy(fixture['usage'][0]))
        with self.assertRaises(OracleError):
            angel_guild(fixture)
        self.blocked(run_module_package(angel_package(fixture, reference=self.angel_ref), ROOT), 'DUPLICATE_MAP_KEY')

    def test_angel_wrong_population_platform_is_not_lost_in_adapter(self):
        fixture = read_json(FOLDER / 'angel-guild.json')
        fixture['usage_population']['platform_id'] = 'another-platform'
        with self.assertRaises(OracleError):
            angel_guild(fixture)
        self.blocked(run_module_package(angel_package(fixture, reference=self.angel_ref), ROOT), 'ANGEL_POPULATION_PLATFORM')

    def test_registered_scope_and_cutoff_cannot_disagree_with_source_ports(self):
        package = angel_package(reference=self.angel_ref)
        package['inputs']['scope']['pool_id'] = 'unrelated-pool'
        self.blocked(run_module_package(package, ROOT), 'MODULE_REFERENCE_SCOPE')
        package = angel_package(reference=self.angel_ref)
        package['parameters']['cutoff'] = '2026-01-01T00:00:00Z'
        self.blocked(run_module_package(package, ROOT), 'MODULE_SCOPE_MISMATCH')

    def test_angel_unsupported_policy_and_nonexact_transport_are_rejected(self):
        fixture = read_json(FOLDER / 'angel-guild.json')
        fixture['policy']['rounding'] = 'per_line_cents'
        with self.assertRaises(ValueError):
            angel_package(fixture, reference=self.angel_ref)
        fixture = read_json(FOLDER / 'angel-guild.json')
        fixture['cash_records'][0]['amount'] = True
        with self.assertRaises(ValueError):
            angel_package(fixture, reference=self.angel_ref)

    def test_mqp_selected_agreement_date_and_actual_date_sensitivity(self):
        fixture = read_json(FOLDER / 'mqp-ordered.json')
        selected = self.calculate(mqp_package(fixture, reference=self.mqp_ref))
        self.compare_mqp(fixture, selected)
        self.assertEqual(exact(selected['results']['comparison']['fee']), 40)
        alternative = deepcopy(fixture)
        alternative['policy']['trigger'] = 'actual_date'
        alternate_result = self.calculate(mqp_package(alternative, reference=self.mqp_ref))
        self.compare_mqp(alternative, alternate_result)
        self.assertEqual(exact(alternate_result['results']['comparison']['fee']), 50)
        self.assertNotEqual(selected['method_digest'], alternate_result['method_digest'])

    def test_mqp_complete_equality_and_physical_input_permutation(self):
        fixture = read_json(FOLDER / 'mqp-ordered.json')
        fixture['policy']['threshold_comparison'] = 'greater_than'
        fixture['events'].reverse()
        result = self.calculate(mqp_package(fixture, reference=self.mqp_ref))
        self.compare_mqp(fixture, result)
        self.assertEqual(exact(result['results']['comparison']['fee']), 30)

    def test_mqp_ambiguous_order_blocks_before_economic_steps(self):
        fixture = read_json(FOLDER / 'mqp-ordered.json')
        duplicate = deepcopy(fixture['events'][1])
        duplicate['id'] = 'equal-semantic-key'
        fixture['events'].append(duplicate)
        with self.assertRaises(OracleError):
            mqp_ordered_fees(fixture)
        self.blocked(run_module_package(mqp_package(fixture, reference=self.mqp_ref), ROOT), 'UNRESOLVED_EVENT_ORDER')

    def test_mqp_linked_agreement_mismatch_is_atomic(self):
        fixture = read_json(FOLDER / 'mqp-ordered.json')
        agreement = next(row for row in fixture['events'] if row['kind'] == 'agreement')
        agreement['agreed_amount'] = '99'
        with self.assertRaises(OracleError):
            mqp_ordered_fees(fixture)
        self.blocked(run_module_package(mqp_package(fixture, reference=self.mqp_ref), ROOT), 'MQP_AGREEMENT_AMOUNT_MISMATCH')

    def test_mqp_structured_registry_and_scalar_state_carry_across_close(self):
        fixture = read_json(FOLDER / 'mqp-ordered.json')
        first = deepcopy(fixture)
        first['case_id'] = 'mqp-two-closes'
        first['period']['end'] = '2008-02-01'
        first['observed_through'] = '2008-01-31'
        first['evidence'][0]['observed_date'] = '2008-01-31'
        first['events'] = [row for row in first['events'] if row['date'] < '2008-02-01']
        initial = self.calculate(mqp_package(first, reference=self.mqp_ref))
        self.compare_mqp(first, initial)
        second = deepcopy(fixture)
        second['case_id'] = 'mqp-two-closes'
        second['period']['start'] = '2008-02-01'
        second['events'] = [row for row in second['events'] if row['date'] >= '2008-02-01']
        package = mqp_package(second, reference=self.mqp_ref)
        package['state_cells'] = [{key: value for key, value in cell.items() if key != 'movement'} for cell in deepcopy(initial['closing_state'])]
        successor = self.calculate(bind_module_package(package, ROOT))
        self.assertEqual(exact(successor['results']['comparison']['fee']), 20)
        self.assertEqual(exact(successor['results']['comparison']['closing_fee_available_paid']), 1000)
        registry = next(cell for cell in successor['closing_state'] if cell['opening_port'] == 'payment_registry')
        self.assertEqual(len(registry['quantity']), 1)
        self.assertTrue(registry['quantity'][0]['agreed'])
        self.assertTrue(all('prior_result_ref' in cell for cell in successor['closing_state']))


if __name__ == '__main__':
    unittest.main()
