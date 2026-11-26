"""Original-fact, as-known and actual-carry controls before executable SPL."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.merchandising_reprice import MerchandisingRepriceOracleError, exact_json, merchandising_reprice


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/merchandising-reprice/neutral.json").read_text(encoding="utf-8"))


def prefix(data, count):
    """Mechanically subset this fixed UTC whole-second fixture's known records."""
    result = deepcopy(data)
    selected = data["views"][count - 1]
    cutoff = selected["cutoff"]
    views = {row["id"] for row in data["views"][:count]}
    periods = {row["id"] for row in data["periods"][:count]}
    for key in ("periods", "views", "receipts", "box_office", "issues", "payments", "applications", "populations", "no_default", "evidence"):
        result[key] = [row for row in result[key] if row["observed_at"] < cutoff
                       and (key != "periods" or row["id"] in periods)
                       and (key != "views" or row["id"] in views)
                       and (key not in ("populations", "no_default") or row["view_id"] in views)]
    result["case_id"] = selected["source_case_id"]
    result["run"] = {"view_id": selected["id"], "mode": "final"}
    result.pop("prior_result", None)
    return result


def with_predecessor(data, previous):
    data["opening_state"] = exact_json(previous["closing_state"])
    data["prior_result"] = exact_json({"source_case_id": previous["source_case_id"], "period": previous["period"], "closing_state": previous["closing_state"]})
    return data


def actual_chain(data=None):
    original = fixture() if data is None else data
    first = prefix(original, 1)
    first["opening_state"] = {"scope": deepcopy(first["scope"]), "purpose": "first_dollar_merchandising", "policy": deepcopy(first["policy"]),
                              "boundary": "2006-01-01", "origin": "genesis", "source_case_id": "genesis"}
    first_result = json.loads(json.dumps(exact_json(merchandising_reprice(first))))
    second = with_predecessor(prefix(original, 2), first_result)
    second_result = json.loads(json.dumps(exact_json(merchandising_reprice(second))))
    third = with_predecessor(prefix(original, 3), second_result)
    return first, first_result, second, second_result, third, merchandising_reprice(third)


def add_fact(data, identity, kind, observed_at, **fields):
    data["evidence"].append({"id": identity + "-evidence", "scope": deepcopy(data["scope"]), "kind": kind,
                             "approved": True, "observed_at": observed_at, "source_ref": "synthetic-original-evidence:" + identity})
    return {"id": identity, "scope": deepcopy(data["scope"]), "observed_at": observed_at,
            "source_ref": "synthetic-original:" + identity, "evidence_ref": identity + "-evidence", **fields}


def extend_q4(previous_input, previous):
    data = deepcopy(previous_input)
    data["case_id"] = "merch-q4"
    data["run"] = {"view_id": "view-q4", "mode": "final"}
    data["periods"].append(add_fact(data, "period-q4", "declared-calendar-period", "2006-10-04T00:00:00Z", period={"start": "2006-10-01", "end": "2007-01-01"}))
    data["views"].append(add_fact(data, "view-q4", "approved-final-recognition-view", "2007-01-02T00:00:00Z", source_case_id="merch-q4", period_id="period-q4",
                                  mode="final", as_of="2006-12-31", cutoff="2007-01-03T00:00:00Z", coverage_end="2007-01-01", recognition_id="recognition-q4", approved=True))
    data["no_default"].append(add_fact(data, "no-default-q4", "approved-current-no-material-default-finding", "2007-01-02T00:00:00Z", view_id="view-q4", approved=True, not_in_material_default=True))
    population = deepcopy(data["populations"][-1])
    population.update(add_fact(data, "population-q4", "complete_original_known_population", "2007-01-02T12:00:00Z", view_id="view-q4"))
    population["receipt_coverage"]["end"] = "2007-01-01"
    data["populations"].append(population)
    return with_predecessor(data, previous)


def preview():
    data = fixture()
    data["case_id"] = "merch-q3-preview"
    data["run"] = {"view_id": "preview-q3", "mode": "preview"}
    view = data["views"][-1]
    view.update(id="preview-q3", source_case_id=data["case_id"], mode="preview", cutoff="2006-09-10T00:00:00Z", coverage_end="2006-09-10",
                as_of="2006-09-09", recognition_id="", observed_at="2006-09-09T00:00:00Z", source_ref="synthetic-original-preview-view")
    population = data["populations"][-1]
    population.update(view_id="preview-q3", observed_at="2006-09-09T12:00:00Z", source_ref="synthetic-original-preview-population", box_office_ids=["box-q1", "box-q2"])
    population["receipt_coverage"]["end"] = "2006-09-10"
    finding = data["no_default"][-1]
    finding.update(view_id="preview-q3", observed_at="2006-09-09T00:00:00Z")
    for row in data["evidence"]:
        if row["id"] in {view["evidence_ref"], finding["evidence_ref"]}:
            row["observed_at"] = "2006-09-09T00:00:00Z"
        elif row["id"] == population["evidence_ref"]:
            row["observed_at"] = "2006-09-09T12:00:00Z"
    for key in ("box_office", "evidence"):
        data[key] = [row for row in data[key] if row["observed_at"] < view["cutoff"]]
    return data


def population(data, view="view-q3"):
    return next(row for row in data["populations"] if row["view_id"] == view)


class MerchandisingRepriceOracleTests(unittest.TestCase):
    def reject(self, data, code):
        with self.assertRaises(MerchandisingRepriceOracleError) as raised:
            merchandising_reprice(data)
        self.assertEqual(str(raised.exception), code)
        return raised.exception

    def test_hand_economics_and_distinct_financial_amount_spaces(self):
        result = merchandising_reprice(fixture())
        self.assertEqual(result["thresholds"], [77000000, 87000000, 107000000])
        self.assertEqual([result[key] for key in ("production_cost", "production_charge", "funding_charge")], [40000000, 6000000, 1000000])
        self.assertEqual([result[key] for key in ("current_earnings", "catchup", "new_recognition_candidate", "recognized_this_run")], [Fraction(525, 2), 210, Fraction(945, 2), Fraction(945, 2)])
        self.assertEqual([result[key] for key in ("cumulative_entitlement_asof", "known_issued", "actual_paid", "issued_outstanding", "candidate_unissued", "candidate_total_unpaid")], [Fraction(3675, 2), 1365, 1310, 55, Fraction(945, 2), Fraction(1055, 2)])
        self.assertEqual(result["payment_status"], "complete_original_population")
        self.assertEqual(result["issue_status"], "original_issues_retained_no_new_issue_inferred")
        self.assertTrue(result["consumable_state"])

    def test_original_row_targets_deltas_and_immutable_issue_versions(self):
        result = merchandising_reprice(fixture())
        rows = {row["receipt_id"]: row for row in result["attributions"]}
        self.assertEqual([rows[key]["nmi"] for key in ("license-q1", "license-q2", "license-q3")], [7000, 14000, 3500])
        self.assertEqual([rows[key]["license_deduction"] for key in ("license-q1", "license-q2", "license-q3")], [3000, 6000, 1500])
        self.assertEqual([rows[key]["previously_recognized"] for key in ("license-q1", "license-q2", "license-q3")], [455, 910, 0])
        self.assertEqual([rows[key]["target_entitlement"] for key in ("license-q1", "license-q2", "license-q3")], [525, 1050, Fraction(525, 2)])
        self.assertEqual([rows[key]["recognition_delta"] for key in ("license-q1", "license-q2", "license-q3")], [70, 140, Fraction(525, 2)])
        self.assertEqual([row["original_amount"] for row in result["obligation_lines"]], [455, 910])
        self.assertEqual([row["amount"] for row in result["recognition_history"]], [455, 910, Fraction(945, 2)])

    def test_original_calculation_cutoffs_do_not_know_later_issues_or_payments(self):
        result = merchandising_reprice(fixture())
        first, second, third = result["as_known_snapshots"]
        self.assertEqual([first[key] for key in ("rate", "current_earnings", "known_issued", "actual_paid")], [Fraction(13, 200), 455, 0, 0])
        self.assertEqual(first["known_issue_ids"], [])
        self.assertEqual(first["known_payment_ids"], [])
        self.assertEqual(second["known_issue_ids"], ["issue-q1"])
        self.assertEqual(second["known_payment_ids"], ["payment-q1"])
        self.assertEqual([second[key] for key in ("current_earnings", "known_issued", "actual_paid", "candidate_unissued")], [910, 455, 400, 910])
        self.assertEqual(third["known_issue_ids"], ["issue-q1", "issue-q2"])
        self.assertEqual(third["actual_paid"], 1310)

    def test_actual_serialized_q1_q2_q3_q4_carry_does_not_repeat_catchup(self):
        first, r1, second, r2, third, r3 = actual_chain()
        self.assertEqual([Fraction(r1["recognized_this_run"]), Fraction(r2["recognized_this_run"]), r3["recognized_this_run"]], [455, 910, Fraction(945, 2)])
        fourth = extend_q4(third, json.loads(json.dumps(exact_json(r3))))
        result = merchandising_reprice(fourth)
        self.assertEqual([result[key] for key in ("current_earnings", "catchup", "recognized_this_run")], [0, 0, 0])
        self.assertEqual(result["candidate_total_unpaid"], Fraction(1055, 2))
        self.assertEqual(result["actual_paid"], 1310)
        self.assertEqual(result["closing_state"]["recognized_rows"], r3["closing_state"]["recognized_rows"])
        self.assertEqual(len(result["recognition_history"]), 4)
        self.assertEqual(result["recognition_history"][-1]["id"], "recognition-q4")

    def test_threshold_equality_and_wrong_negative_cost_discriminator(self):
        data = fixture()
        data["box_office"][-1]["gross"] = "86999999.99"
        below = merchandising_reprice(data)
        self.assertEqual(below["rate"], Fraction(13, 200))
        self.assertEqual(below["catchup"], 0)
        self.assertEqual(below["candidate_total_unpaid"], Fraction(565, 2))
        equal = merchandising_reprice(fixture())
        self.assertEqual(equal["rate"], Fraction(3, 40))
        self.assertEqual(equal["thresholds"][1], 87000000)
        self.assertNotEqual(equal["thresholds"][1], 2 * (40000000 + 6000000 + 1000000))
        data = fixture()
        data["terms"]["solved_second_threshold"] = "94000000"
        self.reject(data, "MR_RECORD_FIELDS")

    def test_prospective_only_and_double_recognition_are_wrong_controls(self):
        result = merchandising_reprice(fixture())
        self.assertNotEqual(result["candidate_total_unpaid"], Fraction(635, 2))  # 317.50 omits historical 210.
        self.assertNotEqual(result["candidate_total_unpaid"], Fraction(1475, 2))  # 737.50 recognizes 210 twice.
        self.assertNotEqual(result["candidate_total_unpaid"], Fraction(1165, 2))  # 582.50 uses paid as prior entitlement.
        for method in ("prospective_only", "amend_and_catchup"):
            data = fixture()
            data["policy"]["method"] = method
            self.reject(data, "MR_SELECTED_POLICY")
        first, r1, second, r2, third, r3 = actual_chain()
        fourth = extend_q4(third, r3)
        fourth["views"][-1]["recognition_id"] = "recognition-q3"
        self.reject(fourth, "MR_DUPLICATE_RECOGNITION")

    def test_cash_payment_changes_arrears_not_catchup_entitlement_base(self):
        data = fixture()
        payment = add_fact(data, "payment-extra", "actual_participant_disbursement", "2006-09-02T00:00:00Z", bank_disbursement_id="owner-bank-extra", amount="55", paid_date="2006-09-01")
        application = add_fact(data, "application-extra", "actual_payment_application", "2006-09-03T00:00:00Z", payment_id="payment-extra", issue_id="issue-q1", amount="55", applied_date="2006-09-02")
        data["payments"].append(payment)
        data["applications"].append(application)
        control = population(data)
        control["payment_ids"].append(payment["id"])
        control["disbursement_ids"].append(payment["bank_disbursement_id"])
        control["application_ids"].append(application["id"])
        control["payment_total"] = control["application_total"] = "1365"
        result = merchandising_reprice(data)
        self.assertEqual(result["catchup"], 210)
        self.assertEqual(result["actual_paid"], 1365)
        self.assertEqual(result["issued_outstanding"], 0)
        self.assertEqual(result["candidate_total_unpaid"], Fraction(945, 2))

    def test_pretrigger_preview_is_partial_known_view_and_has_no_recognized_state(self):
        data = preview()
        result = merchandising_reprice(data)
        self.assertEqual(result["status"], "preview")
        self.assertFalse(result["consumable_state"])
        self.assertIsNone(result["closing_state"])
        self.assertEqual([result[key] for key in ("rate", "current_earnings", "catchup", "new_recognition_candidate", "recognized_this_run")], [Fraction(13, 200), Fraction(455, 2), 0, Fraction(455, 2), 0])
        self.assertEqual(result["recognized_cumulative"], 1365)
        self.assertEqual(result["candidate_total_unpaid"], Fraction(565, 2))
        self.assertEqual(len(result["recognition_history"]), 2)
        self.assertLess(data["views"][-1]["coverage_end"], data["periods"][-1]["period"]["end"])
        self.assertNotIn("box-q3", data["populations"][-1]["box_office_ids"])

    def test_preview_cannot_claim_complete_future_period_or_be_finalized(self):
        data = preview()
        data["views"][-1].update(mode="final", recognition_id="recognition-preview")
        data["run"]["mode"] = "final"
        self.reject(data, "MR_PREVIEW_NOT_FINAL")
        data = preview()
        data["views"][-1].update(coverage_end="2006-10-01", as_of="2006-09-30")
        self.reject(data, "MR_VIEW_COVERAGE")
        data = preview()
        data["populations"][-1]["receipt_coverage"]["end"] = "2006-10-01"
        self.reject(data, "MR_RECEIPT_POPULATION_COVERAGE")

    def test_complete_empty_and_missing_original_populations_differ(self):
        data = fixture()
        result = merchandising_reprice(data)
        self.assertEqual(result["as_known_snapshots"][0]["actual_paid"], 0)
        first_control = population(data, "view-q1")
        self.assertEqual(first_control["payment_ids"], [])
        self.assertEqual(first_control["payment_total"], "0")
        for view in ("view-q1", "view-q3"):
            changed = fixture()
            changed["populations"] = [row for row in changed["populations"] if row["view_id"] != view]
            error = self.reject(changed, "MR_COMPLETE_POPULATION_REQUIRED")
            self.assertEqual(error.payment_evidence_status, "no_event_supplied")
        data = fixture()
        population(data)["complete"] = False
        self.reject(data, "MR_COMPLETE_POPULATION_REQUIRED")

    def test_dropping_cash_issue_or_payment_facts_fails_population_controls(self):
        for key in ("receipts", "issues", "payments", "applications"):
            data = fixture()
            if key == "receipts":
                data[key].pop()  # Current receipt; CB and old issues remain intact.
            elif key == "issues":
                data[key].pop()
                data["applications"] = data["applications"][:1]
                data["payments"] = data["payments"][:1]
            elif key == "payments":
                data[key].pop()
                data["applications"].pop()
            else:
                data[key].pop()
            with self.subTest(key=key):
                self.reject(data, "MR_ORIGINAL_POPULATION_CONTROL")

    def test_cb_zero_reclassification_authority_and_lineage_are_mandatory(self):
        data = fixture()
        data["cb_switch"] = None
        self.reject(data, "MR_CB_RECLASSIFICATION_REQUIRED")
        for field in ("complete", "approved", "removed_from_defined_receipts", "included_in_nmi"):
            data = fixture()
            data["cb_switch"][field] = False
            self.reject(data, "MR_CB_RECLASSIFICATION_REQUIRED")
        data = fixture()
        data["cb_switch"]["prior_credit_total"] = "1"
        self.reject(data, "MR_NONZERO_CB_VARIANT_REQUIRED")
        data = fixture()
        data["cb_switch"]["receipt_ids"] = []
        self.reject(data, "MR_CB_SOURCE_LINEAGE")

    def test_qualifying_feature_prephotography_and_no_default_evidence_required(self):
        for field, value in (("graphic_units", "24999"), ("graphic_units", "25000.5"), ("comics_rank", "201"), ("comics_rank", "199.5"), ("feature_released", False), ("approved", False), ("units_date", "2005-02-01")):
            data = fixture()
            data["qualifications"][field] = value
            self.reject(data, "MR_QUALIFICATION_REQUIRED")
        data = fixture()
        data["no_default"][-1]["not_in_material_default"] = False
        self.reject(data, "MR_NO_DEFAULT_REQUIRED")

    def test_scope_source_metric_and_unknown_references_block(self):
        data = fixture()
        data["receipts"][-1]["scope"]["asset_id"] = "other-picture"
        self.reject(data, "MR_FACT_SCOPE")
        data = fixture()
        data["box_office"][-1]["metric"] = "worldwide-estimate"
        self.reject(data, "MR_BOX_OFFICE_METRIC")
        data = fixture()
        data["applications"][-1]["issue_id"] = "unknown-issue"
        self.reject(data, "MR_APPLICATION_REFERENCE")
        data = fixture()
        data["issues"][-1]["recognition_id"] = "unknown-recognition"
        self.reject(data, "MR_ISSUE_RECOGNITION_REFERENCE")

    def test_late_evidence_and_historical_source_corrections_are_not_silently_admitted(self):
        data = fixture()
        data["receipts"][-1]["observed_at"] = data["views"][-1]["cutoff"]
        self.reject(data, "MR_SOURCE_AFTER_CUTOFF")
        data = fixture()
        next(row for row in data["evidence"] if row["id"] == "license-q1-evidence")["observed_at"] = "2006-05-01T00:00:00Z"
        self.reject(data, "MR_SOURCE_AFTER_CUTOFF")
        data = fixture()
        data["receipts"][0]["observed_at"] = "2006-05-01T00:00:00Z"
        self.reject(data, "MR_LATE_HISTORICAL_RECEIPT_VARIANT_REQUIRED")
        data = fixture()
        data["box_office"][0]["observed_at"] = "2006-05-01T00:00:00Z"
        self.reject(data, "MR_CORRECTED_THRESHOLD_VARIANT_REQUIRED")

    def test_exact_submicrosecond_cutoff_preserves_original_recognition(self):
        data = fixture()
        instant = "2006-10-02T23:59:59.999999999999Z"
        data["receipts"][-1]["observed_at"] = instant
        control = population(data)
        control["observed_at"] = instant
        next(row for row in data["evidence"] if row["id"] == control["evidence_ref"])["observed_at"] = instant
        self.assertEqual(merchandising_reprice(data)["candidate_total_unpaid"], Fraction(1055, 2))
        data["receipts"][-1]["observed_at"] = "2006-10-03T00:00:00Z"
        self.reject(data, "MR_SOURCE_AFTER_CUTOFF")

    def test_physical_source_array_permutation_preserves_finance_and_normalized_state(self):
        data = fixture()
        expected = exact_json(merchandising_reprice(data))
        for key in ("periods", "views", "receipts", "box_office", "issues", "payments", "applications", "populations", "no_default", "evidence"):
            data[key].reverse()
        self.assertEqual(exact_json(merchandising_reprice(data)), expected)

    def test_duplicate_record_source_alias_and_bank_disbursement_do_not_create_money(self):
        data = fixture()
        data["receipts"].append(deepcopy(data["receipts"][-1]))
        self.reject(data, "MR_DUPLICATE_ID")
        data = fixture()
        alias = deepcopy(data["receipts"][-1])
        alias.update(id="license-alias", source_ref="renamed-license-source")
        data["receipts"].append(alias)
        self.reject(data, "MR_DUPLICATE_LICENSE_CASH_LINE")
        data = fixture()
        alias = deepcopy(data["payments"][-1])
        alias.update(id="payment-alias", source_ref="renamed-payment-source")
        data["payments"].append(alias)
        self.reject(data, "MR_DUPLICATE_PARTICIPANT_DISBURSEMENT")

    def test_original_issue_is_not_rewritten_to_current_repriced_allocation(self):
        data = fixture()
        data["issues"][0]["amount"] = "525"
        self.reject(data, "MR_ORIGINAL_ISSUE_AMOUNT_DATE")

    def test_issuance_cannot_precede_its_original_calculation_knowledge_cutoff(self):
        data = fixture()
        data["issues"][0].update(issued_date="2006-04-02", observed_at="2006-04-02T12:00:00Z")
        self.reject(data, "MR_ORIGINAL_ISSUE_AMOUNT_DATE")
        data = fixture()
        data["box_office"][-1]["observed_at"] = "2006-09-21T12:00:00Z"
        self.reject(data, "MR_BOX_OFFICE_OBSERVATION_ORDER")

    def test_nonqualifying_current_cash_is_retained_but_excluded_from_nmi(self):
        data = fixture()
        data["receipts"][-1]["qualifying"] = False
        result = merchandising_reprice(data)
        row = next(row for row in result["attributions"] if row["receipt_id"] == "license-q3")
        self.assertEqual(row["license_cash"], 5000)
        self.assertEqual(row["nmi"], 0)
        self.assertEqual(result["current_earnings"], 0)
        self.assertEqual(result["candidate_total_unpaid"], 265)

    def test_payment_application_conservation_and_obligation_cap(self):
        data = fixture()
        data["applications"][-1]["amount"] = "909"
        population(data)["application_total"] = "1309"
        self.reject(data, "MR_PAYMENT_APPLICATION_CONSERVATION")
        data = fixture()
        data["payments"][-1]["amount"] = data["applications"][-1]["amount"] = "911"
        population(data)["payment_total"] = population(data)["application_total"] = "1311"
        self.reject(data, "MR_ISSUE_OVERPAYMENT")

    def test_actual_predecessor_and_original_reconstruction_reject_forged_recognition(self):
        first, r1, second, r2, third, r3 = actual_chain()
        third.pop("prior_result")
        self.reject(third, "MR_PREDECESSOR_REQUIRED")
        third = with_predecessor(prefix(fixture(), 3), r2)
        third["opening_state"]["recognized_rows"][0]["amount"] = "400"
        third["prior_result"]["closing_state"] = deepcopy(third["opening_state"])
        self.reject(third, "MR_OPENING_HISTORY_RECONCILIATION")
        third = with_predecessor(prefix(fixture(), 3), r2)
        third["prior_result"]["source_case_id"] = "different-predecessor"
        self.reject(third, "MR_PREDECESSOR_MISMATCH")

    def test_zero_empty_and_fractional_current_license_amounts_keep_exact_policy(self):
        for amount, expected in (("0", Fraction()), ("1", Fraction(21, 400))):
            data = fixture()
            data["receipts"][-1]["amount"] = amount
            population(data)["receipt_total"] = str(30000 + Fraction(amount))
            result = merchandising_reprice(data)
            self.assertEqual(result["current_earnings"], expected)
            self.assertEqual(result["new_recognition_candidate"], 210 + expected)
        data = fixture()
        data["receipts"].pop()
        population(data)["receipt_ids"].remove("license-q3")
        population(data)["receipt_total"] = "30000"
        result = merchandising_reprice(data)
        self.assertEqual(result["current_earnings"], 0)
        self.assertEqual(result["catchup"], 210)

    def test_no_automatic_withholding_or_solved_threshold_delta_inputs(self):
        for key in ("withholding_rate", "target_entitlement", "catchup"):
            data = fixture()
            data[key] = "0.1"
            self.reject(data, "MR_RECORD_FIELDS")
        source = (ROOT / "oracles/merchandising_reprice.py").read_text(encoding="utf-8")
        imports = [node for node in ast.walk(ast.parse(source)) if isinstance(node, (ast.Import, ast.ImportFrom))]
        self.assertEqual({node.module if isinstance(node, ast.ImportFrom) else alias.name for node in imports
                          for alias in (node.names if isinstance(node, ast.Import) else [None])}, {"datetime", "fractions", "re"})

    def test_source_files_are_lf_from_authoring(self):
        for path in (ROOT / "oracles/merchandising_reprice.py", ROOT / "cases/merchandising-reprice/neutral.json"):
            self.assertNotIn(b"\r", path.read_bytes())


if __name__ == "__main__":
    unittest.main()
