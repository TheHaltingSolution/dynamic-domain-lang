"""Independent term-finality, cap precedence and actual-funding controls."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.term_guarantees import TermGuaranteeOracleError, exact_json, term_guarantees


ROOT = Path(__file__).resolve().parents[1]


def fixture(method="actual_funded_advance", earned="80", funding="150", floor=None, cap=None, face=None):
    data = json.loads((ROOT / "cases/term-guarantees/neutral.json").read_text(encoding="utf-8"))
    data["policy"]["method"] = data["opening_state"]["method"] = method
    advance = method == "actual_funded_advance" or "advance_" in method
    floor_active = method == "term_floor_at_end" or method.startswith(("floor_cap_", "cap_floor_"))
    cap_active = method == "term_cap" or method.startswith(("floor_cap_", "cap_floor_"))
    data["term"].update(floor=floor if floor is not None else "100" if floor_active else "0",
                         cap=cap if cap is not None else "90" if method.startswith(("floor_cap_", "cap_floor_")) else "100" if cap_active else "0",
                         recoupable_minimum_face=face if face is not None else funding if advance and funding is not None else "150" if advance else "0")
    data["opening_state"]["term"] = deepcopy(data["term"])
    data["earnings"][0]["amount"] = earned
    if not advance:
        data["fundings"] = []
        data["evidence"] = [row for row in data["evidence"] if row["kind"] not in ("complete_funding_population", "actual_advance_funding")]
    elif funding is None:
        data["fundings"] = []
    else:
        data["fundings"][0].update(amount=funding, source_ref="synthetic-funded-" + funding)
    if advance:
        attested = next(row for row in data["evidence"] if row["kind"] == "complete_funding_population")
        attested.update(funding_ids=[row["id"] for row in data["fundings"]],
                        disbursement_ids=[row["disbursement_id"] for row in data["fundings"]],
                        funded_total=str(sum((Fraction(row["amount"]) for row in data["fundings"]), Fraction())))
    return data


def extend_term(data):
    data["term"]["period"]["end"] = "2026-07-01"
    data["opening_state"]["term"] = deepcopy(data["term"])


def successor(previous, previous_input, earned="40", funding=None):
    data = deepcopy(previous_input)
    data.update(case_id="term-q2", period={"start": previous["period"]["end"], "end": data["term"]["period"]["end"]},
                as_of="2026-06-30", cutoff="2026-07-03T00:00:00Z")
    data["opening_state"] = exact_json(previous["closing_state"])
    data["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
    original_earned = deepcopy(fixture()["earnings"][0])
    original_earned.update(id="earned-q2", amount=earned, effective_date="2026-06-15", observed_at="2026-07-01T00:00:00Z",
                           source_ref="synthetic-original-earned-q2", evidence_ref="earnings-source-q2")
    data["earnings"] = [original_earned]
    data["evidence"].append({"id": "earnings-source-q2", "scope": deepcopy(data["scope"]), "observed_at": "2026-07-01T00:00:00Z", "kind": "synthetic-original-earnings"})
    advance = previous["advance_active"]
    data["fundings"] = []
    if advance:
        data["evidence"].append({"id": "complete-q2", "scope": deepcopy(data["scope"]), "term_id": data["term"]["id"],
                                 "period": deepcopy(data["period"]), "observed_at": "2026-07-02T00:00:00Z", "kind": "complete_funding_population",
                                 "funding_ids": [], "disbursement_ids": [], "funded_total": "0"})
        if funding is not None:
            row = deepcopy(fixture()["fundings"][0])
            row.update(id="funded-advance-q2", disbursement_id="disbursement-q2", amount=funding, funded_date="2026-05-10",
                       funded_at="2026-05-10T12:00:00Z", observed_at="2026-05-11T00:00:00Z", source_ref="synthetic-funded-q2", evidence_ref="funding-source-q2")
            data["fundings"] = [row]
            data["evidence"].append({"id": "funding-source-q2", "scope": deepcopy(data["scope"]), "observed_at": "2026-05-11T00:00:00Z", "kind": "actual_advance_funding"})
            next(row for row in data["evidence"] if row["id"] == "complete-q2").update(
                funding_ids=[row["id"]], disbursement_ids=[row["disbursement_id"]], funded_total=funding)
    return data


class TermGuaranteeOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(TermGuaranteeOracleError) as raised:
            term_guarantees(data)
        self.assertEqual(str(raised.exception), code)
        return raised.exception

    def test_actual_funded_minimum_baseline_and_payment_separation(self):
        result = term_guarantees(fixture())
        self.assertEqual([result[key] for key in ("earned", "entitlement", "new_actual_funding", "available_prepayment", "recovery_base", "recovered", "payable_calculated")], [80, 80, 150, 150, 80, 80, 0])
        self.assertEqual(result["closing_meters"]["prepayment"], 70)
        self.assertEqual(result["closing_meters"]["term_recognized_entitlement"], 80)
        self.assertEqual(result["funding_population_status"], "complete_with_funding")
        self.assertEqual(result["settlement_payment_evidence_status"], "no_event_supplied")
        self.assertNotIn("actual_paid", result)
        self.assertEqual(result["closing_state"]["period_history"][0]["fundings"][0]["disbursement_id"], "actual-disbursement-q1")

    def test_face_only_does_not_manufacture_advance_under_complete_empty_view(self):
        result = term_guarantees(fixture(funding=None, face="150"))
        self.assertEqual((result["new_actual_funding"], result["recovered"], result["payable_calculated"], result["closing_meters"]["prepayment"]), (0, 0, 80, 0))
        self.assertEqual(result["funding_population_status"], "complete_no_events")
        self.assertEqual(result["settlement_payment_evidence_status"], "no_event_supplied")

    def test_missing_funding_population_is_unknown_and_blocks_final_state(self):
        for funding in (None, "150"):
            data = fixture(funding=funding)
            data["evidence"] = [row for row in data["evidence"] if row["kind"] != "complete_funding_population"]
            error = self.reject(data, "TERM_FUNDING_POPULATION_REQUIRED")
            self.assertEqual(error.funding_evidence_status, "no_event_supplied")
            self.assertFalse(hasattr(error, "prepayment"))
            self.assertFalse(hasattr(error, "actual_paid"))

    def test_original_funding_population_ids_and_totals_cannot_be_dropped(self):
        data = fixture(); data["fundings"] = []
        self.reject(data, "TERM_FUNDING_POPULATION_CONTROL")
        data = fixture(); data["fundings"][0]["amount"] = "100"
        self.reject(data, "TERM_FUNDING_POPULATION_CONTROL")
        data = fixture(); next(row for row in data["evidence"] if row["kind"] == "complete_funding_population")["funding_ids"] = []
        self.reject(data, "TERM_FUNDING_POPULATION_CONTROL")
        data = fixture(); data["evidence"] = [row for row in data["evidence"] if row["id"] != "funding-source"]
        self.reject(data, "TERM_EVIDENCE_REQUIRED")
        first_data = fixture(funding="100", face="150"); extend_term(first_data)
        first = term_guarantees(first_data)
        data = successor(first, first_data)
        data["evidence"] = [row for row in data["evidence"] if row["id"] != "complete-q1"]
        self.assertEqual(self.reject(data, "TERM_FUNDING_POPULATION_REQUIRED").funding_evidence_status, "no_event_supplied")

    def test_end_only_term_floor_interim40_then_final60(self):
        first_data = fixture("term_floor_at_end", earned="40")
        extend_term(first_data)
        first = term_guarantees(first_data)
        self.assertEqual((first["is_term_end"], first["floor_topup_before_cap"], first["entitlement"]), (False, 0, 40))
        final = term_guarantees(successor(first, first_data))
        self.assertEqual((final["earned"], final["floor_topup_before_cap"], final["entitlement"], final["payable_calculated"]), (40, 20, 60, 60))
        self.assertEqual(final["closing_meters"]["term_recognized_entitlement"], 100)
        self.assertTrue(final["closing_meters"]["term_closed"])
        self.assertEqual(final["closing_meters"]["total_funded"], 0)

    def test_term_cap_is_cumulative_not_a_period_reset(self):
        first_data = fixture("term_cap", earned="60", cap="100"); extend_term(first_data)
        first = term_guarantees(first_data)
        second = term_guarantees(successor(first, first_data, earned="60"))
        self.assertEqual((first["entitlement"], second["entitlement"]), (60, 40))
        self.assertEqual((second["closing_meters"]["term_earned"], second["closing_meters"]["term_cap_consumed"], second["closing_meters"]["term_recognized_entitlement"]), (120, 100, 100))

    def test_floor_cap_and_cap_floor_with_funded50(self):
        first = term_guarantees(fixture("floor_cap_advance_including_topup", funding="50"))
        second = term_guarantees(fixture("cap_floor_advance_including_topup", funding="50"))
        self.assertEqual((first["entitlement"], first["payable_calculated"], first["retained_topup"], first["closing_meters"]["term_cap_consumed"]), (90, 40, 10, 90))
        self.assertEqual((second["entitlement"], second["payable_calculated"], second["retained_topup"], second["closing_meters"]["term_cap_consumed"]), (100, 50, 20, 80))
        self.assertEqual(first["unmet_floor_at_term_end"], 10)
        self.assertEqual(second["unmet_floor_at_term_end"], 0)

    def test_funded150_topup_recovery_is_explicitly_selected(self):
        controls = {"floor_cap_advance_including_topup": (90, 90, 0, 60),
                    "floor_cap_advance_earned_only": (90, 80, 10, 70),
                    "cap_floor_advance_including_topup": (100, 100, 0, 50),
                    "cap_floor_advance_earned_only": (100, 80, 20, 70)}
        for method, expected in controls.items():
            result = term_guarantees(fixture(method, funding="150"))
            self.assertEqual((result["entitlement"], result["recovered"], result["payable_calculated"], result["closing_meters"]["prepayment"]), expected)
            self.assertEqual(result["closing_meters"]["total_funded"], 150)
            self.assertEqual(result["available_prepayment"], 150)

    def test_actual_funding_and_recovery_carry_with_original_predecessor(self):
        first_data = fixture(earned="80", funding="100", face="150"); extend_term(first_data)
        first = term_guarantees(first_data)
        second_data = successor(first, first_data, earned="40", funding="50")
        second = term_guarantees(second_data)
        self.assertEqual((first["closing_meters"]["prepayment"], second["new_actual_funding"], second["available_prepayment"], second["recovered"], second["closing_meters"]["prepayment"]), (20, 50, 70, 40, 30))
        self.assertEqual((second["closing_meters"]["total_funded"], second["closing_meters"]["total_recovered"]), (150, 120))
        self.assertEqual(len(second["closing_state"]["period_history"]), 2)
        self.assertEqual(json.loads(json.dumps(second_data)), second_data)

    def test_floor_meter_counts_entitlement_not_reduced_payable(self):
        data = fixture("cap_floor_advance_including_topup", earned="40", funding="100", floor="100", cap="200", face="100")
        extend_term(data)
        first = term_guarantees(data)
        self.assertEqual((first["entitlement"], first["payable_calculated"]), (40, 0))
        second = term_guarantees(successor(first, data, earned="40"))
        self.assertEqual((second["floor_topup_before_cap"], second["entitlement"], second["recovered"], second["payable_calculated"]), (20, 60, 60, 0))
        self.assertEqual(second["closing_meters"]["term_recognized_entitlement"], 100)

    def test_non_advance_methods_reject_funding_and_other_prepayment(self):
        data = fixture("term_floor_at_end")
        data["fundings"] = deepcopy(fixture()["fundings"])
        self.reject(data, "TERM_ADVANCE_OUTSIDE_METHOD")
        data = fixture("term_cap"); data["opening_state"]["prepayment"] = "1"
        self.reject(data, "TERM_ADVANCE_OUTSIDE_METHOD")
        data = fixture("term_floor_at_end"); data["term"]["recoupable_minimum_face"] = "150"
        self.reject(data, "TERM_UNUSED_AMOUNT")

    def test_actual_funding_dates_observation_and_support_evidence(self):
        changes = [("TERM_FUNDED_UTC_DATE", lambda d: d["fundings"][0].update(funded_date="2026-01-11")),
                   ("TERM_FUNDING_OBSERVATION_ORDER", lambda d: d["fundings"][0].update(observed_at="2026-01-10T11:59:59Z")),
                   ("TERM_ACTUAL_FUNDING_REQUIRED", lambda d: d["fundings"][0].update(approved=False)),
                   ("TERM_ACTUAL_FUNDING_EVIDENCE", lambda d: d["evidence"][2].update(kind="planned_funding")),
                   ("TERM_FACT_CUTOFF", lambda d: d["fundings"][0].update(observed_at=d["cutoff"])),
                   ("TERM_EVIDENCE_CUTOFF", lambda d: d["evidence"][2].update(observed_at=d["cutoff"]))]
        for code, change in changes:
            data = fixture(); change(data); self.reject(data, code)
        data = fixture(); data["fundings"][0].update(funded_date="2026-04-01", funded_at="2026-04-01T00:00:00Z", observed_at="2026-04-02T00:00:00Z")
        self.reject(data, "TERM_FUNDING_PERIOD")

    def test_late_observed_june30_funding_and_offset_utc_date(self):
        data = fixture()
        period = {"start": "2026-04-01", "end": "2026-07-01"}
        data.update(period=period, as_of="2026-06-30", cutoff="2026-07-03T00:00:00Z")
        data["term"]["period"] = deepcopy(period)
        data["opening_state"].update(boundary=period["start"], term=deepcopy(data["term"]))
        data["earnings"][0]["effective_date"] = "2026-05-15"
        data["fundings"][0].update(funded_date="2026-06-30", funded_at="2026-07-01T00:30:00+01:00", observed_at="2026-07-02T00:00:00Z")
        data["evidence"][2]["observed_at"] = "2026-07-02T00:00:00Z"
        data["evidence"][3].update(period=deepcopy(period), observed_at="2026-07-02T12:00:00Z")
        self.assertEqual(term_guarantees(data)["closing_meters"]["prepayment"], 70)
        data["fundings"][0]["funded_date"] = "2026-07-01"
        self.reject(data, "TERM_FUNDED_UTC_DATE")

    def test_duplicate_events_disbursements_and_historical_replay_fail(self):
        for field in ("earnings", "fundings", "evidence"):
            data = fixture(); data[field].append(deepcopy(data[field][0]))
            self.reject(data, "TERM_DUPLICATE_ID")
        data = fixture(); data["fundings"].append({**deepcopy(data["fundings"][0]), "id": "renamed-funding", "source_ref": "renamed-source"})
        self.reject(data, "TERM_DISBURSEMENT_ALREADY_RECOGNIZED")
        first_data = fixture(funding="100", face="150"); extend_term(first_data)
        first = term_guarantees(first_data)
        data = successor(first, first_data, funding="50"); data["fundings"][0]["disbursement_id"] = "actual-disbursement-q1"
        self.reject(data, "TERM_DISBURSEMENT_ALREADY_RECOGNIZED")
        data = successor(first, first_data); data["earnings"][0]["id"] = "earned-q1"
        self.reject(data, "TERM_EARNING_ALREADY_RECOGNIZED")
        data = fixture(); data["fundings"][0]["amount"] = "151"
        next(row for row in data["evidence"] if row["kind"] == "complete_funding_population")["funded_total"] = "151"
        self.reject(data, "TERM_FUNDED_CEILING")

    def test_full_term_method_cap_reduction_and_predecessor_are_pinned(self):
        first_data = fixture("term_cap", earned="60"); extend_term(first_data)
        first = term_guarantees(first_data)
        original = successor(first, first_data)
        changes = [("TERM_OPENING_METHOD", lambda d: d["opening_state"].update(method="term_floor_at_end")),
                   ("TERM_OPENING_METHOD", lambda d: d["opening_state"].update(cap_reduction_order="earned_first")),
                   ("TERM_AMENDMENT_REQUIRED", lambda d: d["term"].update(cap="200")),
                   ("TERM_OPENING_SCOPE", lambda d: d["opening_state"].update(purpose="reserve")),
                   ("TERM_OPENING_BOUNDARY", lambda d: d["opening_state"].update(boundary="2026-04-02")),
                   ("TERM_PREDECESSOR_REQUIRED", lambda d: d.pop("prior_result")),
                   ("TERM_PREDECESSOR_MISMATCH", lambda d: d["opening_state"].update(term_cap_consumed="0"))]
        for code, change in changes:
            data = deepcopy(original); change(data); self.reject(data, code)
        data = fixture(); data["policy"]["cap_reduction_order"] = "earned_before_topup"
        self.reject(data, "TERM_SELECTED_POLICY")

    def test_original_history_recomputes_each_distinct_meter(self):
        first_data = fixture(funding="100", face="150"); extend_term(first_data)
        first = term_guarantees(first_data)
        for field, value in (("term_earned", "81"), ("term_recognized_entitlement", "81"), ("total_funded", "99"),
                             ("total_recovered", "79"), ("prepayment", "21")):
            data = successor(first, first_data)
            data["opening_state"][field] = value
            data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
            self.reject(data, "TERM_OPENING_HISTORY_RECONCILIATION")

    def test_term_finality_scope_and_missing_complete_population_for_history(self):
        first_data = fixture(); first = term_guarantees(first_data)
        data = deepcopy(first_data)
        data["period"] = {"start": "2026-04-01", "end": "2026-07-01"}
        self.reject(data, "TERM_PERIOD_OUTSIDE_TERM")
        data = fixture(); data["fundings"][0]["scope"]["pool_id"] = "outside"
        self.reject(data, "TERM_FACT_SCOPE")
        data = fixture(); data["evidence"][3]["term_id"] = "outside"
        self.reject(data, "TERM_FUNDING_COMPLETENESS_SCOPE")
        data = fixture(); data["evidence"].append({**deepcopy(data["evidence"][3]), "id": "other-complete"})
        self.reject(data, "TERM_FUNDING_POPULATION_AMBIGUOUS")

    def test_zero_empty_end_floor_and_exact_fractional_stage_amounts(self):
        data = fixture("term_floor_at_end"); data["earnings"] = []
        self.assertEqual((term_guarantees(data)["entitlement"], term_guarantees(data)["new_actual_funding"]), (100, 0))
        data = fixture("term_cap", earned="0", cap="0")
        self.assertEqual(term_guarantees(data)["entitlement"], 0)
        data = fixture("actual_funded_advance", earned="1/3", funding="1/7")
        result = term_guarantees(data)
        self.assertEqual((result["recovered"], result["payable_calculated"]), (Fraction(1, 7), Fraction(4, 21)))
        self.assertEqual(exact_json(result)["payable_calculated"], "4/21")
        for amount in (0.1, True, "-1", "1e2"):
            data = fixture(); data["earnings"][0]["amount"] = amount
            self.reject(data, "TERM_EXACT_NONNEGATIVE_VALUE")

    def test_input_permutation_determinism_and_no_compiler_imports(self):
        data = fixture(); original = deepcopy(data)
        expected = term_guarantees(data)
        self.assertEqual(data, original)
        data["evidence"].reverse(); data["earnings"].reverse(); data["fundings"].reverse()
        self.assertEqual(term_guarantees(data), expected)
        self.assertEqual(term_guarantees(original), expected)
        tree = ast.parse((ROOT / "oracles/term_guarantees.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
