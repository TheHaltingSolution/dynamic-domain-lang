"""Original term/funding transport; no entitlement or recovery calculation."""
from copy import deepcopy
from datetime import date
from fractions import Fraction
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, instant_utc_day, money, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-TERM-GUARANTEES-01"
METHODS = ["term_cap", "term_floor_at_end", "actual_funded_advance", "floor_cap_advance_including_topup",
           "floor_cap_advance_earned_only", "cap_floor_advance_including_topup", "cap_floor_advance_earned_only"]
MONEY_METERS = ["term_earned", "term_recognized_entitlement", "term_cap_consumed", "total_funded", "total_recovered", "prepayment"]
POPULATION_FIELDS = {"term_id", "period", "funding_ids", "disbursement_ids", "funded_total"}


def _record(value, fields, optional=()):
    if type(value) is not dict or not set(fields) <= value.keys() or not value.keys() <= set(fields) | set(optional):
        raise ValueError("TERM_RECORD_FIELDS")


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("TERM_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _utc_opening(period):
    value = period["start"]
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("TERM_DATE")
    date.fromisoformat(value)
    return value + "T00:00:00Z"


def _term(original):
    _record(original, {"id", "revision", "scope", "period", "floor", "cap", "recoupable_minimum_face", "approved_date", "recorded_date", "observed_at", "source_ref", "evidence_ref"})
    row = deepcopy(original)
    for key in ["floor", "cap", "recoupable_minimum_face"]:
        row["source_" + key], row[key] = original[key], money(_q(original[key]))
    row.update(source_observed_at=original["observed_at"], opening_utc=_utc_opening(original["period"]))
    return row


def _earning(original):
    _record(original, {"id", "term_id", "scope", "amount", "effective_date", "observed_at", "source_ref", "evidence_ref"})
    return {**deepcopy(original), "amount": money(_q(original["amount"])), "source_amount": original["amount"], "source_observed_at": original["observed_at"]}


def _funding(original):
    _record(original, {"id", "disbursement_id", "term_id", "scope", "amount", "funded_date", "funded_at", "observed_at", "approved", "source_ref", "evidence_ref"})
    return {**deepcopy(original), "amount": money(_q(original["amount"])), "source_amount": original["amount"],
            "source_observed_at": original["observed_at"], "source_funded_at": original["funded_at"],
            "funded_utc_date": instant_utc_day(original["funded_at"]).isoformat()}


def _state(original):
    _record(original, {"scope", "purpose", "policy_id", "policy_revision", "method", "cap_reduction_order", "term", "boundary", "origin", "source_case_id",
                       *MONEY_METERS, "term_closed", "period_history"})
    row = deepcopy(original)
    row["term"] = _term(original["term"])
    for key in MONEY_METERS:
        row[key] = money(_q(original[key]))
    row["period_history"] = []
    for record in original["period_history"]:
        _record(record, {"source_case_id", "period", "earnings", "fundings"})
        row["period_history"].append({**deepcopy(record), "earnings": [_earning(event) for event in record["earnings"]],
                                       "fundings": [_funding(event) for event in record["fundings"]]})
    return row


def neutral_value(value):
    """Remove exact-value/source transport tags, preserving original lexemes."""
    if isinstance(value, list):
        return [neutral_value(row) for row in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"value", "currency"}:
        if value["currency"] != "USD":
            raise ValueError("TERM_CURRENCY")
        return str(exact(value["value"]))
    row = {key: neutral_value(item) for key, item in value.items()}
    for key in ["amount", "floor", "cap", "recoupable_minimum_face", "observed_at", "funded_at"]:
        if "source_" + key in row:
            row[key] = row.pop("source_" + key)
    row.pop("opening_utc", None)
    row.pop("funded_utc_date", None)
    return row


neutral_state = neutral_value


def register_term_guarantees():
    reference = _descriptor("term-guarantees", "term-guarantees.spl", "policy.md",
        {"policy": "parameter", "cutoff": "parameter", "evidence": "evidence", "comparison": "result",
         "period_replays": "detail", "current_facts": "detail", "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "history", "closing": "history", "purpose": "term_guarantee_and_prepayment", "unit": "structured",
                "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"], "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:term-guarantees"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["seven-explicit-methods", "final-only-floor", "nonreset-term-cap",
        "actual-funding-not-face", "complete-empty-versus-missing", "original-history-meter-replay"])
    for field in ["earnings", "fundings"]:
        descriptor["constraints"].append({"kind": "unique", "path": "inputs." + field, "fields": ["id"], "target": "", "value": ""})
    descriptor["constraints"].append({"kind": "unique", "path": "evidence.evidence", "fields": ["id"], "target": "", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def term_guarantee_package(fixture=None, *, reference=None, state_cells=None):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _record(data, {"schema_version", "case_id", "scope", "period", "as_of", "cutoff", "policy", "term", "earnings", "fundings", "evidence", "opening_state"}, {"prior_result"})
    if data["schema_version"] != "term-guarantees-neutral/1":
        raise ValueError("TERM_NEUTRAL_SCHEMA")
    reference = reference or register_term_guarantees()
    scope = data["scope"]
    frame = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"], "asset_id": scope["asset_id"]}
    opening = _state(data["opening_state"])
    inputs = {"scope": {key: value for key, value in frame.items() if key != "asset_id"} | {"period": data["period"]},
        "project": scope["asset_id"], "fact_scope": scope, "case_id": data["case_id"], "as_of": data["as_of"], "term": _term(data["term"]),
        "earnings": [_earning(row) for row in data["earnings"]], "fundings": [_funding(row) for row in data["fundings"]],
        "supplied_opening": opening, "predecessor": {"none": True}}
    cell = {"opening_port": "history", "state_key": canonical({**frame, "purpose": "term_guarantee_and_prepayment"}), "purpose": "term_guarantee_and_prepayment",
        "unit": "structured", "scope": frame, "boundary": data["period"]["start"], "quantity": opening,
        "provenance_ref": "supplied-original-term-history", "scenario_id": "SYNTHETIC-TERM-GUARANTEES"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if type(prior.get("result_ref")) is not str or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("TERM_CANONICAL_PREDECESSOR_REQUIRED")
        inputs["predecessor"] = {"some": {"source_case_id": prior["source_case_id"], "period": prior["period"], "closing_state": _state(prior["closing_state"])}}
        cell["prior_result_ref"] = prior["result_ref"]
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells):
        raise ValueError("TERM_CANONICAL_PREDECESSOR_MISMATCH")
    evidence = []
    for original in data["evidence"]:
        _record(original, {"id", "scope", "observed_at", "kind"}, POPULATION_FIELDS)
        population = {"none": True}
        if original["kind"] == "complete_funding_population":
            if not POPULATION_FIELDS <= original.keys():
                raise ValueError("TERM_FUNDING_POPULATION_CONTROL")
            population = {"some": {key: deepcopy(original[key]) for key in POPULATION_FIELDS}}
            population["some"]["funded_total"] = money(_q(original["funded_total"]))
        elif POPULATION_FIELDS & original.keys():
            raise ValueError("TERM_RECORD_FIELDS")
        evidence.append({key: deepcopy(original[key]) for key in ["id", "scope", "observed_at"]} | {
            "source_kind": original["kind"], "source_observed_at": original["observed_at"], "population": population,
            "kind": "selected_synthetic_record", "approval_ref": "TERM_GUARANTEES_SELECTED", "evidence_ref": original["id"]})
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"] + "-run", "scenario_id": "SYNTHETIC-TERM-GUARANTEES", "mode": "final", "period": data["period"],
            "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"],
                  "asset_ids": [scope["asset_id"]], "purpose": "term_guarantee_and_prepayment"},
        "inputs": inputs, "parameters": {"policy": data["policy"], "cutoff": data["cutoff"]}, "evidence": {"evidence": evidence}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "synthetic-term-interpretation"}
                      for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def run_term_guarantee_package(package, registry_root=None, *, backend="compare", artifact_dir=None):
    """Label only missing funding completeness before generic atomic publication."""
    return run_module_package(package, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir,
        blocked_evidence_labels={"TERM_FUNDING_POPULATION_REQUIRED": {"funding_evidence_status": "no_event_supplied"}})


if __name__ == "__main__":
    reference = register_term_guarantees()
    for method in METHODS:
        data = read_json(FOLDER / "neutral.json")
        data["policy"]["method"] = data["opening_state"]["method"] = method
        floor_active = method == "term_floor_at_end" or method.startswith(("floor_cap_", "cap_floor_"))
        cap_active = method == "term_cap" or method.startswith(("floor_cap_", "cap_floor_"))
        advance = method == "actual_funded_advance" or method.startswith(("floor_cap_", "cap_floor_"))
        data["term"].update(floor="100" if floor_active else "0", cap="100" if method == "term_cap" else "90" if cap_active else "0",
                            recoupable_minimum_face="150" if advance else "0")
        data["opening_state"]["term"] = deepcopy(data["term"])
        if not advance:
            data["fundings"] = []
            data["evidence"] = [row for row in data["evidence"] if row["kind"] not in ["complete_funding_population", "actual_advance_funding"]]
        package = term_guarantee_package(data, reference=reference)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / (method.replace("_", "-") + "-canonical-package.json"), package)
        if method == "actual_funded_advance":
            write_json(FOLDER / "canonical-package.json", package)
