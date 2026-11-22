"""Independent exact controls from neutral facts for the selected C03/C07 case.

No compiler, canonical projection, source parser or evaluation helper is used.
This is arithmetic under the explicit synthetic policy, not contract approval.
"""
from datetime import date, datetime
from fractions import Fraction
import re


class OracleError(ValueError):
    pass


def _require(condition, code):
    if not condition:
        raise OracleError(code)


def _q(value):
    _require(type(value) in {str, int}, "exact_number_required")
    _require(not isinstance(value, str) or re.fullmatch(r"-?\d+(?:\.\d+|/[1-9]\d*)?", value), "exact_number_required")
    return Fraction(value)


def _positive(value):
    value = _q(value)
    _require(value >= 0, "negative_amount")
    return value


def _unique(rows, key="id"):
    seen = set()
    for row in rows:
        value = row.get(key)
        _require(isinstance(value, str) and bool(value), "identity_required")
        _require(value not in seen, "duplicate_identity")
        seen.add(value)


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value


def _calculate(fixture):
    scope = fixture["scope"]
    fields = ["agreement_id", "pool_id", "asset_id", "participant_group", "purpose", "currency"]
    _require(all(isinstance(scope[field], str) and scope[field] for field in fields), "scope_required")
    _require(scope["purpose"] == "capital_recovery" and scope["currency"] == "USD", "scope_purpose_currency")
    start, end = (date.fromisoformat(fixture["period"][key]) for key in ["start", "end"])
    _require(start < end, "period_required")
    cutoff = datetime.fromisoformat(fixture["cutoff"].replace("Z", "+00:00"))
    _require(cutoff.utcoffset() is not None, "cutoff_zone_required")
    policy = fixture["policy"]
    _require(policy["fee_base"] == "gross_before_costs" and policy["rounding"] == "exact_no_rounding" and policy["ties"] == "reject", "selected_policy_required")
    method = policy["recovery_method"]
    _require(method in {"priority", "pro_rata"}, "method_required")
    fee_rate = _positive(policy["fee_rate"])
    _require(fee_rate <= 1, "fee_rate_domain")
    _unique(fixture["evidence"])
    evidence = set()
    for row in fixture["evidence"]:
        observed = datetime.fromisoformat(row["observed_at"].replace("Z", "+00:00"))
        _require(observed.utcoffset() is not None and observed < cutoff, "evidence_after_cutoff")
        evidence.add(row["id"])
    _require(evidence, "evidence_required")
    recipients = fixture["beneficiaries"]
    _unique(recipients, "participant_id")
    weights = {}
    for recipient in recipients:
        identity = recipient["participant_id"]
        _require(identity != scope["participant_group"], "group_not_beneficiary")
        weights[identity] = _positive(recipient["residual_weight"])
    weight_total = sum(weights.values(), Fraction())
    _require(weight_total > 0, "zero_denominator")
    totals = {}
    for collection in ["cash_records", "costs"]:
        rows = fixture[collection]
        _unique(rows)
        total = Fraction()
        for row in rows:
            _require(all(row[field] == scope[field] for field in fields), collection + "_scope")
            _require(start <= date.fromisoformat(row["effective_date"]) < end, collection + "_period")
            _require(row["evidence_id"] in evidence, "missing_evidence")
            if collection == "costs":
                _require(row["eligible"] is True, "cost_eligibility")
            total += _positive(row["amount"])
        totals[collection] = total
    gross = totals["cash_records"]
    fee = gross * fee_rate
    costs = totals["costs"]
    available = gross - fee - costs
    _require(available >= 0, "deductions_exceed_cash")
    claims = fixture["opening_claims"]
    _unique(claims)
    order_keys = set()
    opening_claims = Fraction()
    for claim in claims:
        _require(claim["kind"] == "capital", "claim_kind")
        _require(claim["participant_id"] in weights, "claim_beneficiary")
        _require(type(claim["priority"]) is int and claim["priority"] >= 0 and type(claim["sequence"]) is int and claim["sequence"] >= 0, "priority_required")
        order = (claim["priority"], claim["sequence"])
        _require(order not in order_keys, "unresolved_event_order")
        order_keys.add(order)
        balance, principal = map(_positive, [claim["balance"], claim["principal"]])
        _require(balance <= principal, "claim_overapplication")
        opening_claims += balance
    recovery_pool = min(available, opening_claims)
    funds = available
    movements, ledger = [], []
    for claim in sorted(claims, key=lambda row: (row["priority"], row["sequence"])):
        balance = _q(claim["balance"])
        recovered = (min(funds, balance) if method == "priority" else
                     recovery_pool * balance / opening_claims if opening_claims else Fraction())
        _require(0 <= recovered <= balance and recovered <= funds, "claim_overapplication")
        movements.append({"id": claim["id"], "participant_id": claim["participant_id"], "opening_balance": balance,
                          "available_before": funds, "recovered": recovered, "closing_balance": balance - recovered,
                          "available_after": funds - recovered})
        funds -= recovered
        ledger.append({**claim, "principal": _q(claim["principal"]), "balance": balance - recovered})
    residual_lines = []
    for identity, weight in sorted(weights.items()):
        recovered = sum((row["recovered"] for row in movements if row["participant_id"] == identity), Fraction())
        residual = funds * weight / weight_total
        residual_lines.append({"participant_id": identity, "recovered": recovered, "residual": residual, "payable": recovered + residual})
    total_recovered = sum((row["recovered"] for row in movements), Fraction())
    allocated = sum((row["residual"] for row in residual_lines), Fraction())
    _require(total_recovered == recovery_pool and allocated == funds, "reconciliation")
    _require(gross == fee + costs + total_recovered + allocated, "cash_reconciliation")
    return {"control": {"gross": gross, "fee": fee, "deductions": costs, "available_funds": available,
                        "opening_claims": opening_claims, "recovered": total_recovered,
                        "closing_claims": opening_claims - total_recovered, "residual": funds, "allocated_residual": allocated},
            "claim_movements": movements, "residual_lines": residual_lines, "claim_ledger": ledger}


def waterfall(fixture):
    """Compute independent controls from complete, explicitly scoped neutral facts."""
    try:
        return _calculate(fixture)
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, OracleError):
            raise
        raise OracleError("malformed_neutral_fact") from exc
