"""Independent original-row controls for five fixed-table escalation policies."""
from datetime import date
from fractions import Fraction
import re


POLICY_ID = "SYNTHETIC-ESCALATION-01"
METHODS = {"prospective_split", "current_period_ending_rate", "row_opening_rate", "row_ending_rate", "cumulative_reprice_delta"}
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}


class EscalationOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise EscalationOracleError(code)


def _fields(value, required, optional=()):
    _need(type(value) is dict and required <= value.keys() and value.keys() <= required | set(optional), "ESCALATION_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "ESCALATION_IDENTITY_REQUIRED")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "ESCALATION_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "ESCALATION_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise EscalationOracleError("ESCALATION_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "ESCALATION_PERIOD")
    return start, end


def _instant(value):
    _need(type(value) is str, "ESCALATION_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "ESCALATION_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "ESCALATION_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "ESCALATION_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "ESCALATION_INSTANT")
    return result


def _index(rows):
    _need(type(rows) is list, "ESCALATION_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row["id"])
        _need(identity not in result, "ESCALATION_DUPLICATE_ID")
        result[identity] = row
    return result


def _snapshot(table):
    return {**table, "brackets": sorted(table["brackets"], key=lambda row: row["sequence"])}


def _compute(events, basis, recognized, bands, method):
    def select(value):
        return next(row for row in bands if row["lower"] <= value and (row["upper"] is None or value < row["upper"]))

    period_basis = sum((_q(row["basis"]) for row in events), Fraction())
    ending_band = select(basis + period_basis)
    rows, earned, original_recognized = [], Fraction(), recognized
    for row in sorted(events, key=lambda event: event["sequence"]):
        amount, before = _q(row["basis"]), basis
        after = before + amount
        if method == "prospective_split":
            slices = []
            for band in bands:
                width = max(Fraction(), min(after, band["upper"] if band["upper"] is not None else after) - max(before, band["lower"]))
                if width:
                    slices.append({"bracket_id": band["id"], "width": width, "rate": band["rate"], "amount": width * band["rate"]})
            current = sum((part["amount"] for part in slices), Fraction())
            details = {"kind": "marginal_slices", "slices": slices}
        else:
            band = ending_band if method == "current_period_ending_rate" else select(before if method == "row_opening_rate" else after)
            if method == "cumulative_reprice_delta":
                repriced = after * band["rate"]
                current = repriced - recognized
                _need(current >= 0, "ESCALATION_NEGATIVE_REPRICE_DELTA")
            else:
                current = amount * band["rate"]
            details = {"kind": "selected_rate", "bracket_id": band["id"], "rate": band["rate"]}
        rows.append({"id": row["id"], "sequence": row["sequence"], "basis": amount, "basis_before": before, "basis_after": after,
                     "recognized_before": recognized, "current_result": current, "recognized_after": recognized + current,
                     "rate_details": details, "source_ref": row["source_ref"], "evidence_ref": row["evidence_ref"]})
        earned += current
        recognized += current
        basis = after
    if method == "cumulative_reprice_delta":
        _need(earned == basis * select(basis)["rate"] - original_recognized, "ESCALATION_REPRICE_RECONCILIATION")
    return {"period_basis": period_basis, "closing_basis": basis, "closing_recognized": recognized, "current_result": earned,
            "ending_bracket_id": ending_band["id"], "ending_rate": ending_band["rate"], "rows": rows}


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "period", "as_of", "cutoff", "policy", "bracket_table", "events", "evidence", "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "escalation-neutral/1", "ESCALATION_NEUTRAL_SCHEMA")
    case_id, scope, policy, opening = _text(data["case_id"]), data["scope"], data["policy"], data["opening_state"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "ESCALATION_CURRENCY")
    _fields(policy, {"id", "revision", "method", "equality", "rounding", "evidence_class", "table_availability"})
    method = policy["method"]
    _need(method in METHODS, "ESCALATION_METHOD_REQUIRED")
    _need((policy["id"], policy["revision"], policy["equality"], policy["rounding"], policy["evidence_class"], policy["table_availability"])
          == (POLICY_ID, "1", "lower_inclusive", "exact_no_rounding", "research_assumption", "before_all_period_openings_utc"), "ESCALATION_SELECTED_POLICY")
    start, end = _period(data["period"])
    as_of, cutoff = _day(data["as_of"]), _instant(data["cutoff"])
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _fields(row, {"id", "scope", "observed_at", "kind"})
        _need(row["scope"] == scope, "ESCALATION_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "ESCALATION_EVIDENCE_CUTOFF")
    table = data["bracket_table"]
    _fields(table, {"id", "version", "scope", "effective", "approved_date", "recorded_date", "observed_at", "source_ref", "evidence_ref", "brackets"})
    _text(table["id"]); _text(table["version"]); _text(table["source_ref"])
    _need(table["scope"] == scope and table["evidence_ref"] in evidence, "ESCALATION_BRACKET_SCOPE_EVIDENCE")
    _need(_day(table["approved_date"]) <= _day(table["recorded_date"]) <= as_of, "ESCALATION_TABLE_ASOF")
    table_observed = _instant(table["observed_at"])
    _need(table_observed < cutoff, "ESCALATION_TABLE_CUTOFF")
    table_start, table_end = _period(table["effective"])
    raw_bands = _index(table["brackets"])
    _need(bool(raw_bands), "ESCALATION_BRACKETS_REQUIRED")
    sequences, bands = set(), []
    for row in raw_bands.values():
        _fields(row, {"id", "sequence", "lower", "upper", "rate", "source_ref", "evidence_ref"})
        sequence = row["sequence"]
        _need(type(sequence) is int and sequence >= 0 and sequence not in sequences, "ESCALATION_BRACKET_SEQUENCE")
        sequences.add(sequence)
        _text(row["source_ref"])
        _need(row["evidence_ref"] in evidence, "ESCALATION_BRACKET_SCOPE_EVIDENCE")
        rate = _q(row["rate"])
        _need(rate <= 1, "ESCALATION_RATE_DOMAIN")
        bands.append({"id": row["id"], "sequence": sequence, "lower": _q(row["lower"]),
                      "upper": None if row["upper"] == "unbounded" else _q(row["upper"]), "rate": rate})
    bands.sort(key=lambda row: row["sequence"])
    boundary, previous_rate = Fraction(), Fraction()
    for index, band in enumerate(bands):
        _need(band["lower"] == boundary and (band["upper"] is None or band["upper"] > band["lower"]), "ESCALATION_BRACKET_PARTITION")
        _need((band["upper"] is None) == (index == len(bands) - 1), "ESCALATION_FINAL_UNBOUNDED")
        _need(band["rate"] >= previous_rate, "ESCALATION_DECREASING_RATE")
        previous_rate, boundary = band["rate"], band["upper"]
    snapshot = _snapshot(table)
    _fields(opening, {"scope", "purpose", "policy_id", "policy_revision", "method", "bracket_table", "boundary", "origin", "source_case_id",
                      "cumulative_basis", "recognized_entitlement", "period_history"})
    _need(opening["scope"] == scope and opening["purpose"] == "cumulative_escalation", "ESCALATION_OPENING_SCOPE")
    _need((opening["policy_id"], opening["policy_revision"], opening["method"]) == (POLICY_ID, "1", method), "ESCALATION_OPENING_METHOD")
    _need(_snapshot(opening["bracket_table"]) == snapshot, "ESCALATION_BRACKET_AMENDMENT")
    _need(opening["boundary"] == data["period"]["start"], "ESCALATION_OPENING_BOUNDARY")
    opening_basis, opening_recognized = _q(opening["cumulative_basis"]), _q(opening["recognized_entitlement"])
    history = opening["period_history"]
    _need(type(history) is list, "ESCALATION_HISTORY_REQUIRED")
    if opening["origin"] == "genesis":
        _need(opening_basis == 0 and opening_recognized == 0 and not history and opening["source_case_id"] == "genesis"
              and "prior_result" not in data, "ESCALATION_GENESIS")
    elif opening["origin"] == "supplied_history":
        _need(bool(history) and "prior_result" not in data, "ESCALATION_SUPPLIED_HISTORY")
    else:
        _need(opening["origin"] == "prior_result" and "prior_result" in data, "ESCALATION_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if "result_ref" in prior:
            _text(prior["result_ref"])
        _, prior_end = _period(prior["period"])
        _need(prior_end == start, "ESCALATION_PREDECESSOR_BOUNDARY")
        _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id
              and prior["closing_state"] == opening, "ESCALATION_PREDECESSOR_MISMATCH")
    used_ids, used_sources, used_cases = set(), set(), {case_id}

    def available_terms(period_start, period_end):
        _need(table_start <= period_start < period_end <= table_end, "ESCALATION_TABLE_EFFECTIVE")
        _need(_day(table["recorded_date"]) <= period_start
              and table_observed < _instant(period_start.isoformat() + "T00:00:00Z"), "ESCALATION_TABLE_HISTORICAL_AVAILABILITY")

    def events_for(rows, period_start, period_end):
        indexed = _index(rows)
        sequences = set()
        for identity, row in indexed.items():
            _fields(row, {"id", "scope", "basis", "sequence", "effective_date", "observed_at", "source_ref", "evidence_ref"})
            _need(identity not in used_ids, "ESCALATION_EVENT_ALREADY_RECOGNIZED")
            used_ids.add(identity)
            source = _text(row["source_ref"])
            _need(source not in used_sources, "ESCALATION_SOURCE_ALREADY_RECOGNIZED")
            used_sources.add(source)
            _need(row["scope"] == scope, "ESCALATION_FACT_SCOPE")
            _need(row["evidence_ref"] in evidence, "ESCALATION_FACT_EVIDENCE")
            _need(_instant(row["observed_at"]) < cutoff, "ESCALATION_FACT_CUTOFF")
            _need(period_start <= _day(row["effective_date"]) < period_end, "ESCALATION_FACT_PERIOD")
            _q(row["basis"])
            sequence = row["sequence"]
            _need(type(sequence) is int and sequence >= 0 and sequence not in sequences, "ESCALATION_EVENT_SEQUENCE")
            sequences.add(sequence)
        return sorted(rows, key=lambda row: row["sequence"])

    replay_basis, replay_recognized, previous_end = Fraction(), Fraction(), None
    normalized_history = []
    for row in sorted(history, key=lambda record: record["period"]["start"]):
        _fields(row, {"source_case_id", "period", "opening_basis", "opening_recognized", "events", "current_result", "closing_basis", "closing_recognized"})
        history_case = _text(row["source_case_id"])
        _need(history_case not in used_cases, "ESCALATION_DUPLICATE_PERIOD_CASE")
        used_cases.add(history_case)
        history_start, history_end = _period(row["period"])
        _need(history_end <= start and (previous_end is None or previous_end == history_start), "ESCALATION_HISTORY_BOUNDARY")
        available_terms(history_start, history_end)
        _need(_q(row["opening_basis"]) == replay_basis and _q(row["opening_recognized"]) == replay_recognized, "ESCALATION_HISTORY_RECONCILIATION")
        original_events = events_for(row["events"], history_start, history_end)
        calculated = _compute(original_events, replay_basis, replay_recognized, bands, method)
        _need(_q(row["current_result"]) == calculated["current_result"] and _q(row["closing_basis"]) == calculated["closing_basis"]
              and _q(row["closing_recognized"]) == calculated["closing_recognized"], "ESCALATION_HISTORY_RECONCILIATION")
        replay_basis, replay_recognized, previous_end = calculated["closing_basis"], calculated["closing_recognized"], history_end
        normalized_history.append({**row, "events": original_events})
    _need(replay_basis == opening_basis and replay_recognized == opening_recognized
          and (not history or (previous_end == start and normalized_history[-1]["source_case_id"] == opening["source_case_id"])), "ESCALATION_OPENING_HISTORY_RECONCILIATION")
    available_terms(start, end)
    events = events_for(data["events"], start, end)
    result = _compute(events, opening_basis, opening_recognized, bands, method)
    current_history = {"source_case_id": case_id, "period": dict(data["period"]), "opening_basis": opening_basis,
                       "opening_recognized": opening_recognized, "events": [dict(row) for row in events],
                       "current_result": result["current_result"], "closing_basis": result["closing_basis"], "closing_recognized": result["closing_recognized"]}
    closing = {"scope": dict(scope), "purpose": "cumulative_escalation", "policy_id": POLICY_ID, "policy_revision": "1", "method": method,
               "bracket_table": snapshot, "boundary": data["period"]["end"], "origin": "prior_result", "source_case_id": case_id,
               "cumulative_basis": result["closing_basis"], "recognized_entitlement": result["closing_recognized"],
               "period_history": normalized_history + [current_history]}
    return {"source_case_id": case_id, "period": dict(data["period"]), "method": method,
            "opening_basis": opening_basis, "opening_recognized": opening_recognized, **result, "closing_state": closing,
            "status_meaning": "synthetic calculated entitlement/delta, not issued or actually paid"}


def escalation(data):
    """Return independent ordered financial controls or reject without state."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, StopIteration) as error:
        if isinstance(error, EscalationOracleError):
            raise
        raise EscalationOracleError("ESCALATION_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
