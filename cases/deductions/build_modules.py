"""Registration and mechanical transport of original staged-deduction facts.

No financial stage, category selection, cap allocation or historical consumption
is computed here. SPL performs those decisions; the neutral oracle is separate.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin, _type
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, day, exact, instant, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-STAGED-DEDUCTIONS-01"
SCOPE_FIELDS = ["contract_id", "participant_id", "pool_id", "asset_id", "currency"]
COST_FIELDS = ["id", "scope", "amount", "category", "sequence", "effective_date", "observed_at", "source_ref", "evidence_ref"]
STATE_FIELDS = ["scope", "purpose", "policy_id", "policy_revision", "variant", "cap_limit", "cap_consumed", "cost_history", "boundary", "origin", "source_case_id"]


def _fields(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or not value.keys() <= set(required) | set(optional):
        raise ValueError("DEDUCTION_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("DEDUCTION_EXACT_VALUE_REQUIRED")
    return Fraction(value)


def _observation(row):
    # Date/observation consistency is a physical fact check. This neither selects
    # the period nor computes a deduction; every supplied row is retained.
    if instant(day(row["effective_date"]).isoformat() + "T00:00:00Z") > instant(row["observed_at"]):
        raise ValueError("DEDUCTION_OBSERVATION_BEFORE_EVENT")


def _cost(row, historical=False):
    _fields(row, COST_FIELDS + (["deducted", "disposition", "recognized_period"] if historical else []))
    _fields(row["scope"], SCOPE_FIELDS)
    if type(row["sequence"]) is not int:
        raise ValueError("DEDUCTION_COST_SEQUENCE")
    _observation(row)
    result = deepcopy(row)
    result["amount"] = money(_q(row["amount"]))
    result["sequence"] = str(row["sequence"])
    if historical:
        result["deducted"] = money(_q(row["deducted"]))
    return result


def _state(value):
    _fields(value, STATE_FIELDS)
    _fields(value["scope"], SCOPE_FIELDS)
    result = deepcopy(value)
    result["cap_limit"] = money(_q(value["cap_limit"]))
    result["cap_consumed"] = money(_q(value["cap_consumed"]))
    result["cost_history"] = [_cost(row, historical=True) for row in value["cost_history"]]
    return result


def neutral_state(value):
    """Decode actual serialized closing state into neutral exact fact spellings."""
    if isinstance(value, dict):
        if set(value) == {"value", "currency"}:
            if value["currency"] != "USD":
                raise ValueError("DEDUCTION_CURRENCY")
            return str(exact(value["value"]))
        result = {key: neutral_state(child) for key, child in value.items()}
        if "sequence" in result:
            sequence = exact(result["sequence"])
            if sequence.denominator != 1:
                raise ValueError("DEDUCTION_COST_SEQUENCE")
            result["sequence"] = sequence.numerator
        return result
    if isinstance(value, list):
        return [neutral_state(child) for child in value]
    return value


def _register(name, **kwargs):
    reference = _descriptor(name, name + ".spl", "policy.md", kwargs.pop("roles", {}), folder=FOLDER, **kwargs)
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:deduction-" + name
    descriptor["policy"].update(id=POLICY, evidence_class="synthetic", review_status="proposed",
                                discriminating_cases=["deduction-six-variants", "deduction-cap-carry", "deduction-no-original-cost-reuse"])
    if name == "deductions":
        # The neutral policy permits a genuinely empty close. Every supplied
        # fact/history row still requires a validated evidence reference in SPL;
        # nonempty evidence retains the generic cutoff/authority checks.
        for constraint in descriptor["constraints"]:
            if constraint["kind"] == "evidence":
                constraint["required"] = False
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def register_deductions():
    syntax = parse((FOLDER / "stages.spl").read_text(encoding="utf-8"))
    check_schedule(syntax)
    parameters = [{"name": d["name"], "type": d["type"]} for d in syntax["declarations"] if d["kind"] == "input"]
    result = _type(next(d for d in syntax["declarations"] if d.get("name") == "stages")["expr"]["_type"])
    stages = _register("stages", exports=[{"name": "calculate", "definition": "stages", "parameters": parameters, "result": result}])
    return _register("deductions", imports=[{"module_ref": stages, "alias": "stages", "symbols": [{"export": "calculate", "local": "deduction_stages"}]}],
                     roles={**{name: "parameter" for name in ["cutoff", "policy_id", "policy_revision", "variant", "share", "fee_rate", "cap", "eligible_categories", "rounding", "allocation", "evidence_class"]},
                            "evidence": "evidence", "comparison": "result", "cost_lines": "detail", "reconciliation": "reconciliation"},
                     domains={"share": {"minimum": "0", "maximum": "1"}, "fee_rate": {"minimum": "0", "maximum": "1"}, "cap": {"minimum": money("0")}},
                     state=[{"opening": "ledger", "closing": "ledger", "purpose": "distribution_deduction", "unit": "structured",
                             "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"],
                             "movement_kinds": ["transition"], "history_required": False}])


def deduction_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _fields(data, ["schema_version", "case_id", "scope", "period", "cutoff", "terms", "receipts", "costs", "evidence", "opening_state"], ["prior_result"])
    if data["schema_version"] != "deduction-neutral/1":
        raise ValueError("DEDUCTION_NEUTRAL_SCHEMA")
    scope, terms = data["scope"], data["terms"]
    _fields(scope, SCOPE_FIELDS)
    _fields(terms, ["policy_id", "policy_revision", "variant", "share", "fee_rate", "cap", "eligible_categories", "rounding", "allocation", "evidence_class"])
    if scope["currency"] != "USD":
        raise ValueError("DEDUCTION_CURRENCY")
    reference = reference or register_deductions()
    decisions = [{"decision_id": decision, "policy_id": row["descriptor"]["policy"]["id"], "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-synthetic-staged-deductions"}
                 for row in resolve_module(reference, ROOT).closure for decision in row["descriptor"]["policy"]["decision_ids"]]
    inputs = {"scope": {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "period": data["period"]},
              "project": scope["asset_id"], "fact_scope": scope, "case_id": data["case_id"], "supplied_opening": _state(data["opening_state"])}
    receipts = []
    for row in data["receipts"]:
        _fields(row, ["id", "scope", "gross_amount", "net_amount", "effective_date", "observed_at", "source_ref", "evidence_ref"])
        _fields(row["scope"], SCOPE_FIELDS)
        _observation(row)
        receipts.append({**row, "gross_amount": money(_q(row["gross_amount"])), "net_amount": money(_q(row["net_amount"]))})
    inputs["receipts"], inputs["costs"] = receipts, [_cost(row) for row in data["costs"]]
    evidence = []
    for row in data["evidence"]:
        _fields(row, ["id", "scope", "observed_at", "kind"])
        _fields(row["scope"], SCOPE_FIELDS)
        evidence.append({"id": row["id"], "scope": row["scope"], "observed_at": row["observed_at"], "source_kind": row["kind"],
                         "approval_ref": "DEDUCTIONS_SELECTED", "evidence_ref": row["id"], "kind": "selected_synthetic_record"})
    cell_scope = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    cell = {"opening_port": "ledger", "state_key": canonical({**cell_scope, "purpose": "distribution_deduction"}), "purpose": "distribution_deduction", "unit": "structured",
            "scope": cell_scope, "boundary": data["period"]["start"], "quantity": _state(data["opening_state"]),
            "provenance_ref": "supplied-original-cost-opening", "scenario_id": "SYNTHETIC-DEDUCTIONS"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _fields(prior, ["source_case_id", "period", "closing_state"], ["result_ref"])
        if not isinstance(prior.get("result_ref"), str) or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("DEDUCTION_CANONICAL_PREDECESSOR_REQUIRED")
        cell["prior_result_ref"] = prior["result_ref"]
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
    else:
        inputs["predecessor"] = {"none": True}
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(c.get("prior_result_ref") != cell["prior_result_ref"] for c in cells):
        raise ValueError("DEDUCTION_CANONICAL_PREDECESSOR_MISMATCH")
    parameters = {name: terms[name] for name in ["policy_id", "policy_revision", "variant", "eligible_categories", "rounding", "allocation", "evidence_class"]}
    parameters.update(cutoff=data["cutoff"], share=number(_q(terms["share"])), fee_rate=number(_q(terms["fee_rate"])), cap=money(_q(terms["cap"])))
    package = {"profile": "spl-module/1", "module_ref": reference,
               "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-DEDUCTIONS", "mode": "final", "period": data["period"], "cutoff": data["cutoff"],
                            "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
               "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": "selected-synthetic-deductions"},
               "inputs": inputs, "parameters": parameters, "evidence": {"evidence": evidence}, "decisions": decisions, "state_cells": cells}
    return bind_module_package(package, ROOT)


def run_deduction_package(package, registry_root=None, *, backend="compare", artifact_dir=None):
    return run_module_package(package, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir)


if __name__ == "__main__":
    package = deduction_package(reference=register_deductions())
    package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
    write_json(FOLDER / "canonical-package.json", package)
