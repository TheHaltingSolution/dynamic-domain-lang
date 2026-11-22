"""Transport the neutral synthetic facts; economics are exclusively SPL source."""
from copy import deepcopy
from pathlib import Path
from fractions import Fraction
import re

from spl_compiler.codecs import canonical, fail, file_digest, number, read_json, write_json
from spl_compiler.modules import dimensioned_state_unit

ROOT = Path(__file__).resolve().parents[2]
PREFIX = "cases/quantities/"
DECISION = "QUANTITY-PARTICIPATION"


def _exact_transport(value):
    """Normalize neutral rational notation; perform no economic calculation."""
    if type(value) is int:
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"-?(?:0|[1-9][0-9]*)/[1-9][0-9]*", value):
        return number(Fraction(value))
    return deepcopy(value)


def typ(name, *args):
    return {"name": name, "args": list(args)}


def register_quantities():
    """Register only this new synthetic source and readable policy."""
    def pin(name):
        return {"locator": PREFIX + name, "sha256": file_digest(ROOT / PREFIX / name)}

    def port(name, role, type_, dimensions=(), domain=None):
        return {"name": name, "role": role, "type": type_, "dimensions": list(dimensions), "domain": domain or {}}

    quantity, rate, money = typ("Quantity", typ("Download")), typ("Rate", typ("Download"), typ("USD")), typ("Money", typ("USD"))
    usage = typ("List", typ("UsageRow"))
    ports = [port(name, "input", typ("Id", typ(kind)), [dimension]) for name, kind, dimension in
             [("agreement", "Agreement", "agreement"), ("participant", "Participant", "participant"),
              ("pool", "Pool", "pool"), ("asset", "Asset", "asset")]]
    ports += [port("accounting_period", "input", typ("Period"), ["period"]),
              port("observation_cutoff", "input", typ("Instant")), port("usage", "input", usage, ["unit", "period"]),
              port("attestations", "evidence", typ("List", typ("Attestation"))),
              port("unit_rate", "parameter", rate, ["unit", "currency"]),
              port("participation", "parameter", typ("Ratio"), domain={"minimum": "0", "maximum": "1"}),
              port("rounding", "parameter", typ("Text"), domain={"choices": ["exact_no_rounding"], "methodology": True}),
              port("quantity_policy", "parameter", typ("Text"), domain={"choices": ["nonnegative_selected_period"], "methodology": True}),
              port("meter", "opening", quantity, ["unit"]), port("earned", "result", money, ["currency"]),
              port("gross", "detail", money, ["currency"]), port("period_quantity", "detail", quantity, ["unit"]),
              port("usage_detail", "detail", usage, ["unit", "period"]), port("reconciliation", "reconciliation", typ("Bool"))]
    constraints = [{"kind": "unique", "path": "inputs.usage", "fields": ["record_id"], "target": "", "value": ""},
                   {"kind": "unique", "path": "evidence.attestations", "fields": ["evidence_id"], "target": "", "value": ""},
                   {"kind": "evidence", "path": "evidence.attestations", "fields": [], "target": "", "value": "usage_attestation", "required": False}]
    for path, target in [("inputs.accounting_period", "manifest.period"), ("inputs.observation_cutoff", "manifest.cutoff")]:
        constraints.append({"kind": "equals", "path": path, "fields": [], "target": target, "value": ""})
    descriptor = {"schema_version": "spl-module-descriptor/1", "id": "synthetic:download-participation", "revision": "1",
        "compatibility": {"surface": "spl/0.1-draft", "core": "spl-core/0.1-draft", "ir": "spl-ir/0.1", "package": "spl-module/1",
            "toolchain": "leanprover/lean4:v4.35.0", "codecs": ["spl-exact/1", "spl-instant/1", "spl-quantity/1"],
            "capabilities": ["spl.core/1", "spl.instant/1", "spl.quantities/1"]},
        "source": pin("download-participation.spl"), "imports": [],
        "interface": {"ports": ports, "exports": [], "dictionaries": {"spl.units/1": ["Download"]}, "schemas": [
            {"name": "UsageRow", "fields": {"record_id": typ("Id", typ("Usage")), "quantity": quantity,
                "effective_date": typ("Date"), "observed_at": typ("Instant"), "evidence_ref": typ("Text")}},
            {"name": "Attestation", "fields": {"evidence_id": typ("Text"), "observed_at": typ("Instant"),
                "approval_ref": typ("Id", typ("Decision")), "evidence_ref": typ("Text"), "kind": typ("Text")}}]},
        "policy": {"id": "synthetic:download-policy", "revision": "1", "readable": pin("policy.md"), "decision_ids": [DECISION],
            "evidence_class": "synthetic", "review_status": "proposed", "discriminating_cases": ["100x1.50x50%", "zero", "fractional", "unit-mismatch", "successor-carry"]},
        "constraints": constraints,
        "state": [{"opening": "meter", "closing": "meter", "purpose": "download-meter", "unit": dimensioned_state_unit(quantity),
            "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose", "unit"], "movement_kinds": ["transition"], "history_required": False}]}
    write_json(ROOT / PREFIX / "descriptor.json", descriptor)
    return {"id": descriptor["id"], "revision": descriptor["revision"], "locator": PREFIX + "descriptor.json",
            "sha256": file_digest(ROOT / PREFIX / "descriptor.json")}


def quantity_package(fixture=None, reference=None):
    data = deepcopy(fixture) if fixture is not None else read_json(ROOT / PREFIX / "neutral.json")
    if data["schema_version"] != "quantity-neutral/1":
        fail("Q_NEUTRAL_VERSION", "Expected quantity-neutral/1")
    scope, opening, terms = data["scope"], data["opening_state"], data["terms"]
    if scope["unit"] != "Download" or scope["currency"] != "USD":
        fail("Q_SCOPE_DIMENSION", "The selected source profile is Download/USD")
    if opening["scope"] != scope:
        fail("Q_OPENING_SCOPE", "Opening scope must exactly match the neutral scope")
    if any(row.get("scope", scope) != scope for row in data["usage"]):
        fail("Q_USAGE_SCOPE", "Supplied usage scopes must exactly match the selected scope")
    reference = reference or {"id": "synthetic:download-participation", "revision": "1", "locator": PREFIX + "descriptor.json",
                              "sha256": file_digest(ROOT / PREFIX / "descriptor.json")}
    unit = dimensioned_state_unit(typ("Quantity", typ("Download")))
    cell_scope = {"agreement_id": scope["contract_id"], "participant_id": scope["participant_id"], "pool_id": scope["pool_id"],
                  "asset_id": scope["asset_id"], "unit": unit}
    cell = {"state_key": canonical({**cell_scope, "purpose": "download-meter"}), "opening_port": "meter", "purpose": "download-meter",
            "unit": unit, "scope": cell_scope, "boundary": data["period"]["start"],
            "quantity": {"value": _exact_transport(opening["quantity"]), "unit": opening["unit"]}, "provenance_ref": "explicit-synthetic-opening",
            "scenario_id": "DOWNLOAD-SYNTHETIC"}
    return {"profile": "spl-module/1", "module_ref": deepcopy(reference),
        "manifest": {"run_id": data["case_id"], "scenario_id": "DOWNLOAD-SYNTHETIC", "mode": "final", "period": deepcopy(data["period"]),
            "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
            "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["contract_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"],
            "asset_ids": [scope["asset_id"]], "purpose": "download-meter"},
        "inputs": {"agreement": scope["contract_id"], "participant": scope["participant_id"], "pool": scope["pool_id"], "asset": scope["asset_id"],
            "accounting_period": deepcopy(data["period"]), "observation_cutoff": data["cutoff"], "usage": [
                {"record_id": row["record_id"], "quantity": {"value": _exact_transport(row["quantity"]), "unit": row["unit"]},
                 "effective_date": row["effective_date"], "observed_at": row["observed_at"], "evidence_ref": row["evidence_ref"]} for row in data["usage"]]},
        "parameters": {"unit_rate": {"value": _exact_transport(terms["rate"]), "per_unit": terms["per_unit"], "currency": terms["currency"]},
            "participation": _exact_transport(terms["participation"]), "rounding": terms["rounding"], "quantity_policy": terms["quantity_policy"]},
        "evidence": {"attestations": [{**row, "approval_ref": DECISION, "evidence_ref": row["evidence_id"], "kind": "usage_attestation"} for row in data["evidence"]]},
        "state_cells": [cell], "decisions": [{"decision_id": DECISION, "policy_id": "synthetic:download-policy", "policy_revision": "1",
            "status": "proposed", "evidence_ref": "explicit-synthetic-policy-selection"}]}


if __name__ == "__main__":
    write_json(ROOT / PREFIX / "package.json", quantity_package(reference=register_quantities()))
