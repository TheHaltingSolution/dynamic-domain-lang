"""Lossless supplied-policy/original-basis transport; economic arithmetic is SPL.

The fixed default dates are explicit canonical execution metadata. Original
numeric facts have no economic period and no result depends on these dates.
"""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, instant, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
PROFILE = "numeric-precision-original-json/1"
CODEC = "unicode-utf8-hex/1"
POLICY = "SYNTHETIC-NUMERIC-PRECISION-01"
PURPOSE = "numeric_precision_statement"
DEFAULT_PERIOD = {"start": "2026-01-01", "end": "2026-01-02"}
DEFAULT_CUTOFF = "2026-01-03T00:00:00Z"
SCOPE = {"agreement_id", "participant_id", "pool_id", "asset_id", "currency"}
POLICY_FIELDS = {"id", "revision", "evidence_class", "ratio_expression_id", "ratio_expression_unit", "ratio_expressed_decimal_places",
                 "ratio_quantum", "ratio_mode", "ratio_point", "money_quantum", "money_mode", "money_point", "bridge", "arithmetic"}


def _record(value, keys):
    if type(value) is not dict or value.keys() != set(keys):
        raise ValueError("PRECISION_FIELDS")


def _text(value):
    if type(value) is not str or not value or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError("PRECISION_TEXT")
    return value


def encode_identity(value):
    return _text(value).encode("utf-8").hex()


def decode_identity(value):
    if type(value) is not str or not value or len(value) % 2 or not re.fullmatch(r"[0-9a-f]+", value):
        raise ValueError("PRECISION_IDENTITY_TRANSPORT")
    try:
        original = bytes.fromhex(value).decode("utf-8", errors="strict")
    except (ValueError, UnicodeError):
        raise ValueError("PRECISION_IDENTITY_TRANSPORT") from None
    if encode_identity(original) != value:
        raise ValueError("PRECISION_IDENTITY_TRANSPORT")
    return original


def _numeric(value):
    if type(value) is str:
        if not re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
            raise ValueError("PRECISION_EXACT_NUMBER")
        return Fraction(value)
    _record(value, {"numerator", "denominator"})
    numerator, denominator = value["numerator"], value["denominator"]
    if (type(numerator) is not str or not re.fullmatch(r"-?(?:0|[1-9][0-9]*)", numerator) or
            type(denominator) is not str or not re.fullmatch(r"[1-9][0-9]*", denominator)):
        raise ValueError("PRECISION_EXACT_NUMBER")
    parsed = Fraction(int(numerator), int(denominator))
    if str(parsed.numerator) != numerator or str(parsed.denominator) != denominator:
        raise ValueError("PRECISION_NORMALIZED_FRACTION")
    return parsed


def _monetary(value, code):
    if type(value) is not dict or value.get("dimension") != "Money":
        raise ValueError(code)
    _record(value, {"dimension", "currency", "value"})
    if value["currency"] != "USD":
        raise ValueError("PRECISION_CURRENCY")
    return money(_numeric(value["value"]))


def _raw(value):
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)
    if json.loads(raw) != value:
        raise ValueError("PRECISION_RAW_TRANSPORT")
    return raw


def _unraw(value):
    def reject(_):
        raise ValueError("PRECISION_RAW_TRANSPORT")
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("PRECISION_RAW_TRANSPORT")
            result[key] = item
        return result
    if type(value) is not str:
        raise ValueError("PRECISION_RAW_TRANSPORT")
    original = json.loads(value, parse_float=reject, parse_constant=reject, object_pairs_hook=pairs)
    if _raw(original) != value:
        raise ValueError("PRECISION_RAW_TRANSPORT")
    return original


def _scope(value):
    _record(value, SCOPE)
    if value["currency"] != "USD":
        raise ValueError("PRECISION_CURRENCY")
    return {key: item if key == "currency" else encode_identity(item) for key, item in value.items()}


def transport(data):
    """Decode exact supplied values; do not calculate scales, rounds or earnings."""
    _record(data, {"schema_version", "case_id", "scope", "policy", "policy_ref", "ratio_expression", "lines", "population"})
    if data["schema_version"] != "numeric-precision-neutral/1":
        raise ValueError("PRECISION_SCHEMA")
    selected = data["policy"]
    _record(selected, POLICY_FIELDS)
    typed_policy = {key: _text(selected[key]) for key in ["evidence_class", "ratio_expression_unit", "ratio_mode", "ratio_point", "money_mode", "money_point", "bridge", "arithmetic"]}
    for key in ["id", "revision", "ratio_expression_id"]:
        typed_policy[key] = encode_identity(selected[key])
    places = selected["ratio_expressed_decimal_places"]
    if type(places) is not int:
        raise ValueError("PRECISION_EXPRESSION_PRECISION")
    typed_policy["ratio_expressed_decimal_places"] = number(places)
    ratio_quantum = selected["ratio_quantum"]
    if type(ratio_quantum) is not dict or ratio_quantum.get("dimension") != "Ratio":
        raise ValueError("PRECISION_RATIO_QUANTUM_DIMENSION")
    _record(ratio_quantum, {"dimension", "value"})
    typed_policy["ratio_quantum"] = number(_numeric(ratio_quantum["value"]))
    typed_policy["money_quantum"] = _monetary(selected["money_quantum"], "PRECISION_MONEY_QUANTUM_DIMENSION")
    reference = data["policy_ref"]
    _record(reference, {"id", "revision", "sha256"})
    if type(reference["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", reference["sha256"]):
        raise ValueError("PRECISION_POLICY_PIN")
    typed_reference = {"id": encode_identity(reference["id"]), "revision": encode_identity(reference["revision"]), "sha256": reference["sha256"]}
    expression = data["ratio_expression"]
    _record(expression, {"id", "scope", "original_ref", "source_ref", "expressed_unit", "expressed_value"})
    typed_expression = {key: encode_identity(expression[key]) for key in ["id", "original_ref", "source_ref"]}
    typed_expression.update(scope=_scope(expression["scope"]), expressed_unit=_text(expression["expressed_unit"]), expressed_value=number(_numeric(expression["expressed_value"])))
    if type(data["lines"]) is not list:
        raise ValueError("PRECISION_FIELDS")
    lines, originals = [], []
    for row in data["lines"]:
        _record(row, {"id", "scope", "original_ref", "source_ref", "basis", "ratio_expression_id"})
        item = {key: encode_identity(row[key]) for key in ["id", "original_ref", "source_ref", "ratio_expression_id"]}
        item.update(scope=_scope(row["scope"]), basis=_monetary(row["basis"], "PRECISION_BASIS_DIMENSION"))
        lines.append(item); originals.append({"id": item["id"], "raw_original": _raw(row)})
    pop = data["population"]
    _record(pop, {"id", "scope", "source_ref", "complete", "row_ids", "basis_total"})
    if type(pop["complete"]) is not bool or type(pop["row_ids"]) is not list:
        raise ValueError("PRECISION_COMPLETE_POPULATION")
    population = {"id": encode_identity(pop["id"]), "scope": _scope(pop["scope"]), "source_ref": encode_identity(pop["source_ref"]), "complete": pop["complete"],
                  "row_ids": [encode_identity(item) for item in pop["row_ids"]], "basis_total": _monetary(pop["basis_total"], "PRECISION_BASIS_DIMENSION")}
    policy_json = _raw(selected)
    return {"case_id": encode_identity(data["case_id"]), "fact_scope": _scope(data["scope"]), "selected": typed_policy, "policy_ref": typed_reference,
        "expression": typed_expression, "lines": lines, "population": population,
        "originals": {"profile": PROFILE, "identity_codec": CODEC, "case_id": encode_identity(data["case_id"]), "document": _raw(data)},
        "original_policy": {"id": typed_policy["id"], "revision": typed_policy["revision"], "sha256": sha256(policy_json.encode("utf-8")).hexdigest(), "raw_original": policy_json},
        "original_expression": {"id": typed_expression["id"], "raw_original": _raw(expression)}, "original_lines": originals,
        "original_population": {"id": population["id"], "raw_original": _raw(pop)}}


def _named(name, *args):
    return {"name": name, "args": list(args)}


def register_all():
    refs = {}
    for name, typ in [("ratio-rounding", _named("Ratio")), ("money-rounding", _named("Money", _named("USD")))]:
        reference = _descriptor(name, name + ".spl", "policy.md", {}, folder=FOLDER, exports=[{"name": "round", "definition": "rounded",
            "parameters": [{"name": "value", "type": typ}, {"name": "quantum", "type": typ}, {"name": "mode", "type": _named("Text")}], "result": typ}])
        path = ROOT / reference["locator"]; descriptor = read_json(path); descriptor["id"] = "synthetic:numeric-" + name
        write_json(path, descriptor); refs[name] = {"id": descriptor["id"], "revision": "1", **_pin(path)}
    reference = _descriptor("numeric-precision", "numeric-precision.spl", "policy.md", {"cutoff": "parameter", "comparison": "result", "reconciliation": "reconciliation"}, folder=FOLDER,
        imports=[{"module_ref": refs[name], "alias": alias, "symbols": [{"export": "round", "local": local}]} for name, alias, local in
                 [("ratio-rounding", "ratio_rounding", "round_ratio"), ("money-rounding", "money_rounding", "round_money")]])
    path = ROOT / reference["locator"]; descriptor = read_json(path); descriptor["id"] = "synthetic:numeric-precision"; descriptor["policy"]["id"] = POLICY
    for key in ["agreement_id", "participant_id", "pool_id"]:
        descriptor["constraints"].append({"kind": "member_of" if key == "participant_id" else "equals", "path": "inputs.fact_scope." + key, "fields": [],
            "target": "scope." + ("participant_ids" if key == "participant_id" else key), "value": ""})
    descriptor["constraints"].append({"kind": "equals", "path": "inputs.fact_scope.asset_id", "fields": [], "target": "inputs.project", "value": ""})
    descriptor["policy"]["discriminating_cases"] = ["ratio-percent-fraction-precision", "five-signed-literal-modes", "row-aggregate-half-cent-bridges", "original-exact-policy-pin"]
    write_json(path, descriptor); refs["numeric-precision"] = {"id": descriptor["id"], "revision": "1", **_pin(path)}
    return refs


def numeric_precision_package(data=None, *, reference=None, scenario="money_half_even_row", mode="final", period=None, cutoff=DEFAULT_CUTOFF):
    original = deepcopy(read_json(FOLDER / "neutral.json")["scenarios"][scenario] if data is None else data)
    if mode not in {"final", "preview"}:
        raise ValueError("PRECISION_EXECUTION_MODE")
    facts = transport(original)
    reference = reference or register_all()["numeric-precision"]
    period = deepcopy(DEFAULT_PERIOD if period is None else period)
    _record(period, {"start", "end"}); stamp = instant(cutoff).canonical
    work = facts["fact_scope"]
    inputs = {**facts, "scope": {key: work[key] for key in ["agreement_id", "participant_id", "pool_id"]} | {"period": period}, "project": work["asset_id"]}
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": "numeric-precision-run", "scenario_id": facts["case_id"], "mode": mode, "period": period, "cutoff": stamp,
                     "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": work["agreement_id"], "participant_ids": [work["participant_id"]], "pool_id": work["pool_id"], "asset_ids": [work["asset_id"]], "purpose": PURPOSE},
        "inputs": inputs, "parameters": {"cutoff": stamp}, "evidence": {}, "state_cells": [],
        "decisions": [{"decision_id": decision, "policy_id": entry["descriptor"]["policy"]["id"], "policy_revision": entry["descriptor"]["policy"]["revision"],
                       "status": "proposed", "evidence_ref": "supplied-synthetic-numeric-profile"} for entry in resolve_module(reference, ROOT).closure for decision in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def validate_prepared_package(package):
    original = _unraw(package["inputs"]["originals"]["document"])
    facts = transport(original); work = facts["fact_scope"]
    expected = {**facts, "scope": {key: work[key] for key in ["agreement_id", "participant_id", "pool_id"]} | {"period": package["manifest"]["period"]}, "project": work["asset_id"]}
    outer = {"agreement_id": work["agreement_id"], "participant_ids": [work["participant_id"]], "pool_id": work["pool_id"], "asset_ids": [work["asset_id"]], "purpose": PURPOSE}
    if (package["inputs"] != expected or package["parameters"] != {"cutoff": instant(package["manifest"]["cutoff"]).canonical} or package["scope"] != outer or
            package["state_cells"] != [] or package["evidence"] != {} or package["profile"] != "spl-module/1" or
            package["manifest"]["scenario_id"] != facts["case_id"] or package["manifest"]["mode"] not in {"final", "preview"} or
            package["module_ref"]["id"] != "synthetic:numeric-precision" or package["module_ref"]["revision"] != "1"):
        raise ValueError("PRECISION_PREPARED_PACKAGE_MISMATCH")


def run_numeric_precision_package(package, registry_root=None, *, backend="compare", artifact_dir=None, audit_profile="array-v1"):
    from spl_compiler.artifacts import ArtifactPublication, PublicationError
    from spl_compiler.audited_artifacts import AuditedPublication, unavailable_trace
    from spl_compiler.compact_execution import require_profile
    try:
        require_profile(audit_profile, backend, artifact_dir)
    except BaseException:
        if artifact_dir is not None: (AuditedPublication if audit_profile == "compact-v2" else ArtifactPublication)(artifact_dir)
        raise
    snapshot = None
    try:
        snapshot = deepcopy(package); validate_prepared_package(snapshot)
    except (KeyError, IndexError, TypeError, ValueError, OverflowError, PublicationError):
        result = {"status": "blocked", "results": {}, "statements": [], "detail": [], "closing_state": [], "trace": unavailable_trace() if audit_profile == "compact-v2" else [],
            "reconciliation": {}, "policy_review": {}, "manifest": snapshot.get("manifest", {}) if type(snapshot) is dict else {}, "issuance_status": "unissued", "payment_evidence_status": "not_assessed",
            "diagnostics": [{"code": "PRECISION_PREPARED_PACKAGE_MISMATCH", "message": "Prepared typed values do not match complete retained numeric originals"}]}
        if artifact_dir is not None:
            return (AuditedPublication if audit_profile == "compact-v2" else ArtifactPublication)(artifact_dir).finish(result,
                {"results.json": "results", "statement.json": "statements", "detail.json": "detail", "trace.json": "trace", "closing-state.json": "closing_state", "reconciliation.json": "reconciliation", "diagnostics.json": "diagnostics", "policy-review.json": "policy_review"})
        return result
    except BaseException:
        if artifact_dir is not None: (AuditedPublication if audit_profile == "compact-v2" else ArtifactPublication)(artifact_dir)
        raise
    return run_module_package(snapshot, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir, audit_profile=audit_profile)


def neutral_result(value, key=""):
    if key in {"original", "policy", "population"} and isinstance(value, str):
        return _unraw(value)
    if key in {"case_id", "id", "revision", "agreement_id", "participant_id", "pool_id", "asset_id"}:
        return decode_identity(value)
    if key == "source_row_ids":
        return [decode_identity(item) for item in value]
    if isinstance(value, dict) and set(value) in [{"value", "currency"}, {"numerator", "denominator"}]:
        return str(exact(value["value"] if "currency" in value else value))
    if isinstance(value, list):
        return [neutral_result(item) for item in value]
    if isinstance(value, dict):
        return {name: neutral_result(item, name) for name, item in value.items()}
    if key == "declared_decimal_places":
        parsed = exact(value)
        if parsed.denominator != 1: raise ValueError("PRECISION_PLACES_TRANSPORT")
        return parsed.numerator
    # Exact scalar numeric strings occur only in the declared numerical fields.
    numeric_fields = {"expressed_exact", "exact_ratio", "ratio_quantum", "rounded_ratio", "ratio_rounding_delta", "exact_original_ratio", "selected_ratio",
        "basis", "exact_before_ratio_rounding", "exact_after_ratio_rounding", "ratio_rounding_effect", "displayed_rounded", "money_rounding_delta",
        "original_basis_total", "ratio_rounding_effect_total", "sum_rounded_detail", "aggregate_rounded_control", "money_quantum", "selected_total", "total_adjustment", "rounding_bridge"}
    if key in numeric_fields:
        return str(exact(value))
    return value


if __name__ == "__main__":
    reference = register_all()["numeric-precision"]
    for scenario in read_json(FOLDER / "neutral.json")["scenarios"]:
        for mode, suffix in [("final", ""), ("preview", "-preview")]:
            package = numeric_precision_package(reference=reference, scenario=scenario, mode=mode)
            package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
            write_json(FOLDER / (scenario.replace("_", "-") + suffix + "-package.json"), package)
