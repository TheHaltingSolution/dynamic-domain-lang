"""Author pinned generic registrations for the existing synthetic mechanisms.

This copies typed fixture inputs and opening snapshots and derives checked port
shapes only. All financial calculations remain in the unchanged SPL sources;
independent expected amounts belong to Tests/test_module_mechanisms.py.
Running this script deliberately authors new unissued registration artifacts.
Execution never silently repins a previously authored run.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from spl_compiler.checker import check_schedule, type_from_ast
from spl_compiler.codecs import canonical, file_digest, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent

# These are interface/policy registrations, not execution profiles or economic
# callbacks. The generic runner accepts each descriptor without contract dispatch.
REGISTRATIONS = {
    "advance-issues": {
        "purpose": "participation_prepayment", "authority": "authority",
        "decision_ids": ["RR-01-FUNDED-AS-OF-POOLED", "synthetic-prospective"],
        "parameters": ["observation_cutoff", "authority", "balance_purpose", "currency"],
        "results": ["advances"], "state": [("prepayment", "USD")],
        "domains": {"authority": {"choices": ["synthetic-prospective"]},
                    "balance_purpose": {"choices": ["participation_prepayment"], "methodology": True},
                    "currency": {"choices": ["USD"]}},
        "keys": {"issues": ["event_id", "issue_id", "disbursement_id"], "evidence": ["evidence_id"]},
        "cases": ["advance-5000-carry", "advance-following-quarter", "funded-date-boundary", "observation-cutoff", "wrong-scope-purpose-evidence"],
    },
    "reserve-vintage": {
        "purpose": "return_reserve", "authority": "authority",
        "decision_ids": ["SYNTHETIC-RES-VINTAGE", "synthetic-vintage"],
        "parameters": ["observation_cutoff", "authority", "purpose"],
        "results": ["reserve_ledger"], "state": [("reserve_vintages", "structured")],
        "domains": {"authority": {"choices": ["synthetic-vintage"]},
                    "purpose": {"choices": ["return_reserve"], "methodology": True}},
        "keys": {"movements": ["event_id", "evidence_ref"], "evidence": ["evidence_id"]},
        "cases": ["vintage-1-zero-vintage-2-20", "serialized-liquidation", "wrong-scope-purpose-evidence", "after-cutoff"],
    },
    "correction-payments": {
        "purpose": "obligation_reconciliation", "authority": "required_authority",
        "decision_ids": ["SYNTHETIC-CORR-RESTATEMENT", "synthetic-restatement"],
        "parameters": ["payment_cutoff", "required_authority"],
        "results": ["obligation_reconciliation"], "state": [],
        "domains": {"required_authority": {"choices": ["synthetic-restatement"]}},
        "keys": {"payments": ["event_id"]},
        "cases": ["supplied-revision-outstanding-10", "wrong-scope-authority", "paid-date-cutoff", "overpayment-blocked"],
    },
}


def _pin(path):
    return {"locator": path.relative_to(ROOT).as_posix(), "sha256": file_digest(path)}


def _type(typ):
    # Expand built-in records into structural types without mutating the checker
    # schema registry; both native and reference source declarations are checked.
    result = {"name": typ.name, "args": [_type(item) for item in typ.args]}
    if typ.fields and typ.name != "Period":
        result = {"name": "Record", "args": [], "fields": [[name, _type(field)] for name, field in typ.fields]}
    return result


def _constraint(kind, path, fields=(), target="", value=""):
    return {"kind": kind, "path": path, "fields": list(fields), "target": target, "value": value}


def build_descriptor(name):
    registration = REGISTRATIONS[name]
    source = FOLDER / (name + ".spl")
    syntax = parse(source.read_text(encoding="utf-8"), source.name)
    check_schedule(syntax)
    ports = []
    for declaration in syntax["declarations"]:
        kind = declaration["kind"]
        port_name = declaration.get("name")
        if kind in {"input", "opening"}:
            role = "opening" if kind == "opening" else "parameter" if port_name in registration["parameters"] else "input"
            typ = type_from_ast(declaration["type"])
        elif kind == "emit":
            role = "result" if port_name in registration["results"] else "detail"
            typ = declaration["expr"]["_type"]
        else:
            continue
        ports.append({"name": port_name, "role": role, "type": _type(typ),
            "dimensions": ["agreement", "participant", "pool", "purpose", "period", "currency"]
                if typ.fields or typ.name == "List" or role == "opening" else [],
            "domain": deepcopy(registration["domains"].get(port_name, {}))})
    constraints = [
        _constraint("equals", "inputs.scope", ["agreement_id"], "scope.agreement_id"),
        _constraint("equals", "inputs.scope", ["pool_id"], "scope.pool_id"),
        _constraint("member_of", "inputs.scope", ["participant_id"], "scope.participant_ids"),
        _constraint("equals", "inputs.scope", ["period"], "manifest.period"),
        _constraint("equals", "scope.purpose", value=registration["purpose"]),
        _constraint("member_of", "parameters." + registration["authority"], target="decisions.*.decision_id"),
    ]
    if "observation_cutoff" in registration["parameters"]:
        constraints.append(_constraint("equals", "parameters.observation_cutoff", target="manifest.cutoff"))
    for collection, keys in registration["keys"].items():
        constraints.extend(_constraint("unique", "inputs." + collection, [key]) for key in keys)
    return {"schema_version": "spl-module-descriptor/1", "id": "synthetic:" + name, "revision": "1",
        "compatibility": {"surface": "spl/0.1-draft", "core": "spl-core/0.1-draft", "ir": "spl-ir/0.1",
            "package": "spl-module/1", "toolchain": "leanprover/lean4:v4.35.0", "codecs": ["spl-exact/1", "spl-instant/1"],
            "capabilities": ["spl.core/1", "spl.instant/1", "spl.modules/1"]},
        "source": _pin(source), "imports": [],
        "interface": {"ports": ports, "schemas": [], "dictionaries": {}, "exports": []},
        "policy": {"id": "synthetic:" + name + "-policy", "revision": "1", "readable": _pin(FOLDER / (name + "-policy.md")),
            "decision_ids": registration["decision_ids"], "evidence_class": "synthetic", "review_status": "proposed",
            "discriminating_cases": registration["cases"]},
        "constraints": constraints,
        "state": [{"opening": opening, "closing": opening, "purpose": registration["purpose"], "unit": unit,
            "key_fields": ["agreement_id", "participant_id", "pool_id", "purpose"],
            "movement_kinds": ["net_change" if unit == "USD" else "transition"], "history_required": False}
            for opening, unit in registration["state"]]}


def register(name):
    descriptor = build_descriptor(name)
    path = FOLDER / (name + "-module.json")
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": descriptor["revision"], **_pin(path)}


def build_package(name, *, reference=None, bindings=None):
    registration = REGISTRATIONS[name]
    values = deepcopy(bindings if bindings is not None else read_json(FOLDER / (name + "-bindings.json")))
    reference = reference or register(name)
    resolved = resolve_module(reference, ROOT)
    scope = values["inputs"]["scope"]
    parameters = {key: values["inputs"].pop(key) for key in registration["parameters"]}
    # PaymentApplication has a paid Date and no observation timestamp. This is
    # the selected Date boundary, not fabricated observation evidence.
    cutoff = parameters.get("observation_cutoff", parameters.get("payment_cutoff", "") + "T00:00:00Z")
    cells = []
    scenario = name + "-synthetic"
    for opening, unit in registration["state"]:
        cell_scope = {key: scope[key] for key in ["agreement_id", "participant_id", "pool_id"]}
        quantity = values["openings"][opening]
        cells.append({"state_key": canonical({**cell_scope, "purpose": registration["purpose"]}),
            "opening_port": opening, "purpose": registration["purpose"], "unit": unit, "scope": cell_scope,
            "boundary": scope["period"]["start"], "quantity": quantity["value"] if unit == "USD" else quantity,
            "provenance_ref": "synthetic-original-" + opening + "-snapshot", "scenario_id": scenario})
    decisions = []
    for entry in resolved.closure:
        policy = entry["descriptor"]["policy"]
        decisions.extend({"decision_id": identity, "policy_id": policy["id"], "policy_revision": policy["revision"],
            "status": policy["review_status"], "evidence_ref": "existing-synthetic-fixture-and-selected-policy"}
            for identity in policy["decision_ids"])
    assets = sorted({row["source_title_id"] for row in values["inputs"].get("issues", [])})
    return bind_module_package({"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": name + "-canonical", "scenario_id": scenario, "mode": "final", "period": deepcopy(scope["period"]),
            "cutoff": cutoff, "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["agreement_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"],
            "purpose": registration["purpose"], "asset_ids": assets},
        "inputs": values["inputs"], "parameters": parameters, "evidence": {}, "state_cells": cells, "decisions": decisions}, ROOT)


if __name__ == "__main__":
    for name in REGISTRATIONS:
        write_json(FOLDER / (name + "-module-package.json"), build_package(name))
