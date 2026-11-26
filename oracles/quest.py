"""Neutral-fact oracle for one synthetic Quest additional-return component.

This module has no compiler dependency. It was authored from the neutral fixture
specification before reading the new SPL method. Decimal logarithms/exponentials
nominate a cent cell; exact Fraction powers certify that cell and its half-even
parity. This is independent of the SPL fixed-slot rational binary search.
Monthly/combined liability, payment execution and Excel operational equivalence
are outside this proposed research-assumption policy.
"""
from copy import deepcopy
from datetime import date
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from math import gcd
import re


POLICY_ID = "DYN02-QUEST-TWOFLOW-NEAREST-EVEN"
CLAUSE_SOURCE = "sec-quest-agreement@sha256:9f1c535acfa79aaab13b860e18cd731936425e2d42ac519942d37451deeda151"
CLAUSE_LOCATOR = "Schedule II, page 19, late-payment paragraph"
CALENDAR_SOURCE = "gregorian-calendar-2026-v1"
CALENDAR_DATES = {"2026-01-01", "2026-06-30", "2026-07-02", "2027-01-01", "2027-01-02"}
DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")


class QuestOracleError(ValueError):
    def __init__(self, code, message=""):
        self.code = code
        super().__init__(code + (": " + message if message else ""))


def _need(condition, code, message=""):
    if not condition:
        raise QuestOracleError(code, message)


def _fields(value, names):
    _need(type(value) is dict and set(value) == set(names.split()), "INVALID_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value.strip()) and value == value.strip(), "SOURCE_OR_ID_REQUIRED")
    return value


def _id(value):
    _text(value)
    _need(value.isascii() and not any(char.isspace() for char in value), "INVALID_ID")
    return value


def _exact(value):
    if type(value) is str and DECIMAL.fullmatch(value):
        return Fraction(value)
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        n, d = value["numerator"], value["denominator"]
        if type(n) is str and type(d) is str and INTEGER.fullmatch(n) and re.fullmatch(r"[1-9][0-9]*", d):
            numerator, denominator = int(n), int(d)
            _need(n != "-0" and gcd(numerator, denominator) == 1, "INVALID_EXACT_NUMBER")
            return Fraction(numerator, denominator)
    raise QuestOracleError("INVALID_EXACT_NUMBER")


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "INVALID_DATE")
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise QuestOracleError("INVALID_DATE") from None
    _need(parsed.isoformat() == value, "INVALID_DATE")
    return parsed


def _instant(value):
    _need(type(value) is str, "INVALID_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None and match[6] != "-00:00", "INVALID_INSTANT")
    hours, minutes, seconds = map(int, match.group(2, 3, 4))
    _need(hours < 24 and minutes < 60 and seconds < 60, "INVALID_INSTANT")
    zone, offset = match[6], 0
    if zone != "Z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zh < 24 and zm < 60, "INVALID_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    fractional = Fraction("0" + match[5]) if match[5] else Fraction(0)
    return Fraction(_day(match[1]).toordinal() * 86400 + hours * 3600 + minutes * 60 + seconds - offset) + fractional


def _unique(rows, field, code):
    _need(type(rows) is list, "RECORD_LIST_REQUIRED")
    identities = [_id(row[field]) for row in rows]
    _need(len(identities) == len(set(identities)), code)


def _cent_cell(principal, target_power, index):
    quantum = Fraction(1, 100)
    lower_domain = index == 0
    lower = max(Fraction(0), (Fraction(index) - Fraction(1, 2)) * quantum)
    upper = (Fraction(index) + Fraction(1, 2)) * quantum
    lower_power = ((principal + lower) / principal) ** 365
    upper_power = ((principal + upper) / principal) ** 365
    even = index % 2 == 0
    lower_ok = target_power >= 1 if lower_domain else lower_power <= target_power if even else lower_power < target_power
    upper_ok = target_power <= upper_power if even else target_power < upper_power
    return {"chosen_index": Fraction(index), "index_even": even,
            "lower_bound": lower, "upper_bound": upper, "lower_power": lower_power,
            "upper_power": upper_power, "lower_domain_boundary": lower_domain,
            "lower_ok": lower_ok, "upper_ok": upper_ok, "target_power": target_power}


def _charge(principal, annual_target, days):
    """Nominate via high precision real approximation, accept only exact cells."""
    target_power = (1 + annual_target) ** days
    for precision in (80, 160, 320):
        with localcontext() as context:
            context.prec = precision
            p = Decimal(principal.numerator) / Decimal(principal.denominator)
            r = Decimal(annual_target.numerator) / Decimal(annual_target.denominator)
            growth = ((1 + r).ln() * Decimal(days) / Decimal(365)).exp()
            nominated = int((p * (growth - 1) * 100).to_integral_value(rounding=ROUND_HALF_EVEN))
        # Neighbour checks resolve exact ties and arbitrarily close rationals;
        # approximation never decides which side of a half-cent is accepted.
        for index in dict.fromkeys((max(0, nominated), max(0, nominated - 1), max(0, nominated + 1))):
            certificate = _cent_cell(principal, target_power, index)
            if certificate["lower_ok"] and certificate["upper_ok"]:
                charge = Fraction(index, 100)
                minimum_index = index if ((principal + charge) / principal) ** 365 >= target_power else index + 1
                minimum = Fraction(minimum_index, 100)
                minimum_ok = ((principal + minimum) / principal) ** 365 >= target_power
                predecessor_ok = minimum_index == 0 or ((principal + minimum - Fraction(1, 100)) / principal) ** 365 < target_power
                _need(minimum_ok and predecessor_ok, "NUMERICAL_CERTIFICATE_FAILED")
                certificate.update(minimum_charge=minimum, minimum_ok=minimum_ok, predecessor_ok=predecessor_ok)
                return charge, minimum, certificate
    raise QuestOracleError("NUMERICAL_CERTIFICATE_FAILED")


def _calculate(facts):
    _fields(facts, "schema_version case_id scope period cutoff clause terms selected obligations payments applications evidence calendar")
    _need(facts["schema_version"] == "quest-two-flow-neutral/1", "UNSUPPORTED_NEUTRAL_SCHEMA")
    _id(facts["case_id"])
    scope = facts["scope"]
    _fields(scope, "agreement_id participant_id pool_id asset_id currency")
    for value in scope.values():
        _id(value)
    _need(scope["currency"] == "USD", "UNSUPPORTED_CURRENCY")
    _fields(facts["period"], "start end")
    start, end = map(_day, (facts["period"]["start"], facts["period"]["end"]))
    _need(start < end, "INVALID_PERIOD")
    cutoff = _instant(facts["cutoff"])
    clause = facts["clause"]
    _fields(clause, "source_ref locator component")
    _need(clause == {"source_ref": CLAUSE_SOURCE, "locator": CLAUSE_LOCATOR, "component": "additional_target_return_only"}, "CLAUSE_IDENTITY")
    terms = facts["terms"]
    _fields(terms, "policy_id revision annual_target day_count quantum rounding")
    _need((terms["policy_id"], terms["revision"], terms["day_count"], terms["rounding"]) ==
          (POLICY_ID, "1", "ACT/365", "half_even"), "SELECTED_POLICY_REQUIRED")
    annual_target, quantum = _exact(terms["annual_target"]), _exact(terms["quantum"])
    _need(annual_target >= 0 and quantum == Fraction(1, 100), "TERM_DOMAIN")
    _fields(facts["selected"], "obligation_id payment_id application_id")
    for value in facts["selected"].values():
        _id(value)
    evidence_rows = facts["evidence"]
    _unique(evidence_rows, "id", "DUPLICATE_EVIDENCE")
    evidence = {}
    for row in evidence_rows:
        _fields(row, "id observed_at source_ref")
        _text(row["source_ref"])
        _need(_instant(row["observed_at"]) < cutoff, "EVIDENCE_AFTER_CUTOFF")
        evidence[row["id"]] = row

    def observation(row):
        _id(row["evidence_id"])
        _text(row["source_ref"])
        _need(_instant(row["observed_at"]) < cutoff, "OBSERVATION_AFTER_CUTOFF")
        support = evidence.get(row["evidence_id"])
        _need(support is not None, "EVIDENCE_REQUIRED")
        _need(row["source_ref"] == support["source_ref"], "SOURCE_IDENTITY")

    economic = {}
    row_fields = {"obligations": "id amount currency due_date scope observed_at evidence_id source_ref",
                  "payments": "id economic_event_id amount currency paid_date scope observed_at evidence_id source_ref",
                  "applications": "id obligation_id payment_id amount currency effective_date scope observed_at evidence_id source_ref"}
    for group, fields in row_fields.items():
        rows = facts[group]
        _unique(rows, "id", "DUPLICATE_ECONOMIC_RECORD")
        _need(len(rows) == 1, "UNSUPPORTED_CARDINALITY")
        row = rows[0]
        _fields(row, fields)
        observation(row)
        _need(row["scope"] == scope, "ECONOMIC_SCOPE")
        _need(row["currency"] == "USD", "UNSUPPORTED_CURRENCY")
        economic[group] = row
    obligation, payment, application = (economic[name] for name in ("obligations", "payments", "applications"))
    _unique(facts["payments"], "economic_event_id", "DUPLICATE_PAYMENT_EVENT")
    _need(facts["selected"] == {"obligation_id": obligation["id"], "payment_id": payment["id"], "application_id": application["id"]}, "SELECTED_RECORD_REQUIRED")
    _need(application["obligation_id"] == obligation["id"] and application["payment_id"] == payment["id"], "APPLICATION_LINK")
    principal, paid, applied = (_exact(row["amount"]) for row in (obligation, payment, application))
    _need(principal >= Fraction(1, 100), "PRINCIPAL_DOMAIN")
    _need(principal == paid == applied, "FULL_PRINCIPAL_PAYMENT_REQUIRED")
    due, paid_date = _day(obligation["due_date"]), _day(payment["paid_date"])
    _need(_day(application["effective_date"]) == paid_date, "APPLICATION_DATE")
    _need(start <= paid_date < end, "PAYMENT_OUTSIDE_PERIOD")
    # Date arithmetic is independently derived from original financial records.
    days = (paid_date - due).days
    _need(0 <= days <= 365, "ELAPSED_DAY_DOMAIN")
    limit = principal * annual_target / quantum
    ceiling = -(-limit.numerator // limit.denominator)
    _need(ceiling < 2 ** 24, "SEARCH_DOMAIN")
    calendar = facts["calendar"]
    _fields(calendar, "id version origin source_ref observations")
    _need((calendar["id"], calendar["version"], calendar["origin"], calendar["source_ref"]) ==
          ("gregorian-2026", "1", "2026-01-01", CALENDAR_SOURCE), "CALENDAR_IDENTITY")
    origin = _day(calendar["origin"])
    observations = calendar["observations"]
    _unique(observations, "id", "DUPLICATE_CALENDAR_ID")
    _unique(observations, "date", "DUPLICATE_CALENDAR_DATE")
    dates = {}
    for row in observations:
        _fields(row, "id date ordinal observed_at evidence_id source_ref")
        observation(row)
        _need(row["source_ref"] == calendar["source_ref"], "CALENDAR_SOURCE")
        actual_day, ordinal = _day(row["date"]), _exact(row["ordinal"])
        _need(ordinal.denominator == 1 and ordinal >= 0, "CALENDAR_ORDINAL_DOMAIN")
        _need(row["date"] in CALENDAR_DATES and ordinal == (actual_day - origin).days, "CALENDAR_TRUTH")
        dates[row["date"]] = ordinal
    _need(obligation["due_date"] in dates and payment["paid_date"] in dates, "CALENDAR_ENDPOINT_REQUIRED")
    _need(dates[payment["paid_date"]] - dates[obligation["due_date"]] == days, "CALENDAR_TRUTH")
    charge, minimum, certificate = _charge(principal, annual_target, days)
    return {"additional_charge": charge, "actual_principal_paid": principal,
            "elapsed_days": Fraction(days), "day_count": "ACT/365", "annual_target": annual_target,
            "policy_id": POLICY_ID, "policy_revision": "1", "policy_status": "proposed",
            "evidence_class": "research_assumption", **deepcopy(facts["selected"]),
            "scenario_status": "calculated_unissued", "additional_payment_status": "no_event_supplied",
            "monthly_status": "not_computed", "combined_status": "unresolved_not_computed",
            **certificate, "minimum_charge": minimum, "certificate": certificate,
            "observations": deepcopy({name: facts[name] for name in ("scope", "period", "cutoff", "clause", "calendar", "obligations", "payments", "applications", "evidence")})}


def quest_two_flow(facts):
    """Validate complete neutral records, then return exact unissued controls."""
    try:
        return _calculate(facts)
    except (KeyError, TypeError, ValueError, ArithmeticError) as error:
        if isinstance(error, QuestOracleError):
            raise
        raise QuestOracleError("MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    """JSON-safe exact controls; fractions are numerator/denominator objects."""
    if isinstance(value, Fraction):
        return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
    if isinstance(value, dict):
        return {key: exact_json(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(child) for child in value]
    return value
