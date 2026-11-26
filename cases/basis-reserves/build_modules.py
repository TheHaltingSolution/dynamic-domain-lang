"""Mechanical original-record transport for elected basis reserves.

All additions, deadlines, returns, unused releases, Net Receipts, fees and
allocations execute in SPL. This module only encodes originals/state and binds
the generic registered interface. Evidence slots are original positions.
"""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, instant, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "RR04-GENIUS-BASIS-RESERVE-01"
PURPOSE = "basis_stage_videogram_returns"
TRANSPORT = "basis-reserve-original-json/1"
ARRAYS = ["checkpoints", "receipts", "elections", "returns", "return_authorities", "populations", "clearances", "evidence"]
BASE = {"id", "scope", "observed_at", "source_ref", "evidence_ref"}
FIELDS = {
    "authority": BASE | {"version", "effective", "sales_period_id", "reserve_rate", "fee_rate", "fee_substitute", "source_fee_redacted", "original_distributor", "successor_id", "successor_authorized", "covered_program", "approved"},
    "checkpoints": BASE | {"source_case_id", "period", "as_of", "cutoff", "approved"},
    "receipts": BASE | {"amount", "receipt_date", "sequence", "cash_received_country", "territory", "medium", "election_id", "cash_line_ref"},
    "elections": BASE | {"receipt_id", "vintage_id", "purpose", "elected", "election_date", "approved_date", "approved"},
    "returns": BASE | {"receipt_id", "vintage_id", "claim_id", "amount", "return_date", "sequence", "authority_id", "return_line_ref"},
    "return_authorities": BASE | {"return_id", "receipt_id", "vintage_id", "purpose", "approved", "approved_date"},
    "populations": BASE | {"checkpoint_id", "complete", "receipt_ids", "receipt_total", "election_ids", "return_ids", "return_total", "authority_ids", "other_adjustment_ids", "other_adjustment_total"},
    "clearances": BASE | {"checkpoint_id", "complete", "approved", "minimum_guarantee_remaining", "expense_remaining", "unresolved_claim_ids"},
    "evidence": {"id", "scope", "kind", "approved", "observed_at", "source_ref"},
}
MONEY = {"amount", "receipt_total", "return_total", "other_adjustment_total", "minimum_guarantee_remaining", "expense_remaining"}
RATIOS = {"reserve_rate", "fee_rate"}
DATES = {"as_of", "receipt_date", "election_date", "approved_date", "return_date"}
TOTALS = ["gross", "added", "applied_returns", "released", "net_receipts", "fee", "allocation"]
VINTAGE_MONEY = {"added", "applied_returns", "released", "available"}
MOVE_MONEY = {"gross", "reserve_addition", "return_applied", "release", "net_receipts", "fee", "allocation"}
MOVEMENT_CATEGORIES = {"addition", "return", "due-release"}


def _record(value, fields, optional=()):
    if type(value) is not dict or not set(fields) <= value.keys() or not value.keys() <= set(fields) | set(optional):
        raise ValueError("BR_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("BR_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _midnight(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("BR_DATE")
    date.fromisoformat(value)
    return value + "T00:00:00Z"


def _raw(original):
    payload = json.dumps(original, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if json.loads(payload) != original:
        raise ValueError("BR_ORIGINAL_JSON_TRANSPORT")
    return payload


def _fact(original, kind, slots=None):
    _record(original, FIELDS[kind])
    row = deepcopy(original)
    for field in ["cash_line_ref", "return_line_ref"]:
        if field in row:
            prefix, marker, suffix = row[field].rpartition("#")
            if not (prefix and marker and suffix):
                raise ValueError("BR_ORIGINAL_LINE_REFERENCE")
    for key in MONEY | RATIOS:
        if key in row:
            row["source_" + key] = original[key]
            row[key] = money(_q(original[key])) if key in MONEY else number(_q(original[key]))
    if "sequence" in row:
        if type(row["sequence"]) is not int:
            raise ValueError("BR_INTEGER_SEQUENCE")
        row["sequence"] = number(row["sequence"])
    for key in ["observed_at", "cutoff"]:
        if key in row:
            row["source_" + key] = original[key]
    for key in DATES:
        if key in row:
            row[key + "_utc"] = _midnight(original[key])
    if "as_of" in row:
        row["as_of_next"] = (date.fromisoformat(original["as_of"]) + timedelta(days=1)).isoformat()
    for key in ["period", "effective"]:
        if key in row:
            _record(original[key], {"start", "end"})
            row[key + "_start_utc"] = _midnight(original[key]["start"])
            row[key + "_end_utc"] = _midnight(original[key]["end"])
    lookup = slots or {}
    if kind == "evidence":
        row["slot"] = number(lookup.get(original["id"], -1))
    else:
        row["evidence_slot"] = number(lookup.get(original["evidence_ref"], -1))
    row["raw_original"] = _raw(original)
    if neutral_value(row) != original:
        raise ValueError("BR_TYPED_ORIGINAL_TRANSPORT")
    return row


def _key(value):
    if type(value) is not str:
        raise ValueError("BR_MOVEMENT_ID")
    prefix, separator, original = value.partition(":")
    if prefix not in MOVEMENT_CATEGORIES or not separator or not original:
        raise ValueError("BR_MOVEMENT_ID")
    return [prefix, original]


def _movement(original):
    base = {"id", "kind", "date", "receipt_id", "vintage_id", *MOVE_MONEY}
    _record(original, base, {"election_id", "source_ref", "claim_id", "authority_id"})
    row = {key: deepcopy(original[key]) for key in base}
    row["id"] = _key(original["id"])
    row["movement_date"] = row.pop("date")
    for key in MOVE_MONEY:
        row[key] = money(_q(original[key]))
    for key in ["election_id", "source_ref", "claim_id", "authority_id"]:
        row[key] = {"some": original[key]} if key in original else {"none": True}
    return row


def _vintage(original):
    _record(original, {"id", "scope", "purpose", "receipt_id", "cash_line_ref", "election_id", "election_record", "reserve_elected", "origin_date", "due_date", *VINTAGE_MONEY, "return_ids", "claim_ids", "release_ids"})
    row = deepcopy(original)
    _fact(original["election_record"], "elections")
    row["election_record"] = _raw(original["election_record"])
    for key in VINTAGE_MONEY:
        row[key] = money(_q(original[key]))
    row["release_ids"] = [_key(value) for value in original["release_ids"]]
    return row


def _state(original):
    frame = {"scope", "purpose", "policy", "boundary", "origin", "source_case_id"}
    detail = {"research", "authority", "last_checkpoint_id", "vintages", "cumulative", "movements", "sources"}
    _record(original, frame, detail)
    row = {key: deepcopy(original[key]) for key in frame}
    row["transport_profile"] = TRANSPORT
    if original["origin"] == "genesis":
        _record(original, frame)
        row["detail"] = {"none": True}
        return row
    _record(original, frame | detail)
    _fact(original["authority"], "authority")
    _record(original["cumulative"], TOTALS)
    _record(original["sources"], ARRAYS)
    item = {"research": deepcopy(original["research"]), "authority": _raw(original["authority"]), "last_checkpoint_id": original["last_checkpoint_id"],
        "vintages": [_vintage(record) for record in original["vintages"]],
        "cumulative": {key: money(_q(original["cumulative"][key])) for key in TOTALS},
        "movements": [_movement(record) for record in original["movements"]], "sources": {}}
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
            raise ValueError("BR_CURRENCY")
        return str(exact(value["value"]))
    if set(value) == {"id", "category", "record"}:
        original = json.loads(value["record"])
        if value["category"] not in ARRAYS or original["id"] != value["id"]:
            raise ValueError("BR_ORIGINAL_STATE_ENVELOPE")
        _record(original, FIELDS[value["category"]])
        return original
    row = {key: neutral_value(item) for key, item in value.items()}
    for field in ["raw_original", "slot", "evidence_slot", "evidence_observed_at", "transport_profile"]:
        row.pop(field, None)
    for key in list(row):
        if key.startswith("source_") and key not in {"source_case_id", "source_ref"}:
            name = key[len("source_"):]
            if name in MONEY | RATIOS | {"observed_at", "cutoff"}:
                row[name] = row.pop(key)
        if key.endswith("_utc") or key == "as_of_next":
            row.pop(key, None)
    if "sequence" in row:
        row["sequence"] = int(exact(row["sequence"]))
    if "id" in row and "checkpoint_id" in row and "closing_reserve" in row:
        row.pop("id")  # Duplicate original checkpoint identity on derived rows.
    if "kind" in row and "net_receipts" in row and isinstance(row.get("id"), list):
        category, original = row["id"]
        if category not in MOVEMENT_CATEGORIES or not original:
            raise ValueError("BR_MOVEMENT_ID")
        row["id"] = category + ":" + original
        row["date"] = row.pop("movement_date")
        for key in ["election_id", "source_ref", "claim_id", "authority_id"]:
            item = row.pop(key)
            if "some" in item:
                row[key] = item["some"]
    if "release_ids" in row:
        restored = []
        for category, original in row["release_ids"]:
            if category != "due-release" or original != row["id"]:
                raise ValueError("BR_RELEASE_ID")
            restored.append(category + ":" + original)
        row["release_ids"] = restored
    for key in ["authority", "election_record"]:
        if key in row and isinstance(row[key], str):
            row[key] = json.loads(row[key])
    if "detail" in row and set(row) == {"scope", "purpose", "policy", "boundary", "origin", "source_case_id", "detail"}:
        item = row.pop("detail")
        if "some" in item:
            row.update(item["some"])
    return row


neutral_state = neutral_value


def first_run(facts):
    """Materialize only the first declared fixture checkpoint, never finances."""
    data = deepcopy(facts)
    checkpoint = data["checkpoints"][0]
    data["case_id"], data["run_checkpoint_id"] = checkpoint["source_case_id"], checkpoint["id"]
    data["checkpoints"] = [checkpoint]
    for key in ["populations", "clearances"]:
        data[key] = [row for row in data[key] if row["checkpoint_id"] == checkpoint["id"]]
    data["receipts"] = [row for row in data["receipts"] if row["receipt_date"] <= checkpoint["as_of"]]
    receipts = {row["id"] for row in data["receipts"]}
    data["elections"] = [row for row in data["elections"] if row["receipt_id"] in receipts]
    data["returns"] = [row for row in data["returns"] if row["return_date"] <= checkpoint["as_of"]]
    returned = {row["id"] for row in data["returns"]}
    data["return_authorities"] = [row for row in data["return_authorities"] if row["return_id"] in returned]
    before = instant(checkpoint["cutoff"]).seconds
    data["evidence"] = [row for row in data["evidence"] if instant(row["observed_at"]).seconds < before]
    data["opening_state"] = {"scope": data["scope"], "purpose": PURPOSE, "policy": data["policy"], "boundary": data["authority"]["effective"]["start"], "origin": "genesis", "source_case_id": "genesis"}
    return data


def register_basis_reserves():
    reference = _descriptor("basis-reserves", "basis-reserves.spl", "policy.md",
        {"policy": "parameter", "cutoff": "parameter", "evidence": "evidence", "comparison": "result", "checkpoint_results": "detail", "vintages": "detail", "movements": "detail", "reconciliation": "reconciliation"}, folder=FOLDER, capabilities=("spl.calendar-months/1",),
        state=[{"opening": "history", "closing": "history", "purpose": PURPOSE, "unit": "structured",
            "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"], "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:basis-reserves"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["five-period-1740-174-1566", "non-elected-positive", "six-calendar-months", "due-return-before-release", "within-vintage-no-borrowing", "excess-return-separate-policy"])
    for key in ARRAYS:
        descriptor["constraints"].append({"kind": "unique", "path": ("evidence." if key == "evidence" else "inputs.") + key, "fields": ["id"], "target": "", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def basis_reserve_package(fixture=None, *, reference=None, state_cells=None, mode="final"):
    data = deepcopy(first_run(read_json(FOLDER / "neutral.json")["facts"]) if fixture is None else fixture)
    _record(data, {"schema_version", "case_id", "scope", "policy", "research", "authority", "run_checkpoint_id", *ARRAYS, "opening_state"}, {"prior_result"})
    if data["schema_version"] != "basis-reserves-neutral/1" or mode not in {"final", "preview"}:
        raise ValueError("BR_NEUTRAL_SCHEMA")
    _record(data["research"], {"rr04_sha256", "ld03_sha256", "primary_url", "assignment_url", "clauses"})
    for key in ["rr04_sha256", "ld03_sha256"]:
        if type(data["research"][key]) is not str or re.fullmatch(r"[0-9a-f]{64}", data["research"][key]) is None:
            raise ValueError("BR_RESEARCH_PIN")
    selected = [row for row in data["checkpoints"] if row["id"] == data["run_checkpoint_id"]]
    if len(selected) != 1:
        raise ValueError("BR_CURRENT_CHECKPOINT")
    checkpoint, scope = selected[0], data["scope"]
    reference = reference or register_basis_reserves()
    frame = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    slots = {row["id"]: index for index, row in enumerate(data["evidence"])}
    opening = _state(data["opening_state"])
    inputs = {"scope": {key: value for key, value in frame.items() if key != "asset_id"} | {"period": checkpoint["period"]}, "project": scope["asset_id"],
        "fact_scope": scope, "case_id": data["case_id"], "run_checkpoint_id": data["run_checkpoint_id"], "research": data["research"],
        "source_cutoff": checkpoint["cutoff"], "authority": _fact(data["authority"], "authority", slots),
        **{key: [_fact(row, key, slots) for row in data[key]] for key in ARRAYS if key != "evidence"},
        "supplied_opening": opening, "predecessor": {"none": True}}
    cell = {"opening_port": "history", "state_key": canonical({**frame, "purpose": PURPOSE}), "purpose": PURPOSE, "unit": "structured", "scope": frame,
        "boundary": checkpoint["period"]["start"], "quantity": opening, "provenance_ref": "supplied-original-reserve-history", "scenario_id": "SYNTHETIC-BASIS-RESERVES"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if type(prior.get("result_ref")) is not str or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("BR_CANONICAL_PREDECESSOR_REQUIRED")
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
        cell["prior_result_ref"] = prior["result_ref"]
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells):
        raise ValueError("BR_CANONICAL_PREDECESSOR_MISMATCH")
    evidence = [_fact(row, "evidence", slots) | {"source_kind": row["kind"], "kind": "selected_synthetic_record", "approval_ref": "BASIS_RESERVES_SELECTED", "evidence_ref": row["id"]} for row in data["evidence"]]
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-BASIS-RESERVES", "mode": mode, "period": checkpoint["period"], "cutoff": checkpoint["cutoff"],
            "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": PURPOSE},
        "inputs": inputs, "parameters": {"policy": data["policy"], "cutoff": checkpoint["cutoff"]}, "evidence": {"evidence": evidence}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "synthetic-selected-genius-reserve-policy"}
            for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def run_basis_reserve_package(package, registry_root=None, *, backend="compare", artifact_dir=None):
    return run_module_package(package, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir)


if __name__ == "__main__":
    reference = register_basis_reserves()
    for mode, name in [("final", "canonical-package.json"), ("preview", "preview-canonical-package.json")]:
        package = basis_reserve_package(reference=reference, mode=mode)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / name, package)
