"""Independent original-event tier/escalation controls before SPL implementation."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.escalation import EscalationOracleError, escalation, exact_json


ROOT = Path(__file__).resolve().parents[1]
METHOD_RESULTS = {"prospective_split": 12, "current_period_ending_rate": 14, "row_opening_rate": 11,
                  "row_ending_rate": 14, "cumulative_reprice_delta": 22}


def fixture(method="prospective_split"):
    data = json.loads((ROOT / "cases/escalation/neutral.json").read_text(encoding="utf-8"))
    data["policy"]["method"] = data["opening_state"]["method"] = method
    return data


def replace_events(data, amounts):
    prototype = deepcopy(data["events"][0])
    data["events"] = [{**deepcopy(prototype), "id": f"replacement-{index}", "source_ref": f"replacement-source-{index}",
                       "sequence": index, "basis": amount} for index, amount in enumerate(amounts)]


def genesis(method="prospective_split", amounts=("80",)):
    data = fixture(method)
    old = deepcopy(data["opening_state"]["period_history"][0])
    data.update(case_id="actual-oracle-genesis", period=old["period"], as_of="2026-01-01", cutoff="2026-01-03T00:00:00Z")
    data["events"] = old["events"]
    data["evidence"] = [row for row in data["evidence"] if row["id"] != "current-source"]
    replace_events(data, amounts)
    data["opening_state"].update(boundary=old["period"]["start"], origin="genesis", source_case_id="genesis",
                                  cumulative_basis="0", recognized_entitlement="0", period_history=[])
    return data


def with_predecessor(previous, method=None):
    data = fixture(method or previous["method"])
    data["opening_state"] = exact_json(previous["closing_state"])
    data["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
    return data


class EscalationOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(EscalationOracleError) as raised:
            escalation(data)
        self.assertEqual(str(raised.exception), code)

    def test_all_five_hand_controls_and_original_opening(self):
        for method, expected in METHOD_RESULTS.items():
            with self.subTest(method=method):
                result = escalation(fixture(method))
                self.assertEqual((result["opening_basis"], result["opening_recognized"], result["period_basis"], result["closing_basis"]), (80, 8, 70, 150))
                self.assertEqual(result["current_result"], expected)
                self.assertEqual(result["closing_recognized"], 8 + expected)
                self.assertEqual(result["ending_rate"], Fraction(1, 5))
                self.assertEqual([row["basis_before"] for row in result["rows"]], [80, 110])
                self.assertNotIn("actual_paid", result)
                self.assertNotIn("issued", result)

    def test_prospective_original_band_slices(self):
        result = escalation(fixture())
        slices = result["rows"][0]["rate_details"]["slices"]
        self.assertEqual([(row["bracket_id"], row["width"], row["rate"], row["amount"]) for row in slices],
                         [("tier-0", 20, Fraction(1, 10), 2), ("tier-1", 10, Fraction(1, 5), 2)])
        self.assertEqual([row["current_result"] for row in result["rows"]], [4, 8])

    def test_reprice_delta_subtracts_original_recognized_once(self):
        result = escalation(fixture("cumulative_reprice_delta"))
        self.assertEqual([row["current_result"] for row in result["rows"]], [14, 8])
        self.assertEqual([row["recognized_before"] for row in result["rows"]], [8, 22])
        self.assertEqual((result["current_result"], result["closing_recognized"]), (22, 30))
        self.assertNotEqual(result["current_result"], 30)

    def test_actual_genesis_then_adjacent_successor_for_every_method(self):
        for method, expected in METHOD_RESULTS.items():
            with self.subTest(method=method):
                first = escalation(genesis(method))
                self.assertEqual((first["current_result"], first["closing_basis"], first["closing_recognized"]), (8, 80, 8))
                data = with_predecessor(first)
                # Current rows use distinct original IDs from those in genesis.
                self.assertEqual(escalation(data)["current_result"], expected)
                self.assertEqual(len(escalation(data)["closing_state"]["period_history"]), 2)
                self.assertEqual(json.loads(json.dumps(data)), data)

    def test_lower_inclusive_threshold_is_method_specific(self):
        expected = {"prospective_split": 10, "current_period_ending_rate": 20, "row_opening_rate": 10,
                    "row_ending_rate": 20, "cumulative_reprice_delta": 20}
        for method, amount in expected.items():
            result = escalation(genesis(method, ("100",)))
            self.assertEqual((result["current_result"], result["ending_rate"]), (amount, Fraction(1, 5)))

    def test_event_repartition_does_not_have_universal_invariance(self):
        expected = {"prospective_split": (12, 12), "current_period_ending_rate": (14, 14),
                    "row_opening_rate": (7, 7), "row_ending_rate": (14, 13), "cumulative_reprice_delta": (22, 22)}
        for method, (one, split) in expected.items():
            whole = fixture(method); replace_events(whole, ("70",))
            two = fixture(method); replace_events(two, ("10", "60"))
            self.assertEqual((escalation(whole)["current_result"], escalation(two)["current_result"]), (one, split))
        self.assertEqual(escalation(fixture("row_opening_rate"))["current_result"], 11)

    def test_explicit_order_changes_whole_row_economics(self):
        data = fixture("row_opening_rate")
        data["events"][0]["sequence"], data["events"][1]["sequence"] = 2, 1
        result = escalation(data)
        # 40 first uses .1, then30 uses .2:4+6=10, not the old11.
        self.assertEqual(result["current_result"], 10)
        self.assertEqual([row["basis"] for row in result["rows"]], [40, 30])

    def test_zero_empty_and_exact_fractional_intermediates(self):
        for method in METHOD_RESULTS:
            data = fixture(method); data["events"] = []
            result = escalation(data)
            self.assertEqual((result["current_result"], result["closing_basis"], result["closing_recognized"]), (0, 80, 8))
            data = fixture(method); replace_events(data, ("0",))
            self.assertEqual(escalation(data)["current_result"], 0)
        data = fixture(); replace_events(data, ("1/3",))
        self.assertEqual(escalation(data)["current_result"], Fraction(1, 30))
        self.assertEqual(exact_json(escalation(data))["current_result"], "1/30")

    def test_brackets_gap_overlap_unbounded_order_and_monotone_rates(self):
        changes = [("ESCALATION_BRACKET_PARTITION", lambda d: d["bracket_table"]["brackets"][1].update(lower="101")),
                   ("ESCALATION_BRACKET_PARTITION", lambda d: d["bracket_table"]["brackets"][1].update(lower="99")),
                   ("ESCALATION_FINAL_UNBOUNDED", lambda d: d["bracket_table"]["brackets"][1].update(upper="200")),
                   ("ESCALATION_DECREASING_RATE", lambda d: d["bracket_table"]["brackets"][1].update(rate="0.05")),
                   ("ESCALATION_RATE_DOMAIN", lambda d: d["bracket_table"]["brackets"][1].update(rate="1.1")),
                   ("ESCALATION_BRACKET_SEQUENCE", lambda d: d["bracket_table"]["brackets"][1].update(sequence=1))]
        for code, change in changes:
            data = fixture(); change(data); self.reject(data, code)
        data = fixture(); data["bracket_table"]["brackets"] = []
        self.reject(data, "ESCALATION_BRACKETS_REQUIRED")

    def test_actual_state_rejects_method_and_full_bracket_amendments(self):
        first = escalation(genesis())
        data = with_predecessor(first); data["policy"]["method"] = "row_ending_rate"
        self.reject(data, "ESCALATION_OPENING_METHOD")
        for field, value in (("rate", "0.25"), ("source_ref", "amended-source")):
            data = with_predecessor(first); data["bracket_table"]["brackets"][1][field] = value
            self.reject(data, "ESCALATION_BRACKET_AMENDMENT")
        data = with_predecessor(first); data["bracket_table"]["version"] = "2"
        self.reject(data, "ESCALATION_BRACKET_AMENDMENT")
        data["opening_state"]["bracket_table"] = deepcopy(data["bracket_table"])
        self.reject(data, "ESCALATION_PREDECESSOR_MISMATCH")

    def test_original_event_duplicate_id_source_alias_and_sequence_fail(self):
        data = fixture(); data["events"].append(deepcopy(data["events"][0]))
        self.reject(data, "ESCALATION_DUPLICATE_ID")
        data = fixture(); data["events"][1]["sequence"] = 1
        self.reject(data, "ESCALATION_EVENT_SEQUENCE")
        data = fixture(); data["events"][0]["id"] = "basis-original-80"
        self.reject(data, "ESCALATION_EVENT_ALREADY_RECOGNIZED")
        data = fixture(); data["events"][0]["source_ref"] = "synthetic-original-basis80"
        self.reject(data, "ESCALATION_SOURCE_ALREADY_RECOGNIZED")
        data = fixture(); data["events"][0]["sequence"] = True
        self.reject(data, "ESCALATION_EVENT_SEQUENCE")

    def test_history_replays_original_basis_and_recognized_results(self):
        for field, value in (("current_result", "9"), ("closing_recognized", "9"), ("closing_basis", "81"), ("opening_recognized", "1")):
            data = fixture(); data["opening_state"]["period_history"][0][field] = value
            self.reject(data, "ESCALATION_HISTORY_RECONCILIATION")
        data = fixture(); data["opening_state"]["recognized_entitlement"] = "9"
        self.reject(data, "ESCALATION_OPENING_HISTORY_RECONCILIATION")
        data = fixture(); data["opening_state"]["period_history"][0]["period"]["end"] = "2025-12-31"
        self.reject(data, "ESCALATION_OPENING_HISTORY_RECONCILIATION")

    def test_terms_available_before_all_historical_periods_not_new_retroactivity(self):
        data = fixture(); data["bracket_table"]["observed_at"] = "2025-10-01T00:00:00Z"
        data["opening_state"]["bracket_table"] = deepcopy(data["bracket_table"])
        self.reject(data, "ESCALATION_TABLE_HISTORICAL_AVAILABILITY")
        data = fixture(); data["bracket_table"]["recorded_date"] = "2025-10-02"
        data["opening_state"]["bracket_table"] = deepcopy(data["bracket_table"])
        self.reject(data, "ESCALATION_TABLE_HISTORICAL_AVAILABILITY")
        data = fixture(); data["bracket_table"]["effective"]["start"] = "2025-10-02"
        data["opening_state"]["bracket_table"] = deepcopy(data["bracket_table"])
        self.reject(data, "ESCALATION_TABLE_EFFECTIVE")
        data = fixture(); data["as_of"] = "2025-09-30"
        self.assertEqual(escalation(data)["current_result"], 12)
        data["as_of"] = "2025-09-29"
        self.reject(data, "ESCALATION_TABLE_ASOF")

    def test_scope_evidence_period_and_exact_cutoff(self):
        for field in ("events", "evidence"):
            data = fixture(); data[field][0]["scope"]["pool_id"] = "outside"
            self.reject(data, "ESCALATION_FACT_SCOPE" if field == "events" else "ESCALATION_EVIDENCE_SCOPE")
        for effective in ("2025-12-31", "2026-04-01"):
            data = fixture(); data["events"][0]["effective_date"] = effective
            self.reject(data, "ESCALATION_FACT_PERIOD")
        data = fixture(); data["events"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "ESCALATION_FACT_CUTOFF")
        data = fixture(); data["evidence"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "ESCALATION_EVIDENCE_CUTOFF")
        data = fixture(); data["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        data["events"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
        self.assertEqual(escalation(data)["current_result"], 12)

    def test_actual_predecessor_boundary_and_full_history_are_required(self):
        first = escalation(genesis())
        original = with_predecessor(first)
        changes = [("ESCALATION_PREDECESSOR_REQUIRED", lambda d: d.pop("prior_result")),
                   ("ESCALATION_OPENING_BOUNDARY", lambda d: d["opening_state"].update(boundary="2026-01-02")),
                   ("ESCALATION_PREDECESSOR_BOUNDARY", lambda d: d["prior_result"]["period"].update(end="2025-12-31")),
                   ("ESCALATION_PREDECESSOR_MISMATCH", lambda d: d["opening_state"].update(recognized_entitlement="9")),
                   ("ESCALATION_PREDECESSOR_MISMATCH", lambda d: d["opening_state"].update(period_history=[]))]
        for code, change in changes:
            data = deepcopy(original); change(data); self.reject(data, code)

    def test_nonnegative_basis_and_exact_money_no_binary_float(self):
        for value in ("-1", 30.0, True, "3e1"):
            data = fixture(); data["events"][0]["basis"] = value
            self.reject(data, "ESCALATION_EXACT_NONNEGATIVE_VALUE")
        data = fixture(); data["policy"]["method"] = "default"
        self.reject(data, "ESCALATION_METHOD_REQUIRED")
        data = fixture(); data["policy"]["rounding"] = "half_even"
        self.reject(data, "ESCALATION_SELECTED_POLICY")

    def test_original_row_and_bracket_permutation_preserves_named_method(self):
        for method in METHOD_RESULTS:
            data = fixture(method); original = deepcopy(data)
            expected = escalation(data)
            self.assertEqual(data, original)
            data["events"].reverse(); data["bracket_table"]["brackets"].reverse(); data["evidence"].reverse()
            self.assertEqual(escalation(data), expected)
            self.assertEqual(escalation(original), expected)
        tree = ast.parse((ROOT / "oracles/escalation.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
