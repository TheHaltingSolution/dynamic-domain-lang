"""Independent controls for explicitly selected synthetic accounting mechanisms."""
from copy import deepcopy
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, loads, money, read_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.mechanisms import run_mechanism
from spl_compiler.parser import parse


def binding(case):
    return read_json(ROOT / "cases/mechanisms" / (case + "-bindings.json"))


def reference(case, values):
    path = ROOT / "cases/mechanisms" / (case + ".spl")
    return evaluate(check_schedule(parse(path.read_text(encoding="utf-8"))), values["inputs"], values["openings"]).to_dict()


class MechanismTests(unittest.TestCase):
    def assert_blocked(self, result, code):
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["emissions"], {})
        self.assertEqual(result["closing"], {})
        self.assertEqual(result["diagnostics"][0]["code"], code)

    def test_prospective_advance_issue_is_distinct_from_receipts_or_costs(self):
        r = run_mechanism("advance-issues", binding("advance-issues"))
        self.assertEqual(r["diagnostics"], [])
        line = r["emissions"]["advances"]
        self.assertEqual({k: line[k] for k in ["opening_balance", "additions", "available", "earned", "recovered", "payable", "closing_balance"]},
                         {"opening_balance": "0", "additions": "15000", "available": "15000", "earned": "10000", "recovered": "10000", "payable": "0", "closing_balance": "5000"})
        self.assertEqual(r["closing"], {"prepayment": "5000"})

    def test_new_issue_after_prior_period_does_not_reopen_prior_earned_payment(self):
        q1 = binding("advance-issues")
        q1["inputs"]["scope"]["period"] = {"start": "2026-01-01", "end": "2026-04-01"}
        q1["inputs"].update(issues=[], earned=money("20000"))
        q1["openings"]["prepayment"] = money("15000")
        first = run_mechanism("advance-issues", q1)
        self.assertEqual(first["emissions"]["advances"]["payable"], "5000")
        q2 = binding("advance-issues")
        q2["openings"]["prepayment"] = money(loads(canonical(first["closing"]))["prepayment"])
        second = run_mechanism("advance-issues", q2)
        self.assertEqual(second["closing"]["prepayment"], "5000")
        self.assertEqual(second["emissions"]["advances"]["payable"], "0")
        self.assertEqual(first["emissions"]["advances"]["payable"], "5000")

    def test_reserve_vintage_rollforward_and_serialized_liquidation(self):
        first = run_mechanism("reserve-vintage", binding("reserve-vintage"))
        line = first["emissions"]["reserve_ledger"]
        self.assertEqual({k: line[k] for k in ["opening_balance", "additions", "applications", "releases", "closing_balance"]},
                         {"opening_balance": "12", "additions": "20", "applications": "7", "releases": "5", "closing_balance": "20"})
        self.assertEqual({r["vintage_id"]: r["closing_balance"] for r in first["emissions"]["reserve_vintage_ledger"]},
                         {"vintage-1": "0", "vintage-2": "20"})
        q2 = binding("reserve-vintage")
        q2["inputs"]["scope"]["period"] = {"start": "2026-07-01", "end": "2026-10-01"}
        q2["inputs"]["observation_cutoff"] = "2026-10-15T00:00:00Z"
        q2["inputs"]["movements"] = q2["inputs"]["movements"][1:]
        q2["inputs"]["evidence"] = q2["inputs"]["evidence"][1:]
        for collection in ["movements", "evidence"]:
            for row, value in zip(q2["inputs"][collection], ["8", "12"]):
                row.update(effective_date="2026-08-01", observed_at="2026-08-02T00:00:00Z", vintage_id="vintage-2")
                row["amount"] = money(value)
        carried = loads(canonical(first["closing"]))["reserve_vintages"]
        for row in carried:
            row["balance"] = money(row["balance"])
        q2["openings"]["reserve_vintages"] = carried
        second = run_mechanism("reserve-vintage", q2)
        self.assertEqual({r["vintage_id"]: r["balance"] for r in second["closing"]["reserve_vintages"]},
                         {"vintage-1": "0", "vintage-2": "0"})
        self.assertEqual(second["emissions"]["reserve_ledger"]["closing_balance"], "0")
        self.assertNotIn("payable", second["emissions"]["reserve_ledger"])

    def test_revised_obligation_preserves_issued_and_actual_payment(self):
        r = run_mechanism("correction-payments", binding("correction-payments"))
        line = r["emissions"]["obligation_reconciliation"]
        self.assertEqual({k: line[k] for k in ["original_issued", "revised_entitlement", "correction_delta", "actual_paid", "remaining_obligation"]},
                         {"original_issued": "100", "revised_entitlement": "90", "correction_delta": "-10", "actual_paid": "80", "remaining_obligation": "10"})
        self.assertNotIn("payable", line)
        self.assertEqual(r["issuance_status"], "unissued")

    def test_duplicate_payment_is_not_applied_again(self):
        p = binding("correction-payments")
        p["inputs"]["payments"].append(deepcopy(p["inputs"]["payments"][0]))
        self.assert_blocked(run_mechanism("correction-payments", p), "DUPLICATE_EVENT_ID")

    def test_overpayment_and_excess_reserve_movements_block(self):
        correction = binding("correction-payments")
        correction["inputs"]["revised_entitlement"] = money("70")
        self.assert_blocked(run_mechanism("correction-payments", correction), "CORR_OVERPAYMENT_POLICY_REQUIRED")
        reserve = binding("reserve-vintage")
        reserve["inputs"]["movements"][1]["amount"] = money("40")
        reserve["inputs"]["evidence"][1]["amount"] = money("40")
        self.assert_blocked(run_mechanism("reserve-vintage", reserve), "RES_MOVEMENT_EXCEEDS_AVAILABLE")

    def test_wrong_scope_authority_and_vintage_do_not_become_zero(self):
        cases = [("advance-issues", "issues", "ADV_ISSUE_WRONG_SCOPE", "ADV_ISSUE_AUTHORITY_REQUIRED"),
                 ("reserve-vintage", "movements", "RES_WRONG_SCOPE", "RES_AUTHORITY_REQUIRED"),
                 ("correction-payments", "payments", "CORR_PAYMENT_WRONG_SCOPE", "CORR_PAYMENT_AUTHORITY_REQUIRED")]
        for case, field, scope_error, authority_error in cases:
            p = binding(case)
            p["inputs"][field][0]["pool_id"] = "unrelated"
            self.assert_blocked(reference(case, p), scope_error)
            p = binding(case)
            approval_field = "evidence" if case == "reserve-vintage" else field
            p["inputs"][approval_field][0]["approved"] = False
            self.assert_blocked(reference(case, p), authority_error)
        p = binding("reserve-vintage")
        p["inputs"]["movements"][0]["vintage_id"] = "another-vintage"
        self.assert_blocked(reference("reserve-vintage", p), "RES_WRONG_VINTAGE")

    def test_issue_at_observation_cutoff_is_excluded(self):
        p = binding("advance-issues")
        p["inputs"]["issues"][0]["observed_at"] = p["inputs"]["observation_cutoff"]
        result = run_mechanism("advance-issues", p)
        self.assertEqual(result["status"], "calculated")
        self.assertEqual(result["emissions"]["advances"]["additions"], "0")
        self.assertFalse(result["emissions"]["advance_issue_audit"][0]["included"])


if __name__ == "__main__":
    unittest.main()
