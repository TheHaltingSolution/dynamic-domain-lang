"""Original-fact independent controls, with no compiler implementation imports."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.lionsgate import LionsgateOracleError, exact_json, lionsgate


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/lg/neutral-oracle.json").read_text(encoding="utf-8"))


def event(data, kind):
    return next(row for row in data["package"]["evidence_events"] if row["kind"] == kind)


def decision(data, identity):
    return next(row for view in data["package"]["interpretations"] for row in view["decisions"]
                if row["decision_id"] == identity)


def cost(data, amount="300", *, eligible=True, incurred="2026-03-01", posting="2026-04-02"):
    p = data["package"]
    prototype = p["financial_facts"][0]
    row = {"fact_id": "cost-1", "batch_ref": deepcopy(prototype["batch_ref"]), "source_row": "cost-source:1",
           "event_kind": "incurred_cost", "amount": {"value": amount, "currency": "USD"},
           "asset_id": "work-D", "category": "approved_actual_third_party_cost",
           "dates": {"incurred_date": incurred, "posting_date": posting},
           "temporal_basis": {"kind": "incurred_date", "date": incurred}}
    p["financial_facts"].append(row)
    p["source_batches"][0]["row_count"] += 1
    p["parameters"]["cost_decisions"].append({"fact_id": row["fact_id"], "decision_id": "LG-TRUE-CASH-COST",
                                              "eligible": eligible, "branch": "lg", "reason": "Explicit synthetic selected cost eligibility"})
    decision(data, "LG-TRUE-CASH-COST").setdefault("cost_terms", []).append({"fact_id": row["fact_id"], "eligible": eligible, "branch": "lg"})
    return row


def allocated(data):
    """Original parent retained; one authorized destination consumes it once."""
    p = data["package"]
    parent = p["financial_facts"][0]
    p["assets"].append({"asset_id": "raw-bundle", "kind": "bundle"})
    parent["asset_id"] = "raw-bundle"
    metadata = {"source_fact_id": parent["fact_id"], "allocation_group_id": "lg-allocation-group",
                "method": "approved_weights", "method_version": "1", "authority_ref": "LG-TRUE-CASH",
                "policy_ref": "LG-TRUE-CASH", "scenario_id": p["manifest"]["scenario_id"],
                "effective": deepcopy(p["manifest"]["period"])}
    weights = [{"asset_id": "work-D", "weight": "1"}]
    data["allocation_authorities"] = [{**deepcopy(metadata), "weights": deepcopy(weights)}]
    p["allocations"] = [{**deepcopy(metadata), "allocation_id": "lg-allocation-1", "weight": "1",
                         "target_scope": {"agreement_id": "lg", "participant_id": "seller-group",
                                          "pool_id": "crossed-group", "asset_ids": ["work-D"]}}]
    decision(data, "LG-TRUE-CASH")["allocation_terms"] = deepcopy(weights)
    return data


class LionsgateOracleTests(unittest.TestCase):
    def reject(self, data, code=None):
        with self.assertRaises(LionsgateOracleError) as caught:
            lionsgate(data)
        if code:
            self.assertEqual(caught.exception.code, code)
        self.assertFalse(hasattr(caught.exception, "payable"))
        self.assertFalse(hasattr(caught.exception, "closing_state"))
        return caught.exception

    def test_neutral_preserves_original_raw_package(self):
        raw = json.loads((ROOT / "cases/lg/canonical-package.json").read_text(encoding="utf-8"))
        self.assertEqual(fixture()["package"], raw)
        self.assertTrue(all("observed_at" not in row for row in raw["financial_facts"]))

    def test_baseline_full_gate_and_separate_payout_all_intermediates(self):
        result = lionsgate(fixture())
        expected = {"opening_gate_gross": 100, "opening_gate_cost": 100, "cash_measure": 300,
                    "actual_cost_measure": 0, "non_video_receipts": 180, "home_video_receipts": 120,
                    "closing_gate_gross": 400, "closing_gate_cost": 100, "gate_surplus": 300,
                    "payout_base": 210, "gross_before_offset": 42, "producer_fee_offset": 12,
                    "gross_candidate": 30, "crossed_net_subtotal": 175, "net_candidate": 35,
                    "earned": 35, "payable": 35, "opening_payment_holdback": 0,
                    "holdback_addition": 0, "holdback_release": 0, "closing_payment_holdback": 0}
        for key, value in expected.items():
            with self.subTest(key=key):
                self.assertEqual(result[key], value)
        self.assertEqual(result["selected_label"], "net")
        self.assertEqual(result["closing_state"], {"gate_gross": 400, "gate_cost": 100, "payment_holdback": 0})
        self.assertEqual(sum(row["amount"] for row in result["contributions"]), 300)

    def test_original_evidence_and_unknown_paid_status_remain_explicit(self):
        data = fixture()
        result = lionsgate(data)
        self.assertEqual(result["outside_hurdle"], event(data, "hurdle_attestation"))
        self.assertEqual(result["work_gate_history"], event(data, "gate_history"))
        self.assertEqual(result["crossed_net_worksheet"], event(data, "crossed_net_worksheet"))
        self.assertEqual(result["net_ledger_basis"], "supplied_worksheet")
        self.assertEqual(result["gate_history_basis"], "supplied_attestation")
        self.assertEqual(result["payment_evidence_status"], "no_event_supplied")
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertEqual(result["professional_approval"], "not_established")
        self.assertNotIn("actual_paid", result)
        self.assertTrue(all(row["review_status"] == "proposed" and row["evidence_label"] == "research_assumption"
                            for row in result["review_records"]))

    def test_gross_winner_tie_and_proxy_change(self):
        for subtotal, label, earned in [("100", "gross", 30), ("150", "tie", 30), ("175", "net", 35)]:
            data = fixture()
            event(data, "crossed_net_worksheet")["amount"]["value"] = subtotal
            result = lionsgate(data)
            self.assertEqual((result["selected_label"], result["earned"]), (label, earned))
        data = fixture()
        data["package"]["parameters"]["policy"]["video_proxy"] = "0.5"
        result = lionsgate(data)
        self.assertEqual((result["cash_measure"], result["closing_gate_gross"], result["payout_base"], result["gross_candidate"]),
                         (300, 400, 240, 36))

    def test_work_gate_equality_is_distinct_from_outside_hurdle_timing(self):
        data = fixture()
        cost(data, "300")
        result = lionsgate(data)
        self.assertEqual((result["closing_gate_gross"], result["closing_gate_cost"], result["gate_surplus"], result["payable"]), (400, 400, 0, 35))
        for day in ["2026-01-01", "2026-01-02"]:
            changed = deepcopy(data)
            event(changed, "hurdle_attestation")["effective_date"] = day
            self.reject(changed, "LG_HURDLE_TIMING_POLICY_REQUIRED")

    def test_outside_and_history_evidence_missing_false_wrong_scope(self):
        for kind in ["hurdle_attestation", "gate_history"]:
            data = fixture()
            data["package"]["evidence_events"] = [row for row in data["package"]["evidence_events"] if row["kind"] != kind]
            self.reject(data, "LG_ORACLE_REQUIRED_EVIDENCE")
            data = fixture()
            event(data, kind)["satisfied"] = False
            self.reject(data, "LG_OUTSIDE_HURDLE_NOT_ATTAINED" if kind == "hurdle_attestation" else "LG_GATE_HISTORY_POLICY_REQUIRED")
        data = fixture()
        event(data, "gate_history")["period"]["end"] = "2026-03-31"
        self.reject(data, "LG_ORACLE_HISTORY_PERIOD")
        data = fixture()
        event(data, "gate_history")["asset_id"] = "other"
        self.reject(data, "LG_ORACLE_HISTORY_SCOPE")
        data = fixture()
        event(data, "hurdle_attestation")["agreement_id"] = "other"
        self.reject(data, "LG_ORACLE_EVIDENCE_SCOPE")

    def test_exact_evidence_cutoff_offset_and_submicroseconds(self):
        data = fixture()
        data["package"]["manifest"]["cutoff"] = "2026-12-31T00:00:00.0000002Z"
        event(data, "hurdle_attestation")["observed_at"] = "2026-12-31T01:00:00.0000001+01:00"
        self.assertEqual(lionsgate(data)["payable"], 35)
        for instant in ["2026-12-31T00:00:00.0000002Z", "2026-12-31T00:00:00.0000003Z"]:
            event(data, "hurdle_attestation")["observed_at"] = instant
            self.reject(data, "LG_ORACLE_EVIDENCE_CUTOFF")

    def test_receipt_date_half_open_no_posting_substitution_and_invoice_exclusion(self):
        for cash_date, expected in [("2025-12-31", 120), ("2026-01-01", 300), ("2026-03-31", 300), ("2026-04-01", 120)]:
            data = fixture()
            row = data["package"]["financial_facts"][0]
            row["dates"] = {"cash_received_date": cash_date, "posting_date": "2026-02-01"}
            row["temporal_basis"]["date"] = cash_date
            self.assertEqual(lionsgate(data)["cash_measure"], expected)
        data = fixture()
        invoice = deepcopy(data["package"]["financial_facts"][0])
        invoice.update(fact_id="invoice-context", event_kind="invoice", source_row="invoice-source")
        invoice["dates"] = {"invoice_date": "2026-02-01"}
        invoice["temporal_basis"] = {"kind": "invoice_date", "date": "2026-02-01"}
        data["package"]["financial_facts"].append(invoice)
        data["package"]["source_batches"][0]["row_count"] += 1
        self.assertEqual(lionsgate(data)["cash_measure"], 300)
        self.assertIn({"fact_id": "invoice-context", "disposition": "excluded", "reason": "invoice_is_not_cash"}, lionsgate(data)["dispositions"])

    def test_approved_cost_selector_exclusion_and_missing_incurred(self):
        data = fixture()
        row = cost(data, "50", incurred="2026-03-31", posting="2026-04-02")
        self.assertEqual(lionsgate(data)["actual_cost_measure"], 50)
        row["dates"]["incurred_date"] = "2026-04-01"
        row["temporal_basis"]["date"] = "2026-04-01"
        self.assertEqual(lionsgate(data)["actual_cost_measure"], 0)
        row["dates"].pop("incurred_date")
        self.reject(data, "LG_ORACLE_INCURRED_DATE_REQUIRED")
        data = fixture()
        cost(data, "50", eligible=False)
        self.assertEqual(lionsgate(data)["actual_cost_measure"], 0)
        data["package"]["parameters"]["cost_decisions"][0]["eligible"] = True
        self.reject(data, "LG_ORACLE_COST_AUTHORITY")

    def test_opening_and_closing_work_gate_fail_without_crossing_policy(self):
        data = fixture()
        data["package"]["state_cells"][0]["quantity"] = "99"
        self.reject(data, "LG_CROSSING_POLICY_REQUIRED")
        data = fixture()
        cost(data, "301")
        self.reject(data, "LG_RECROSSING_POLICY_REQUIRED")

    def test_synthetic_holdback_is_after_earnings_not_a_basis_reserve(self):
        data = fixture()
        data["package"]["state_cells"][2]["quantity"] = "10"
        data["package"]["parameters"]["payment_holdback_addition"]["value"] = "20"
        data["package"]["parameters"]["payment_holdback_release"]["value"] = "5"
        result = lionsgate(data)
        self.assertEqual((result["cash_measure"], result["payout_base"], result["earned"], result["payable"], result["closing_payment_holdback"]),
                         (300, 210, 35, 20, 25))
        data["package"]["parameters"]["payment_holdback_release"]["value"] = "11"
        self.reject(data, "SYNTHETIC_HOLDBACK_RELEASE_EXCEEDS_OPENING")
        data["package"]["parameters"]["payment_holdback_release"]["value"] = "5"
        data["package"]["parameters"]["payment_holdback_addition"]["value"] = "41"
        self.reject(data, "SYNTHETIC_HOLDBACK_ADDITION_EXCEEDS_AVAILABLE")

    def test_gross_offset_zero_floor_and_exact_fraction_no_rounding(self):
        data = fixture()
        data["package"]["parameters"]["producer_fee_offset"]["value"] = "50"
        self.assertEqual((lionsgate(data)["gross_candidate"], lionsgate(data)["net_candidate"]), (0, 35))
        data = fixture()
        data["package"]["parameters"]["policy"]["net_rate"] = {"numerator": "1", "denominator": "3"}
        self.assertEqual(lionsgate(data)["net_candidate"], Fraction(175, 3))
        data["package"]["parameters"]["policy"]["net_rate"] = 0.2
        self.reject(data, "LG_ORACLE_EXACT_NUMBER")

    def test_independent_allocation_authority_and_parent_consumed_once(self):
        data = allocated(fixture())
        result = lionsgate(data)
        self.assertEqual((result["cash_measure"], result["payout_base"], result["payable"]), (300, 210, 35))
        self.assertEqual(len([row for row in result["contributions"] if row["fact_id"] == "lg-other"]), 1)
        self.assertEqual(next(row for row in result["contributions"] if row["fact_id"] == "lg-other")["allocation_id"], "lg-allocation-1")
        data["package"]["allocations"][0]["weight"] = "0.5"
        self.reject(data, "LG_ORACLE_ALLOCATION_AUTHORITY")
        data = allocated(fixture())
        data["package"]["allocations"][0]["target_scope"]["asset_ids"] = ["outside"]
        self.reject(data, "LG_ORACLE_ALLOCATION_SCOPE")
        data = allocated(fixture())
        data["allocation_authorities"][0]["policy_ref"] = "lg-cleared@1"
        data["package"]["allocations"][0]["policy_ref"] = "lg-cleared@1"
        self.reject(data, "LG_ORACLE_POLICY_REQUIRED")

    def test_parent_child_cash_duplicates_cycles_and_batch_controls(self):
        data = fixture()
        child = deepcopy(data["package"]["financial_facts"][0])
        child.update(fact_id="duplicate-child", parent_fact_id="lg-other", source_row="duplicate-child")
        data["package"]["financial_facts"].append(child)
        data["package"]["source_batches"][0]["row_count"] += 1
        self.reject(data, "LG_ORACLE_PARENT_CHILD_CASH")
        data = fixture()
        data["package"]["financial_facts"][0]["parent_fact_id"] = "lg-other"
        self.reject(data, "LG_ORACLE_PARENT_GRAPH")
        data = fixture()
        data["package"]["source_batches"][0]["control_totals"] = [{"amount_kind": "cash_receipt", "currency": "USD", "signed_total": "300", "absolute_total": "300"}]
        self.assertEqual(lionsgate(data)["cash_measure"], 300)
        data["package"]["source_batches"][0]["control_totals"][0]["signed_total"] = "301"
        self.reject(data, "LG_ORACLE_BATCH_CONTROL")

    def test_scope_policy_worksheet_state_duplicates_and_missing_dates(self):
        mutations = [
            lambda d: d["package"]["parameters"]["policy"].update(asset_id="unknown"),
            lambda d: event(d, "crossed_net_worksheet").update(member_ids=["outside"]),
            lambda d: event(d, "crossed_net_worksheet").update(pool_id="outside"),
            lambda d: d["package"]["state_cells"][0].update(boundary="2025-12-31"),
            lambda d: d["package"]["state_cells"][0].update(scenario_id="other"),
            lambda d: decision(d, "LG-GREATER-OF")["scope"].update(pool_id="other"),
            lambda d: d["package"]["financial_facts"][0]["amount"].update(currency="EUR"),
            lambda d: d["package"]["financial_facts"][0]["dates"].pop("cash_received_date"),
            lambda d: d["package"]["financial_facts"][0].pop("channel"),
            lambda d: d["package"]["financial_facts"].append(deepcopy(d["package"]["financial_facts"][0])),
            lambda d: d["package"]["evidence_events"].append(deepcopy(d["package"]["evidence_events"][0])),
        ]
        for index, mutate in enumerate(mutations):
            data = fixture()
            mutate(data)
            with self.subTest(index=index):
                self.reject(data)

    def test_original_input_permutation_and_no_mutation(self):
        data = fixture()
        original = deepcopy(data)
        result = lionsgate(data)
        self.assertEqual(data, original)
        for key in ["financial_facts", "evidence_events", "state_cells", "opening_aliases"]:
            data["package"][key].reverse()
        self.assertEqual(lionsgate(data), result)
        self.assertEqual(json.loads(json.dumps(exact_json(result)))["payable"], "35")

    def test_oracle_imports_only_standard_library_and_reads_no_files(self):
        tree = ast.parse((ROOT / "oracles/lionsgate.py").read_text(encoding="utf-8"))
        imports = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertLessEqual(imports, {"collections", "copy", "datetime", "fractions", "re"})
        self.assertFalse(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                             and node.func.id in {"open", "eval", "exec", "compile"} for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
