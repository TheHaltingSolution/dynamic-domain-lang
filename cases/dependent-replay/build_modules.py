"""Mechanical original-record/state transport; all replay finance runs in SPL."""
from copy import deepcopy
from datetime import date
from fractions import Fraction
import json
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, instant, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = "SYNTHETIC-DEPENDENT-REPLAY-01"
PURPOSE = "authorized_dependent_replay"
TRANSPORT = "dependent-replay-original-json/1"
IDENTITY_CODEC = "unicode-utf8-hex/1"
COMMON = {"id", "scope", "observed_at", "source_ref", "evidence_ref"}
SCOPE = {"agreement_id", "participant_id", "pool_id", "asset_id", "currency", "purpose"}
FRAME = {"case_id", "period_id", "period", "as_of", "cutoff", "predecessor_period_id", "predecessor_result_ref", "receipts", "population", "cash_population", "replacements", "authorities", "requests", "correction_population", "evidence"}
TABLES = {"periods": {"period", "as_of", "cutoff", "predecessor_period_id"},
    "terms": {"kind", "effective", "approved", "approved_date", "original_ref", "flat_rate", "lower_rate", "upper_rate", "threshold"},
    "receipts": {"period_id", "term_id", "base_amount", "effective_date", "sequence", "original_ref", "entitlement_ref"},
    "issued_artifacts": {"period_id", "receipt_ids", "complete", "issued_at", "original_ref", "result_ref", "predecessor_issue_id", "basis_total", "earned", "opening_cumulative_basis", "closing_cumulative_basis"},
    "payments": {"receipt_id", "payer_id", "recipient_id", "purpose", "amount", "paid_at", "original_ref"},
    "applications": {"payment_id", "receipt_id", "original_entitlement_ref", "amount", "approved"},
    "payment_population": {"complete", "through_period_id", "payment_ids", "application_ids", "paid_total"},
    "population": {"period", "complete", "receipt_ids", "gross_basis_total"}, "cash_population": {"period", "complete", "event_ids", "total"},
    "replacements": {"original_receipt_id", "base_amount", "effective_date", "original_basis_ref", "original_ref"},
    "authorities": {"replacement_id", "original_receipt_id", "original_issue_id", "route", "dependent_period_ids", "predecessor_result_ref", "approved", "approved_date", "recorded_date", "apply_revised_basis_to_future", "original_ref"},
    "requests": {"replacement_id", "authority_id", "sequence"}, "correction_population": {"period", "complete", "request_ids", "replacement_ids", "authority_ids"}}
STATIC_ARRAYS = ("periods", "terms", "receipts", "issued_artifacts", "payments", "applications", "evidence")
DYNAMIC_ARRAYS = ("receipts", "replacements", "authorities", "requests", "evidence")
IDENTITIES = {"id", "source_ref", "evidence_ref", "period_id", "term_id", "original_ref", "entitlement_ref", "result_ref", "predecessor_result_ref", "receipt_id", "payer_id", "recipient_id", "payment_id", "original_entitlement_ref", "through_period_id", "original_receipt_id", "original_basis_ref", "replacement_id", "original_issue_id", "authority_id"}
ID_ARRAYS = {"receipt_ids", "payment_ids", "application_ids", "event_ids", "dependent_period_ids", "request_ids", "replacement_ids", "authority_ids"}
MONEY = {"base_amount", "threshold", "basis_total", "earned", "opening_cumulative_basis", "closing_cumulative_basis", "amount", "paid_total", "gross_basis_total", "total"}
RATIOS = {"flat_rate", "lower_rate", "upper_rate"}
INSTANCES = {"observed_at", "cutoff", "issued_at", "paid_at"}
DATES = {"as_of", "approved_date", "effective_date", "recorded_date"}
OPTION_IDS = {"predecessor_period_id", "predecessor_issue_id"}
RESULT_MONEY = {"current_gross_basis", "current_economic_earned", "current_posted_adjustment", "current_recognized", "cumulative_economic_entitlement", "cumulative_recognized_entitlement", "actual_original_paid", "original_issued_total", "original_issued_unpaid", "revised_original_issued_economic_total", "revised_original_issued_economic_unpaid", "calculated_unissued_earnings", "authorized_correction_credit", "signed_net_unissued_recognition", "calculated_restatement_credit", "calculated_prospective_credit", "outstanding", "closing_cumulative_basis", "actual_current_cash"}
CONTROL_MONEY = {"opening_cumulative_basis", "gross_basis", "earned", "closing_cumulative_basis"}
DETAIL_MONEY = {"original_basis", "selected_basis", "opening_cumulative_basis", "lower_basis", "upper_basis", "earned", "closing_cumulative_basis"}
LINE_MONEY = {"economic_earned", "recognized_entitlement", "opening_cumulative_basis", "closing_cumulative_basis"}
CHANGE_MONEY = {"original_basis", "replacement_basis", "basis_delta"}
ADJUSTMENT_MONEY = {"previous_earned", "revised_earned", "delta"}


def record(value, keys):
    if type(value) is not dict or set(value) != set(keys): raise ValueError("REPLAY_RECORD_TRANSPORT")


def encode_identity(value):
    if type(value) is not str or not value or any(0xD800 <= ord(c) <= 0xDFFF for c in value): raise ValueError("REPLAY_TEXT_TRANSPORT")
    return value.encode("utf-8").hex()


def decode_identity(value):
    if type(value) is not str or not value or len(value) % 2 or not re.fullmatch(r"[0-9a-f]+", value): raise ValueError("REPLAY_IDENTITY_TRANSPORT")
    try: decoded = bytes.fromhex(value).decode("utf-8", errors="strict")
    except (ValueError, UnicodeError): raise ValueError("REPLAY_IDENTITY_TRANSPORT") from None
    if encode_identity(decoded) != value: raise ValueError("REPLAY_IDENTITY_TRANSPORT")
    return decoded


def q(value, *, signed=False):
    if type(value) is not str or not re.fullmatch(("-?" if signed else "") + r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value): raise ValueError("REPLAY_EXACT_TRANSPORT")
    return Fraction(value)


def derived_money(value):
    decoded = q(value, signed=True)
    if value != str(decoded): raise ValueError("REPLAY_DERIVED_NUMBER_CANONICAL")
    return money(decoded)


def day(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value): raise ValueError("REPLAY_DATE_TRANSPORT")
    return date.fromisoformat(value)


def stamp(value): return instant(value).canonical
def midnight(value): return stamp(day(value).isoformat() + "T00:00:00Z")
def raw(value): return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
def original_loads(value):
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result: raise ValueError("REPLAY_DUPLICATE_ORIGINAL_JSON_KEY")
            result[key] = item
        return result
    def constant(value): raise ValueError("REPLAY_ORIGINAL_JSON_CONSTANT")
    return json.loads(value, object_pairs_hook=pairs, parse_constant=constant)
def scope(value):
    record(value, SCOPE)
    return {key: item if key in {"currency", "purpose"} else encode_identity(item) for key, item in value.items()}


def period(value):
    record(value, {"start", "end"}); day(value["start"]); day(value["end"])
    return deepcopy(value)


def line(value):
    prefix, marker, suffix = value.rpartition("#") if isinstance(value, str) else ("", "", "")
    if not prefix or not marker or not suffix: raise ValueError("REPLAY_ORIGINAL_LINE_TRANSPORT")
    return encode_identity(value)


def slots(rows):
    if type(rows) is not list: raise ValueError("REPLAY_LIST_TRANSPORT")
    return {row["id"]: str(position) for position, row in enumerate(rows)}


def fact(row, kind, positions, source_case=None):
    if kind == "evidence":
        record(row, {"id", "scope", "kind", "approved", "observed_at", "source_ref"})
    else: record(row, COMMON | TABLES[kind])
    result = {}
    for key, value in row.items():
        if key == "scope": result[key] = scope(value)
        elif key in {"original_ref", "original_basis_ref", "entitlement_ref", "original_entitlement_ref"}: result[key] = line(value)
        elif key in IDENTITIES: result[key] = encode_identity(value)
        elif key in OPTION_IDS: result[key] = {"none": True} if value is None else {"some": encode_identity(value)}
        elif key in ID_ARRAYS:
            if type(value) is not list: raise ValueError("REPLAY_ID_LIST_TRANSPORT")
            result[key] = [encode_identity(item) for item in value]
        elif key in MONEY: result[key] = money(q(value))
        elif key in RATIOS: result[key] = number(q(value))
        elif key in INSTANCES:
            result[key] = stamp(value)
            if key in {"issued_at", "paid_at"}: result[key + "_utc_date"] = result[key].split("T", 1)[0]
        elif key in DATES:
            result[key] = day(value).isoformat(); result[key + "_utc"] = midnight(value)
            if key == "as_of": result["as_of_ordinal"] = str(day(value).toordinal())
        elif key in {"period", "effective"}:
            result[key] = period(value)
            result[key + "_end_utc"] = midnight(value["end"])
            result[key + "_end_ordinal"] = str(day(value["end"]).toordinal())
        elif key == "sequence":
            if type(value) is not int: raise ValueError("REPLAY_SEQUENCE_TRANSPORT")
            result[key] = str(value)
        else: result[key] = deepcopy(value)
    if kind == "evidence": result["slot"] = positions[row["id"]]
    else: result["evidence_slot"] = positions.get(row["evidence_ref"], "-1")
    if kind == "replacements": result["source_case_id"] = encode_identity(source_case)
    return result


def normalized_registry(original):
    result = deepcopy(original)
    for key, value in result.items():
        if type(value) is list: result[key] = sorted(value, key=lambda item: item["id"]) if value and type(value[0]) is dict else sorted(value)
    return result


def registry(original):
    record(original, {"party_ids", "payer_id", "origin", "payment_population", *STATIC_ARRAYS})
    positions = slots(original["evidence"])
    record(original["origin"], {"boundary", "cumulative_basis", "recognized_entitlement", "actual_paid"})
    result = {"party_ids": [encode_identity(item) for item in original["party_ids"]], "payer_id": encode_identity(original["payer_id"]),
        "origin": {"boundary": day(original["origin"]["boundary"]).isoformat(), **{key: money(q(original["origin"][key])) for key in ("cumulative_basis", "recognized_entitlement", "actual_paid")}},
        "payment_population": fact(original["payment_population"], "payment_population", positions)}
    for kind in STATIC_ARRAYS:
        if type(original[kind]) is not list: raise ValueError("REPLAY_LIST_TRANSPORT")
        result[kind] = [fact(row, kind, positions) for row in original[kind]]
    return result


def frame(original):
    record(original, FRAME); positions = slots(original["evidence"])
    result = {"id": encode_identity(original["case_id"]), "period_id": encode_identity(original["period_id"]), "period": period(original["period"]),
        "as_of": day(original["as_of"]).isoformat(), "as_of_ordinal": str(day(original["as_of"]).toordinal()), "period_end_ordinal": str(day(original["period"]["end"]).toordinal()),
        "period_end_utc": midnight(original["period"]["end"]), "cutoff": stamp(original["cutoff"]), "predecessor_period_id": encode_identity(original["predecessor_period_id"]), "predecessor_result_ref": encode_identity(original["predecessor_result_ref"])}
    originals = {}
    for kind in DYNAMIC_ARRAYS:
        if type(original[kind]) is not list: raise ValueError("REPLAY_LIST_TRANSPORT")
        result[kind] = [fact(row, kind, positions, original["case_id"]) for row in original[kind]]
        originals[kind] = [{"id": row["id"], "raw_original": raw(source)} for row, source in zip(result[kind], original[kind])]
    for kind in ("population", "cash_population", "correction_population"): result[kind] = fact(original[kind], kind, positions)
    return result, {"id": result["id"], "period": result["period"], "raw_original": raw(original), "originals": originals}


def validate_frame_transport(typed, original):
    expected, originals = frame(json.loads(original["raw_original"]))
    if expected != typed or originals != original: raise ValueError("REPLAY_TYPED_RAW_MISMATCH")


def result_transport(original):
    result = deepcopy(original)
    for key in RESULT_MONEY: result[key] = derived_money(original[key])
    result["source_case_id"] = encode_identity(original["source_case_id"])
    result["consumed_correction_ids"] = [encode_identity(item) for item in original["consumed_correction_ids"]]
    result["original_issued_artifacts"] = [raw(item) for item in original["original_issued_artifacts"]]
    for kind in ("original_period_controls", "replayed_period_controls"):
        for row, source in zip(result[kind], original[kind]):
            row.update(period_id=encode_identity(source["period_id"]), **{key: derived_money(source[key]) for key in CONTROL_MONEY})
            for item, raw_item in zip(row["receipt_details"], source["receipt_details"]):
                item.update(receipt_id=encode_identity(raw_item["receipt_id"]), term_id=encode_identity(raw_item["term_id"]),
                    replacement_id={"none": True} if raw_item["replacement_id"] is None else {"some": encode_identity(raw_item["replacement_id"])}, **{key: derived_money(raw_item[key]) for key in DETAIL_MONEY})
    for row, source in zip(result["period_lines"], original["period_lines"]):
        row.update(period_id=encode_identity(source["period_id"]), original_issued_entitlement={"none": True} if source["original_issued_entitlement"] is None else {"some": derived_money(source["original_issued_entitlement"])},
            original_issued_result_ref={"none": True} if source["original_issued_result_ref"] is None else {"some": encode_identity(source["original_issued_result_ref"])}, **{key: derived_money(source[key]) for key in LINE_MONEY})
    for row, source in zip(result["source_changes"], original["source_changes"]):
        row.update(**{key: encode_identity(source[key]) for key in ("request_id", "original_receipt_id")}, dependent_period_ids=[encode_identity(item) for item in source["dependent_period_ids"]], **{key: derived_money(source[key]) for key in CHANGE_MONEY})
    for kind in ("restatement_records", "prospective_adjustments"):
        for row, source in zip(result[kind], original[kind]):
            row.update(key=[encode_identity(item) for item in source["key"]], **{key: encode_identity(source[key]) for key in ("request_id", "replacement_id", "authority_id", "affected_period_id")},
                original_issued_result_ref={"none": True} if source["original_issued_result_ref"] is None else {"some": encode_identity(source["original_issued_result_ref"])}, **{key: derived_money(source[key]) for key in ADJUSTMENT_MONEY})
    return result


def state_transport(original, context):
    if original.get("origin") == "genesis":
        record(original, {"origin", "boundary", "source_case_id", "history"})
        return {"transport_profile": TRANSPORT, "identity_codec": IDENTITY_CODEC, "origin": "genesis", "boundary": original["boundary"], "source_case_id": encode_identity(original["source_case_id"]),
            "scope": scope(context["scope"]), "policy": deepcopy(context["policy"]), "research": deepcopy(context["research"]), "registry_original": raw(normalized_registry(context["registry"])), "detail": {"none": True}}
    record(original, {"schema_version", "scope", "policy", "research", "registry", "boundary", "origin", "source_case_id", "history", "active_replacements", "consumed_correction_ids", "consumed_original_receipt_ids", "recognized_period_lines", "cumulative_basis", "recognized_entitlement", "actual_paid", "authorized_correction_credit", "outstanding"})
    history = []
    for item in original["history"]:
        record(item, {"facts", "result"}); frame(item["facts"])
        history.append({"facts": raw(item["facts"]), "result": result_transport(item["result"])})
    # The original-schema inverse uses the same exact field codecs as result.
    sample_lines = {"period_lines": original["recognized_period_lines"]}
    physical_lines = deepcopy(original["recognized_period_lines"])
    for row, source in zip(physical_lines, sample_lines["period_lines"]):
        row.update(period_id=encode_identity(source["period_id"]), original_issued_entitlement={"none": True} if source["original_issued_entitlement"] is None else {"some": derived_money(source["original_issued_entitlement"])},
            original_issued_result_ref={"none": True} if source["original_issued_result_ref"] is None else {"some": encode_identity(source["original_issued_result_ref"])}, **{key: derived_money(source[key]) for key in LINE_MONEY})
    detail = {"schema_version": original["schema_version"], "history": history, "active_replacements": [raw(item) for item in original["active_replacements"]],
        "consumed_correction_ids": [encode_identity(item) for item in original["consumed_correction_ids"]], "consumed_original_receipt_ids": [encode_identity(item) for item in original["consumed_original_receipt_ids"]], "recognized_period_lines": physical_lines,
        **{key: derived_money(original[key]) for key in ("cumulative_basis", "recognized_entitlement", "actual_paid", "authorized_correction_credit", "outstanding")}}
    return {"transport_profile": TRANSPORT, "identity_codec": IDENTITY_CODEC, "origin": original["origin"], "boundary": original["boundary"], "source_case_id": encode_identity(original["source_case_id"]),
        "scope": scope(original["scope"]), "policy": deepcopy(original["policy"]), "research": deepcopy(original["research"]), "registry_original": raw(original["registry"]), "detail": {"some": detail}}


def neutral_result(value):
    if isinstance(value, list): return [neutral_result(item) for item in value]
    if not isinstance(value, dict): return value
    if set(value) == {"value", "currency"}: return str(exact(value["value"]))
    if set(value) == {"numerator", "denominator"}: return str(exact(value))
    if set(value) == {"none"}: return None
    if set(value) == {"some"}: return neutral_result(value["some"])
    identities = {"source_case_id", "period_id", "receipt_id", "term_id", "replacement_id", "request_id", "original_receipt_id", "authority_id", "affected_period_id", "original_issued_result_ref"}
    result = {}
    monetary_fields = RESULT_MONEY | CONTROL_MONEY | DETAIL_MONEY | LINE_MONEY | CHANGE_MONEY | ADJUSTMENT_MONEY | {"original_issued_entitlement"}
    for key, item in value.items():
        if key in identities: result[key] = None if "none" in item else decode_identity(item["some"]) if isinstance(item, dict) else decode_identity(item)
        elif key in {"key", "dependent_period_ids", "consumed_correction_ids"}: result[key] = [decode_identity(part) for part in item]
        elif key == "scope": result[key] = {name: scalar if name in {"currency", "purpose"} else decode_identity(scalar) for name, scalar in item.items()}
        elif key == "original_issued_artifacts": result[key] = [json.loads(row) for row in item]
        else:
            decoded = neutral_result(item)
            result[key] = None if decoded is None else str(Fraction(decoded) if isinstance(decoded, str) else exact(decoded)) if key in monetary_fields else decoded
    return result


def neutral_state(value):
    if value["transport_profile"] != TRANSPORT or value["identity_codec"] != IDENTITY_CODEC: raise ValueError("REPLAY_STATE_TRANSPORT")
    result = {"origin": value["origin"], "boundary": value["boundary"], "source_case_id": decode_identity(value["source_case_id"]), "history": []}
    if value["origin"] != "genesis":
        detail = value["detail"]["some"]
        result.update(schema_version=detail["schema_version"], scope={key: item if key in {"currency", "purpose"} else decode_identity(item) for key, item in value["scope"].items()},
            policy=deepcopy(value["policy"]), research=deepcopy(value["research"]), registry=json.loads(value["registry_original"]), history=[{"facts": json.loads(row["facts"]), "result": neutral_result(row["result"])} for row in detail["history"]],
            active_replacements=[json.loads(item) for item in detail["active_replacements"]], consumed_correction_ids=[decode_identity(item) for item in detail["consumed_correction_ids"]],
            consumed_original_receipt_ids=[decode_identity(item) for item in detail["consumed_original_receipt_ids"]], recognized_period_lines=neutral_result(detail["recognized_period_lines"]),
            **{key: str(exact(detail[key]["value"])) for key in ("cumulative_basis", "recognized_entitlement", "actual_paid", "authorized_correction_credit", "outstanding")})
    context = {"scope": {key: item if key in {"currency", "purpose"} else decode_identity(item) for key, item in value["scope"].items()}, "policy": value["policy"], "research": value["research"], "registry": json.loads(value["registry_original"])}
    if state_transport(result, context) != value: raise ValueError("REPLAY_RESTORED_STATE_TRANSPORT")
    return result


def register_dependent_replay():
    reference = _descriptor("dependent-replay", "dependent-replay.spl", "policy.md", {"policy": "parameter", "cutoff": "parameter", "comparison": "result", "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "history", "closing": "history", "purpose": PURPOSE, "unit": "structured", "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"], "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]; descriptor = read_json(path); descriptor["id"] = "synthetic:dependent-replay"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["simple40-distinct-route-lines", "dependent10-to8-outstanding18", "immutable-issued-paid-bridge", "actual-no-repeat-successor", "whole-dependent-suffix-authority"])
    for field in ("agreement_id", "participant_id", "pool_id"):
        descriptor["constraints"].append({"kind": "member_of" if field == "participant_id" else "equals", "path": "inputs.fact_scope." + field, "fields": [], "target": "scope.participant_ids" if field == "participant_id" else "scope." + field, "value": ""})
    descriptor["constraints"].append({"kind": "equals", "path": "inputs.fact_scope.asset_id", "fields": [], "target": "inputs.project", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def dependent_replay_package(fixture=None, *, reference=None, state_cells=None, mode="final"):
    data = deepcopy(original_loads((FOLDER / "neutral.json").read_text(encoding="utf-8"))["scenarios"]["simple_restatement"] if fixture is None else fixture)
    record(data, {"schema_version", "scope", "policy", "research", "registry", "opening_state", *FRAME} | ({"prior_result"} if "prior_result" in data else set()))
    if data["schema_version"] != "dependent-replay-neutral/1": raise ValueError("REPLAY_SCHEMA_TRANSPORT")
    record(data["research"], {"catalog_sha256", "backlog_sha256", "scope_note"})
    if any(type(data["research"][key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", data["research"][key]) for key in ("catalog_sha256", "backlog_sha256")): raise ValueError("REPLAY_RESEARCH_PIN_TRANSPORT")
    reference = reference or register_dependent_replay()
    typed_registry = registry(data["registry"])
    opening = state_transport(data["opening_state"], data)
    history = [row["facts"] for row in data["opening_state"].get("history", [])]
    frames, originals = [], []
    for source in [*history, {key: data[key] for key in FRAME}]:
        typed, original = frame(source); validate_frame_transport(typed, original); frames.append(typed); originals.append(original)
    work = scope(data["scope"]); execution = {key: work[key] for key in ("agreement_id", "participant_id", "pool_id", "asset_id")}
    inputs = {"scope": {key: execution[key] for key in ("agreement_id", "participant_id", "pool_id")} | {"period": data["period"]}, "project": work["asset_id"], "fact_scope": work,
        "source_context": raw({key: data[key] for key in ("schema_version", "scope", "policy", "research", "registry")}),
        "registry": typed_registry, "registry_original": raw(normalized_registry(data["registry"])), "original_registry": {kind: [{"id": encode_identity(row["id"]), "raw_original": raw(row)} for row in data["registry"][kind]] for kind in STATIC_ARRAYS},
        "frames": frames, "original_frames": originals, "research": deepcopy(data["research"]), "supplied_opening": opening, "predecessor": {"none": True}}
    cell = {"opening_port": "history", "state_key": canonical({**execution, "purpose": PURPOSE}), "purpose": PURPOSE, "unit": "structured", "scope": execution, "boundary": data["period"]["start"], "quantity": deepcopy(opening), "provenance_ref": "original-issued-chain-and-disclosed-replay", "scenario_id": "SYNTHETIC-DEPENDENT-REPLAY"}
    if "prior_result" in data:
        prior = data["prior_result"]; record(prior, {"source_case_id", "period", "closing_state", "result_ref"})
        if type(prior["result_ref"]) is not str or not re.fullmatch(r"result@sha256:[0-9a-f]{64}", prior["result_ref"]): raise ValueError("REPLAY_CANONICAL_PREDECESSOR_REQUIRED")
        inputs["predecessor"] = {"some": {"source_case_id": encode_identity(prior["source_case_id"]), "period": period(prior["period"]), "result_ref": encode_identity(prior["result_ref"]), "closing_state": state_transport(prior["closing_state"], data)}}
        cell["prior_result_ref"] = prior["result_ref"]
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells): raise ValueError("REPLAY_CANONICAL_PREDECESSOR_MISMATCH")
    package = {"profile": "spl-module/1", "module_ref": reference, "manifest": {"run_id": "dependent-replay-run", "scenario_id": "SYNTHETIC-DEPENDENT-REPLAY", "mode": mode, "period": data["period"], "cutoff": data["cutoff"], "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": work["agreement_id"], "participant_ids": [work["participant_id"]], "pool_id": work["pool_id"], "asset_ids": [work["asset_id"]], "purpose": PURPOSE}, "inputs": inputs, "parameters": {"policy": deepcopy(data["policy"]), "cutoff": data["cutoff"]}, "evidence": {}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-original-dependent-replay-policy"} for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def validate_prepared_package(package):
    context = original_loads(package["inputs"]["source_context"])
    record(context, {"schema_version", "scope", "policy", "research", "registry"})
    current = original_loads(package["inputs"]["original_frames"][-1]["raw_original"])
    data = {**context, **current, "opening_state": neutral_state(package["inputs"]["supplied_opening"])}
    if data["opening_state"]["boundary"] != current["period"]["start"]:
        raise ValueError("REPLAY_PREPARED_PACKAGE_MISMATCH")
    prior = package["inputs"]["predecessor"]
    if "some" in prior:
        summary = prior["some"]
        data["prior_result"] = {"source_case_id": decode_identity(summary["source_case_id"]), "period": deepcopy(summary["period"]), "result_ref": decode_identity(summary["result_ref"]), "closing_state": neutral_state(summary["closing_state"])}
    expected = dependent_replay_package(data, reference=package["module_ref"], mode=package["manifest"]["mode"])
    for key in ("profile", "scope", "inputs", "parameters", "evidence", "state_cells"):
        if package[key] != expected[key]: raise ValueError("REPLAY_PREPARED_PACKAGE_MISMATCH")
    for key in ("period", "cutoff"):
        if package["manifest"][key] != expected["manifest"][key]: raise ValueError("REPLAY_PREPARED_PACKAGE_MISMATCH")


def run_dependent_replay_package(package, registry_root=None, *, backend="compare", artifact_dir=None, audit_profile="array-v1"):
    from spl_compiler.artifacts import ArtifactPublication
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
    except (IndexError, KeyError, TypeError, ValueError):
        compact = audit_profile == "compact-v2"
        result = {"status": "blocked", "results": {}, "statements": [], "detail": [], "closing_state": [], "trace": unavailable_trace() if compact else [], "reconciliation": {}, "policy_review": {},
            "manifest": snapshot.get("manifest", {}) if isinstance(snapshot, dict) else {}, "issuance_status": "unissued", "payment_evidence_status": "not_assessed",
            "diagnostics": [{"code": "REPLAY_PREPARED_PACKAGE_MISMATCH", "message": "Canonical transport rejected bindings that differ from retained originals/state", "pointer": "inputs.source_context"}]}
        if artifact_dir is not None:
            publication = (AuditedPublication if compact else ArtifactPublication)(artifact_dir)
            return publication.finish(result, {"results.json": "results", "statement.json": "statements", "detail.json": "detail", "trace.json": "trace", "closing-state.json": "closing_state", "reconciliation.json": "reconciliation", "diagnostics.json": "diagnostics", "policy-review.json": "policy_review"})
        return result
    except BaseException:
        # Preparation precedes the generic runner's own publication. An
        # interrupted invocation must invalidate a reused success destination.
        if artifact_dir is not None:
            (AuditedPublication if audit_profile == "compact-v2" else ArtifactPublication)(artifact_dir)
        raise
    return run_module_package(snapshot, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir, audit_profile=audit_profile,
        blocked_evidence_labels={"REPLAY_CURRENT_CASH_UNKNOWN": {"payment_evidence_status": "not_assessed"}, "REPLAY_COMPLETE_PAID_POPULATION": {"payment_evidence_status": "not_assessed"}})


if __name__ == "__main__":
    reference = register_dependent_replay()
    for name, data in original_loads((FOLDER / "neutral.json").read_text(encoding="utf-8")).get("scenarios", {}).items():
        package = dependent_replay_package(data, reference=reference)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / (name.replace("_", "-") + "-canonical-package.json"), package)
