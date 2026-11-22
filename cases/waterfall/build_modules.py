"""Explicit registration and mechanical neutral-record transport for C03/C07.

Only SPL computes fees, recovery and allocations. No contract-name dispatch is
added to the canonical adapter, compiler, runtime or schemas.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, file_digest, money, number, read_json, write_json
from spl_compiler.linker import link_schedule
from spl_compiler.modules import bind_module_package, resolve_module
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
PURPOSE = "capital_recovery"


def _q(value):
    if type(value) not in {str, int} or (isinstance(value, str) and not re.fullmatch(r"-?\d+(?:\.\d+|/[1-9]\d*)?", value)):
        raise ValueError("WF_EXACT_TRANSPORT_REQUIRED")
    return Fraction(value)


def _pin(path):
    return {"locator": path.relative_to(ROOT).as_posix(), "sha256": file_digest(path)}


def _type(value):
    result = {"name": value.name, "args": [_type(item) for item in value.args]}
    if value.fields:
        result = {"name": "Record", "args": [], "fields": [[name, _type(typ)] for name, typ in value.fields]}
    return result


def _constraint(kind, path, target="", fields=(), value=""):
    return {"kind": kind, "path": path, "fields": list(fields), "target": target, "value": value}


def _descriptor(name, *, imports=(), exports=(), roles=None, constraints=(), state=(), domains=None):
    source = FOLDER / (name + ".spl")
    syntax = parse(source.read_text(encoding="utf-8"), source.name)
    if imports:
        resolved = resolve_module(imports[0]["module_ref"], ROOT)
        manifest = {"modules": [{"reference": entry["reference"], "source": entry["source_path"].read_text(encoding="utf-8"),
                                 "descriptor": entry["descriptor"]} for entry in resolved.closure], "imports": list(imports)}
        syntax = link_schedule(syntax, manifest)
    check_schedule(syntax)
    roles, domains = roles or {}, domains or {}
    descriptor = {"schema_version": "spl-module-descriptor/1", "id": "waterfall:" + name, "revision": "1",
        "compatibility": {"surface": "spl/0.1-draft", "core": "spl-core/0.1-draft", "ir": "spl-ir/0.1",
            "package": "spl-module/1", "toolchain": "leanprover/lean4:v4.35.0", "codecs": ["spl-exact/1", "spl-instant/1"],
            "capabilities": ["spl.core/1", "spl.instant/1", "spl.tuple-map/1", "spl.fold/1", "spl.modules/1"]},
        "source": _pin(source), "imports": list(imports),
        "interface": {"ports": [], "schemas": [], "dictionaries": {}, "exports": list(exports)},
        "policy": {"id": "spl:policy:waterfall:" + name, "revision": "1", "readable": _pin(FOLDER / "policy.md"),
            "decision_ids": ["WF_" + name.upper() + "_SELECTED"], "evidence_class": "synthetic", "review_status": "proposed",
            "discriminating_cases": ["funds120-priority-vs-pro-rata", "roundlake-like-period1-period2"]},
        "constraints": list(constraints), "state": list(state)}
    for declaration in syntax["declarations"]:
        kind = declaration["kind"]
        if kind in {"input", "opening", "emit"}:
            port_name = declaration["name"]
            role = "opening" if kind == "opening" else roles.get(port_name, "detail" if kind == "emit" else "input")
            typ = _type(declaration["expr"]["_type"]) if kind == "emit" else declaration["type"]
            descriptor["interface"]["ports"].append({"name": port_name, "role": role, "type": typ,
                "dimensions": [], "domain": deepcopy(domains.get(port_name, {}))})
    path = FOLDER / (name + "-module.json")
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def register_waterfall():
    ratio = {"name": "Ratio", "args": []}
    usd = {"name": "Money", "args": [{"name": "USD", "args": []}]}
    library = _descriptor("proportional", exports=[{"name": "proportional", "parameters": [
        {"name": "amount", "type": usd}, {"name": "weight", "type": ratio}, {"name": "total_weight", "type": ratio}],
        "result": usd, "definition": "allocated"}])
    constraints = [
        _constraint("equals", "inputs.scope.agreement_id", "scope.agreement_id"),
        _constraint("equals", "inputs.scope.pool_id", "scope.pool_id"),
        _constraint("equals", "inputs.scope.participant_id", "inputs.participant_group"),
        _constraint("member_of", "inputs.participant_group", "scope.participant_ids"),
        _constraint("equals", "inputs.scope.period", "manifest.period"),
        _constraint("equals", "parameters.cutoff", "manifest.cutoff"),
        _constraint("equals", "inputs.purpose", "scope.purpose"),
        _constraint("equals", "inputs.purpose", value=PURPOSE),
        _constraint("member_of", "inputs.project", "scope.asset_ids"),
        _constraint("member_of", "inputs.beneficiaries", "scope.participant_ids", ["participant_id"]),
        _constraint("equals", "state_cells", "inputs.participant_group", ["scope.participant_id"]),
        _constraint("equals", "state_cells", "inputs.project", ["scope.asset_id"]),
        _constraint("evidence", "evidence.evidence", value="selected_synthetic_record")]
    return _descriptor("waterfall", imports=[{"module_ref": library, "alias": "allocation", "symbols": [{"export": "proportional", "local": "proportional"}]}],
        roles={"cutoff": "parameter", "recovery_method": "parameter", "fee_rate": "parameter", "evidence": "evidence",
               "control": "reconciliation", "settlements": "result"}, constraints=constraints,
        domains={"fee_rate": {"minimum": "0", "maximum": "1"},
                 "recovery_method": {"choices": ["priority", "pro_rata"], "methodology": True}},
        state=[{"opening": "claim_ledger", "closing": "claim_ledger", "purpose": PURPOSE, "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"],
                "movement_kinds": ["transition"], "history_required": False}])


def waterfall_package(fixture=None, *, reference=None):
    """Transport exact source facts; preserve supplied scope and identities."""
    fixture = deepcopy(fixture or read_json(FOLDER / "roundlake-like-p1.json"))
    if fixture["policy"]["fee_base"] != "gross_before_costs" or fixture["policy"]["rounding"] != "exact_no_rounding" or fixture["policy"]["ties"] != "reject":
        raise ValueError("WF_UNSUPPORTED_SELECTED_POLICY")
    reference = reference or register_waterfall()
    scope = fixture["scope"]
    participants = [scope["participant_group"], *[row["participant_id"] for row in fixture["beneficiaries"]]]
    inputs = {"scope": {"agreement_id": scope["agreement_id"], "participant_id": scope["participant_group"],
                        "pool_id": scope["pool_id"], "period": deepcopy(fixture["period"])},
              "participant_group": scope["participant_group"], "project": scope["asset_id"], "purpose": scope["purpose"],
              "currency": scope["currency"], "beneficiaries": deepcopy(fixture["beneficiaries"])}
    for row in inputs["beneficiaries"]:
        row["residual_weight"] = number(_q(row["residual_weight"]))
    for collection in ["cash_records", "costs"]:
        inputs[collection] = deepcopy(fixture[collection])
        for row in inputs[collection]:
            row["amount"] = money(_q(row["amount"]))
    ledger = deepcopy(fixture["opening_claims"])
    for row in ledger:
        for name in ["principal", "balance"]:
            row[name] = money(_q(row[name]))
        for name in ["priority", "sequence"]:
            row[name] = number(_q(row[name]))
    state_scope = {"agreement_id": scope["agreement_id"], "participant_id": scope["participant_group"],
                   "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    resolved = resolve_module(reference, ROOT)
    decisions = []
    for entry in resolved.closure:
        policy = entry["descriptor"]["policy"]
        decisions.extend({"decision_id": identity, "policy_id": policy["id"], "policy_revision": "1", "status": "proposed",
                          "evidence_ref": "project-selected-synthetic-policy"} for identity in policy["decision_ids"])
    evidence = [{"evidence_id": row["id"], "observed_at": row["observed_at"], "approval_ref": "WF_WATERFALL_SELECTED",
                 "evidence_ref": row["id"], "kind": "selected_synthetic_record"} for row in fixture["evidence"]]
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": fixture["case_id"] + "-" + fixture["period"]["start"], "scenario_id": fixture["case_id"], "mode": "final",
            "period": deepcopy(fixture["period"]), "cutoff": fixture["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["agreement_id"], "participant_ids": list(dict.fromkeys(participants)),
                  "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": scope["purpose"]},
        "inputs": inputs, "parameters": {"cutoff": fixture["cutoff"], "fee_rate": number(_q(fixture["policy"]["fee_rate"])),
                                          "recovery_method": fixture["policy"]["recovery_method"]},
        "evidence": {"evidence": evidence}, "decisions": decisions,
        "state_cells": [{"state_key": canonical({**state_scope, "purpose": PURPOSE}), "opening_port": "claim_ledger",
            "purpose": PURPOSE, "unit": "structured", "scope": state_scope, "boundary": fixture["period"]["start"], "quantity": ledger,
            "provenance_ref": "selected-synthetic-opening-claims", "scenario_id": fixture["case_id"]}]}
    return bind_module_package(package, ROOT)


if __name__ == "__main__":
    print(register_waterfall())
