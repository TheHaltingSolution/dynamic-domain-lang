"""Independent controls for one supplied USD withholding/deferment policy.

Neutral original facts, original issuance identities and separately evidenced
actual cash are authoritative inputs. This module imports no SPL/compiler code.
Money is cent-integral; exact rates may produce half-cent withholding ties.
"""
from datetime import date
from fractions import Fraction
import re


POLICY_ID = "SYNTHETIC-SETTLEMENT-01"
POLICY_REVISION = "1"
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}


class SettlementOracleError(ValueError):
    def __init__(self, code, payment_evidence_status=None):
        super().__init__(code)
        self.code = code
        self.payment_evidence_status = payment_evidence_status


def _need(condition, code):
    if not condition:
        raise SettlementOracleError(code)


def _fields(record, required, optional=()):
    _need(type(record) is dict and required <= record.keys()
          and record.keys() <= required | set(optional), "SETTLEMENT_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "SETTLEMENT_IDENTITY_REQUIRED")
    return value


def _exact(value):
    _need(type(value) is str and re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value),
          "SETTLEMENT_EXACT_VALUE_REQUIRED")
    return Fraction(value)


def _money(value, positive=False):
    amount = _exact(value)
    _need(amount > 0 if positive else amount >= 0, "SETTLEMENT_AMOUNT_DOMAIN")
    _need((amount * 100).denominator == 1, "SETTLEMENT_MINOR_UNIT")
    return amount


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "SETTLEMENT_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise SettlementOracleError("SETTLEMENT_DATE") from None


def _instant(value):
    _need(type(value) is str, "SETTLEMENT_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "SETTLEMENT_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "SETTLEMENT_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "SETTLEMENT_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset)
    result += Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "SETTLEMENT_INSTANT")
    return result


def _scope(scope):
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "SETTLEMENT_CURRENCY")


def _identities(rows):
    _need(type(rows) is list, "SETTLEMENT_RECORD_LIST")
    identities = [_text(row["id"]) for row in rows]
    _need(len(identities) == len(set(identities)), "SETTLEMENT_DUPLICATE_ID")
    return set(identities)


def _half_even_cent(value):
    scaled = value * 100
    whole, remainder = divmod(scaled.numerator, scaled.denominator)
    twice = remainder * 2
    rounded = whole + (twice > scaled.denominator or (twice == scaled.denominator and whole % 2 == 1))
    return Fraction(rounded, 100)


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "period", "cutoff", "terms", "earned",
                   "issued", "payments", "applications", "evidence", "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "settlement-neutral/1", "SETTLEMENT_NEUTRAL_SCHEMA")
    case_id, scope, terms, opening = _text(data["case_id"]), data["scope"], data["terms"], data["opening_state"]
    _scope(scope)
    _fields(data["period"], {"start", "end"})
    start, end = _day(data["period"]["start"]), _day(data["period"]["end"])
    _need(start < end, "SETTLEMENT_PERIOD")
    cutoff = _instant(data["cutoff"])
    _fields(terms, {"policy_id", "policy_revision", "withholding_rate", "minimum_payout", "rounding", "threshold", "evidence_class"})
    _need((terms["policy_id"], terms["policy_revision"], terms["rounding"], terms["threshold"], terms["evidence_class"])
          == (POLICY_ID, POLICY_REVISION, "half_even_cent_once", "at_least", "research_assumption"), "SETTLEMENT_POLICY")
    rate, threshold = _exact(terms["withholding_rate"]), _money(terms["minimum_payout"])
    _need(0 <= rate <= 1, "SETTLEMENT_RATE_DOMAIN")

    _fields(opening, {"scope", "purpose", "policy_id", "policy_revision", "boundary", "origin", "source_case_id", "deferred_unissued", "issued_obligations", "recognized_ids"})
    _need(opening["scope"] == scope and opening["purpose"] == "net_unpaid", "SETTLEMENT_OPENING_SCOPE")
    _need((opening["policy_id"], opening["policy_revision"]) == (POLICY_ID, POLICY_REVISION), "SETTLEMENT_OPENING_POLICY")
    _need(opening["boundary"] == data["period"]["start"], "SETTLEMENT_OPENING_BOUNDARY")
    deferred = _money(opening["deferred_unissued"])
    _need(type(opening["recognized_ids"]) is list, "SETTLEMENT_RECOGNIZED_IDS")
    recognized = [_text(value) for value in opening["recognized_ids"]]
    _need(all(re.fullmatch(r"(?:earned|issued|payments|applications):.+", value) for value in recognized), "SETTLEMENT_RECOGNIZED_IDS")
    _need(len(set(recognized)) == len(recognized), "SETTLEMENT_DUPLICATE_ID")
    if opening["origin"] == "genesis":
        _need(deferred == 0 and opening["issued_obligations"] == [] and not recognized
              and opening["source_case_id"] == "genesis" and "prior_result" not in data, "SETTLEMENT_GENESIS")
    else:
        _need(opening["origin"] == "prior_result"
              and "prior_result" in data, "SETTLEMENT_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if "result_ref" in prior:
            _text(prior["result_ref"])
        _fields(prior["period"], {"start", "end"})
        _need(_day(prior["period"]["start"]) < _day(prior["period"]["end"])
              and prior["period"]["end"] == data["period"]["start"], "SETTLEMENT_PREDECESSOR_BOUNDARY")
        _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id
              and prior["closing_state"] == opening, "SETTLEMENT_PREDECESSOR_MISMATCH")

    evidence_ids = _identities(data["evidence"])
    evidence = {}
    completeness = []
    for row in data["evidence"]:
        _fields(row, {"id", "scope", "observed_at", "kind"}, {"period"})
        _need(row["scope"] == scope, "SETTLEMENT_EVIDENCE_SCOPE")
        _need(_instant(row["observed_at"]) < cutoff, "SETTLEMENT_EVIDENCE_CUTOFF")
        _text(row["kind"])
        if row["kind"] == "complete_settlement_population":
            _need(row.get("period") == data["period"], "SETTLEMENT_COMPLETENESS_SCOPE")
            completeness.append(row)
        evidence[row["id"]] = row
    if not completeness:
        raise SettlementOracleError("SETTLEMENT_PAYMENT_POPULATION_REQUIRED", "no_event_supplied")
    _need(len(completeness) == 1, "SETTLEMENT_COMPLETENESS_AMBIGUOUS")

    base_fields = {"id", "scope", "amount", "observed_at", "source_ref", "evidence_ref"}

    def observed(row):
        _need(row["scope"] == scope, "SETTLEMENT_FACT_SCOPE")
        _need(_instant(row["observed_at"]) < cutoff, "SETTLEMENT_FACT_CUTOFF")
        _text(row["source_ref"])
        _need(row["evidence_ref"] in evidence_ids, "SETTLEMENT_FACT_EVIDENCE")

    obligation_ids = _identities(opening["issued_obligations"])
    obligations = {}
    for row in opening["issued_obligations"]:
        _fields(row, base_fields | {"issued_date", "paid_to_date"})
        observed(row)
        _need(_day(row["issued_date"]) < start, "SETTLEMENT_ORIGINAL_ISSUE_DATE")
        amount, paid = _money(row["amount"], positive=True), _money(row["paid_to_date"])
        _need(paid < amount and "issued:" + row["id"] in recognized, "SETTLEMENT_ORIGINAL_OBLIGATION")
        obligations[row["id"]] = {**row, "amount": amount, "paid_to_date": paid}
    opening_issued = sum((row["amount"] - row["paid_to_date"] for row in obligations.values()), Fraction())

    all_new = []
    for kind, date_field in (("earned", "effective_date"), ("issued", "issued_date"), ("payments", "paid_date"), ("applications", None)):
        _identities(data[kind])
        for row in data[kind]:
            extra = {date_field} if date_field else {"payment_id", "issued_id"}
            _fields(row, base_fields | extra)
            observed(row)
            if date_field:
                effective = _day(row[date_field])
                _need(start <= effective < end, "SETTLEMENT_FACT_PERIOD")
                _need(effective.toordinal() * 86400 <= _instant(row["observed_at"]), "SETTLEMENT_OBSERVATION_BEFORE_EVENT")
            _money(row["amount"], positive=kind != "earned")
            all_new.append(kind + ":" + row["id"])
    _need(not (set(all_new) & set(recognized)), "SETTLEMENT_ALREADY_RECOGNIZED")

    earned = sum((_money(row["amount"]) for row in data["earned"]), Fraction())
    withheld = _half_even_cent(earned * rate)
    net = earned - withheld
    candidate = deferred + net
    reached = candidate >= threshold
    new_eligible = candidate if reached else Fraction()
    _need(len(data["issued"]) <= 1, "SETTLEMENT_ONE_NEW_ISSUE")
    issued = sum((_money(row["amount"], positive=True) for row in data["issued"]), Fraction())
    _need(not data["issued"] or issued == new_eligible, "SETTLEMENT_ISSUE_AMOUNT")
    _need(not (obligation_ids & {row["id"] for row in data["issued"]}), "SETTLEMENT_DUPLICATE_ID")
    for row in data["issued"]:
        obligations[row["id"]] = {**row, "amount": _money(row["amount"], positive=True), "paid_to_date": Fraction()}

    payments = {row["id"]: row for row in data["payments"]}
    applied_by_payment = {identity: Fraction() for identity in payments}
    applied_by_issue = {identity: Fraction() for identity in obligations}
    for row in data["applications"]:
        _need(row["payment_id"] in payments and row["issued_id"] in obligations, "SETTLEMENT_APPLICATION_REFERENCE")
        payment, obligation = payments[row["payment_id"]], obligations[row["issued_id"]]
        _need(_day(obligation["issued_date"]) <= _day(payment["paid_date"]), "SETTLEMENT_PAYMENT_BEFORE_ISSUE")
        _need(_instant(payment["observed_at"]) <= _instant(row["observed_at"])
              and _instant(obligation["observed_at"]) <= _instant(row["observed_at"]), "SETTLEMENT_APPLICATION_OBSERVATION")
        amount = _money(row["amount"], positive=True)
        applied_by_payment[row["payment_id"]] += amount
        applied_by_issue[row["issued_id"]] += amount
    for identity, payment in payments.items():
        _need(applied_by_payment[identity] == _money(payment["amount"], positive=True), "SETTLEMENT_PAYMENT_CONSERVATION")
    closing_obligations, lines = [], []
    for identity, obligation in sorted(obligations.items()):
        applied = applied_by_issue[identity]
        opening_paid = obligation["paid_to_date"]
        _need(opening_paid + applied <= obligation["amount"], "SETTLEMENT_OBLIGATION_OVERPAYMENT")
        remaining = obligation["amount"] - opening_paid - applied
        lines.append({"issued_id": identity, "original_amount": obligation["amount"],
                      "opening_paid_to_date": opening_paid, "current_actual_paid": applied,
                      "remaining": remaining, "source_ref": obligation["source_ref"], "evidence_ref": obligation["evidence_ref"]})
        if remaining:
            closing_obligations.append({**obligation, "paid_to_date": opening_paid + applied})
    actual_paid = sum((_money(row["amount"], positive=True) for row in data["payments"]), Fraction())
    closing_unissued = candidate - issued
    closing_issued = sum((line["remaining"] for line in lines), Fraction())
    closing_total = closing_unissued + closing_issued
    opening_total = deferred + opening_issued
    _need(closing_total == opening_total + net - actual_paid, "SETTLEMENT_RECONCILIATION")
    closing_state = {"scope": dict(scope), "purpose": "net_unpaid", "policy_id": POLICY_ID,
                     "policy_revision": POLICY_REVISION, "boundary": data["period"]["end"],
                     "origin": "prior_result", "source_case_id": case_id,
                     "deferred_unissued": closing_unissued, "issued_obligations": closing_obligations,
                     "recognized_ids": sorted(set(recognized) | set(all_new))}
    return {"source_case_id": case_id, "period": dict(data["period"]), "earned": earned, "withheld": withheld,
            "current_net": net, "opening_unissued": deferred, "opening_issued_outstanding": opening_issued,
            "opening_unpaid": opening_total, "issuance_candidate": candidate, "threshold_reached": reached,
            "new_eligible_due": new_eligible, "total_eligible_due": opening_issued + new_eligible,
            "new_issued": issued, "actual_paid": actual_paid,
            "payment_evidence_status": "complete_with_events" if payments else "complete_no_events",
            "issuance_evidence_status": "supplied_issue" if data["issued"] else "complete_no_events",
            "closing_unissued": closing_unissued, "closing_issued_outstanding": closing_issued,
            "closing_unpaid": closing_total, "obligations": lines, "closing_state": closing_state}


def settlement_adjustments(data):
    """Return Fraction controls or reject; rejection supplies no consumable state."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, SettlementOracleError):
            raise
        raise SettlementOracleError("SETTLEMENT_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    """Serialize neutral carry without compiler codecs; all money is cents."""
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
