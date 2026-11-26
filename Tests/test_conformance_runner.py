"""Campaign reporting must preserve failures and distinguish unexecuted evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import spl_conformance as campaign
from validation.generated_cases import generate_cases


class CampaignRunnerTests(unittest.TestCase):
    def test_matrix_execution_does_not_promote_gaps_or_skips(self):
        matrix = {"features": [
            {"id": "mapped", "status": "witnessed", "witnesses": [{"test": "a"}, {"test": "b"}]},
            {"id": "gap", "status": "gap", "witnesses": []},
        ]}
        for outcomes, expected in [({}, "not_executed"), ({"a": "passed", "b": "skipped"}, "not_executed"),
                                   ({"a": "passed", "b": "passed"}, "passed"),
                                   ({"a": "passed", "b": "failed"}, "failed")]:
            with self.subTest(outcomes=outcomes):
                rows = campaign.matrix_report(matrix, outcomes)["features"]
                self.assertEqual(rows[0]["execution"], expected)
                self.assertEqual(rows[1]["execution"], "gap")

    def test_backend_failure_retains_case_bindings_and_completed_result(self):
        case = generate_cases()[0]
        expected = case["expected"]
        reference = {"status": expected["status"], "emissions": expected["emissions"],
                     "closing": expected["closing"], "diagnostics": [], "trace": []}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch.object(campaign, "evaluate") as evaluate, \
                 patch.object(campaign, "interpret_schedule", side_effect=RuntimeError("native unavailable")):
                evaluate.return_value.to_dict.return_value = reference
                row = campaign.run_generated([case], output)[0]
            work = output / row["artifact"]
            self.assertEqual(row["status"], "failed")
            self.assertEqual(row["error"]["message"], "native unavailable")
            self.assertEqual(json.loads((work / "case.json").read_text()), case)
            self.assertEqual(json.loads((work / "bindings.json").read_text()), case["bindings"])
            self.assertEqual((work / "Source.spl").read_bytes(), case["source"].encode())
            self.assertEqual(json.loads((work / "reference.json").read_text()), reference)
            self.assertTrue((work / "check.json").is_file())

    def test_wrong_independent_control_is_reported_for_every_executed_backend(self):
        case = generate_cases()[0]
        bad = deepcopy(case)
        bad["expected"]["emissions"]["total"] = "999999"
        actual = {"status": case["expected"]["status"], "emissions": case["expected"]["emissions"],
                  "closing": case["expected"]["closing"], "diagnostics": [], "trace": []}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            with patch.object(campaign, "interpret_schedule", return_value=actual), \
                 patch.object(campaign, "summarize_trace", return_value={"observed": []}), \
                 patch.object(campaign, "compile_schedule") as compile_mock, \
                 patch.object(campaign, "lean", return_value=json.dumps(actual)):
                # Return a real path rather than Path.write_text's byte count.
                def compile_target(source, target):
                    target.write_text("emitted")
                    return target
                compile_mock.side_effect = compile_target
                row = campaign.run_generated([bad], output)[0]
            self.assertEqual(row["status"], "failed")
            self.assertEqual(set(row["backends"]), {"reference", "native_ir", "native_emitted"})
            self.assertTrue(all(v["status"] == "failed" for v in row["backends"].values()))

    def test_overrides_are_rejected_before_creating_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "run"
            with patch.dict(campaign.os.environ, {"SPL_M1_BACKEND": "reference"}), \
                 self.assertRaises(SystemExit) as caught:
                campaign.main(["--output", str(output)])
            self.assertEqual(caught.exception.code, 2)
            self.assertFalse(output.exists())

    def test_source_change_detection_uses_exact_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "source.spl"
            path.write_bytes(b"line\n")
            manifest = {"files": {"source.spl": campaign.sha256(path.read_bytes())}}
            with patch.object(campaign, "ROOT", root):
                self.assertEqual(campaign.changed_sources(manifest), [])
                path.write_bytes(b"line\r\n")
                self.assertEqual(campaign.changed_sources(manifest), ["source.spl"])

    def test_source_inventory_retains_new_untracked_method_and_oracle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["oracles/independent.py", "cases/new/method.spl", "cases/new/neutral.json", "docs/spl/new-method.md"]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("source")
            with patch.object(campaign, "ROOT", root), patch.object(campaign, "git", return_value=b"tracked.spl\0"):
                inventory = campaign.source_names()
            self.assertTrue({"tracked.spl", "oracles/independent.py", "cases/new/method.spl",
                             "cases/new/neutral.json", "docs/spl/new-method.md"} <= inventory)

    def test_skipped_or_missing_requested_witness_is_not_a_passing_batch(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            campaign.dump(output / "witness-results.json", {
                "tests_run": 0, "outcomes": {"setUpClass (Tests.Example)": "skipped"}, "successful": True})
            with patch.object(campaign.subprocess, "run") as run:
                run.return_value.returncode = 0
                result = campaign.run_witnesses(["Tests.Example.test_claim"], output)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["uncredited_selectors"], ["Tests.Example.test_claim"])


if __name__ == "__main__":
    unittest.main()
