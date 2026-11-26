"""Reversible original-fact transport; participation arithmetic executes in SPL."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import instant, money, number, quantity, rate, read_json, write_json
from spl_compiler.dimensions import UNIT_DICTIONARY
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-PARTICIPATION-BASES-01"
TRANSPORT = "participation-bases-original-json/1"
IDENTITY_CODEC = "unicode-utf8-hex/1"
METHODS = ("gross_percent", "net_percent", "unit_rate", "unit_rate_then_participation")
SCOPE = {"agreement_id", "participant_id", "asset_id", "pool_id", "currency"}
ROW = {"id", "original_ref", "source_ref", "scope", "effective_date", "observed_at", "amount"}


def record(value, names):
    if type(value) is not dict or set(value) != set(names): raise ValueError("BASE_RECORD_TRANSPORT")


def encode_identity(value):
    if type(value) is not str or not value or any(0xD800 <= ord(c) <= 0xDFFF for c in value): raise ValueError("BASE_TEXT_TRANSPORT")
    return value.encode("utf-8").hex()


def decode_identity(value):
    if type(value) is not str or not value or len(value) % 2 or not re.fullmatch(r"[0-9a-f]+", value): raise ValueError("BASE_IDENTITY_TRANSPORT")
    try: decoded = bytes.fromhex(value).decode("utf-8", errors="strict")
    except (UnicodeError, ValueError): raise ValueError("BASE_IDENTITY_TRANSPORT") from None
    if encode_identity(decoded) != value: raise ValueError("BASE_IDENTITY_TRANSPORT")
    return decoded


def original_number(value):
    if type(value) is not str or re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+|[0-9]+/[1-9][0-9]*)", value) is None: raise ValueError("BASE_EXACT_TRANSPORT")
    return Fraction(value)


def scope(value):
    record(value, SCOPE)
    return {key: item if key == "currency" else encode_identity(item) for key, item in value.items()}


def period(value):
    record(value, {"start", "end"})
    return deepcopy(value)


def stamp(value):
    # The selected policy compares known UTC instants. RFC3339 -00:00 retains
    # unknown LOCAL offset; preserve that metadata separately from UTC transport.
    physical = value[:-6] + "Z" if isinstance(value, str) and value.endswith("-00:00") else value
    return instant(physical).canonical


def original_json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def original_loads(value):
    # Original opaque Unicode is intentionally not subject to the generic
    # outer interface's NFC rule. Duplicate JSON keys remain inadmissible.
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result: raise ValueError("BASE_DUPLICATE_ORIGINAL_KEY")
            result[key] = item
        return result
    def constant(value): raise ValueError("BASE_ORIGINAL_JSON_CONSTANT")
    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)


def transport(data):
    record(data, {"case_id", "method", "scope", "period", "cutoff", "terms", "receipts", "deductions", "usage", "populations"})
    term = data["terms"]
    record(term, {"id", "source_ref", "scope", "approved", "effective", "observed_at", "percentage", "unit_rate", "unit", "participation_share"})
    result = {"case_id": encode_identity(data["case_id"]), "fact_scope": scope(data["scope"]), "accounting_period": period(data["period"]),
        "period_end_utc": stamp(data["period"]["end"] + "T00:00:00Z"),
        "terms": {"id": encode_identity(term["id"]), "source_ref": encode_identity(term["source_ref"]), "scope": scope(term["scope"]), "approved": term["approved"],
            "effective": period(term["effective"]), "observed_at": stamp(term["observed_at"]), "percentage": number(original_number(term["percentage"])),
            "unit_rate": rate(original_number(term["unit_rate"]), "Download"), "unit": term["unit"], "participation_share": number(original_number(term["participation_share"]))}}
    for kind in ("receipts", "deductions", "usage"):
        if type(data[kind]) is not list: raise ValueError("BASE_ROW_TRANSPORT")
        result[kind] = []
        for row in data[kind]:
            record(row, ROW)
            result[kind].append({"id": encode_identity(row["id"]), "original_ref": encode_identity(row["original_ref"]), "source_ref": encode_identity(row["source_ref"]),
                "scope": scope(row["scope"]), "effective_date": row["effective_date"], "effective_midnight": stamp(row["effective_date"] + "T00:00:00Z"),
                "observed_at": stamp(row["observed_at"]), "amount": quantity(original_number(row["amount"]), "Download") if kind == "usage" else money(original_number(row["amount"]))})
    if type(data["populations"]) is not list: raise ValueError("BASE_POPULATION_TRANSPORT")
    result["populations"] = []
    for population in data["populations"]:
        record(population, {"id", "source_ref", "scope", "kind", "period", "complete", "row_ids", "reported_total", "observed_at"})
        kind = population["kind"]
        if type(kind) is not str or kind not in {"receipts", "deductions", "usage"}: raise ValueError("BASE_POPULATION_KIND_TRANSPORT")
        if type(population["row_ids"]) is not list: raise ValueError("BASE_POPULATION_IDS_TRANSPORT")
        total = original_number(population["reported_total"])
        result["populations"].append({"id": encode_identity(population["id"]), "source_ref": encode_identity(population["source_ref"]), "scope": scope(population["scope"]),
            "kind": kind, "period": period(population["period"]), "complete": population["complete"], "row_ids": [encode_identity(identity) for identity in population["row_ids"]],
            "money_total": {"none": True} if kind == "usage" else {"some": money(total)},
            "quantity_total": {"some": quantity(total, "Download")} if kind == "usage" else {"none": True}, "observed_at": stamp(population["observed_at"])})
    timestamp_fields = [("cutoff", data["cutoff"]), ("terms.observed_at", term["observed_at"])]
    for kind in ("receipts", "deductions", "usage", "populations"):
        timestamp_fields.extend((f"{kind}.{position}.observed_at", row["observed_at"]) for position, row in enumerate(data[kind]))
    result["originals"] = {"profile": TRANSPORT, "identity_codec": IDENTITY_CODEC, "case_id": result["case_id"], "terms_id": result["terms"]["id"], "cutoff": stamp(data["cutoff"]),
        "unknown_local_offset_paths": [path for path, value in timestamp_fields if value.endswith("-00:00")],
        **{kind + "_ids": [row["id"] for row in result[kind]] for kind in ("receipts", "deductions", "usage", "populations")}, "raw_original": original_json(data)}
    return result


def validate_original_transport(inputs):
    original = original_loads(inputs["originals"]["raw_original"])
    if transport(original) != inputs: raise ValueError("BASE_TYPED_RAW_MISMATCH")


def validate_prepared_package(package):
    """Recheck custody correspondence at the public execution boundary."""
    original = original_loads(package["inputs"]["originals"]["raw_original"])
    facts = transport(original)
    work = facts["fact_scope"]
    expected_inputs = {**facts, "scope": {key: work[key] for key in ("agreement_id", "participant_id", "pool_id")} | {"period": original["period"]}, "project": work["asset_id"]}
    expected_scope = {"agreement_id": work["agreement_id"], "participant_ids": [work["participant_id"]], "pool_id": work["pool_id"], "asset_ids": [work["asset_id"]], "purpose": "stateless_participation_base"}
    if (package["inputs"] != expected_inputs or package["parameters"] != {"method": original["method"], "cutoff": stamp(original["cutoff"])} or
            package["scope"] != expected_scope or package["manifest"]["period"] != original["period"] or package["manifest"]["cutoff"] != stamp(original["cutoff"]) or
            package["state_cells"] != [] or package["evidence"] != {} or package["profile"] != "spl-module/1" or
            package["module_ref"]["id"] != "synthetic:participation-bases" or package["module_ref"]["revision"] != "1"):
        raise ValueError("BASE_PREPARED_PACKAGE_MISMATCH")


def neutral_result(value):
    def scalar(item):
        if isinstance(item, dict) and "value" in item: return scalar(item["value"])
        if isinstance(item, dict) and set(item) == {"numerator", "denominator"}: return str(Fraction(int(item["numerator"]), int(item["denominator"])))
        return str(original_number(item))
    monetary = value["selected_money_basis"]
    unit = value["selected_quantity_basis"]
    ratio = value["selected_percentage"]
    per_unit = value["selected_unit_rate"]
    if ("some" in monetary) == ("some" in unit) or ("some" in ratio) == ("some" in per_unit): raise ValueError("BASE_RESULT_DIMENSION")
    if ("some" in monetary) != ("some" in ratio): raise ValueError("BASE_RESULT_RATE_DIMENSION")
    result = {key: scalar(value[key]) for key in ("gross", "deductions", "net", "quantity", "pre_participation", "applied_participation", "earned")}
    result.update(case_id=decode_identity(value["case_id"]), method=value["method"], scope={key: item if key == "currency" else decode_identity(item) for key, item in value["scope"].items()},
        period=deepcopy(value["period"]), basis_measure="USD" if "some" in monetary else "Download", selected_basis=scalar(monetary["some"] if "some" in monetary else unit["some"]),
        selected_rate=scalar(ratio["some"] if "some" in ratio else per_unit["some"]), rate_measure="Ratio" if "some" in ratio else "USD/Download", issuance_status=value["issuance_status"])
    return result


def register_participation_bases():
    reference = _descriptor("participation-bases", "participation-bases.spl", "policy.md", {"method": "parameter", "cutoff": "parameter", "comparison": "result", "original_detail": "detail", "reconciliation": "reconciliation"},
        folder=FOLDER, capabilities=("spl.quantities/1",))
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:participation-bases"
    descriptor["compatibility"]["codecs"].append("spl-quantity/1")
    descriptor["interface"]["dictionaries"][UNIT_DICTIONARY] = ["Download"]
    descriptor["policy"].update(id=POLICY, discriminating_cases=[*METHODS, "money-quantity-asymmetry", "complete-unused-originals", "fractional-exact-no-rounding"])
    for field in ("agreement_id", "participant_id", "pool_id"):
        descriptor["constraints"].append({"kind": "member_of" if field == "participant_id" else "equals", "path": "inputs.fact_scope." + field,
            "fields": [], "target": "scope.participant_ids" if field == "participant_id" else "scope." + field, "value": ""})
    descriptor["constraints"].append({"kind": "equals", "path": "inputs.fact_scope.asset_id", "fields": [], "target": "inputs.project", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": descriptor["revision"], **_pin(path)}


def participation_base_package(fixture=None, *, reference=None, mode="final"):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    facts = transport(data)
    validate_original_transport(facts)
    reference = reference or register_participation_bases()
    work = facts["fact_scope"]
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": "participation-base-run", "scenario_id": "SYNTHETIC-PARTICIPATION-BASES", "mode": mode, "period": data["period"], "cutoff": stamp(data["cutoff"]),
            "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": work["agreement_id"], "participant_ids": [work["participant_id"]], "pool_id": work["pool_id"], "asset_ids": [work["asset_id"]], "purpose": "stateless_participation_base"},
        "inputs": {**facts, "scope": {key: work[key] for key in ("agreement_id", "participant_id", "pool_id")} | {"period": data["period"]}, "project": work["asset_id"]},
        "parameters": {"method": data["method"], "cutoff": stamp(data["cutoff"])}, "evidence": {}, "state_cells": [],
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-original-participation-policy"}
            for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def run_participation_base_package(package, registry_root=None, *, backend="compare", artifact_dir=None):
    snapshot = deepcopy(package)
    try:
        validate_prepared_package(snapshot)
    except (KeyError, TypeError, ValueError):
        # Preparation errors are a separate stage, before source evaluation.
        # Reused destinations still get a fresh atomic blocked completion.
        result = {"status": "blocked", "results": {}, "statements": [], "detail": [], "closing_state": [], "trace": [], "reconciliation": {}, "policy_review": {},
            "manifest": snapshot.get("manifest", {}) if isinstance(snapshot, dict) else {}, "issuance_status": "unissued", "payment_evidence_status": "not_assessed",
            "diagnostics": [{"code": "BASE_PREPARED_PACKAGE_MISMATCH", "message": "Canonical transport rejected bindings that differ from retained original facts", "pointer": "inputs.originals"}]}
        if artifact_dir is not None:
            from spl_compiler.artifacts import ArtifactPublication
            return ArtifactPublication(artifact_dir).finish(result, {"results.json": "results", "statement.json": "statements", "detail.json": "detail", "trace.json": "trace", "closing-state.json": "closing_state", "reconciliation.json": "reconciliation", "diagnostics.json": "diagnostics", "policy-review.json": "policy_review"})
        return result
    return run_module_package(snapshot, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir)


if __name__ == "__main__":
    reference = register_participation_bases()
    for method in METHODS:
        data = read_json(FOLDER / "neutral.json"); data["method"] = method
        package = participation_base_package(data, reference=reference)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / (method.replace("_", "-") + "-canonical-package.json"), package)
