"""Neutral-fact controls authored independently from executable SPL."""
from copy import deepcopy
from fractions import Fraction
import itertools
import unittest

from oracles.quantities import QuantityOracleError, exact_json, quantity_participation


def fixture(amounts=('100',)):
    scope = {'contract_id': 'agreement', 'participant_id': 'participant', 'pool_id': 'pool',
             'asset_id': 'picture', 'currency': 'USD', 'unit': 'Download'}
    return {'schema_version': 'quantity-neutral/1', 'case_id': 'oracle-downloads', 'scope': scope,
            'period': {'start': '2025-01-01', 'end': '2025-04-01'}, 'cutoff': '2025-04-03T00:00:00Z',
            'usage': [{'record_id': 'record-' + str(i), 'quantity': amount, 'unit': 'Download',
                       'effective_date': '2025-02-01', 'observed_at': '2025-04-02T00:00:00Z',
                       'evidence_ref': 'usage-evidence'} for i, amount in enumerate(amounts)],
            'evidence': [{'evidence_id': 'usage-evidence', 'observed_at': '2025-04-02T00:00:00Z'}],
            'terms': {'rate': '1.50', 'per_unit': 'Download', 'currency': 'USD', 'participation': '1/2',
                      'rounding': 'exact_no_rounding', 'quantity_policy': 'nonnegative_selected_period'},
            'opening_state': {'scope': dict(scope), 'quantity': '0', 'unit': 'Download'}}


class QuantityOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaisesRegex(QuantityOracleError, '^' + code + '$'):
            quantity_participation(data)

    def test_manual_amounts_and_separate_share(self):
        data = fixture()
        data['opening_state']['quantity'] = '10'
        result = quantity_participation(data)
        self.assertEqual([result[key] for key in ['period_quantity', 'gross', 'earned', 'closing_quantity']], [100, 150, 75, 110])
        data['terms']['participation'] = '1'
        self.assertEqual(quantity_participation(data)['earned'], 150)

    def test_zero_empty_and_fractional_quantities(self):
        for amounts in [(), ('0',)]:
            data = fixture(amounts)
            data['opening_state']['quantity'] = '7'
            result = quantity_participation(data)
            self.assertEqual((result['period_quantity'], result['gross'], result['earned'], result['closing_quantity']), (0, 0, 0, 7))
            if not amounts:
                data['evidence'] = []
                self.assertEqual(quantity_participation(data)['closing_quantity'], 7)
        result = quantity_participation(fixture(('1/3',)))
        self.assertEqual((result['gross'], result['earned']), (Fraction(1, 2), Fraction(1, 4)))

    def test_split_permutation_and_bounded_rates(self):
        for first, second in itertools.product(range(5), repeat=2):
            split = fixture((str(first), str(second)))
            whole = fixture((str(first + second),))
            result = quantity_participation(split)
            self.assertEqual(result['earned'], Fraction(3 * (first + second), 4))
            self.assertEqual(result['earned'], quantity_participation(whole)['earned'])
            split['usage'].reverse()
            self.assertEqual(quantity_participation(split), result)
        for rate in ['0', '1/3', '1.50', '1000']:
            data = fixture(('2',))
            data['terms']['rate'] = rate
            self.assertEqual(quantity_participation(data)['earned'], Fraction(rate))

    def test_neutral_carry_across_periods(self):
        first = fixture(('50',))
        closing = quantity_participation(first)
        following = fixture(('30',))
        following['opening_state'] = exact_json(closing['closing_state'])
        following['period'] = {'start': '2025-04-01', 'end': '2025-07-01'}
        following['cutoff'] = '2025-07-03T00:00:00Z'
        following['usage'][0].update(effective_date='2025-05-01', observed_at='2025-07-02T00:00:00Z')
        following['evidence'][0]['observed_at'] = '2025-07-02T00:00:00Z'
        result = quantity_participation(following)
        self.assertEqual(result['closing_quantity'], 80)
        self.assertEqual(closing['earned'] + result['earned'], 60)

    def test_unit_currency_and_scope_mismatches(self):
        changes = [
            ('USAGE_UNIT', lambda d: d['usage'][0].update(unit='UsageMinute')),
            ('RATE_DIMENSION', lambda d: d['terms'].update(per_unit='UsageMinute')),
            ('RATE_DIMENSION', lambda d: d['terms'].update(currency='EUR')),
            ('OPENING_SCOPE', lambda d: d['opening_state']['scope'].update(pool_id='other')),
            ('OPENING_SCOPE', lambda d: d['opening_state'].update(unit='UsageMinute')),
            ('USAGE_SCOPE', lambda d: d['usage'][0].update(scope={**d['scope'], 'asset_id': 'other'})),
            ('SELECTED_SCOPE_DIMENSION', lambda d: d['scope'].update(currency='EUR'))]
        for code, mutate in changes:
            data = fixture(); mutate(data)
            self.reject(data, code)

    def test_half_open_period_and_exact_cutoff(self):
        for effective in ['2024-12-31', '2025-04-01']:
            data = fixture(); data['usage'][0]['effective_date'] = effective
            self.reject(data, 'USAGE_OUTSIDE_SELECTED_PERIOD')
        data = fixture(); data['usage'][0]['effective_date'] = '2025-01-01'
        data['cutoff'] = '2025-04-03T00:00:00.0000000002Z'
        data['usage'][0]['observed_at'] = '2025-04-03T01:00:00.0000000001+01:00'
        self.assertEqual(quantity_participation(data)['earned'], 75)
        data['usage'][0]['observed_at'] = data['cutoff']
        self.reject(data, 'USAGE_AFTER_CUTOFF')
        data = fixture(); data['evidence'][0]['observed_at'] = data['cutoff']
        self.reject(data, 'EVIDENCE_AFTER_CUTOFF')

    def test_duplicates_missing_evidence_and_case_domain(self):
        data = fixture(); data['usage'].append(deepcopy(data['usage'][0]))
        self.reject(data, 'DUPLICATE_IDENTITY')
        data = fixture(); data['evidence'].append(deepcopy(data['evidence'][0]))
        self.reject(data, 'DUPLICATE_IDENTITY')
        data = fixture(); data['usage'][0]['evidence_ref'] = 'missing'
        self.reject(data, 'USAGE_EVIDENCE_REQUIRED')
        data = fixture(('0',)); data['evidence'] = []
        self.reject(data, 'USAGE_EVIDENCE_REQUIRED')
        self.reject(fixture(('100', '-1')), 'NEGATIVE_SELECTED_QUANTITY')
        for key, value in [('rate', '-1'), ('participation', '101/100')]:
            data = fixture(); data['terms'][key] = value
            self.reject(data, 'SELECTED_TERM_DOMAIN')
        for quantity in [True, 1.0, '1e2', '01', 'NaN', '1/0']:
            self.reject(fixture((quantity,)), 'EXACT_VALUE_REQUIRED')

    def test_schema_policy_and_dates_are_explicit(self):
        data = fixture(); data['schema_version'] = 'quantity-neutral/99'
        self.reject(data, 'UNSUPPORTED_NEUTRAL_SCHEMA')
        for key, value in [('rounding', 'nearest_cent'), ('quantity_policy', 'floor_negative')]:
            data = fixture(); data['terms'][key] = value
            self.reject(data, 'SELECTED_POLICY_REQUIRED')
        data = fixture(); data['usage'][0]['effective_date'] = '2025-02-30'
        self.reject(data, 'INVALID_DATE')
        for value in ['2025-04-03', '2025-04-03T00:00:00-00:00', '2025-04-03T00:00:60Z']:
            data = fixture(); data['cutoff'] = value
            self.reject(data, 'INVALID_INSTANT')


if __name__ == '__main__':
    unittest.main()
