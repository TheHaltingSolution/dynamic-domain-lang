"""Independent linked-return, original-rate and selected loss-method controls."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.returns_losses import ReturnsOracleError, exact_json, returns_losses


ROOT = Path(__file__).resolve().parents[1]


def fixture(method="signed_pool"):
    data = json.loads((ROOT / "cases/returns/neutral.json").read_text(encoding="utf-8"))
    data["policy"]["method"] = data["opening_state"]["method"] = method
    return data


def successor(previous, previous_input, quarter=2, sale_basis="30"):
    data = fixture(previous["method"])
    month, end_month, start = ("05", "07", "2026-04-01") if quarter == 2 else ("08", "10", "2026-07-01")
    data.update(case_id=f"returns-q{quarter}", period={"start": start, "end": f"2026-{end_month}-01"}, cutoff=f"2026-{end_month}-03T00:00:00Z")
    data["opening_state"] = exact_json(previous["closing_state"])
    data["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
    data["originals"], data["returns"] = [], []
    data["evidence"] = deepcopy(previous_input["evidence"])
    source_id = f"current-source-q{quarter}"
    data["evidence"].append({"id": source_id, "scope": deepcopy(data["scope"]), "observed_at": f"2026-{end_month}-01T00:00:00Z", "kind": "synthetic_current_facts"})
    for row in data["current_rates"]:
        row.update(effective=deepcopy(data["period"]), observed_at=f"2026-{end_month}-01T00:00:00Z", evidence_ref=source_id,
                   source_ref=f"synthetic-rate-{row['asset_id']}-q{quarter}")
    if sale_basis is None:
        data["sales"] = []
    else:
        data["sales"][0].update(id=f"sale-a-q{quarter}", basis=sale_basis, effective_date=f"2026-{month}-01",
                                 observed_at=f"2026-{end_month}-01T00:00:00Z", evidence_ref=source_id,
                                 source_ref=f"synthetic-current-sale-a-q{quarter}")
    return data


def add_old_return(data, magnitude="20", identity="return-b-q2"):
    row = deepcopy(fixture()["returns"][0])
    start = data["period"]["start"]
    row.update(id=identity, returned_basis=magnitude, return_date=start, recognition_date=start,
               observed_at=data["current_rates"][0]["observed_at"], evidence_ref=data["current_rates"][0]["evidence_ref"],
               source_ref=f"synthetic-{identity}")
    data["returns"].append(row)


class ReturnsOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(ReturnsOracleError) as raised:
            returns_losses(data)
        self.assertEqual(str(raised.exception), code)

    def test_baseline_original_rate_signed_and_title_floor(self):
        signed = returns_losses(fixture())
        floored = returns_losses(fixture("per_title_floor"))
        self.assertEqual((signed["current_earned"], signed["reversed_earned"], signed["pool_signed_earned"], signed["recognized_entitlement"]), (100, 40, 60, 60))
        self.assertEqual(floored["recognized_entitlement"], 100)
        self.assertEqual([row["signed_earned"] for row in signed["titles"]], [100, -40])
        self.assertEqual([row["floored_earned"] for row in floored["titles"]], [100, 0])
        reversal = signed["returns"][0]
        self.assertEqual((reversal["original_rate"], reversal["signed_effect"], reversal["original_measurement_date"]),
                         (Fraction(1, 2), -40, "2025-12-15"))
        self.assertEqual(signed["titles"][1]["current_rate"], Fraction(4, 5))
        self.assertNotIn("actual_paid", signed)
        self.assertNotIn("bank_refund", signed)
        self.assertNotIn("payable", signed)

    def test_current_rate_cannot_reprice_original_return(self):
        for rate in ("0", "0.1", "0.8", "1"):
            data = fixture(); data["current_rates"][1]["rate"] = rate
            result = returns_losses(data)
            self.assertEqual((result["returns"][0]["original_rate"], result["reversed_earned"], result["recognized_entitlement"]),
                             (Fraction(1, 2), 40, 60))

    def test_historical_registry_is_not_reearned_and_current_sales_register(self):
        data = fixture(); data["sales"], data["returns"] = [], []
        result = returns_losses(data)
        self.assertEqual((result["current_earned"], result["pool_signed_earned"], result["recognized_entitlement"]), (0, 0, 0))
        self.assertEqual(result["closing_state"]["original_registry"][0]["id"], "old-b")
        baseline = returns_losses(fixture())
        original = next(row for row in baseline["closing_state"]["original_registry"] if row["id"] == "sale-a-q1")
        self.assertEqual((original["basis"], original["rate"], original["returned_basis"], original["origin_kind"]), (100, 1, 0, "current_sale"))
        self.assertEqual(original["registered_case_id"], "returns-q1")

    def test_pooled_loss_carry_negative40_then_positive30_then20(self):
        first_data = fixture("pooled_loss_carry"); first_data["sales"] = []
        first = returns_losses(first_data)
        self.assertEqual((first["pool_signed_earned"], first["recognized_entitlement"], first["new_loss"], first["closing_loss"]), (-40, 0, 40, 40))
        second_data = successor(first, first_data)
        second = returns_losses(second_data)
        self.assertEqual((second["opening_loss"], second["pool_signed_earned"], second["loss_applied"], second["recognized_entitlement"], second["closing_loss"]), (40, 30, 30, 0, 10))
        third_data = successor(second, second_data, quarter=3, sale_basis="20")
        third = returns_losses(third_data)
        self.assertEqual((third["opening_loss"], third["loss_applied"], third["recognized_entitlement"], third["closing_loss"]), (10, 10, 10, 0))
        for result in (first, second, third):
            self.assertEqual(result["pool_signed_earned"] + result["closing_loss"], result["recognized_entitlement"] + result["opening_loss"])

    def test_partial_return_meter_across_periods_and_equality_limit(self):
        first_data = fixture(); first_data["sales"] = []; first_data["returns"][0]["returned_basis"] = "30"
        first = returns_losses(first_data)
        self.assertEqual((first["recognized_entitlement"], first["originals"][0]["remaining_basis"]), (-15, 50))
        second_data = successor(first, first_data, sale_basis=None)
        add_old_return(second_data, magnitude="50")
        second = returns_losses(second_data)
        old = next(row for row in second["originals"] if row["original_id"] == "old-b")
        self.assertEqual((old["opening_returned_basis"], old["current_returned_basis"], old["closing_returned_basis"], old["remaining_basis"]), (30, 50, 80, 0))
        self.assertEqual(second["recognized_entitlement"], -25)
        third_data = successor(second, second_data, quarter=3, sale_basis=None)
        add_old_return(third_data, magnitude="0.01", identity="return-b-q3")
        self.reject(third_data, "RETURNS_ORIGINAL_OVERRETURN")

    def test_multiple_partial_returns_sum_before_original_limit(self):
        data = fixture(); data["returns"][0]["returned_basis"] = "30"
        second = deepcopy(data["returns"][0]); second.update(id="partial-b-2", returned_basis="50", source_ref="synthetic-partial-b-2")
        data["returns"].append(second)
        result = returns_losses(data)
        self.assertEqual((result["reversed_earned"], result["originals"][0]["closing_returned_basis"]), (40, 80))
        data["returns"][1]["returned_basis"] = "50.01"
        self.reject(data, "RETURNS_ORIGINAL_OVERRETURN")

    def test_same_period_returns_to_new_sale_count_sale_once(self):
        data = fixture()
        current_return = deepcopy(data["returns"][0])
        current_return.update(id="current-return-a", original_id="sale-a-q1", asset_id="picture-a", returned_basis="25", source_ref="synthetic-current-return-a")
        data["returns"].append(current_return)
        result = returns_losses(data)
        self.assertEqual((result["current_earned"], result["reversed_earned"], result["recognized_entitlement"]), (100, 65, 35))
        current = next(row for row in result["originals"] if row["original_id"] == "sale-a-q1")
        self.assertEqual((current["current_returned_basis"], current["remaining_basis"]), (25, 75))
        current_return["observed_at"] = "2026-02-28T23:59:59Z"
        self.reject(data, "RETURNS_OBSERVATION_ORDER")

    def test_original_registration_duplicates_and_replayed_returns_block(self):
        for field in ("originals", "sales", "returns", "evidence"):
            data = fixture(); data[field].append(deepcopy(data[field][0]))
            self.reject(data, "RETURNS_DUPLICATE_ID")
        data = fixture(); data["sales"][0]["id"] = "old-b"
        self.reject(data, "RETURNS_ORIGINAL_ALREADY_REGISTERED")
        first_data = fixture(); first = returns_losses(first_data)
        data = successor(first, first_data, sale_basis=None)
        add_old_return(data, magnitude="0", identity="return-b-q1")
        self.reject(data, "RETURNS_ALREADY_RECOGNIZED")
        data = successor(first, first_data, sale_basis=None)
        data["originals"] = deepcopy(first_data["originals"])
        self.reject(data, "RETURNS_ORIGINAL_ALREADY_REGISTERED")

    def test_zero_magnitudes_empty_activity_and_zero_original_rate(self):
        data = fixture(); data["sales"], data["returns"] = [], []
        self.assertEqual(returns_losses(data)["recognized_entitlement"], 0)
        data = fixture(); data["returns"][0]["returned_basis"] = "0"
        self.assertEqual(returns_losses(data)["recognized_entitlement"], 100)
        data = fixture(); data["originals"][0]["rate"] = "0"
        result = returns_losses(data)
        self.assertEqual((result["reversed_earned"], result["originals"][0]["closing_returned_basis"]), (0, 80))
        self.assertEqual(result["recognized_entitlement"], 100)

    def test_return_scope_original_identity_and_date_recognition(self):
        changes = [("RETURNS_ORIGINAL_REQUIRED", lambda d: d["returns"][0].update(original_id="missing")),
                   ("RETURNS_ORIGINAL_SCOPE", lambda d: d["returns"][0].update(asset_id="picture-a")),
                   ("RETURNS_FACT_SCOPE", lambda d: d["returns"][0]["scope"].update(pool_id="outside")),
                   ("RETURNS_DATE_ORDER", lambda d: d["returns"][0].update(return_date="2025-12-14")),
                   ("RETURNS_DATE_ORDER", lambda d: d["returns"][0].update(return_date="2026-02-16")),
                   ("RETURNS_RECOGNITION_PERIOD", lambda d: d["returns"][0].update(recognition_date="2026-04-01")),
                   ("RETURNS_HISTORICAL_ORIGINAL_DATE", lambda d: d["originals"][0].update(measurement_date="2026-01-01"))]
        for code, change in changes:
            data = fixture(); change(data)
            self.reject(data, code)
        data = fixture(); data["returns"][0].update(return_date="2025-12-31", recognition_date="2026-01-01")
        self.assertEqual(returns_losses(data)["recognized_entitlement"], 60)

    def test_nonnegative_original_raw_magnitudes_exact_rates_and_no_rounding(self):
        for field, amount_field in (("originals", "basis"), ("sales", "basis"), ("returns", "returned_basis")):
            data = fixture(); data[field][0][amount_field] = "-1"
            self.reject(data, "RETURNS_EXACT_NONNEGATIVE_VALUE")
        for value in (0.5, True, "1e-1"):
            data = fixture(); data["originals"][0]["rate"] = value
            self.reject(data, "RETURNS_EXACT_NONNEGATIVE_VALUE")
        data = fixture(); data["originals"][0]["rate"] = "1.1"
        self.reject(data, "RETURNS_RATE_DOMAIN")
        data = fixture(); data["originals"][0]["rate"] = "1/3"; data["returns"][0]["returned_basis"] = "1/7"
        result = returns_losses(data)
        self.assertEqual(result["returns"][0]["signed_effect"], Fraction(-1, 21))
        self.assertEqual(result["recognized_entitlement"], Fraction(2099, 21))

    def test_opening_scope_policy_method_loss_and_predecessor(self):
        first_data = fixture("pooled_loss_carry"); first_data["sales"] = []
        first = returns_losses(first_data)
        original = successor(first, first_data)
        changes = [("RETURNS_OPENING_SCOPE", lambda d: d["opening_state"].update(purpose="prepayment")),
                   ("RETURNS_OPENING_SCOPE", lambda d: d["opening_state"].update(asset_ids=["picture-a"])),
                   ("RETURNS_OPENING_METHOD", lambda d: d["policy"].update(method="signed_pool")),
                   ("RETURNS_OPENING_BOUNDARY", lambda d: d["opening_state"].update(boundary="2026-04-02")),
                   ("RETURNS_PREDECESSOR_REQUIRED", lambda d: d.pop("prior_result")),
                   ("RETURNS_PREDECESSOR_BOUNDARY", lambda d: d["prior_result"]["period"].update(end="2026-03-31")),
                   ("RETURNS_PREDECESSOR_MISMATCH", lambda d: d["opening_state"].update(loss_carry="0")),
                   ("RETURNS_PREDECESSOR_MISMATCH", lambda d: d["opening_state"]["original_registry"][0].update(rate="0.8")),
                   ("RETURNS_PREDECESSOR_MISMATCH", lambda d: d["prior_result"].update(source_case_id="other"))]
        for code, change in changes:
            data = deepcopy(original); change(data); self.reject(data, code)
        data = fixture(); data["opening_state"]["loss_carry"] = "1"
        self.reject(data, "RETURNS_LOSS_OUTSIDE_METHOD")

    def test_carried_registry_independently_checks_meter_and_provenance(self):
        first_data = fixture(); first = returns_losses(first_data)
        for change, code in ((lambda row: row.update(returned_basis="81"), "RETURNS_ORIGINAL_METER"),
                              (lambda row: row.update(origin_kind="unknown"), "RETURNS_ORIGINAL_PROVENANCE"),
                              (lambda row: row.update(measurement_date="2026-04-01"), "RETURNS_CARRIED_ORIGINAL_DATE")):
            data = successor(first, first_data)
            change(data["opening_state"]["original_registry"][0])
            data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
            self.reject(data, code)

    def test_current_rates_universe_and_half_open_sale_period(self):
        data = fixture(); data["current_rates"].pop()
        self.reject(data, "RETURNS_CURRENT_RATE_COVERAGE")
        data = fixture(); data["current_rates"][0]["effective"]["start"] = "2026-01-02"
        self.reject(data, "RETURNS_CURRENT_RATE_PERIOD")
        data = fixture(); data["asset_ids"].append("picture-a")
        self.reject(data, "RETURNS_ASSET_UNIVERSE")
        for effective in ("2025-12-31", "2026-04-01"):
            data = fixture(); data["sales"][0]["effective_date"] = effective
            self.reject(data, "RETURNS_SALE_PERIOD")

    def test_exact_cutoff_evidence_scope_and_missing_original_support(self):
        data = fixture(); data["returns"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "RETURNS_FACT_CUTOFF")
        data = fixture(); data["evidence"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "RETURNS_EVIDENCE_CUTOFF")
        data = fixture(); data["originals"][0]["evidence_ref"] = "missing"
        self.reject(data, "RETURNS_FACT_EVIDENCE")
        data = fixture(); data["evidence"][0]["scope"]["contract_id"] = "outside"
        self.reject(data, "RETURNS_EVIDENCE_SCOPE")
        data = fixture(); data["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        data["returns"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
        self.assertEqual(returns_losses(data)["recognized_entitlement"], 60)

    def test_permutation_replay_immutability_and_distinct_category_ids(self):
        data = fixture(); original = deepcopy(data)
        expected = returns_losses(data)
        self.assertEqual(data, original)
        for field in ("asset_ids", "current_rates", "originals", "sales", "returns", "evidence"):
            data[field].reverse()
        self.assertEqual(returns_losses(data), expected)
        self.assertEqual(returns_losses(deepcopy(original)), expected)
        data = fixture(); data["returns"][0]["id"] = "sale-a-q1"
        history = returns_losses(data)["closing_state"]["recognized_ids"]
        self.assertIn("sales:sale-a-q1", history)
        self.assertIn("returns:sale-a-q1", history)
        self.assertEqual(json.loads(json.dumps(exact_json(expected)))["recognized_entitlement"], "60")

    def test_oracle_only_imports_standard_library(self):
        tree = ast.parse((ROOT / "oracles/returns_losses.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
