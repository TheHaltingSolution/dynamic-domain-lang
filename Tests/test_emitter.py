from fractions import Fraction
from pathlib import Path
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.emitter import emit_module, run_generated
from spl_compiler.parser import parse


HEADER = 'schedule Test language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" '


class EmissionTests(unittest.TestCase):
    def run_lean(self, body, inputs=None, openings=None):
        checked = check_schedule(parse(HEADER + "{" + body + "}"))
        return run_generated(checked, inputs or {}, openings or {})

    def test_parameterized_calculation(self):
        result = self.run_lean('input n: Money<USD>; define x = n * 0.2; emit "x" = x;', {"n": Fraction(100)})
        self.assertEqual(result["emissions"]["x"], {"numerator": "20", "denominator": "1"})

    def test_lazy_conditional(self):
        result = self.run_lean('define x = if true then USD 2 else USD 1 / 0.0; emit "x" = x;')
        self.assertEqual(result["emissions"]["x"]["numerator"], "2")

    def test_ambiguous_choice_blocks_atomically(self):
        result = self.run_lean('input yes: Bool; define x = choose unique { when yes => USD 1; when yes => USD 1; }; emit "x" = x;', {"yes": True})
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["diagnostics"][0]["code"], "AMBIGUOUS_RULE")
        self.assertEqual(result["closing"], {})

    def test_exact_signed_rounding(self):
        result = self.run_lean('emit "a" = quantize(-USD 1.005, USD 0.01, "half_away_from_zero"); emit "b" = quantize(-USD 1.005, USD 0.01, "half_even");')
        self.assertEqual(result["emissions"]["a"], {"numerator": "-101", "denominator": "100"})
        self.assertEqual(result["emissions"]["b"], {"numerator": "-1", "denominator": "1"})

    def test_forward_definition(self):
        result = self.run_lean('define y = x + USD 1; define x = USD 2; emit "y" = y;')
        self.assertEqual(result["emissions"]["y"]["numerator"], "3")

    def test_lexical_assertion_barriers(self):
        cases = [
            ('require false else "POLICY"; define value = USD 1 / 0.0; emit "x" = value;', "POLICY"),
            ('require forward > USD 0 else "FORWARD_POLICY"; define value = USD 1 / 0.0; define forward = USD 0; emit "x" = value;', "FORWARD_POLICY"),
            ('require forward > USD 0 else "FORWARD_POLICY"; define value = USD 1 / 0.0; define forward = USD 2; emit "x" = value;', "DIVISION_BY_ZERO"),
            ('define rows = for each item in [1] { require false else "LOCAL_POLICY"; define value = USD 1 / 0.0; yield value; }; emit "rows" = rows;', "LOCAL_POLICY"),
        ]
        for body, expected in cases:
            with self.subTest(expected=expected):
                result = self.run_lean(body)
                self.assertEqual(result["status"], "blocked")
                self.assertEqual(result["diagnostics"][0]["code"], expected)
                self.assertEqual(result["closing"], {})

    def test_inactive_forward_references_are_lazy(self):
        cases = [
            ('define selected = if true then USD 1 else future; require false else "POLICY"; define future = USD 1 / 0.0;', {}),
            ('define selected = choose unique { when true => USD 1; when false => future; }; require false else "POLICY"; define future = USD 1 / 0.0;', {}),
            ('define selected = false and future; require false else "POLICY"; define future = USD 1 / 0.0 > USD 0;', {}),
            ('input xs: List<Money<USD>>; define selected = for each item in xs { define y = future; yield y; }; require false else "POLICY"; define future = USD 1 / 0.0;', {"xs": []}),
        ]
        for body, inputs in cases:
            with self.subTest(source=body):
                result = self.run_lean(body, inputs)
                self.assertEqual(result["diagnostics"][0]["code"], "POLICY")
                self.assertEqual(result["emissions"], {})
                self.assertEqual(result["closing"], {})

    def test_total_structural_equality_ignores_record_field_order(self):
        result = self.run_lean('emit "equal" = { a: [{ x: USD 1, y: false }], b: true } == { b: true, a: [{ y: false, x: USD 1 }] };')
        self.assertTrue(result["emissions"]["equal"])

    def test_hygienic_strings(self):
        result = self.run_lean(r'emit "str" = "\"; #eval IO.println \"injected";')
        self.assertEqual(result["emissions"]["str"], '"; #eval IO.println "injected')


if __name__ == "__main__":
    unittest.main()
