"""Exact original-fact transport for separately authorized recovery.

No original gross, paid total, capacity, claim, priority or offset is solved here.
"""
from copy import deepcopy
from datetime import date
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, instant_utc_day, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-AUTHORIZED-OFFSETS-01"
ARRAY_KINDS = {"reversals": "reversal", "revision_authorities": "revision", "offset_authorities": "authority",
               "future_earnings": "earning", "cash_recoveries": "cash", "recovery_applications": "cash_application"}
BASE = {"id", "scope", "observed_at", "source_ref", "evidence_ref"}
EXTRA = {
    "original": {"basis", "rate", "measurement_date"},
    "issued": {"original_id", "amount", "issued_date"},
    "payment": {"issued_id", "amount", "paid_at", "disbursement_id"},
    "payment_application": {"payment_id", "issued_id", "amount"},
    "other": {"amount", "measurement_date", "origin_ref"},
    "revision": {"original_id", "issued_id", "effective", "approved", "approved_date", "recorded_date", "permitted_reversal_ids", "maximum_returned_basis"},
    "reversal": {"original_id", "revision_authority_id", "returned_basis", "return_date", "recognition_date"},
    "authority": {"claim_id", "kind", "origin_id", "amount", "priority", "sequence", "eligible_from", "effective", "approved", "approved_date", "recorded_date"},
    "earning": {"amount", "effective_date", "sequence", "upstream_ref"},
    "cash": {"receipt_id", "amount", "received_date", "received_at"},
    "cash_application": {"cash_id", "claim_id", "amount"}}
MONEY = {"original": ["basis"], "revision": ["maximum_returned_basis"], "reversal": ["returned_basis"]}
PAYMENT_CONTROL = {"issued_id", "as_of", "payment_ids", "disbursement_ids", "application_ids", "paid_total"}
CASH_CONTROL = {"period", "cash_ids", "receipt_ids", "application_ids", "cash_total"}
CLAIM_FIELDS = {"id", "kind", "origin_id", "authorized_amount", "priority", "sequence", "eligible_from", "authority_id", "authority_record", "actual_cash_recovered", "earning_offsets", "remaining"}


def _record(value, fields, optional=()):
    if type(value) is not dict or not set(fields) <= value.keys() or not value.keys() <= set(fields) | set(optional):
        raise ValueError("OFFSET_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("OFFSET_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _integer(value):
    if type(value) is not int:
        raise ValueError("OFFSET_EXPLICIT_INTEGER_REQUIRED")
    return str(value)


def _line(value):
    if type(value) is not str:
        raise ValueError("OFFSET_ORIGINAL_LINE_REFERENCE")
    artifact, marker, identity = value.rpartition("#")
    if not artifact or not marker or not identity:
        raise ValueError("OFFSET_ORIGINAL_LINE_REFERENCE")


def _opening_utc(period):
    value = period["start"]
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("OFFSET_DATE")
    date.fromisoformat(value)
    return value + "T00:00:00Z"


def _fact(original, kind):
    _record(original, BASE | EXTRA[kind])
    row = deepcopy(original)
    for field in MONEY.get(kind, ["amount"]):
        row["source_" + field], row[field] = original[field], money(_q(original[field]))
    if kind == "original":
        row["source_rate"], row["rate"] = original["rate"], number(_q(original["rate"]))
    for field in ["observed_at", "paid_at", "received_at"]:
        if field in original:
            row["source_" + field] = original[field]
    for field in ["priority", "sequence"]:
        if field in original:
            row[field] = _integer(original[field])
    if kind == "cash":
        row["received_utc_date"] = instant_utc_day(original["received_at"]).isoformat()
    for field in ["origin_ref", "upstream_ref"]:
        if field in original:
            _line(original[field])
    return row


def _bundle(original):
    _record(original, {"original", "issued", "payment_snapshot", "other_claims"})
    snapshot = original["payment_snapshot"]
    _record(snapshot, {"as_of", "payments", "applications", "evidence_ref"})
    return {"original": _fact(original["original"], "original"), "issued": _fact(original["issued"], "issued"),
        "payment_snapshot": {"as_of": snapshot["as_of"], "source_as_of": snapshot["as_of"], "evidence_ref": snapshot["evidence_ref"],
            "payments": [_fact(row, "payment") for row in snapshot["payments"]],
            "applications": [_fact(row, "payment_application") for row in snapshot["applications"]]},
        "other_claims": [_fact(row, "other") for row in original["other_claims"]]}


def _period_record(original):
    _record(original, {"source_case_id", "period", "as_of", "cutoff", *ARRAY_KINDS})
    return {"source_case_id": original["source_case_id"], "period": deepcopy(original["period"]), "as_of": original["as_of"],
        "cutoff": original["cutoff"], "source_cutoff": original["cutoff"], "opening_utc": _opening_utc(original["period"]),
        **{key: [_fact(row, kind) for row in original[key]] for key, kind in ARRAY_KINDS.items()}}


def _claim(original):
    _record(original, CLAIM_FIELDS)
    row = deepcopy(original)
    row["authority_record"] = _fact(original["authority_record"], "authority")
    for field in ["authorized_amount", "actual_cash_recovered", "earning_offsets", "remaining"]:
        row[field] = money(_q(original[field]))
    row["priority"], row["sequence"] = _integer(original["priority"]), _integer(original["sequence"])
    return row


def _state(original):
    _record(original, {"scope", "purpose", "policy_id", "policy_revision", "priority_recipe", "original_bundle", "boundary", "origin", "source_case_id", "returned_basis", "claims", "period_history"})
    return {**deepcopy(original), "original_bundle": _bundle(original["original_bundle"]), "returned_basis": money(_q(original["returned_basis"])),
            "claims": [_claim(row) for row in original["claims"]], "period_history": [_period_record(row) for row in original["period_history"]]}


def neutral_value(value):
    """Restore original lexical fields; decode accounting numbers without solving."""
    if isinstance(value, list):
        return [neutral_value(row) for row in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"value", "currency"}:
        if value["currency"] != "USD":
            raise ValueError("OFFSET_CURRENCY")
        return str(exact(value["value"]))
    row = {key: neutral_value(item) for key, item in value.items()}
    for field in ["basis", "rate", "amount", "returned_basis", "maximum_returned_basis", "observed_at", "paid_at", "received_at", "as_of", "cutoff"]:
        if "source_" + field in row:
            row[field] = row.pop("source_" + field)
    for field in ["priority", "sequence"]:
        if field in row:
            row[field] = int(exact(row[field]))
    row.pop("opening_utc", None)
    row.pop("received_utc_date", None)
    return row


neutral_state = neutral_value


def register_authorized_offsets():
    reference = _descriptor("authorized-offsets", "authorized-offsets.spl", "policy.md",
        {"policy": "parameter", "cutoff": "parameter", "evidence": "evidence", "comparison": "result", "claims": "detail",
         "earning_lines": "detail", "offset_lines": "detail", "period_replays": "detail", "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "history", "closing": "history", "purpose": "authorized_original_recovery", "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"], "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:authorized-offsets"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["immutable-paid80", "no-authority-pay30", "authorized20-pay10",
        "cash-before-offset", "two-explicit-priority-recipes", "prospective-source-capacity", "three-period-actual-carry"])
    for field in [*ARRAY_KINDS, "original_bundle.payment_snapshot.payments", "original_bundle.payment_snapshot.applications", "original_bundle.other_claims"]:
        descriptor["constraints"].append({"kind": "unique", "path": "inputs." + field, "fields": ["id"], "target": "", "value": ""})
    descriptor["constraints"].append({"kind": "unique", "path": "evidence.evidence", "fields": ["id"], "target": "", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def authorized_offset_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _record(data, {"schema_version", "case_id", "scope", "period", "as_of", "cutoff", "policy", "original_bundle", *ARRAY_KINDS, "evidence", "opening_state"}, {"prior_result"})
    if data["schema_version"] != "authorized-offsets-neutral/1":
        raise ValueError("OFFSET_NEUTRAL_SCHEMA")
    reference = reference or register_authorized_offsets()
    scope = data["scope"]
    frame = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    opening = _state(data["opening_state"])
    inputs = {"scope": {key: value for key, value in frame.items() if key != "asset_id"} | {"period": data["period"]},
        "project": scope["asset_id"], "fact_scope": scope, "case_id": data["case_id"], "as_of": data["as_of"],
        "source_cutoff": data["cutoff"], "opening_utc": _opening_utc(data["period"]), "original_bundle": _bundle(data["original_bundle"]),
        **{key: [_fact(row, kind) for row in data[key]] for key, kind in ARRAY_KINDS.items()},
        "supplied_opening": opening, "predecessor": {"none": True}}
    cell = {"opening_port": "history", "state_key": canonical({**frame, "purpose": "authorized_original_recovery"}),
        "purpose": "authorized_original_recovery", "unit": "structured", "scope": frame, "boundary": data["period"]["start"], "quantity": opening,
        "provenance_ref": "supplied-original-payment-and-recovery-history", "scenario_id": "SYNTHETIC-AUTHORIZED-OFFSETS"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if type(prior.get("result_ref")) is not str or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("OFFSET_CANONICAL_PREDECESSOR_REQUIRED")
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
        cell["prior_result_ref"] = prior["result_ref"]
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells):
        raise ValueError("OFFSET_CANONICAL_PREDECESSOR_MISMATCH")
    evidence = []
    for original in data["evidence"]:
        extra = PAYMENT_CONTROL if original["kind"] == "complete_original_payment_population" else CASH_CONTROL if original["kind"] == "complete_cash_recovery_population" else set()
        _record(original, {"id", "scope", "observed_at", "kind"} | extra)
        payment_population, cash_population = {"none": True}, {"none": True}
        if original["kind"] == "complete_original_payment_population":
            payment_population = {"some": {key: deepcopy(original[key]) for key in PAYMENT_CONTROL}}
            payment_population["some"].update(paid_total=money(_q(original["paid_total"])), source_as_of=original["as_of"])
        elif original["kind"] == "complete_cash_recovery_population":
            cash_population = {"some": {key: deepcopy(original[key]) for key in CASH_CONTROL}}
            cash_population["some"]["cash_total"] = money(_q(original["cash_total"]))
        evidence.append({key: deepcopy(original[key]) for key in ["id", "scope", "observed_at"]} | {
            "source_kind": original["kind"], "source_observed_at": original["observed_at"], "payment_population": payment_population,
            "cash_population": cash_population, "kind": "selected_synthetic_record", "approval_ref": "AUTHORIZED_OFFSETS_SELECTED", "evidence_ref": original["id"]})
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-AUTHORIZED-OFFSETS", "mode": "final", "period": data["period"],
            "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"],
                  "asset_ids": [scope["asset_id"]], "purpose": "authorized_original_recovery"},
        "inputs": inputs, "parameters": {"policy": data["policy"], "cutoff": data["cutoff"]}, "evidence": {"evidence": evidence}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "synthetic-authorized-offset-interpretation"}
                      for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def run_authorized_offset_package(package, registry_root=None, *, backend="compare", artifact_dir=None):
    return run_module_package(package, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir,
        blocked_evidence_labels={"OFFSET_PAYMENT_POPULATION_REQUIRED": {"payment_evidence_status": "no_event_supplied"},
                                 "OFFSET_RECOVERY_POPULATION_REQUIRED": {"recovery_evidence_status": "no_event_supplied"}})


if __name__ == "__main__":
    reference = register_authorized_offsets()
    for name in ["canonical-package.json", "no-authority-canonical-package.json"]:
        data = read_json(FOLDER / "neutral.json")
        if name.startswith("no-authority"):
            data["offset_authorities"] = []
        package = authorized_offset_package(data, reference=reference)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / name, package)
