"""Negative validation must distinguish expected rejection from a broken probe."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import spl_negative_conformance as negative
from spl_compiler.codecs import DataError


class NegativeConformanceTests(unittest.TestCase):
    def test_actual_boundaries_and_retained_original_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            self.assertEqual(negative.main(["--output", str(output)]), 0)
            report = json.loads((output / "summary.json").read_text())
            self.assertEqual(len(report["checks"]), 8)
            self.assertEqual(report["changed_sources"], [])
            canonical = report["checks"][-1]
            self.assertEqual(canonical["calculation_backends"], "not_executed_precalculation_rejection")
            original = json.loads((output / "canonical/original-package.json").read_text())
            mutated = json.loads((output / "canonical/mutated-package.json").read_text())
            self.assertNotEqual(original["inputs"]["participant_b"], mutated["inputs"]["participant_b"])
            self.assertTrue((output / "native-ir/Constructors.lean").is_file())

    def test_broken_native_driver_is_not_credited_as_ir_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with patch.object(negative, "lean", side_effect=DataError("LEAN_FAILED", "broken generated probe")):
                self.assertEqual(negative.main(["--output", str(output)]), 1)
            report = json.loads((output / "summary.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["stage_error"]["stage"], "native_ir")
            self.assertEqual(report["stage_error"]["diagnostic"]["code"], "LEAN_FAILED")
            self.assertEqual(len(report["checks"]), 4)
            self.assertTrue(all(row["stage"] == "frontend_rejection" for row in report["checks"]))
            self.assertTrue((output / "native-ir/Constructors.lean").is_file())


if __name__ == "__main__":
    unittest.main()
