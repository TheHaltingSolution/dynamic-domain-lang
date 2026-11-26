"""Hand controls for independent original revision and authorized recovery."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.authorized_offsets import AuthorizedOffsetOracleError, authorized_offsets, exact_json


ROOT = Path(__file__).resolve().parents[1]
ARRAYS = ("reversals", "revision_authorities", "offset_authorities", "future_earnings", "cash_recoveries", "recovery_applications")


def fixture():
    return json.loads((ROOT / "cases/authorized-offsets/neutral.json").read_text(encoding="utf-8"))


def control(data, kind, period=None):
    return next(row for row in data["evidence"] if row["kind"] == kind and (period is None or row.get("period") == period))


def pin_bundle(data):
    data["opening_state"]["original_bundle"] = deepcopy(data["original_bundle"])


def payment(data, amount):
    snapshot = data["original_bundle"]["payment_snapshot"]
    if Fraction(amount):
        snapshot["payments"][0]["amount"] = snapshot["applications"][0]["amount"] = amount
    else:
        snapshot["payments"] = []
        snapshot["applications"] = []
    population = control(data, "complete_original_payment_population")
    population.update(payment_ids=[row["id"] for row in snapshot["payments"]],
                      disbursement_ids=[row["disbursement_id"] for row in snapshot["payments"]],
                      application_ids=[row["id"] for row in snapshot["applications"]], paid_total=amount)
    pin_bundle(data)


def competing(data, recipe="clawback_first"):
    data["policy"]["priority_recipe"] = data["opening_state"]["priority_recipe"] = recipe
    data["offset_authorities"][0]["priority"] = 0 if recipe == "clawback_first" else 1
    row = deepcopy(data["offset_authorities"][0])
    row.update(id="other-authority", claim_id="other-claim", kind="other_supplied_claim", origin_id="other-claim-source",
               amount="25", priority=1 if recipe == "clawback_first" else 0, sequence=2, source_ref="synthetic-other-authorization")
    data["offset_authorities"].append(row)


def add_cash(data, amount="5"):
    data["cash_recoveries"] = [{"id": "cash-q1", "receipt_id": "bank-receipt-q1", "scope": deepcopy(data["scope"]),
                                "amount": amount, "received_date": "2026-03-15", "received_at": "2026-03-15T12:00:00Z",
                                "observed_at": "2026-03-16T00:00:00Z", "source_ref": "synthetic-cash-repayment-q1", "evidence_ref": "cash-source"}]
    data["recovery_applications"] = [{"id": "cash-app-q1", "cash_id": "cash-q1", "claim_id": "overpayment-claim-1",
                                      "scope": deepcopy(data["scope"]), "amount": amount, "observed_at": "2026-03-16T01:00:00Z",
                                      "source_ref": "synthetic-cash-application-q1", "evidence_ref": "cash-source"}]
    data["evidence"].append({"id": "cash-source", "scope": deepcopy(data["scope"]), "observed_at": "2026-03-16T01:00:00Z", "kind": "actual_cash_recovery"})
    control(data, "complete_cash_recovery_population", data["period"]).update(
        cash_ids=["cash-q1"], receipt_ids=["bank-receipt-q1"], application_ids=["cash-app-q1"], cash_total=amount)


def successor(previous, previous_input, earned="3", quarter=2):
    data = deepcopy(previous_input)
    endings = {2: ("2026-07-01", "2026-06-30", "2026-07-03T00:00:00Z", "2026-05-15"),
               3: ("2026-10-01", "2026-09-30", "2026-10-03T00:00:00Z", "2026-08-15")}
    end, as_of, cutoff, earning_date = endings[quarter]
    data.update(case_id="authorized-offsets-q" + str(quarter), period={"start": previous["period"]["end"], "end": end}, as_of=as_of, cutoff=cutoff)
    data["opening_state"] = exact_json(previous["closing_state"])
    data["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
    for key in ARRAYS:
        data[key] = []
    row = deepcopy(fixture()["future_earnings"][0])
    row.update(id="earned-q" + str(quarter), amount=earned, effective_date=earning_date,
               observed_at=earning_date + "T12:00:00Z", source_ref="synthetic-earned-q" + str(quarter),
               upstream_ref="synthetic:earned-q" + str(quarter) + "#line-1", evidence_ref="earned-source-q" + str(quarter))
    data["future_earnings"] = [row]
    data["evidence"].append({"id": row["evidence_ref"], "scope": deepcopy(data["scope"]), "observed_at": row["observed_at"], "kind": "synthetic-future-earned-source"})
    data["evidence"].append({"id": "complete-recoveries-q" + str(quarter), "scope": deepcopy(data["scope"]),
                             "observed_at": as_of + "T12:00:00Z", "kind": "complete_cash_recovery_population",
                             "period": deepcopy(data["period"]), "cash_ids": [], "receipt_ids": [], "application_ids": [], "cash_total": "0"})
    return data


class AuthorizedOffsetOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(AuthorizedOffsetOracleError) as raised:
            authorized_offsets(data)
        self.assertEqual(str(raised.exception), code)
        return raised.exception

    def test_original_reversal_paid_and_offset_are_separate(self):
        result = authorized_offsets(fixture())
        self.assertEqual([result[key] for key in ("original_gross", "original_issued", "original_actual_paid", "current_signed_reversal",
                                                 "revised_original_entitlement", "original_outstanding", "potential_overpayment",
                                                 "current_actual_cash_recovered", "current_earning_offsets", "payable_calculated")],
                         [100, 100, 80, -40, 60, 0, 20, 0, 20, 10])
        self.assertEqual(result["original_payment_status"], "complete_with_payments")
        self.assertEqual(result["cash_recovery_status"], "complete_no_events")
        self.assertEqual(result["current_settlement_payment_status"], "no_event_supplied")
        claim = result["claims"][0]
        self.assertEqual([claim[key] for key in ("authorized_amount", "actual_cash_recovered", "earning_offsets", "remaining")], [20, 0, 20, 0])
        self.assertEqual(result["closing_state"]["original_bundle"], fixture()["original_bundle"])

    def test_no_offset_authority_retains_unresolved_potential_and_earning(self):
        data = fixture()
        data["offset_authorities"] = []
        result = authorized_offsets(data)
        self.assertEqual([result[key] for key in ("potential_overpayment", "unallocated_overpayment_capacity", "current_earning_offsets", "payable_calculated")], [20, 20, 0, 30])
        self.assertEqual(result["claims"], [])

    def test_partial_and_explicit_empty_payment_controls_change_outstanding(self):
        for paid, outstanding, status in (("50", 10, "complete_with_payments"), ("0", 60, "complete_no_events")):
            with self.subTest(paid=paid):
                data = fixture()
                payment(data, paid)
                data["offset_authorities"] = []
                result = authorized_offsets(data)
                self.assertEqual([result[key] for key in ("original_actual_paid", "original_outstanding", "potential_overpayment", "payable_calculated")], [Fraction(paid), outstanding, 0, 30])
                self.assertEqual(result["original_payment_status"], status)

    def test_missing_completeness_is_unknown_not_paid_or_recovered_zero(self):
        for kind, code in (("complete_original_payment_population", "OFFSET_PAYMENT_POPULATION_REQUIRED"),
                           ("complete_cash_recovery_population", "OFFSET_RECOVERY_POPULATION_REQUIRED")):
            data = fixture()
            data["evidence"] = [row for row in data["evidence"] if row["kind"] != kind]
            self.assertEqual(self.reject(data, code).evidence_status, "no_event_supplied")

    def test_population_controls_prevent_dropping_original_cash_facts(self):
        data = fixture()
        data["original_bundle"]["payment_snapshot"]["payments"] = []
        data["original_bundle"]["payment_snapshot"]["applications"] = []
        pin_bundle(data)
        self.reject(data, "OFFSET_PAYMENT_POPULATION_CONTROL")
        data = fixture()
        add_cash(data)
        data["cash_recoveries"] = data["recovery_applications"] = []
        self.reject(data, "OFFSET_RECOVERY_POPULATION_CONTROL")

    def test_actual_cash_is_applied_before_calculated_offsets(self):
        data = fixture()
        add_cash(data)
        data["future_earnings"][0]["amount"] = "10"
        result = authorized_offsets(data)
        self.assertEqual([result[key] for key in ("original_actual_paid", "current_actual_cash_recovered", "current_earning_offsets", "payable_calculated")], [80, 5, 10, 0])
        self.assertEqual([result["claims"][0][key] for key in ("actual_cash_recovered", "earning_offsets", "remaining")], [5, 10, 5])
        self.assertEqual(result["offset_lines"][0]["claim_before"], 15)

    def test_priority_recipes_have_amount_changing_claim_results(self):
        for recipe, expected_offsets, expected_remaining in (("clawback_first", [20, 10], [0, 15]), ("other_claim_first", [5, 25], [15, 0])):
            data = fixture()
            competing(data, recipe)
            result = authorized_offsets(data)
            claims = {row["id"]: row for row in result["claims"]}
            self.assertEqual([claims[key]["earning_offsets"] for key in ("overpayment-claim-1", "other-claim")], expected_offsets)
            self.assertEqual([claims[key]["remaining"] for key in ("overpayment-claim-1", "other-claim")], expected_remaining)
            self.assertEqual(result["payable_calculated"], 0)
            self.assertEqual(result["offset_lines"][0]["priority"], 0)

    def test_earning_dates_and_explicit_sequences_not_physical_row_order(self):
        data = fixture()
        data["future_earnings"][0].update(amount="10", effective_date="2026-02-17")
        second = deepcopy(data["future_earnings"][0])
        second.update(id="later-earned", amount="15", effective_date="2026-02-18", sequence=2, source_ref="synthetic-later-earned", upstream_ref="synthetic:later#line-1")
        data["future_earnings"].append(second)
        result = authorized_offsets(data)
        self.assertEqual([row["earning_offset"] for row in result["earning_lines"]], [0, 15])
        self.assertEqual(result["payable_calculated"], 10)
        self.assertEqual(result["claims"][0]["remaining"], 5)
        permuted = deepcopy(data)
        for key in ARRAYS:
            permuted[key].reverse()
        self.assertEqual(exact_json(authorized_offsets(permuted)), exact_json(result))

    def test_explicit_sequence_changes_competing_same_kind_allocations(self):
        data = fixture()
        data["future_earnings"][0]["amount"] = "10"
        data["offset_authorities"][0]["amount"] = "8"
        second = deepcopy(data["offset_authorities"][0])
        second.update(id="second-authority", claim_id="second-claim", sequence=2, amount="12", source_ref="synthetic-second-claim")
        data["offset_authorities"].append(second)
        result = authorized_offsets(data)
        claims = {row["id"]: row for row in result["claims"]}
        self.assertEqual([claims[key]["earning_offsets"] for key in ("overpayment-claim-1", "second-claim")], [8, 2])
        permuted = deepcopy(data)
        permuted["offset_authorities"].reverse()
        self.assertEqual(exact_json(authorized_offsets(permuted)), exact_json(result))
        data["offset_authorities"][0]["sequence"] = 2
        data["offset_authorities"][1]["sequence"] = 1
        claims = {row["id"]: row for row in authorized_offsets(data)["claims"]}
        self.assertEqual([claims[key]["earning_offsets"] for key in ("overpayment-claim-1", "second-claim")], [0, 10])

    def test_real_serialized_adjacent_carry_does_not_repeat_reversal_or_recovery(self):
        first_input = fixture()
        add_cash(first_input)
        first_input["future_earnings"][0]["amount"] = "10"
        first = json.loads(json.dumps(exact_json(authorized_offsets(first_input))))
        second_input = successor(first, first_input)
        second = authorized_offsets(second_input)
        self.assertEqual([second[key] for key in ("current_signed_reversal", "cumulative_signed_reversal", "current_actual_cash_recovered", "current_earning_offsets", "payable_calculated")], [0, -40, 0, 3, 0])
        self.assertEqual([second["claims"][0][key] for key in ("actual_cash_recovered", "earning_offsets", "remaining")], [5, 13, 2])
        third_input = successor(json.loads(json.dumps(exact_json(second))), second_input, earned="5", quarter=3)
        third = authorized_offsets(third_input)
        self.assertEqual([third[key] for key in ("current_earning_offsets", "payable_calculated", "original_actual_paid")], [2, 3, 80])
        self.assertEqual([third["claims"][0][key] for key in ("actual_cash_recovered", "earning_offsets", "remaining")], [5, 15, 0])
        self.assertEqual(len(third["closing_state"]["period_history"]), 3)

    def test_closed_claim_principal_cannot_be_authorized_again(self):
        first_input = fixture()
        first = authorized_offsets(first_input)
        data = successor(first, first_input)
        row = deepcopy(first_input["offset_authorities"][0])
        row.update(id="new-authority", claim_id="new-claim", sequence=2, source_ref="synthetic-new-authority", effective=deepcopy(data["period"]),
                   eligible_from="2026-04-10", approved_date="2026-04-09", recorded_date="2026-04-09", observed_at="2026-04-10T00:00:00Z")
        data["offset_authorities"] = [row]
        self.reject(data, "OFFSET_OVERPAYMENT_AUTHORIZATION_CAPACITY")

    def test_additional_return_only_expands_unallocated_capacity(self):
        first_input = fixture()
        data = successor(authorized_offsets(first_input), first_input, earned="30")
        revision = deepcopy(first_input["revision_authorities"][0])
        revision.update(id="revision-q2", effective=deepcopy(data["period"]), approved_date="2026-04-15", recorded_date="2026-04-15",
                        observed_at="2026-04-16T00:00:00Z", permitted_reversal_ids=["reversal-q2"], maximum_returned_basis="40", source_ref="synthetic-revision-q2")
        reversal = deepcopy(first_input["reversals"][0])
        reversal.update(id="reversal-q2", revision_authority_id="revision-q2", returned_basis="40", return_date="2026-04-15", recognition_date="2026-04-15",
                        observed_at="2026-04-16T00:00:00Z", source_ref="synthetic-return-q2")
        authority = deepcopy(first_input["offset_authorities"][0])
        authority.update(id="offset-q2", claim_id="claim-q2", sequence=2, effective=deepcopy(data["period"]), approved_date="2026-04-16", recorded_date="2026-04-16",
                         eligible_from="2026-04-17", observed_at="2026-04-17T00:00:00Z", source_ref="synthetic-offset-q2")
        data["revision_authorities"], data["reversals"], data["offset_authorities"] = [revision], [reversal], [authority]
        result = authorized_offsets(data)
        self.assertEqual([result[key] for key in ("current_signed_reversal", "cumulative_signed_reversal", "revised_original_entitlement", "potential_overpayment", "total_authorized_original", "current_earning_offsets", "payable_calculated")], [-20, -60, 40, 40, 40, 20, 10])
        data["offset_authorities"][0]["amount"] = "21"
        self.reject(data, "OFFSET_OVERPAYMENT_AUTHORIZATION_CAPACITY")

    def test_later_recognition_cannot_finance_an_earlier_prospective_claim(self):
        data = fixture()
        data["reversals"][0]["recognition_date"] = "2026-03-15"
        self.reject(data, "OFFSET_OVERPAYMENT_AUTHORIZATION_CAPACITY")

    def test_authority_capacity_and_all_unused_authorizations_are_checked(self):
        data = fixture()
        data["offset_authorities"][0]["amount"] = "21"
        self.reject(data, "OFFSET_OVERPAYMENT_AUTHORIZATION_CAPACITY")
        data = fixture()
        competing(data)
        data["offset_authorities"][1]["amount"] = "26"
        self.reject(data, "OFFSET_OTHER_AUTHORIZATION_CAPACITY")
        data = fixture()
        unused = deepcopy(data["revision_authorities"][0])
        unused.update(id="unused-invalid-authority", source_ref="synthetic-unused-authority", approved=False)
        data["revision_authorities"].append(unused)
        self.reject(data, "OFFSET_AUTHORITY_ASOF_SCOPE")

    def test_revision_required_and_original_measurement_limit(self):
        data = fixture()
        data["revision_authorities"] = []
        self.reject(data, "OFFSET_REVISION_AUTHORITY_REQUIRED")
        data = fixture()
        data["reversals"][0]["returned_basis"] = "201"
        data["revision_authorities"][0]["maximum_returned_basis"] = "201"
        self.reject(data, "OFFSET_ORIGINAL_OVERRETURN")
        data = fixture()
        data["reversals"][0]["returned_basis"] = "81"
        self.reject(data, "OFFSET_REVISION_AUTHORITY_LIMIT")

    def test_duplicate_ids_and_original_payment_aliases(self):
        data = fixture()
        data["reversals"].append(deepcopy(data["reversals"][0]))
        self.reject(data, "OFFSET_DUPLICATE_ID")
        data = fixture()
        alias = deepcopy(data["original_bundle"]["payment_snapshot"]["payments"][0])
        alias.update(id="payment-alias", source_ref="new-name-same-bank-disbursement")
        data["original_bundle"]["payment_snapshot"]["payments"].append(alias)
        pin_bundle(data)
        self.reject(data, "OFFSET_DUPLICATE_BANK_PAYMENT")

    def test_cash_receipt_and_other_claim_origin_aliases_are_not_fresh_value(self):
        data = fixture()
        add_cash(data)
        alias = deepcopy(data["cash_recoveries"][0])
        alias.update(id="cash-alias", source_ref="synthetic-renamed-cash")
        data["cash_recoveries"].append(alias)
        self.reject(data, "OFFSET_BANK_RECEIPT_ALREADY_RECOGNIZED")
        data = fixture()
        alias = deepcopy(data["original_bundle"]["other_claims"][0])
        alias.update(id="other-alias", source_ref="synthetic-renamed-other-source")
        data["original_bundle"]["other_claims"].append(alias)
        pin_bundle(data)
        self.reject(data, "OFFSET_OTHER_CLAIM_SOURCE")
        data = fixture()
        add_cash(data)
        first = authorized_offsets(data)
        following = successor(first, data)
        following["cash_recoveries"] = deepcopy(data["cash_recoveries"])
        following["cash_recoveries"][0].update(id="cash-q2", source_ref="synthetic-cash-q2", received_date="2026-05-15",
                                              received_at="2026-05-15T12:00:00Z", observed_at="2026-05-16T00:00:00Z")
        self.reject(following, "OFFSET_BANK_RECEIPT_ALREADY_RECOGNIZED")

    def test_source_and_upstream_line_aliases_do_not_add_earnings(self):
        data = fixture()
        alias = deepcopy(data["future_earnings"][0])
        alias.update(id="alias", sequence=2, source_ref="renamed-same-upstream")
        data["future_earnings"].append(alias)
        self.reject(data, "OFFSET_EARNING_LINE_ALREADY_RECOGNIZED")
        data = fixture()
        alias = deepcopy(data["reversals"][0])
        alias["id"] = "reversal-alias"
        data["reversals"].append(alias)
        data["revision_authorities"][0]["permitted_reversal_ids"].append(alias["id"])
        self.reject(data, "OFFSET_SOURCE_ALREADY_RECOGNIZED")

    def test_overapplications_and_unapplied_actual_cash_block(self):
        data = fixture()
        data["original_bundle"]["payment_snapshot"]["applications"][0]["amount"] = "81"
        pin_bundle(data)
        self.reject(data, "OFFSET_ORIGINAL_PAYMENT_CONSERVATION")
        data = fixture()
        add_cash(data, "21")
        self.reject(data, "OFFSET_CLAIM_CASH_OVERAPPLICATION")
        data = fixture()
        add_cash(data)
        data["recovery_applications"][0]["amount"] = "4"
        self.reject(data, "OFFSET_CASH_APPLICATION_CONSERVATION")

    def test_scope_authority_priority_and_ambiguous_sequences(self):
        data = fixture()
        data["offset_authorities"][0]["scope"]["pool_id"] = "wrong-pool"
        self.reject(data, "OFFSET_FACT_SCOPE")
        data = fixture()
        data["offset_authorities"][0]["priority"] = 1
        self.reject(data, "OFFSET_EXPLICIT_PRIORITY")
        data = fixture()
        competing(data)
        data["offset_authorities"][1]["sequence"] = 1
        self.reject(data, "OFFSET_CLAIM_SEQUENCE")
        data = fixture()
        data["as_of"] = "2026-02-15"
        self.reject(data, "OFFSET_AUTHORITY_ASOF_SCOPE")

    def test_exact_cutoff_and_population_chronology(self):
        data = fixture()
        data["future_earnings"][0]["observed_at"] = data["cutoff"]
        self.reject(data, "OFFSET_FACT_CUTOFF")
        data["future_earnings"][0]["observed_at"] = "2026-04-02T23:59:59.999999999999Z"
        self.assertEqual(authorized_offsets(data)["payable_calculated"], 10)
        data = fixture()
        control(data, "complete_original_payment_population")["observed_at"] = "2025-12-15T00:00:00Z"
        self.reject(data, "OFFSET_POPULATION_OBSERVATION_ORDER")
        data = fixture()
        add_cash(data)
        control(data, "complete_cash_recovery_population")["observed_at"] = "2026-03-15T00:00:00Z"
        self.reject(data, "OFFSET_POPULATION_OBSERVATION_ORDER")

    def test_actual_original_payment_is_historical_and_cash_is_not_earning(self):
        data = fixture()
        data["original_bundle"]["payment_snapshot"]["payments"][0].update(paid_at="2026-02-01T00:00:00Z", observed_at="2026-02-02T00:00:00Z")
        pin_bundle(data)
        self.reject(data, "OFFSET_PAYMENT_NOT_HISTORICAL")
        data = fixture()
        add_cash(data)
        next(row for row in data["evidence"] if row["id"] == "cash-source")["kind"] = "synthetic-earning-not-cash"
        self.reject(data, "OFFSET_ACTUAL_CASH_EVIDENCE")

    def test_predecessor_history_and_replays_are_validated(self):
        first_input = fixture()
        first = authorized_offsets(first_input)
        data = successor(first, first_input)
        data.pop("prior_result")
        self.reject(data, "OFFSET_PREDECESSOR_REQUIRED")
        data = successor(first, first_input)
        data["opening_state"]["claims"][0]["remaining"] = "1"
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        self.reject(data, "OFFSET_OPENING_HISTORY_RECONCILIATION")
        data = successor(first, first_input)
        data["future_earnings"][0]["id"] = first_input["future_earnings"][0]["id"]
        self.reject(data, "OFFSET_EVENT_ALREADY_RECOGNIZED")
        data = successor(first, first_input)
        data["future_earnings"][0]["upstream_ref"] = first_input["future_earnings"][0]["upstream_ref"]
        self.reject(data, "OFFSET_EARNING_LINE_ALREADY_RECOGNIZED")
        data = successor(first, first_input)
        next(row for row in data["evidence"] if row["id"] == "earnings-source")["observed_at"] = "2026-05-01T00:00:00Z"
        self.reject(data, "OFFSET_EVIDENCE_CUTOFF")

    def test_exact_fraction_values_are_not_rounded(self):
        data = fixture()
        data["offset_authorities"][0]["amount"] = "1/3"
        data["future_earnings"][0]["amount"] = "1/2"
        result = authorized_offsets(data)
        self.assertEqual([result[key] for key in ("current_earning_offsets", "payable_calculated")], [Fraction(1, 3), Fraction(1, 6)])
        self.assertEqual(exact_json(result)["payable_calculated"], "1/6")
        data["future_earnings"][0]["amount"] = 0.5
        self.reject(data, "OFFSET_EXACT_NONNEGATIVE_VALUE")

    def test_no_compiler_imports_or_solved_financial_inputs(self):
        source = (ROOT / "oracles/authorized_offsets.py").read_text(encoding="utf-8")
        imports = [node for node in ast.walk(ast.parse(source)) if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertEqual({node.module if isinstance(node, ast.ImportFrom) else alias.name for node in imports
                          for alias in (node.names if isinstance(node, ast.Import) else [None])}, {"datetime", "fractions", "re"})
        data = fixture()
        data["solved_payable"] = "10"
        self.reject(data, "OFFSET_RECORD_FIELDS")


if __name__ == "__main__":
    unittest.main()
