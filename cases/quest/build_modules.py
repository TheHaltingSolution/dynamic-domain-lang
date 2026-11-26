"""Register the Quest synthetic method and faithfully transport original facts.

Only checked SPL derives elapsed days, target powers, charge indices or money.
Calendar date/origin checks below validate nonfinancial Gregorian fact transport.
"""
from copy import deepcopy
from pathlib import Path

from cases.r1.build_modules import _descriptor, _pin, _type
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import (day, exact, fail, file_digest, money,
                                 number, read_json, write_json)
from spl_compiler.modules import bind_module_package, resolve_module
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "DYN02-QUEST-TWOFLOW-NEAREST-EVEN"
DECISION = "QUEST_TWOFLOW_SELECTED"
POWER_DECISION = "QUEST_POWER_SELECTED"
SOURCE_REF = "sec-quest-agreement@sha256:9f1c535acfa79aaab13b860e18cd731936425e2d42ac519942d37451deeda151"
SOURCE_LOCATOR = "Schedule II, page 19, late-payment paragraph"


def _fields(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        fail("QUEST_NEUTRAL_SHAPE", "Unexpected or missing fields in " + label)


def _neutral_shape(data):
    _fields(data, "schema_version case_id scope period cutoff clause terms selected obligations payments applications evidence calendar", "neutral fixture")
    scope_fields = "agreement_id participant_id pool_id asset_id currency"
    _fields(data["scope"], scope_fields, "scope")
    _fields(data["period"], "start end", "period")
    _fields(data["clause"], "source_ref locator component", "clause")
    _fields(data["terms"], "policy_id revision annual_target day_count quantum rounding", "terms")
    _fields(data["selected"], "obligation_id payment_id application_id", "selected identities")
    _fields(data["calendar"], "id version origin source_ref observations", "calendar")
    row_fields = {"obligations": "id amount currency due_date scope observed_at evidence_id source_ref",
                  "payments": "id economic_event_id amount currency paid_date scope observed_at evidence_id source_ref",
                  "applications": "id obligation_id payment_id amount currency effective_date scope observed_at evidence_id source_ref",
                  "evidence": "id observed_at source_ref"}
    for collection, expected in row_fields.items():
        if not isinstance(data[collection], list):
            fail("QUEST_NEUTRAL_SHAPE", collection + " must be a list")
        for row in data[collection]:
            _fields(row, expected, collection)
            if collection != "evidence":
                _fields(row["scope"], scope_fields, collection + " scope")
    if not isinstance(data["calendar"]["observations"], list):
        fail("QUEST_NEUTRAL_SHAPE", "calendar observations must be a list")
    for row in data["calendar"]["observations"]:
        _fields(row, "id date ordinal observed_at evidence_id source_ref", "calendar observation")


def _calendar_ordinal(day_value, origin_value, ordinal):
    """Validate a Gregorian fact, never the financial due-to-paid interval."""
    observed_day, origin = day(day_value), day(origin_value)
    value = exact(ordinal)
    if value.denominator != 1 or value < 0 or value != (observed_day - origin).days:
        fail("QUEST_CALENDAR_FACT", "Gregorian date/origin and supplied ordinal disagree")
    return number(value)


def _calendar_facts():
    facts = read_json(FOLDER / "calendar-facts.json")
    if facts["schema_version"] != "quest-calendar-facts/1":
        fail("QUEST_CALENDAR_VERSION", "Expected quest-calendar-facts/1")
    seen = set()
    for row in facts["facts"]:
        if row["date"] in seen:
            fail("QUEST_CALENDAR_FACT", "Duplicate ordinary calendar date")
        seen.add(row["date"])
        _calendar_ordinal(row["date"], facts["origin"], row["ordinal"])
    if not any(row["date"] == facts["origin"] and exact(row["ordinal"]) == 0 for row in facts["facts"]):
        fail("QUEST_CALENDAR_FACT", "Calendar truth requires its origin at ordinal zero")
    return facts


def _power_exports():
    syntax = parse((FOLDER / "power.spl").read_text(encoding="utf-8"), "power.spl")
    check_schedule(syntax)
    result = next(row for row in syntax["declarations"] if row.get("name") == "result")
    return [{"name": "pow", "definition": "result",
             "parameters": [{"name": row["name"], "type": row["type"]}
                            for row in syntax["declarations"] if row["kind"] == "input"],
             "result": _type(result["expr"]["_type"])}]


def _truth_transport(facts):
    # `date` is reserved in source; retain the neutral fact through a rename.
    return [{"calendar_date": row["date"], "ordinal": row["ordinal"]} for row in facts["facts"]]


def _registered(name, *, decisions, **kwargs):
    reference = _descriptor(name, name + ".spl", "policy.md", kwargs.pop("roles", {}), folder=FOLDER, **kwargs)
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "quest:" + name
    descriptor["policy"].update(id="quest:" + name + "-policy", decision_ids=list(decisions),
        evidence_class="synthetic", review_status="proposed",
        discriminating_cases=["quest-1000-20pct-182days", "quest-half-cent-even-zero", "quest-half-cent-even-two",
                              "quest-zero-days", "quest-full-year", "quest-180days", "quest-invalid-flow-calendar-cutoff"])
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": descriptor["revision"], **_pin(path)}


def register_quest():
    """Deliberately author only this new module closure; never refresh old runs."""
    facts = _calendar_facts()
    source = read_json(FOLDER / "source-index.json")
    if source["source_ref"] != SOURCE_REF or source["locator"] != SOURCE_LOCATOR or not SOURCE_REF.endswith(source["sha256"]):
        fail("QUEST_SOURCE_IDENTITY", "Actual source provenance differs from the selected clause")
    power = _registered("power", decisions=[POWER_DECISION], exports=_power_exports())
    domains = {
        "clause_source": {"choices": [SOURCE_REF], "methodology": True},
        "clause_locator": {"choices": [SOURCE_LOCATOR], "methodology": True},
        "annual_target": {"minimum": "0"},
        "quantum": {"choices": [money("0.01")], "methodology": True},
        "rounding": {"choices": ["half_even"], "methodology": True},
        "day_count": {"choices": ["ACT/365"], "methodology": True},
        "policy_id": {"choices": [POLICY], "methodology": True},
        "policy_revision": {"choices": ["1"], "methodology": True},
        "calendar_id": {"choices": [facts["id"]], "methodology": True},
        "calendar_version": {"choices": [facts["version"]], "methodology": True},
        "calendar_origin": {"choices": [facts["origin"]], "methodology": True},
        "calendar_source": {"choices": [facts["source_ref"]], "methodology": True},
        "calendar_source_sha256": {"choices": [file_digest(FOLDER / "calendar-facts.json")], "methodology": True},
        "calendar_truth": {"choices": [_truth_transport(facts)], "methodology": True},
        **{name: {"min_items": 1, "max_items": 1} for name in ["obligations", "payments", "applications"]}}
    parameters = {"cutoff", "obligation_id", "payment_id", "application_id", "clause_source", "clause_locator",
                  "annual_target", "quantum", "rounding", "day_count", "policy_id", "policy_revision",
                  "calendar_id", "calendar_version", "calendar_origin", "calendar_source", "calendar_source_sha256", "calendar_truth"}
    root = _registered("charge", decisions=[DECISION],
        imports=[{"module_ref": power, "alias": "quest_power", "symbols": [{"export": "pow", "local": "int_power"}]}],
        roles={**{name: "parameter" for name in parameters}, "evidence": "evidence", "comparison": "detail",
               "settlements": "result", "certificate": "reconciliation", "observations": "detail"}, domains=domains)
    path = ROOT / root["locator"]
    descriptor = read_json(path)
    constraints = descriptor["constraints"]
    for collection, fields in [("obligations", ["id"]), ("payments", ["id", "economic_event_id"]),
                               ("applications", ["id"]), ("calendar", ["id", "calendar_date"])]:
        for field in fields:
            constraints.append({"kind": "unique", "path": "inputs." + collection, "fields": [field], "target": "", "value": ""})
        constraints.append({"kind": "references", "path": "inputs." + collection, "fields": ["evidence_id"],
                            "target": "evidence.evidence.*.evidence_id", "value": ""})
    constraints.append({"kind": "unique", "path": "evidence.evidence", "fields": ["evidence_id"], "target": "", "value": ""})
    for field, target in [("obligation_id", "obligations"), ("payment_id", "payments")]:
        constraints.append({"kind": "references", "path": "inputs.applications", "fields": [field],
                            "target": "inputs." + target + ".*.id", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def quest_package(fixture=None, *, reference=None):
    """Copy facts/terms and validate only mechanical calendar/source transport."""
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _neutral_shape(data)
    if data["schema_version"] != "quest-two-flow-neutral/1":
        fail("QUEST_NEUTRAL_VERSION", "Expected quest-two-flow-neutral/1")
    scope, terms, calendar, selected, clause = (data[name] for name in ["scope", "terms", "calendar", "selected", "clause"])
    if scope["currency"] != "USD" or clause["component"] != "additional_target_return_only":
        fail("QUEST_SELECTED_PROFILE", "Selected profile requires USD and the additional target-return component")
    facts = _calendar_facts()
    evidence = [{"evidence_id": row["id"], "observed_at": row["observed_at"], "approval_ref": DECISION,
                 "evidence_ref": row["id"], "kind": "selected_synthetic_record", "source_ref": row["source_ref"]}
                for row in data["evidence"]]
    inputs = {"scope": {"agreement_id": scope["agreement_id"], "participant_id": scope["participant_id"],
                         "pool_id": scope["pool_id"], "period": deepcopy(data["period"])}, "project": scope["asset_id"]}
    for collection in ["obligations", "payments", "applications"]:
        inputs[collection] = [{**deepcopy(row), "amount": money(exact(row["amount"]), row["currency"])} for row in data[collection]]
    inputs["calendar"] = [{**{key: deepcopy(value) for key, value in row.items() if key != "date"},
        "calendar_date": row["date"], "calendar_id": calendar["id"], "version": calendar["version"],
        "origin": calendar["origin"], "ordinal": _calendar_ordinal(row["date"], calendar["origin"], row["ordinal"])}
        for row in calendar["observations"]]
    reference = reference or register_quest()
    resolved = resolve_module(reference, ROOT)
    decisions = [{"decision_id": name, "policy_id": entry["descriptor"]["policy"]["id"],
                  "policy_revision": entry["descriptor"]["policy"]["revision"], "status": "proposed",
                  "evidence_ref": "selected-research-assumption-not-professional-approval"}
                 for entry in resolved.closure for name in entry["descriptor"]["policy"]["decision_ids"]]
    parameters = {"cutoff": data["cutoff"], **{name: selected[name] for name in ["obligation_id", "payment_id", "application_id"]},
        "clause_source": clause["source_ref"], "clause_locator": clause["locator"],
        "annual_target": number(exact(terms["annual_target"])), "quantum": money(exact(terms["quantum"])),
        "rounding": terms["rounding"], "day_count": terms["day_count"], "policy_id": terms["policy_id"], "policy_revision": terms["revision"],
        "calendar_id": calendar["id"], "calendar_version": calendar["version"], "calendar_origin": calendar["origin"],
        "calendar_source": calendar["source_ref"], "calendar_source_sha256": file_digest(FOLDER / "calendar-facts.json"),
        "calendar_truth": _truth_transport(facts)}
    return bind_module_package({"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-quest-run", "scenario_id": data["case_id"], "mode": "final",
            "period": deepcopy(data["period"]), "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["agreement_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"],
                  "asset_ids": [scope["asset_id"]], "purpose": "quest_additional_target_return_only"},
        "inputs": inputs, "parameters": parameters, "evidence": {"evidence": evidence}, "state_cells": [], "decisions": decisions}, ROOT)


def quest_bindings(package):
    """Transport the already declared ports to the direct interpreter envelope."""
    return {"inputs": deepcopy({**package["inputs"], **package["parameters"], **package["evidence"]}), "openings": {}}


if __name__ == "__main__":
    package = quest_package(reference=register_quest())
    package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
    write_json(FOLDER / "package.json", package)
