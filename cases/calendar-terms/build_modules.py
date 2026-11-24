"""Mechanical calendar validation and transport; no financial oracle imports.

Gregorian metadata, finite coverage and fiscal partition are data checks. Day
counts for proration, term selection, money and rolled deadlines execute in SPL.
"""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import money, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
MAX_COVERAGE_DAYS = 400
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}


def _require(condition, code):
    if not condition:
        raise ValueError(code)


def _record(value, fields):
    _require(type(value) is dict and set(value) == set(fields), "CALENDAR_RECORD_FIELDS")


def _text(value):
    _require(type(value) is str and bool(value), "CALENDAR_IDENTITY_REQUIRED")


def _date(value):
    _require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "CALENDAR_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("CALENDAR_DATE") from None


def _period(value):
    _record(value, {"start", "end"})
    a, b = _date(value["start"]), _date(value["end"])
    _require(a < b, "CALENDAR_PERIOD")
    return a, b


def _index(rows):
    _require(type(rows) is list, "CALENDAR_RECORD_LIST")
    result = {}
    for row in rows:
        _require(type(row) is dict, "CALENDAR_RECORD_FIELDS")
        _text(row["id"])
        _require(row["id"] not in result, "CALENDAR_DUPLICATE_ID")
        result[row["id"]] = row
    return result


def validate_calendar_inputs(data):
    """Validate original mechanical data; return no solved financial values."""
    _record(data, {"schema_version", "case_id", "scope", "calendar", "fiscal_periods", "selected_period_id",
                   "days", "terms", "as_of", "deadline", "policy", "cutoff", "evidence"})
    _require(data["schema_version"] == "calendar-terms-neutral/1", "CALENDAR_NEUTRAL_SCHEMA")
    _text(data["case_id"])
    scope = data["scope"]
    _record(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _require(scope["currency"] == "USD", "CALENDAR_CURRENCY")
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _record(row, {"id", "scope", "observed_at", "kind"})
        _text(row["kind"])
    calendar = data["calendar"]
    _record(calendar, {"id", "version", "coverage", "closed_weekdays", "ordinal_epoch", "evidence_ref", "source_ref"})
    for key in ["id", "version", "source_ref"]:
        _text(calendar[key])
    _require(calendar["evidence_ref"] in evidence, "CALENDAR_EVIDENCE_REQUIRED")
    _require(calendar["ordinal_epoch"] == "gregorian_0001_01_01_is_1", "CALENDAR_ORDINAL_EPOCH")
    coverage_start, coverage_end = _period(calendar["coverage"])
    _require((coverage_end - coverage_start).days <= MAX_COVERAGE_DAYS, "CALENDAR_COVERAGE_LIMIT")
    weekdays = calendar["closed_weekdays"]
    _require(type(weekdays) is list and all(type(n) is int and 1 <= n <= 7 for n in weekdays)
             and len(set(weekdays)) == len(weekdays), "CALENDAR_WEEKDAY_POLICY")

    def shared(row):
        _require(row["scope"] == scope, "CALENDAR_FACT_SCOPE")
        _require((row["calendar_id"], row["calendar_version"]) == (calendar["id"], calendar["version"]), "CALENDAR_ID_VERSION")
        _require(row["evidence_ref"] in evidence, "CALENDAR_EVIDENCE_REQUIRED")
        _text(row["source_ref"])

    days = _index(data["days"])
    civil_days = set()
    for row in days.values():
        _record(row, {"id", "date", "ordinal", "weekday", "proration_eligible", "holiday_closed", "closed",
                      "calendar_id", "calendar_version", "scope", "evidence_ref", "source_ref"})
        shared(row)
        civil = _date(row["date"])
        _require(civil not in civil_days, "CALENDAR_DUPLICATE_DATE")
        civil_days.add(civil)
        _require(type(row["ordinal"]) is int and row["ordinal"] == civil.toordinal(), "CALENDAR_ORDINAL")
        _require(type(row["weekday"]) is int and row["weekday"] == civil.isoweekday(), "CALENDAR_WEEKDAY")
        _require(all(type(row[key]) is bool for key in ["proration_eligible", "holiday_closed", "closed"]), "CALENDAR_BOOLEAN_FLAGS")
        _require(row["closed"] == (row["holiday_closed"] or row["weekday"] in weekdays), "CALENDAR_CLOSED_FLAGS")
    cursor = coverage_start
    for civil in sorted(civil_days):
        _require(civil == cursor and civil < coverage_end, "CALENDAR_INCOMPLETE_POPULATION")
        cursor += timedelta(days=1)
    _require(cursor == coverage_end, "CALENDAR_INCOMPLETE_POPULATION")
    periods = _index(data["fiscal_periods"])
    _require(data["selected_period_id"] in periods, "CALENDAR_SELECTED_FISCAL_PERIOD")
    intervals = []
    for row in periods.values():
        _record(row, {"id", "calendar_id", "calendar_version", "scope", "period", "evidence_ref", "source_ref"})
        shared(row)
        start, end = _period(row["period"])
        _require(coverage_start <= start < end <= coverage_end, "CALENDAR_FISCAL_BOUNDS")
        intervals.append((start, end))
    cursor = coverage_start
    for start, end in sorted(intervals):
        _require(start >= cursor, "CALENDAR_FISCAL_OVERLAP")
        _require(start == cursor, "CALENDAR_FISCAL_GAP")
        cursor = end
    _require(cursor == coverage_end, "CALENDAR_FISCAL_GAP")


def _amount(value):
    _require(type(value) is str and re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "CALENDAR_EXACT_NONNEGATIVE_MONEY")
    return money(Fraction(value))


def register_calendar_terms():
    reference = _descriptor("calendar-terms", "calendar-terms.spl", "policy.md",
        {"cutoff": "parameter", "policy": "parameter", "evidence": "evidence",
         "comparison": "result", "day_lines": "detail", "term_lines": "detail",
         "observations": "detail", "reconciliation": "reconciliation"}, folder=FOLDER)
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:calendar-terms"
    descriptor["policy"].update(id="SYNTHETIC-CALENDAR-TERMS-01", discriminating_cases=[
        "calendar-proration-01", "recorded-equality", "amendment150", "finite-business-margin", "eligible29"])
    for field in ["days", "fiscal_periods", "terms"]:
        descriptor["constraints"].append({"kind": "unique", "path": "inputs." + field,
            "fields": ["id"], "target": "", "value": ""})
    descriptor["constraints"].append({"kind": "unique", "path": "evidence.evidence",
        "fields": ["id"], "target": "", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def calendar_package(fixture=None, *, reference=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    validate_calendar_inputs(data)
    # Selected record identity resolves the canonical period. This copies an
    # original fiscal record; no financial day count or term answer is computed.
    selected = next(row for row in data["fiscal_periods"] if row["id"] == data["selected_period_id"])
    scope = data["scope"]
    reference = reference or register_calendar_terms()
    days = []
    for original in data["days"]:
        row = deepcopy(original)
        row["calendar_date"] = row.pop("date")
        row["ordinal"], row["weekday"] = str(row["ordinal"]), str(row["weekday"])
        days.append(row)
    terms = []
    for original in _index(data["terms"]).values():
        _record(original, {"id", "revision", "predecessor_id", "effective", "monthly_amount", "scope", "signed_date",
                           "recorded_date", "observed_at", "evidence_ref", "source_ref"})
        _require(type(original["revision"]) is int, "CALENDAR_TERM_REVISION")
        row = deepcopy(original)
        row["revision"], row["monthly_amount"] = str(row["revision"]), _amount(row["monthly_amount"])
        terms.append(row)
    _record(data["deadline"], {"date", "roll", "source_ref"})
    evidence = [{**deepcopy(row), "source_kind": row["kind"], "kind": "selected_synthetic_record",
                 "approval_ref": "CALENDAR_TERMS_SELECTED", "evidence_ref": row["id"]} for row in data["evidence"]]
    calendar = deepcopy(data["calendar"])
    calendar["closed_weekdays"] = [str(value) for value in calendar["closed_weekdays"]]
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-CALENDAR-TERMS", "mode": "final",
            "period": deepcopy(selected["period"]), "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]],
                  "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": "selected-calendar-proration"},
        "inputs": {"scope": {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "period": deepcopy(selected["period"])},
                   "project": scope["asset_id"], "fact_scope": scope, "case_id": data["case_id"], "calendar": calendar,
                   "selected_period_id": data["selected_period_id"], "fiscal_periods": data["fiscal_periods"], "days": days, "terms": terms,
                   "as_of": data["as_of"], "deadline": {"due_date": data["deadline"]["date"], "roll": data["deadline"]["roll"], "source_ref": data["deadline"]["source_ref"]}},
        "parameters": {"policy": data["policy"], "cutoff": data["cutoff"]}, "evidence": {"evidence": evidence}, "state_cells": [],
        "decisions": [{"decision_id": name, "policy_id": "SYNTHETIC-CALENDAR-TERMS-01", "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-synthetic-original-calendar"}
                      for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


if __name__ == "__main__":
    package = calendar_package(reference=register_calendar_terms())
    package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
    write_json(FOLDER / "canonical-package.json", package)
