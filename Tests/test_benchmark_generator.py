"""Receipt probe controls; this is not a production capacity assertion."""
import unittest
from fractions import Fraction

from scripts.spl_benchmark import ROOT, assert_expected, receipt_probe
from spl_compiler.checker import check_schedule
from spl_compiler.evaluator import evaluate
from spl_compiler.parser import parse


class BenchmarkGeneratorTests(unittest.TestCase):
    def test_empty_and_multititle_probes_preserve_exact_independent_controls(self):
        checked = check_schedule(parse((ROOT / 'cases/sv/sv01.spl').read_text(encoding='utf-8')))
        for rows, pictures in [(0, 3), (7, 3), (100, 8)]:
            with self.subTest(rows=rows, pictures=pictures):
                binding = receipt_probe(rows, pictures)
                self.assertEqual(len(binding['inputs']['receipts']), rows)
                self.assertEqual(len({r['fact_id'] for r in binding['inputs']['receipts']}), rows)
                result = evaluate(checked, binding['inputs'], binding['openings']).to_dict()
                assert_expected(result, rows)
                self.assertEqual(sum(Fraction(r['cash']) for r in result['emissions']['titles']), rows)

    def test_outside_probe_envelope_rejected_before_generation(self):
        for rows, pictures in [(-1, 2), (100001, 2), (1, 0), (1, 1001)]:
            with self.assertRaises(ValueError):
                receipt_probe(rows, pictures)


if __name__ == '__main__':
    unittest.main()
