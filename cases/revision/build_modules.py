"""Registration and mechanical transport; all restatement economics stay in SPL."""
from copy import deepcopy
from pathlib import Path

from cases.r1.build_modules import _descriptor, _pin, _q
from spl_compiler.codecs import canonical, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent


def register_revision():
    slots = [{"opening": name, "closing": name, "purpose": purpose, "unit": unit,
              "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"],
              "movement_kinds": ["net_change" if unit == "USD" else "transition"], "history_required": False}
             for name, purpose, unit in [("entitlement", "restated_affected_period_entitlement", "USD"),
                                         ("recognized", "restatement_recognition", "structured")]]
    reference = _descriptor("restatement", "restatement.spl", "policy.md",
        {"cutoff": "parameter", "rate": "parameter", "evidence": "evidence",
         "comparison": "result", "cash_control": "reconciliation"},
        state=slots, domains={"rate": {"minimum": "0", "maximum": "1"}}, folder=FOLDER)
    path = FOLDER / "restatement-module.json"
    descriptor = read_json(path)
    for field, target in [("provenance_ref", "inputs.original.opening_snapshot_id"),
                          ("scope.participant_id", "inputs.scope.participant_id"),
                          ("scope.asset_id", "inputs.project")]:
        descriptor["constraints"].append({"kind": "equals", "path": "state_cells", "fields": [field], "target": target, "value": ""})
    for section in ["original", "authorization", "payment"]:
        for field in ["agreement_id", "participant_id", "pool_id", "asset_id"]:
            descriptor["constraints"].append({"kind": "equals", "path": "inputs." + section + "." + field,
                "fields": [], "target": "inputs.project" if field == "asset_id" else "inputs.scope." + field, "value": ""})
    write_json(path, descriptor)
    return {"id": reference["id"], "revision": reference["revision"], **_pin(path)}


def revision_package(fixture=None, *, reference=None):
    fixture = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    policy = fixture["policy"]
    if any(policy[key] != value for key, value in {"route": "restatement_only", "rounding": "exact_no_rounding", "overpayment": "block"}.items()):
        raise ValueError("REV_UNSUPPORTED_POLICY")
    reference = reference or register_revision()
    scope = fixture["scope"]
    inputs = {name: deepcopy(fixture[name]) for name in ["original", "bank", "application", "authorization", "corrections", "payment"]}
    inputs.update(scope={"agreement_id": scope["agreement_id"], "participant_id": scope["participant_id"],
                         "pool_id": scope["pool_id"], "period": deepcopy(fixture["period"])}, project=scope["asset_id"])
    for row, fields in [(inputs["original"], ["issued", "opening_prepaid"]), (inputs["bank"], ["amount"]),
                        (inputs["application"], ["amount"]), (inputs["payment"], ["amount"]),
                        *[(row, ["amount", "reallocated_amount"]) for row in inputs["corrections"]]]:
        for field in fields:
            row[field] = money(_q(row[field]))
    decision = "RESTATEMENT_SELECTED"
    evidence = [{"evidence_id": row["id"], "observed_at": row["observed_at"], "approval_ref": decision,
                 "evidence_ref": row["id"], "kind": "selected_synthetic_record"} for row in fixture["evidence"]]
    cells = []
    for name, purpose, unit, quantity in [
            ("entitlement", "restated_affected_period_entitlement", "USD", number(_q(fixture["opening_entitlement"]))),
            ("recognized", "restatement_recognition", "structured", deepcopy(fixture["recognized"]))]:
        cells.append({"opening_port": name, "state_key": canonical({**scope, "purpose": purpose}),
            "purpose": purpose, "unit": unit, "scope": deepcopy(scope), "boundary": fixture["original"]["opening_boundary"],
            "quantity": quantity, "provenance_ref": fixture["original"]["opening_snapshot_id"], "scenario_id": fixture["case_id"]})
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": fixture["case_id"] + "-revision-run", "scenario_id": fixture["case_id"], "mode": "final",
            "period": deepcopy(fixture["period"]), "cutoff": fixture["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound",
            "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["agreement_id"], "participant_ids": [scope["participant_id"]],
                  "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": "authorized_synthetic_restatement"},
        "inputs": inputs, "parameters": {"cutoff": fixture["cutoff"], "rate": number(_q(policy["rate"]))},
        "evidence": {"evidence": evidence}, "state_cells": cells,
        "decisions": [{"decision_id": decision, "policy_id": "spl:policy:r1:restatement", "policy_revision": "1",
                       "status": "proposed", "evidence_ref": "selected-synthetic-CORR-01-policy"}]}
    return bind_module_package(package, ROOT)


if __name__ == "__main__":
    print(register_revision())
