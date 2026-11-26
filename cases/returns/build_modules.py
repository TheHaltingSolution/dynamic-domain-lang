"""Explicit linked-return registration and mechanical original-record transport.

Original-rate reversals, original registration, cumulative measurement limits,
title aggregation and loss arithmetic run in SPL. No financial oracle imports.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-RETURNS-LOSSES-01"


def _record(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or not value.keys() <= set(required) | set(optional):
        raise ValueError("RETURNS_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("RETURNS_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _original(row, *, registry=False):
    fields = {"id", "asset_id", "scope", "basis", "rate", "measurement_date", "observed_at", "source_ref", "evidence_ref"}
    if registry:
        fields |= {"returned_basis", "origin_kind", "registered_case_id"}
    _record(row, fields)
    result = deepcopy(row)
    result["basis"], result["rate"] = money(_q(row["basis"])), number(_q(row["rate"]))
    if registry:
        result["returned_basis"] = money(_q(row["returned_basis"]))
    return result


def _state(value):
    _record(value, {"scope", "asset_ids", "purpose", "policy_id", "policy_revision", "method", "boundary", "origin",
                    "source_case_id", "loss_carry", "original_registry", "recognized_ids"})
    result = deepcopy(value)
    result["loss_carry"] = money(_q(value["loss_carry"]))
    result["original_registry"] = [_original(row, registry=True) for row in value["original_registry"]]
    tokens = []
    for token in value["recognized_ids"]:
        if type(token) is not str or ":" not in token:
            raise ValueError("RETURNS_RECOGNIZED_HISTORY")
        kind, identity = token.split(":", 1)
        if kind not in {"originals", "sales", "returns"} or not identity:
            raise ValueError("RETURNS_RECOGNIZED_HISTORY")
        tokens.append([kind, identity])
    result["recognized_ids"] = tokens
    return result


def neutral_state(value):
    """Decode canonical quantity tags and tuple history, without pricing."""
    if isinstance(value, dict):
        if set(value) == {"value", "currency"}:
            if value["currency"] != "USD":
                raise ValueError("RETURNS_CURRENCY")
            return str(exact(value["value"]))
        if set(value) == {"numerator", "denominator"}:
            return str(exact(value))
        result = {key: neutral_state(item) for key, item in value.items()}
        if "rate" in result:
            result["rate"] = str(exact(value["rate"]))
        if "recognized_ids" in result:
            result["recognized_ids"] = [kind + ":" + identity for kind, identity in result["recognized_ids"]]
        return result
    if isinstance(value, list):
        return [neutral_state(item) for item in value]
    return value


def register_returns():
    reference = _descriptor("returns", "returns.spl", "policy.md",
        {"cutoff": "parameter", "policy": "parameter", "evidence": "evidence", "comparison": "result",
         "titles": "detail", "sale_lines": "detail", "return_lines": "detail", "original_lines": "detail",
         "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "ledger", "closing": "ledger", "purpose": "returns_and_loss", "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "purpose"],
                "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:returns-losses"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["signed60-floor100", "old-rate-not-current-rate", "loss40-10-0", "partial30-plus50"])
    for field, identity in [("originals", "id"), ("sales", "id"), ("returns", "id"), ("current_rates", "asset_id")]:
        descriptor["constraints"].append({"kind": "unique", "path": "inputs." + field,
            "fields": [identity], "target": "", "value": ""})
    descriptor["constraints"].extend([
        {"kind": "unique", "path": "evidence.evidence", "fields": ["id"], "target": "", "value": ""},
        {"kind": "member_of", "path": "inputs.asset_ids", "fields": [], "target": "scope.asset_ids", "value": ""},
        {"kind": "member_of", "path": "scope.asset_ids", "fields": [], "target": "inputs.asset_ids", "value": ""}])
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def returns_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _record(data, {"schema_version", "case_id", "scope", "asset_ids", "period", "cutoff", "policy", "current_rates",
                   "originals", "sales", "returns", "evidence", "opening_state"}, {"prior_result"})
    if data["schema_version"] != "returns-neutral/1":
        raise ValueError("RETURNS_NEUTRAL_SCHEMA")
    scope = data["scope"]
    _record(scope, {"contract_id", "participant_id", "pool_id", "currency"})
    if scope["currency"] != "USD":
        raise ValueError("RETURNS_CURRENCY")
    reference = reference or register_returns()
    inputs = {"scope": {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"],
                        "pool_id": scope["pool_id"], "period": deepcopy(data["period"])},
              "fact_scope": scope, "asset_ids": data["asset_ids"], "case_id": data["case_id"],
              "originals": [_original(row) for row in data["originals"]], "supplied_opening": _state(data["opening_state"])}
    rates = []
    for original in data["current_rates"]:
        _record(original, {"asset_id", "rate", "scope", "effective", "observed_at", "source_ref", "evidence_ref"})
        row = deepcopy(original)
        row["rate"] = number(_q(row["rate"]))
        rates.append(row)
    inputs["current_rates"] = rates
    for key, amount_field, extra in [
            ("sales", "basis", {"effective_date"}),
            ("returns", "returned_basis", {"original_id", "return_date", "recognition_date"})]:
        inputs[key] = []
        for original in data[key]:
            _record(original, {"id", "asset_id", "scope", amount_field, "observed_at", "source_ref", "evidence_ref"} | extra)
            row = deepcopy(original)
            row[amount_field] = money(_q(row[amount_field]))
            inputs[key].append(row)
    evidence = []
    for row in data["evidence"]:
        _record(row, {"id", "scope", "observed_at", "kind"})
        evidence.append({**deepcopy(row), "source_kind": row["kind"], "kind": "selected_synthetic_record",
                         "approval_ref": "RETURNS_SELECTED", "evidence_ref": row["id"]})
    cell_scope = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"]}
    cell = {"opening_port": "ledger", "state_key": canonical({**cell_scope, "purpose": "returns_and_loss"}),
            "purpose": "returns_and_loss", "unit": "structured", "scope": cell_scope, "boundary": data["period"]["start"],
            "quantity": _state(data["opening_state"]), "provenance_ref": "supplied-original-returns-opening", "scenario_id": "SYNTHETIC-RETURNS"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if type(prior.get("result_ref")) is not str or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("RETURNS_CANONICAL_PREDECESSOR_REQUIRED")
        cell["prior_result_ref"] = prior["result_ref"]
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
    else:
        inputs["predecessor"] = {"none": True}
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells):
        raise ValueError("RETURNS_CANONICAL_PREDECESSOR_MISMATCH")
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-RETURNS", "mode": "final",
            "period": data["period"], "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]],
                  "pool_id": scope["pool_id"], "asset_ids": data["asset_ids"], "purpose": "selected-original-rate-returns"},
        "inputs": inputs, "parameters": {"cutoff": data["cutoff"], "policy": data["policy"]}, "evidence": {"evidence": evidence}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-synthetic-original-measurements"}
                      for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


if __name__ == "__main__":
    reference = register_returns()
    for method in ["signed_pool", "per_title_floor", "pooled_loss_carry"]:
        data = read_json(FOLDER / "neutral.json")
        data["policy"]["method"] = data["opening_state"]["method"] = method
        package = returns_package(data, reference=reference)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / (method.replace("_", "-") + "-canonical-package.json"), package)
