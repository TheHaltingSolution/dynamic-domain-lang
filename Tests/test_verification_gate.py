"""Comparative release gate behavior through native stages and real CLI calls."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from spl_compiler import verification
from spl_compiler.artifacts import load_completed_result
from spl_compiler.certification import default_link
from spl_compiler.codecs import DataError, read_json, write_json
from spl_compiler.lean_tools import ROOT, compile_schedule, export_ir


SOURCE = '''schedule Gate language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {
  input gross: Money<USD>;
  define due = gross * 0.50;
  emit "payable" = due;
}
'''


class VerificationGateTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="spl-gate-test-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.source = self.work / "Authored Contract.spl"
        self.source.write_text(SOURCE, encoding="utf-8")
        self.bundle = self.work / "release"
        self.bindings = self.work / "binding.json"
        write_json(self.bindings, {"inputs": {"gross": {"currency": "USD", "value": "10"}}, "openings": {}})

    def cli(self, *args, exit_code):
        # Give this worktree precedence over the Windows embedded Python ._pth.
        entry = "import runpy,sys;sys.path.insert(0,'.');runpy.run_module('spl_compiler.verification',run_name='__main__')"
        process = subprocess.run([sys.executable, "-B", "-c", entry, *map(str, args)], cwd=ROOT,
                                 capture_output=True, encoding="utf-8", timeout=360)
        self.assertEqual(process.returncode, exit_code, process.stdout + process.stderr)
        return json.loads(process.stdout)

    def test_frontend_rejections_keep_original_source_and_stages(self):
        for stage, source in (("source", "schedule Broken"),
                              ("type", SOURCE.replace("gross * 0.50", "gross * true")),
                              ("unsupported", SOURCE.replace("spl/0.1-draft", "spl/future"))):
            with self.subTest(stage=stage):
                self.source.write_text(source, encoding="utf-8")
                refusal = self.cli("certify", self.source, self.bundle, exit_code=1)
                diagnostic = refusal["diagnostics"][0]
                self.assertEqual(diagnostic["stage"], stage, refusal)
                self.assertEqual(diagnostic["pointer"], str(self.source))
                self.assertIn("span", diagnostic)
                self.assertFalse(self.bundle.exists())

    def test_bad_link_is_rejected_with_link_stage(self):
        link = self.work / "Broken Link.json"
        link.write_text("{", encoding="utf-8")
        refusal = self.cli("certify", self.source, self.bundle, "--link", link, exit_code=1)
        diagnostic = refusal["diagnostics"][0]
        self.assertEqual(diagnostic["stage"], "link", refusal)
        self.assertEqual(diagnostic["pointer"], str(link))
        self.assertFalse(self.bundle.exists())

    def test_changed_linked_rule_with_stale_source_pin_is_rejected(self):
        source = ROOT / "cases/certification/aggregate-readable.spl"
        link = self.work / "Changed Policy Link.json"
        manifest = default_link()
        module = manifest["modules"][0]
        original = module["source"]
        module["source"] = original.replace('quantize(value, quantum, "half_even")',
                                            'quantize(value, quantum, "floor")')
        self.assertNotEqual(module["source"], original)
        write_json(link, manifest)
        refusal = self.cli("certify", source, self.bundle, "--link", link, exit_code=1)
        diagnostic = refusal["diagnostics"][0]
        self.assertEqual((diagnostic["code"], diagnostic["stage"]), ("SOURCE_LINK_PIN_MISMATCH", "link"))
        self.assertEqual(diagnostic["pointer"], str(link))
        self.assertFalse(self.bundle.exists())

    def test_native_emission_failure_and_input_budget_report_distinct_stages(self):
        with patch.object(verification, "compile_schedule", side_effect=DataError("LEAN_FAILED", "Emitter fault")):
            with self.assertRaises(DataError) as emission:
                verification.certify(self.source, self.bundle)
        self.assertEqual((emission.exception.code, emission.exception.stage), ("LEAN_FAILED", "emit"))
        with patch.object(verification, "MAX_BYTES", 16):
            with self.assertRaises(DataError) as budget:
                verification.certify(self.source, self.bundle)
        self.assertEqual((budget.exception.code, budget.exception.stage), ("VERIFICATION_RESOURCE_LIMIT", "resource"))
        self.assertFalse(self.bundle.exists())

    def test_mismatched_native_ir_blocks_before_emission(self):
        wrong = self.work / "Wrong IR.spl"
        wrong.write_text(SOURCE.replace("0.50", "0.40"), encoding="utf-8")

        def wrong_export(_source, artifact, **options):
            return export_ir(wrong, artifact, **options)

        with patch.object(verification, "export_ir", side_effect=wrong_export), patch.object(verification, "compile_schedule") as emit:
            with self.assertRaises(DataError) as refusal:
                verification.certify(self.source, self.bundle)
            emit.assert_not_called()
        self.assertEqual((refusal.exception.code, refusal.exception.stage), ("SOURCE_IR_MISMATCH", "ir"))
        self.assertFalse(self.bundle.exists())

    def test_well_typed_but_wrong_native_emitter_output_fails_kernel_and_leaves_no_release(self):
        wrong = self.work / "Wrong.spl"
        wrong.write_text(SOURCE.replace("0.50", "0.40"), encoding="utf-8")

        def wrong_translation(_source, artifact, **options):
            return compile_schedule(wrong, artifact, **options)

        with patch.object(verification, "compile_schedule", side_effect=wrong_translation):
            output = io.StringIO()
            with redirect_stdout(output):
                status = verification.main(["certify", str(self.source), str(self.bundle)])
        self.assertEqual(status, 1)
        refusal = json.loads(output.getvalue())
        diagnostic = refusal["diagnostics"][0]
        self.assertEqual((diagnostic["code"], diagnostic["stage"]), ("TARGET_PROOF_FAILED", "proof"))
        self.assertFalse(self.bundle.exists())

    def test_changed_file_after_proof_cannot_be_released(self):
        original_check = verification.check_target

        def change_after_proof(work, artifact, checked, **options):
            proof = original_check(work, artifact, checked, **options)
            artifact.write_bytes(artifact.read_bytes() + b"\n-- changed after proof\n")
            return proof

        with patch.object(verification, "check_target", side_effect=change_after_proof):
            with self.assertRaises(DataError) as refusal:
                verification.certify(self.source, self.bundle)
        self.assertEqual((refusal.exception.code, refusal.exception.stage),
                         ("VERIFICATION_PROOF_ARTIFACT_CHANGED", "proof"))
        self.assertFalse(self.bundle.exists())

    def test_interrupted_release_leaves_no_public_bundle(self):
        def interrupted_publish(staged, destination):
            self.assertTrue((Path(staged) / "certificate.json").is_file())
            self.assertFalse(Path(destination).exists())
            raise OSError("simulated failure before atomic release")

        with patch.object(verification.os, "rename", side_effect=interrupted_publish):
            with self.assertRaisesRegex(DataError, "simulated failure") as refusal:
                verification.certify(self.source, self.bundle)
        self.assertEqual(refusal.exception.stage, "release")
        self.assertFalse(self.bundle.exists())
        missing = self.cli("verify", self.bundle, exit_code=1)["diagnostics"][0]
        self.assertEqual((missing["code"], missing["stage"]), ("VERIFICATION_CERTIFICATE_MISSING", "certificate"))

    def test_rejected_certificate_replaces_success_with_nonconsumable_publication(self):
        original = self.cli("certify", self.source, self.bundle, exit_code=0)
        publication = self.work / "result"
        result = self.cli("run", self.bundle, self.bindings, "--output", publication, exit_code=0)
        self.assertEqual(result, load_completed_result(publication))
        self.assertEqual(result["status"], "calculated")

        receipt_path = self.bundle / "certificate.json"
        altered = read_json(receipt_path)
        altered["target_proof"]["proof_sha256"] = "0" * 64
        write_json(receipt_path, altered)
        blocked = self.cli("run", self.bundle, self.bindings, "--output", publication, exit_code=1)
        diagnostic = blocked["diagnostics"][0]
        self.assertEqual((diagnostic["code"], diagnostic["stage"]), ("VERIFICATION_CERTIFICATE_MISMATCH", "certificate"))
        self.assertEqual(load_completed_result(publication), blocked)
        self.assertEqual((blocked["emissions"], blocked["closing"]), ({}, {}))

        write_json(receipt_path, original)
        artifact = self.bundle / "Settlement.lean"
        contents = artifact.read_bytes()
        artifact.unlink()
        missing = self.cli("run", self.bundle, self.bindings, exit_code=1)["diagnostics"][0]
        self.assertEqual((missing["code"], missing["stage"]), ("VERIFICATION_BUNDLE_FILE_MISSING", "certificate"))
        artifact.write_bytes(contents)
        receipt_path.unlink()
        blocked = self.cli("run", self.bundle, self.bindings, "--output", publication, exit_code=1)
        diagnostic = blocked["diagnostics"][0]
        self.assertEqual((diagnostic["code"], diagnostic["stage"]), ("VERIFICATION_CERTIFICATE_MISSING", "certificate"))
        self.assertEqual(load_completed_result(publication), blocked)
        self.assertEqual((blocked["emissions"], blocked["closing"]), ({}, {}))
        write_json(receipt_path, original)
        self.assertEqual(self.cli("verify", self.bundle, exit_code=0), original)
