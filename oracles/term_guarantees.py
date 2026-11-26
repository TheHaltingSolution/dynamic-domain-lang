"""Independent fixed-term caps/floors and evidenced funded-prepayment controls."""
from datetime import date
from fractions import Fraction
import re


POLICY_ID = "SYNTHETIC-TERM-GUARANTEES-01"
METHODS = {"term_cap", "term_floor_at_end", "actual_funded_advance", "floor_cap_advance_including_topup",
           "floor_cap_advance_earned_only", "cap_floor_advance_including_topup", "cap_floor_advance_earned_only"}
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}
MONEY_METERS = ("term_earned", "term_recognized_entitlement", "term_cap_consumed", "total_funded", "total_recovered", "prepayment")


class TermGuaranteeOracleError(ValueError):
    def __init__(self, code, funding_evidence_status=None):
        super().__init__(code)
        self.funding_evidence_status = funding_evidence_status


def _need(condition, code):
    if not condition:
        raise TermGuaranteeOracleError(code)


def _fields(value, required, optional=()):
    _need(type(value) is dict and required <= value.keys() and value.keys() <= required | set(optional), "TERM_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "TERM_IDENTITY_REQUIRED")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "TERM_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "TERM_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise TermGuaranteeOracleError("TERM_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "TERM_PERIOD")
    return start, end


def _instant(value):
    _need(type(value) is str, "TERM_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "TERM_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "TERM_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "TERM_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "TERM_INSTANT")
    return result


def _index(rows):
    _need(type(rows) is list, "TERM_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row["id"])
        _need(identity not in result, "TERM_DUPLICATE_ID")
        result[identity] = row
    return result


def _stages(method, floor, cap, face, meters, earned, funded, final):
    cap_active = method == "term_cap" or method.startswith(("floor_cap_", "cap_floor_"))
    floor_active = method == "term_floor_at_end" or method.startswith(("floor_cap_", "cap_floor_"))
    advance_active = method == "actual_funded_advance" or method.startswith(("floor_cap_", "cap_floor_"))
    floor_topup, cap_input, cap_applied = Fraction(), Fraction(), Fraction()
    if method == "term_cap":
        cap_input = earned
        cap_applied = min(earned, cap - meters["term_cap_consumed"])
        entitlement, retained_earned, retained_topup = cap_applied, cap_applied, Fraction()
    elif method == "term_floor_at_end":
        floor_topup = max(floor - meters["term_recognized_entitlement"] - earned, Fraction()) if final else Fraction()
        entitlement, retained_earned, retained_topup = earned + floor_topup, earned, floor_topup
    elif method == "actual_funded_advance":
        entitlement, retained_earned, retained_topup = earned, earned, Fraction()
    elif method.startswith("floor_cap_"):
        floor_topup = max(floor - meters["term_recognized_entitlement"] - earned, Fraction()) if final else Fraction()
        cap_input = earned + floor_topup
        cap_applied = min(cap_input, cap - meters["term_cap_consumed"])
        entitlement = cap_applied
        retained_earned, retained_topup = min(earned, entitlement), entitlement - min(earned, entitlement)
    else:
        cap_input = earned
        cap_applied = min(earned, cap - meters["term_cap_consumed"])
        floor_topup = max(floor - meters["term_recognized_entitlement"] - cap_applied, Fraction()) if final else Fraction()
        entitlement, retained_earned, retained_topup = cap_applied + floor_topup, cap_applied, floor_topup
    available = meters["prepayment"] + funded
    _need(meters["total_funded"] + funded <= face, "TERM_FUNDED_CEILING")
    recovery_base = (retained_earned if method.endswith("earned_only") else entitlement) if advance_active else Fraction()
    recovered = min(available, recovery_base)
    payable = entitlement - recovered
    closing = {"term_earned": meters["term_earned"] + earned,
               "term_recognized_entitlement": meters["term_recognized_entitlement"] + entitlement,
               "term_cap_consumed": meters["term_cap_consumed"] + cap_applied,
               "total_funded": meters["total_funded"] + funded, "total_recovered": meters["total_recovered"] + recovered,
               "prepayment": available - recovered, "term_closed": final}
    _need(closing["prepayment"] == closing["total_funded"] - closing["total_recovered"]
          and payable + recovered == entitlement, "TERM_RECONCILIATION")
    _need(not cap_active or closing["term_cap_consumed"] <= cap, "TERM_CAP_RECONCILIATION")
    return {"earned": earned, "is_term_end": final, "floor_active": floor_active, "cap_active": cap_active, "advance_active": advance_active,
            "floor_topup_before_cap": floor_topup, "cap_stage_input": cap_input, "cap_applied": cap_applied,
            "retained_earned": retained_earned, "retained_topup": retained_topup, "entitlement": entitlement,
            "new_actual_funding": funded, "available_prepayment": available, "recovery_base": recovery_base,
            "recovered": recovered, "payable_calculated": payable,
            "unmet_floor_at_term_end": max(floor - closing["term_recognized_entitlement"], Fraction()) if final and floor_active else Fraction(),
            "closing_meters": closing}


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "period", "as_of", "cutoff", "policy", "term", "earnings", "fundings", "evidence", "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "term-guarantees-neutral/1", "TERM_NEUTRAL_SCHEMA")
    case_id, scope, policy, term, opening = _text(data["case_id"]), data["scope"], data["policy"], data["term"], data["opening_state"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "TERM_CURRENCY")
    _fields(policy, {"id", "revision", "method", "floor_timing", "cap_reset", "cap_reduction_order", "funding_date_basis", "term_availability", "rounding", "evidence_class"})
    method = policy["method"]
    _need(method in METHODS, "TERM_METHOD_REQUIRED")
    _need({key: value for key, value in policy.items() if key != "method"}
          == {"id": POLICY_ID, "revision": "1", "floor_timing": "term_end", "cap_reset": "never_within_term",
              "cap_reduction_order": "topup_before_earned", "funding_date_basis": "supplied_utc_date", "term_availability": "known_at_open_utc",
              "rounding": "exact_no_rounding", "evidence_class": "research_assumption"}, "TERM_SELECTED_POLICY")
    advance_active = method == "actual_funded_advance" or method.startswith(("floor_cap_", "cap_floor_"))
    _fields(term, {"id", "revision", "scope", "period", "floor", "cap", "recoupable_minimum_face", "approved_date", "recorded_date", "observed_at", "source_ref", "evidence_ref"})
    term_id = _text(term["id"])
    _text(term["revision"]); _text(term["source_ref"])
    _need(term["scope"] == scope, "TERM_TERM_SCOPE")
    term_start, term_end = _period(term["period"])
    start, end = _period(data["period"])
    _need(term_start <= start < end <= term_end, "TERM_PERIOD_OUTSIDE_TERM")
    as_of, cutoff = _day(data["as_of"]), _instant(data["cutoff"])
    _need(_day(term["approved_date"]) <= _day(term["recorded_date"]) <= min(as_of, term_start)
          and _instant(term["observed_at"]) < _instant(term["period"]["start"] + "T00:00:00Z"), "TERM_AVAILABILITY")
    _need(_instant(term["observed_at"]) < cutoff, "TERM_OBSERVATION_CUTOFF")
    floor, cap, face = (_q(term[key]) for key in ("floor", "cap", "recoupable_minimum_face"))
    if method == "term_cap":
        _need(floor == face == 0, "TERM_UNUSED_AMOUNT")
    elif method == "term_floor_at_end":
        _need(cap == face == 0, "TERM_UNUSED_AMOUNT")
    elif method == "actual_funded_advance":
        _need(floor == cap == 0, "TERM_UNUSED_AMOUNT")
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _fields(row, {"id", "scope", "observed_at", "kind"}, {"term_id", "period", "funding_ids", "disbursement_ids", "funded_total"})
        _need(row["scope"] == scope, "TERM_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "TERM_EVIDENCE_CUTOFF")
        if row["kind"] == "complete_funding_population":
            _need(row.get("term_id") == term_id and "period" in row, "TERM_FUNDING_COMPLETENESS_SCOPE")
            population_start, population_end = _period(row["period"])
            _need(term_start <= population_start < population_end <= term_end, "TERM_FUNDING_COMPLETENESS_SCOPE")
            for field in ("funding_ids", "disbursement_ids"):
                values = row.get(field)
                _need(type(values) is list and all(type(value) is str and value for value in values)
                      and len(set(values)) == len(values), "TERM_FUNDING_POPULATION_CONTROL")
            _q(row["funded_total"])
        else:
            _need(not ({"term_id", "period", "funding_ids", "disbursement_ids", "funded_total"} & row.keys()), "TERM_RECORD_FIELDS")
    _need(term["evidence_ref"] in evidence, "TERM_EVIDENCE_REQUIRED")
    _fields(opening, {"scope", "purpose", "policy_id", "policy_revision", "method", "cap_reduction_order", "term", "boundary", "origin", "source_case_id",
                      *MONEY_METERS, "term_closed", "period_history"})
    _need(opening["scope"] == scope and opening["purpose"] == "term_guarantee_and_prepayment", "TERM_OPENING_SCOPE")
    _need((opening["policy_id"], opening["policy_revision"], opening["method"], opening["cap_reduction_order"])
          == (POLICY_ID, "1", method, "topup_before_earned"), "TERM_OPENING_METHOD")
    _need(opening["term"] == term, "TERM_AMENDMENT_REQUIRED")
    _need(opening["boundary"] == data["period"]["start"], "TERM_OPENING_BOUNDARY")
    opening_meters = {key: _q(opening[key]) for key in MONEY_METERS}
    _need(type(opening["term_closed"]) is bool, "TERM_CLOSED_FLAG")
    _need(advance_active or opening_meters["prepayment"] == 0, "TERM_ADVANCE_OUTSIDE_METHOD")
    history = opening["period_history"]
    _need(type(history) is list, "TERM_HISTORY_REQUIRED")
    if opening["origin"] == "genesis":
        _need(not any(opening_meters.values()) and not history and opening["term_closed"] is False
              and opening["source_case_id"] == "genesis" and start == term_start and "prior_result" not in data, "TERM_GENESIS")
    else:
        _need(opening["origin"] == "prior_result" and "prior_result" in data, "TERM_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if "result_ref" in prior:
            _text(prior["result_ref"])
        _, prior_end = _period(prior["period"])
        _need(prior_end == start, "TERM_PREDECESSOR_BOUNDARY")
        _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id
              and prior["closing_state"] == opening, "TERM_PREDECESSOR_MISMATCH")
    used_earnings, used_fundings, used_disbursements, used_sources = set(), set(), set(), set()

    def sources(earnings, fundings, period_start, period_end):
        earned_rows, funded_rows = _index(earnings), _index(fundings)
        _need(advance_active or not funded_rows, "TERM_ADVANCE_OUTSIDE_METHOD")
        if advance_active:
            attestations = [row for row in evidence.values() if row["kind"] == "complete_funding_population"
                            and row["period"] == {"start": period_start.isoformat(), "end": period_end.isoformat()}]
            if not attestations:
                raise TermGuaranteeOracleError("TERM_FUNDING_POPULATION_REQUIRED", "no_event_supplied")
            _need(len(attestations) == 1, "TERM_FUNDING_POPULATION_AMBIGUOUS")
        total_earned, total_funded = Fraction(), Fraction()

        def fact(row, category):
            _need(row["scope"] == scope and row["term_id"] == term_id, "TERM_FACT_SCOPE")
            _need(row["evidence_ref"] in evidence, "TERM_EVIDENCE_REQUIRED")
            _need(_instant(row["observed_at"]) < cutoff, "TERM_FACT_CUTOFF")
            source = (category, _text(row["source_ref"]))
            _need(source not in used_sources, "TERM_SOURCE_ALREADY_RECOGNIZED")
            used_sources.add(source)

        for identity, row in earned_rows.items():
            _fields(row, {"id", "term_id", "scope", "amount", "effective_date", "observed_at", "source_ref", "evidence_ref"})
            _need(identity not in used_earnings, "TERM_EARNING_ALREADY_RECOGNIZED")
            used_earnings.add(identity)
            fact(row, "earning")
            _need(period_start <= _day(row["effective_date"]) < period_end, "TERM_EARNING_PERIOD")
            total_earned += _q(row["amount"])
        for identity, row in funded_rows.items():
            _fields(row, {"id", "disbursement_id", "term_id", "scope", "amount", "funded_date", "funded_at", "observed_at", "approved", "source_ref", "evidence_ref"})
            _need(identity not in used_fundings, "TERM_FUNDING_ALREADY_RECOGNIZED")
            used_fundings.add(identity)
            disbursement = _text(row["disbursement_id"])
            _need(disbursement not in used_disbursements, "TERM_DISBURSEMENT_ALREADY_RECOGNIZED")
            used_disbursements.add(disbursement)
            fact(row, "funding")
            amount, funded, observed = _q(row["amount"]), _instant(row["funded_at"]), _instant(row["observed_at"])
            _need(amount > 0 and row["approved"] is True, "TERM_ACTUAL_FUNDING_REQUIRED")
            funded_day = _day(row["funded_date"])
            _need(funded_day.toordinal() * 86400 <= funded < (funded_day.toordinal() + 1) * 86400, "TERM_FUNDED_UTC_DATE")
            _need(period_start <= funded_day < period_end, "TERM_FUNDING_PERIOD")
            _need(funded <= observed, "TERM_FUNDING_OBSERVATION_ORDER")
            support = evidence[row["evidence_ref"]]
            _need(support["kind"] == "actual_advance_funding" and funded <= _instant(support["observed_at"]), "TERM_ACTUAL_FUNDING_EVIDENCE")
            total_funded += amount
        if advance_active:
            attested = attestations[0]
            _need(set(attested["funding_ids"]) == set(funded_rows)
                  and set(attested["disbursement_ids"]) == {row["disbursement_id"] for row in funded_rows.values()}
                  and _q(attested["funded_total"]) == total_funded, "TERM_FUNDING_POPULATION_CONTROL")
        return total_earned, total_funded, [dict(earned_rows[key]) for key in sorted(earned_rows)], [dict(funded_rows[key]) for key in sorted(funded_rows)]

    meters = {key: Fraction() for key in MONEY_METERS}
    meters["term_closed"] = False
    history_end, history_cases, normalized = term_start, {case_id}, []
    for row in sorted(history, key=lambda record: record["period"]["start"]):
        _fields(row, {"source_case_id", "period", "earnings", "fundings"})
        history_case = _text(row["source_case_id"])
        _need(history_case not in history_cases, "TERM_DUPLICATE_PERIOD_CASE")
        history_cases.add(history_case)
        history_start, period_end = _period(row["period"])
        _need(history_start == history_end and period_end <= start and not meters["term_closed"], "TERM_HISTORY_BOUNDARY")
        earned, funded, earned_records, funded_records = sources(row["earnings"], row["fundings"], history_start, period_end)
        meters = _stages(method, floor, cap, face, meters, earned, funded, period_end == term_end)["closing_meters"]
        history_end = period_end
        normalized.append({**row, "earnings": earned_records, "fundings": funded_records})
    _need(history_end == start and all(meters[key] == opening_meters[key] for key in MONEY_METERS)
          and meters["term_closed"] == opening["term_closed"]
          and (not history or normalized[-1]["source_case_id"] == opening["source_case_id"]), "TERM_OPENING_HISTORY_RECONCILIATION")
    _need(not meters["term_closed"], "TERM_ALREADY_CLOSED")
    earned, funded, earned_records, funded_records = sources(data["earnings"], data["fundings"], start, end)
    result = _stages(method, floor, cap, face, meters, earned, funded, end == term_end)
    current_history = {"source_case_id": case_id, "period": dict(data["period"]), "earnings": earned_records, "fundings": funded_records}
    closing = {"scope": dict(scope), "purpose": "term_guarantee_and_prepayment", "policy_id": POLICY_ID, "policy_revision": "1",
               "method": method, "cap_reduction_order": "topup_before_earned", "term": dict(term), "boundary": data["period"]["end"],
               "origin": "prior_result", "source_case_id": case_id, **result["closing_meters"], "period_history": normalized + [current_history]}
    return {"source_case_id": case_id, "period": dict(data["period"]), "method": method,
            "opening_meters": dict(meters), **result, "closing_state": closing,
            "funding_population_status": ("complete_with_funding" if funded_records else "complete_no_events") if advance_active else "not_applicable",
            "settlement_payment_evidence_status": "no_event_supplied",
            "status_meaning": "calculated entitlement/recovery/payable; actual funding is separate from unknown settlement payment"}


def term_guarantees(data):
    """Return exact controls from original term facts; reject without carry."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, TermGuaranteeOracleError):
            raise
        raise TermGuaranteeOracleError("TERM_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
