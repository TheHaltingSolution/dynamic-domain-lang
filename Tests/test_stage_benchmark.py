"""Independent controls and resource budgets for bounded stage measurements."""
from copy import deepcopy
import os
from pathlib import Path
import sys
import tempfile
import unittest

from scripts.spl_benchmark import receipt_probe
from scripts.spl_stage_benchmark import compare_expected, independent_expected, run_process, validate_arguments
from spl_compiler.checker import check_schedule
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.parser import parse


class StageBenchmarkTests(unittest.TestCase):
    def test_all_title_intermediates_scope_and_state_have_independent_controls(self):
        checked = check_schedule(parse((ROOT / "cases/sv/sv01.spl").read_text(encoding="utf-8")))
        for count in (0, 7, 100):
            with self.subTest(count=count):
                bindings = receipt_probe(count, 3)
                expected = independent_expected(bindings)
                actual = evaluate(checked, bindings["inputs"], bindings["openings"]).to_dict()
                compare_expected(actual, expected)
                mutated = deepcopy(actual)
                mutated["emissions"]["titles"][0]["fee"] = "1"
                with self.assertRaises(ValueError):
                    compare_expected(mutated, expected)

    def test_neutral_domain_rejects_duplicate_wrong_scope_date_or_amount(self):
        base = receipt_probe(2, 2)
        mutations = [lambda b: b["inputs"]["receipts"][1].update(fact_id=b["inputs"]["receipts"][0]["fact_id"]),
                     lambda b: b["inputs"]["receipts"][0].update(asset_id="other"),
                     lambda b: b["inputs"]["receipts"][0].update(cash_received_date="2026-04-01"),
                     lambda b: b["inputs"]["receipts"][0]["amount"].update(value="2")]
        for mutate in mutations:
            changed = deepcopy(base)
            mutate(changed)
            with self.assertRaises(ValueError):
                independent_expected(changed)

    def test_streaming_output_budget_stops_and_retains_bounded_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "overflow"
            result = run_process([sys.executable, "-c", "import sys;sys.stdout.buffer.write(b'x'*200000)"],
                                 work, os.environ.copy(), timeout=10, max_output_bytes=1024)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["output_budget_exceeded"])
            self.assertEqual((work / "stdout.bin").stat().st_size, 1024)
            self.assertGreater(result["stdout_observed_bytes"], 1024)

    def test_timeout_and_nonzero_exit_cannot_be_credited(self):
        with tempfile.TemporaryDirectory() as temporary:
            for label, command, limit in (("timeout", "import time;time.sleep(5)", 0.1),
                                          ("failure", "raise SystemExit(7)", 10)):
                result = run_process([sys.executable, "-c", command], Path(temporary) / label,
                                     os.environ.copy(), timeout=limit, max_output_bytes=1024)
                self.assertEqual(result["status"], "failed")
                if label == "timeout":
                    self.assertTrue(result["timed_out"])
                else:
                    self.assertEqual(result["exit_code"], 7)

    def test_probe_limits_and_fresh_output_are_explicit(self):
        for values in (([101], 2, 3, 60, 1024), ([0, 0], 2, 3, 60, 1024),
                       ([0], 9, 3, 60, 1024), ([0], 2, 0, 60, 1024)):
            with self.assertRaises(ValueError):
                validate_arguments(*values)
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileExistsError):
                run_process([sys.executable, "-c", "pass"], Path(temporary))

    @unittest.skipUnless(os.name == "nt", "Windows process working-set API")
    def test_memory_budget_failure_is_explicit_and_stress_is_opt_in(self):
        validate_arguments([1000], 2, 1, 60, 1024, stress=True)
        with tempfile.TemporaryDirectory() as temporary:
            result = run_process([sys.executable, "-c", "import time;data=bytearray(10_000_000);time.sleep(1)"],
                                 Path(temporary) / "memory", timeout=5, max_output_bytes=1024,
                                 max_working_set_bytes=1024)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(result["working_set_budget_exceeded"])
            self.assertGreater(result["peak_working_set_bytes"], result["working_set_budget_bytes"])


if __name__ == "__main__":
    unittest.main()
