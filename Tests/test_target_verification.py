"""Check the generalized settlement and native transport proofs on real emission."""

from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from spl_compiler.certification import PILOT, default_link
from spl_compiler.codecs import DataError, file_digest, read_json, write_json
from spl_compiler.lean_tools import ROOT, compile_schedule, lean
from spl_compiler.modules import linking_manifest, resolve_module
from spl_compiler.source_verification import check_source
from spl_compiler.target_verification import CLAIM, THEOREMS, check_target


class TargetVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="spl-target-test-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.artifact = self.work / "Emitted.lean"
        self.check = self.work / "check"

    def assert_checked(self, checked, *, mode="single"):
        receipt = check_target(self.check, self.artifact, checked, mode=mode)
        self.assertEqual(receipt["format"], CLAIM)
        self.assertEqual(receipt["mode"], mode)
        self.assertEqual(receipt["theorems"], list(THEOREMS))
        self.assertEqual(receipt["artifact_sha256"], sha256(self.artifact.read_bytes()).hexdigest())
        return receipt

    def test_readable_stateful_series_entry_proves_all_input_agreement(self):
        source = ROOT / "cases/sv/rq07-readable.spl"
        lean(["--run", ROOT / "SPL/Main.lean", "compile-series", source, self.artifact])
        self.assert_checked(check_source(source), mode="series")

    def test_dimension_extension_preserves_input_and_target_meanings(self):
        source = ROOT / "cases/usage-conversion/hour-meter.spl"
        compile_schedule(source, self.artifact)
        self.assert_checked(check_source(source))

    def test_linked_rounding_function_proves_all_input_agreement(self):
        source = PILOT / "aggregate-readable.spl"
        manifest = self.work / "Link.json"
        write_json(manifest, default_link())
        compile_schedule(source, self.artifact, link=manifest)
        self.assert_checked(check_source(source, link=manifest))

    def test_large_nested_transport_proof_checks_dependent_replay(self):
        locator = "cases/dependent-replay/dependent-replay-module.json"
        descriptor = read_json(ROOT / locator)
        reference = {"id": descriptor["id"], "revision": descriptor["revision"],
                     "locator": locator, "sha256": file_digest(ROOT / locator)}
        module = resolve_module(reference, ROOT)
        manifest = self.work / "Link.json"
        write_json(manifest, linking_manifest(module))
        compile_schedule(module.source_path, self.artifact, link=manifest)
        self.assert_checked(check_source(module.source_path, link=manifest))

    def test_mistranslated_share_cannot_prove_equality(self):
        source = PILOT / "aggregate-readable.spl"
        alternative = self.work / "FortyPercent.spl"
        alternative.write_bytes(source.read_bytes().replace(b"50%", b"40%"))
        manifest = self.work / "Link.json"
        write_json(manifest, default_link())
        compile_schedule(alternative, self.artifact, link=manifest)
        with self.assertRaises(DataError) as failed:
            check_target(self.check, self.artifact, check_source(source, link=manifest))
        self.assertEqual(failed.exception.code, "TARGET_PROOF_FAILED")
        self.assertIn("settlement_equivalent", failed.exception.args[0])

    def test_unchanged_calculation_with_wrong_binding_signature_is_rejected(self):
        source = ROOT / "cases/sv/rq07.spl"
        compile_schedule(source, self.artifact)
        emitted = self.artifact.read_bytes()
        wrong = emitted.replace(b'(.named "Money" [(.named "USD" [])])', b'(.named "Ratio" [])', 1)
        self.assertNotEqual(wrong, emitted)
        self.artifact.write_bytes(wrong)
        with self.assertRaises(DataError) as failed:
            check_target(self.check, self.artifact, check_source(source))
        self.assertEqual(failed.exception.code, "TARGET_PROOF_FAILED")
        self.assertIn("entry_equivalent", failed.exception.args[0])
