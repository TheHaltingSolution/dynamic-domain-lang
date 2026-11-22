"""Explicit registration and mechanical transport for the selected M1a recipes.

Only SPL calculates financial results. This adapter tags exact facts, binds
scope/evidence, and transports original or serialized successor state.
"""
from copy import deepcopy
from pathlib import Path
import json

from cases.r1.build_modules import _descriptor, _pin, _q
from spl_compiler.codecs import canonical, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
METHODS = ["period_marginal", "period_whole_base", "cumulative_marginal", "period_cap",
           "cumulative_cap", "period_floor", "tiers_then_cap"]


def _register(name, **kwargs):
    ref = _descriptor(name, name + ".spl", "policy.md", kwargs.pop("roles", {}), folder=FOLDER, **kwargs)
    path = ROOT / ref["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "m1:" + name
    descriptor["policy"]["id"] = "spl:policy:m1:" + name
    witnesses = {
        "tiers": ["period-marginal", "period-whole-base", "cumulative-marginal", "tiers-then-cap"],
        "cumulative-tiers": ["cumulative-marginal"],
        "cap": ["period-cap", "cumulative-cap", "tiers-then-cap"],
        "guarantee": ["period-floor"],
        "ordinary": ["period-marginal", "period-whole-base", "cumulative-marginal", "period-cap",
                     "cumulative-cap", "period-floor", "tiers-then-cap"]}
    descriptor["policy"]["discriminating_cases"] = ["m1-" + case for case in witnesses[name]]
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def _exports(source, names):
    from spl_compiler.checker import check_schedule
    from spl_compiler.parser import parse
    from cases.r1.build_modules import _type
    syntax = parse((FOLDER / (source + ".spl")).read_text(encoding="utf-8"))
    check_schedule(syntax)
    parameters = [{"name": row["name"], "type": row["type"]} for row in syntax["declarations"] if row["kind"] == "input"]
    return [{"name": public, "definition": definition, "parameters": parameters,
             "result": _type(next(row for row in syntax["declarations"] if row.get("name") == definition)["expr"]["_type"])}
            for public, definition in names]


def _import(reference, symbols):
    return {"module_ref": reference, "alias": reference["id"].split(":")[1].replace("-", "_"),
            "symbols": [{"export": exported, "local": local} for exported, local in symbols]}


def register_m1():
    tiers = _register("tiers", exports=_exports("tiers", [("marginal", "marginal"), ("whole_base", "whole_base")]))
    # The cumulative result type is a structural record, independent of values.
    money_type = {"name": "Money", "args": [{"name": "USD", "args": []}]}
    tier_descriptor = read_json(ROOT / tiers["locator"])
    bracket_type = tier_descriptor["interface"]["exports"][0]["parameters"][1]["type"]
    cumulative = _register("cumulative-tiers", imports=[_import(tiers, [("marginal", "tier_marginal")])], exports=[{
        "name": "cumulative", "definition": "cumulative",
        "parameters": [{"name": "prior_basis", "type": money_type}, {"name": "current_basis", "type": money_type}, {"name": "brackets", "type": bracket_type}],
        "result": {"name": "Record", "args": [], "fields": [["earned", money_type], ["ending", money_type]]}}])
    cap = _register("cap", exports=_exports("cap", [("apply", "capped")]))
    guarantee = _register("guarantee", exports=_exports("guarantee", [("period", "guaranteed")]))
    return _register("ordinary", imports=[_import(tiers, [("marginal", "marginal_tiers"), ("whole_base", "whole_tiers")]),
        _import(cumulative, [("cumulative", "cumulative_tiers")]), _import(cap, [("apply", "apply_cap")]),
        _import(guarantee, [("period", "period_guarantee")])],
        roles={"cutoff": "parameter", "method": "parameter", "brackets": "parameter", "cap": "parameter", "floor": "parameter",
               "reset_period_cap": "parameter", "evidence": "evidence", "comparison": "detail", "settlements": "result"},
        domains={"method": {"choices": METHODS, "methodology": True},
                 "cap": {"minimum": money("0")}, "floor": {"minimum": money("0")}},
        state=[{"opening": "meter", "closing": "meter", "purpose": "m1_selected_method_meter", "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"],
                "movement_kinds": ["transition"], "history_required": False}])


def _state_scope(scope):
    return {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"],
            "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}


def m1_package(fixture=None, *, reference=None):
    fixture = deepcopy(fixture if fixture is not None else json.loads((FOLDER / "fixtures" / "period-marginal.json").read_text(encoding="utf-8")))
    if fixture.get("schema_version") != "m1-neutral/1":
        raise ValueError("M1_NEUTRAL_SCHEMA_REQUIRED")
    policy = fixture["policy"]
    if any(type(row["sequence"]) is not int or row["sequence"] < 0 for row in policy["tiers"]):
        raise ValueError("M1_TIER_SEQUENCE_REQUIRED")
    if any(policy[key] != value for key, value in {"rounding": "exact_no_rounding", "negative_basis": "reject",
                                                  "threshold_equality": "lower_inclusive"}.items()):
        raise ValueError("M1_UNSUPPORTED_POLICY")
    scope = fixture["scope"]
    if scope["currency"] != "USD" or fixture["opening_state"]["scope"]["currency"] != "USD":
        raise ValueError("M1_SELECTED_USD_REQUIRED")
    reference = reference or register_m1()
    resolved = resolve_module(reference, ROOT)
    decisions = [{"decision_id": name, "policy_id": row["descriptor"]["policy"]["id"], "policy_revision": "1", "status": "proposed",
                  "evidence_ref": "project-selected-synthetic-policy"}
                 for row in resolved.closure for name in row["descriptor"]["policy"]["decision_ids"]]
    facts = [{"id": row["id"], "effective_date": row["effective_date"], "observed_at": row["observed_at"],
              "evidence_id": row["evidence_id"], "amount": money(_q(row["amount"])),
              "fact_scope": deepcopy(row.get("scope", scope))} for row in fixture["facts"]]
    brackets = [{"id": row["id"], "sequence": str(row["sequence"]), "lower": money(_q(row["lower"])), "rate": number(_q(row["rate"])),
                 "upper": {"none": True} if row["upper"] is None else {"some": money(_q(row["upper"]))}}
                for row in policy["tiers"]]
    evidence = [{"evidence_id": row["id"], "observed_at": row["observed_at"], "approval_ref": "ORDINARY_SELECTED",
                 "evidence_ref": row["id"], "kind": "selected_synthetic_record"} for row in fixture["evidence"]]
    opening = fixture["opening_state"]
    cell_scope = _state_scope(opening["scope"])
    purpose = "m1_selected_method_meter"
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": fixture["case_id"] + "-run", "scenario_id": fixture["case_id"], "mode": "final",
            "period": deepcopy(fixture["period"]), "cutoff": fixture["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"],
                  "asset_ids": [scope["asset_id"]], "purpose": "selected_synthetic_calculation"},
        "inputs": {"scope": {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "period": deepcopy(fixture["period"])},
                   "project": scope["asset_id"], "facts": facts},
        "parameters": {"cutoff": fixture["cutoff"], "method": policy["method"], "cap": money(_q(policy["cap"])), "floor": money(_q(policy["floor"])),
                       "reset_period_cap": policy["reset_period_cap"], "brackets": brackets},
        "evidence": {"evidence": evidence}, "decisions": decisions,
        "state_cells": [{"state_key": canonical({**cell_scope, "purpose": purpose}), "opening_port": "meter", "purpose": purpose,
            "unit": "structured", "scope": cell_scope, "boundary": fixture["period"]["start"],
            "quantity": {"method": opening["method"], "balance": money(_q(opening["balance"])), "period": deepcopy(opening["period"])},
            "provenance_ref": "selected-synthetic-original-opening", "scenario_id": fixture["case_id"]}]}
    return bind_module_package(package, ROOT)


if __name__ == "__main__":
    reference = register_m1()
    for path in sorted((FOLDER / "fixtures").glob("*.json")):
        fixture = json.loads(path.read_text(encoding="utf-8"))
        if fixture.get("schema_version") == "m1-neutral/1":
            package = m1_package(fixture, reference=reference)
            package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
            write_json(FOLDER / (path.stem + "-canonical-package.json"), package)
