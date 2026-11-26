"""Independent hand controls for synthetic withholding and issued/unissued carry."""
import ast
from copy import deepcopy
from fractions import Fraction
import itertools
import json
from pathlib import Path
import unittest

from oracles.settlement_adjustments import SettlementOracleError, exact_json, settlement_adjustments


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/settlement/neutral.json").read_text(encoding="utf-8"))


def unissued(amounts=("100",), rate="0.10", minimum="25"):
    data = fixture()
    prototype = data["earned"][0]
    data["earned"] = [{**deepcopy(prototype), "id": f"earned-{index}", "amount": amount,
                       "source_ref": f"synthetic-earned-{index}"} for index, amount in enumerate(amounts)]
    data["issued"], data["payments"], data["applications"] = [], [], []
    data["terms"].update(withholding_rate=rate, minimum_payout=minimum)
    return data


def successor(previous, quarter=2, amounts=("10",)):
    """Serialize exact neutral predecessor; preserve original issue evidence."""
    first = fixture()
    period = ({"start": "2026-04-01", "end": "2026-07-01"} if quarter == 2 else
              {"start": "2026-07-01", "end": "2026-10-01"})
    month, cutoff_month = ("06", "07") if quarter == 2 else ("09", "10")
    case_id, source_id = f"settlement-q{quarter}", f"source-q{quarter}"
    source_evidence = {**deepcopy(first["evidence"][0]), "id": source_id,
                       "observed_at": f"2026-{cutoff_month}-01T02:00:00Z"}
    data = {**first, "case_id": case_id, "period": period,
            "cutoff": f"2026-{cutoff_month}-03T00:00:00Z",
            "opening_state": exact_json(previous["closing_state"]),
            "prior_result": exact_json({"source_case_id": previous["source_case_id"],
                                         "period": previous["period"], "closing_state": previous["closing_state"]}),
            "earned": [], "issued": [], "payments": [], "applications": []}
    for index, amount in enumerate(amounts):
        data["earned"].append({**deepcopy(first["earned"][0]), "id": f"earned-q{quarter}-{index}",
                               "amount": amount, "effective_date": f"2026-{month}-15",
                               "observed_at": f"2026-{month}-28T00:00:00Z",
                               "evidence_ref": source_id, "source_ref": f"synthetic-q{quarter}-earned-{index}"})
    # Original source evidence is retained, not a prior completeness attestation.
    data["evidence"] = [deepcopy(first["evidence"][0]), source_evidence,
                        {**deepcopy(first["evidence"][1]), "id": f"complete-q{quarter}",
                         "period": deepcopy(period), "observed_at": f"2026-{cutoff_month}-02T00:00:00Z"}]
    return data


class SettlementOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(SettlementOracleError) as raised:
            settlement_adjustments(data)
        self.assertEqual(raised.exception.code, code)
        return raised.exception

    def test_baseline_hand_controls_and_original_issue(self):
        result = settlement_adjustments(fixture())
        fields = ("earned", "withheld", "current_net", "opening_unpaid", "issuance_candidate",
                  "new_eligible_due", "new_issued", "actual_paid", "closing_unissued",
                  "closing_issued_outstanding", "closing_unpaid")
        self.assertEqual([result[key] for key in fields], [100, 10, 90, 0, 90, 90, 90, 80, 0, 10, 10])
        self.assertEqual(result["payment_evidence_status"], "complete_with_events")
        obligation = result["closing_state"]["issued_obligations"][0]
        self.assertEqual((obligation["id"], obligation["amount"], obligation["paid_to_date"]), ("issue-q1", 90, 80))
        self.assertEqual((obligation["source_ref"], obligation["evidence_ref"]),
                         ("synthetic-issued-statement-q1", "source-q1"))
        self.assertEqual(result["closing_state"]["source_case_id"], "settlement-q1")
        self.assertNotIn("prior_result_ref", result["closing_state"])

    def test_half_even_ties_and_round_once_after_aggregation(self):
        for earned, withheld, net in (("0.01", "0", "0.01"), ("0.03", "0.02", "0.01"),
                                       ("0.05", "0.02", "0.03"), ("0.07", "0.04", "0.03")):
            with self.subTest(earned=earned):
                result = settlement_adjustments(unissued((earned,), rate="0.5"))
                self.assertEqual((result["withheld"], result["current_net"]), (Fraction(withheld), Fraction(net)))
        result = settlement_adjustments(unissued(("0.01", "0.01"), rate="0.5"))
        self.assertEqual((result["earned"], result["withheld"], result["current_net"]),
                         (Fraction("0.02"), Fraction("0.01"), Fraction("0.01")))

    def test_threshold_equality_and_eligibility_is_not_issuance(self):
        for amount, expected in (("24.99", False), ("25", True), ("25.01", True)):
            with self.subTest(amount=amount):
                result = settlement_adjustments(unissued((amount,), rate="0"))
                self.assertEqual(result["threshold_reached"], expected)
                self.assertEqual(result["new_eligible_due"], Fraction(amount) if expected else 0)
                self.assertEqual((result["new_issued"], result["actual_paid"]), (0, 0))
                self.assertEqual(result["closing_unissued"], Fraction(amount))
                self.assertEqual(result["payment_evidence_status"], "complete_no_events")
        data = unissued(("25",), rate="0")
        data["issued"] = [{**fixture()["issued"][0], "amount": "25"}]
        result = settlement_adjustments(data)
        self.assertEqual((result["new_issued"], result["closing_unissued"], result["closing_issued_outstanding"]), (25, 0, 25))

    def test_zero_empty_and_endpoint_rates(self):
        for amounts in ((), ("0",)):
            result = settlement_adjustments(unissued(amounts))
            self.assertEqual([result[key] for key in ("earned", "withheld", "current_net", "actual_paid", "closing_unpaid")], [0] * 5)
        for rate, withheld, net in (("0", 0, 100), ("1", 100, 0)):
            result = settlement_adjustments(unissued(rate=rate))
            self.assertEqual((result["withheld"], result["current_net"]), (withheld, net))

    def test_three_period_carry_keeps_old_issuance_distinct(self):
        first = settlement_adjustments(fixture())
        middle_data = successor(first)
        middle = settlement_adjustments(middle_data)
        self.assertEqual([middle[key] for key in ("earned", "withheld", "current_net", "opening_issued_outstanding",
                                                  "issuance_candidate", "new_eligible_due", "total_eligible_due",
                                                  "closing_unissued", "closing_issued_outstanding", "closing_unpaid")],
                         [10, 1, 9, 10, 9, 0, 10, 9, 10, 19])
        last_data = successor(middle, quarter=3, amounts=("20",))
        template = fixture()
        last_data["issued"] = [{**deepcopy(template["issued"][0]), "id": "issue-q3", "amount": "27",
                                "issued_date": "2026-09-29", "observed_at": "2026-09-29T12:00:00Z",
                                "source_ref": "synthetic-issued-statement-q3", "evidence_ref": "source-q3"}]
        last_data["payments"] = [{**deepcopy(template["payments"][0]), "id": "payment-q3", "amount": "20",
                                  "paid_date": "2026-09-30", "observed_at": "2026-10-01T00:00:00Z",
                                  "source_ref": "synthetic-bank-q3", "evidence_ref": "source-q3"}]
        last_data["applications"] = [{**deepcopy(template["applications"][0]), "id": f"application-q3-{index}",
                                      "payment_id": "payment-q3", "issued_id": issued_id, "amount": "10",
                                      "observed_at": "2026-10-01T01:00:00Z", "evidence_ref": "source-q3",
                                      "source_ref": f"synthetic-remittance-q3-{index}"}
                                     for index, issued_id in enumerate(("issue-q1", "issue-q3"))]
        final = settlement_adjustments(last_data)
        self.assertEqual([final[key] for key in ("opening_unissued", "opening_issued_outstanding", "withheld", "current_net",
                                                 "issuance_candidate", "new_eligible_due", "new_issued", "actual_paid",
                                                 "closing_unissued", "closing_issued_outstanding", "closing_unpaid")],
                         [9, 10, 2, 18, 27, 27, 27, 20, 0, 17, 17])
        self.assertEqual([row["id"] for row in final["closing_state"]["issued_obligations"]], ["issue-q3"])
        self.assertIn("issued:issue-q1", final["closing_state"]["recognized_ids"])
        # Summed net earned less actual paid is the ending obligation, never
        # subtracting issued 90 or 27 as though those were bank payments.
        self.assertEqual(first["current_net"] + middle["current_net"] + final["current_net"]
                         - first["actual_paid"] - final["actual_paid"], 17)

    def test_old_issued_remains_payable_below_new_threshold(self):
        data = successor(settlement_adjustments(fixture()), amounts=())
        original = fixture()
        data["payments"] = [{**deepcopy(original["payments"][0]), "id": "old-payment-q2", "amount": "5",
                             "paid_date": "2026-06-30", "observed_at": "2026-07-01T00:00:00Z", "evidence_ref": "source-q2"}]
        data["applications"] = [{**deepcopy(original["applications"][0]), "id": "old-application-q2", "amount": "5",
                                 "payment_id": "old-payment-q2", "observed_at": "2026-07-01T01:00:00Z", "evidence_ref": "source-q2"}]
        result = settlement_adjustments(data)
        self.assertEqual((result["new_eligible_due"], result["total_eligible_due"], result["actual_paid"], result["closing_unpaid"]), (0, 10, 5, 5))
        self.assertEqual(result["withheld"], 0)

    def test_missing_complete_payment_evidence_is_not_zero(self):
        for has_events in (False, True):
            data = fixture() if has_events else unissued()
            data["evidence"] = data["evidence"][:1]
            error = self.reject(data, "SETTLEMENT_PAYMENT_POPULATION_REQUIRED")
            self.assertEqual(error.payment_evidence_status, "no_event_supplied")
            self.assertFalse(hasattr(error, "actual_paid"))
            self.assertFalse(hasattr(error, "closing_state"))

    def test_duplicate_category_ids_and_reused_history_block(self):
        for kind in ("earned", "issued", "payments", "applications", "evidence"):
            data = fixture()
            data[kind].append(deepcopy(data[kind][0]))
            with self.subTest(kind=kind):
                self.reject(data, "SETTLEMENT_DUPLICATE_ID")
        data = successor(settlement_adjustments(fixture()))
        data["earned"][0]["id"] = "earned-q1-a"
        self.reject(data, "SETTLEMENT_ALREADY_RECOGNIZED")
        data = fixture()
        data["earned"][0]["id"] = "payment-q1"
        result = settlement_adjustments(data)
        self.assertIn("earned:payment-q1", result["closing_state"]["recognized_ids"])
        self.assertIn("payments:payment-q1", result["closing_state"]["recognized_ids"])

    def test_original_issue_cannot_be_reissued_in_successor(self):
        data = successor(settlement_adjustments(fixture()), amounts=("100",))
        data["issued"] = [{**deepcopy(fixture()["issued"][0]), "issued_date": "2026-06-30",
                           "observed_at": "2026-07-01T00:00:00Z", "evidence_ref": "source-q2"}]
        self.reject(data, "SETTLEMENT_ALREADY_RECOGNIZED")

    def test_scope_currency_purpose_and_policy(self):
        changes = [("SETTLEMENT_CURRENCY", lambda d: d["scope"].update(currency="EUR")),
                   ("SETTLEMENT_OPENING_SCOPE", lambda d: d["opening_state"]["scope"].update(asset_id="other")),
                   ("SETTLEMENT_OPENING_SCOPE", lambda d: d["opening_state"].update(purpose="reserve")),
                   ("SETTLEMENT_OPENING_POLICY", lambda d: d["opening_state"].update(policy_revision="2")),
                   ("SETTLEMENT_POLICY", lambda d: d["terms"].update(evidence_class="approved")),
                   ("SETTLEMENT_FACT_SCOPE", lambda d: d["payments"][0]["scope"].update(pool_id="other")),
                   ("SETTLEMENT_EVIDENCE_SCOPE", lambda d: d["evidence"][0]["scope"].update(participant_id="other"))]
        for code, change in changes:
            with self.subTest(code=code):
                data = fixture(); change(data); self.reject(data, code)

    def test_minor_units_nonnegative_money_exact_rates_and_no_floats(self):
        for field in ("earned", "issued", "payments", "applications"):
            data = fixture(); data[field][0]["amount"] = "0.006"
            with self.subTest(field=field):
                self.reject(data, "SETTLEMENT_MINOR_UNIT")
        for amount in ("-0.01", "-1"):
            data = unissued((amount,)); self.reject(data, "SETTLEMENT_AMOUNT_DOMAIN")
        for rate in ("-0.1", "1.01"):
            data = unissued(rate=rate); self.reject(data, "SETTLEMENT_RATE_DOMAIN")
        for rate in (0.1, "1e-1", True):
            data = unissued(rate=rate); self.reject(data, "SETTLEMENT_EXACT_VALUE_REQUIRED")
        data = unissued(("0.006",), rate="1")
        self.reject(data, "SETTLEMENT_MINOR_UNIT")
        data = unissued(); data["terms"]["minimum_payout"] = "0.005"
        self.reject(data, "SETTLEMENT_MINOR_UNIT")

    def test_payment_application_conservation_caps_and_references(self):
        changes = [("SETTLEMENT_PAYMENT_CONSERVATION", lambda d: d["applications"][0].update(amount="79")),
                   ("SETTLEMENT_PAYMENT_CONSERVATION", lambda d: d.update(applications=[])),
                   ("SETTLEMENT_OBLIGATION_OVERPAYMENT", lambda d: (d["payments"][0].update(amount="91"), d["applications"][0].update(amount="91"))),
                   ("SETTLEMENT_APPLICATION_REFERENCE", lambda d: d["applications"][0].update(payment_id="unknown")),
                   ("SETTLEMENT_APPLICATION_REFERENCE", lambda d: d["applications"][0].update(issued_id="unknown")),
                   ("SETTLEMENT_ISSUE_AMOUNT", lambda d: d["issued"][0].update(amount="89")),
                   ("SETTLEMENT_ONE_NEW_ISSUE", lambda d: d["issued"].append({**deepcopy(d["issued"][0]), "id": "second-issue"})),
                   ("SETTLEMENT_AMOUNT_DOMAIN", lambda d: d["payments"][0].update(amount="0"))]
        for code, change in changes:
            with self.subTest(code=code):
                data = fixture(); change(data); self.reject(data, code)

    def test_evidence_fact_cutoff_and_exact_offset(self):
        data = fixture()
        data["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        data["earned"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
        self.assertEqual(settlement_adjustments(data)["earned"], 100)
        for group, code in (("earned", "SETTLEMENT_FACT_CUTOFF"), ("evidence", "SETTLEMENT_EVIDENCE_CUTOFF")):
            data = fixture(); data[group][0]["observed_at"] = data["cutoff"]
            self.reject(data, code)
        data = fixture(); data["earned"][0]["evidence_ref"] = "missing"
        self.reject(data, "SETTLEMENT_FACT_EVIDENCE")
        data = fixture(); data["evidence"][-1]["period"]["end"] = "2026-07-01"
        self.reject(data, "SETTLEMENT_COMPLETENESS_SCOPE")
        data = fixture(); data["evidence"].append({**deepcopy(data["evidence"][-1]), "id": "ambiguous-complete"})
        self.reject(data, "SETTLEMENT_COMPLETENESS_AMBIGUOUS")

    def test_selected_period_and_temporal_causality(self):
        for group, field in (("earned", "effective_date"), ("issued", "issued_date"), ("payments", "paid_date")):
            for day in ("2025-12-31", "2026-04-01"):
                data = fixture(); data[group][0][field] = day
                with self.subTest(group=group, day=day):
                    self.reject(data, "SETTLEMENT_FACT_PERIOD")
        data = fixture(); data["payments"][0]["paid_date"] = "2026-03-29"
        self.reject(data, "SETTLEMENT_PAYMENT_BEFORE_ISSUE")
        data = fixture(); data["payments"][0]["observed_at"] = "2026-03-30T23:00:00Z"
        self.reject(data, "SETTLEMENT_OBSERVATION_BEFORE_EVENT")
        data = fixture(); data["applications"][0]["observed_at"] = "2026-03-31T23:00:00Z"
        self.reject(data, "SETTLEMENT_APPLICATION_OBSERVATION")

    def test_serialized_predecessor_boundary_scope_history_and_case_identity(self):
        original = successor(settlement_adjustments(fixture()))
        self.assertEqual(json.loads(json.dumps(original)), original)
        for code, change in [
            ("SETTLEMENT_PREDECESSOR_REQUIRED", lambda d: d.pop("prior_result")),
            ("SETTLEMENT_OPENING_BOUNDARY", lambda d: d["opening_state"].update(boundary="2026-04-02")),
            ("SETTLEMENT_PREDECESSOR_BOUNDARY", lambda d: d["prior_result"]["period"].update(end="2026-03-31")),
            ("SETTLEMENT_PREDECESSOR_MISMATCH", lambda d: d["prior_result"].update(source_case_id="other-case")),
            ("SETTLEMENT_PREDECESSOR_MISMATCH", lambda d: d["opening_state"].update(deferred_unissued="1")),
            ("SETTLEMENT_PREDECESSOR_MISMATCH", lambda d: d["opening_state"]["issued_obligations"][0].update(source_ref="changed")),
            ("SETTLEMENT_PREDECESSOR_MISMATCH", lambda d: d.update(case_id="settlement-q1")),
        ]:
            with self.subTest(code=code):
                data = deepcopy(original); change(data); self.reject(data, code)
        valid = deepcopy(original)
        valid["prior_result"]["result_ref"] = "result@sha256:" + "a" * 64
        self.assertEqual(settlement_adjustments(valid)["closing_unpaid"], 19)
        data = fixture(); data["opening_state"]["deferred_unissued"] = "10"
        self.reject(data, "SETTLEMENT_GENESIS")

    def test_small_finite_rounding_and_permutation_controls(self):
        for cents, tenths in itertools.product(range(8), range(11)):
            data = unissued((str(Fraction(cents, 100)),), rate=str(Fraction(tenths, 10)))
            result = settlement_adjustments(data)
            # Independently enumerate the nearest integer cent; ties choose even.
            exact_cents = Fraction(cents * tenths, 10)
            expected = min(range(cents + 1), key=lambda value: (abs(value - exact_cents), value % 2))
            self.assertEqual(result["withheld"], Fraction(expected, 100))
            self.assertGreaterEqual(result["current_net"], 0)
        data = fixture(); expected = settlement_adjustments(data)
        data["earned"].reverse(); data["evidence"].reverse()
        self.assertEqual(settlement_adjustments(data), expected)
        self.assertEqual(settlement_adjustments(data), settlement_adjustments(deepcopy(data)))

    def test_oracle_has_only_standard_library_dependencies(self):
        path = ROOT / "oracles/settlement_adjustments.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imported.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imported, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
