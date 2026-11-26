"""Independent financial controls: neutral data in, exact intermediates out."""
import ast
from copy import deepcopy
from fractions import Fraction
import itertools
import json
from pathlib import Path
import sys
import unittest

from oracles.r1 import (OracleError, angel_guild, exact_json, mqp_correction,
                        mqp_ordered_fees, supplied_due_reserve)


ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "cases" / "r1" / (name + ".json")).read_text(encoding="utf-8"))


class R1OracleTests(unittest.TestCase):
    def test_oracle_imports_only_standard_library_and_oracle_siblings(self):
        allowed = sys.stdlib_module_names
        for path in (ROOT / "oracles").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split(".")[0], allowed,
                                      f"{path.name}:{node.lineno}: {alias.name}")
                if isinstance(node, ast.ImportFrom):
                    if node.level:
                        self.assertEqual(node.level, 1)
                        self.assertTrue(node.module and "." not in node.module)
                        self.assertTrue((ROOT / "oracles" / (node.module + ".py")).is_file())
                    else:
                        self.assertIn(node.module.split(".")[0], allowed,
                                      f"{path.name}:{node.lineno}: {node.module}")

    def assert_rejects(self, code, calculate, data):
        with self.assertRaisesRegex(OracleError, "^" + code + "$"):
            calculate(data)

    def test_angel_rr03_intermediates_and_platform_denominator(self):
        data = fixture("angel-guild")
        result = angel_guild(data)
        self.assertEqual({k: exact_json(result[k]) for k in data["expected"]}, data["expected"])
        self.assertEqual(result["title_allocations"], {"king-of-kings": Fraction(85), "other-titles": Fraction(415)})
        self.assertEqual(result["excluded_cash"], [{"id": "ordinary-cash", "reason": "ordinary_distribution"}])
        more = deepcopy(data["usage"][1])
        more.update(id="added-other-minutes", minutes="1000")
        data["usage"].append(more)
        result = angel_guild(data)
        self.assertEqual(result["qualified_minutes"], 2000)
        self.assertEqual(result["focal_title_amount"], Fraction(85, 2))
        self.assertEqual(result["other_titles_amount"], Fraction(915, 2))
        self.assertEqual(result["allocation_residual"], 0)

    def test_angel_usage_grouping_and_exact_conservation_exhaustively(self):
        # Distinct title records, repeated title rows, and zero-weight titles.
        for a, b in itertools.product(range(4), repeat=2):
            if a + b == 0:
                continue
            data = fixture("angel-guild")
            data["usage"][0]["minutes"] = str(a)
            data["usage"][1]["minutes"] = str(b)
            duplicate_title = deepcopy(data["usage"][0])
            duplicate_title.update(id="second-focal-row", minutes="1/3")
            data["usage"].append(duplicate_title)
            result = angel_guild(data)
            self.assertEqual(result["focal_title_amount"], 500 * (Fraction(a) + Fraction(1, 3)) / (a + b + Fraction(1, 3)))
            self.assertEqual(sum(result["title_allocations"].values()), result["filmmaker_pool"])
            self.assertEqual(result["angel_share"] + result["filmmaker_pool"], result["net_guild"])

    def test_angel_period_edges_and_wrong_cash_scope(self):
        data = fixture("angel-guild")
        data["cash_records"][0]["date"] = data["period"]["start"]
        self.assertEqual(angel_guild(data)["gross_guild"], 1500)
        data["cash_records"][0]["date"] = data["period"]["end"]
        data["costs"] = []
        self.assertEqual(angel_guild(data)["gross_guild"], 0)
        data["cash_records"][0].update(date="2025-05-01", pool_id="other-pool")
        self.assertEqual(angel_guild(data)["gross_guild"], 0)

    def test_angel_boundaries_and_invalid_evidence(self):
        mutations = [
            ("incomplete_platform_population", lambda d: d["usage_population"].update(complete=False)),
            ("zero_platform_minutes", lambda d: [r.update(minutes="0") for r in d["usage"]]),
            ("negative_net", lambda d: d["costs"][0].update(amount="2000")),
            ("cost_scope_mismatch", lambda d: d["costs"][0].update(pool_id="other-pool")),
            ("usage_platform_mismatch", lambda d: d["usage"][0].update(platform_id="other")),
            ("usage_period_mismatch", lambda d: d["usage"][0].update(period={"start": "2025-01-01", "end": "2025-04-01"})),
            ("unqualified_usage_in_population", lambda d: d["usage"][0].update(qualified=False)),
            ("duplicate_id", lambda d: d["usage"].append(deepcopy(d["usage"][0]))),
            ("missing_evidence", lambda d: d["usage"][0].update(evidence_id="missing")),
            ("evidence_after_cutoff", lambda d: d["evidence"][0].update(observed_date="2025-07-02")),
            ("exact_number_required", lambda d: d["usage"][0].update(minutes=170.0)),
            ("nonzero_carry_outside_selected_method", lambda d: d.update(opening_carry="1")),
        ]
        for code, mutate in mutations:
            with self.subTest(code=code):
                data = fixture("angel-guild")
                mutate(data)
                self.assert_rejects(code, angel_guild, data)

    def test_mqp_rr03_agreement_date_and_actual_date_sensitivity(self):
        data = fixture("mqp-ordered")
        result = mqp_ordered_fees(data)
        for key, expected in data["expected"].items():
            if key != "receipt_fees":
                self.assertEqual(exact_json(result[key]), expected)
        self.assertEqual(exact_json([r["fee"] for r in result["receipts"]]), data["expected"]["receipt_fees"])
        self.assertEqual(result["history"][0]["actual_paid"], 900)  # accrual is not actual cash
        payment = next(r for r in result["history"] if r["id"] == "actual-payment")
        self.assertEqual((payment["actual_paid"], payment["fee_available_paid"]), (1000, 900))
        self.assertEqual(len(result["excluded_events"]), 2)
        data["policy"]["trigger"] = "actual_date"
        result = mqp_ordered_fees(data)
        expected = data["sensitivity_expected"]["actual_date"]
        self.assertEqual((exact_json(result["fee"]), exact_json(result["adjusted_receipts_before_RPPA"])),
                         (expected["fee"], expected["adjusted_receipts_before_RPPA"]))
        self.assertEqual(exact_json([r["fee"] for r in result["receipts"]]), expected["receipt_fees"])

    def test_mqp_threshold_equality_and_no_implicit_retroactivity(self):
        data = fixture("mqp-ordered")
        data["policy"]["threshold_comparison"] = "greater_than"
        result = mqp_ordered_fees(data)
        self.assertEqual(result["fee"], 30)
        self.assertEqual(result["adjusted_receipts_before_RPPA"], 270)
        data["policy"]["threshold_comparison"] = "at_least"
        data["events"][2]["disputed"] = False
        data["events"] = [e for e in data["events"] if e["kind"] not in ("dispute", "agreement")]
        self.assertEqual(mqp_ordered_fees(data)["fee"], 50)

    def test_mqp_same_day_order_and_physical_input_permutation(self):
        data = fixture("mqp-ordered")
        expected = mqp_ordered_fees(data)
        data["events"].reverse()
        self.assertEqual(mqp_ordered_fees(data), expected)
        data = fixture("mqp-ordered")
        agreement = next(e for e in data["events"] if e["kind"] == "agreement")
        receipt = next(e for e in data["events"] if e["id"] == "receipt-during-dispute")
        receipt.update(date=agreement["date"], sequence=1)
        self.assertEqual(mqp_ordered_fees(data)["fee"], 50)
        agreement["sequence"], receipt["sequence"] = 1, 0
        self.assertEqual(mqp_ordered_fees(data)["fee"], 40)
        receipt["sequence"] = 1
        self.assert_rejects("ambiguous_event_order", mqp_ordered_fees, data)

    def test_mqp_invalid_trigger_scope_timing_and_links(self):
        mutations = [
            ("unknown_trigger", lambda d: d["policy"].update(trigger="default")),
            ("unknown_equality_policy", lambda d: d["policy"].update(threshold_comparison="default")),
            ("ordering_policy_required", lambda d: d["policy"].update(same_day_order="input_order")),
            ("event_outside_period", lambda d: d["events"][0].update(date="2008-04-01")),
            ("event_after_cutoff", lambda d: d["events"][0].update(date="2008-04-02")),
            ("missing_prior_payment", lambda d: d["events"][5].update(payment_id="other-project-payment")),
            ("agreement_actual_date_mismatch", lambda d: d["events"][5].update(agreed_actual_date="2008-01-10")),
            ("amount_change_outside_selected_method", lambda d: d["events"][5].update(agreed_amount="99")),
        ]
        for code, mutate in mutations:
            with self.subTest(code=code):
                data = fixture("mqp-ordered")
                mutate(data)
                self.assert_rejects(code, mqp_ordered_fees, data)

    def test_mqp_empty_events_and_other_project_cannot_escalate(self):
        data = fixture("mqp-ordered")
        data["events"] = [e for e in data["events"] if e["kind"] == "receipt" or e["project_id"] == "project-b"]
        self.assertEqual(mqp_ordered_fees(data)["fee"], 30)
        data["events"] = []
        result = mqp_ordered_fees(data)
        self.assertEqual((result["fee"], result["adjusted_receipts_before_RPPA"], result["closing_actual_paid"]), (0, 0, 900))

    def test_mqp_correction_movements_capacity_and_carry(self):
        data = fixture("mqp-correction")
        result = mqp_correction(data)
        self.assertEqual(result["applied"], 10)
        self.assertEqual([r["applied"] for r in result["movements"]], [4, 6])
        self.assertEqual([r["closing_correction"] for r in result["movements"]], [6, 0])
        self.assertEqual([r["unused_capacity"] for r in result["movements"]], [0, 6])
        data["capacities"] = data["capacities"][:1]
        self.assertEqual(mqp_correction(data)["closing_correction"], 6)
        data["capacities"][0]["amount"] = "0"
        self.assertEqual(mqp_correction(data)["closing_correction"], 10)
        data["capacities"] = []
        self.assertEqual(mqp_correction(data)["closing_correction"], 10)

    def test_correction_small_capacities_conserve_authorized_amount(self):
        for a, b in itertools.product(range(12), repeat=2):
            data = fixture("mqp-correction")
            for row, amount in zip(data["capacities"], (a, b)):
                row["amount"] = str(amount)
            result = mqp_correction(data)
            self.assertEqual(result["applied"], min(10, a + b))
            self.assertEqual(result["applied"] + result["closing_correction"], 10)
            self.assertTrue(all(0 <= r["applied"] <= r["available_capacity"] for r in result["movements"]))

    def test_correction_requires_authority_scope_and_once_only_recognition(self):
        mutations = [
            ("unauthorized_correction", lambda d: d["authorizations"][0].update(authorized=False)),
            ("correction_already_recognized", lambda d: d["previously_recognized_ids"].append(d["authorizations"][0]["id"])),
            ("duplicate_id", lambda d: d["authorizations"].append(deepcopy(d["authorizations"][0]))),
            ("capacity_scope_mismatch", lambda d: d["capacities"][0].update(pool_id="another-pool")),
            ("capacity_before_authority", lambda d: d["capacities"][0].update(date="2008-02-04")),
            ("authority_after_cutoff", lambda d: d["authorizations"][0].update(authorized_date="2008-04-02")),
        ]
        for code, mutate in mutations:
            with self.subTest(code=code):
                data = fixture("mqp-correction")
                mutate(data)
                self.assert_rejects(code, mqp_correction, data)

    def test_supplied_due_reserve_before_on_date_and_scope(self):
        data = fixture("supplied-due-reserve")
        result = supplied_due_reserve(data)
        self.assertEqual({k: exact_json(result[k]) for k in data["expected"]}, data["expected"])
        data["close_date"] = "2025-02-27"
        self.assertEqual(supplied_due_reserve(data)["released"], 0)
        data["vintage"]["pool_id"] = "other-pool"
        self.assert_rejects("vintage_scope_mismatch", supplied_due_reserve, data)
        data = fixture("supplied-due-reserve")
        data["close_date"] = "2025-03-01"
        self.assert_rejects("close_outside_period_or_cutoff", supplied_due_reserve, data)

    def test_calculations_do_not_read_expected_or_mutate_neutral_inputs(self):
        for name, calculate in (("angel-guild", angel_guild), ("mqp-ordered", mqp_ordered_fees),
                                ("mqp-correction", mqp_correction), ("supplied-due-reserve", supplied_due_reserve)):
            data = fixture(name)
            original = deepcopy(data)
            result = calculate(data)
            self.assertEqual(data, original)
            del data["expected"]
            self.assertEqual(calculate(data), result)


if __name__ == "__main__":
    unittest.main()
