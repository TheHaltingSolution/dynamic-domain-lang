"""Independent finite calendar/term controls, with mechanical validation separate.

Original daily rows and declared flags are inputs. Counts, term choices,
proration and business-day relations are derived here, not supplied answers.
"""
from datetime import date
from fractions import Fraction
import re


MAX_COVERAGE_DAYS = 400
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}


class CalendarTermsOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise CalendarTermsOracleError(code)


def _fields(value, required):
    _need(type(value) is dict and set(value) == required, "CALENDAR_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "CALENDAR_IDENTITY_REQUIRED")
    return value


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "CALENDAR_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise CalendarTermsOracleError("CALENDAR_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "CALENDAR_PERIOD")
    return start, end


def _instant(value):
    _need(type(value) is str, "CALENDAR_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "CALENDAR_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "CALENDAR_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "CALENDAR_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "CALENDAR_INSTANT")
    return result


def _money(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "CALENDAR_EXACT_NONNEGATIVE_MONEY")
    return Fraction(value)


def _index(rows):
    _need(type(rows) is list, "CALENDAR_RECORD_LIST")
    index = {}
    for row in rows:
        identity = _text(row["id"])
        _need(identity not in index, "CALENDAR_DUPLICATE_ID")
        index[identity] = row
    return index


def _validate_calendar(data):
    """Check original population and Gregorian metadata; do not price anything."""
    _fields(data, {"schema_version", "case_id", "scope", "calendar", "fiscal_periods", "selected_period_id",
                   "days", "terms", "as_of", "deadline", "policy", "cutoff", "evidence"})
    _need(data["schema_version"] == "calendar-terms-neutral/1", "CALENDAR_NEUTRAL_SCHEMA")
    _text(data["case_id"])
    scope = data["scope"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "CALENDAR_CURRENCY")
    cutoff = _instant(data["cutoff"])
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _fields(row, {"id", "scope", "observed_at", "kind"})
        _need(row["scope"] == scope, "CALENDAR_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "CALENDAR_EVIDENCE_CUTOFF")
    calendar = data["calendar"]
    _fields(calendar, {"id", "version", "coverage", "closed_weekdays", "ordinal_epoch", "evidence_ref", "source_ref"})
    _text(calendar["id"]); _text(calendar["version"]); _text(calendar["source_ref"])
    _need(calendar["evidence_ref"] in evidence, "CALENDAR_EVIDENCE_REQUIRED")
    _need(calendar["ordinal_epoch"] == "gregorian_0001_01_01_is_1", "CALENDAR_ORDINAL_EPOCH")
    coverage_start, coverage_end = _period(calendar["coverage"])
    _need((coverage_end - coverage_start).days <= MAX_COVERAGE_DAYS, "CALENDAR_COVERAGE_LIMIT")
    weekdays = calendar["closed_weekdays"]
    _need(type(weekdays) is list and all(type(value) is int and 1 <= value <= 7 for value in weekdays)
          and len(set(weekdays)) == len(weekdays), "CALENDAR_WEEKDAY_POLICY")
    day_ids = _index(data["days"])
    days = {}

    def common(row):
        _need(row["scope"] == scope, "CALENDAR_FACT_SCOPE")
        _need(row["calendar_id"] == calendar["id"] and row["calendar_version"] == calendar["version"], "CALENDAR_ID_VERSION")
        _need(row["evidence_ref"] in evidence, "CALENDAR_EVIDENCE_REQUIRED")
        _text(row["source_ref"])

    for row in day_ids.values():
        _fields(row, {"id", "date", "ordinal", "weekday", "proration_eligible", "holiday_closed", "closed",
                      "calendar_id", "calendar_version", "scope", "evidence_ref", "source_ref"})
        common(row)
        civil = _day(row["date"])
        _need(civil not in days, "CALENDAR_DUPLICATE_DATE")
        _need(type(row["ordinal"]) is int and row["ordinal"] == civil.toordinal(), "CALENDAR_ORDINAL")
        _need(type(row["weekday"]) is int and row["weekday"] == civil.isoweekday(), "CALENDAR_WEEKDAY")
        _need(all(type(row[field]) is bool for field in ("proration_eligible", "holiday_closed", "closed")), "CALENDAR_BOOLEAN_FLAGS")
        _need(row["closed"] == (row["weekday"] in weekdays or row["holiday_closed"]), "CALENDAR_CLOSED_FLAGS")
        days[civil] = row
    expected = set(range(coverage_start.toordinal(), coverage_end.toordinal()))
    _need({value.toordinal() for value in days} == expected, "CALENDAR_INCOMPLETE_POPULATION")
    periods = _index(data["fiscal_periods"])
    _need(data["selected_period_id"] in periods, "CALENDAR_SELECTED_FISCAL_PERIOD")
    owners = {civil: [] for civil in days}
    for row in periods.values():
        _fields(row, {"id", "calendar_id", "calendar_version", "scope", "period", "evidence_ref", "source_ref"})
        common(row)
        period_start, period_end = _period(row["period"])
        _need(coverage_start <= period_start < period_end <= coverage_end, "CALENDAR_FISCAL_BOUNDS")
        for civil in days:
            if period_start <= civil < period_end:
                owners[civil].append(row["id"])
    _need(all(len(ids) <= 1 for ids in owners.values()), "CALENDAR_FISCAL_OVERLAP")
    _need(all(len(ids) == 1 for ids in owners.values()), "CALENDAR_FISCAL_GAP")
    return {"calendar_id": calendar["id"], "calendar_version": calendar["version"],
            "days": days, "fiscal_periods": periods, "evidence": evidence}


def validate_calendar(data):
    """Return mechanically validated indexes of supplied rows, no financial counts."""
    try:
        return _validate_calendar(data)
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CalendarTermsOracleError):
            raise
        raise CalendarTermsOracleError("CALENDAR_MALFORMED_NEUTRAL_INPUT") from error


def _calculate(data):
    supplied = _validate_calendar(data)
    policy = data["policy"]
    _fields(policy, {"id", "revision", "proration", "term_selection", "no_term", "rounding", "evidence_class"})
    _need(policy == {"id": "SYNTHETIC-CALENDAR-TERMS-01", "revision": "1", "proration": "eligible_days_selected_fiscal_period",
                     "term_selection": "greatest_revision_unique", "no_term": "inactive_zero", "rounding": "exact_no_rounding",
                     "evidence_class": "research_assumption"}, "CALENDAR_SELECTED_POLICY")
    as_of, cutoff = _day(data["as_of"]), _instant(data["cutoff"])
    terms = _index(data["terms"])
    for row in terms.values():
        _fields(row, {"id", "revision", "predecessor_id", "effective", "monthly_amount", "scope", "signed_date",
                      "recorded_date", "observed_at", "evidence_ref", "source_ref"})
        _need(row["scope"] == data["scope"], "CALENDAR_TERM_SCOPE")
        _need(row["evidence_ref"] in supplied["evidence"], "CALENDAR_EVIDENCE_REQUIRED")
        _text(row["source_ref"])
        _need(type(row["revision"]) is int and row["revision"] >= 1, "CALENDAR_TERM_REVISION")
        _period(row["effective"])
        _money(row["monthly_amount"])
        _need(_day(row["signed_date"]) <= _day(row["recorded_date"]), "CALENDAR_SIGNED_RECORDED_ORDER")
        _need(_instant(row["observed_at"]) < cutoff, "CALENDAR_TERM_CUTOFF")
        predecessor = row["predecessor_id"]
        _need(type(predecessor) is str, "CALENDAR_PREDECESSOR")
        if predecessor:
            _need(predecessor in terms and terms[predecessor]["revision"] < row["revision"]
                  and terms[predecessor]["scope"] == row["scope"]
                  and _day(terms[predecessor]["recorded_date"]) <= _day(row["recorded_date"]), "CALENDAR_PREDECESSOR")
        else:
            _need(row["revision"] == 1, "CALENDAR_PREDECESSOR")
    period = supplied["fiscal_periods"][data["selected_period_id"]]["period"]
    start, end = _period(period)
    selected_days = [(civil, row) for civil, row in sorted(supplied["days"].items()) if start <= civil < end]
    denominator = sum(row["proration_eligible"] for _, row in selected_days)
    _need(denominator > 0, "CALENDAR_ZERO_ELIGIBLE_DAYS")
    day_lines, term_totals, numerator, amount = [], {}, 0, Fraction()
    for civil, row in selected_days:
        candidates = [term for term in terms.values() if _day(term["signed_date"]) <= as_of and _day(term["recorded_date"]) <= as_of
                      and _day(term["effective"]["start"]) <= civil < _day(term["effective"]["end"])]
        if candidates:
            revision = max(term["revision"] for term in candidates)
            winners = [term for term in candidates if term["revision"] == revision]
            _need(len(winners) == 1, "CALENDAR_AMBIGUOUS_AMENDMENT")
            term = winners[0]
            contribution = _money(term["monthly_amount"]) / denominator if row["proration_eligible"] else Fraction()
            numerator += int(row["proration_eligible"])
            if term["id"] not in term_totals:
                term_totals[term["id"]] = {"term_id": term["id"], "revision": revision, "monthly_amount": _money(term["monthly_amount"]),
                                            "eligible_days": 0, "amount": Fraction(), "predecessor_id": term["predecessor_id"],
                                            "source_ref": term["source_ref"], "evidence_ref": term["evidence_ref"]}
            term_totals[term["id"]]["eligible_days"] += int(row["proration_eligible"])
            term_totals[term["id"]]["amount"] += contribution
            term_id, selection = term["id"], "selected"
        else:
            contribution, term_id, selection = Fraction(), "", "inactive_zero"
        amount += contribution
        day_lines.append({"day_id": row["id"], "date": row["date"], "proration_eligible": row["proration_eligible"],
                          "closed": row["closed"], "term_id": term_id, "selection": selection, "amount": contribution,
                          "calendar_source_ref": row["source_ref"]})
    deadline = data["deadline"]
    _fields(deadline, {"date", "roll", "source_ref"})
    _text(deadline["source_ref"])
    due = _day(deadline["date"])
    _need(due in supplied["days"], "CALENDAR_DEADLINE_OUTSIDE_COVERAGE")
    _need(deadline["roll"] in ("following", "preceding"), "CALENDAR_ROLL_POLICY")
    candidates = [civil for civil, row in supplied["days"].items() if not row["closed"] and
                  (civil >= due if deadline["roll"] == "following" else civil <= due)]
    _need(bool(candidates), "CALENDAR_BUSINESS_RELATION_UNAVAILABLE")
    rolled = min(candidates) if deadline["roll"] == "following" else max(candidates)
    return {"calendar_id": supplied["calendar_id"], "calendar_version": supplied["calendar_version"],
            "fiscal_period_id": data["selected_period_id"], "period": dict(period), "as_of": data["as_of"],
            "eligible_day_count": denominator, "active_eligible_day_count": numerator, "amount": amount,
            "day_lines": day_lines, "term_lines": [term_totals[key] for key in sorted(term_totals)],
            "deadline": deadline["date"], "roll": deadline["roll"], "rolled_deadline": rolled.isoformat(),
            "deadline_day_id": supplied["days"][due]["id"], "rolled_day_id": supplied["days"][rolled]["id"],
            "limits": ["Signed/recorded Date as-of selection is separate from exact observation-cutoff availability.",
                       "No full bitemporal observed-knowledge reconstruction or payment execution.",
                       "Supplied holiday flags and closed weekdays are synthetic policy, not an external legal calendar."]}


def calendar_terms(data):
    """Derive daily financial controls and finite business relations independently."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, CalendarTermsOracleError):
            raise
        raise CalendarTermsOracleError("CALENDAR_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
