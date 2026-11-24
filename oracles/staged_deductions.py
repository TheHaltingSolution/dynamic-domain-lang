"""Independent original-fact controls for named synthetic staged deductions.

Only standard-library exact arithmetic is used. This is not an SPL evaluator,
accounting approval, signed-loss policy, payment instruction or tax calculation.
"""
from datetime import date
from fractions import Fraction
import re


POLICY_ID = "SYNTHETIC-STAGED-DEDUCTIONS-01"
VARIANTS = {
    "pre_basis_gross_fee": ("pre_basis", "gross_receipts"),
    "pre_basis_net_fee": ("pre_basis", "stage_net"),
    "pre_share_gross_fee": ("pre_share", "gross_receipts"),
    "pre_share_net_fee": ("pre_share", "stage_net"),
    "post_share_gross_fee": ("post_share", "gross_receipts"),
    "post_share_net_fee": ("post_share", "stage_net"),
}
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}
COST_FIELDS = {"id", "scope", "amount", "category", "sequence", "effective_date", "observed_at", "source_ref", "evidence_ref"}


class DeductionOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise DeductionOracleError(code)


def _fields(value, required, optional=()):
    _need(type(value) is dict and required <= value.keys() and value.keys() <= required | set(optional), "DEDUCTION_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "DEDUCTION_IDENTITY_REQUIRED")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "DEDUCTION_EXACT_VALUE_REQUIRED")
    return Fraction(value)


def _money(value):
    amount = _q(value)
    _need(amount >= 0, "DEDUCTION_NEGATIVE_MONEY")
    return amount


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "DEDUCTION_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise DeductionOracleError("DEDUCTION_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "DEDUCTION_PERIOD")
    return start, end


def _instant(value):
    _need(type(value) is str, "DEDUCTION_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "DEDUCTION_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "DEDUCTION_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "DEDUCTION_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "DEDUCTION_INSTANT")
    return result


def _identities(rows):
    _need(type(rows) is list, "DEDUCTION_RECORD_LIST")
    identities = [_text(row["id"]) for row in rows]
    _need(len(set(identities)) == len(identities), "DEDUCTION_DUPLICATE_ID")
    return set(identities)


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "period", "cutoff", "terms", "receipts", "costs", "evidence", "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "deduction-neutral/1", "DEDUCTION_NEUTRAL_SCHEMA")
    case_id, scope, terms, opening = _text(data["case_id"]), data["scope"], data["terms"], data["opening_state"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "DEDUCTION_CURRENCY")
    start, end = _period(data["period"])
    cutoff = _instant(data["cutoff"])
    _fields(terms, {"policy_id", "policy_revision", "variant", "share", "fee_rate", "cap", "eligible_categories", "rounding", "allocation", "evidence_class"})
    _need((terms["policy_id"], terms["policy_revision"], terms["rounding"], terms["allocation"], terms["evidence_class"])
          == (POLICY_ID, "1", "exact_no_rounding", "sequence_priority_no_residual", "research_assumption"), "DEDUCTION_POLICY")
    _need(terms["variant"] in VARIANTS, "DEDUCTION_VARIANT_REQUIRED")
    stage, fee_base_kind = VARIANTS[terms["variant"]]
    share, rate, cap = _q(terms["share"]), _q(terms["fee_rate"]), _money(terms["cap"])
    _need(0 <= share <= 1 and 0 <= rate <= 1, "DEDUCTION_RATE_DOMAIN")
    categories = terms["eligible_categories"]
    _need(type(categories) is list, "DEDUCTION_CATEGORY_LIST")
    for category in categories:
        _text(category)
    _need(len(set(categories)) == len(categories), "DEDUCTION_CATEGORY_LIST")

    state_fields = {"scope", "purpose", "policy_id", "policy_revision", "variant", "cap_limit", "cap_consumed", "cost_history", "boundary", "origin", "source_case_id"}
    _fields(opening, state_fields)
    _need(opening["scope"] == scope and opening["purpose"] == "distribution_deduction", "DEDUCTION_OPENING_SCOPE")
    _need((opening["policy_id"], opening["policy_revision"], opening["variant"])
          == (POLICY_ID, "1", terms["variant"]), "DEDUCTION_OPENING_METHOD")
    _need(opening["boundary"] == data["period"]["start"], "DEDUCTION_OPENING_BOUNDARY")
    used = _money(opening["cap_consumed"])
    _need(_money(opening["cap_limit"]) == cap and used <= cap, "DEDUCTION_CAP_STATE")
    if opening["origin"] == "genesis":
        _need(used == 0 and opening["cost_history"] == [] and opening["source_case_id"] == "genesis"
              and "prior_result" not in data, "DEDUCTION_GENESIS")
    else:
        _need(opening["origin"] == "prior_result" and "prior_result" in data, "DEDUCTION_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if "result_ref" in prior:
            _text(prior["result_ref"])
        _, prior_end = _period(prior["period"])
        _need(prior_end == start, "DEDUCTION_PREDECESSOR_BOUNDARY")
        _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id
              and prior["closing_state"] == opening, "DEDUCTION_PREDECESSOR_MISMATCH")

    evidence_ids = _identities(data["evidence"])
    for row in data["evidence"]:
        _fields(row, {"id", "scope", "observed_at", "kind"})
        _need(row["scope"] == scope, "DEDUCTION_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "DEDUCTION_EVIDENCE_CUTOFF")

    def observation(row):
        _need(row["scope"] == scope, "DEDUCTION_FACT_SCOPE")
        _need(row["evidence_ref"] in evidence_ids, "DEDUCTION_FACT_EVIDENCE")
        _text(row["source_ref"])
        observed, effective = _instant(row["observed_at"]), _day(row["effective_date"])
        _need(observed < cutoff, "DEDUCTION_FACT_CUTOFF")
        _need(effective.toordinal() * 86400 <= observed, "DEDUCTION_OBSERVATION_BEFORE_EVENT")
        return effective

    historical_ids = _identities(opening["cost_history"])
    history = []
    historical_total = Fraction()
    for row in opening["cost_history"]:
        _fields(row, COST_FIELDS | {"deducted", "disposition", "recognized_period"})
        effective = observation(row)
        historical_start, historical_end = _period(row["recognized_period"])
        _need(historical_start <= effective < historical_end <= start, "DEDUCTION_HISTORICAL_PERIOD")
        _need(type(row["sequence"]) is int and row["sequence"] >= 0, "DEDUCTION_COST_SEQUENCE")
        _text(row["category"])
        amount, deducted = _money(row["amount"]), _money(row["deducted"])
        disposition = row["disposition"]
        _need((disposition == "excluded_category" and deducted == 0)
              or (disposition == "eligible_full" and deducted == amount)
              or (disposition == "eligible_capped" and deducted < amount), "DEDUCTION_HISTORICAL_CONSUMPTION")
        historical_total += deducted
        history.append({**row, "amount": amount, "deducted": deducted})
    _need(historical_total == used, "DEDUCTION_CAP_HISTORY_RECONCILIATION")

    receipt_ids, cost_ids = _identities(data["receipts"]), _identities(data["costs"])
    _need(not (historical_ids & cost_ids), "DEDUCTION_COST_ALREADY_RECOGNIZED")
    gross, net = Fraction(), Fraction()
    for row in data["receipts"]:
        _fields(row, {"id", "scope", "gross_amount", "net_amount", "effective_date", "observed_at", "source_ref", "evidence_ref"})
        effective = observation(row)
        _need(start <= effective < end, "DEDUCTION_FACT_PERIOD")
        row_gross, row_net = _money(row["gross_amount"]), _money(row["net_amount"])
        _need(row_net <= row_gross, "DEDUCTION_RECEIPT_VIEWS")
        gross += row_gross
        net += row_net
    sequences = set()
    for row in data["costs"]:
        _fields(row, COST_FIELDS)
        effective = observation(row)
        _need(start <= effective < end, "DEDUCTION_FACT_PERIOD")
        _money(row["amount"])
        _text(row["category"])
        sequence = row["sequence"]
        _need(type(sequence) is int and sequence >= 0, "DEDUCTION_COST_SEQUENCE")
        _need(sequence not in sequences, "DEDUCTION_SEQUENCE_TIE")
        sequences.add(sequence)

    eligible, excluded, admitted = Fraction(), Fraction(), Fraction()
    cost_lines = []
    for row in sorted(data["costs"], key=lambda value: value["sequence"]):
        amount = _money(row["amount"])
        if row["category"] in categories:
            eligible += amount
            deducted = min(amount, cap - used - admitted)
            disposition = "eligible_full" if deducted == amount else "eligible_capped"
        else:
            excluded += amount
            deducted, disposition = Fraction(), "excluded_category"
        admitted += deducted
        entry = {**row, "amount": amount, "deducted": deducted, "disposition": disposition,
                 "recognized_period": dict(data["period"])}
        cost_lines.append(entry)
        history.append(entry)

    stage_net = net - admitted if stage == "pre_basis" else net
    _need(stage_net >= 0, "DEDUCTION_NEGATIVE_STAGE")
    fee_base = gross if fee_base_kind == "gross_receipts" else stage_net
    fee = fee_base * rate
    after_fee = stage_net - fee
    _need(after_fee >= 0, "DEDUCTION_NEGATIVE_STAGE")
    participation_basis = after_fee - admitted if stage == "pre_share" else after_fee
    _need(participation_basis >= 0, "DEDUCTION_NEGATIVE_STAGE")
    before_post_share = participation_basis * share
    earned = before_post_share - admitted if stage == "post_share" else before_post_share
    _need(earned >= 0, "DEDUCTION_NEGATIVE_EARNINGS")
    closing_used = used + admitted
    history.sort(key=lambda row: (row["recognized_period"]["start"], row["sequence"], row["id"]))
    closing = {"scope": dict(scope), "purpose": "distribution_deduction", "policy_id": POLICY_ID,
               "policy_revision": "1", "variant": terms["variant"], "cap_limit": cap,
               "cap_consumed": closing_used, "cost_history": history,
               "boundary": data["period"]["end"], "origin": "prior_result", "source_case_id": case_id}
    return {"source_case_id": case_id, "period": dict(data["period"]), "variant": terms["variant"],
            "cost_stage": stage, "fee_base_kind": fee_base_kind, "gross_receipts": gross, "net_receipts": net,
            "eligible_costs": eligible, "excluded_costs": excluded, "admitted_deduction": admitted,
            "eligible_unadmitted": eligible - admitted, "opening_cap_consumed": used,
            "cap_available": cap - used, "stage_net": stage_net, "fee_base": fee_base, "fee": fee,
            "after_fee": after_fee, "participation_basis": participation_basis, "before_post_share": before_post_share,
            "earned": earned, "closing_cap_consumed": closing_used, "closing_cap_available": cap - closing_used,
            "receipt_ids": sorted(receipt_ids), "cost_lines": cost_lines, "closing_state": closing}


def staged_deductions(data):
    """Return original-fact exact controls; invalid input yields no closing state."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, DeductionOracleError):
            raise
        raise DeductionOracleError("DEDUCTION_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
