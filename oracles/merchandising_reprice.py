"""Independent first-dollar merchandising recognition from original known views."""
from datetime import date, timedelta
from fractions import Fraction
import re


POLICY_ID = "RR04-MERCHANDISING-CATCHUP-01"
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}
SOURCE_ARRAYS = ("periods", "views", "receipts", "box_office", "issues", "payments", "applications", "populations", "no_default", "evidence")
SOURCE_URL = "https://www.sec.gov/Archives/edgar/data/1410132/000101376207002025/ex1014.htm"


class MerchandisingRepriceOracleError(ValueError):
    def __init__(self, code, payment_evidence_status=None):
        super().__init__(code)
        self.payment_evidence_status = payment_evidence_status


def _need(condition, code):
    if not condition:
        raise MerchandisingRepriceOracleError(code)


def _fields(row, required, optional=()):
    _need(type(row) is dict and required <= row.keys() <= required | set(optional), "MR_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "MR_IDENTITY_REQUIRED")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "MR_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _positive(value):
    result = _q(value)
    _need(result > 0, "MR_POSITIVE_AMOUNT")
    return result


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "MR_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise MerchandisingRepriceOracleError("MR_DATE") from None


def _period(row):
    _fields(row, {"start", "end"})
    first, last = _day(row["start"]), _day(row["end"])
    _need(first < last, "MR_PERIOD")
    return first, last


def _instant(value):
    _need(type(value) is str, "MR_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "MR_INSTANT")
    day, hour, minute, second, part, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "MR_INSTANT")
    offset = 0
    if zone != "Z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "MR_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(part or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "MR_INSTANT")
    return result


def _index(rows):
    _need(type(rows) is list, "MR_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row["id"])
        _need(identity not in result, "MR_DUPLICATE_ID")
        result[identity] = row
    return result


def _ids(values):
    _need(type(values) is list and all(type(value) is str and value for value in values), "MR_POPULATION_IDS")
    _need(len(set(values)) == len(values), "MR_DUPLICATE_POPULATION_ID")
    return set(values)


def _line(value):
    _text(value)
    prefix, marker, suffix = value.rpartition("#")
    _need(bool(prefix and marker and suffix), "MR_ORIGINAL_LINE_REFERENCE")
    return value


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "policy", "research", "terms", "cost_basis", "qualifications", "cb_switch", "run", *SOURCE_ARRAYS, "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "merchandising-reprice-neutral/1", "MR_SCHEMA")
    scope, policy, run = data["scope"], data["policy"], data["run"]
    case_id = _text(data["case_id"])
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "MR_CURRENCY")
    _need(policy == {"id": POLICY_ID, "revision": "1", "method": "trigger_period_catchup", "credit_profile": "complete_approved_zero_cb_credit",
                     "amounts": "exact_no_rounding", "negative_adjustments": "reject", "cash_date_basis": "supplied_utc_date",
                     "evidence_class": "research_assumption", "professional_review": "proposed"}, "MR_SELECTED_POLICY")
    _fields(data["research"], {"rr04_sha256", "ld03_sha256", "contract_url", "clause_locator"})
    _need(data["research"]["contract_url"] == SOURCE_URL and data["research"]["clause_locator"] == "3.2(a)(i)-(v);3.2(c);3.2(d)(i)-(ii)(a);Exhibit CB", "MR_RESEARCH_SOURCE")
    for key in ("rr04_sha256", "ld03_sha256"):
        _need(re.fullmatch(r"[0-9a-f]{64}", data["research"][key]) is not None, "MR_RESEARCH_PIN")
    _fields(run, {"view_id", "mode"})
    _need(run["mode"] in ("final", "preview"), "MR_RUN_MODE")
    rows = {name: _index(data[name]) for name in SOURCE_ARRAYS}
    for key in ("receipts", "box_office", "issues", "payments", "applications"):
        source_refs = [row["source_ref"] for row in rows[key].values()]
        _need(len(set(source_refs)) == len(source_refs), "MR_DUPLICATE_SOURCE_VIEW")
    periods, views, evidence = rows["periods"], rows["views"], rows["evidence"]
    _need(1 <= len(periods) <= 8 and len(views) == len(periods), "MR_FINITE_PERIOD_BOUND")
    _need(run["view_id"] in views, "MR_CURRENT_VIEW_REQUIRED")
    current_view = views[run["view_id"]]
    cutoff = _instant(current_view["cutoff"])
    current_period_id = current_view["period_id"]
    _need(current_period_id in periods, "MR_UNKNOWN_PERIOD")
    ordered = sorted(periods.values(), key=lambda row: row["period"]["start"])
    _need(ordered[-1]["id"] == current_period_id, "MR_CURRENT_FINAL_PERIOD")
    for index, row in enumerate(ordered):
        _fields(row, {"id", "period", "scope", "observed_at", "source_ref", "evidence_ref"})
        first, last = _period(row["period"])
        if index:
            _need(ordered[index - 1]["period"]["end"] == row["period"]["start"], "MR_PERIOD_ADJACENCY")
    initial_date = _period(ordered[0]["period"])[0]

    for row in evidence.values():
        _fields(row, {"id", "scope", "kind", "approved", "observed_at", "source_ref"})
        _need(row["scope"] == scope, "MR_EVIDENCE_SCOPE")
        _need(row["approved"] is True, "MR_EVIDENCE_APPROVAL")
        _text(row["kind"]); _text(row["source_ref"])
        _need(_instant(row["observed_at"]) < cutoff, "MR_EVIDENCE_AFTER_CUTOFF")

    def support(row, before=cutoff, kind=None):
        _need(row["scope"] == scope, "MR_FACT_SCOPE")
        _text(row["source_ref"])
        _need(row["evidence_ref"] in evidence, "MR_EVIDENCE_REQUIRED")
        item = evidence[row["evidence_ref"]]
        _need(_instant(row["observed_at"]) < before and _instant(item["observed_at"]) < before, "MR_SOURCE_AFTER_CUTOFF")
        if kind:
            _need(item["kind"] == kind, "MR_EVIDENCE_KIND")

    terms, cost, qualification, cb = data["terms"], data["cost_basis"], data["qualifications"], data["cb_switch"]
    _fields(terms, {"id", "version", "scope", "effective", "production_charge_rate", "license_deduction_rate", "multipliers", "rates", "approved", "recorded_date", "observed_at", "source_ref", "evidence_ref"})
    support(terms, kind="fixed-approved-contract-terms")
    _need(terms["approved"] is True and _day(terms["recorded_date"]) <= initial_date, "MR_TERMS_AUTHORITY")
    _need(_period(terms["effective"])[0] <= initial_date and _period(terms["effective"])[1] >= _period(ordered[-1]["period"])[1], "MR_TERMS_EFFECTIVE")
    _need([_q(value) for value in terms["multipliers"]] == [Fraction(7, 4), 2, Fraction(5, 2)]
          and [_q(value) for value in terms["rates"]] == [Fraction(13, 200), Fraction(3, 40), Fraction(7, 80)]
          and _q(terms["production_charge_rate"]) == Fraction(3, 20) and _q(terms["license_deduction_rate"]) == Fraction(3, 10), "MR_FIXED_SOURCED_TERMS")
    _fields(cost, {"id", "scope", "production_cost", "funding_charge", "observed_at", "source_ref", "evidence_ref"})
    support(cost, kind="original-production-and-funding-stage")
    production, funding = _q(cost["production_cost"]), _q(cost["funding_charge"])
    charge = production * _q(terms["production_charge_rate"])
    thresholds = [production * _q(multiplier) + charge + funding for multiplier in terms["multipliers"]]
    _fields(qualification, {"id", "scope", "graphic_units", "units_date", "comics_rank", "rank_date", "photography_date", "feature_produced", "feature_released", "approved", "observed_at", "source_ref", "evidence_ref"})
    support(qualification, kind="approved-feature-and-pre-photography-records")
    _need(qualification["approved"] is True and qualification["feature_produced"] is True and qualification["feature_released"] is True
          and _q(qualification["graphic_units"]) >= 25000 and 0 < _q(qualification["comics_rank"]) <= 200
          and _q(qualification["graphic_units"]).denominator == 1 and _q(qualification["comics_rank"]).denominator == 1
          and _day(qualification["units_date"]) < _day(qualification["photography_date"])
          and _day(qualification["rank_date"]) < _day(qualification["photography_date"]), "MR_QUALIFICATION_REQUIRED")
    if type(cb) is not dict:
        raise MerchandisingRepriceOracleError("MR_CB_RECLASSIFICATION_REQUIRED")
    _fields(cb, {"id", "scope", "complete", "approved", "effective_date", "receipt_ids", "credit_line_ids", "prior_owner_entitlement", "prior_credit_total", "removed_from_defined_receipts", "included_in_nmi", "observed_at", "source_ref", "evidence_ref"})
    support(cb, kind="complete_cb_reclassification_zero_credit")
    _need(cb["complete"] is True and cb["approved"] is True and cb["removed_from_defined_receipts"] is True and cb["included_in_nmi"] is True, "MR_CB_RECLASSIFICATION_REQUIRED")
    _need(_q(cb["prior_owner_entitlement"]) == 0 and _q(cb["prior_credit_total"]) == 0 and _ids(cb["credit_line_ids"]) == set(), "MR_NONZERO_CB_VARIANT_REQUIRED")

    _need(len(rows["receipts"]) <= 32 and len(rows["box_office"]) <= 16 and len(rows["issues"]) <= 8
          and len(rows["payments"]) <= 32 and len(rows["applications"]) <= 64, "MR_FINITE_RECORD_BOUND")
    receipt_refs = set()
    for row in rows["receipts"].values():
        _fields(row, {"id", "scope", "period_id", "amount", "received_date", "recognition_date", "qualifying", "lane", "receipt_ref", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="actual_license_cash_receipt")
        _need(row["period_id"] in periods, "MR_RECEIPT_PERIOD_REFERENCE")
        first, last = _period(periods[row["period_id"]]["period"])
        _need(first <= _day(row["recognition_date"]) < last and _day(row["received_date"]) == _day(row["recognition_date"]), "MR_RECEIPT_RECOGNITION_DATE")
        _need(_day(row["received_date"]).toordinal() * 86400 <= _instant(row["observed_at"]), "MR_RECEIPT_OBSERVATION_ORDER")
        _need(type(row["qualifying"]) is bool and row["lane"] == "third_party_license", "MR_LICENSE_LANE")
        reference = _line(row["receipt_ref"])
        _need(reference not in receipt_refs, "MR_DUPLICATE_LICENSE_CASH_LINE")
        receipt_refs.add(reference); _q(row["amount"])
    before_switch = {row["id"] for row in rows["receipts"].values() if row["qualifying"] and _day(row["recognition_date"]) <= _day(cb["effective_date"])}
    _need(_ids(cb["receipt_ids"]) == before_switch, "MR_CB_SOURCE_LINEAGE")
    previous_gross, previous_day = Fraction(), None
    for row in sorted(rows["box_office"].values(), key=lambda row: row["effective_date"]):
        _fields(row, {"id", "scope", "gross", "effective_date", "recorded_date", "metric", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="authoritative_daily_variety_box_office")
        day, gross = _day(row["effective_date"]), _q(row["gross"])
        _need(row["metric"] == "Daily_Variety_US_Canada_theatrical_cumulative", "MR_BOX_OFFICE_METRIC")
        _need(day <= _day(row["recorded_date"]), "MR_BOX_OFFICE_DATE")
        _need(_day(row["recorded_date"]).toordinal() * 86400 <= _instant(row["observed_at"]), "MR_BOX_OFFICE_OBSERVATION_ORDER")
        _need(previous_day is None or previous_day < day, "MR_BOX_OFFICE_AMENDMENT_REQUIRED")
        _need(previous_gross <= gross, "MR_DECREASING_BOX_OFFICE_POLICY_REQUIRED")
        previous_day, previous_gross = day, gross

    by_period = {}
    for row in views.values():
        _fields(row, {"id", "source_case_id", "period_id", "mode", "as_of", "cutoff", "coverage_end", "recognition_id", "scope", "approved", "observed_at", "source_ref", "evidence_ref"})
        support(row)
        _need(row["period_id"] in periods and row["period_id"] not in by_period, "MR_VIEW_PERIOD_CARDINALITY")
        by_period[row["period_id"]] = row
        _need(row["approved"] is True and row["mode"] == (run["mode"] if row["id"] == current_view["id"] else "final"), "MR_RECOGNITION_AUTHORITY")
        first, last = _period(periods[row["period_id"]]["period"])
        coverage = _day(row["coverage_end"])
        _need(first < coverage <= last and _day(row["as_of"]) == coverage - timedelta(days=1)
              and _instant(row["cutoff"]) >= coverage.toordinal() * 86400, "MR_VIEW_COVERAGE")
        _need((row["mode"] == "final" and coverage == last and bool(row["recognition_id"]))
              or (row["mode"] == "preview" and coverage < last and row["recognition_id"] == ""), "MR_PREVIEW_NOT_FINAL")
        _need(row["source_case_id"] != "" and (row["id"] != current_view["id"] or row["source_case_id"] == case_id), "MR_VIEW_CASE_IDENTITY")
        _need(_instant(row["observed_at"]) < _instant(row["cutoff"]), "MR_VIEW_OBSERVATION")
    _need(set(by_period) == set(periods), "MR_VIEW_PERIOD_CARDINALITY")
    for row in rows["receipts"].values():
        _need(_instant(row["observed_at"]) < _instant(by_period[row["period_id"]]["cutoff"]), "MR_LATE_HISTORICAL_RECEIPT_VARIANT_REQUIRED")
    for row in rows["box_office"].values():
        containing = [period for period in ordered if _period(period["period"])[0] <= _day(row["effective_date"]) < _period(period["period"])[1]]
        _need(len(containing) == 1 and _instant(row["observed_at"]) < _instant(by_period[containing[0]["id"]]["cutoff"]), "MR_CORRECTED_THRESHOLD_VARIANT_REQUIRED")
    final_recognition_ids = [row["recognition_id"] for row in views.values() if row["mode"] == "final"]
    _need(len(set(final_recognition_ids)) == len(final_recognition_ids), "MR_DUPLICATE_RECOGNITION")
    _need(len({row["source_case_id"] for row in views.values()}) == len(views), "MR_DUPLICATE_CASE")

    for row in rows["populations"].values():
        _fields(row, {"id", "view_id", "scope", "complete", "receipt_coverage", "receipt_ids", "receipt_total", "adjustment_ids", "adjustment_total",
                      "box_office_ids", "issue_ids", "issue_total", "payment_ids", "disbursement_ids", "payment_total", "application_ids", "application_total", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="complete_original_known_population")
        _need(row["view_id"] in views, "MR_POPULATION_VIEW_REFERENCE")
    for row in rows["no_default"].values():
        _fields(row, {"id", "view_id", "scope", "approved", "not_in_material_default", "observed_at", "source_ref", "evidence_ref"})
        support(row)
        _need(row["view_id"] in views, "MR_NO_DEFAULT_VIEW_REFERENCE")

    recognized, recognition_history, snapshots, prefix_states = {}, [], [], []
    previous_cutoff = None
    for index, period in enumerate(ordered):
        view = by_period[period["id"]]
        before = _instant(view["cutoff"])
        _need(previous_cutoff is None or previous_cutoff < before, "MR_HISTORICAL_CUTOFF_ORDER")
        previous_cutoff = before
        for original in (period, terms, cost, qualification, cb):
            support(original, before)
        support(view, before)
        default = [row for row in rows["no_default"].values() if row["view_id"] == view["id"]]
        _need(len(default) == 1, "MR_NO_DEFAULT_REQUIRED")
        support(default[0], before)
        _need(default[0]["approved"] is True and default[0]["not_in_material_default"] is True, "MR_NO_DEFAULT_REQUIRED")
        available_receipts = [row for row in rows["receipts"].values() if _day(row["recognition_date"]) < _day(view["coverage_end"]) and _instant(row["observed_at"]) < before]
        for row in available_receipts:
            support(row, before)
        available_box = [row for row in rows["box_office"].values() if _day(row["effective_date"]) <= _day(view["as_of"])
                         and _day(row["recorded_date"]) <= _day(view["as_of"]) and _instant(row["observed_at"]) < before]
        for row in available_box:
            support(row, before)
        _need(bool(available_box), "MR_BOX_OFFICE_HISTORY_REQUIRED")
        selected = max(available_box, key=lambda row: row["effective_date"])
        rate, tier = Fraction(), 0
        for tier_index, threshold in enumerate(thresholds, 1):
            if _q(selected["gross"]) >= threshold:
                rate, tier = _q(terms["rates"][tier_index - 1]), tier_index
        # This bounded CB-reclassified lane starts after first qualification.
        _need(tier > 0, "MR_PRE_SWITCH_VARIANT_REQUIRED")
        first_qualified = min((_day(row["effective_date"]) for row in available_box if _q(row["gross"]) >= thresholds[0]))
        _need(_day(cb["effective_date"]) == first_qualified, "MR_CB_SWITCH_DATE")
        current_earnings = catchup = Fraction()
        attributions = []
        for row in sorted(available_receipts, key=lambda row: row["id"]):
            gross = _q(row["amount"])
            deduction = gross * _q(terms["license_deduction_rate"]) if row["qualifying"] else Fraction()
            basis = gross - deduction if row["qualifying"] else Fraction()
            target = basis * rate
            old = recognized.get(row["id"], Fraction())
            delta = target - old
            _need(delta >= 0, "MR_NEGATIVE_RECOGNITION_POLICY_REQUIRED")
            current = row["period_id"] == period["id"]
            if current:
                current_earnings += delta
            else:
                catchup += delta
            attributions.append({"receipt_id": row["id"], "earned_period_id": row["period_id"], "receipt_ref": row["receipt_ref"], "license_cash": gross,
                                 "qualifying": row["qualifying"], "license_deduction": deduction, "nmi": basis, "rate": rate,
                                 "previously_recognized": old, "target_entitlement": target, "recognition_delta": delta,
                                 "kind": "current_earnings" if current else "historical_catchup"})
        new_recognition = current_earnings + catchup
        cumulative_target = sum((row["target_entitlement"] for row in attributions), Fraction())
        if view["mode"] == "final":
            for row in attributions:
                recognized[row["receipt_id"]] = row["target_entitlement"]
            recognition_history.append({"id": view["recognition_id"], "view_id": view["id"], "period_id": period["id"], "source_case_id": view["source_case_id"],
                                        "cutoff": view["cutoff"], "current_earnings": current_earnings, "catchup": catchup, "amount": new_recognition,
                                        "attributions": attributions})
        snapshot = {"view_id": view["id"], "source_case_id": view["source_case_id"], "period_id": period["id"], "mode": view["mode"],
                    "as_of": view["as_of"], "cutoff": view["cutoff"], "coverage_end": view["coverage_end"], "box_office_id": selected["id"],
                    "box_office_gross": _q(selected["gross"]), "tier": tier, "rate": rate, "current_earnings": current_earnings,
                    "catchup": catchup, "new_recognition_candidate": new_recognition, "cumulative_entitlement_asof": cumulative_target,
                    "recognized_cumulative": sum(recognized.values(), Fraction()), "attributions": attributions}
        snapshots.append(snapshot)

    recognition_map = {row["id"]: row for row in recognition_history}
    issue_calculations = set()
    for row in rows["issues"].values():
        _fields(row, {"id", "scope", "version", "recognition_id", "amount", "issued_date", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="original_statement_issue")
        _need(row["version"] == "1" and row["recognition_id"] in recognition_map and row["recognition_id"] not in issue_calculations, "MR_ISSUE_RECOGNITION_REFERENCE")
        original = recognition_map[row["recognition_id"]]
        _need(_q(row["amount"]) == original["amount"] and _day(row["issued_date"]) >= _period(periods[original["period_id"]]["period"])[1]
              and _day(row["issued_date"]).toordinal() * 86400 >= _instant(original["cutoff"]), "MR_ORIGINAL_ISSUE_AMOUNT_DATE")
        _need(_day(row["issued_date"]).toordinal() * 86400 <= _instant(row["observed_at"]), "MR_ISSUE_OBSERVATION_ORDER")
        issue_calculations.add(row["recognition_id"])
    disbursements = set()
    for row in rows["payments"].values():
        _fields(row, {"id", "scope", "bank_disbursement_id", "amount", "paid_date", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="actual_participant_disbursement")
        _need(row["bank_disbursement_id"] not in disbursements, "MR_DUPLICATE_PARTICIPANT_DISBURSEMENT")
        disbursements.add(_text(row["bank_disbursement_id"])); _positive(row["amount"])
        _need(_day(row["paid_date"]).toordinal() * 86400 <= _instant(row["observed_at"]), "MR_PAYMENT_OBSERVATION_ORDER")
    for row in rows["applications"].values():
        _fields(row, {"id", "scope", "payment_id", "issue_id", "amount", "applied_date", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="actual_payment_application")
        _need(row["payment_id"] in rows["payments"] and row["issue_id"] in rows["issues"], "MR_APPLICATION_REFERENCE")
        payment, issue = rows["payments"][row["payment_id"]], rows["issues"][row["issue_id"]]
        _need(_day(issue["issued_date"]) <= _day(payment["paid_date"]) <= _day(row["applied_date"]), "MR_APPLICATION_DATE_ORDER")
        _need(max(_instant(payment["observed_at"]), _instant(issue["observed_at"])) <= _instant(row["observed_at"]), "MR_APPLICATION_OBSERVATION_ORDER")
        _need(_day(row["applied_date"]).toordinal() * 86400 <= _instant(row["observed_at"]), "MR_APPLICATION_OBSERVATION_ORDER")
        _positive(row["amount"])

    def state(index, accounting):
        view, period = by_period[ordered[index]["id"]], ordered[index]
        before = _instant(view["cutoff"])
        processed = {row["id"] for row in ordered[:index + 1]}
        source = {}
        for key in SOURCE_ARRAYS:
            source[key] = []
            for row in rows[key].values():
                visible = _instant(row["observed_at"]) < before
                if key == "periods":
                    visible = visible and row["id"] in processed
                elif key == "views":
                    visible = visible and row["period_id"] in processed
                elif key in ("populations", "no_default"):
                    visible = visible and views[row["view_id"]]["period_id"] in processed
                elif key == "receipts":
                    visible = visible and row["period_id"] in processed
                elif key == "box_office":
                    visible = visible and _day(row["recorded_date"]) <= _day(view["as_of"])
                if visible:
                    source[key].append(row)
            source[key].sort(key=lambda row: row["id"])
        snapshot = snapshots[index]
        historic = recognition_history[:index + 1]
        amounts = {row["receipt_id"]: row["target_entitlement"] for row in snapshot["attributions"]}
        return {"scope": dict(scope), "purpose": "first_dollar_merchandising", "policy": dict(policy), "research": dict(data["research"]),
                "terms": dict(terms), "cost_basis": dict(cost), "qualifications": dict(qualification), "cb_switch": dict(cb),
                "boundary": period["period"]["end"], "origin": "prior_result", "source_case_id": view["source_case_id"],
                "last_view_id": view["id"], "recognized_rows": [{"receipt_id": identity, "amount": amounts[identity]} for identity in sorted(amounts)],
                "recognition_history": historic, "known_issued": accounting["known_issued"], "actual_paid": accounting["actual_paid"],
                "issued_outstanding": accounting["issued_outstanding"], "recognized_unissued": snapshot["recognized_cumulative"] - accounting["known_issued"],
                "sources": source}

    for index, snapshot in enumerate(snapshots):
        view = views[snapshot["view_id"]]
        before = _instant(view["cutoff"])
        available = {}
        for key in ("receipts", "box_office", "issues", "payments", "applications"):
            available[key] = {identity: row for identity, row in rows[key].items() if _instant(row["observed_at"]) < before}
        available["receipts"] = {identity: row for identity, row in available["receipts"].items() if _day(row["recognition_date"]) < _day(view["coverage_end"])}
        available["box_office"] = {identity: row for identity, row in available["box_office"].items() if _day(row["recorded_date"]) <= _day(view["as_of"])}
        controls = [row for row in rows["populations"].values() if row["view_id"] == view["id"]]
        if len(controls) != 1 or controls[0]["complete"] is not True:
            raise MerchandisingRepriceOracleError("MR_COMPLETE_POPULATION_REQUIRED", "no_event_supplied")
        control = controls[0]
        support(control, before)
        _need(control["receipt_coverage"] == {"start": initial_date.isoformat(), "end": view["coverage_end"]}, "MR_RECEIPT_POPULATION_COVERAGE")
        for key, ids, amount in (("receipts", "receipt_ids", "receipt_total"), ("issues", "issue_ids", "issue_total"),
                                 ("payments", "payment_ids", "payment_total"), ("applications", "application_ids", "application_total")):
            _need(_ids(control[ids]) == set(available[key]) and _q(control[amount]) == sum((_q(row["amount"]) for row in available[key].values()), Fraction()), "MR_ORIGINAL_POPULATION_CONTROL")
        _need(_ids(control["box_office_ids"]) == set(available["box_office"])
              and _ids(control["disbursement_ids"]) == {row["bank_disbursement_id"] for row in available["payments"].values()}, "MR_ORIGINAL_POPULATION_CONTROL")
        _need(_ids(control["adjustment_ids"]) == set() and _q(control["adjustment_total"]) == 0, "MR_NONZERO_ADJUSTMENT_VARIANT_REQUIRED")
        summarized = [row for collection in available.values() for row in collection.values()]
        for original in summarized:
            support(original, before)
        _need(all(_instant(row["observed_at"]) <= _instant(control["observed_at"]) for row in summarized), "MR_POPULATION_OBSERVATION_ORDER")
        per_payment = {identity: Fraction() for identity in available["payments"]}
        per_issue = {identity: Fraction() for identity in available["issues"]}
        for row in available["applications"].values():
            _need(row["payment_id"] in per_payment and row["issue_id"] in per_issue, "MR_KNOWN_APPLICATION_REFERENCE")
            amount = _q(row["amount"])
            per_payment[row["payment_id"]] += amount
            per_issue[row["issue_id"]] += amount
        _need(all(amount == _q(available["payments"][identity]["amount"]) for identity, amount in per_payment.items()), "MR_PAYMENT_APPLICATION_CONSERVATION")
        _need(all(amount <= _q(available["issues"][identity]["amount"]) for identity, amount in per_issue.items()), "MR_ISSUE_OVERPAYMENT")
        known_issued = sum((_q(row["amount"]) for row in available["issues"].values()), Fraction())
        paid = sum(per_payment.values(), Fraction())
        _need(known_issued <= snapshot["recognized_cumulative"], "MR_ISSUED_EXCEEDS_RECOGNIZED")
        outstanding = known_issued - paid
        candidate_unissued = snapshot["cumulative_entitlement_asof"] - known_issued
        snapshot.update(known_issue_ids=sorted(available["issues"]), known_payment_ids=sorted(available["payments"]),
                        known_issued=known_issued, actual_paid=paid, issued_outstanding=outstanding,
                        candidate_unissued=candidate_unissued, candidate_total_unpaid=candidate_unissued + outstanding,
                        obligation_lines=[{"issue_id": identity, "original_amount": _q(available["issues"][identity]["amount"]),
                                           "actual_applied": per_issue[identity], "outstanding": _q(available["issues"][identity]["amount"]) - per_issue[identity]} for identity in sorted(per_issue)])
        if view["mode"] == "final":
            prefix_states.append(state(index, snapshot))

    opening = data["opening_state"]
    _need(type(opening) is dict, "MR_OPENING_REQUIRED")
    if len(ordered) == 1:
        _need(opening == {"scope": scope, "purpose": "first_dollar_merchandising", "policy": policy,
                          "boundary": ordered[0]["period"]["start"], "origin": "genesis", "source_case_id": "genesis"}
              and "prior_result" not in data, "MR_GENESIS")
    else:
        expected = exact_json(prefix_states[len(ordered) - 2])
        _need(opening.get("origin") in ("prior_result", "supplied_history"), "MR_OPENING_ORIGIN")
        expected["origin"] = opening["origin"]
        _need(opening == expected, "MR_OPENING_HISTORY_RECONCILIATION")
        if opening["origin"] == "prior_result":
            _need("prior_result" in data, "MR_PREDECESSOR_REQUIRED")
            prior = data["prior_result"]
            _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
            _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id
                  and prior["closing_state"] == opening and _period(prior["period"])[1] == _period(ordered[-1]["period"])[0], "MR_PREDECESSOR_MISMATCH")
            if "result_ref" in prior:
                _text(prior["result_ref"])
        else:
            _need("prior_result" not in data, "MR_SUPPLIED_HISTORY_NOT_CANONICAL")
    current = snapshots[-1]
    final = run["mode"] == "final"
    return {"source_case_id": case_id, "period": dict(periods[current_period_id]["period"]), "status": "calculated" if final else "preview",
            "consumable_state": final, "production_cost": production, "production_charge": charge, "funding_charge": funding,
            "thresholds": thresholds, **current, "recognized_this_run": current["new_recognition_candidate"] if final else Fraction(),
            "as_known_snapshots": snapshots, "recognition_history": recognition_history,
            "closing_state": prefix_states[-1] if final else None,
            "issue_status": "original_issues_retained_no_new_issue_inferred", "payment_status": "complete_original_population",
            "recognition_status": "final_recognition" if final else "candidate_only_not_recognized",
            "status_meaning": "proposed trigger-period recognition; original issue and actual payment records stay separate"}


def merchandising_reprice(data):
    """Replay original known views independently; no compiler or SPL imports."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, MerchandisingRepriceOracleError):
            raise
        raise MerchandisingRepriceOracleError("MR_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
