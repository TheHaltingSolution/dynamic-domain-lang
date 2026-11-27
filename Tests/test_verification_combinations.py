"""Independent outcomes for two composed, certified Readable SPL contracts."""

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import exact, read_json, write_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import linking_manifest, resolve_module
from spl_compiler.verification import certify, run


CASE = ROOT / "cases/verification-combinations"


class VerificationCombinationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = TemporaryDirectory(prefix="spl-combined-tests-")
        cls.addClassCleanup(scratch.cleanup)
        cls.work = Path(scratch.name)
        cls.share = cls.work / "share"
        certify(CASE / "registered-share-readable.spl", cls.share)
        module = resolve_module(read_json(CASE / "reference.json"), ROOT)
        link = cls.work / "link.json"
        write_json(link, linking_manifest(module))
        cls.advance = cls.work / "advance"
        certificate = certify(module.source_path, cls.advance, link=link, mode="series")
        if "consumed.link.json" not in certificate["files"]:
            raise AssertionError("certificate omitted the linked validator and rounding closure")
        cls.advance_input = read_json(CASE / "advance-recovery-bindings.json")

    def test_registered_unique_selection_has_a_half_even_tie_and_rejects_overlap(self):
        sample = CASE / "share-bindings.json"
        accepted = run(self.share, sample)
        self.assertEqual(accepted["status"], "calculated")
        self.assertEqual(exact(accepted["emissions"]["share"]), Fraction(1, 2))
        # USD 0.03 × 1/2 is 1.5 cents, which rounds to the even two cents.
        self.assertEqual(exact(accepted["emissions"]["payable"]), Fraction(2, 100))

        overlap = read_json(sample)
        overlap["inputs"]["renewal_eligible"] = True
        path = self.work / "overlap.json"
        write_json(path, overlap)
        blocked = run(self.share, path)
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["diagnostics"], [{"code": "AMBIGUOUS_RULE"}])
        self.assertEqual(blocked["emissions"], {})

    def test_priority_rounding_reports_and_structured_closing_across_three_quarters(self):
        output = self.work / "publication"
        result = run(self.advance, CASE / "advance-recovery-bindings.json", output=output)
        self.assertEqual(result, load_completed_result(output))
        self.assertEqual(result["status"], "calculated")
        # Receipt basis, selected rate, earned, recovery, payable, carried advance, next start.
        expected = [
            ("0.25", "0.50", "0.12", "0.12", "0.00", "0.08", "2026-04-01"),
            ("0.54", "0.25", "0.14", "0.08", "0.06", "0.00", "2026-07-01"),
            ("0.05", "0.10", "0.00", "0.00", "0.00", "0.00", "2026-10-01"),
        ]
        for step, quarter_input, known in zip(result["periods"], self.advance_input["periods"], expected, strict=True):
            scope = quarter_input["scope"]
            with self.subTest(quarter=scope["period"]["start"]):
                pool = step["emissions"]["pool"]
                closing = step["closing"]["ledger"]
                fields = ("basis", "rate", "earned", "recouped", "payable")
                self.assertEqual(tuple(exact(pool[key]) for key in fields), tuple(map(Fraction, known[:5])))
                self.assertEqual(exact(closing["balance"]), Fraction(known[5]))
                self.assertEqual(closing["next_start"], known[6])
                for identity in ("agreement_id", "participant_id", "pool_id"):
                    self.assertEqual(pool[identity], scope[identity])
                    self.assertEqual(closing[identity], scope[identity])
                self.assertEqual(pool["period"], scope["period"])
        self.assertEqual(result["closing"], result["periods"][-1]["closing"])

    def test_linked_admission_discards_the_series_on_an_invalid_later_receipt(self):
        invalid = deepcopy(self.advance_input)
        invalid["periods"][1]["receipts"][0]["cash_received_date"] = "2026-07-01"
        self.assert_series_rejected(invalid, "RECEIPT_OUTSIDE_PERIOD", 1)

    def test_opening_and_successor_scope_are_checked_before_calculation(self):
        invalid = deepcopy(self.advance_input)
        invalid["openings"]["ledger"]["balance"]["value"] = "-0.01"
        self.assert_series_rejected(invalid, "ADVANCE_NEGATIVE_OPENING", 0)
        invalid = deepcopy(self.advance_input)
        invalid["periods"][1]["scope"]["pool_id"] = "different-pool"
        self.assert_series_rejected(invalid, "ADVANCE_SCOPE_MISMATCH", 1)
        invalid = deepcopy(self.advance_input)
        del invalid["periods"][1]
        self.assert_series_rejected(invalid, "ADVANCE_PERIOD_DISCONTINUITY", 1)

    def assert_series_rejected(self, inputs, code, index):
        path = self.work / (code + ".json")
        write_json(path, inputs)
        result = run(self.advance, path)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["diagnostics"], [{"code": code, "period_index": index}])
        self.assertEqual(result["periods"], [])
        self.assertEqual(result["closing"], {})


if __name__ == "__main__":
    unittest.main()
