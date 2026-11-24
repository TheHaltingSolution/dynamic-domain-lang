"""Independent civil Date selection from finite supplied named-zone day cells."""
from datetime import date
from fractions import Fraction
import re


MAX_ZONES = 4
MAX_DAYS_PER_ZONE = 32
MAX_EVENTS = 128
SCOPE_FIELDS = {"contract_id", "asset_id"}


class CivilDateOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise CivilDateOracleError(code)


def _fields(value, required):
    _need(type(value) is dict and set(value) == required, "CIVIL_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "CIVIL_IDENTITY_REQUIRED")
    return value


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "CIVIL_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise CivilDateOracleError("CIVIL_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "CIVIL_LOCAL_COVERAGE")
    return start, end


def _instant(value):
    _need(type(value) is str, "CIVIL_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "CIVIL_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "CIVIL_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "CIVIL_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "CIVIL_INSTANT")
    return result


def _index(rows):
    _need(type(rows) is list, "CIVIL_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row["id"])
        _need(identity not in result, "CIVIL_DUPLICATE_ID")
        result[identity] = row
    return result


def _validate(data):
    """Mechanically check the original relation without selecting event answers."""
    _fields(data, {"schema_version", "case_id", "scope", "cutoff", "policy", "zones", "days", "events", "evidence"})
    _need(data["schema_version"] == "civil-date-neutral/1", "CIVIL_NEUTRAL_SCHEMA")
    _text(data["case_id"])
    scope = data["scope"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    cutoff = _instant(data["cutoff"])
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _fields(row, {"id", "scope", "observed_at", "kind"})
        _need(row["scope"] == scope, "CIVIL_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "CIVIL_EVIDENCE_CUTOFF")
    _need(type(data["zones"]) is list and 1 <= len(data["zones"]) <= MAX_ZONES, "CIVIL_RESOURCE_BOUND")
    zones = {}
    for row in data["zones"]:
        _fields(row, {"id", "version", "scope", "local_coverage", "source_ref", "evidence_ref"})
        key = (_text(row["id"]), _text(row["version"]))
        _need(key not in zones, "CIVIL_DUPLICATE_ZONE_VERSION")
        _need(row["scope"] == scope, "CIVIL_ZONE_SCOPE")
        _text(row["source_ref"])
        _need(row["evidence_ref"] in evidence, "CIVIL_EVIDENCE_REQUIRED")
        start, end = _period(row["local_coverage"])
        _need((end - start).days <= MAX_DAYS_PER_ZONE, "CIVIL_RESOURCE_BOUND")
        zones[key] = row
    indexed_days = _index(data["days"])
    by_zone = {key: {} for key in zones}
    for row in indexed_days.values():
        _fields(row, {"id", "zone_id", "zone_version", "scope", "local_date", "utc_start", "utc_end",
                      "start_offset_minutes", "end_offset_minutes", "source_ref", "evidence_ref"})
        key = (row["zone_id"], row["zone_version"])
        _need(key in zones, "CIVIL_ZONE_VERSION")
        _need(row["scope"] == scope, "CIVIL_DAY_SCOPE")
        _need(row["evidence_ref"] in evidence, "CIVIL_EVIDENCE_REQUIRED")
        _text(row["source_ref"])
        local = _day(row["local_date"])
        _need(local not in by_zone[key], "CIVIL_DUPLICATE_LOCAL_DATE")
        start_offset, end_offset = row["start_offset_minutes"], row["end_offset_minutes"]
        _need(all(type(value) is int and -1439 <= value <= 1439 for value in (start_offset, end_offset)), "CIVIL_OFFSET_MINUTES")
        utc_start, utc_end = _instant(row["utc_start"]), _instant(row["utc_end"])
        _need(utc_start < utc_end, "CIVIL_INTERVAL_POSITIVE")
        _need(utc_start == local.toordinal() * 86400 - start_offset * 60
              and utc_end == (local.toordinal() + 1) * 86400 - end_offset * 60, "CIVIL_MIDNIGHT_OFFSET_RELATION")
        by_zone[key][local] = row
    for key, zone in zones.items():
        start, end = _period(zone["local_coverage"])
        rows = by_zone[key]
        _need({day.toordinal() for day in rows} == set(range(start.toordinal(), end.toordinal())), "CIVIL_INCOMPLETE_LOCAL_POPULATION")
        previous = None
        for local in sorted(rows):
            current = rows[local]
            if previous:
                _need(previous["end_offset_minutes"] == current["start_offset_minutes"], "CIVIL_OFFSET_CONTINUITY")
                _need(_instant(previous["utc_end"]) == _instant(current["utc_start"]), "CIVIL_UTC_GAP_OR_OVERLAP")
            previous = current
    return {"zones": zones, "days": by_zone, "evidence": evidence}


def validate_zone_relation(data):
    """Return original record indexes only; intentionally ignore event selection."""
    try:
        return _validate(data)
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CivilDateOracleError):
            raise
        raise CivilDateOracleError("CIVIL_MALFORMED_NEUTRAL_INPUT") from error


def _derive(data):
    relation = _validate(data)
    _need(data["policy"] == {"id": "SYNTHETIC-CIVIL-DATE-01", "revision": "1", "selection": "unique_containing_half_open_utc_cell",
                            "offset_convention": "local_equals_utc_plus_minutes", "coverage": "complete_declared_local_dates",
                            "evidence_class": "research_assumption"}, "CIVIL_SELECTED_POLICY")
    events = _index(data["events"])
    _need(len(events) <= MAX_EVENTS, "CIVIL_RESOURCE_BOUND")
    cutoff = _instant(data["cutoff"])
    results = []
    for identity, row in sorted(events.items()):
        _fields(row, {"id", "zone_id", "zone_version", "scope", "occurred_at", "observed_at", "source_ref", "evidence_ref"})
        key = (row["zone_id"], row["zone_version"])
        _need(key in relation["zones"], "CIVIL_ZONE_VERSION")
        _need(row["scope"] == data["scope"], "CIVIL_EVENT_SCOPE")
        _need(row["evidence_ref"] in relation["evidence"], "CIVIL_EVIDENCE_REQUIRED")
        _text(row["source_ref"])
        occurred, observed = _instant(row["occurred_at"]), _instant(row["observed_at"])
        _need(occurred <= observed, "CIVIL_OCCURRENCE_AFTER_OBSERVATION")
        _need(observed < cutoff, "CIVIL_EVENT_CUTOFF")
        matches = [cell for cell in relation["days"][key].values()
                   if _instant(cell["utc_start"]) <= occurred < _instant(cell["utc_end"])]
        _need(len(matches) == 1, "CIVIL_EVENT_OUTSIDE_COVERAGE" if not matches else "CIVIL_AMBIGUOUS_DAY")
        cell = matches[0]
        results.append({"event_id": identity, "zone_id": row["zone_id"], "zone_version": row["zone_version"],
                        "occurred_at": row["occurred_at"], "observed_at": row["observed_at"], "local_date": cell["local_date"],
                        "cell_id": cell["id"], "utc_start": cell["utc_start"], "utc_end": cell["utc_end"],
                        "start_offset_minutes": cell["start_offset_minutes"], "end_offset_minutes": cell["end_offset_minutes"],
                        "event_source_ref": row["source_ref"], "event_evidence_ref": row["evidence_ref"],
                        "calendar_source_ref": cell["source_ref"], "calendar_evidence_ref": cell["evidence_ref"]})
    coverage = []
    for key, zone in sorted(relation["zones"].items()):
        cells = [cell for _, cell in sorted(relation["days"][key].items())]
        coverage.append({"zone_id": key[0], "zone_version": key[1], "local_coverage": dict(zone["local_coverage"]),
                         "utc_start": cells[0]["utc_start"], "utc_end": cells[-1]["utc_end"], "cell_ids": [cell["id"] for cell in cells]})
    return {"events": results, "coverage": coverage,
            "status_meaning": "civil Date from supplied versioned day relation; no ambient timezone, wall clock or monetary output"}


def civil_dates(data):
    """Independently select each original event's unique named-zone day cell."""
    try:
        return _derive(data)
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, CivilDateOracleError):
            raise
        raise CivilDateOracleError("CIVIL_MALFORMED_NEUTRAL_INPUT") from error
