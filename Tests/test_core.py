"""Reference-semantics checks independent of generated Lean execution."""
from fractions import Fraction
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.evaluator import decode_value, evaluate, parse_exact, quantize
from spl_compiler.model import SPLException, USD, encode_fraction
from spl_compiler.parser import parse


HEADER = 'schedule Test language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'


class CoreTests(unittest.TestCase):
    def outcome(self, body):
        return evaluate(check_schedule(parse(HEADER + body + '}')), {}, {})

    def test_exact_division_and_serialization(self):
        result = self.outcome('define x = USD 1 / USD 3; emit "x" = x;')
        self.assertEqual(result.emissions['x'], Fraction(1, 3))
        self.assertEqual(encode_fraction(result.emissions['x']), {'numerator': '1', 'denominator': '3'})
        self.assertEqual(encode_fraction(Fraction(-1, 8)), '-0.125')

    def test_lazy_branch_and_short_circuit(self):
        result = self.outcome('define x = if true then USD 7 else USD 1 / 0.0; require true or USD 1 / 0.0 == USD 0 else "BAD"; emit "x" = x;')
        self.assertEqual(result.status, 'calculated')
        self.assertEqual(result.emissions['x'], 7)
        self.assertTrue(any(n['kind'] == 'branch' and n['unselected'] == 'not_evaluated' for n in result.trace))

    def test_failed_guard_is_atomic(self):
        result = self.outcome('define x = USD 10; require false else "BLOCK"; emit "x" = x;')
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(result.emissions, {})
        self.assertEqual(result.closing, {})
        self.assertEqual(result.diagnostics[0]['code'], 'BLOCK')

    def test_lexical_assertion_blocks_unrelated_later_division(self):
        result = self.outcome('require false else "MISSING_POLICY"; define x = USD 1 / 0.0; emit "x" = x;')
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(result.diagnostics[0]['code'], 'MISSING_POLICY')
        self.assertFalse(any(node['kind'] == 'definition' for node in result.trace))

    def test_assertion_demands_forward_definition_only_once(self):
        result = self.outcome('require rate > 0.0 else "RATE_REQUIRED"; define rate = 0.20; define x = USD 100 * rate; emit "x" = x;')
        self.assertEqual(result.status, 'calculated')
        self.assertEqual(result.emissions['x'], 20)
        definitions = [node['name'] for node in result.trace if node['kind'] == 'definition']
        self.assertEqual(definitions, ['rate', 'x'])

    def test_inactive_forward_dependencies_do_not_cross_assertion(self):
        bodies = [
            'define x = if true then USD 1 else future; require false else "POLICY"; define future = USD 1 / 0.0;',
            'define x = choose unique { when true => USD 1; when false => future; }; require false else "POLICY"; define future = USD 1 / 0.0;',
            'define x = false and future; require false else "POLICY"; define future = USD 1 / 0.0 > USD 0;',
        ]
        for body in bodies:
            with self.subTest(body=body):
                result = self.outcome(body)
                self.assertEqual(result.diagnostics[0]['code'], 'POLICY')
                self.assertNotIn('future', [n.get('name') for n in result.trace if n['kind'] == 'definition'])

    def test_deferred_global_trace_keeps_declaration_scope(self):
        source = HEADER + ('input amounts: List<Money<USD>>; define rows = for each item in amounts { '
                           'define earned = if item == USD 0 then USD 0 else item * rate; yield earned; }; '
                           'define rate = 0.20; emit "rows" = rows; }')
        checked = check_schedule(parse(source))
        money = lambda value: {'value': value, 'currency': 'USD'}
        first = evaluate(checked, {'amounts': [money('1')]}, {})
        second = evaluate(checked, {'amounts': [money('0'), money('1')]}, {})
        self.assertEqual(first.emissions['rows'], [Fraction('0.2')])
        self.assertEqual(second.emissions['rows'], [Fraction(0), Fraction('0.2')])
        # The first demand moves from iteration 0 to iteration 1; a global rate
        # still has one declaration-scoped observation with the same identity.
        first_rates = [n for n in first.trace if n.get('name') == 'rate']
        second_rates = [n for n in second.trace if n.get('name') == 'rate']
        self.assertEqual(len(first_rates), 1)
        self.assertEqual(len(second_rates), 1)
        self.assertEqual(first_rates[0]['node_id'], second_rates[0]['node_id'])

    def test_type_and_cycle_checks(self):
        for body, code in [('define x = USD 1 * USD 2;', 'TYPE_MISMATCH'),
                           ('define x = y; define y = x;', 'DEPENDENCY_CYCLE'),
                           ('define x = 1; define x = 2;', 'DUPLICATE_NAME'),
                           ('define x = unknown(1);', 'UNSUPPORTED_BUILTIN')]:
            with self.subTest(code=code), self.assertRaises(SPLException) as raised:
                check_schedule(parse(HEADER + body + '}'))
            self.assertEqual(raised.exception.code, code)

    def test_signed_rounding_modes(self):
        cases = [('1.005', 'half_even', '1'), ('1.015', 'half_even', '1.02'),
                 ('-1.005', 'half_even', '-1'), ('-1.015', 'half_even', '-1.02'),
                 ('-1.005', 'half_away_from_zero', '-1.01'), ('1.005', 'half_away_from_zero', '1.01'),
                 ('-1.001', 'floor', '-1.01'), ('-1.001', 'ceiling', '-1'),
                 ('-1.009', 'toward_zero', '-1')]
        for value, mode, expected in cases:
            with self.subTest(value=value, mode=mode):
                self.assertEqual(quantize(Fraction(value), Fraction('0.01'), mode), Fraction(expected))

    def test_rounding_placement_is_economic(self):
        aggregate = self.outcome('define x = quantize(USD 0.05 * 0.10 + USD 0.05 * 0.10, USD 0.01, "half_away_from_zero"); emit "x" = x;')
        per_line = self.outcome('define x = quantize(USD 0.05 * 0.10, USD 0.01, "half_away_from_zero") + quantize(USD 0.05 * 0.10, USD 0.01, "half_away_from_zero"); emit "x" = x;')
        self.assertEqual(aggregate.emissions['x'], Fraction('0.01'))
        self.assertEqual(per_line.emissions['x'], Fraction('0.02'))

    def test_rational_transport_rejects_noncanonical_or_float(self):
        for value in [0.1, {'numerator': '2', 'denominator': '4'}, {'numerator': '0', 'denominator': '2'}, '1e2']:
            with self.subTest(value=value), self.assertRaises(SPLException):
                parse_exact(value)

    def test_money_requires_explicit_currency_at_input_boundary(self):
        with self.assertRaises(SPLException) as raised:
            decode_value(Fraction(1), USD)
        self.assertEqual(raised.exception.code, 'INVALID_MONEY')


if __name__ == '__main__':
    unittest.main()
