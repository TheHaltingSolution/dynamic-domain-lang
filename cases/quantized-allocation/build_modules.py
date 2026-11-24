"""Closed mechanical original-fact transport; all allocation decisions run in SPL.

Source numeric/Instant lexemes travel alongside typed values and are restored
from actual state. No oracle imports, quota, rank, floor or residual calculation.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, exact, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-QUANTIZED-ALLOCATION-01"
SCOPE = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}
POLICY_FIELDS = {"id", "revision", "method", "parent_rounding", "quota_basis", "residual_order", "evidence_class", "limits"}
COMMON = {"id", "scope", "observed_at", "source_ref", "evidence_ref"}
PARENT = COMMON | {"amount", "effective_date", "upstream_ref", "authority_id"}
TERM = COMMON | {"recipient_id", "weight"}
AUTHORITY = COMMON | {"parent_id", "parent_upstream_ref", "method", "effective", "approved", "approved_date", "recorded_date", "recipient_ids", "terms", "supplied_allocation_ids", "residual_order"}
SUPPLIED = COMMON | {"parent_id", "recipient_id", "amount"}
RECORD = {"source_case_id", "period", "as_of", "cutoff", "parents", "authorities", "supplied_allocations"}
STATE = {"scope", "purpose", "policy", "recipient_registry", "boundary", "origin", "source_case_id", "consumed_parent_ids", "consumed_upstream_refs", "history"}


def _fields(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() <= set(required) | set(optional):
        raise ValueError("QA_RECORD_FIELDS")


def _id(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}", value):
        raise ValueError("QA_ASCII_ID")
    return value


def _text(value):
    if type(value) is not str or not value:
        raise ValueError("QA_SOURCE_REQUIRED")
    return value


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("QA_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _scope(value):
    _fields(value, SCOPE)
    for entry in value.values():
        _id(entry)
    if value["currency"] != "USD":
        raise ValueError("QA_CURRENCY")


def _policy(value):
    _fields(value, POLICY_FIELDS)
    _fields(value["limits"], {"recipients", "parents_per_period", "historical_periods"})
    if any(type(v) is not int for v in value["limits"].values()):
        raise ValueError("QA_POLICY_LIMIT_TYPE")
    return {**deepcopy(value), "limits": {key: str(v) for key, v in value["limits"].items()}}


def _row(row, fields):
    _fields(row, fields)
    _scope(row["scope"])
    for field in ("id", "recipient_id", "parent_id", "authority_id", "evidence_ref"):
        if field in row:
            _id(row[field])
    _text(row["source_ref"])
    result = deepcopy(row)
    result["observed_at_source"] = row["observed_at"]
    if "amount" in fields:
        result["amount"] = money(_q(row["amount"]))
        result["amount_source"] = row["amount"]
    if "weight" in fields:
        result["weight"] = number(_q(row["weight"]))
        result["weight_source"] = row["weight"]
    if "upstream_ref" in fields:
        prefix, separator, line = _text(row["upstream_ref"]).rpartition("#")
        if not prefix or not separator or not line:
            raise ValueError("QA_ORIGINAL_PARENT_LINE")
    if "terms" in fields:
        if type(row["approved"]) is not bool:
            raise ValueError("QA_APPROVAL_TYPE")
        result["terms"] = [_row(term, TERM) for term in row["terms"]]
        for key in ("recipient_ids", "supplied_allocation_ids"):
            if type(row[key]) is not list:
                raise ValueError("QA_ID_LIST")
            for value in row[key]:
                _id(value)
    return result


def _record(value):
    _fields(value, RECORD)
    _id(value["source_case_id"])
    return {**deepcopy(value), "cutoff_source": value["cutoff"], "parents": [_row(row, PARENT) for row in value["parents"]],
            "authorities": [_row(row, AUTHORITY) for row in value["authorities"]],
            "supplied_allocations": [_row(row, SUPPLIED) for row in value["supplied_allocations"]]}


def _state(value):
    _fields(value, STATE)
    _scope(value["scope"])
    _id(value["source_case_id"])
    for identity in value["consumed_parent_ids"]:
        _id(identity)
    return {**deepcopy(value), "policy": _policy(value["policy"]),
            "recipient_registry": [_row(row, COMMON) for row in value["recipient_registry"]],
            "history": [_record(row) for row in value["history"]]}


def neutral_state(value):
    """Restore exact original lexemes from actual serialized structured state."""
    if isinstance(value, list):
        return [neutral_state(item) for item in value]
    if isinstance(value, dict):
        if set(value) == {"value", "currency"}:
            if value["currency"] != "USD":
                raise ValueError("QA_CURRENCY")
            return str(exact(value["value"]))
        if set(value) == {"numerator", "denominator"}:
            return str(exact(value))
        result = {key: neutral_state(item) for key, item in value.items() if key not in {"amount_source", "weight_source", "observed_at_source", "cutoff_source"}}
        for field in ("amount", "weight", "observed_at", "cutoff"):
            if field + "_source" in value:
                result[field] = value[field + "_source"]
        if set(result) == {"recipients", "parents_per_period", "historical_periods"}:
            result = {key: int(v) for key, v in result.items()}
        return result
    return value


def _register(name, **kwargs):
    reference = _descriptor(name, name + ".spl", "policy.md", kwargs.pop("roles", {}), folder=FOLDER, **kwargs)
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:quantized-" + ("parent-library" if name == "allocation" else "allocation")
    descriptor["policy"].update(id=POLICY, evidence_class="synthetic", review_status="proposed",
                                discriminating_cases=["parent-first-half-even", "hamilton-ascii-tie", "supplied-amount-alternative", "original-parent-carry"])
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def _export_type(value):
    # Preserve named built-in record schemas in the actual function result;
    # expanding nested Period into Record changes the source signature.
    result = {"name": value.name, "args": [_export_type(item) for item in value.args]}
    if value.name == "Record":
        result["fields"] = [[name, _export_type(typ)] for name, typ in value.fields]
    return result


def register_quantized_allocation():
    syntax = parse((FOLDER / "allocation.spl").read_text(encoding="utf-8"))
    check_schedule(syntax)
    parameters = [{"name": d["name"], "type": d["type"]} for d in syntax["declarations"] if d["kind"] == "input"]
    result = _export_type(next(d for d in syntax["declarations"] if d.get("name") == "calculated_record")["expr"]["_type"])
    library = _register("allocation", exports=[{"name": "calculate", "definition": "calculated_record", "parameters": parameters, "result": result}])
    return _register("quantized-allocation", roles={"cutoff": "parameter", "cutoff_source": "parameter", "as_of": "parameter", "policy": "parameter", "evidence": "evidence", "comparison": "result", "allocations": "detail", "reconciliation": "reconciliation"},
                     imports=[{"module_ref": library, "alias": "allocation", "symbols": [{"export": "calculate", "local": "allocate_parent_record"}]}],
                     state=[{"opening": "ledger", "closing": "ledger", "purpose": "quantized_parent_allocation", "unit": "structured",
                             "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"],
                             "movement_kinds": ["transition"], "history_required": False}])


def quantized_allocation_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _fields(data, {"schema_version", "case_id", "scope", "period", "as_of", "cutoff", "policy", "recipient_registry", "parents", "authorities", "supplied_allocations", "evidence", "opening_state"}, {"prior_result"})
    if data["schema_version"] != "quantized-allocation-neutral/1":
        raise ValueError("QA_SCHEMA")
    _id(data["case_id"])
    scope = data["scope"]
    _scope(scope)
    reference = reference or register_quantized_allocation()
    decisions = [{"decision_id": decision, "policy_id": row["descriptor"]["policy"]["id"], "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-synthetic-quantized-allocation"}
                 for row in resolve_module(reference, ROOT).closure for decision in row["descriptor"]["policy"]["decision_ids"]]
    current = _record({"source_case_id": data["case_id"], **{key: data[key] for key in RECORD - {"source_case_id"}}})
    inputs = {"scope": {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "period": data["period"]},
              "project": scope["asset_id"], "fact_scope": scope, "case_id": data["case_id"], "supplied_opening": _state(data["opening_state"]),
              "recipients": [_row(row, COMMON) for row in data["recipient_registry"]],
              **{key: current[key] for key in ("parents", "authorities", "supplied_allocations")}}
    evidence = []
    for row in data["evidence"]:
        _fields(row, {"id", "scope", "kind", "observed_at"})
        _id(row["id"]); _scope(row["scope"]); _text(row["kind"])
        evidence.append({"id": row["id"], "scope": row["scope"], "source_kind": row["kind"], "observed_at": row["observed_at"], "observed_at_source": row["observed_at"],
                         "approval_ref": "QUANTIZED_ALLOCATION_SELECTED", "evidence_ref": row["id"], "kind": "selected_synthetic_record"})
    cell_scope = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    cell = {"opening_port": "ledger", "state_key": canonical({**cell_scope, "purpose": "quantized_parent_allocation"}), "purpose": "quantized_parent_allocation", "unit": "structured",
            "scope": cell_scope, "boundary": data["period"]["start"], "quantity": _state(data["opening_state"]),
            "provenance_ref": "supplied-original-parent-opening", "scenario_id": "SYNTHETIC-QUANTIZED-ALLOCATION"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if not isinstance(prior.get("result_ref"), str) or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("QA_CANONICAL_PREDECESSOR_REQUIRED")
        cell["prior_result_ref"] = prior["result_ref"]
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
    else:
        inputs["predecessor"] = {"none": True}
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(c.get("prior_result_ref") != cell["prior_result_ref"] for c in cells):
        raise ValueError("QA_CANONICAL_PREDECESSOR_MISMATCH")
    package = {"profile": "spl-module/1", "module_ref": reference,
               "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-QUANTIZED-ALLOCATION", "mode": "final", "period": data["period"], "cutoff": data["cutoff"],
                            "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
               "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": "selected-synthetic-quantized-allocation"},
               "inputs": inputs, "parameters": {"cutoff": data["cutoff"], "cutoff_source": data["cutoff"], "as_of": data["as_of"], "policy": _policy(data["policy"])}, "evidence": {"evidence": evidence}, "decisions": decisions, "state_cells": cells}
    return bind_module_package(package, ROOT)


def run_quantized_allocation_package(package, registry_root=None, *, backend="compare", artifact_dir=None):
    return run_module_package(package, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir)


if __name__ == "__main__":
    package = quantized_allocation_package(reference=register_quantized_allocation())
    package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
    write_json(FOLDER / "canonical-package.json", package)
