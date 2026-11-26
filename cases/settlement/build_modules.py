"""Explicit registration and mechanical transport for supplied settlement facts.

The adapter checks physical records and chronology, tags exact money and retains
original identities. Withholding, eligibility, obligation application and carry
are calculated exclusively by SPL and independently controlled by the oracle.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin, _type
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, exact, instant, money, number, read_json, write_json, day
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-SETTLEMENT-01"


def _q(value):
    # Neutral records use strings. Reducing a rational during transport changes
    # its spelling only; it neither calculates withholding nor selects policy.
    if type(value) is not str or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("SETTLEMENT_EXACT_VALUE_REQUIRED")
    return Fraction(value)


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= value.keys() or not value.keys() <= set(required) | set(optional):
        raise ValueError("SETTLEMENT_RECORD_FIELDS")


def _register(name, **kwargs):
    ref = _descriptor(name, name + ".spl", "policy.md", kwargs.pop("roles", {}), folder=FOLDER, **kwargs)
    path = ROOT / ref["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:settlement-" + name
    descriptor["policy"].update(id=POLICY, evidence_class="synthetic", review_status="proposed",
                                discriminating_cases=["settlement-baseline", "threshold-equality", "old-issued-below-threshold", "three-period-carry"])
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def register_settlement():
    source = parse((FOLDER / "amounts.spl").read_text(encoding="utf-8"))
    check_schedule(source)
    params = [{"name": d["name"], "type": d["type"]} for d in source["declarations"] if d["kind"] == "input"]
    result_type = _type(next(d for d in source["declarations"] if d.get("name") == "amounts")["expr"]["_type"])
    library = _register("amounts", exports=[{"name": "calculate", "definition": "amounts", "parameters": params, "result": result_type}])
    return _register("settlement", imports=[{"module_ref": library, "alias": "amounts",
        "symbols": [{"export": "calculate", "local": "settlement_amounts"}]}],
        roles={**{name: "parameter" for name in ["cutoff", "policy_id", "policy_revision", "rounding", "threshold_policy", "evidence_class", "withholding_rate", "minimum_payout"]},
               "evidence": "evidence", "comparison": "result", "obligations": "detail", "reconciliation": "reconciliation"},
        domains={"withholding_rate": {"minimum": "0", "maximum": "1"}, "minimum_payout": {"minimum": money("0")}},
        state=[{"opening": "ledger", "closing": "ledger", "purpose": "net_unpaid", "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"],
                "movement_kinds": ["transition"], "history_required": False}])


def _state(value):
    _fields(value, ["scope", "purpose", "policy_id", "policy_revision", "boundary", "origin", "source_case_id", "deferred_unissued", "issued_obligations", "recognized_ids"])
    result = deepcopy(value)
    result["deferred_unissued"] = money(_q(value["deferred_unissued"]))
    tokens = []
    for token in value["recognized_ids"]:
        if not isinstance(token, str) or ":" not in token:
            raise ValueError("SETTLEMENT_RECOGNIZED_IDS")
        kind, identity = token.split(":", 1)
        if kind not in {"earned", "issued", "payments", "applications"} or not identity:
            raise ValueError("SETTLEMENT_RECOGNIZED_IDS")
        tokens.append([kind, identity])
    result["recognized_ids"] = tokens
    for row in result["issued_obligations"]:
        row["amount"], row["paid_to_date"] = money(_q(row["amount"])), money(_q(row["paid_to_date"]))
    return result


def neutral_state(value):
    """Decode a serialized typed closing cell quantity without computing money."""
    if isinstance(value, dict):
        if set(value) == {"value", "currency"}:
            if value["currency"] != "USD":
                raise ValueError("SETTLEMENT_CURRENCY")
            return str(exact(value["value"]))
        result = {k: neutral_state(v) for k, v in value.items()}
        if "recognized_ids" in result:
            result["recognized_ids"] = [kind + ":" + identity for kind, identity in result["recognized_ids"]]
        return result
    if isinstance(value, list):
        return [neutral_state(v) for v in value]
    return value


def settlement_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _fields(data, ["schema_version", "case_id", "scope", "period", "cutoff", "terms", "earned", "issued", "payments", "applications", "evidence", "opening_state"], ["prior_result"])
    if data["schema_version"] != "settlement-neutral/1":
        raise ValueError("SETTLEMENT_NEUTRAL_SCHEMA")
    terms, scope = data["terms"], data["scope"]
    _fields(terms, ["policy_id", "policy_revision", "withholding_rate", "minimum_payout", "rounding", "threshold", "evidence_class"])
    _fields(scope, ["contract_id", "participant_id", "pool_id", "asset_id", "currency"])
    if scope["currency"] != "USD":
        raise ValueError("SETTLEMENT_CURRENCY")
    reference = reference or register_settlement()
    decisions = [{"decision_id": name, "policy_id": row["descriptor"]["policy"]["id"], "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-synthetic-supplied-settlement"}
                 for row in resolve_module(reference, ROOT).closure for name in row["descriptor"]["policy"]["decision_ids"]]
    inputs = {"scope": {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "period": deepcopy(data["period"])},
              "project": scope["asset_id"], "fact_scope": scope, "case_id": data["case_id"], "supplied_opening": _state(data["opening_state"])}
    common = ["id", "scope", "amount", "observed_at", "source_ref", "evidence_ref"]
    for kind, date_field in [("earned", "effective_date"), ("issued", "issued_date"), ("payments", "paid_date"), ("applications", None)]:
        inputs[kind] = deepcopy(data[kind])
        for row in inputs[kind]:
            _fields(row, common + ([date_field] if date_field else ["payment_id", "issued_id"]))
            row["amount"] = money(_q(row["amount"]))
            if date_field:
                # Gregorian normalization/chronology is a data-boundary check,
                # not withholding, threshold selection or payment calculation.
                event_date = day(row[date_field])
                if instant(event_date.isoformat() + "T00:00:00Z") > instant(row["observed_at"]):
                    raise ValueError("SETTLEMENT_OBSERVATION_BEFORE_EVENT")
    evidence = []
    for row in data["evidence"]:
        _fields(row, ["id", "scope", "observed_at", "kind"], ["period"])
        evidence.append({"id": row["id"], "scope": row["scope"], "observed_at": row["observed_at"], "source_kind": row["kind"],
                         "period": {"some": row["period"]} if "period" in row else {"none": True},
                         "approval_ref": "SETTLEMENT_SELECTED", "evidence_ref": row["id"], "kind": "selected_synthetic_record"})
    cell_scope = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    cell = {"opening_port": "ledger", "state_key": canonical({**cell_scope, "purpose": "net_unpaid"}), "purpose": "net_unpaid", "unit": "structured",
            "scope": cell_scope, "boundary": data["period"]["start"], "quantity": _state(data["opening_state"]),
            "provenance_ref": "supplied-original-opening", "scenario_id": "SYNTHETIC-SETTLEMENT"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _fields(prior, ["source_case_id", "period", "closing_state"], ["result_ref"])
        # Actual canonical predecessor provenance is required for canonical carry.
        if not isinstance(prior.get("result_ref"), str) or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("SETTLEMENT_CANONICAL_PREDECESSOR_REQUIRED")
        cell["prior_result_ref"] = prior["result_ref"]
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
    else:
        inputs["predecessor"] = {"none": True}
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(c.get("prior_result_ref") != cell["prior_result_ref"] for c in cells):
        raise ValueError("SETTLEMENT_CANONICAL_PREDECESSOR_MISMATCH")
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-SETTLEMENT", "mode": "final", "period": data["period"], "cutoff": data["cutoff"],
                     "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": "selected-synthetic-settlement"},
        "inputs": inputs, "parameters": {"cutoff": data["cutoff"], "policy_id": terms["policy_id"], "policy_revision": terms["policy_revision"], "rounding": terms["rounding"],
                                        "threshold_policy": terms["threshold"], "evidence_class": terms["evidence_class"], "withholding_rate": number(_q(terms["withholding_rate"])), "minimum_payout": money(_q(terms["minimum_payout"]))},
        "evidence": {"evidence": evidence}, "decisions": decisions, "state_cells": cells}
    return bind_module_package(package, ROOT)


def run_settlement_package(package, registry_root=None, *, backend="compare", artifact_dir=None):
    """Label only an unfinalized missing-population failure for this profile.

    Generic successful results and their digest-bearing fields are untouched.
    Generic blocked runs otherwise retain their not_assessed payment label.
    """
    return run_module_package(package, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir,
        blocked_evidence_labels={"SETTLEMENT_PAYMENT_POPULATION_REQUIRED": {"payment_evidence_status": "no_event_supplied"}})


if __name__ == "__main__":
    package = settlement_package(reference=register_settlement())
    package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
    write_json(FOLDER / "canonical-package.json", package)
