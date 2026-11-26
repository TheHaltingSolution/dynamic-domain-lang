"""Actual compiled settlement timing, full independent controls and anti-elision."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from scripts.spl_pure_benchmark import OFFSET, check_observations, fnv1a64, native_json_bytes, prepare_case
from spl_compiler.codecs import write_json
from spl_compiler.lean_tools import ROOT, lean_environment


class PureBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = prepare_case(100, variants=2, initial_iterations=2, maximum_iterations=2,
                                minimum_span_ns=1, warmups=1, samples=2)

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        suffix = ".exe" if os.name == "nt" else ""
        self.exe = ROOT / ".lake/build/bin" / ("spl_pure_benchmark" + suffix)
        self.assertTrue(self.exe.is_file(), "Build lake build spl_pure_benchmark first")
        self.frontend = self.exe.with_name("spl" + suffix)
        _, self.env = lean_environment()

    def run_plan(self, plan=None):
        plan = deepcopy(self.case["plan"] if plan is None else plan)
        write_json(self.work / "bindings.json", self.case["bindings"])
        write_json(self.work / "plan.json", plan)
        process = subprocess.run([str(self.exe), str(self.work / "bindings.json"), str(self.work / "plan.json")],
                                 cwd=ROOT, env=self.env, capture_output=True, timeout=30)
        return process, json.loads(process.stdout)

    def test_library_is_exact_authoritative_native_importable_emission(self):
        library = self.work / "Emitted.lean"
        process = subprocess.run([str(self.frontend), "compile-library", str(ROOT / "cases/sv/sv01.spl"), str(library)],
                                 cwd=ROOT, env=self.env, capture_output=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(library.read_bytes(), (ROOT / "Demos/SVBenchmarkLibrary.lean").read_bytes())
        self.assertNotIn(b"\ndef main", library.read_bytes())

    def test_native_cached_inputs_varied_openings_and_separate_clock_controls(self):
        process, result = self.run_plan()
        self.assertEqual(process.returncode, 0, result)
        self.assertEqual(check_observations(result, self.case["plan"])["status"], "passed")
        self.assertEqual(result["variant_count"], 2)
        self.assertEqual(result["variants_exercised_per_full_batch"], 2)
        self.assertTrue(result["resolution_span_reached"])
        self.assertGreater(result["binding_read_decode_plan_ns"], 0)
        self.assertGreater(result["first_decoded_call_ns"], 0)
        for sample in result["samples"]:
            self.assertGreater(sample["settlement_ns"], 0)
            self.assertGreater(sample["serialization_ns"], 0)
            self.assertGreater(sample["verification_ns"], 0)
        self.assertNotEqual(self.case["plan"]["variants"][0]["expected"], self.case["plan"]["variants"][1]["expected"])

    def test_independent_title_mismatch_blocks_even_if_final_pool_total_unchanged(self):
        plan = deepcopy(self.case["plan"])
        plan["variants"][0]["expected"]["emissions"]["titles"][0]["cash"] = {"numerator": "999", "denominator": "1"}
        process, result = self.run_plan(plan)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result["status"], "failed")
        self.assertIn("PURE_FIRST_OUTCOME_MISMATCH", result["diagnostics"][0]["message"])

    def test_duplicate_openings_nonces_and_oversized_iteration_budget_fail(self):
        changes = [("PURE_DUPLICATE_NONCE", lambda p: p["variants"][1].update(nonce="0")),
                   ("PURE_DUPLICATE_OPENING", lambda p: p["variants"][1].update(openings=deepcopy(p["variants"][0]["openings"]))),
                   ("PURE_PLAN_RESOURCE_LIMIT", lambda p: p.update(maximum_iterations="8193")),
                   ("PURE_PLAN_RESOURCE_LIMIT", lambda p: p.update(minimum_span_ns="0"))]
        for code, change in changes:
            plan = deepcopy(self.case["plan"])
            change(plan)
            process, result = self.run_plan(plan)
            with self.subTest(code=code):
                self.assertNotEqual(process.returncode, 0)
                self.assertEqual(result["status"], "failed")
                self.assertIn(code, result["diagnostics"][0]["message"])

    def test_parent_rejects_checksum_bytes_and_clock_tampering(self):
        process, observed = self.run_plan()
        self.assertEqual(process.returncode, 0, observed)
        changes = [lambda r: r["samples"][0].update(checksum_fnv1a64="0"),
                   lambda r: r["samples"][0].update(serialized_bytes=0),
                   lambda r: r["samples"][0].update(settlement_ns=-1),
                   lambda r: r["samples"][0].update(iterations=8193),
                   lambda r: r.update(resolution_span_reached=False)]
        for change in changes:
            result = deepcopy(observed); change(result)
            with self.assertRaises(ValueError):
                check_observations(result, self.case["plan"])

    def test_portable_checksum_and_explicit_native_control_escape_encoding(self):
        self.assertEqual(fnv1a64(OFFSET, b""), OFFSET)
        self.assertEqual(fnv1a64(OFFSET, b"hello"), int("a430d84680aabd0b", 16))
        self.assertEqual(native_json_bytes({"x": "é雪\t\b\f\n\r\"\\"}),
                         '{"x":"é雪\\u0009\\u0008\\u000c\\n\\r\\\"\\\\"}'.encode("utf-8"))
        with self.assertRaises(ValueError):
            native_json_bytes(0.1)


if __name__ == "__main__":
    unittest.main()
