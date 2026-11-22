"""Independent exact controls for the declared synthetic M1a royalty methods.

Inputs are neutral source facts, observation/evidence dates and scoped opening
state. No SPL, compiler projection, IR or implementation helper is consulted.
Bands cover [0, infinity), with lower-inclusive thresholds: a whole-base amount
exactly at 100 uses the band beginning at 100. Marginal earnings are areas under
those bands. Facts are aggregated before applying a period method; physical
input order has no economic meaning. Cumulative marginal earnings are the
difference between closing and opening marginal areas.

The supplied facts are a selected-period input view. M1-01 requires every row
to be effective in that period; an out-of-period row is a failed precondition,
not a silently excluded ledger item. Raw multi-period selection is outside
this profile.

The only composition is period marginal tiers followed by a fresh period cap.
Historical whole-base escalation, recoupable guarantees and offset precedence
are outside this deliberately finite interpretation. All amounts are exact USD;
each fact must be nonnegative, rather than applying a universal loss floor.
"""
from datetime import date
from fractions import Fraction
import re


class OracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise OracleError(code)


def _q(value):
    _need(type(value) in {str, int}, "exact_number_required")
    _need(type(value) is int or re.fullmatch(r"-?\d+(?:\.\d+|/[1-9]\d*)?", value), "exact_number_required")
    return Fraction(value)


def _nonnegative(value):
    result = _q(value)
    _need(result >= 0, "negative_amount")
    return result


def _day(value):
    _need(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value), "invalid_date")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise OracleError("invalid_date") from None


def _period(value):
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "invalid_period")
    return start, end


def _instant(value):
    # datetime's microsecond limit would silently lose the strict cutoff edge.
    _need(isinstance(value, str), "invalid_instant")
    match = re.fullmatch(r"(\d{4}-\d{2}-\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(\.\d+)?([Zz]|[+-]\d{2}:\d{2})", value)
    _need(match is not None, "invalid_instant")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "invalid_instant")
    offset = 0
    if zone.lower() != "z":
        hours, minutes = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and hours < 24 and minutes < 60, "invalid_instant")
        offset = (hours * 3600 + minutes * 60) * (1 if zone[0] == "+" else -1)
    return Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")


def _identities(rows):
    seen = set()
    for row in rows:
        identity = row["id"]
        _need(isinstance(identity, str) and bool(identity), "identity_required")
        _need(identity not in seen, "duplicate_identity")
        seen.add(identity)


def _scope(scope):
    fields = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}
    _need(isinstance(scope, dict) and set(scope) == fields, "scope_required")
    _need(all(isinstance(value, str) and value for value in scope.values()), "scope_required")
    _need(scope["currency"] == "USD", "unsupported_currency")


def _bands(rows, required):
    _identities(rows)
    _need(bool(rows) or not required, "tiers_required")
    sequences = set()
    for row in rows:
        sequence = row["sequence"]
        _need(type(sequence) is int and sequence >= 0, "tier_sequence_required")
        _need(sequence not in sequences, "duplicate_tier_sequence")
        sequences.add(sequence)
    rows = sorted(rows, key=lambda row: row["sequence"])
    bands, boundary = [], Fraction()
    for index, row in enumerate(rows):
        lower, rate = _nonnegative(row["lower"]), _nonnegative(row["rate"])
        upper = None if row["upper"] is None else _nonnegative(row["upper"])
        _need(rate <= 1, "rate_domain")
        _need(lower == boundary, "noncontiguous_tiers")
        _need(upper is None or upper > lower, "invalid_tier_bounds")
        _need((upper is None) == (index == len(rows) - 1), "unbounded_final_tier_required")
        bands.append((lower, upper, rate))
        boundary = upper
    return bands


def _area(amount, bands):
    return sum((max(Fraction(), (amount if upper is None else min(amount, upper)) - lower) * rate
                for lower, upper, rate in bands), Fraction())


def _calculate(data):
    _need(data["schema_version"] == "m1-neutral/1", "unsupported_neutral_schema")
    scope, policy, opening = data["scope"], data["policy"], data["opening_state"]
    _scope(scope)
    _need(opening["scope"] == scope, "state_scope_mismatch")
    start, end = _period(data["period"])
    opening_start, opening_end = _period(opening["period"])
    cutoff = _instant(data["cutoff"])
    method = policy["method"]
    _need(method in {"period_marginal", "period_whole_base", "cumulative_marginal", "period_cap", "cumulative_cap", "period_floor", "tiers_then_cap"}, "unsupported_method")
    _need(opening["method"] == method, "state_method_mismatch")
    _need(policy["rounding"] == "exact_no_rounding" and policy["negative_basis"] == "reject" and policy["threshold_equality"] == "lower_inclusive", "selected_policy_required")
    _need(type(policy["reset_period_cap"]) is bool, "explicit_cap_reset_required")
    balance = _nonnegative(opening["balance"])
    cap, floor = _nonnegative(policy["cap"]), _nonnegative(policy["floor"])
    bands = _bands(policy["tiers"], method in {"period_marginal", "period_whole_base", "cumulative_marginal", "tiers_then_cap"})
    same_period = (opening_start, opening_end) == (start, end)
    if method == "period_cap":
        if policy["reset_period_cap"]:
            _need(opening_end <= start, "invalid_reset_boundary")
            consumed = Fraction()
        else:
            _need(same_period, "period_cap_reset_required")
            consumed = balance
        _need(consumed <= cap, "cap_consumption_exceeds_limit")
    else:
        _need(policy["reset_period_cap"] is False, "reset_outside_period_cap")
        _need(same_period or opening_end <= start, "state_period_mismatch")
        consumed = balance if method == "cumulative_cap" else Fraction()
        if method == "cumulative_cap":
            _need(consumed <= cap, "cap_consumption_exceeds_limit")
        elif method != "cumulative_marginal":
            _need(balance == 0, "carry_outside_selected_method")
    evidence = data["evidence"]
    _identities(evidence)
    evidence_ids = set()
    for row in evidence:
        _need(_instant(row["observed_at"]) < cutoff, "evidence_after_cutoff")
        evidence_ids.add(row["id"])
    facts = data["facts"]
    _identities(facts)
    basis, included = Fraction(), []
    for row in facts:
        _need(row.get("scope", scope) == scope, "fact_scope_mismatch")
        _need(row["evidence_id"] in evidence_ids, "missing_evidence")
        _need(_instant(row["observed_at"]) < cutoff, "fact_after_cutoff")
        amount, effective = _nonnegative(row["amount"]), _day(row["effective_date"])
        _need(start <= effective < end, "fact_outside_selected_period")
        basis += amount
        included.append(row["id"])
    if method in {"period_marginal", "tiers_then_cap"}:
        uncapped = _area(basis, bands)
    elif method == "cumulative_marginal":
        uncapped = _area(balance + basis, bands) - _area(balance, bands)
    elif method == "period_whole_base":
        rate = next(rate for lower, upper, rate in bands if lower <= basis and (upper is None or basis < upper))
        uncapped = basis * rate
    else:
        uncapped = basis
    entitlement = uncapped
    if method in {"period_cap", "cumulative_cap", "tiers_then_cap"}:
        entitlement = min(uncapped, cap - consumed)
    elif method == "period_floor":
        entitlement = max(uncapped, floor)
    closing = (balance + basis if method == "cumulative_marginal" else
               consumed + entitlement if method in {"period_cap", "cumulative_cap"} else Fraction())
    return {"basis": basis, "uncapped": uncapped, "entitlement": entitlement, "closing_balance": closing,
            "included_ids": sorted(included), "excluded_ids": [],
            "opening_consumed": consumed, "floor_topup": entitlement - uncapped if method == "period_floor" else Fraction(),
            "closing_state": {"scope": dict(scope), "method": method, "balance": closing, "period": dict(data["period"])}}


def ordinary_royalties(data):
    """Return exact controls; serialize closing_state with exact_json for carry."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, StopIteration) as exc:
        if isinstance(exc, OracleError):
            raise
        raise OracleError("malformed_neutral_fact") from exc


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
