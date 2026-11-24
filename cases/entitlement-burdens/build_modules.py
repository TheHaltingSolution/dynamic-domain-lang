"""Lossless original-record transport for the selected entitlement burden.

Scope, term/evidence selection, original participation/payment measurements,
graph checks, cap replay and financial results are calculated in SPL.
"""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, instant, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-CONTRACT-BURDENS-01"
PURPOSE = "cross_contract_entitlement_burden"
TRANSPORT = "entitlement-burdens-original-json/5"
IDENTITY_CODEC = "unicode-utf8-hex/1"
ENVELOPE = "entitlement-burden-execution"
OPERATOR = "coordinator-reader"
POOL = "coordinator-execution"
ARRAYS = ["accounts", "terms", "receipts", "authorizations", "requests", "payments", "applications", "receipt_populations", "payment_populations", "evidence"]
STATIC = ["accounts", "terms", "authorizations"]
FRAME = {"case_id", "period", "as_of", "cutoff", *ARRAYS}
BASE = {"id", "observed_at", "source_ref", "evidence_ref"}
FIELDS = {
    "accounts": BASE | {"scope"},
    "terms": BASE | {"account_id", "scope", "share", "effective", "approved", "approved_date", "original_ref"},
    "receipts": BASE | {"account_id", "scope", "amount", "term_id", "effective_date", "original_ref", "entitlement_line_ref"},
    "authorizations": BASE | {"claimant_account", "burdened_account", "claimant_scope", "burdened_scope", "purpose", "basis_kind", "burden_rate", "minimum_basis", "cap", "sequence", "effective", "approved", "approved_date", "recorded_date", "original_ref"},
    "requests": BASE | {"authorization_id", "claimant_account", "burdened_account", "claimant_scope", "burdened_scope", "measurement_id", "basis_receipt_ids", "recognition_date", "original_ref"},
    "payments": BASE | {"account_id", "scope", "amount", "purpose", "paid_at", "original_ref"},
    "applications": BASE | {"account_id", "scope", "payment_id", "receipt_id", "entitlement_line_ref", "amount", "approved", "application_date"},
    "receipt_populations": BASE | {"account_id", "scope", "period", "complete", "receipt_ids", "gross_total"},
    "payment_populations": BASE | {"account_id", "scope", "period", "complete", "payment_ids", "application_ids", "paid_total"},
    "evidence": {"id", "coordinator_id", "account_ids", "kind", "approved", "observed_at", "source_ref"},
}
SCOPE = {"agreement_id", "participant_id", "pool_id", "asset_id", "currency"}
ID_FIELDS = {"id", "account_id", "term_id", "authorization_id", "claimant_account", "burdened_account", "measurement_id", "payment_id", "receipt_id", "coordinator_id", "original_ref", "entitlement_line_ref", "source_ref", "evidence_ref", "source_case_id", "case_id"}
ID_LISTS = {"account_ids", "basis_receipt_ids", "receipt_ids", "payment_ids", "application_ids"}
MONEY = {"amount", "minimum_basis", "cap", "gross_total", "paid_total"}
RATIOS = {"share", "burden_rate"}
DATES = {"approved_date", "recorded_date", "effective_date", "recognition_date", "application_date"}
KINDS = ["receipt_ids", "receipt_refs", "entitlement_refs", "payment_ids", "payment_refs", "application_ids", "request_ids", "request_refs", "semantic_keys"]
ACCOUNT_MONEY = {"original_gross_basis", "original_accrued", "burden_applied", "adjusted_entitlement", "claimant_credit_added"}
BURDEN_MONEY = {"source_original_accrued", "basis", "minimum_basis", "requested", "cap_limit", "cap_opening_consumed", "cap_remaining_before", "applied", "cap_excess_not_carried", "cap_consumed_after", "cap_remaining_after", "target_before", "target_after", "claimant_credit_added"}


def _record(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() <= set(required) | set(optional):
        raise ValueError("BURDEN_RECORD_FIELDS")


def encode_identity(value):
    if type(value) is not str or not value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("BURDEN_TEXT_IDENTITY")
    return value.encode("utf-8").hex()


def decode_identity(value):
    if type(value) is not str or not value or len(value) % 2 or not re.fullmatch(r"[0-9a-f]+", value):
        raise ValueError("BURDEN_IDENTITY_TRANSPORT")
    try:
        original = bytes.fromhex(value).decode("utf-8", errors="strict")
    except (ValueError, UnicodeError):
        raise ValueError("BURDEN_IDENTITY_TRANSPORT") from None
    if encode_identity(original) != value:
        raise ValueError("BURDEN_IDENTITY_TRANSPORT")
    return original


def _q(value):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value):
        raise ValueError("BURDEN_EXACT_NONNEGATIVE")
    return Fraction(value)


def _midnight(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("BURDEN_DATE")
    date.fromisoformat(value)
    return value + "T00:00:00Z"


def _raw(value):
    # ASCII escaping preserves decomposed Unicode inside a canonical NFC Text.
    payload = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if json.loads(payload) != value:
        raise ValueError("BURDEN_ORIGINAL_JSON_TRANSPORT")
    return payload


def _scope(value):
    _record(value, SCOPE)
    return {key: value[key] if key == "currency" else encode_identity(value[key]) for key in value}


def _fact(original, kind, slots=None):
    _record(original, FIELDS[kind])
    row = deepcopy(original)
    for key in ["original_ref", "entitlement_line_ref"]:
        if key in row:
            before, marker, after = row[key].rpartition("#")
            if not (before and marker and after):
                raise ValueError("BURDEN_ORIGINAL_LINE_REFERENCE")
    for key in ID_FIELDS & row.keys():
        row[key] = encode_identity(original[key])
    for key in ID_LISTS & row.keys():
        if type(original[key]) is not list:
            raise ValueError("BURDEN_POPULATION_IDS")
        row[key] = [encode_identity(item) for item in original[key]]
    for key in ["scope", "claimant_scope", "burdened_scope"]:
        if key in row:
            row[key] = _scope(original[key])
    for key in MONEY | RATIOS:
        if key in row:
            row["source_" + key] = original[key]
            row[key] = money(_q(original[key])) if key in MONEY else number(_q(original[key]))
    if "sequence" in row:
        if type(original["sequence"]) is not int:
            raise ValueError("BURDEN_AUTHORIZED_SEQUENCE")
        row["sequence"] = number(original["sequence"])
    for key in DATES & row.keys():
        row[key + "_utc"] = _midnight(original[key])
    for key in ["effective", "period"]:
        if key in row:
            _record(original[key], {"start", "end"})
            row[key + "_start_utc"] = _midnight(original[key]["start"])
            row[key + "_end_utc"] = _midnight(original[key]["end"])
    for key in ["observed_at", "paid_at"]:
        if key in row:
            instant(original[key])
            row["source_" + key] = original[key]
    if "paid_at" in row:
        row["paid_utc_date"] = instant(original["paid_at"]).canonical[:10]
        row["paid_utc_midnight"] = _midnight(row["paid_utc_date"])
    positions = slots or {}
    row["slot" if kind == "evidence" else "evidence_slot"] = number(positions.get(original["id"] if kind == "evidence" else original["evidence_ref"], -1))
    row["raw_original"] = _raw(original)
    if neutral_fact(row) != original:
        raise ValueError("BURDEN_TYPED_ORIGINAL_TRANSPORT")
    return row


def neutral_fact(value):
    result = {}
    for key, item in value.items():
        if key in {"raw_original", "slot", "evidence_slot", "paid_utc_date", "paid_utc_midnight"} or key.endswith("_utc"):
            continue
        if key in ID_FIELDS:
            result[key] = decode_identity(item)
        elif key in ID_LISTS:
            result[key] = [decode_identity(identity) for identity in item]
        elif key in {"scope", "claimant_scope", "burdened_scope"}:
            result[key] = {name: scalar if name == "currency" else decode_identity(scalar) for name, scalar in item.items()}
        elif key in MONEY | RATIOS:
            continue  # Exact ORIGINAL numeric spelling is restored below.
        elif key == "sequence":
            result[key] = int(exact(item))
        elif key.startswith("source_") and key[7:] in MONEY | RATIOS | {"observed_at", "paid_at"}:
            result[key[7:]] = item
        else:
            result[key] = deepcopy(item)
    if "raw_original" in value and json.loads(value["raw_original"]) != result:
        raise ValueError("BURDEN_TYPED_RAW_MISMATCH")
    return result


def _frame(original):
    _record(original, FRAME)
    positions = {row["id"]: index for index, row in enumerate(original["evidence"])}
    row = {"id": encode_identity(original["case_id"]), "period": deepcopy(original["period"]), "as_of": original["as_of"],
           "as_of_next": (date.fromisoformat(original["as_of"]) + timedelta(days=1)).isoformat(), "cutoff": original["cutoff"],
           "period_end_utc": _midnight(original["period"]["end"]), "raw_original": _raw(original)}
    instant(original["cutoff"])
    row["originals"] = {}
    for key in ARRAYS:
        if type(original[key]) is not list:
            raise ValueError("BURDEN_FINITE_RECORDS")
        transported = [_fact(item, key, positions) for item in original[key]]
        row[key] = [{name: value for name, value in item.items() if name != "raw_original"} for item in transported]
        row["originals"][key] = [{"id": item["id"], "raw_original": item["raw_original"], **({"slot": item["slot"]} if key == "evidence" else {})} for item in transported]
    return row


def _semantic(original):
    if type(original) not in {list, tuple} or len(original) != 5 or len(original[1]) != 5:
        raise ValueError("BURDEN_SEMANTIC_KEY_TRANSPORT")
    return {"authorization_ref": encode_identity(original[0]), "claimant_scope": _scope(dict(zip(sorted(SCOPE), original[1]))),
            "start": original[2], "end": original[3], "method": original[4]}


def _execution_frame(frame):
    """Mechanical field projection; every original row remains in original_frames."""
    result = {key: deepcopy(frame[key]) for key in ["id", "period", "as_of", "as_of_next", "cutoff", "period_end_utc"]}
    for kind in ARRAYS:
        result[kind] = []
        for row in frame[kind]:
            result[kind].append({key: deepcopy(value) for key, value in row.items()
                if key != "raw_original" and not key.endswith(("_start_utc", "_end_utc"))
                and key not in {"paid_utc_midnight", "source_observed_at", "source_paid_at"}
                and key not in {"source_" + name for name in MONEY | RATIOS if name != "share"}
                and not (kind == "authorizations" and key == "approved_date_utc")})
    return result


def _optional(value):
    return {"none": True} if value is None else {"some": money(_q(value))}


def _result(original):
    result = deepcopy(original)
    for key in ["original_entitlement_total", "applied_burden_total", "adjusted_entitlement_total"]:
        result[key] = money(_q(original[key]))
    result["source_case_id"] = encode_identity(original["source_case_id"])
    result["dependency_order"] = [encode_identity(item) for item in original["dependency_order"]]
    for row, source in zip(result["account_results"], original["account_results"]):
        row.update(id=encode_identity(source["id"]), scope=_scope(source["scope"]), actual_paid=_optional(source["actual_paid"]))
        for key in ACCOUNT_MONEY:
            row[key] = money(_q(source[key]))
    for row, source in zip(result["receipt_details"], original["receipt_details"]):
        _fact(source["receipt"], "receipts")
        row["receipt"] = _raw(source["receipt"])
        row["derived_participation_entitlement"] = money(_q(source["derived_participation_entitlement"]))
    for row, source in zip(result["payment_application_details"], original["payment_application_details"]):
        _fact(source["application"], "applications")
        row["application"] = _raw(source["application"])
        for key in ["derived_participation_limit", "applied"]:
            row[key] = money(_q(source[key]))
    for row, source in zip(result["burden_details"], original["burden_details"]):
        _fact(source["request"], "requests")
        row.update(request=_raw(source["request"]), authorization_id=encode_identity(source["authorization_id"]), source_actual_paid=_optional(source["source_actual_paid"]))
        for key in BURDEN_MONEY:
            row[key] = money(_q(source[key]))
        row["burden_rate"] = number(_q(source["burden_rate"]))
    return result


def _registry(original):
    _record(original, {*STATIC, "static_evidence"})
    result = {}
    for kind in STATIC + ["static_evidence"]:
        result[kind] = []
        for row in original[kind]:
            _fact(row, "evidence" if kind == "static_evidence" else kind)
            result[kind].append(_raw(row))
    return result


def _state(original, context):
    row = {"transport_profile": TRANSPORT, "identity_codec": IDENTITY_CODEC, "coordinator": {**context["coordinator"], "id": encode_identity(context["coordinator"]["id"])},
           "policy": deepcopy(context["policy"]), "research": deepcopy(context["research"]), "boundary": original["boundary"],
           "origin": original["origin"], "source_case_id": encode_identity(original["source_case_id"]), "detail": {"none": True}}
    if original["origin"] == "genesis":
        _record(original, {"origin", "boundary", "source_case_id", "history"})
        if original["history"]:
            raise ValueError("BURDEN_GENESIS")
        return row
    _record(original, {"schema_version", "coordinator", "policy", "research", "registry", "boundary", "origin", "source_case_id", "history", "cap_usage", "consumed"})
    row.update(coordinator={**original["coordinator"], "id": encode_identity(original["coordinator"]["id"])}, policy=deepcopy(original["policy"]), research=deepcopy(original["research"]))
    records = []
    for record in original["history"]:
        _record(record, {"facts", "result"})
        _frame(record["facts"])
        records.append({"facts": _raw(record["facts"]), "result": _result(record["result"])})
    row["detail"] = {"some": {"schema_version": original["schema_version"], "registry": _registry(original["registry"]), "history": records,
        "cap_usage": [{"authorization_id": encode_identity(item["authorization_id"]), **{key: money(_q(item[key])) for key in ["cap_limit", "consumed", "remaining"]}} for item in original["cap_usage"]],
        "consumed": {key: [_semantic(item) if key == "semantic_keys" else encode_identity(item) for item in original["consumed"][key]] for key in KINDS}}}
    return row


def neutral_result(value):
    if isinstance(value, list):
        return [neutral_result(item) for item in value]
    if not isinstance(value, dict):
        return value
    if set(value) == {"numerator", "denominator"}:
        return str(exact(value))
    if set(value) == {"value", "currency"}:
        if value["currency"] != "USD":
            raise ValueError("BURDEN_CURRENCY")
        return str(exact(value["value"]))
    if set(value) == {"none"}:
        return None
    if set(value) == {"some"}:
        return neutral_result(value["some"])
    result = {}
    for key, item in value.items():
        if key in {"receipt", "application", "request"}:
            result[key] = json.loads(item)
        elif key in {"source_case_id", "id", "authorization_id"}:
            result[key] = decode_identity(item)
        elif key == "scope":
            result[key] = {name: scalar if name == "currency" else decode_identity(scalar) for name, scalar in item.items()}
        elif key == "dependency_order":
            result[key] = [decode_identity(identity) for identity in item]
        elif key in ACCOUNT_MONEY | BURDEN_MONEY | {"actual_paid", "source_actual_paid", "burden_rate", "derived_participation_entitlement", "derived_participation_limit", "original_entitlement_total", "applied_burden_total", "adjusted_entitlement_total"}:
            decoded = neutral_result(item)
            result[key] = None if decoded is None else str(_q(decoded))
        else:
            result[key] = neutral_result(item)
    return result


def neutral_state(value):
    if value["transport_profile"] != TRANSPORT or value["identity_codec"] != IDENTITY_CODEC:
        raise ValueError("BURDEN_STATE_TRANSPORT")
    if value["origin"] == "genesis":
        return {"origin": "genesis", "boundary": value["boundary"], "source_case_id": decode_identity(value["source_case_id"]), "history": []}
    detail = value["detail"]["some"]
    consumed = {}
    for key, values in detail["consumed"].items():
        consumed[key] = []
        for item in values:
            if key == "semantic_keys":
                scoped = {name: scalar if name == "currency" else decode_identity(scalar) for name, scalar in item["claimant_scope"].items()}
                consumed[key].append([decode_identity(item["authorization_ref"]), [scoped[name] for name in sorted(SCOPE)], item["start"], item["end"], item["method"]])
            else:
                consumed[key].append(decode_identity(item))
    result = {"schema_version": detail["schema_version"], "coordinator": {**value["coordinator"], "id": decode_identity(value["coordinator"]["id"])},
              "policy": deepcopy(value["policy"]), "research": deepcopy(value["research"]), "boundary": value["boundary"], "origin": value["origin"], "source_case_id": decode_identity(value["source_case_id"]),
              "registry": {kind: [json.loads(row) for row in rows] for kind, rows in detail["registry"].items()},
              "history": [{"facts": json.loads(record["facts"]), "result": neutral_result(record["result"])} for record in detail["history"]],
              "cap_usage": [{"authorization_id": decode_identity(item["authorization_id"]), **{key: neutral_result(item[key]) for key in ["cap_limit", "consumed", "remaining"]}} for item in detail["cap_usage"]], "consumed": consumed}
    if _state(result, result) != value:
        raise ValueError("BURDEN_RESTORED_STATE_TRANSPORT")
    return result


def register_entitlement_burdens():
    reference = _descriptor("entitlement-burdens", "entitlement-burdens.spl", "policy.md",
        {"policy": "parameter", "cutoff": "parameter", "comparison": "result", "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "history", "closing": "history", "purpose": PURPOSE, "unit": "structured", "key_fields": ["agreement_id", "participant_id", "pool_id", "purpose"], "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:entitlement-burdens"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["accrued100-other170", "linked-paid60-other182", "cap45-three-periods", "original-pre-burden-dag", "unicode-exact-originals", "unknown-paid-not-zero"])
    for name, expected in [("agreement_id", ENVELOPE), ("participant_id", OPERATOR), ("pool_id", POOL)]:
        descriptor["constraints"].append({"kind": "equals", "path": "inputs.scope." + name, "fields": [], "target": "", "value": expected})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def entitlement_burden_package(fixture=None, *, reference=None, state_cells=None, mode="final"):
    data = deepcopy(read_json(FOLDER / "neutral.json") if fixture is None else fixture)
    _record(data, {"schema_version", "coordinator", "policy", "research", "opening_state", *FRAME}, {"prior_result"})
    if data["schema_version"] != "entitlement-burdens-neutral/1" or mode not in {"final", "preview"}:
        raise ValueError("BURDEN_SCHEMA")
    _record(data["coordinator"], {"id", "currency", "purpose"})
    _record(data["research"], {"ld03_sha256", "rr04_sha256", "review_locator"})
    for key in ["ld03_sha256", "rr04_sha256"]:
        if type(data["research"][key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", data["research"][key]):
            raise ValueError("BURDEN_REVIEW_PIN")
    reference = reference or register_entitlement_burdens()
    opening = _state(data["opening_state"], data)
    frames = [_frame(record["facts"]) for record in data["opening_state"].get("history", [])]
    frames.append(_frame({key: data[key] for key in FRAME}))
    execution = {"agreement_id": ENVELOPE, "participant_id": OPERATOR, "pool_id": POOL}
    inputs = {"scope": {**execution, "period": data["period"]}, "coordinator": {**data["coordinator"], "id": encode_identity(data["coordinator"]["id"])},
              "frames": [_execution_frame(frame) for frame in frames],
              "original_frames": [{key: deepcopy(frame[key]) for key in ["id", "period", "raw_original", "originals"]} for frame in frames],
              "research": data["research"], "supplied_opening": opening, "predecessor": {"none": True}}
    cell = {"opening_port": "history", "state_key": canonical({**execution, "purpose": PURPOSE}), "purpose": PURPOSE, "unit": "structured", "scope": execution,
            "boundary": data["period"]["start"], "quantity": opening, "provenance_ref": "original-burden-history-transport", "scenario_id": "SYNTHETIC-ENTITLEMENT-BURDENS"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if type(prior.get("result_ref")) is not str or not prior["result_ref"].startswith("result@sha256:"):
            raise ValueError("BURDEN_CANONICAL_PREDECESSOR_REQUIRED")
        inputs["predecessor"] = {"some": {"source_case_id": encode_identity(prior["source_case_id"]), "period": prior["period"], "closing_state": _state(prior["closing_state"], data)}}
        cell["prior_result_ref"] = prior["result_ref"]
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells):
        raise ValueError("BURDEN_CANONICAL_PREDECESSOR_MISMATCH")
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": "entitlement-burden-run", "scenario_id": "SYNTHETIC-ENTITLEMENT-BURDENS", "mode": mode, "period": data["period"], "cutoff": data["cutoff"],
            "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": ENVELOPE, "participant_ids": [OPERATOR], "pool_id": POOL, "asset_ids": [], "purpose": PURPOSE},
        "inputs": inputs, "parameters": {"policy": data["policy"], "cutoff": data["cutoff"]}, "evidence": {}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "synthetic-selected-burden-policy"}
            for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def validate_prepared_package(package):
    """Check reversible preparation, without deriving any financial answer.

    Raw JSON is supplied evidence, not authenticated source material. The generic
    module API accepts deliberately prepared typed inputs and does not call this
    case-specific boundary check.
    """
    from spl_compiler.artifacts import _strict_json

    def same(actual, expected):
        if _raw(actual) != _raw(expected):
            raise ValueError("BURDEN_PREPARED_PACKAGE_MISMATCH")

    inputs = package["inputs"]
    cells = package["state_cells"]
    if type(cells) is not list or len(cells) != 1:
        raise ValueError("BURDEN_PREPARED_PACKAGE_MISMATCH")
    opening = cells[0]["quantity"]
    same(inputs["supplied_opening"], opening)
    context = {"coordinator": {**opening["coordinator"], "id": decode_identity(opening["coordinator"]["id"])},
               "policy": opening["policy"], "research": opening["research"]}
    neutral = neutral_state(opening)
    same(opening, _state(neutral, context))  # Includes genesis metadata/detail.
    same(inputs["coordinator"], opening["coordinator"])
    same(inputs["research"], context["research"])
    originals = inputs["original_frames"]
    if type(originals) is not list or not originals:
        raise ValueError("BURDEN_PREPARED_PACKAGE_MISMATCH")
    current = _strict_json(originals[-1]["raw_original"])
    frames = [_frame(record["facts"]) for record in neutral.get("history", [])]
    frames.append(_frame(current))
    same(inputs["frames"], [_execution_frame(frame) for frame in frames])
    same(originals, [{key: frame[key] for key in ["id", "period", "raw_original", "originals"]} for frame in frames])
    execution = {"agreement_id": ENVELOPE, "participant_id": OPERATOR, "pool_id": POOL}
    same(inputs["scope"], {**execution, "period": current["period"]})
    same(package["scope"], {"agreement_id": ENVELOPE, "participant_ids": [OPERATOR], "pool_id": POOL,
                           "asset_ids": [], "purpose": PURPOSE})
    same(package["parameters"], {"policy": context["policy"], "cutoff": current["cutoff"]})
    same(package["manifest"]["period"], current["period"])
    same(package["manifest"]["cutoff"], current["cutoff"])
    for key, expected in {"opening_port": "history", "state_key": canonical({**execution, "purpose": PURPOSE}),
                          "purpose": PURPOSE, "unit": "structured", "scope": execution,
                          "boundary": current["period"]["start"]}.items():
        same(cells[0][key], expected)
    predecessor = inputs["predecessor"]
    if _raw(predecessor) != _raw({"none": True}):
        _record(predecessor, {"some"})
        prior = predecessor["some"]
        _record(prior, {"source_case_id", "period", "closing_state"})
        same(prior["closing_state"], opening)
        same(prior["source_case_id"], opening["source_case_id"])
        same(prior["period"], neutral["history"][-1]["facts"]["period"])
        prior_ref = cells[0].get("prior_result_ref")
        if type(prior_ref) is not str or not re.fullmatch(r"result@sha256:[0-9a-f]{64}", prior_ref):
            raise ValueError("BURDEN_PREPARED_PACKAGE_MISMATCH")


def run_entitlement_burden_package(package, registry_root=None, *, backend="compare", artifact_dir=None, audit_profile="array-v1"):
    from spl_compiler.artifacts import ArtifactPublication, PublicationError
    from spl_compiler.audited_artifacts import AuditedPublication, unavailable_trace
    from spl_compiler.compact_execution import require_profile
    try:
        require_profile(audit_profile, backend, artifact_dir)
    except BaseException:
        if artifact_dir is not None:
            (AuditedPublication if audit_profile == "compact-v2" else ArtifactPublication)(artifact_dir)
        raise
    snapshot = None
    try:
        snapshot = deepcopy(package)
        validate_prepared_package(snapshot)
    except (KeyError, IndexError, TypeError, ValueError, PublicationError):
        result = {"status": "blocked", "results": {}, "statements": [], "detail": [], "closing_state": [],
                  "trace": unavailable_trace() if audit_profile == "compact-v2" else [],
                  "reconciliation": {}, "policy_review": {},
                  "manifest": snapshot.get("manifest", {}) if type(snapshot) is dict else {},
                  "issuance_status": "unissued", "payment_evidence_status": "not_assessed",
                  "diagnostics": [{"code": "BURDEN_PREPARED_PACKAGE_MISMATCH",
                                   "message": "Prepared inputs do not match their original-record/state transport"}]}
        if artifact_dir is not None:
            publication = (AuditedPublication if audit_profile == "compact-v2" else ArtifactPublication)(artifact_dir)
            return publication.finish(result, {"results.json": "results", "statement.json": "statements",
                "detail.json": "detail", "trace.json": "trace", "closing-state.json": "closing_state",
                "reconciliation.json": "reconciliation", "diagnostics.json": "diagnostics", "policy-review.json": "policy_review"})
        return result
    except BaseException:
        # Cancellation during preparation cannot leave an older successful
        # directory looking like the completed outcome of this invocation.
        if artifact_dir is not None:
            (AuditedPublication if audit_profile == "compact-v2" else ArtifactPublication)(artifact_dir)
        raise
    return run_module_package(snapshot, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir,
        audit_profile=audit_profile,
        blocked_evidence_labels={"BURDEN_PAID_BASIS_UNKNOWN": {"payment_evidence_status": "no_event_supplied"},
                                 "BURDEN_COMPLETE_PAYMENT_POPULATION_REQUIRED": {"payment_evidence_status": "not_assessed"}})


if __name__ == "__main__":
    reference = register_entitlement_burdens()
    for mode, name in [("final", "canonical-package.json"), ("preview", "preview-canonical-package.json")]:
        package = entitlement_burden_package(reference=reference, mode=mode)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / name, package)
