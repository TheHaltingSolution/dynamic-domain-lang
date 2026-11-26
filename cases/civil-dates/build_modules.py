"""Mechanical original-zone relation validation; SPL classifies every event."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import instant, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-CIVIL-DATE-01"
READER = "civil-date-reader"
POOL = "civil-date-evidence"


def _need(condition, code):
    if not condition:
        raise ValueError(code)


def _record(value, fields):
    _need(type(value) is dict and set(value) == set(fields), "CIVIL_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "CIVIL_IDENTITY_REQUIRED")


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "CIVIL_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("CIVIL_DATE") from None


def _period(value):
    _record(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "CIVIL_LOCAL_COVERAGE")
    return start, end


def _index(rows):
    _need(type(rows) is list, "CIVIL_RECORD_LIST")
    result = {}
    for row in rows:
        _text(row["id"])
        _need(row["id"] not in result, "CIVIL_DUPLICATE_ID")
        result[row["id"]] = row
    return result


def validate_original_relation(data):
    """Validate ORIGINAL day/zone/evidence rows; never read event values.

    Exact Instant seconds use the compiler codec's explicit UTC epoch (day1=0).
    No timezone database, clock or event-specific date/interval selection occurs.
    """
    _record(data, {"schema_version", "case_id", "scope", "cutoff", "policy", "zones", "days", "events", "evidence"})
    _need(data["schema_version"] == "civil-date-neutral/1", "CIVIL_NEUTRAL_SCHEMA")
    _text(data["case_id"])
    _record(data["scope"], {"contract_id", "asset_id"})
    for value in data["scope"].values():
        _text(value)
    cutoff = instant(data["cutoff"]).seconds
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _record(row, {"id", "scope", "observed_at", "kind"})
        _need(row["scope"] == data["scope"], "CIVIL_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(instant(row["observed_at"]).seconds < cutoff, "CIVIL_EVIDENCE_CUTOFF")
    _need(type(data["zones"]) is list and 1 <= len(data["zones"]) <= 4, "CIVIL_RESOURCE_BOUND")
    zones, cells = {}, {}
    for row in data["zones"]:
        _record(row, {"id", "version", "scope", "local_coverage", "source_ref", "evidence_ref"})
        for field in ["id", "version", "source_ref"]:
            _text(row[field])
        key = row["id"], row["version"]
        _need(key not in zones, "CIVIL_DUPLICATE_ZONE_VERSION")
        _need(row["scope"] == data["scope"], "CIVIL_ZONE_SCOPE")
        _need(row["evidence_ref"] in evidence, "CIVIL_EVIDENCE_REQUIRED")
        start, end = _period(row["local_coverage"])
        _need((end - start).days <= 32, "CIVIL_RESOURCE_BOUND")
        zones[key], cells[key] = row, {}
    for row in _index(data["days"]).values():
        _record(row, {"id", "zone_id", "zone_version", "scope", "local_date", "utc_start", "utc_end", "start_offset_minutes", "end_offset_minutes", "source_ref", "evidence_ref"})
        key = row["zone_id"], row["zone_version"]
        _need(key in zones, "CIVIL_ZONE_VERSION")
        _need(row["scope"] == data["scope"], "CIVIL_DAY_SCOPE")
        _need(row["evidence_ref"] in evidence, "CIVIL_EVIDENCE_REQUIRED")
        _text(row["source_ref"])
        local = _day(row["local_date"])
        _need(local not in cells[key], "CIVIL_DUPLICATE_LOCAL_DATE")
        start_offset, end_offset = row["start_offset_minutes"], row["end_offset_minutes"]
        _need(all(type(value) is int and -1439 <= value <= 1439 for value in [start_offset, end_offset]), "CIVIL_OFFSET_MINUTES")
        start, end = instant(row["utc_start"]).seconds, instant(row["utc_end"]).seconds
        _need(start < end, "CIVIL_INTERVAL_POSITIVE")
        _need(start == (local.toordinal() - 1) * 86400 - start_offset * 60 and end == local.toordinal() * 86400 - end_offset * 60,
              "CIVIL_MIDNIGHT_OFFSET_RELATION")
        cells[key][local] = row
    for key, zone in zones.items():
        start, end = _period(zone["local_coverage"])
        _need({day.toordinal() for day in cells[key]} == set(range(start.toordinal(), end.toordinal())), "CIVIL_INCOMPLETE_LOCAL_POPULATION")
        previous = None
        for local in sorted(cells[key]):
            current = cells[key][local]
            if previous is not None:
                _need(previous["end_offset_minutes"] == current["start_offset_minutes"], "CIVIL_OFFSET_CONTINUITY")
                _need(instant(previous["utc_end"]).seconds == instant(current["utc_start"]).seconds, "CIVIL_UTC_GAP_OR_OVERLAP")
            previous = current
    return {"zones": zones, "days": cells, "evidence": evidence}


def neutral_value(value):
    if isinstance(value, list):
        return [neutral_value(row) for row in value]
    if isinstance(value, dict):
        row = {key: neutral_value(item) for key, item in value.items()}
        for field in ["start_offset_minutes", "end_offset_minutes"]:
            if field in row:
                row[field] = int(row[field])
        return row
    return value


def register_civil_dates():
    reference = _descriptor("civil-dates", "civil-dates.spl", "policy.md",
        {"policy": "parameter", "cutoff": "parameter", "evidence": "evidence", "comparison": "result", "event_results": "detail",
         "coverage": "detail", "reconciliation": "reconciliation"}, folder=FOLDER)
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:civil-dates"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["native-selected-date", "midnight-inclusive", "submicrosecond-before-boundary", "23-and-25-hour-cells", "explicit-zone-version"])
    for field, identities in [("zones", ["id", "version"]), ("days", ["id"]), ("events", ["id"])]:
        descriptor["constraints"].append({"kind": "unique", "path": "inputs." + field, "fields": identities, "target": "", "value": ""})
    descriptor["constraints"].extend([
        {"kind": "unique", "path": "evidence.evidence", "fields": ["id"], "target": "", "value": ""},
        {"kind": "equals", "path": "inputs.contract", "fields": [], "target": "scope.agreement_id", "value": ""},
        {"kind": "equals", "path": "parameters.cutoff", "fields": [], "target": "manifest.cutoff", "value": ""}])
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def civil_date_package(fixture=None, *, reference=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    relation = validate_original_relation(data)
    reference = reference or register_civil_dates()
    events = []
    _need(type(data["events"]) is list and len(data["events"]) <= 128, "CIVIL_RESOURCE_BOUND")
    for original in data["events"]:
        _record(original, {"id", "zone_id", "zone_version", "scope", "occurred_at", "observed_at", "source_ref", "evidence_ref"})
        events.append({**deepcopy(original), "source_occurred_at": original["occurred_at"], "source_observed_at": original["observed_at"]})
    days = []
    for original in data["days"]:
        row = deepcopy(original)
        row.update(source_utc_start=original["utc_start"], source_utc_end=original["utc_end"],
                   start_offset_minutes=str(original["start_offset_minutes"]), end_offset_minutes=str(original["end_offset_minutes"]))
        days.append(row)
    evidence = [{**deepcopy(row), "source_kind": row["kind"], "kind": "selected_synthetic_record", "approval_ref": "CIVIL_DATES_SELECTED", "evidence_ref": row["id"]}
                for row in data["evidence"]]
    # Only original DECLARED coverage bounds determine execution metadata. No
    # event is classified or used to derive an event-specific civil Date here.
    envelope = {"start": min(row["local_coverage"]["start"] for row in relation["zones"].values()),
                "end": max(row["local_coverage"]["end"] for row in relation["zones"].values())}
    _need(all(envelope["start"] <= row["local_coverage"]["start"] < row["local_coverage"]["end"] <= envelope["end"]
              for row in data["zones"]), "CIVIL_LOCAL_COVERAGE")
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-CIVIL-DATE", "mode": "final", "period": envelope,
            "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": data["scope"]["contract_id"], "participant_ids": [READER], "pool_id": POOL,
                  "asset_ids": [data["scope"]["asset_id"]], "purpose": "civil_date_evidence_envelope_only"},
        "inputs": {"contract": data["scope"]["contract_id"], "project": data["scope"]["asset_id"], "fact_scope": data["scope"],
            "case_id": data["case_id"], "zones": data["zones"], "days": days, "events": events},
        "parameters": {"policy": data["policy"], "cutoff": data["cutoff"]}, "evidence": {"evidence": evidence}, "state_cells": [],
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "supplied-synthetic-zone-relation"}
                      for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


if __name__ == "__main__":
    package = civil_date_package(reference=register_civil_dates())
    package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
    write_json(FOLDER / "canonical-package.json", package)
