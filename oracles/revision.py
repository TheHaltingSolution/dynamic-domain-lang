"""Independent neutral-fact CORR-01 oracle; no compiler, codec or SPL imports."""
from datetime import date
from fractions import Fraction
import re


class RevisionError(ValueError):
    pass


def _need(test, code):
    if not test:
        raise RevisionError(code)


def _q(value):
    _need(type(value) in {str, int} and (type(value) is int or re.fullmatch(r"-?\d+(?:\.\d+|/[1-9]\d*)?", value)), "REV_EXACT_INPUT")
    return Fraction(value)


def _instant(value):
    """Exact independent RFC3339 subset: retain arbitrary fractional seconds."""
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(\.\d+)?([Zz]|[+-]\d{2}:\d{2})", value)
    _need(match is not None, "REV_INSTANT")
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    civil = date(year, month, day)
    _need(hour < 24 and minute < 60 and second < 60, "REV_INSTANT")
    fraction, zone = match.groups()[6:]
    offset = 0
    if zone.lower() != "z":
        _need(zone != "-00:00", "REV_INSTANT")
        hours, minutes = int(zone[1:3]), int(zone[4:])
        _need(hours < 24 and minutes < 60, "REV_INSTANT")
        offset = (hours * 3600 + minutes * 60) * (1 if zone[0] == "+" else -1)
    return Fraction(civil.toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")


def restate(fixture):
    """Recompute original and replacement entitlement, then reconcile actual cash."""
    original, bank, application, auth, payment = (fixture[key] for key in ["original", "bank", "application", "authorization", "payment"])
    policy = fixture["policy"]
    for row in [original, auth, payment]:
        _need(all(row[key] == value for key, value in fixture["scope"].items()), "MODULE_SCOPE_MISMATCH")
    _need(all(policy[key] == value for key, value in {"route": "restatement_only", "rounding": "exact_no_rounding", "overpayment": "block"}.items()), "REV_UNSUPPORTED_POLICY")
    rate = _q(policy["rate"])
    _need(0 <= rate <= 1, "REV_RATE_DOMAIN")
    period = fixture["period"]
    start, end = date.fromisoformat(period["start"]), date.fromisoformat(period["end"])
    _need(start < end, "REV_AFFECTED_PERIOD")
    within = lambda value: start <= date.fromisoformat(value) < end
    cutoff = _instant(fixture["cutoff"])
    _need(original["opening_boundary"] == period["start"] and _q(original["opening_prepaid"]) == 0 and _q(fixture["opening_entitlement"]) == 0, "REV_ORIGINAL_OPENING_REQUIRED")
    _need(original["run_id"] == auth["original_run_id"] and original["opening_snapshot_id"] == auth["original_opening_id"], "REV_ORIGINAL_LINEAGE")
    _need(auth["authorized"] is True and auth["route"] == "restatement_only", "REV_AUTHORIZATION_REQUIRED")
    _need(_instant(auth["approved_at"]) <= _instant(auth["observed_at"]) < cutoff, "REV_AUTHORIZATION_CUTOFF")
    evidence = {}
    for row in fixture["evidence"]:
        _need(row["id"] not in evidence, "DUPLICATE_MAP_KEY")
        _need(_instant(row["observed_at"]) < cutoff, "REV_EVIDENCE_CUTOFF")
        evidence[row["id"]] = row
    for row in [original, bank, application, payment]:
        _need(_instant(row["observed_at"]) < cutoff, "REV_FACT_CUTOFF")
    for row in [original, bank, application, auth, payment]:
        _need(row["evidence_id"] in evidence, "REV_EVIDENCE_REQUIRED")
    _need(application["id"] == original["application_id"] and application["bank_id"] == bank["id"], "REV_APPLICATION_LINEAGE")
    _need(within(bank["effective_date"]) and within(application["effective_date"]), "REV_AFFECTED_PERIOD")
    cash, initial_application = _q(bank["amount"]), _q(application["amount"])
    _need(cash >= 0 and initial_application == cash, "REV_ORIGINAL_CASH_CONTROL")
    original_recomputed = initial_application * rate
    _need(_q(original["issued"]) == original_recomputed, "REV_ORIGINAL_RESULT_MISMATCH")
    corrections = {}
    for row in fixture["corrections"]:
        _need(row["id"] not in corrections, "DUPLICATE_MAP_KEY")
        corrections[row["id"]] = row
    _need(len(corrections) == 1, "REV_ONE_CORRECTION_REQUIRED")
    _need(auth["correction_id"] in corrections, "REV_AUTHORIZED_CORRECTION_REQUIRED")
    correction = corrections[auth["correction_id"]]
    _need(correction["id"] not in fixture["recognized"], "REV_CORRECTION_ALREADY_RECOGNIZED")
    _need(not fixture["recognized"], "REV_ORIGINAL_HISTORY_REQUIRED")
    _need(correction["original_run_id"] == original["run_id"] and correction["replaces_id"] == application["id"] and correction["replacement_id"] == auth["replacement_id"] and correction["replacement_id"] != application["id"], "REV_REPLACEMENT_LINEAGE")
    _need(correction["bank_id"] == bank["id"] and correction["invoice_id"] == application["invoice_id"], "REV_REPLACEMENT_CASH_LINEAGE")
    _need(_instant(correction["observed_at"]) < cutoff and correction["evidence_id"] in evidence, "REV_CORRECTION_CUTOFF")
    _need(within(correction["effective_date"]), "REV_AFFECTED_PERIOD")
    replacement, outside = _q(correction["amount"]), _q(correction["reallocated_amount"])
    _need(replacement >= 0 and outside >= 0 and replacement + outside == cash, "REV_CASH_CONSERVATION")
    _need(payment["obligation_id"] == original["obligation_id"] and payment["original_run_id"] == original["run_id"], "REV_PAYMENT_LINEAGE")
    actual = _q(payment["amount"])
    _need(_instant(payment["disbursed_at"]) <= _instant(payment["observed_at"]) and _instant(payment["disbursed_at"]) < cutoff and actual >= 0, "REV_PAYMENT_DATE_AMOUNT")
    revised = replacement * rate
    _need(actual <= revised, "REV_OVERPAYMENT_POLICY_UNSUPPORTED")
    return {"bank_cash": cash, "original_application": initial_application, "revised_application": replacement,
            "reallocated_cash": outside, "original_issued": _q(original["issued"]), "original_recomputed": original_recomputed,
            "revised_entitlement": revised, "correction_delta": revised - _q(original["issued"]),
            "actual_paid_asof": actual, "outstanding_asof": revised - actual,
            "recognized": [correction["id"]]}
