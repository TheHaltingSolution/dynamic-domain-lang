"""Original-fact hand controls for named fee/cost stages and cumulative caps."""
import ast
from copy import deepcopy
from fractions import Fraction
import itertools
import json
from pathlib import Path
import unittest

from oracles.staged_deductions import DeductionOracleError, exact_json, staged_deductions


ROOT = Path(__file__).resolve().parents[1]


def fixture(variant="pre_share_net_fee", fee_rate="0", cap="1000", costs=None):
    data = json.loads((ROOT / "cases/deductions/neutral.json").read_text(encoding="utf-8"))
    data["terms"].update(variant=variant, fee_rate=fee_rate, cap=cap)
    data["opening_state"].update(variant=variant, cap_limit=cap)
    if costs is not None:
        prototype = data["costs"][0]
        data["costs"] = [{**deepcopy(prototype), "id": f"cost-{index}", "amount": amount,
                          "sequence": index, "source_ref": f"synthetic-cost-{index}"}
                         for index, amount in enumerate(costs)]
    return data


def successor(previous, costs=("30",), quarter=2):
    state = previous["closing_state"]
    data = fixture(variant=previous["variant"], cap=str(state["cap_limit"]), costs=costs)
    month, end_month = ("06", "07") if quarter == 2 else ("09", "10")
    data["case_id"] = f"deduction-q{quarter}"
    data["period"] = {"start": state["boundary"], "end": f"2026-{end_month}-01"}
    data["cutoff"] = f"2026-{end_month}-03T00:00:00Z"
    data["opening_state"] = exact_json(state)
    data["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": state})
    for kind in ("receipts", "costs"):
        for row in data[kind]:
            row.update(id=f"{row['id']}-q{quarter}", effective_date=f"2026-{month}-15",
                       observed_at=f"2026-{end_month}-01T00:00:00Z", evidence_ref=f"source-q{quarter}",
                       source_ref=f"{row['source_ref']}-q{quarter}")
    data["evidence"].append({**deepcopy(data["evidence"][0]), "id": f"source-q{quarter}",
                              "observed_at": f"2026-{end_month}-02T00:00:00Z"})
    return data


class DeductionOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(DeductionOracleError) as raised:
            staged_deductions(data)
        self.assertEqual(str(raised.exception), code)

    def test_c03_before_and_after_share_hand_control(self):
        before = staged_deductions(fixture())
        after = staged_deductions(fixture(variant="post_share_net_fee"))
        self.assertEqual((before["earned"], after["earned"]), (400, 300))
        self.assertEqual([before[key] for key in ("gross_receipts", "net_receipts", "eligible_costs", "excluded_costs",
                                                  "admitted_deduction", "participation_basis", "fee", "closing_cap_consumed")],
                         [1000, 1000, 500, 200, 500, 500, 0, 500])

    def test_six_named_variants_fee_stage_intermediates(self):
        controls = {
            "pre_basis_gross_fee": (500, 1000, 100, 400, 320),
            "pre_basis_net_fee": (500, 500, 50, 450, 360),
            "pre_share_gross_fee": (1000, 1000, 100, 400, 320),
            "pre_share_net_fee": (1000, 1000, 100, 400, 320),
            "post_share_gross_fee": (1000, 1000, 100, 900, 220),
            "post_share_net_fee": (1000, 1000, 100, 900, 220),
        }
        for variant, expected in controls.items():
            with self.subTest(variant=variant):
                result = staged_deductions(fixture(variant=variant, fee_rate="0.1"))
                self.assertEqual(tuple(result[key] for key in ("stage_net", "fee_base", "fee", "participation_basis", "earned")), expected)

    def test_gross_and_net_fee_views_are_not_additive_receipts(self):
        for variant, expected in (("pre_share_gross_fee", "44.5"), ("pre_share_net_fee", "45")):
            data = fixture(variant=variant, fee_rate="0.1", costs=())
            data["terms"]["share"] = "0.5"
            data["receipts"][0].update(gross_amount="110", net_amount="100")
            result = staged_deductions(data)
            self.assertEqual(result["earned"], Fraction(expected))
            self.assertEqual((result["gross_receipts"], result["net_receipts"]), (110, 100))
        for variant, expected in (("pre_share_gross_fee", "44.5"), ("post_share_gross_fee", "39")):
            data = fixture(variant=variant, costs=("11",))
            data["terms"]["share"] = "0.5"
            data["receipts"][0].update(gross_amount="110", net_amount="100")
            self.assertEqual(staged_deductions(data)["earned"], Fraction(expected))

    def test_explicit_eligibility_subsets_keep_all_original_costs(self):
        for categories, eligible, excluded, earned in ((["distribution"], 500, 200, 400),
                                                       (["unselected_publicity"], 200, 500, 640), ([], 0, 700, 800)):
            data = fixture(); data["terms"]["eligible_categories"] = categories
            result = staged_deductions(data)
            self.assertEqual((result["eligible_costs"], result["excluded_costs"], result["earned"]), (eligible, excluded, earned))
            self.assertEqual(len(result["cost_lines"]), 2)
            self.assertEqual(len(result["closing_state"]["cost_history"]), 2)
        original = fixture()["costs"][1]
        retained = staged_deductions(fixture())["cost_lines"][1]
        self.assertEqual((retained["id"], retained["amount"], retained["source_ref"], retained["deducted"], retained["disposition"]),
                         (original["id"], 200, original["source_ref"], 0, "excluded_category"))

    def test_scarce_cap_uses_authorized_sequence_not_physical_order(self):
        data = fixture(cap="100", costs=("80", "80"))
        result = staged_deductions(data)
        self.assertEqual([(row["id"], row["deducted"]) for row in result["cost_lines"]], [("cost-0", 80), ("cost-1", 20)])
        self.assertEqual((result["eligible_unadmitted"], result["closing_cap_consumed"], result["earned"]), (60, 100, 720))
        data["costs"].reverse()
        self.assertEqual(staged_deductions(data), result)
        data["costs"][0]["sequence"], data["costs"][1]["sequence"] = 0, 1
        changed = staged_deductions(data)
        self.assertEqual([(row["id"], row["deducted"]) for row in changed["cost_lines"]], [("cost-1", 80), ("cost-0", 20)])

    def test_adjacent_cumulative_cap_carry_equality_and_exhaustion(self):
        first = staged_deductions(fixture(cap="100", costs=("80",)))
        second_data = successor(first)
        second = staged_deductions(second_data)
        self.assertEqual((second["opening_cap_consumed"], second["eligible_costs"], second["admitted_deduction"], second["closing_cap_consumed"]), (80, 30, 20, 100))
        self.assertEqual((second["cost_lines"][0]["amount"], second["cost_lines"][0]["deducted"], second["cost_lines"][0]["disposition"]), (30, 20, "eligible_capped"))
        third_data = successor(second, costs=("5",), quarter=3)
        # Q3 keeps Q2 source evidence as well as the original Q1 source.
        third_data["evidence"].append(deepcopy(second_data["evidence"][-1]))
        third = staged_deductions(third_data)
        self.assertEqual((third["admitted_deduction"], third["closing_cap_consumed"], third["earned"]), (0, 100, 800))
        self.assertEqual(sum(row["deducted"] for row in third["closing_state"]["cost_history"]), 100)
        equal = staged_deductions(fixture(cap="100", costs=("100",)))
        self.assertEqual((equal["admitted_deduction"], equal["eligible_unadmitted"]), (100, 0))

    def test_prior_consumption_and_no_residual_or_reclassification(self):
        first = staged_deductions(fixture(cap="100", costs=("80",)))
        data = successor(first)
        data["costs"][0]["id"] = "cost-0"
        self.reject(data, "DEDUCTION_COST_ALREADY_RECOGNIZED")
        excluded = staged_deductions(fixture())
        data = successor(excluded)
        data["costs"][0]["id"] = "excluded-q1"
        self.reject(data, "DEDUCTION_COST_ALREADY_RECOGNIZED")
        for variant in ("pre_basis_gross_fee", "pre_basis_net_fee", "pre_share_gross_fee", "post_share_net_fee", "post_share_gross_fee"):
            data = successor(first); data["terms"]["variant"] = variant
            self.reject(data, "DEDUCTION_OPENING_METHOD")

    def test_no_cap_reset_or_purpose_scope_switch(self):
        first = staged_deductions(fixture(cap="100", costs=("80",)))
        changes = [("DEDUCTION_CAP_STATE", lambda d: d["terms"].update(cap="200")),
                   ("DEDUCTION_PREDECESSOR_MISMATCH", lambda d: d["opening_state"].update(cap_consumed="0")),
                   ("DEDUCTION_OPENING_SCOPE", lambda d: d["opening_state"].update(purpose="participation_advance")),
                   ("DEDUCTION_OPENING_SCOPE", lambda d: d["opening_state"]["scope"].update(pool_id="other")),
                   ("DEDUCTION_OPENING_METHOD", lambda d: d["opening_state"].update(policy_revision="2"))]
        for code, change in changes:
            data = successor(first); change(data)
            with self.subTest(code=code):
                self.reject(data, code)

    def test_duplicate_ids_sequences_and_history_reconciliation(self):
        for field in ("receipts", "costs", "evidence"):
            data = fixture(); data[field].append(deepcopy(data[field][0]))
            self.reject(data, "DEDUCTION_DUPLICATE_ID")
        data = fixture(); data["costs"][1]["sequence"] = data["costs"][0]["sequence"]
        self.reject(data, "DEDUCTION_SEQUENCE_TIE")
        for value in (-1, "1", True):
            data = fixture(); data["costs"][0]["sequence"] = value
            self.reject(data, "DEDUCTION_COST_SEQUENCE")
        first = staged_deductions(fixture())
        data = successor(first)
        # A self-consistent supplied predecessor cannot hide duplicate or
        # nonconserved history: the oracle independently rechecks the history.
        data["opening_state"]["cost_history"].append(deepcopy(data["opening_state"]["cost_history"][0]))
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        self.reject(data, "DEDUCTION_DUPLICATE_ID")
        data = successor(first)
        data["opening_state"]["cap_consumed"] = "499"
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        self.reject(data, "DEDUCTION_CAP_HISTORY_RECONCILIATION")

    def test_wrong_scope_not_hidden_by_cost_exclusion(self):
        for field in ("receipts", "costs", "evidence"):
            data = fixture(); data[field][-1]["scope"]["asset_id"] = "outside"
            self.reject(data, "DEDUCTION_EVIDENCE_SCOPE" if field == "evidence" else "DEDUCTION_FACT_SCOPE")
        data = fixture(); data["scope"]["currency"] = "EUR"
        self.reject(data, "DEDUCTION_CURRENCY")

    def test_empty_zero_and_exact_fractional_source_precision(self):
        data = fixture(costs=()); data["receipts"] = []; data["evidence"] = []
        result = staged_deductions(data)
        self.assertEqual((result["earned"], result["admitted_deduction"], result["fee"], result["closing_cap_consumed"]), (0, 0, 0, 0))
        data = fixture(costs=("0",), cap="0"); data["receipts"][0].update(gross_amount="0", net_amount="0")
        self.assertEqual(staged_deductions(data)["earned"], 0)
        data = fixture(costs=("1/7",)); data["terms"].update(share="1/3", fee_rate="1/11")
        data["receipts"][0].update(gross_amount="1", net_amount="1")
        result = staged_deductions(data)
        self.assertEqual(result["fee"], Fraction(1, 11))
        self.assertEqual(result["earned"], Fraction(59, 231))
        self.assertEqual(exact_json(result)["earned"], "59/231")

    def test_negative_stages_and_losses_are_rejected_without_floor(self):
        data = fixture(variant="pre_basis_net_fee", costs=("1100",), cap="2000")
        self.reject(data, "DEDUCTION_NEGATIVE_STAGE")
        data = fixture(variant="pre_share_net_fee", costs=("1000",), fee_rate="0.1")
        self.reject(data, "DEDUCTION_NEGATIVE_STAGE")
        data = fixture(variant="post_share_net_fee", costs=("900",))
        self.reject(data, "DEDUCTION_NEGATIVE_EARNINGS")
        data = fixture(variant="pre_share_gross_fee", costs=(), fee_rate="1")
        data["receipts"][0].update(gross_amount="110", net_amount="100")
        data["terms"]["share"] = "0"
        self.reject(data, "DEDUCTION_NEGATIVE_STAGE")

    def test_exact_domains_explicit_variant_and_policy(self):
        for field in ("share", "fee_rate"):
            for value in ("-0.1", "1.1"):
                data = fixture(); data["terms"][field] = value
                self.reject(data, "DEDUCTION_RATE_DOMAIN")
        for value in (0.8, True, "8e-1"):
            data = fixture(); data["terms"]["share"] = value
            self.reject(data, "DEDUCTION_EXACT_VALUE_REQUIRED")
        data = fixture(); data["costs"][0]["amount"] = "-1"
        self.reject(data, "DEDUCTION_NEGATIVE_MONEY")
        data = fixture(); data["terms"]["variant"] = "default"
        self.reject(data, "DEDUCTION_VARIANT_REQUIRED")
        data = fixture(); data["terms"]["rounding"] = "half_even"
        self.reject(data, "DEDUCTION_POLICY")
        data = fixture(); data["terms"]["eligible_categories"].append("distribution")
        self.reject(data, "DEDUCTION_CATEGORY_LIST")
        data = fixture(); data["receipts"][0]["net_amount"] = "1001"
        self.reject(data, "DEDUCTION_RECEIPT_VIEWS")

    def test_effective_period_evidence_and_exact_cutoff(self):
        for field in ("receipts", "costs"):
            for day in ("2025-12-31", "2026-04-01"):
                data = fixture(); data[field][0]["effective_date"] = day
                self.reject(data, "DEDUCTION_FACT_PERIOD")
            data = fixture(); data[field][0]["observed_at"] = data["cutoff"]
            self.reject(data, "DEDUCTION_FACT_CUTOFF")
        data = fixture(); data["evidence"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "DEDUCTION_EVIDENCE_CUTOFF")
        data = fixture(); data["costs"][0]["evidence_ref"] = "missing"
        self.reject(data, "DEDUCTION_FACT_EVIDENCE")
        data = fixture(); data["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        data["costs"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
        self.assertEqual(staged_deductions(data)["earned"], 400)

    def test_predecessor_state_is_serialized_and_adjacent(self):
        original = successor(staged_deductions(fixture()))
        self.assertEqual(json.loads(json.dumps(original)), original)
        changes = [("DEDUCTION_PREDECESSOR_REQUIRED", lambda d: d.pop("prior_result")),
                   ("DEDUCTION_OPENING_BOUNDARY", lambda d: d["opening_state"].update(boundary="2026-04-02")),
                   ("DEDUCTION_PREDECESSOR_BOUNDARY", lambda d: d["prior_result"]["period"].update(end="2026-03-31")),
                   ("DEDUCTION_PREDECESSOR_MISMATCH", lambda d: d["prior_result"].update(source_case_id="other")),
                   ("DEDUCTION_PREDECESSOR_MISMATCH", lambda d: d.update(case_id="deduction-q1")),
                   ("DEDUCTION_PREDECESSOR_MISMATCH", lambda d: d["opening_state"]["cost_history"][0].update(source_ref="changed"))]
        for code, change in changes:
            data = deepcopy(original); change(data); self.reject(data, code)

    def test_small_finite_split_and_permutation_controls(self):
        for first, second in itertools.product(range(4), repeat=2):
            data = fixture(costs=(str(first), str(second)))
            split = staged_deductions(data)
            whole = staged_deductions(fixture(costs=(str(first + second),)))
            self.assertEqual(split["earned"], Fraction(4, 5) * (1000 - first - second))
            self.assertEqual(split["earned"], whole["earned"])
            data["receipts"].reverse(); data["costs"].reverse(); data["evidence"].reverse()
            self.assertEqual(staged_deductions(data), split)

    def test_oracle_dependencies_are_standard_library_only(self):
        tree = ast.parse((ROOT / "oracles/staged_deductions.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
