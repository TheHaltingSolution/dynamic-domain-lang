"""Exact, hand-authored controls for the selected RR-03 synthetic methods.

These functions consume neutral financial/evidence records, never SPL bindings.
They establish arithmetic under supplied policies, not contractual approval.
All dates here are civil dates: no sub-day ordering or observation claim is made.
"""
from datetime import date
from fractions import Fraction
import re


class OracleError(ValueError):
    """A neutral fixture cannot support the requested calculation."""


def _require(condition, message):
    if not condition:
        raise OracleError(message)


def _q(value):
    _require(type(value) is int or isinstance(value, str), "exact_number_required")
    _require(not isinstance(value, str) or
             re.fullmatch(r"-?\d+(?:\.\d+|/[1-9]\d*)?", value) is not None,
             "exact_number_required")
    return Fraction(value)


def _positive(value, *, zero=True):
    result = _q(value)
    _require(result >= 0 if zero else result > 0, "negative_or_zero_amount")
    return result


def _day(value):
    _require(isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value),
             "iso_civil_date_required")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise OracleError("invalid_civil_date") from exc


def _unique(rows, field="id"):
    result = {}
    for row in rows:
        key = row[field]
        _require(isinstance(key, str) and bool(key), "nonempty_id_required")
        _require(key not in result, "duplicate_" + field)
        result[key] = row
    return result


def _context(fixture):
    scope = fixture["scope"]
    for key in ("contract_id", "pool_id", "currency"):
        _require(isinstance(scope[key], str) and bool(scope[key]), "invalid_scope")
    _require(scope["currency"] == "USD", "only_selected_USD_method")
    start, end = map(_day, (fixture["period"]["start"], fixture["period"]["end"]))
    cutoff = _day(fixture["observed_through"])
    _require(start < end, "invalid_period")
    evidence = _unique(fixture["evidence"])
    for row in evidence.values():
        _require(_day(row["observed_date"]) <= cutoff, "evidence_after_cutoff")
    return start, end, evidence


def _evidenced(row, evidence):
    _require(row["evidence_id"] in evidence, "missing_evidence")


def _in_scope(row, scope):
    return all(row[key] == scope[key] for key in ("contract_id", "pool_id", "currency"))


def exact_json(value):
    """Render oracle Fractions as reduced strings, recursively, without rounding."""
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    return value


def angel_guild(fixture):
    """Allocate the full declared Guild filmmaker pool by qualified platform minutes."""
    start, end, evidence = _context(fixture)
    _require(_day(fixture["observed_through"]) >= end, "full_period_usage_requires_period_close")
    policy = fixture["policy"]
    _require(policy["rounding"] == "exact_no_rounding", "unsupported_rounding")
    _require(policy["negative_net"] == "reject", "unsupported_negative_net_policy")
    _require(policy["zero_minutes"] == "reject", "unsupported_zero_minutes_policy")
    _require(policy["metric_unit"] == "qualified_minutes", "unsupported_metric")
    _require(fixture["usage_population"]["complete"] is True, "incomplete_platform_population")
    _evidenced(fixture["usage_population"], evidence)
    _require(fixture["usage_population"]["platform_id"] == fixture["platform_id"],
             "population_platform_mismatch")
    _require(_positive(fixture["opening_carry"]) == 0, "nonzero_carry_outside_selected_method")
    selected, excluded = [], []
    _unique(fixture["cash_records"])
    for row in fixture["cash_records"]:
        _evidenced(row, evidence)
        amount = _positive(row["amount"])
        _require(row["channel"] in ("guild", "ordinary_distribution"), "unknown_channel")
        reason = ("other_scope" if not _in_scope(row, fixture["scope"]) else
                  "outside_period" if not start <= _day(row["date"]) < end else
                  "ordinary_distribution" if row["channel"] != "guild" else None)
        (excluded if reason else selected).append(
            {"id": row["id"], "reason": reason} if reason else {**row, "amount": amount})
    gross = sum((row["amount"] for row in selected), Fraction())
    cost_total = Fraction()
    _unique(fixture["costs"])
    for row in fixture["costs"]:
        _evidenced(row, evidence)
        _require(_in_scope(row, fixture["scope"]) and row["channel"] == "guild",
                 "cost_scope_mismatch")
        _require(start <= _day(row["date"]) < end, "cost_outside_period")
        _require(row["eligible"] is True, "cost_eligibility_required")
        cost_total += _positive(row["amount"])
    marketing_rate = _positive(policy["marketing_rate"])
    filmmaker_share = _positive(policy["filmmaker_share"])
    _require(marketing_rate <= 1 and filmmaker_share <= 1, "ratio_out_of_range")
    marketing = gross * marketing_rate
    net = gross - marketing - cost_total
    _require(net >= 0, "negative_net")
    filmmaker_pool = net * filmmaker_share
    weights = {}
    _unique(fixture["usage"])
    for row in fixture["usage"]:
        _evidenced(row, evidence)
        _require(row["platform_id"] == fixture["platform_id"], "usage_platform_mismatch")
        _require(row["period"] == fixture["period"], "usage_period_mismatch")
        _require(row["qualified"] is True, "unqualified_usage_in_population")
        _require(isinstance(row["title_id"], str) and bool(row["title_id"]), "title_id_required")
        weights[row["title_id"]] = weights.get(row["title_id"], Fraction()) + _positive(row["minutes"])
    minutes = sum(weights.values(), Fraction())
    _require(minutes > 0, "zero_platform_minutes")
    allocations = {title: filmmaker_pool * weight / minutes for title, weight in sorted(weights.items())}
    _require(fixture["focal_title"] in allocations, "focal_title_absent")
    return {"gross_guild": gross, "marketing": marketing, "other_costs": cost_total,
            "net_guild": net, "angel_share": net - filmmaker_pool,
            "filmmaker_pool": filmmaker_pool, "qualified_minutes": minutes,
            "title_minutes": dict(sorted(weights.items())), "title_allocations": allocations,
            "focal_title_amount": allocations[fixture["focal_title"]],
            "other_titles_amount": filmmaker_pool - allocations[fixture["focal_title"]],
            "allocation_residual": filmmaker_pool - sum(allocations.values(), Fraction()),
            "excluded_cash": excluded}


def mqp_ordered_fees(fixture):
    """Ordered prospective fee calculation, before RPPA or producer allocation.

    Actual cash and fee-available payments are separate ledgers. Accrual never
    counts as cash. Disputed cash is available only after its linked agreement
    under agreement_date; actual_date is an explicit sensitivity alternative.
    """
    start, end, evidence = _context(fixture)
    policy = fixture["policy"]
    _require(policy["trigger"] in ("agreement_date", "actual_date"), "unknown_trigger")
    _require(policy["threshold_comparison"] in ("at_least", "greater_than"), "unknown_equality_policy")
    _require(policy["same_day_order"] == "explicit_unique_sequence", "ordering_policy_required")
    _require(policy["application"] == "whole_receipt_prospective", "unsupported_fee_application")
    _require(policy["rounding"] == "exact_no_rounding", "unsupported_rounding")
    threshold = _positive(policy["threshold"], zero=False)
    low, high = map(_positive, (policy["lower_rate"], policy["upper_rate"]))
    _require(low <= 1 and high <= 1, "ratio_out_of_range")
    actual = _positive(fixture["opening_actual_paid"])
    available = _positive(fixture["opening_fee_available_paid"])
    _require(available <= actual, "available_exceeds_actual_paid")
    _unique(fixture["events"])
    order_keys = set()
    selected, excluded = [], []
    for row in fixture["events"]:
        _evidenced(row, evidence)
        day = _day(row["date"])
        _require(type(row["sequence"]) is int and row["sequence"] >= 0, "invalid_sequence")
        _require(day <= _day(fixture["observed_through"]), "event_after_cutoff")
        if not _in_scope(row, fixture["scope"]) or row["project_id"] != fixture["project_id"]:
            excluded.append({"id": row["id"], "reason": "other_scope_or_project"})
            continue
        _require(start <= day < end, "event_outside_period")
        key = (day, row["sequence"])
        _require(key not in order_keys, "ambiguous_event_order")
        order_keys.add(key)
        selected.append(row)
    payments, receipts, history = {}, [], []
    for row in sorted(selected, key=lambda r: (_day(r["date"]), r["sequence"])):
        kind = row["kind"]
        if kind == "accrual":
            _positive(row["amount"])
        elif kind == "actual_payment":
            amount = _positive(row["amount"])
            _require(type(row["disputed"]) is bool, "dispute_status_required")
            credited = policy["trigger"] == "actual_date" or not row["disputed"]
            payments[row["id"]] = {"amount": amount, "disputed": row["disputed"],
                                    "agreed": False, "credited": credited}
            actual += amount
            available += amount if credited else 0
        elif kind in ("dispute", "agreement"):
            _require(row["payment_id"] in payments, "missing_prior_payment")
            payment = payments[row["payment_id"]]
            _require(payment["disputed"], "payment_not_declared_disputed")
            if kind == "agreement":
                _require(not payment["agreed"], "duplicate_agreement")
                _require(_positive(row["agreed_amount"]) == payment["amount"],
                         "amount_change_outside_selected_method")
                _require(row["agreed_actual_date"] == next(
                    r["date"] for r in selected if r["id"] == row["payment_id"]),
                    "agreement_actual_date_mismatch")
                payment["agreed"] = True
                if not payment["credited"]:
                    available += payment["amount"]
                    payment["credited"] = True
        elif kind == "receipt":
            amount = _positive(row["amount"])
            _require(row["receipt_class"] in ("eligible", "principal_US_TV_license"), "unknown_receipt_class")
            if row["receipt_class"] != "eligible":
                excluded.append({"id": row["id"], "reason": "principal_US_TV_license"})
            else:
                reached = available >= threshold if policy["threshold_comparison"] == "at_least" else available > threshold
                rate = high if reached else low
                receipts.append({"id": row["id"], "amount": amount,
                                 "fee_available_paid": available, "rate": rate,
                                 "fee": amount * rate, "adjusted_receipts": amount * (1 - rate)})
        else:
            raise OracleError("unknown_event_kind")
        history.append({"id": row["id"], "actual_paid": actual, "fee_available_paid": available})
    return {"receipts": receipts, "eligible_receipts": sum((r["amount"] for r in receipts), Fraction()),
            "fee": sum((r["fee"] for r in receipts), Fraction()),
            "adjusted_receipts_before_RPPA": sum((r["adjusted_receipts"] for r in receipts), Fraction()),
            "closing_actual_paid": actual, "closing_fee_available_paid": available,
            "history": history, "excluded_events": sorted(excluded, key=lambda r: r["id"])}


def mqp_correction(fixture):
    """Apply one authorized prior-fee correction against supplied future capacity."""
    start, end, evidence = _context(fixture)
    _require(fixture["policy"] == {"application": "prospective_receipts_limited", "rounding": "exact_no_rounding"},
             "unsupported_correction_policy")
    authorizations = _unique(fixture["authorizations"])
    for auth in authorizations.values():
        _evidenced(auth, evidence)
        _require(auth["authorized"] is True, "unauthorized_correction")
        _require(_in_scope(auth, fixture["scope"]), "correction_scope_mismatch")
        _require(auth["original_fee_id"], "original_fee_link_required")
    _require(len(authorizations) == 1, "one_correction_only_in_selected_method")
    auth = next(iter(authorizations.values()))
    _require(_day(auth["authorized_date"]) <= _day(fixture["observed_through"]), "authority_after_cutoff")
    _require(auth["id"] not in fixture["previously_recognized_ids"], "correction_already_recognized")
    opening = _positive(auth["amount"])
    remaining = opening
    _unique(fixture["capacities"])
    keys, movements = set(), []
    for row in sorted(fixture["capacities"], key=lambda r: (_day(r["date"]), r["sequence"])):
        _evidenced(row, evidence)
        _require(_in_scope(row, fixture["scope"]), "capacity_scope_mismatch")
        _require(start <= _day(row["date"]) < end, "capacity_outside_period")
        _require(_day(row["date"]) >= _day(auth["authorized_date"]), "capacity_before_authority")
        _require(_day(row["date"]) <= _day(fixture["observed_through"]), "capacity_after_cutoff")
        _require(type(row["sequence"]) is int and row["sequence"] >= 0, "invalid_sequence")
        key = (row["date"], row["sequence"])
        _require(key not in keys, "ambiguous_capacity_order")
        keys.add(key)
        capacity = _positive(row["amount"])
        applied = min(remaining, capacity)
        remaining -= applied
        movements.append({"id": row["id"], "available_capacity": capacity, "applied": applied,
                          "unused_capacity": capacity - applied, "closing_correction": remaining})
    return {"recognized_correction_id": auth["id"], "original_fee_id": auth["original_fee_id"],
            "authorized_amount": opening, "movements": movements,
            "applied": opening - remaining, "closing_correction": remaining}


def supplied_due_reserve(fixture):
    """Baseline comparison of supplied due date; intentionally no month derivation."""
    start, end, evidence = _context(fixture)
    _require(fixture["policy"] == "inclusive_supplied_due_date", "unsupported_due_policy")
    vintage = fixture["vintage"]
    _evidenced(vintage, evidence)
    _require(_in_scope(vintage, fixture["scope"]), "vintage_scope_mismatch")
    due, creation, close = map(_day, (vintage["supplied_due_date"], vintage["creation_date"], fixture["close_date"]))
    _require(creation <= due, "due_before_creation")
    _require(start <= close < end and close <= _day(fixture["observed_through"]), "close_outside_period_or_cutoff")
    available = _positive(vintage["available_balance"])
    released = available if close >= due else Fraction()
    return {"vintage_id": vintage["id"], "available": available,
            "released": released, "closing_balance": available - released}
