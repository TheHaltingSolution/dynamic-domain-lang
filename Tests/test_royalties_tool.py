"""Acceptance and publication checks through the royalties tool's actual route."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from spl_compiler import artifacts, certification, royalties
from spl_compiler.lean_tools import ROOT, lean


class RoyaltiesToolTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(prefix="spl-royalties-test-")
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.workspace = self.root / "draft"
        self.output = self.root / "result"
        self.sample = self.receipts("sample", "0.01", "0.01")

    def receipts(self, name, first, second, *, second_id="receipt-2"):
        path = self.root / (name + ".json")
        path.write_text(json.dumps({"receipts": [
            {"id": "receipt-1", "amount": first}, {"id": second_id, "amount": second}]}), encoding="utf-8")
        return path

    def cli(self, command, *paths, status=0):
        # The embedded Windows Python can have a different checkout in its
        # ._pth. Select this checkout before entering the actual module CLI.
        entry = "import runpy, sys; sys.path.insert(0, '.'); runpy.run_module('spl_compiler.royalties', run_name='__main__')"
        process = subprocess.run([sys.executable, "-B", "-c", entry, command, *map(str, paths)],
                                 cwd=ROOT, capture_output=True, encoding="utf-8", timeout=360)
        self.assertEqual(process.returncode, status, process.stdout + process.stderr)
        return json.loads(process.stdout)

    def prepare(self, rounding="aggregate"):
        royalties.init(self.workspace, rounding=rounding)
        review = royalties.preview(self.workspace, [self.sample])
        royalties.approve(self.workspace, review["review_sha256"])
        return royalties.compile_approved(self.workspace)

    def test_participant_reviews_approves_and_reloads_later_period(self):
        self.assertEqual(self.cli("init", self.workspace)["status"], "draft")
        later = self.receipts("later", "0.13", "0.09")
        review = self.cli("preview", self.workspace, self.sample, later)
        self.assertEqual(review["status"], "preview")
        example = review["examples"][0]
        self.assertEqual(example["half_even_usd_cents"], {"row": 0, "aggregate": 1})
        self.assertEqual(example["interpreted_participation"], {"value": "0.01", "currency": "USD"})
        self.assertEqual(review["examples"][1]["interpreted_participation"]["value"], "0.11")
        self.assertFalse((self.workspace / royalties.COMPILED).exists())
        blocked = self.cli("compile", self.workspace, status=1)
        self.assertEqual(blocked["diagnostics"][0]["code"], "APPROVAL_REQUIRED")
        wrong = self.cli("approve", self.workspace, "0" * 64, status=1)
        self.assertEqual(wrong["diagnostics"][0]["code"], "REVIEW_DIGEST_MISMATCH")
        self.assertEqual(self.cli("approve", self.workspace, review["review_sha256"])["status"], "approved")
        compiled = self.cli("compile", self.workspace)
        self.assertEqual(compiled["status"], "certified")
        result = self.cli("run", self.workspace, later, self.output)
        self.assertEqual(result["status"], "calculated")
        self.assertEqual(result["results"]["participation"], {"value": "0.11", "currency": "USD"})
        self.assertEqual(result["review_sha256"], review["review_sha256"])
        self.assertEqual(result["certificate"], compiled["certificate"])
        self.assertEqual(result["certificate"]["link_sha256"], review["linked_policy_manifest_sha256"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertEqual(result["closing_state"], [])
        self.assertEqual(self.cli("reload", self.output), result)
        target = self.workspace / "builds" / compiled["build"] / "Settlement.lean"
        with target.open("ab") as stream:
            stream.write(b"\n-- replaced after approval\n")
        refusal = self.cli("run", self.workspace, later, self.output, status=1)
        self.assertEqual(refusal["diagnostics"][0]["code"], "CERT_ARTIFACT_MISMATCH")
        self.assertEqual(self.cli("reload", self.output, status=1), refusal)

    def test_row_review_and_later_exact_rationals(self):
        self.prepare("row")
        result = self._run(self.sample)
        self.assertEqual(result["results"]["participation"]["value"], "0")
        rational = self.receipts("rational", {"numerator": "1", "denominator": "3"}, "-0.01")
        result = self._run(rational)
        self.assertEqual(result["results"]["participation"], {"value": "0.17", "currency": "USD"})
        self.assertEqual(result["receipts"][0]["amount"], {"numerator": "1", "denominator": "3"})

    def _run(self, receipts):
        return royalties.run(self.workspace, receipts, self.output)

    def test_new_examples_preserve_the_approval_but_changed_source_requires_review(self):
        certified = self.prepare()
        review = royalties.preview(self.workspace, [self.receipts("other", "1", "2")])
        self.assertNotEqual(review["review_sha256"], certified["review_sha256"])
        result = royalties.run(self.workspace, self.sample, self.output)
        self.assertEqual(result["review_sha256"], certified["review_sha256"])
        shutil.copyfile(royalties.FIXTURES / "row-readable.spl", self.workspace / royalties.SOURCE)
        blocked = royalties.run(self.workspace, self.sample, self.output)
        self.assertEqual(blocked["diagnostics"][0]["code"], "STALE_REVIEW")
        review = royalties.preview(self.workspace, [self.sample])
        royalties.approve(self.workspace, review["review_sha256"])
        blocked = royalties.run(self.workspace, self.sample, self.output)
        self.assertEqual(blocked["diagnostics"][0]["code"], "STALE_CERTIFICATE")

    def test_admission_rejection_replaces_prior_success(self):
        self.prepare()
        self._run(self.sample)
        self.assertEqual(royalties.reload(self.output)["status"], "calculated")
        duplicate = self.receipts("duplicate", "0.01", "0.01", second_id="receipt-1")
        blocked = royalties.run(self.workspace, duplicate, self.output)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["diagnostics"][0]["code"], "DUPLICATE_RECEIPT_ID")
        self.assertEqual(blocked["diagnostics"][0]["pointer"], "/receipts/1/id")
        self.assertEqual(blocked["results"], {})
        self.assertEqual(blocked["closing_state"], [])
        self.assertEqual(royalties.reload(self.output), blocked)
        omitted = self.root / "omitted.json"
        omitted.write_text('{"receipts":[{"id":"receipt-1","amount":"0.01"}]}', encoding="utf-8")
        self.assertEqual(self._run(omitted)["diagnostics"][0]["code"], "RECEIPT_COUNT")
        oversized = self.root / "oversized.json"
        oversized.write_bytes(b" " * (royalties.MAX_RECEIPT_BYTES + 1))
        self.assertEqual(self._run(oversized)["diagnostics"][0]["code"], "RECEIPT_RESOURCE_LIMIT")

    def test_interruption_before_completion_cannot_reload_compatibility_view(self):
        self.prepare()
        self._run(self.sample)
        original_write = artifacts._atomic_bytes

        def interrupt(path, payload):
            if path == self.output / "completion.json" and json.loads(payload)["status"] == "completed":
                raise OSError("simulated interruption at completion write")
            original_write(path, payload)

        with patch.object(artifacts, "_atomic_bytes", side_effect=interrupt):
            with self.assertRaisesRegex(artifacts.PublicationError, "simulated interruption"):
                self._run(self.sample)
        self.assertEqual(json.loads((self.output / "result.json").read_text(encoding="utf-8"))["status"], "calculated")
        with self.assertRaisesRegex(artifacts.PublicationError, "PUBLICATION_NOT_COMPLETED"):
            royalties.reload(self.output)
        self._run(self.sample)
        self.assertEqual(royalties.reload(self.output)["results"]["participation"]["value"], "0.01")

    def test_settlement_timeout_publishes_a_blocked_result(self):
        self.prepare()

        def short_execution_budget(args, *other, **options):
            if args[0] == "--run" and Path(args[1]).name == "CertifiedArtifact.lean":
                return lean(args, timeout=0.000001)
            return lean(args, *other, **options)

        with patch.object(certification, "lean", side_effect=short_execution_budget):
            blocked = self._run(self.sample)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["diagnostics"][0]["code"], "LEAN_RESOURCE_LIMIT")
        self.assertEqual(blocked["results"], {})
        self.assertEqual(blocked["closing_state"], [])
        self.assertEqual(royalties.reload(self.output), blocked)


if __name__ == "__main__":
    unittest.main()
