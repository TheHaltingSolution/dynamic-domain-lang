"""Kernel and identity checks for the exact Readable SPL certification pilot."""

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from spl_compiler import certification
from spl_compiler.codecs import DataError, write_json
from spl_compiler.lean_tools import compile_schedule


class ReadableCertificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = TemporaryDirectory(prefix="spl-cert-tests-")
        cls.addClassCleanup(work.cleanup)
        cls.work = Path(work.name)
        cls.aggregate = certification.PILOT / "aggregate-readable.spl"
        cls.row = certification.PILOT / "row-readable.spl"
        cls.artifact = cls.work / "Aggregate.lean"
        cls.receipt = cls.work / "Aggregate.json"
        cls.checked = certification.certify(cls.aggregate, cls.artifact, cls.receipt)

    def write_bindings(self, name, first="0.01", second="0.01", currency="USD"):
        path = self.work / name
        write_json(path, {
            "inputs": {
                "first_receipt": {"currency": currency, "value": first},
                "second_receipt": {"currency": "USD", "value": second},
            },
            "openings": {},
        })
        return path

    def test_both_proved_artifacts_distinguish_aggregation_from_row_rounding(self):
        bindings = self.write_bindings("TwoCents.json")
        self.assertEqual(certification.identify(self.aggregate), "aggregate")
        self.assertEqual(certification.identify(self.row), "row")
        row_artifact = self.work / "Row.lean"
        row_receipt = self.work / "Row.json"
        certification.certify(self.row, row_artifact, row_receipt)
        cases = [
            (self.aggregate, self.artifact, self.receipt, "1", "100"),
            (self.row, row_artifact, row_receipt, "0", "1"),
        ]
        for source, artifact, receipt, numerator, denominator in cases:
            with self.subTest(source=source.name):
                result = certification.run_certified(source, artifact, receipt, bindings)
                self.assertEqual(result, {
                    "status": "calculated", "closing": {}, "diagnostics": [],
                    "emissions": {"participation": {"numerator": numerator, "denominator": denominator}},
                })

    def test_invalid_native_money_does_not_calculate(self):
        bindings = self.write_bindings("BadCurrency.json", currency="EUR")
        result = certification.run_certified(
            self.aggregate, self.artifact, self.receipt, bindings, include_certificate=True
        )
        self.assertEqual(result, {
            "status": "blocked", "closing": {}, "emissions": {},
            "diagnostics": [{"code": "UNSUPPORTED_CURRENCY"}], "certificate": self.checked,
        })

    def test_missing_receipt_and_other_approved_source_are_blocked(self):
        with self.assertRaises(DataError) as missing:
            certification.verify(self.aggregate, self.artifact, self.work / "Absent.json")
        self.assertEqual(missing.exception.code, "CERT_CERTIFICATE_MISSING")
        with self.assertRaises(DataError) as other:
            certification.verify(self.row, self.artifact, self.receipt)
        self.assertEqual(other.exception.code, "CERT_CERTIFICATE_MISMATCH")

    def test_changed_authored_rule_and_linked_policy_are_blocked(self):
        changed = self.work / "Changed.spl"
        changed.write_bytes(self.aggregate.read_bytes().replace(b"50%", b"40%"))
        with self.assertRaises(DataError) as source_error:
            certification.verify(changed, self.artifact, self.receipt)
        self.assertEqual(source_error.exception.code, "CERT_SOURCE_UNSUPPORTED")
        link = certification.default_link()
        policy = link["modules"][0]
        policy["source"] = policy["source"].replace('"half_even")', '"floor")')
        policy["descriptor"]["source"]["sha256"] = sha256(policy["source"].encode()).hexdigest()
        policy["reference"]["sha256"] = "0" * 64
        manifest = self.work / "ChangedLink.json"
        write_json(manifest, link)
        with self.assertRaises(DataError) as policy_error:
            certification.verify(self.aggregate, self.artifact, self.receipt, link=manifest)
        self.assertEqual(policy_error.exception.code, "CERT_POLICY_MISMATCH")

    def test_changed_artifact_and_rehashed_receipt_are_blocked_before_proof(self):
        changed = self.work / "Changed.lean"
        changed.write_bytes(self.artifact.read_bytes() + b"\n-- altered bytes\n")
        forged = self.work / "Rehashed.json"
        write_json(forged, {**self.checked, "artifact_sha256": sha256(changed.read_bytes()).hexdigest()})
        for receipt in [self.receipt, forged]:
            with self.subTest(receipt=receipt.name), patch.object(certification, "_check_proof") as proof:
                with self.assertRaises(DataError) as error:
                    certification.verify(self.aggregate, changed, receipt)
                self.assertEqual(error.exception.code, "CERT_ARTIFACT_MISMATCH")
                proof.assert_not_called()

    def test_independent_kernel_claim_rejects_type_correct_wrong_translation(self):
        def wrong_translation(source, target, *, link):
            changed = source.with_name("WrongExpansion.spl")
            changed.write_bytes(source.read_bytes().replace(b"50%", b"40%"))
            return compile_schedule(changed, target, link=link)

        artifact = self.work / "Mistranslated.lean"
        receipt = self.work / "Mistranslated.json"
        with patch.object(certification, "compile_schedule", side_effect=wrong_translation):
            with self.assertRaises(DataError) as error:
                certification.certify(self.aggregate, artifact, receipt)
        self.assertEqual(error.exception.code, "CERT_PROOF_FAILED")
        self.assertFalse(artifact.exists())
        self.assertFalse(receipt.exists())
