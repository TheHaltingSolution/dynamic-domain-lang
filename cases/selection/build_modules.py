"""Register named rule methods and transport original facts without selecting."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import money, number, read_json, write_json
from spl_compiler.modules import bind_module_package


ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
METHODS = ("unique_no_fallback", "unique_explicit_fallback", "priority_explicit_fallback")
POLICY_ID = "SYNTHETIC-SELECTION-01"
DECISION = "SELECTION_SELECTED"


def _record(row, fields):
    if type(row) is not dict or set(row) != set(fields):
        raise ValueError("SELECTION_NEUTRAL_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("SELECTION_EXACT_NONNEGATIVE_TRANSPORT")
    return Fraction(value)


def module_reference(method):
    if method not in METHODS:
        raise ValueError("SELECTION_METHOD")
    path = FOLDER / ("selection-" + method + "-module.json")
    descriptor = read_json(path)
    return {"id": descriptor["id"], "revision": descriptor["revision"], **_pin(path)}


def register_selection(method):
    if method not in METHODS:
        raise ValueError("SELECTION_METHOD")
    identity = "synthetic:selection-" + method
    reference = _descriptor("selection-" + method, "selection.spl", "policy.md",
        {"method": "parameter", "module_id": "parameter", "cutoff": "parameter", "fallback": "parameter",
         "evidence": "evidence", "statement": "result", "selection_detail": "detail", "source_audit": "detail", "reconciliation": "reconciliation"},
        folder=FOLDER, capabilities=["spl.priority/1"], domains={
            "method": {"choices": [method], "methodology": True}, "module_id": {"choices": [identity], "methodology": True}})
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = identity
    descriptor["policy"].update(id=POLICY_ID, decision_ids=[DECISION], discriminating_cases=[
        "cash100-rate20", "selected-zero", "absent-rule", "duplicate-unique", "tied-priority", "lazy-unselected-body", "demanded-predicate", "demanded-body"])
    descriptor["constraints"].extend([
        {"kind": "equals", "path": "inputs.receipt.agreement_id", "fields": [], "target": "scope.agreement_id", "value": ""},
        {"kind": "member_of", "path": "inputs.receipt.asset_id", "fields": [], "target": "scope.asset_ids", "value": ""}])
    write_json(path, descriptor)
    return module_reference(method)


def selection_package(fixture=None, *, reference=None, bind=True):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _record(data, {"schema_version", "case_id", "scope", "period", "cutoff", "policy", "receipt", "rules", "fallback", "evidence"})
    if data["schema_version"] != "selection-neutral/1":
        raise ValueError("SELECTION_NEUTRAL_SCHEMA")
    _record(data["policy"], {"id", "revision", "method", "rounding", "evidence_class"})
    method = data["policy"]["method"]
    if method not in METHODS or {key: value for key, value in data["policy"].items() if key != "method"} != {
            "id": POLICY_ID, "revision": "1", "rounding": "exact_no_rounding", "evidence_class": "research_assumption"}:
        raise ValueError("SELECTION_SELECTED_POLICY")
    _record(data["scope"], {"agreement_id", "participant_id", "pool_id", "asset_id", "currency"})
    scope = data["scope"]
    if scope["currency"] != "USD":
        raise ValueError("SELECTION_CURRENCY")
    _record(data["receipt"], {"id", "agreement_id", "asset_id", "channel", "amount", "effective_date", "observed_at", "source_ref", "evidence_ref"})
    receipt = data["receipt"]
    receipt["amount"] = money(_q(receipt["amount"]))
    _record(data["rules"], {"primary", "competing", "unsafe"})
    rules = {}
    for slot, original in data["rules"].items():
        _record(original, {"id", "agreement_id", "asset_id", "channel", "effective", "enabled", "observed_at", "source_ref", "evidence_ref", "rate", "predicate_divisor", "body_divisor"})
        row = deepcopy(original)
        for field in ("rate", "predicate_divisor", "body_divisor"):
            row[field] = number(_q(row[field]))
        rules[slot] = row
    _record(data["fallback"], {"rate", "body_divisor", "source_ref", "evidence_ref"})
    fallback = deepcopy(data["fallback"])
    for field in ("rate", "body_divisor"):
        fallback[field] = number(_q(fallback[field]))
    evidence = []
    for original in data["evidence"]:
        _record(original, {"id", "agreement_id", "asset_id", "authority_rule_id", "approved", "observed_at", "source_ref", "kind"})
        evidence.append({**original, "source_kind": original["kind"], "kind": "selected_synthetic_record", "approval_ref": DECISION, "evidence_ref": original["id"]})
    reference = reference or module_reference(method)
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-SCOPED-SELECTION", "mode": "final",
            "period": data["period"], "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["agreement_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"],
                  "asset_ids": [scope["asset_id"]], "purpose": "synthetic-scoped-rule-entitlement"},
        "inputs": {"scope": {"agreement_id": scope["agreement_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "period": data["period"]},
                   "project": scope["asset_id"], "receipt": receipt, **rules},
        "parameters": {"method": method, "module_id": "synthetic:selection-" + method, "cutoff": data["cutoff"], "fallback": fallback},
        "evidence": {"evidence": evidence}, "state_cells": [],
        "decisions": [{"decision_id": DECISION, "policy_id": POLICY_ID, "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-synthetic-original-rules"}]}
    return bind_module_package(package, ROOT) if bind else package


if __name__ == "__main__":
    fixture = read_json(FOLDER / "neutral.json")
    for method in METHODS:
        reference = register_selection(method)
        fixture["policy"]["method"] = method
        write_json(FOLDER / (method + "-package.unbound.json"), selection_package(fixture, reference=reference, bind=False))
