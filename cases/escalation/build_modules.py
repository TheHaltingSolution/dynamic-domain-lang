"""Exact original-fact transport for fixed-table escalation; no financial oracle."""
from copy import deepcopy
from datetime import date
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-ESCALATION-01"
METHODS = ["prospective_split", "current_period_ending_rate", "row_opening_rate", "row_ending_rate", "cumulative_reprice_delta"]
SUMMARY = ["opening_basis", "opening_recognized", "current_result", "closing_basis", "closing_recognized"]


def _record(value, fields, optional=()):
    if type(value) is not dict or not set(fields) <= value.keys() or not value.keys() <= set(fields) | set(optional):
        raise ValueError("ESCALATION_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("ESCALATION_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _sequence(value):
    if type(value) is not int:
        raise ValueError("ESCALATION_EXPLICIT_INTEGER_SEQUENCE")
    return str(value)


def _utc_opening(period):
    # Mechanical convention explicitly selected by policy. No financial selection.
    day = period["start"]
    if type(day) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day):
        raise ValueError("ESCALATION_DATE")
    date.fromisoformat(day)
    return day + "T00:00:00Z"


def _event(original):
    _record(original, {"id", "scope", "basis", "sequence", "effective_date", "observed_at", "source_ref", "evidence_ref"})
    row = deepcopy(original)
    row.update(basis=money(_q(original["basis"])), source_basis=original["basis"], sequence=_sequence(original["sequence"]), source_observed_at=original["observed_at"])
    return row


def _table(original):
    _record(original, {"id", "version", "scope", "effective", "approved_date", "recorded_date", "observed_at", "source_ref", "evidence_ref", "brackets"})
    result = deepcopy(original)
    result["source_observed_at"] = original["observed_at"]
    result["brackets"] = []
    for original_band in original["brackets"]:
        _record(original_band, {"id", "sequence", "lower", "upper", "rate", "source_ref", "evidence_ref"})
        row = deepcopy(original_band)
        row.update(sequence=_sequence(row["sequence"]), source_lower=row["lower"], source_upper=row["upper"], source_rate=row["rate"],
                   lower=money(_q(row["lower"])), upper={"none": True} if row["upper"] == "unbounded" else {"some": money(_q(row["upper"]))},
                   rate=number(_q(row["rate"])))
        result["brackets"].append(row)
    return result


def _history(original):
    _record(original, {"source_case_id", "period", "opening_basis", "opening_recognized", "events", "current_result", "closing_basis", "closing_recognized"})
    row = deepcopy(original)
    row.update(opening_utc=_utc_opening(row["period"]), events=[_event(event) for event in row["events"]])
    # Preserve original historical summary spellings only when normalization loses
    # them. Calculated current summaries use none(), stable across actual carry.
    raw = {key: original[key] for key in SUMMARY}
    row["source_numbers"] = {"some": raw} if any(str(_q(raw[key])) != raw[key] for key in SUMMARY) else {"none": True}
    for key in SUMMARY:
        row[key] = money(_q(original[key]))
    return row


def _state(original):
    _record(original, {"scope", "purpose", "policy_id", "policy_revision", "method", "bracket_table", "boundary", "origin", "source_case_id",
                       "cumulative_basis", "recognized_entitlement", "period_history"})
    row = deepcopy(original)
    row.update(bracket_table=_table(row["bracket_table"]), cumulative_basis=money(_q(row["cumulative_basis"])),
               recognized_entitlement=money(_q(row["recognized_entitlement"])), period_history=[_history(record) for record in row["period_history"]])
    return row


def neutral_value(value):
    """Decode tagged money, explicit alternatives and source lexical metadata."""
    if isinstance(value, list):
        return [neutral_value(row) for row in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"value", "currency"}:
        if value["currency"] != "USD":
            raise ValueError("ESCALATION_CURRENCY")
        return str(exact(value["value"]))
    result = {key: neutral_value(item) for key, item in value.items()}
    if "sequence" in result:
        result["sequence"] = int(exact(result["sequence"]))
    if "source_basis" in result:
        result["basis"] = result.pop("source_basis")
    if "source_observed_at" in result:
        result["observed_at"] = result.pop("source_observed_at")
    if "source_lower" in result:
        for key in ["lower", "upper", "rate"]:
            result[key] = result.pop("source_" + key)
    if "source_numbers" in result:
        original = result.pop("source_numbers")
        result.update(original.get("some", {}))
    result.pop("opening_utc", None)
    if "rate_details" in result:
        detail = result["rate_details"]
        result["rate_details"] = ({"kind": detail["kind"], "slices": detail["slices"]} if detail["kind"] == "marginal_slices"
                                  else {"kind": detail["kind"], **detail["selected"]["some"]})
    return result


neutral_state = neutral_value


def register_escalation():
    reference = _descriptor("escalation", "escalation.spl", "policy.md",
        {"policy": "parameter", "cutoff": "parameter", "evidence": "evidence", "comparison": "result", "rows": "detail",
         "period_replays": "detail", "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "history", "closing": "history", "purpose": "cumulative_escalation", "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"], "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:ordered-escalation"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["five-distinct-methods", "actual-history-replay", "lower-inclusive", "row-partition-effects"])
    for field in ["events", "bracket_table.brackets"]:
        descriptor["constraints"].append({"kind": "unique", "path": "inputs." + field, "fields": ["id"], "target": "", "value": ""})
    descriptor["constraints"].append({"kind": "unique", "path": "evidence.evidence", "fields": ["id"], "target": "", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def escalation_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _record(data, {"schema_version", "case_id", "scope", "period", "as_of", "cutoff", "policy", "bracket_table", "events", "evidence", "opening_state"}, {"prior_result"})
    if data["schema_version"] != "escalation-neutral/1":
        raise ValueError("ESCALATION_NEUTRAL_SCHEMA")
    reference = reference or register_escalation()
    scope = data["scope"]
    frame = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    opening = _state(data["opening_state"])
    inputs = {"scope": {key: value for key, value in frame.items() if key != "asset_id"} | {"period": data["period"]},
              "project": scope["asset_id"], "fact_scope": scope, "case_id": data["case_id"], "as_of": data["as_of"],
              "opening_utc": _utc_opening(data["period"]), "bracket_table": _table(data["bracket_table"]),
              "events": [_event(row) for row in data["events"]], "supplied_opening": opening, "predecessor": {"none": True}}
    cell = {"opening_port": "history", "state_key": canonical({**frame, "purpose": "cumulative_escalation"}),
            "purpose": "cumulative_escalation", "unit": "structured", "scope": frame, "boundary": data["period"]["start"],
            "quantity": opening, "provenance_ref": "supplied-original-escalation-history", "scenario_id": "SYNTHETIC-ESCALATION"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if type(prior.get("result_ref")) is not str or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("ESCALATION_CANONICAL_PREDECESSOR_REQUIRED")
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
        cell["prior_result_ref"] = prior["result_ref"]
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells):
        raise ValueError("ESCALATION_CANONICAL_PREDECESSOR_MISMATCH")
    evidence = []
    for original in data["evidence"]:
        _record(original, {"id", "scope", "observed_at", "kind"})
        evidence.append({**deepcopy(original), "source_kind": original["kind"], "kind": "selected_synthetic_record",
                         "source_observed_at": original["observed_at"],
                         "approval_ref": "ESCALATION_SELECTED", "evidence_ref": original["id"]})
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-ESCALATION", "mode": "final", "period": data["period"],
                     "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
                     "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": "cumulative_escalation"},
        "inputs": inputs, "parameters": {"policy": data["policy"], "cutoff": data["cutoff"]}, "evidence": {"evidence": evidence}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "synthetic-fixed-table-method"}
                      for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


if __name__ == "__main__":
    reference = register_escalation()
    for method in METHODS:
        data = read_json(FOLDER / "neutral.json")
        data["policy"]["method"] = data["opening_state"]["method"] = method
        package = escalation_package(data, reference=reference)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / (method.replace("_", "-") + "-canonical-package.json"), package)
