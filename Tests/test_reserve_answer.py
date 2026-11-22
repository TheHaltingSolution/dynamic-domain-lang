"""RR-02 acceptance controls: separate reserve vintages and linked actual returns.

Expected per-vintage amounts are authored from the research answer, independently
of the SPL source. This is a ledger mechanism, not contractual reserve adoption.
"""
from copy import deepcopy
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, loads, money, read_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.mechanisms import run_mechanism
from spl_compiler.parser import parse


def binding():
    return read_json(ROOT / "cases/mechanisms/reserve-vintage-bindings.json")


def reference(package):
    source = ROOT / "cases/mechanisms/reserve-vintage.spl"
    checked = check_schedule(parse(source.read_text(encoding="utf-8")))
    return evaluate(checked, package["inputs"], package["openings"]).to_dict()


def change_amount(package, index, value):
    movement = package["inputs"]["movements"][index]
    movement["amount"] = money(value)
    evidence = next(e for e in package["inputs"]["evidence"] if e["evidence_id"] == movement["evidence_ref"])
    evidence["amount"] = money(value)


class ReserveAnswerTests(unittest.TestCase):
    def assert_blocked(self, result, code):
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["emissions"], {})
        self.assertEqual(result["closing"], {})
        self.assertEqual([d["code"] for d in result["diagnostics"]], [code])

    def test_research_checkpoint_preserves_both_vintages(self):
        result = run_mechanism("reserve-vintage", binding())
        self.assertEqual(result["status"], "calculated")
        rows = result["emissions"]["reserve_vintage_ledger"]
        columns = ["opening_balance", "additions", "applications", "releases", "closing_balance"]
        self.assertEqual({r["vintage_id"]: [r[k] for k in columns] for r in rows},
                         {"vintage-1": ["12", "0", "7", "5", "0"],
                          "vintage-2": ["0", "20", "0", "0", "20"]})
        total = result["emissions"]["reserve_ledger"]
        self.assertEqual([total[k] for k in columns], ["12", "20", "7", "5", "20"])
        self.assertEqual({r["vintage_id"]: r["balance"] for r in result["closing"]["reserve_vintages"]},
                         {"vintage-1": "0", "vintage-2": "20"})
        self.assertNotIn("payable", total)
        self.assertNotIn("earned", total)

    def test_serialized_state_carries_vintage_identity_into_liquidation(self):
        first = reference(binding())
        package = binding()
        carried = loads(canonical(first["closing"]))["reserve_vintages"]
        for row in carried:
            row["balance"] = money(row["balance"])
        package["openings"]["reserve_vintages"] = carried
        package["inputs"]["scope"]["period"] = {"start": "2026-07-01", "end": "2026-10-01"}
        package["inputs"]["observation_cutoff"] = "2026-10-15T00:00:00Z"
        package["inputs"]["movements"] = package["inputs"]["movements"][1:]
        package["inputs"]["evidence"] = package["inputs"]["evidence"][1:]
        for collection in ["movements", "evidence"]:
            for row in package["inputs"][collection]:
                row.update(vintage_id="vintage-2", effective_date="2026-08-01", observed_at="2026-08-02T00:00:00Z")
        change_amount(package, 0, "8")
        change_amount(package, 1, "12")
        result = run_mechanism("reserve-vintage", package)
        self.assertEqual([r["balance"] for r in result["closing"]["reserve_vintages"]], ["0", "0"])
        self.assertEqual(result["emissions"]["reserve_ledger"]["closing_balance"], "0")

    def test_unrelated_vintage_balance_cannot_cover_old_vintage_application(self):
        package = binding()
        # Aggregate funds 32 cover aggregate outflow 18; vintage-1 only has 12.
        change_amount(package, 1, "13")
        self.assert_blocked(run_mechanism("reserve-vintage", package), "RES_MOVEMENT_EXCEEDS_AVAILABLE")

    def test_actual_return_and_authorized_release_evidence_are_required(self):
        for index in [0, 1, 2]:
            with self.subTest(index=index):
                package = binding()
                package["inputs"]["evidence"].pop(index)
                self.assert_blocked(reference(package), "RES_EVIDENCE_REQUIRED")
        package = binding()
        package["inputs"]["evidence"][1]["kind"] = "authorized_release"
        self.assert_blocked(run_mechanism("reserve-vintage", package), "RES_EVIDENCE_WRONG_KIND")

    def test_duplicate_identity_and_evidence_reuse_block(self):
        for collection, key, code in [("movements", "inputs", "DUPLICATE_EVENT_ID"),
                                      ("evidence", "inputs", "DUPLICATE_EVIDENCE_ID"),
                                      ("reserve_vintages", "openings", "DUPLICATE_VINTAGE_ID")]:
            with self.subTest(collection=collection):
                package = binding()
                package[key][collection].append(deepcopy(package[key][collection][0]))
                self.assert_blocked(reference(package), code)
        package = binding()
        duplicate = deepcopy(package["inputs"]["movements"][1])
        duplicate["event_id"] = "second-application"
        package["inputs"]["movements"].append(duplicate)
        self.assert_blocked(run_mechanism("reserve-vintage", package), "RES_EVIDENCE_ALREADY_APPLIED")

    def test_scope_purpose_currency_vintage_authority_and_amount_must_match(self):
        changes = [("movements", "pool_id", "other", "RES_WRONG_SCOPE"),
                   ("movements", "purpose", "payment_holdback", "RES_WRONG_PURPOSE"),
                   ("movements", "currency", "EUR", "RES_WRONG_CURRENCY"),
                   ("movements", "vintage_id", "missing", "RES_WRONG_VINTAGE"),
                   ("evidence", "pool_id", "other", "RES_EVIDENCE_WRONG_SCOPE"),
                   ("evidence", "purpose", "payment_holdback", "RES_EVIDENCE_WRONG_PURPOSE"),
                   ("evidence", "currency", "EUR", "RES_EVIDENCE_WRONG_CURRENCY"),
                   ("evidence", "vintage_id", "other", "RES_EVIDENCE_WRONG_VINTAGE"),
                   ("evidence", "approved", False, "RES_AUTHORITY_REQUIRED"),
                   ("evidence", "amount", money("19"), "RES_EVIDENCE_MISMATCH")]
        for collection, field, value, code in changes:
            with self.subTest(collection=collection, field=field):
                package = binding()
                package["inputs"][collection][0][field] = value
                self.assert_blocked(reference(package), code)
        package = binding()
        package["openings"]["reserve_vintages"][0]["purpose"] = "payment_holdback"
        self.assert_blocked(reference(package), "RES_WRONG_PURPOSE")

    def test_effective_date_selects_period_while_observation_uses_exact_instant(self):
        for collection, code in [("movements", "RES_MOVEMENT_NOT_AVAILABLE"),
                                 ("evidence", "RES_EVIDENCE_NOT_AVAILABLE")]:
            package = binding()
            # Same UTC instant as cutoff despite different textual date/offset.
            package["inputs"][collection][0]["observed_at"] = "2026-07-14T17:00:00-07:00"
            self.assert_blocked(reference(package), code)
            package["inputs"][collection][0]["observed_at"] = "2026-07-14T16:59:59.999999999-07:00"
            self.assertEqual(reference(package)["status"], "calculated")
        package = binding()
        package["inputs"]["movements"][0]["effective_date"] = "2026-07-01"
        package["inputs"]["evidence"][0]["effective_date"] = "2026-07-01"
        self.assert_blocked(reference(package), "RES_OUTSIDE_PERIOD")
        package = binding()
        package["inputs"]["evidence"][0]["observed_at"] = "2026-07-14T17:00:00.000000001-07:00"
        self.assert_blocked(run_mechanism("reserve-vintage", package), "RES_EVIDENCE_NOT_AVAILABLE")


if __name__ == "__main__":
    unittest.main()
