"""Explicit coordinator envelope and original current-entitlement transport.

All endpoint scopes remain genuine inner records. No oracle, topology, balances
or transfer arithmetic is calculated in this adapter.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, money, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-CONTRACT-TRANSFERS-01"
OPERATOR = "coordinator-operator"
ENVELOPE_POOL = "coordinator-ledger"


def _record(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() or not value.keys() <= set(required) | set(optional):
        raise ValueError("TRANSFER_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("TRANSFER_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _upstream(value):
    if type(value) is not str:
        raise ValueError("TRANSFER_UPSTREAM_LINE_REFERENCE")
    artifact, separator, line = value.rpartition("#")
    if not separator or not artifact or not line:
        raise ValueError("TRANSFER_UPSTREAM_LINE_REFERENCE")


def _state(value):
    _record(value, {"coordinator_id", "account_scopes", "purpose", "policy_id", "policy_revision", "boundary", "origin",
                    "source_case_id", "consumed_transfer_ids", "consumed_entitlement_ids", "consumed_authorization_ids",
                    "consumed_upstream_refs", "last_period"})
    result = deepcopy(value)
    for reference in value["consumed_upstream_refs"]:
        _upstream(reference)
    for last in result["last_period"]:
        _record(last, {"source_case_id", "period", "accounts", "entitlement_facts", "applied_transfers"})
        for row in last["accounts"]:
            for field in ["original_entitlement", "received_credit", "transferred_out", "final_entitlement"]:
                row[field] = money(_q(row[field]))
        # These are historical ORIGINAL source strings, not current funds.
        # Preserve their amount spelling instead of repricing or normalizing it.
        for row in last["entitlement_facts"]:
            _q(row["amount"])
            _upstream(row["upstream_result_ref"])
            row["source_observed_at"] = row["observed_at"]
        for row in last["applied_transfers"]:
            row["source_observed_at"] = row["observed_at"]
            for field in ["amount", "source_before", "source_after", "target_before", "target_after"]:
                row[field] = money(_q(row[field]))
            if type(row["sequence"]) is not int:
                raise ValueError("TRANSFER_AUTHORIZED_SEQUENCE")
            row["sequence"] = str(row["sequence"])
    return result


def neutral_state(value):
    """Decode tagged audit money and sequence metadata, without moving funds."""
    if isinstance(value, dict):
        if set(value) == {"value", "currency"}:
            if value["currency"] != "USD":
                raise ValueError("TRANSFER_CURRENCY")
            return str(exact(value["value"]))
        result = {key: neutral_state(item) for key, item in value.items()}
        if "source_observed_at" in result:
            result["observed_at"] = result.pop("source_observed_at")
        if "sequence" in result:
            result["sequence"] = int(exact(value["sequence"]))
        return result
    if isinstance(value, list):
        return [neutral_state(item) for item in value]
    return value


def register_transfers():
    reference = _descriptor("transfers", "transfers.spl", "policy.md",
        {"cutoff": "parameter", "policy": "parameter", "evidence": "evidence", "comparison": "result",
         "account_results": "detail", "applied_transfers": "detail", "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "history", "closing": "history", "purpose": "current_entitlement_transfers", "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "purpose"],
                "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:contract-transfers"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["source70-target30", "downstream-credit", "authorized-sequence", "current-only-carry"])
    for field in ["accounts", "entitlements", "authorizations", "transfers"]:
        descriptor["constraints"].append({"kind": "unique", "path": "inputs." + field,
            "fields": ["id"], "target": "", "value": ""})
    descriptor["constraints"].extend([
        {"kind": "unique", "path": "evidence.evidence", "fields": ["id"], "target": "", "value": ""},
        {"kind": "equals", "path": "inputs.coordinator.id", "fields": [], "target": "scope.agreement_id", "value": ""},
        {"kind": "equals", "path": "scope.pool_id", "fields": [], "target": "", "value": ENVELOPE_POOL},
        {"kind": "equals", "path": "inputs.scope.participant_id", "fields": [], "target": "", "value": OPERATOR}])
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def transfers_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _record(data, {"schema_version", "case_id", "coordinator", "period", "as_of", "cutoff", "policy", "accounts",
                   "entitlements", "authorizations", "transfers", "evidence", "opening_state"}, {"prior_result"})
    if data["schema_version"] != "transfers-neutral/1":
        raise ValueError("TRANSFER_NEUTRAL_SCHEMA")
    reference = reference or register_transfers()
    inputs = {"scope": {"agreement_id": data["coordinator"]["id"], "participant_id": OPERATOR,
                        "pool_id": ENVELOPE_POOL, "period": deepcopy(data["period"])},
              "case_id": data["case_id"], "coordinator": data["coordinator"], "as_of": data["as_of"],
              "accounts": data["accounts"], "supplied_opening": _state(data["opening_state"])}
    entitlements = []
    for original in data["entitlements"]:
        _record(original, {"id", "account_id", "scope", "amount", "effective_date", "observed_at", "source_ref", "upstream_result_ref", "evidence_ref"})
        _upstream(original["upstream_result_ref"])
        row = deepcopy(original)
        row["source_amount"], row["amount"] = original["amount"], money(_q(original["amount"]))
        row["source_observed_at"] = original["observed_at"]
        entitlements.append(row)
    inputs["entitlements"] = entitlements
    authorizations = []
    for original in data["authorizations"]:
        _record(original, {"id", "source_account", "target_account", "source_scope", "target_scope", "effective", "approved", "approved_date",
                           "recorded_date", "observed_at", "sequence", "maximum_amount", "source_ref", "evidence_ref"})
        if type(original["sequence"]) is not int:
            raise ValueError("TRANSFER_AUTHORIZED_SEQUENCE")
        row = deepcopy(original)
        row["maximum_amount"], row["sequence"] = money(_q(original["maximum_amount"])), str(original["sequence"])
        authorizations.append(row)
    inputs["authorizations"] = authorizations
    inputs["transfers"] = []
    for original in data["transfers"]:
        _record(original, {"id", "authorization_id", "source_account", "target_account", "source_scope", "target_scope", "amount",
                           "recognition_date", "observed_at", "source_ref", "evidence_ref"})
        row = deepcopy(original)
        row["amount"] = money(_q(row["amount"]))
        row["source_observed_at"] = original["observed_at"]
        inputs["transfers"].append(row)
    evidence = []
    for row in data["evidence"]:
        _record(row, {"id", "coordinator_id", "account_ids", "observed_at", "kind"})
        evidence.append({**deepcopy(row), "source_kind": row["kind"], "kind": "selected_synthetic_record",
                         "approval_ref": "TRANSFERS_SELECTED", "evidence_ref": row["id"]})
    frame_scope = {"agreement_id": data["coordinator"]["id"], "participant_id": OPERATOR, "pool_id": ENVELOPE_POOL}
    cell = {"opening_port": "history", "state_key": canonical({**frame_scope, "purpose": "current_entitlement_transfers"}),
            "purpose": "current_entitlement_transfers", "unit": "structured", "scope": frame_scope,
            "boundary": data["period"]["start"], "quantity": _state(data["opening_state"]),
            "provenance_ref": "supplied-coordinator-history", "scenario_id": "SYNTHETIC-CONTRACT-TRANSFERS"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if type(prior.get("result_ref")) is not str or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("TRANSFER_CANONICAL_PREDECESSOR_REQUIRED")
        cell["prior_result_ref"] = prior["result_ref"]
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
    else:
        inputs["predecessor"] = {"none": True}
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells):
        raise ValueError("TRANSFER_CANONICAL_PREDECESSOR_MISMATCH")
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-CONTRACT-TRANSFERS", "mode": "final",
            "period": data["period"], "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": data["coordinator"]["id"], "participant_ids": [OPERATOR],
                  "pool_id": ENVELOPE_POOL, "asset_ids": [], "purpose": "coordination_envelope_only"},
        "inputs": inputs, "parameters": {"cutoff": data["cutoff"], "policy": data["policy"]}, "evidence": {"evidence": evidence}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "explicit-endpoint-approvals"}
                      for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


if __name__ == "__main__":
    package = transfers_package(reference=register_transfers())
    package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
    write_json(FOLDER / "canonical-package.json", package)
