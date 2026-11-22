"""Mechanical neutral-record transport and explicit R1 module registration.

No entitlement, fee, denominator or correction is calculated here. Financial
rules execute in SPL; independently authored controls live in oracles/r1.py.
Descriptors are generated deliberately for the evolving R1 draft, never repinned
inside execution of an already issued package.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
from pathlib import Path
import re

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, file_digest, money, number, read_json, write_json
from spl_compiler.linker import link_schedule
from spl_compiler.modules import bind_module_package, linking_manifest, resolve_module
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent


def _q(value):
    if type(value) not in {str, int} or (isinstance(value, str) and not re.fullmatch(r"-?\d+(?:\.\d+|/[1-9]\d*)?", value)):
        raise ValueError("R1_EXACT_TRANSPORT_REQUIRED")
    return Fraction(value)


def _pin(path):
    return {"locator": path.resolve().relative_to(ROOT).as_posix(), "sha256": file_digest(path)}


def _type(value):
    result = {"name": value.name, "args": [_type(item) for item in value.args]}
    if value.fields:
        result = {"name": "Record", "args": [], "fields": [[name, _type(typ)] for name, typ in value.fields]}
    return result


def _descriptor(name, source_name, policy_name, roles, *, imports=(), exports=(), state=(), domains=None, folder=None, capabilities=()):
    destination = Path(folder or FOLDER)
    source = destination / source_name
    descriptor = {"schema_version": "spl-module-descriptor/1", "id": "r1:" + name, "revision": "1",
        "compatibility": {"surface": "spl/0.1-draft", "core": "spl-core/0.1-draft", "ir": "spl-ir/0.1",
                          "package": "spl-module/1", "toolchain": "leanprover/lean4:v4.35.0",
                          "codecs": ["spl-exact/1", "spl-instant/1"],
                          "capabilities": ["spl.core/1", "spl.instant/1", "spl.tuple-map/1", "spl.group-join/1", "spl.fold/1", "spl.modules/1", *capabilities]},
        "source": _pin(source), "imports": list(imports),
        "interface": {"ports": [], "schemas": [], "dictionaries": {}, "exports": list(exports)},
        "policy": {"id": "spl:policy:r1:" + name, "revision": "1", "readable": _pin(destination / policy_name),
                   "decision_ids": [name.upper().replace("-", "_") + "_SELECTED"], "evidence_class": "synthetic",
                   "review_status": "proposed", "discriminating_cases": [name + "-rr03-selected"]},
        "constraints": [], "state": list(state)}
    syntax = parse(source.read_text(encoding="utf-8"), source.name)
    if imports:
        # Resolve only dependencies while constructing the new, unissued root.
        dependency_entries = []
        seen = set()
        for item in imports:
            for entry in resolve_module(item["module_ref"], ROOT).closure:
                identity = (entry["reference"]["id"], entry["reference"]["revision"])
                if identity not in seen:
                    dependency_entries.append({"reference": entry["reference"], "source": entry["source_path"].read_text(encoding="utf-8"), "descriptor": entry["descriptor"]})
                    seen.add(identity)
        syntax = link_schedule(syntax, {"modules": dependency_entries, "imports": list(imports)})
    checked = check_schedule(syntax)
    for declaration in syntax["declarations"]:
        kind = declaration["kind"]
        if kind in {"input", "opening"}:
            port_name = declaration["name"]
            role = "opening" if kind == "opening" else roles.get(port_name, "input")
            descriptor["interface"]["ports"].append({"name": port_name, "role": role,
                "type": declaration["type"], "dimensions": [], "domain": deepcopy((domains or {}).get(port_name, {}))})
        elif kind == "emit":
            # This derives only the declared checked output shape, not values.
            port_name = declaration["name"]
            descriptor["interface"]["ports"].append({"name": port_name, "role": roles.get(port_name, "detail"),
                "type": _type(declaration["expr"]["_type"]), "dimensions": [], "domain": {}})
    for port in descriptor["interface"]["ports"]:
        if port["role"] == "evidence":
            descriptor["constraints"].append({"kind": "evidence", "path": "evidence." + port["name"],
                "fields": [], "target": "", "value": "selected_synthetic_record"})
    input_names = {port["name"] for port in descriptor["interface"]["ports"] if port["role"] == "input"}
    if "scope" in input_names:
        descriptor["constraints"].extend([
            {"kind": "equals", "path": "inputs.scope.agreement_id", "fields": [], "target": "scope.agreement_id", "value": ""},
            {"kind": "equals", "path": "inputs.scope.pool_id", "fields": [], "target": "scope.pool_id", "value": ""},
            {"kind": "member_of", "path": "inputs.scope.participant_id", "fields": [], "target": "scope.participant_ids", "value": ""},
            {"kind": "equals", "path": "inputs.scope.period", "fields": [], "target": "manifest.period", "value": ""},
            {"kind": "equals", "path": "parameters.cutoff", "fields": [], "target": "manifest.cutoff", "value": ""}])
    if "beneficiaries" in input_names:
        descriptor["constraints"].extend([
            {"kind": "member_of", "path": "inputs.beneficiaries", "fields": ["participant_id"], "target": "scope.participant_ids", "value": ""},
            {"kind": "member_of", "path": "inputs.beneficiaries", "fields": ["asset_id"], "target": "scope.asset_ids", "value": ""}])
    if "project" in input_names:
        descriptor["constraints"].append({"kind": "member_of", "path": "inputs.project", "fields": [], "target": "scope.asset_ids", "value": ""})
        descriptor["constraints"].append({"kind": "equals", "path": "state_cells", "fields": ["scope.asset_id"], "target": "inputs.project", "value": ""})
    path = destination / (name + "-module.json")
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": descriptor["revision"], **_pin(path)}


def _evidence(fixture, decision):
    return [{"evidence_id": row["id"], "observed_at": row["observed_date"] + "T00:00:00Z",
             "approval_ref": decision, "evidence_ref": row["id"], "kind": "selected_synthetic_record"}
            for row in fixture["evidence"]]


def _scope(fixture, participant):
    return {"agreement_id": fixture["scope"]["contract_id"], "participant_id": participant,
            "pool_id": fixture["scope"]["pool_id"], "period": deepcopy(fixture["period"])}


def _package(fixture, reference, inputs, parameters, evidence, participants, assets, state_cells=()):
    if fixture["scope"]["currency"] != "USD":
        raise ValueError("R1_SELECTED_USD_INTERFACE_REQUIRED")
    resolved = resolve_module(reference, ROOT)
    decisions = []
    for entry in resolved.closure:
        policy = entry["descriptor"]["policy"]
        decisions.extend({"decision_id": identity, "policy_id": policy["id"], "policy_revision": policy["revision"],
                          "status": policy["review_status"], "evidence_ref": "project-owned-selected-synthetic-fixture"}
                         for identity in policy["decision_ids"])
    cutoff_date = date.fromisoformat(fixture["observed_through"]) + timedelta(days=1)
    result = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": fixture["case_id"] + "-run", "scenario_id": fixture["case_id"], "mode": "final",
            "period": deepcopy(fixture["period"]), "cutoff": cutoff_date.isoformat() + "T00:00:00Z",
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180},
            "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": []},
        "scope": {"agreement_id": fixture["scope"]["contract_id"], "participant_ids": participants,
            "pool_id": fixture["scope"]["pool_id"], "purpose": "selected_synthetic_calculation", "asset_ids": assets},
        "inputs": inputs, "parameters": parameters, "evidence": evidence,
        "state_cells": list(state_cells), "decisions": decisions}
    return bind_module_package(result, ROOT)


def _slot(opening, unit):
    return {"opening": opening, "closing": opening, "purpose": "mqp_" + opening,
            "unit": unit, "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"],
            "movement_kinds": ["transition" if unit == "structured" else "net_change"], "history_required": False}


def _cell(fixture, opening, quantity, participant):
    scope = {"agreement_id": fixture["scope"]["contract_id"], "participant_id": participant,
             "pool_id": fixture["scope"]["pool_id"], "asset_id": fixture["project_id"]}
    purpose = "mqp_" + opening
    return {"state_key": canonical({**scope, "purpose": purpose}), "opening_port": opening,
        "purpose": purpose, "unit": "structured" if opening == "payment_registry" else "USD", "scope": scope,
        "boundary": fixture["period"]["start"], "quantity": quantity,
        "provenance_ref": "synthetic-original-opening-snapshot", "scenario_id": fixture["case_id"]}


def register_angel():
    money_type = {"name": "Money", "args": [{"name": "USD", "args": []}]}
    ratio_type = {"name": "Ratio", "args": []}
    library = _descriptor("weighted-allocation", "weighted-allocation.spl", "angel-policy.md", {}, exports=[{
        "name": "allocate", "parameters": [{"name": "amount", "type": money_type},
            {"name": "numerator", "type": ratio_type}, {"name": "denominator", "type": ratio_type}],
        "result": money_type, "definition": "allocated"}])
    return _descriptor("angel-guild", "angel-guild.spl", "angel-policy.md",
        {"cutoff": "parameter", "marketing_rate": "parameter", "filmmaker_share": "parameter", "evidence": "evidence",
         "comparison": "reconciliation", "settlements": "result"},
        imports=[{"module_ref": library, "alias": "allocation", "symbols": [{"export": "allocate", "local": "allocate_weighted"}]}],
        domains={"marketing_rate": {"minimum": "0", "maximum": "1"}, "filmmaker_share": {"minimum": "0", "maximum": "1"}})


def angel_package(fixture=None, *, reference=None):
    fixture = deepcopy(fixture or read_json(FOLDER / "angel-guild.json"))
    expected_policy = {"rounding": "exact_no_rounding", "negative_net": "reject", "zero_minutes": "reject", "metric_unit": "qualified_minutes"}
    if any(fixture["policy"][key] != value for key, value in expected_policy.items()):
        raise ValueError("R1_UNSUPPORTED_ANGEL_POLICY")
    if date.fromisoformat(fixture["observed_through"]) < date.fromisoformat(fixture["period"]["end"]):
        raise ValueError("R1_INCOMPLETE_USAGE_PERIOD")
    reference = reference or register_angel()
    decision = "ANGEL_GUILD_SELECTED"
    recipients = [{"asset_id": asset, "participant_id": "recipient-" + asset} for asset in sorted({row["title_id"] for row in fixture["usage"]})]
    cash = deepcopy(fixture["cash_records"])
    costs = deepcopy(fixture["costs"])
    usage = deepcopy(fixture["usage"])
    for row in [*cash, *costs]:
        row["amount"] = money(_q(row["amount"]), row["currency"])
        row["effective_date"] = row.pop("date")
    for row in usage:
        row["minutes"] = number(_q(row["minutes"]))
    cutoff = (date.fromisoformat(fixture["observed_through"]) + timedelta(days=1)).isoformat() + "T00:00:00Z"
    inputs = {"scope": _scope(fixture, recipients[0]["participant_id"]), "platform": fixture["platform_id"],
              "focal_title": fixture["focal_title"], "population_complete": fixture["usage_population"]["complete"],
              "population_platform": fixture["usage_population"]["platform_id"], "opening_carry": money(_q(fixture["opening_carry"])),
              "population_evidence": fixture["usage_population"]["evidence_id"], "cash_records": cash, "costs": costs,
              "usage": usage, "beneficiaries": recipients}
    return _package(fixture, reference, inputs,
        {"cutoff": cutoff, "marketing_rate": number(_q(fixture["policy"]["marketing_rate"])),
         "filmmaker_share": number(_q(fixture["policy"]["filmmaker_share"]))},
        {"evidence": _evidence(fixture, decision)}, [r["participant_id"] for r in recipients], [r["asset_id"] for r in recipients])


def register_mqp():
    return _descriptor("mqp-ordered", "mqp-ordered.spl", "mqp-policy.md",
        {"cutoff": "parameter", "trigger": "parameter", "threshold_comparison": "parameter", "threshold": "parameter",
         "lower_rate": "parameter", "upper_rate": "parameter", "evidence": "evidence", "comparison": "result"},
        state=[_slot("actual_paid", "USD"), _slot("fee_available_paid", "USD"), _slot("payment_registry", "structured")],
        domains={"trigger": {"choices": ["agreement_date", "actual_date"], "methodology": True},
                 "threshold_comparison": {"choices": ["at_least", "greater_than"], "methodology": True},
                 "threshold": {"minimum": money("0")}, "lower_rate": {"minimum": "0", "maximum": "1"},
                 "upper_rate": {"minimum": "0", "maximum": "1"}})


def mqp_package(fixture=None, *, reference=None):
    fixture = deepcopy(fixture or read_json(FOLDER / "mqp-ordered.json"))
    if any(fixture["policy"][key] != value for key, value in {
        "same_day_order": "explicit_unique_sequence", "application": "whole_receipt_prospective", "rounding": "exact_no_rounding"}.items()):
        raise ValueError("R1_UNSUPPORTED_MQP_POLICY")
    reference = reference or register_mqp()
    options = {"amount": lambda value: money(_q(value)), "disputed": lambda value: value, "payment_id": lambda value: value,
               "agreed_amount": lambda value: money(_q(value)), "agreed_actual_date": lambda value: value, "receipt_class": lambda value: value}
    events = []
    for original in fixture["events"]:
        row = {name: deepcopy(original[name]) for name in ["id", "contract_id", "pool_id", "currency", "project_id", "date", "kind", "evidence_id"]}
        row["effective_date"] = row.pop("date")
        row["sequence"] = str(original["sequence"])
        for name, convert in options.items():
            if name in original and name in {"amount", "agreed_amount"}:
                row[name] = {"some": money(_q(original[name]), original["currency"])}
            else:
                row[name] = {"some": convert(original[name])} if name in original else {"none": True}
        events.append(row)
    cutoff = (date.fromisoformat(fixture["observed_through"]) + timedelta(days=1)).isoformat() + "T00:00:00Z"
    parameters = {"cutoff": cutoff, "trigger": fixture["policy"]["trigger"],
        "threshold_comparison": fixture["policy"]["threshold_comparison"], "threshold": money(_q(fixture["policy"]["threshold"])),
        "lower_rate": number(_q(fixture["policy"]["lower_rate"])), "upper_rate": number(_q(fixture["policy"]["upper_rate"]))}
    participant = "mqp-selected-participant"
    cells = [_cell(fixture, "actual_paid", number(_q(fixture["opening_actual_paid"])), participant),
             _cell(fixture, "fee_available_paid", number(_q(fixture["opening_fee_available_paid"])), participant),
             _cell(fixture, "payment_registry", [], participant)]
    return _package(fixture, reference,
        {"scope": _scope(fixture, participant), "project": fixture["project_id"], "observed_through": fixture["observed_through"], "events": events},
        parameters, {"evidence": _evidence(fixture, "MQP_ORDERED_SELECTED")}, [participant],
        sorted({fixture["project_id"], *(row["project_id"] for row in fixture["events"])}), cells)
