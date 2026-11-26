"""Independent original-fact stage/cap/schedule and serialized-state controls."""
import ast
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest

from oracles.reserve_stages import ReserveStageOracleError, reserve_stages, exact_json, policy

ROOT = Path(__file__).resolve().parents[1]


def fixture(name="basis_reserve_vintages"):
    return json.loads((ROOT / "cases/reserve-stages/neutral.json").read_text(encoding="utf-8"))["scenarios"][name]


def view(case, position=0, previous=None):
    data = {"schema_version": "reserve-stages-neutral/1", **deepcopy(case["context"]), **deepcopy(case["frames"][position])}
    if previous is None:
        if position != 0: raise ValueError("Actual previous calculation required")
        data["opening_state"] = {"origin": "genesis", "boundary": data["period"]["start"], "source_case_id": "genesis", "history": []}
    else:
        actual = json.loads(json.dumps(exact_json(previous)))
        data["opening_state"] = deepcopy(actual["closing_state"])
        data["prior_result"] = {"source_case_id": actual["source_case_id"], "period": actual["period"], "result_ref": "supplied-neutral-result#" + actual["source_case_id"], "closing_state": deepcopy(actual["closing_state"])}
    return data


def chain(case):
    results = []
    for position in range(len(case["frames"])): results.append(reserve_stages(view(case, position, results[-1] if results else None)))
    return results


def lots(result): return {row["id"]: row for row in result["vintages"]}


def add_application(case, position, identity, vintage, value, when, total, sequence=1):
    scope = deepcopy(case["context"]["scope"]); frame = case["frames"][position]; observed = when + "T15:00:00Z"
    row = {"id": identity, "scope": scope, "observed_at": observed, "source_ref": "source:" + identity, "evidence_ref": "evidence:" + identity,
        "original_ref": "original-application#" + identity, "vintage_id": vintage, "amount": value, "event_date": when, "sequence": sequence, "authority_id": "authority:" + identity, "reserve_measure": case["context"]["policy"]["reserve_measure"]}
    authority = {"id": row["authority_id"], "scope": deepcopy(scope), "observed_at": observed, "source_ref": "source:" + row["authority_id"], "evidence_ref": "evidence:" + row["authority_id"],
        "application_id": identity, "vintage_id": vintage, "approved": True, "approved_date": when, "reserve_measure": row["reserve_measure"]}
    frame["applications"].append(row); frame["authorities"].append(authority)
    for record, kind in ((row, "reserve_application"), (authority, "reserve_application_authority")):
        frame["evidence"].append({"id": record["evidence_ref"], "scope": deepcopy(scope), "kind": kind, "approved": True, "observed_at": observed, "source_ref": "evidence-source:" + record["id"]})
    frame["population"].update(application_ids=[r["id"] for r in frame["applications"]], authority_ids=[r["id"] for r in frame["authorities"]], application_total=total)


def remove_applications(frame):
    removed = {r["evidence_ref"] for key in ("applications", "authorities") for r in frame[key]}
    frame["applications"] = []; frame["authorities"] = []; frame["evidence"] = [r for r in frame["evidence"] if r["id"] not in removed]
    frame["population"].update(application_ids=[], authority_ids=[], application_total="0")


class ReserveStageOracleTests(unittest.TestCase):
    def reject(self, data, code=None):
        before = deepcopy(data)
        with self.assertRaises(ReserveStageOracleError) as caught: reserve_stages(data)
        if code is not None: self.assertEqual(str(caught.exception), code)
        self.assertEqual(data, before)

    def check(self, result):
        cumulative = result["cumulative"]
        self.assertEqual(cumulative["gross"], cumulative["fee"] + cumulative["producer"] + cumulative["nonparticipant"] + cumulative["applications"] + result["closing_reserve"])
        current = result["current"]
        self.assertEqual(current["gross"] + result["opening_reserve"], current["fee"] + current["producer"] + current["nonparticipant"] + current["applications"] + result["closing_reserve"])
        for vintage in result["vintages"]: self.assertEqual(vintage["original_addition"], vintage["applied"] + vintage["released"] + vintage["available"])
        self.assertEqual(result["issuance_status"], "unissued_calculation"); self.assertEqual(result["payment_evidence_status"], "not_part_of_profile")
        self.assertFalse(result["bank_movement_created"] or result["source_clearance_inferred"])
        self.assertEqual(result["release_policy"], "unconditional_under_supplied_generic_terms")
        return result

    def test_fixed_fee_original_stage_discriminator35_vs36(self):
        a = self.check(chain(fixture("basis_reserve_stage"))[0]); b = self.check(chain(fixture("producer_holdback_stage"))[0])
        self.assertEqual((a["current"]["producer"], b["current"]["producer"]), (35, 36))
        self.assertEqual((a["current"]["additions"], b["current"]["additions"]), (20, 9))
        self.assertEqual((a["current"]["fee"], b["current"]["fee"]), (10, 10))
        self.assertNotEqual(a["reserve_measure"], b["reserve_measure"])

    def test_zero_fixed_fee_exposes_the_commuting_false_discriminator(self):
        amounts = []
        for name in ("basis_reserve_stage", "producer_holdback_stage"):
            case = fixture(name); case["context"]["terms"]["fixed_fee"] = "0"
            amounts.append(self.check(chain(case)[0])["current"]["producer"])
        self.assertEqual(amounts, [40, 40])

    def test_release_does_not_charge_fee_or_participation_twice(self):
        for name, released, producer, nonparticipant in (("basis_reserve_stage", 20, 10, 10), ("producer_holdback_stage", 9, 9, 0)):
            results = chain(fixture(name)); first, last = map(self.check, results)
            self.assertEqual((last["current"]["releases"], last["current"]["producer"], last["current"]["nonparticipant"]), (released, producer, nonparticipant))
            self.assertEqual(last["current"]["fee"], 0); self.assertEqual(last["cumulative"]["fee"], 10)
            self.assertEqual(last["cumulative"]["producer"], 45); self.assertEqual(last["cumulative"]["nonparticipant"], 45)
            self.assertEqual(len(last["fee_consumption_keys"]), 1); self.assertEqual(last["closing_reserve"], 0)

    def test_vintage12_minus7_minus5_and_new20_both_distinct_purposes(self):
        for name, first_gross, second_gross in (("basis_reserve_vintages", 60, 100), ("producer_holdback_vintages", 130, 210)):
            results = chain(fixture(name)); first, second, last = map(self.check, results)
            self.assertEqual((first["current"]["gross"], second["current"]["gross"]), (first_gross, second_gross))
            self.assertEqual((lots(second)["V1"]["original_addition"], lots(second)["V1"]["applied"], lots(second)["V1"]["released"], lots(second)["V1"]["available"]), (12, 7, 5, 0))
            self.assertEqual(lots(second)["V2"]["available"], 20); self.assertEqual(second["closing_reserve"], 20); self.assertEqual(last["closing_reserve"], 0)

    def test_v1_second_application8_cannot_borrow_v2_twenty(self):
        for name in ("basis_reserve_vintages", "producer_holdback_vintages"):
            case = fixture(name); first = reserve_stages(view(case))
            add_application(case, 1, "second-V1-application", "V1", "8", "2026-04-01", "15")
            self.reject(view(case, 1, first), "RS_VINTAGE_APPLICATION_EXCEEDS_AVAILABLE")
            self.assertEqual(lots(first)["V1"]["available"], 12)

    def test_caps_limit_addition_and_keep_unretained_basis_current(self):
        outputs = []
        for cap, addition, receipt_producer in (("32", 20, F(75, 2)), ("33", 21, 37)):
            case = fixture(); case["context"]["terms"]["retained_cap"] = cap; case["frames"][1]["receipts"][0]["gross"] = "105"; case["frames"][1]["population"]["gross_total"] = "105"
            result = self.check(chain(case)[1]); row = result["receipt_details"][0]
            self.assertEqual((row["raw_addition"], row["addition"], row["producer"], row["nonparticipant"]), (21, addition, receipt_producer, receipt_producer))
            self.assertEqual(row["unretained_current"], 21 - addition); self.assertEqual(row["closing_retained_after_addition"], int(cap)); outputs.append(row["producer"])
        self.assertNotEqual(*outputs)

    def test_holdback_cap_limits_producer_hold_not_gross_basis(self):
        for cap, addition, available in (("32", 20, 85), ("33", 21, 84)):
            case = fixture("producer_holdback_vintages"); case["context"]["terms"]["retained_cap"] = cap; case["frames"][1]["receipts"][0]["gross"] = "220"; case["frames"][1]["population"]["gross_total"] = "220"
            row = self.check(chain(case)[1])["receipt_details"][0]
            self.assertEqual((row["raw_addition"], row["addition"], row["producer"], row["nonparticipant"]), (21, addition, available, 105))

    def test_later_application_release_does_not_retroactively_free_capacity(self):
        case = fixture(); case["context"]["terms"]["retained_cap"] = "20"
        result = self.check(chain(case)[1]); row = result["receipt_details"][0]
        self.assertEqual((row["retained_before"], row["cap_room_before"], row["addition"], row["unretained_current"]), (12, 8, 8, 12))
        self.assertEqual((lots(result)["V1"]["available"], lots(result)["V2"]["available"]), (0, 8))

    def test_zero_cap_keeps_all_original_money_current(self):
        for name in ("basis_reserve_stage", "producer_holdback_stage"):
            case = fixture(name); case["context"]["terms"]["retained_cap"] = "0"; first = self.check(chain(case)[0])
            self.assertEqual((first["current"]["additions"], first["current"]["producer"], first["current"]["nonparticipant"]), (0, 45, 45))

    def test_two_original_addition_tranches_and_final_remaining(self):
        for name, first_release_producer in (("basis_reserve_tranches", F(3, 2)), ("producer_holdback_tranches", 3)):
            results = list(map(self.check, chain(fixture(name)))); second, last = results[1:]
            detail = second["release_details"][0]
            self.assertEqual((detail["original_addition"], detail["opening_available"], detail["quota"], detail["released"]), (12, 8, 3, 3))
            self.assertNotEqual(detail["released"], F(8, 4))
            self.assertEqual(second["current"]["producer"], first_release_producer)
            self.assertEqual((last["release_details"][0]["basis"], last["current"]["releases"], last["closing_reserve"]), ("all_remaining", 3, 0))
            self.assertEqual(last["cumulative"]["applications"], 6); self.assertEqual(last["cumulative"]["releases"], 6)
            self.assertEqual(last["cumulative"]["fee"], 10)

    def test_tranche_original_means_actual_capped_addition_not_raw_candidate(self):
        case = fixture("basis_reserve_tranches"); case["context"]["terms"]["retained_cap"] = "12"; case["frames"][0]["receipts"][0]["gross"] = "100"; case["frames"][0]["population"]["gross_total"] = "100"
        results = chain(case); row = results[0]["receipt_details"][0]; release = results[1]["release_details"][0]
        self.assertEqual((row["raw_addition"], row["addition"], release["quota"], release["released"]), (20, 12, 3, 3))

    def test_first_tranche_is_clipped_to_unused_without_borrowing(self):
        case = fixture("basis_reserve_tranches"); case["frames"][0]["applications"][0]["amount"] = "11"; case["frames"][0]["population"]["application_total"] = "11"; remove_applications(case["frames"][1])
        results = chain(case); self.assertEqual((results[1]["release_details"][0]["quota"], results[1]["current"]["releases"]), (3, 1))
        self.assertEqual(results[2]["current"]["releases"], 0); self.assertTrue(lots(results[2])["V1"]["liquidated"])

    def test_calendar_clamp_and_reject_invalid_day_are_explicit(self):
        case = fixture("basis_reserve_tranches"); remove_applications(case["frames"][0]); remove_applications(case["frames"][1])
        case["frames"][0]["receipts"][0]["event_date"] = "2026-01-31"; case["frames"][0]["receipts"][0]["observed_at"] = "2026-01-31T12:00:00Z"
        election = case["frames"][0]["elections"][0]; election.update(event_date="2026-01-31", approved_date="2026-01-31", observed_at="2026-01-31T12:00:00Z")
        result = self.check(chain(case)[0]); self.assertEqual([row["due_date"] for row in lots(result)["V1"]["tranches"]], ["2026-02-28", "2026-04-30"])
        case["context"]["terms"]["calendar_mode"] = "reject_invalid_day"; self.reject(view(case), "RS_RELEASE_INVALID_DAY")

    def test_same_day_applications_precede_computed_due_release(self):
        second = self.check(chain(fixture())[1])
        self.assertEqual(second["application_details"][0]["closing_available"], 5)
        self.assertEqual((second["release_details"][0]["opening_available"], second["release_details"][0]["released"]), (5, 5))

    def test_all_six_actual_serialized_chains_preserve_previous_objects(self):
        for name in json.loads((ROOT / "cases/reserve-stages/neutral.json").read_text())["scenarios"]:
            case = fixture(name); previous = None
            for position in range(len(case["frames"])):
                before = deepcopy(previous)
                result = self.check(reserve_stages(view(case, position, previous)))
                self.assertEqual(previous, before); previous = result
            self.assertEqual(previous["closing_reserve"], 0)
            self.assertEqual(previous["cumulative"]["fee"], 20 if name.endswith("vintages") else 10)

    def test_replayed_due_release_and_fee_are_not_repeated_in_empty_successor(self):
        case = fixture("basis_reserve_stage"); results = chain(case)
        empty = deepcopy(fixture()["frames"][2]); empty["case_id"] = "empty-after-liquidation"; case["frames"].append(empty)
        last = self.check(chain(case)[-1]); self.assertEqual(last["current"]["fee"], 0); self.assertEqual(last["current"]["releases"], 0)
        self.assertEqual(last["cumulative"], results[-1]["cumulative"])

    def test_after_liquidation_is_a_separate_unsupported_application_variant(self):
        case = fixture(); first, second = chain(case)[:2]
        add_application(case, 2, "late-claim", "V1", "1", "2026-07-01", "1", 0)
        self.reject(view(case, 2, second), "RS_AFTER_TERM_APPLICATION_VARIANT_REQUIRED")

    def test_application_ids_refs_and_authorities_are_consumed(self):
        original = fixture("basis_reserve_tranches"); first = reserve_stages(view(original))
        for kind in ("id", "reference", "authority"):
            case = deepcopy(original); old_app = case["frames"][0]["applications"][0]; new_app = case["frames"][1]["applications"][0]
            if kind == "id":
                new_app["id"] = old_app["id"]; case["frames"][1]["authorities"][0]["application_id"] = old_app["id"]; case["frames"][1]["population"]["application_ids"] = [old_app["id"]]
            elif kind == "reference": new_app["original_ref"] = old_app["original_ref"]
            else:
                old_id = case["frames"][0]["authorities"][0]["id"]; case["frames"][1]["authorities"][0]["id"] = old_id; new_app["authority_id"] = old_id; case["frames"][1]["population"]["authority_ids"] = [old_id]
            self.reject(view(case, 1, first), "RS_AUTHORITY_REUSE" if kind == "authority" else "RS_APPLICATION_REUSE")

    def test_old_receipt_ref_and_vintage_cannot_be_relabelled_for_new_fees(self):
        original = fixture(); first = reserve_stages(view(original))
        for kind in ("receipt_ref", "receipt_id", "vintage", "election"):
            case = deepcopy(original); frame = case["frames"][1]
            if kind == "receipt_ref": frame["receipts"][0]["original_ref"] = case["frames"][0]["receipts"][0]["original_ref"]
            elif kind == "receipt_id":
                frame["receipts"][0]["id"] = "receipt:V1"; frame["elections"][0]["receipt_id"] = "receipt:V1"; frame["population"]["receipt_ids"] = ["receipt:V1"]
            elif kind == "vintage": frame["elections"][0]["vintage_id"] = "V1"
            else: frame["elections"][0]["id"] = case["frames"][0]["elections"][0]["id"]; frame["population"]["election_ids"] = [frame["elections"][0]["id"]]
            self.reject(view(case, 1, first), "RS_ORIGINAL_REUSE")

    def test_missing_unknown_and_nonbijective_original_populations(self):
        for field, value in (("complete", False), ("receipt_ids", []), ("gross_total", "0"), ("election_ids", ["unknown"])):
            data = view(fixture()); data["population"][field] = value; self.reject(data)
        data = view(fixture()); data["elections"] = []; data["population"]["election_ids"] = []; self.reject(data, "RS_COMPLETE_ELECTIONS")

    def test_application_authority_scope_purpose_approval_and_links(self):
        case = fixture(); first = reserve_stages(view(case))
        for field, value in (("vintage_id", "V2"), ("approved", False), ("reserve_measure", "other-purpose"), ("approved_date", "9999-12-31")):
            data = view(case, 1, first); data["authorities"][0][field] = value; self.reject(data, "RS_APPLICATION_AUTHORITY")
        data = view(case, 1, first); data["applications"][0]["vintage_id"] = "missing"; data["authorities"][0]["vintage_id"] = "missing"; self.reject(data, "RS_UNKNOWN_VINTAGE")
        data = view(case, 1, first); data["applications"][0]["scope"]["pool_id"] = "other"; self.reject(data, "RS_FACT_SCOPE")
        data = view(case, 1, first); data["authorities"][0]["observed_at"] = "2026-03-31T23:59:59Z"
        selected = next(row for row in data["evidence"] if row["id"] == data["authorities"][0]["evidence_ref"]); selected["observed_at"] = data["authorities"][0]["observed_at"]
        self.reject(data, "RS_APPLICATION_AUTHORITY")

    def test_unused_evidence_must_still_be_valid_and_known(self):
        data = view(fixture()); extra = deepcopy(data["evidence"][0]); extra.update(id="unused", approved=False); data["evidence"].append(extra); self.reject(data, "RS_EVIDENCE_SCOPE_APPROVAL_CUTOFF")
        data = view(fixture()); extra = deepcopy(data["registry_evidence"][0]); extra.update(id="unused-registry", observed_at=data["cutoff"]); data["registry_evidence"].append(extra); self.reject(data, "RS_EVIDENCE_SCOPE_APPROVAL_CUTOFF")

    def test_static_registry_uses_minimum_cutoff_without_monotone_assumption(self):
        case = fixture(); case["frames"][0]["cutoff"] = "2027-01-01T00:00:00Z"
        extra = deepcopy(case["context"]["registry_evidence"][0]); extra.update(id="unused-later-registry", observed_at="2026-08-01T00:00:00Z"); case["context"]["registry_evidence"].append(extra)
        first = self.check(reserve_stages(view(case)))
        self.reject(view(case, 1, first), "RS_EVIDENCE_SCOPE_APPROVAL_CUTOFF")

    def test_explicit_finite_table_and_vintage_bounds(self):
        data = view(fixture()); data["evidence"] = [dict(deepcopy(data["evidence"][0]), id="evidence-" + str(number)) for number in range(33)]
        self.reject(data, "RS_ROW_BOUND")
        data = view(fixture()); data["opening_state"] = {"origin": "prior_result", "history": [{}] * 4}
        self.reject(data, "RS_HISTORY_BOUND")
        data = view(fixture()); data["terms"]["release_schedule"] *= 3; self.reject(data, "RS_RELEASE_SCHEDULE")
        data = view(fixture()); receipt, election = deepcopy(data["receipts"][0]), deepcopy(data["elections"][0]); original_evidence = {row["id"]: row for row in data["evidence"]}
        data["receipts"] = []; data["elections"] = []; data["evidence"] = [row for row in data["evidence"] if row["id"] == data["population"]["evidence_ref"]]
        for number in range(5):
            new_receipt, new_election = deepcopy(receipt), deepcopy(election)
            new_receipt.update(id="new-receipt-" + str(number), original_ref="new-original-" + str(number), sequence=number)
            new_election.update(id="new-election-" + str(number), receipt_id=new_receipt["id"], vintage_id="new-vintage-" + str(number))
            for row in (new_receipt, new_election):
                ev = deepcopy(original_evidence[row["evidence_ref"]]); ev["id"] = row["evidence_ref"] + "-" + str(number); row["evidence_ref"] = ev["id"]; data["evidence"].append(ev)
            data["receipts"].append(new_receipt); data["elections"].append(new_election)
        data["population"].update(receipt_ids=[row["id"] for row in data["receipts"]], election_ids=[row["id"] for row in data["elections"]], gross_total="300")
        self.reject(data, "RS_VINTAGE_BOUND")

    def test_scope_currency_and_stage_units_cannot_mix(self):
        data = view(fixture()); data["scope"]["currency"] = "CAD"; self.reject(data, "RS_SCOPE_STAGE_UNIT")
        data = view(fixture()); data["policy"] = policy("producer_holdback"); self.reject(data, "RS_SCOPE_STAGE_UNIT")
        data = view(fixture()); data["terms"]["reserve_measure"] = "producer_entitlement_USD"; self.reject(data, "RS_SCOPE_STAGE_UNIT")

    def test_context_cap_fee_schedule_and_scope_changes_during_carry_reject(self):
        case = fixture(); first = reserve_stages(view(case))
        for field, value in (("retained_cap", "33"), ("fixed_fee", "9"), ("version", "2")):
            data = view(case, 1, first); data["terms"][field] = value; self.reject(data, "RS_PINNED_CONTEXT")
        data = view(case, 1, first); data["terms"]["release_schedule"][0]["offset_months"] = 4; self.reject(data, "RS_PINNED_CONTEXT")

    def test_opening_balances_consumption_and_historical_results_are_replayed(self):
        case = fixture("basis_reserve_tranches"); first = reserve_stages(view(case))
        for kind in ("balance", "fee", "tranche", "consumed", "historical"):
            data = view(case, 1, first)
            if kind == "balance": data["opening_state"]["vintages"][0]["available"] = "999"
            elif kind == "fee": data["opening_state"]["cumulative"]["fee"] = "0"
            elif kind == "tranche": data["opening_state"]["vintages"][0]["tranches"][0]["processed"] = True
            elif kind == "consumed": data["opening_state"]["consumed_application_ids"] = []
            else: data["opening_state"]["history"][0]["result"]["current"]["producer"] = "0"
            data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
            self.reject(data, "RS_HISTORY_FINANCIAL_REPLAY" if kind == "historical" else "RS_OPENING_RECONCILIATION")

    def test_actual_predecessor_summary_and_adjacent_boundaries_are_required(self):
        case = fixture(); first = reserve_stages(view(case))
        data = view(case, 1, first); del data["prior_result"]; self.reject(data, "RS_PREDECESSOR_REQUIRED")
        data = view(case, 1, first); data["prior_result"]["source_case_id"] = "wrong"; self.reject(data, "RS_PREDECESSOR_MISMATCH")
        data = view(case, 1, first); data["prior_result"]["period"]["start"] = "2025-12-31"; self.reject(data, "RS_PREDECESSOR_MISMATCH")
        data = view(case, 1, first); data["period"]["start"] = "2026-04-02"; self.reject(data)

    def test_unconditional_synthetic_release_never_infers_sourced_claim_clearance(self):
        last = self.check(chain(fixture("basis_reserve_tranches"))[-1])
        self.assertFalse(last["source_clearance_inferred"]); self.assertEqual(last["closing_reserve"], 0)
        data = view(fixture()); data["terms"]["claim_active_clearance"] = True; self.reject(data, "RS_FIELDS")

    def test_no_election_zero_rate_and_zero_gross_fee_are_explicit(self):
        case = fixture("basis_reserve_stage"); case["frames"][0]["elections"][0]["elected"] = False
        self.assertEqual(chain(case)[0]["current"]["producer"], 45)
        case = fixture("basis_reserve_stage"); case["context"]["terms"]["reserve_rate"] = "0"; self.assertEqual(chain(case)[0]["current"]["additions"], 0)
        case = fixture("basis_reserve_stage"); case["context"]["terms"]["fixed_fee"] = "0"; case["frames"][0]["receipts"][0]["gross"] = "0"; case["frames"][0]["population"]["gross_total"] = "0"
        self.assertEqual(chain(case)[0]["current"]["producer"], 0)

    def test_fixed_fee_funding_insufficiency_is_not_silently_floored(self):
        case = fixture("basis_reserve_stage"); case["frames"][0]["receipts"][0]["gross"] = "10"; case["frames"][0]["population"]["gross_total"] = "10"
        self.reject(view(case), "RS_FIXED_FEE_FUNDING_VARIANT_REQUIRED")

    def test_exact_fractional_stage_difference_and_bridges(self):
        outputs = []
        for name, expected in (("basis_reserve_stage", F(1, 12)), ("producer_holdback_stage", F(7, 75))):
            case = fixture(name); case["context"]["terms"]["fixed_fee"] = "0.1"; gross = {"numerator": "1", "denominator": "3"}; case["frames"][0]["receipts"][0]["gross"] = gross; case["frames"][0]["population"]["gross_total"] = deepcopy(gross)
            results = list(map(self.check, chain(case))); self.assertEqual(results[0]["current"]["producer"], expected); self.assertEqual(results[-1]["cumulative"]["producer"], F(7, 60)); outputs.append(expected)
        self.assertEqual(outputs[1] - outputs[0], F(1, 100))

    def test_exact_cutoffs_offsets_submicroseconds_and_unknown_local_offset_labels(self):
        data = view(fixture()); data["receipts"][0]["observed_at"] = data["cutoff"]; self.reject(data, "RS_SOURCE_OBSERVATION")
        data = view(fixture()); data["cutoff"] = "2026-04-03t00:00:00-00:00"; result = self.check(reserve_stages(data)); self.assertIn("frames.0.cutoff", result["unknown_local_offset_paths"])
        data = view(fixture()); data["receipts"][0]["observed_at"] = "2026-01-01t13:00:00.000000000001+01:00"; data["elections"][0]["observed_at"] = data["receipts"][0]["observed_at"]; self.check(reserve_stages(data))

    def test_strict_numeric_temporal_schedule_and_original_answer_fields(self):
        for value in (-1, "-1", .2, True, "1e3", "1/3", {"numerator": "2", "denominator": "4"}):
            data = view(fixture()); data["terms"]["reserve_rate"] = value; self.reject(data)
        for value in (0, -1, True, 25):
            data = view(fixture()); data["terms"]["release_schedule"][0]["offset_months"] = value; self.reject(data, "RS_RELEASE_SCHEDULE")
        for value in ("2026-01-01T12:00:00", "2026-01-01T00:00:60Z", "0001-01-01T00:00:00+23:59"):
            data = view(fixture()); data["terms"]["observed_at"] = value; self.reject(data, "RS_INSTANT")
        data = view(fixture()); data["receipts"][0]["solved_addition"] = "12"; self.reject(data, "RS_FIELDS")

    def test_unresolved_same_stage_order_and_physical_permutation(self):
        case = fixture(); first = reserve_stages(view(case)); frame = case["frames"][1]
        add_application(case, 1, "another-zero-application", "V1", "0", "2026-04-01", "7", 0)
        self.reject(view(case, 1, first), "RS_UNRESOLVED_STAGE_ORDER")
        frame["applications"][1]["sequence"] = 1
        before = self.check(reserve_stages(view(case, 1, first)))
        for key in ("receipts", "elections", "applications", "authorities", "evidence"): frame[key].reverse()
        after = self.check(reserve_stages(view(case, 1, first)))
        self.assertEqual({key: value for key, value in after.items() if key != "closing_state"}, {key: value for key, value in before.items() if key != "closing_state"})
        self.assertNotEqual(after["closing_state"]["history"][-1]["facts"], before["closing_state"]["history"][-1]["facts"])
        self.assertEqual(after["closing_state"]["history"][-1]["facts"], {key: frame[key] for key in after["closing_state"]["history"][-1]["facts"]})

    def test_unicode_originals_and_input_previous_result_nonmutation(self):
        case = fixture("basis_reserve_stage")
        def rename(value):
            if isinstance(value, dict): return {key: rename(item) for key, item in value.items()}
            if isinstance(value, list): return [rename(item) for item in value]
            return "participant:e\u0301/\u96ea:#\x00" if value == "participant" else value
        case = rename(case); data = view(case); before = deepcopy(data); result = self.check(reserve_stages(data)); self.assertEqual(data, before)
        old = deepcopy(result); self.check(reserve_stages(view(case, 1, result))); self.assertEqual(result, old)
        self.assertEqual(result["closing_state"]["scope"]["participant_id"], "participant:e\u0301/\u96ea:#\x00")

    def test_only_standard_library_and_no_implementation_oracle_io_dependency(self):
        tree = ast.parse((ROOT / "oracles/reserve_stages.py").read_text(encoding="utf-8"))
        imports = {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)} | {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertEqual(imports, {"copy", "datetime", "fractions", "calendar", "re"})
        self.assertFalse({node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)} & {"open", "eval", "exec", "__import__"})


if __name__ == "__main__": unittest.main()
