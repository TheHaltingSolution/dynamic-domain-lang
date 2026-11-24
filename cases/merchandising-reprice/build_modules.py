"""Exact original-fact transport for first-dollar recognition.

This adapter validates record shapes and transports UTC civil dates/lexemes.
It never selects a box observation or calculates a threshold, rate, target,
recognition, issue balance, payment balance or reconstructed opening.
"""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "RR04-MERCHANDISING-CATCHUP-01"
ARRAYS = ["periods", "views", "receipts", "box_office", "issues", "payments", "applications", "populations", "no_default", "evidence"]
BASE = {"id", "scope", "observed_at", "source_ref", "evidence_ref"}
FIELDS = {
    "terms": BASE | {"version", "effective", "production_charge_rate", "license_deduction_rate", "multipliers", "rates", "approved", "recorded_date"},
    "cost_basis": BASE | {"production_cost", "funding_charge"},
    "qualifications": BASE | {"graphic_units", "units_date", "comics_rank", "rank_date", "photography_date", "feature_produced", "feature_released", "approved"},
    "cb_switch": BASE | {"complete", "approved", "effective_date", "receipt_ids", "credit_line_ids", "prior_owner_entitlement", "prior_credit_total", "removed_from_defined_receipts", "included_in_nmi"},
    "periods": BASE | {"period"},
    "views": BASE | {"source_case_id", "period_id", "mode", "as_of", "cutoff", "coverage_end", "recognition_id", "approved"},
    "receipts": BASE | {"period_id", "amount", "received_date", "recognition_date", "qualifying", "lane", "receipt_ref"},
    "box_office": BASE | {"gross", "effective_date", "recorded_date", "metric"},
    "issues": BASE | {"version", "recognition_id", "amount", "issued_date"},
    "payments": BASE | {"bank_disbursement_id", "amount", "paid_date"},
    "applications": BASE | {"payment_id", "issue_id", "amount", "applied_date"},
    "populations": BASE | {"view_id", "complete", "receipt_coverage", "receipt_ids", "receipt_total", "adjustment_ids", "adjustment_total", "box_office_ids", "issue_ids", "issue_total", "payment_ids", "disbursement_ids", "payment_total", "application_ids", "application_total"},
    "no_default": BASE | {"view_id", "approved", "not_in_material_default"},
    "evidence": {"id", "scope", "kind", "approved", "observed_at", "source_ref"},
}
MONEY = {"amount", "production_cost", "funding_charge", "gross", "prior_owner_entitlement", "prior_credit_total", "receipt_total", "issue_total", "payment_total", "application_total", "adjustment_total"}
RATIOS = {"production_charge_rate", "license_deduction_rate"}
DATES = {"effective_date", "recorded_date", "units_date", "rank_date", "photography_date", "as_of", "coverage_end", "received_date", "recognition_date", "issued_date", "paid_date", "applied_date"}
STATE_MONEY = {"known_issued", "actual_paid", "issued_outstanding", "recognized_unissued"}
ATTR_MONEY = {"license_cash", "license_deduction", "nmi", "previously_recognized", "target_entitlement", "recognition_delta"}


def _record(value, fields, optional=()):
    if type(value) is not dict or not set(fields) <= value.keys() or not value.keys() <= set(fields) | set(optional):
        raise ValueError("MR_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("MR_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _midnight(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("MR_DATE")
    date.fromisoformat(value)
    return value + "T00:00:00Z"


def _raw(original):
    payload = json.dumps(original, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if json.loads(payload) != original:
        raise ValueError("MR_ORIGINAL_JSON_TRANSPORT")
    return payload


def _fact(original, kind, evidence_slots=None):
    _record(original, FIELDS[kind])
    if kind == "receipts":
        prefix, marker, suffix = original["receipt_ref"].rpartition("#")
        if not (prefix and marker and suffix):
            raise ValueError("MR_ORIGINAL_LINE_REFERENCE")
    row = deepcopy(original)
    for key in MONEY | RATIOS | {"graphic_units", "comics_rank"}:
        if key in row:
            row["source_" + key] = original[key]
            value = _q(original[key])
            if key in {"graphic_units", "comics_rank"} and value.denominator != 1:
                raise ValueError("MR_INTEGRAL_QUALIFICATION_COUNT")
            row[key] = money(value) if key in MONEY else number(value)
    for key in ["multipliers", "rates"]:
        if key in row:
            row["source_" + key] = deepcopy(original[key])
            row[key] = [number(_q(value)) for value in original[key]]
    for key in ["observed_at", "cutoff"]:
        if key in row:
            row["source_" + key] = original[key]
    for key in DATES:
        if key in row:
            row[key + "_utc"] = _midnight(original[key])
    if "as_of" in row:
        row["as_of_next"] = (date.fromisoformat(original["as_of"]) + timedelta(days=1)).isoformat()
    for key in ["period", "effective", "receipt_coverage"]:
        if key in row:
            _record(original[key], {"start", "end"})
            row[key + "_start_utc"] = _midnight(original[key]["start"])
            row[key + "_end_utc"] = _midnight(original[key]["end"])
    slots = evidence_slots or {}
    if kind == "evidence":
        row["slot"] = number(slots.get(original["id"], -1))
    else:
        row["evidence_slot"] = number(slots.get(original["evidence_ref"], -1))
    row["raw_original"] = _raw(original)
    if neutral_value(row) != original:
        raise ValueError("MR_TYPED_ORIGINAL_TRANSPORT")
    return row


def _attribution(original):
    _record(original, {"receipt_id", "earned_period_id", "receipt_ref", "qualifying", "rate", "kind", *ATTR_MONEY})
    return {"id": original["receipt_id"], **{key: money(_q(value)) if key in ATTR_MONEY else number(_q(value)) if key == "rate" else deepcopy(value)
            for key, value in original.items()}}


def _recognition(original):
    _record(original, {"id", "view_id", "period_id", "source_case_id", "cutoff", "current_earnings", "catchup", "amount", "attributions"})
    row = deepcopy(original)
    for key in ["current_earnings", "catchup", "amount"]:
        row[key] = money(_q(original[key]))
    row["source_cutoff"] = original["cutoff"]
    row["attributions"] = [_attribution(item) for item in original["attributions"]]
    return row


def _state(original):
    frame = {"scope", "purpose", "policy", "boundary", "origin", "source_case_id"}
    detail = {"research", "terms", "cost_basis", "qualifications", "cb_switch", "last_view_id", "recognized_rows", "recognition_history", "sources", *STATE_MONEY}
    _record(original, frame, detail)
    row = {key: deepcopy(original[key]) for key in frame}
    row["transport_profile"] = "merchandising-original-json/1"
    if original["origin"] == "genesis":
        _record(original, frame)
        row["detail"] = {"none": True}
        return row
    _record(original, frame | detail)
    item = {key: deepcopy(original[key]) for key in detail}
    for key in ["terms", "cost_basis", "qualifications", "cb_switch"]:
        _fact(original[key], key)  # Assert exact original/typed round trip.
        item[key] = _raw(original[key])
    for key in STATE_MONEY:
        item[key] = money(_q(original[key]))
    for record in original["recognized_rows"]:
        _record(record, {"receipt_id", "amount"})
    item["recognized_rows"] = [{"id": record["receipt_id"], "receipt_id": record["receipt_id"], "amount": money(_q(record["amount"]))} for record in original["recognized_rows"]]
    item["recognition_history"] = [_recognition(record) for record in original["recognition_history"]]
    _record(original["sources"], ARRAYS)
    item["sources"] = {}
    for key in ARRAYS:
        item["sources"][key] = []
        for record in original["sources"][key]:
            _fact(record, key)
            item["sources"][key].append({"category": key, "id": record["id"], "record": _raw(record)})
    row["detail"] = {"some": item}
    return row


def neutral_value(value):
    if isinstance(value, list):
        return [neutral_value(row) for row in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"value", "currency"}:
        if value["currency"] != "USD":
            raise ValueError("MR_CURRENCY")
        return str(exact(value["value"]))
    if set(value) == {"id", "category", "record"}:
        original = json.loads(value["record"])
        if value["category"] not in ARRAYS or original["id"] != value["id"]:
            raise ValueError("MR_ORIGINAL_STATE_ENVELOPE")
        _record(original, FIELDS[value["category"]])
        return original
    row = {key: neutral_value(item) for key, item in value.items()}
    row.pop("raw_original", None)
    row.pop("slot", None)
    row.pop("evidence_slot", None)
    if "id" in row and (("receipt_id" in row and ("target_entitlement" in row or "amount" in row)) or ("issue_id" in row and "original_amount" in row) or ("view_id" in row and "recognized_cumulative" in row)):
        row.pop("id")
    if "rate" in row:
        row["rate"] = str(exact(row["rate"]))
    for key in ["terms", "cost_basis", "qualifications", "cb_switch"]:
        if key in row and isinstance(row[key], str):
            row[key] = json.loads(row[key])
    row.pop("transport_profile", None)
    for key in list(row):
        if key.startswith("source_") and key not in {"source_case_id", "source_ref"}:
            name = key[len("source_"):]
            if name in MONEY | RATIOS | {"graphic_units", "comics_rank", "multipliers", "rates", "observed_at", "cutoff"}:
                row[name] = row.pop(key)
        if key.endswith("_utc") or key == "as_of_next":
            row.pop(key, None)
    if "detail" in row and set(row) == {"scope", "purpose", "policy", "boundary", "origin", "source_case_id", "detail"}:
        item = row.pop("detail")
        if "some" in item:
            row.update(item["some"])
    return row


neutral_state = neutral_value


def register_merchandising_reprice():
    reference = _descriptor("merchandising-reprice", "merchandising-reprice.spl", "policy.md",
        {"policy": "parameter", "cutoff": "parameter", "evidence": "evidence", "comparison": "result",
         "as_known_snapshots": "detail", "recognition_history": "detail", "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "history", "closing": "history", "purpose": "first_dollar_merchandising", "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"], "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:merchandising-reprice"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["first-dollar-not-marginal", "production-multiplier-not-total-stage", "old-recognized-not-paid", "catchup210-once", "preview-no-state", "actual-Q1-Q4-carry"])
    for key in ARRAYS:
        descriptor["constraints"].append({"kind": "unique", "path": ("evidence." if key == "evidence" else "inputs.") + key, "fields": ["id"], "target": "", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def merchandising_reprice_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _record(data, {"schema_version", "case_id", "scope", "policy", "research", "terms", "cost_basis", "qualifications", "cb_switch", "run", *ARRAYS, "opening_state"}, {"prior_result"})
    if data["schema_version"] != "merchandising-reprice-neutral/1":
        raise ValueError("MR_NEUTRAL_SCHEMA")
    _record(data["research"], {"rr04_sha256", "ld03_sha256", "contract_url", "clause_locator"})
    for key in ["rr04_sha256", "ld03_sha256"]:
        if type(data["research"][key]) is not str or re.fullmatch(r"[0-9a-f]{64}", data["research"][key]) is None:
            raise ValueError("MR_RESEARCH_PIN")
    reference = reference or register_merchandising_reprice()
    selected = [row for row in data["views"] if row["id"] == data["run"]["view_id"]]
    if len(selected) != 1:
        raise ValueError("MR_CURRENT_VIEW_REQUIRED")
    selected_period = [row["period"] for row in data["periods"] if row["id"] == selected[0]["period_id"]]
    if len(selected_period) != 1:
        raise ValueError("MR_UNKNOWN_PERIOD")
    period, scope = selected_period[0], data["scope"]
    frame = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    evidence_slots = {row["id"]: index for index, row in enumerate(data["evidence"])}
    opening = _state(data["opening_state"])
    inputs = {"scope": {key: value for key, value in frame.items() if key != "asset_id"} | {"period": period}, "project": scope["asset_id"],
        "fact_scope": scope, "case_id": data["case_id"], "run": data["run"], "research": data["research"], "source_cutoff": selected[0]["cutoff"],
        **{key: _fact(data[key], key, evidence_slots) for key in ["terms", "cost_basis", "qualifications", "cb_switch"]},
        **{key: [_fact(row, key, evidence_slots) for row in data[key]] for key in ARRAYS if key != "evidence"},
        "supplied_opening": opening, "predecessor": {"none": True}}
    cell = {"opening_port": "history", "state_key": canonical({**frame, "purpose": "first_dollar_merchandising"}), "purpose": "first_dollar_merchandising",
        "unit": "structured", "scope": frame, "boundary": period["start"], "quantity": opening,
        "provenance_ref": "supplied-original-recognition-history", "scenario_id": "SYNTHETIC-MERCHANDISING-REPRICE"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if type(prior.get("result_ref")) is not str or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("MR_CANONICAL_PREDECESSOR_REQUIRED")
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
        cell["prior_result_ref"] = prior["result_ref"]
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells):
        raise ValueError("MR_CANONICAL_PREDECESSOR_MISMATCH")
    evidence = [_fact(row, "evidence", evidence_slots) | {"source_kind": row["kind"], "kind": "selected_synthetic_record", "approval_ref": "MERCHANDISING_REPRICE_SELECTED", "evidence_ref": row["id"]} for row in data["evidence"]]
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-MERCHANDISING-REPRICE", "mode": data["run"]["mode"], "period": period,
            "cutoff": selected[0]["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": "first_dollar_merchandising"},
        "inputs": inputs, "parameters": {"policy": data["policy"], "cutoff": selected[0]["cutoff"]}, "evidence": {"evidence": evidence}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "synthetic-merchandising-recognition-interpretation"}
                      for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def run_merchandising_reprice_package(package, registry_root=None, *, backend="compare", artifact_dir=None):
    return run_module_package(package, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir,
        blocked_evidence_labels={"MR_COMPLETE_POPULATION_REQUIRED": {"payment_evidence_status": "no_event_supplied"}})


if __name__ == "__main__":
    reference = register_merchandising_reprice()
    package = merchandising_reprice_package(reference=reference)
    package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
    write_json(FOLDER / "canonical-package.json", package)
