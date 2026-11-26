"""Independent hand and original-history controls for entitlement burdens."""
import ast
from copy import deepcopy
from fractions import Fraction as F
import json
from pathlib import Path
import unittest

from oracles.contract_burdens import ContractBurdenOracleError, contract_burdens, exact_json, policy

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/entitlement-burdens/neutral.json").read_text(encoding="utf-8"))


def paid_method(data):
    data["policy"] = policy("paid_basis_current_period")
    for auth in data["authorizations"]: auth["basis_kind"] = data["policy"]["method"]
    return data


def remove_payments(data, *, complete_empty=False):
    data["payments"] = []; data["applications"] = []
    if complete_empty:
        for pop in data["payment_populations"]: pop.update(payment_ids=[], application_ids=[], paid_total="0")
    else: data["payment_populations"] = []
    return data


def successor(original, previous, quarter):
    """Transport fresh original facts plus an actual serialized oracle predecessor."""
    data = deepcopy(original)
    labels = {2: ("q2", "06", "07", "2026-04-01", "2026-07-01", "2026-06-30"),
              3: ("q3", "09", "10", "2026-07-01", "2026-10-01", "2026-09-30")}
    label, month, next_month, start, end, as_of = labels[quarter]
    changes = {"2026-03-31": as_of, "2026-03-": "2026-" + month + "-", "2026-04-": "2026-" + next_month + "-", "q1": label}
    def rewrite(value):
        if isinstance(value, dict): return {k: rewrite(v) for k, v in value.items()}
        if isinstance(value, list): return [rewrite(v) for v in value]
        if isinstance(value, str):
            for old, new in changes.items(): value = value.replace(old, new)
        return value
    static_evidence = {row["evidence_ref"] for key in ("accounts", "terms", "authorizations") for row in data[key]}
    for key in ("receipts", "requests", "payments", "applications", "receipt_populations", "payment_populations"):
        data[key] = rewrite(data[key])
    data["evidence"] = [row if row["id"] in static_evidence else rewrite(row) for row in data["evidence"]]
    data.update(case_id="burden-" + label, period={"start": start, "end": end}, as_of=as_of, cutoff=end[:8] + "03T00:00:00Z")
    for key in ("receipt_populations", "payment_populations"):
        for pop in data[key]: pop["period"] = deepcopy(data["period"])
    transported = json.loads(json.dumps(exact_json(previous)))
    data["opening_state"] = transported["closing_state"]
    data["prior_result"] = {"source_case_id": transported["source_case_id"], "period": transported["period"],
                            "closing_state": transported["closing_state"], "result_ref": "supplied-result-reference#" + transported["source_case_id"]}
    return data


def accounts(result):
    return {row["id"]: row for row in result["account_results"]}


def add_supported(data, row, kind, endpoint_ids):
    row = deepcopy(row); row["evidence_ref"] = "evidence:" + row["id"]; row["source_ref"] = "original-source:" + row["id"]
    data["evidence"].append({"id": row["evidence_ref"], "coordinator_id": data["coordinator"]["id"], "account_ids": endpoint_ids,
                             "kind": kind, "approved": True, "observed_at": row["observed_at"], "source_ref": "original-evidence:" + row["id"]})
    return row


class ContractBurdenOracleTests(unittest.TestCase):
    def reject(self, data, code):
        before = deepcopy(data)
        with self.assertRaisesRegex(ContractBurdenOracleError, "^" + code + "$"): contract_burdens(data)
        self.assertEqual(data, before)  # Failed calculation does not partially mutate supplied state.

    def test_original_accruals_burden_and_payment_are_different_measures(self):
        result = contract_burdens(fixture()); a = accounts(result)
        self.assertEqual((a["claimant"]["original_gross_basis"], a["claimant"]["original_accrued"], a["claimant"]["actual_paid"]), (200, 100, 60))
        self.assertEqual((a["claimant"]["adjusted_entitlement"], a["burdened"]["original_accrued"], a["burdened"]["adjusted_entitlement"]), (100, 200, 170))
        self.assertEqual(result["original_entitlement_total"], 300)
        self.assertEqual(result["adjusted_entitlement_total"], 270)
        self.assertEqual(result["applied_burden_total"], 30)
        self.assertFalse(result["bank_movement_created"])
        self.assertEqual(a["claimant"]["claimant_credit_added"], 0)
        self.assertIsNone(a["burdened"]["actual_paid"])
        detail = result["burden_details"][0]
        self.assertEqual((detail["basis"], detail["requested"], detail["applied"], detail["cap_remaining_after"]), (100, 30, 30, 15))
        self.assertEqual(result["receipt_details"][1]["derived_participation_entitlement"], 100)
        self.assertNotEqual((a["claimant"]["adjusted_entitlement"], a["burdened"]["adjusted_entitlement"]), (70, 230))

    def test_paid_basis_uses_linked_actual_participation_payment(self):
        result = contract_burdens(paid_method(fixture())); a = accounts(result)
        self.assertEqual((a["claimant"]["original_accrued"], a["claimant"]["actual_paid"], a["claimant"]["adjusted_entitlement"]), (100, 60, 100))
        self.assertEqual((result["burden_details"][0]["basis"], result["applied_burden_total"], a["burdened"]["adjusted_entitlement"]), (60, 18, 182))
        self.assertEqual(result["payment_application_details"][0]["derived_participation_limit"], 100)

    def test_paid_is_limited_by_derived_participation_not_gross_receipts(self):
        data = fixture(); data["payments"][0]["amount"] = "101"; data["applications"][0]["amount"] = "101"; data["payment_populations"][0]["paid_total"] = "101"
        self.reject(data, "BURDEN_PAID_EXCEEDS_PARTICIPATION_ENTITLEMENT")  # Gross200 is not owner entitlement100.
        for key in ("payments", "applications"): data[key][0]["amount"] = "100"
        data["payment_populations"][0]["paid_total"] = "100"
        self.assertEqual(contract_burdens(paid_method(data))["applied_burden_total"], 30)

    def test_missing_payment_view_unknown_accrual_valid_paid_basis_blocks(self):
        data = remove_payments(fixture())
        result = contract_burdens(data)
        self.assertIsNone(accounts(result)["claimant"]["actual_paid"])
        self.assertEqual(accounts(result)["claimant"]["payment_evidence_status"], "no_event_supplied")
        self.assertEqual(result["applied_burden_total"], 30)
        self.reject(paid_method(data), "BURDEN_PAID_BASIS_UNKNOWN")

    def test_complete_empty_payment_view_supports_zero_and_preserves_request(self):
        result = contract_burdens(paid_method(remove_payments(fixture(), complete_empty=True)))
        self.assertEqual(accounts(result)["claimant"]["actual_paid"], 0)
        self.assertEqual(result["applied_burden_total"], 0)
        self.assertEqual(accounts(result)["burdened"]["adjusted_entitlement"], 200)
        self.assertEqual(result["closing_state"]["consumed"]["request_ids"], ["request:q1"])

    def test_empty_original_receipt_populations_and_no_requests(self):
        data = remove_payments(fixture(), complete_empty=True); data["receipts"] = []; data["requests"] = []
        for pop in data["receipt_populations"]: pop.update(receipt_ids=[], gross_total="0")
        result = contract_burdens(data)
        self.assertEqual((result["original_entitlement_total"], result["applied_burden_total"], result["adjusted_entitlement_total"]), (0, 0, 0))
        self.assertEqual(result["closing_state"]["cap_usage"], [{"authorization_id": "authority:burden", "cap_limit": "45", "consumed": "0", "remaining": "45"}])

    def test_zero_and_exact_fraction_no_implicit_rounding(self):
        data = fixture(); data["authorizations"][0]["burden_rate"] = "0"
        self.assertEqual(contract_burdens(data)["applied_burden_total"], 0)
        data = remove_payments(fixture(), complete_empty=True)
        data["receipts"][0]["amount"] = "2/3"; data["receipt_populations"][0]["gross_total"] = "2/3"
        result = contract_burdens(data)
        self.assertEqual(result["burden_details"][0]["basis"], F(1, 3))
        self.assertEqual(result["applied_burden_total"], F(1, 10))
        self.assertEqual(accounts(result)["burdened"]["adjusted_entitlement"], F(1999, 10))

    def test_minimum_basis_equality_and_just_below(self):
        data = fixture(); data["authorizations"][0]["minimum_basis"] = "100"
        self.assertEqual(contract_burdens(data)["applied_burden_total"], 30)
        data["authorizations"][0]["minimum_basis"] = "100.0000000001"
        result = contract_burdens(data)
        self.assertEqual(result["applied_burden_total"], 0)
        self.assertFalse(result["burden_details"][0]["eligible"])
        self.assertEqual(result["closing_state"]["consumed"]["request_ids"], ["request:q1"])

    def test_cap_equality_and_explicit_cap_excess(self):
        data = fixture(); data["authorizations"][0]["cap"] = "30"
        result = contract_burdens(data)
        self.assertEqual((result["applied_burden_total"], result["burden_details"][0]["cap_remaining_after"]), (30, 0))
        data["authorizations"][0]["cap"] = "29"
        result = contract_burdens(data)
        self.assertEqual((result["applied_burden_total"], result["burden_details"][0]["cap_excess_not_carried"]), (29, 1))
        self.assertEqual(accounts(result)["burdened"]["adjusted_entitlement"], 171)

    def test_target_shortfall_atomic_and_cap_precedes_availability_check(self):
        data = fixture(); data["receipts"][1]["amount"] = "40"; data["receipt_populations"][1]["gross_total"] = "40"
        self.reject(data, "BURDEN_TARGET_SHORTFALL_ATOMIC")
        data["authorizations"][0]["cap"] = "10"
        result = contract_burdens(data)
        self.assertEqual((result["applied_burden_total"], accounts(result)["burdened"]["adjusted_entitlement"]), (10, 10))

    def test_three_actual_serialized_periods_cap45_chain_30_15_0(self):
        original = fixture(); first = contract_burdens(original)
        second_input = successor(original, first, 2); second = contract_burdens(second_input)
        third_input = successor(original, second, 3); third = contract_burdens(third_input)
        self.assertEqual([r["applied_burden_total"] for r in (first, second, third)], [30, 15, 0])
        self.assertEqual([accounts(r)["burdened"]["adjusted_entitlement"] for r in (first, second, third)], [170, 185, 200])
        self.assertEqual([r["burden_details"][0]["cap_excess_not_carried"] for r in (first, second, third)], [0, 15, 30])
        self.assertEqual([r["closing_state"]["cap_usage"][0]["consumed"] for r in (first, second, third)], ["30", "45", "45"])
        self.assertEqual([accounts(r)["claimant"]["original_accrued"] for r in (first, second, third)], [100, 100, 100])
        self.assertEqual(len(third["closing_state"]["history"]), 3)
        self.assertEqual(third["closing_state"]["history"][0]["facts"]["receipts"], original["receipts"])
        self.assertEqual(exact_json(contract_burdens(second_input)), exact_json(second))

    def test_original_immutable_period_replay_does_not_consume_twice(self):
        data = fixture()
        self.assertEqual(exact_json(contract_burdens(data)), exact_json(contract_burdens(deepcopy(data))))
        self.assertEqual(contract_burdens(data)["closing_state"]["cap_usage"][0]["consumed"], "30")

    def test_relabelled_request_and_measurement_cannot_repeat_same_canonical_charge(self):
        data = fixture(); extra = deepcopy(data["requests"][0]); extra.update(id="different-request", measurement_id="different-basis-name", original_ref="other-ledger#other-request")
        data["requests"].append(extra)
        self.reject(data, "BURDEN_REPLAY_SEMANTIC_KEYS")

    def test_duplicate_receipt_id_and_upstream_aliases(self):
        data = fixture(); data["receipts"].append(deepcopy(data["receipts"][0])); self.reject(data, "BURDEN_DUPLICATE_ID")
        for alias in ("original_ref", "entitlement_line_ref"):
            data = fixture(); clone = deepcopy(data["receipts"][0]); clone["id"] = "new-row-id"
            if alias == "entitlement_line_ref": clone["original_ref"] = "new-receipt-ledger#different-line"
            data["receipts"].append(clone)
            self.reject(data, "BURDEN_REPLAY_" + ("RECEIPT_REFS" if alias == "original_ref" else "ENTITLEMENT_REFS"))

    def test_adjacent_original_receipt_payment_and_request_aliases_block(self):
        original = fixture(); first = contract_burdens(original)
        for key, field, code in [("receipts", "original_ref", "BURDEN_REPLAY_RECEIPT_REFS"),
                                 ("payments", "original_ref", "BURDEN_REPLAY_PAYMENT_REFS"),
                                 ("requests", "original_ref", "BURDEN_REPLAY_REQUEST_REFS")]:
            data = successor(original, first, 2); data[key][0][field] = original[key][0][field]
            self.reject(data, code)

    def test_authority_alias_unknown_scope_and_same_agreement(self):
        data = fixture(); data["authorizations"].append({**deepcopy(data["authorizations"][0]), "id": "aliased-authority", "sequence": 2})
        self.reject(data, "BURDEN_AUTHORITY_ALIAS")
        data = fixture(); data["requests"][0]["authorization_id"] = "unknown"; self.reject(data, "BURDEN_UNKNOWN_AUTHORITY")
        data = fixture(); data["authorizations"][0]["burdened_scope"]["agreement_id"] = "other"; self.reject(data, "BURDEN_AUTHORITY_SCOPE")
        def change(value):
            if isinstance(value, dict): return {k: change(v) for k, v in value.items()}
            if isinstance(value, list): return [change(v) for v in value]
            return "agreement-claimant" if value == "agreement-burdened" else value
        self.reject(change(fixture()), "BURDEN_CROSS_AGREEMENT_REQUIRED")

    def test_future_approval_effective_end_and_boundary_approval_equality(self):
        data = fixture(); data["authorizations"][0]["approved_date"] = "2026-04-01"; self.reject(data, "BURDEN_AUTHORITY_APPROVAL")
        data = fixture(); data["authorizations"][0]["effective"]["start"] = "2026-04-01"; self.reject(data, "BURDEN_AUTHORITY_EFFECTIVE_OBSERVATION")
        data = fixture(); data["authorizations"][0]["effective"]["end"] = "2026-03-31"; self.reject(data, "BURDEN_AUTHORITY_EFFECTIVE_OBSERVATION")
        data = fixture(); auth = data["authorizations"][0]
        auth.update(approved_date="2026-03-31", recorded_date="2026-03-31", observed_at="2026-04-01T00:00:00Z")
        self.assertEqual(contract_burdens(data)["applied_burden_total"], 30)

    def test_cutoff_equality_missing_evidence_and_exact_offset_lexemes(self):
        data = fixture(); data["requests"][0]["observed_at"] = data["cutoff"]; self.reject(data, "BURDEN_SOURCE_OBSERVATION")
        data = fixture(); data["receipts"][0]["evidence_ref"] = "missing"; self.reject(data, "BURDEN_EVIDENCE_REQUIRED")
        data = fixture(); raw = "2026-04-01T17:00:00.0000000001-07:00"; data["requests"][0]["observed_at"] = raw
        result = contract_burdens(data)
        self.assertEqual(result["closing_state"]["history"][0]["facts"]["requests"][0]["observed_at"], raw)

    def test_missing_complete_receipt_view_and_payment_application_conservation(self):
        data = fixture(); data["receipt_populations"] = []; self.reject(data, "BURDEN_COMPLETE_RECEIPT_POPULATION_REQUIRED")
        data = fixture(); data["payment_populations"] = []; self.reject(data, "BURDEN_COMPLETE_PAYMENT_POPULATION_REQUIRED")
        data = fixture(); data["applications"][0]["amount"] = "59"; self.reject(data, "BURDEN_PAYMENT_APPLICATION_CONSERVATION")
        data = fixture(); data["applications"][0]["entitlement_line_ref"] = data["receipts"][0]["original_ref"]
        self.reject(data, "BURDEN_APPLICATION_SCOPE_LINEAGE")

    def test_application_cannot_precede_actual_participation_payment(self):
        data = fixture(); data["applications"][0]["application_date"] = "2026-03-09"
        self.reject(data, "BURDEN_APPLICATION_CHRONOLOGY")

    def test_predecessor_raw_history_cap_and_registry_are_verified(self):
        original = fixture(); first = contract_burdens(original)
        data = successor(original, first, 2); del data["prior_result"]; self.reject(data, "BURDEN_PREDECESSOR_REQUIRED")
        data = successor(original, first, 2); data["prior_result"]["source_case_id"] = "wrong"; self.reject(data, "BURDEN_PREDECESSOR_MISMATCH")
        data = successor(original, first, 2); data["opening_state"]["cap_usage"][0]["consumed"] = "0"; self.reject(data, "BURDEN_OPENING_RECONCILIATION")
        data = successor(original, first, 2); data["opening_state"]["history"][0]["result"]["applied_burden_total"] = "0"
        self.reject(data, "BURDEN_HISTORY_FINANCIAL_REPLAY")
        data = successor(original, first, 2); data["authorizations"][0]["cap"] = "60"; self.reject(data, "BURDEN_REGISTRY_AMENDMENT_OR_RESET")

    def test_current_paid_basis_cannot_reopen_old_receipt_for_later_payment(self):
        original = paid_method(fixture()); first = contract_burdens(original)
        data = successor(original, first, 2); data["applications"][0]["receipt_id"] = original["receipts"][0]["id"]
        self.reject(data, "BURDEN_CURRENT_PARTICIPATION_REFERENCE")

    def test_complete_population_and_measurement_observation_order(self):
        data = fixture(); data["payment_populations"][0]["complete"] = False
        self.reject(data, "BURDEN_COMPLETE_PAYMENT_POPULATION_REQUIRED")
        data = fixture(); data["requests"][0]["observed_at"] = "2026-03-30T00:00:00Z"
        next(e for e in data["evidence"] if e["id"] == data["requests"][0]["evidence_ref"])["observed_at"] = data["requests"][0]["observed_at"]
        self.reject(data, "BURDEN_REQUEST_OBSERVATION")
        data = fixture(); pop = data["receipt_populations"][0]; pop["observed_at"] = "2026-03-01T00:00:00Z"
        next(e for e in data["evidence"] if e["id"] == pop["evidence_ref"])["observed_at"] = pop["observed_at"]
        self.reject(data, "BURDEN_POPULATION_OBSERVATION")

    def test_late_genesis_cannot_silently_reset_original_authority_cap(self):
        first = contract_burdens(fixture()); data = successor(fixture(), first, 2)
        data["opening_state"] = {"origin": "genesis", "boundary": data["period"]["start"], "source_case_id": "genesis", "history": []}; del data["prior_result"]
        self.reject(data, "BURDEN_GENESIS_CAP_BOUNDARY")

    def test_graph_cycle_is_rejected_even_for_unused_authority(self):
        data = fixture(); reverse = deepcopy(data["authorizations"][0]); reverse.update(id="reverse", sequence=2, original_ref="other-contract-authority#reverse",
            claimant_account="burdened", burdened_account="claimant", claimant_scope=data["accounts"][1]["scope"], burdened_scope=data["accounts"][0]["scope"])
        data["authorizations"].append(add_supported(data, reverse, "cross_contract_authority", ["claimant", "burdened"]))
        self.reject(data, "BURDEN_CYCLIC_DEPENDENCY")

    def test_original_pre_burden_graph_basis_not_adjusted_endpoint_feedback(self):
        data = fixture(); third = deepcopy(data["accounts"][1]); third["id"] = "third"
        third["scope"] = {k: ("USD" if k == "currency" else v.replace("burdened", "third")) for k,v in third["scope"].items()}
        data["accounts"].append(add_supported(data, third, "account_scope", ["third"]))
        term = deepcopy(data["terms"][1]); term.update(id="terms:third", account_id="third", scope=third["scope"], original_ref="original-contract#third")
        data["terms"].append(add_supported(data, term, "participation_terms", ["third"]))
        receipt = deepcopy(data["receipts"][1]); receipt.update(id="receipt:third:q1", account_id="third", scope=third["scope"], amount="600", term_id="terms:third",
            original_ref="original-receipts#third", entitlement_line_ref="original-participation#third")
        data["receipts"].append(add_supported(data, receipt, "original_receipt_basis", ["third"]))
        pop = deepcopy(data["receipt_populations"][1]); pop.update(id="population:third", account_id="third", scope=third["scope"], receipt_ids=[receipt["id"]], gross_total="600")
        data["receipt_populations"].append(add_supported(data, pop, "complete_receipt_population", ["third"]))
        auth = deepcopy(data["authorizations"][0]); auth.update(id="authority:second", claimant_account="burdened", burdened_account="third", claimant_scope=data["accounts"][1]["scope"],
            burdened_scope=third["scope"], sequence=2, burden_rate="0.1", cap="30", original_ref="original-cross-contract#second")
        data["authorizations"].append(add_supported(data, auth, "cross_contract_authority", ["burdened", "third"]))
        request = deepcopy(data["requests"][0]); request.update(id="request:second", authorization_id=auth["id"], claimant_account="burdened", burdened_account="third",
            claimant_scope=auth["claimant_scope"], burdened_scope=auth["burdened_scope"], basis_receipt_ids=[data["receipts"][1]["id"]], original_ref="original-requests#second")
        data["requests"].append(add_supported(data, request, "original_burden_request", ["burdened", "third"]))
        result = contract_burdens(data)
        self.assertEqual([row["basis"] for row in result["burden_details"]], [100, 200])
        self.assertEqual([row["applied"] for row in result["burden_details"]], [30, 20])
        self.assertEqual([accounts(result)[key]["adjusted_entitlement"] for key in ["claimant", "burdened", "third"]], [100, 170, 280])
        self.assertNotEqual(accounts(result)["third"]["adjusted_entitlement"], 283)

    def test_text_ids_are_not_trimmed_normalized_or_treated_as_declared_ascii_ids(self):
        data = remove_payments(fixture(), complete_empty=True)
        first = deepcopy(data["receipts"][0]); second = deepcopy(first)
        first.update(id="é", amount="100", original_ref="original-receipts#é", entitlement_line_ref="participation#é")
        second.update(id="e\u0301", amount="100", original_ref="original-receipts#e\u0301", entitlement_line_ref="participation#e\u0301")
        data["receipts"] = [first, second, data["receipts"][1]]
        data["receipt_populations"][0]["receipt_ids"] = ["é", "e\u0301"]; data["requests"][0]["basis_receipt_ids"] = ["é", "e\u0301"]
        result = contract_burdens(data)
        self.assertEqual(result["applied_burden_total"], 30)
        self.assertEqual(result["closing_state"]["consumed"]["receipt_ids"], ["e\u0301", "receipt:burdened:q1", "é"])
        self.assertEqual([r["id"] for r in result["closing_state"]["history"][0]["facts"]["receipts"][:2]], ["é", "e\u0301"])

    def test_permutation_preserves_financial_results_and_no_compiler_imports(self):
        data = fixture(); reversed_data = deepcopy(data)
        for key,value in reversed_data.items():
            if isinstance(value, list): value.reverse()
        first, second = contract_burdens(data), contract_burdens(reversed_data)
        self.assertEqual({k:v for k,v in first.items() if k != "closing_state"}, {k:v for k,v in second.items() if k != "closing_state"})
        tree = ast.parse((ROOT / "oracles/contract_burdens.py").read_text(encoding="utf-8"))
        imported = {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        imported |= {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imported, {"copy", "datetime", "fractions", "re"})


if __name__ == "__main__": unittest.main()
