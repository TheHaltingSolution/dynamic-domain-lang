"""Mechanical transport for original-history ordered work gates.

No selected receipt/cost amount, event rank, gate, opening balance, proxy base
or entitlement is calculated here. Financial rules execute in SPL.
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
POLICY = "SYNTHETIC-LG-ORDERED-GATE-01"
PURPOSE = "rolling_work_gate"
TRANSPORT = "ordered-gates-original-json/1"
IDENTITY_CODEC = "unicode-utf8-hex/1"
COMMON = {"id", "scope", "original_ref", "source_ref", "evidence_ref", "observed_at"}
SCOPE = {"agreement_id", "participant_id", "pool_id", "asset_id", "purpose", "currency"}
FRAME = {"case_id", "period", "cutoff", "rows", "populations", "evidence", "ordering_authority", "aggregate_hurdle", "net_worksheet"}
TABLES = ["receipts", "costs", "decisions", "reductions", "populations", "evidence", "ordering_authorities", "aggregate_hurdles", "net_worksheets"]
RESULT_MONEY = {"opening_receipts", "opening_costs", "current_full_receipts", "current_eligible_costs", "closing_receipts", "closing_costs", "payout_base", "gross_candidate", "supplied_net_subtotal", "net_candidate", "calculated_unissued_entitlement"}
PATH_MONEY = {"selected_full_amount", "pre_receipts", "pre_costs", "pre_surplus", "post_receipts", "post_costs", "post_surplus", "admitted_full_receipt", "payout_base_contribution"}
SEEN = ["consumed_event_ids", "consumed_original_refs", "consumed_classification_ids", "consumed_classification_refs"]


def _record(value, required, optional=()):
    if type(value) is not dict or not set(required) <= value.keys() <= set(required) | set(optional):
        raise ValueError("GATE_RECORD_FIELDS")


def encode_identity(value):
    if type(value) is not str or not value or any(0xD800 <= ord(char) <= 0xDFFF for char in value):
        raise ValueError("GATE_TEXT")
    return value.encode("utf-8").hex()


def decode_identity(value):
    if type(value) is not str or not value or len(value) % 2 or not re.fullmatch(r"[0-9a-f]+", value):
        raise ValueError("GATE_IDENTITY_TRANSPORT")
    try:
        decoded = bytes.fromhex(value).decode("utf-8", errors="strict")
    except (ValueError, UnicodeError):
        raise ValueError("GATE_IDENTITY_TRANSPORT") from None
    if encode_identity(decoded) != value:
        raise ValueError("GATE_IDENTITY_TRANSPORT")
    return decoded


def _q(value, *, signed=False):
    pattern = r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?"
    if type(value) is not str or not re.fullmatch(("-?" if signed else "") + pattern, value):
        raise ValueError("GATE_EXACT_SIGNED" if signed else "GATE_EXACT_NONNEGATIVE")
    return Fraction(value)


def _derived(value, *, signed=False):
    result = _q(value, signed=signed)
    if value != str(result):
        raise ValueError("GATE_DERIVED_NUMBER_CANONICAL")
    return result


def _midnight(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("GATE_DATE")
    date.fromisoformat(value)
    return value + "T00:00:00Z"


def _raw(value):
    result = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    if json.loads(result) != value:
        raise ValueError("GATE_RAW_TRANSPORT")
    return result


def _period(value):
    _record(value, {"start", "end"})
    return deepcopy(value)


def _scope(original):
    if type(original) is not dict or set(original) not in [SCOPE, {"agreement_id", "participant_id", "currency"}, {"agreement_id", "participant_id", "pool_id", "currency"}]:
        raise ValueError("GATE_SCOPE_SHAPE")
    result = {key: encode_identity(original[key]) for key in ["agreement_id", "participant_id"]}
    result["currency"] = original["currency"]
    for key in ["pool_id", "asset_id", "purpose"]:
        result[key] = {"some": original[key] if key == "purpose" else encode_identity(original[key])} if key in original else {"none": True}
    return result


def _work_scope(original):
    _record(original, SCOPE)
    return {key: original[key] if key in {"currency", "purpose"} else encode_identity(original[key]) for key in original}


def _common(original, slots=None):
    if not COMMON <= original.keys():
        raise ValueError("GATE_RECORD_FIELDS")
    if type(original["original_ref"]) is not str: raise ValueError("GATE_ORIGINAL_LINE")
    before, marker, after = original["original_ref"].rpartition("#")
    if not (before and marker and after):
        raise ValueError("GATE_ORIGINAL_LINE")
    result = {key: encode_identity(original[key]) for key in ["id", "original_ref", "source_ref", "evidence_ref"]}
    result.update(scope=_scope(original["scope"]), observed_at=instant(original["observed_at"]).canonical)
    if slots is not None:
        result["evidence_slot"] = number(slots.get(original["evidence_ref"], -1))
    return result


def _registry(original):
    _record(original, {"terms", "work", "net_pool_id", "genesis_date"})
    terms, work = original["terms"], original["work"]
    _record(terms, COMMON | {"effective_start", "effective_end", "gross_rate", "video_proxy", "net_rate"})
    _record(work, COMMON | {"purchaser_produced", "eligible"})
    t = {**_common(terms), "effective_start": terms["effective_start"], "effective_end": terms["effective_end"]}
    for field in ["effective_start", "effective_end"]: _midnight(terms[field])
    for field in ["gross_rate", "video_proxy", "net_rate"]: t[field] = number(_q(terms[field]))
    _midnight(original["genesis_date"])
    return {"terms": t, "work": {**_common(work), "purchaser_produced": work["purchaser_produced"], "eligible": work["eligible"]},
            "net_pool_id": encode_identity(original["net_pool_id"]), "genesis_date": original["genesis_date"]}


def _research(original):
    _record(original, {"references", "source_boundary", "professional_approval"})
    refs = []
    for row in original["references"]:
        _record(row, {"path", "sha256", "locator"})
        if type(row["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError("GATE_RESEARCH_PINS")
        refs.append({"path": encode_identity(row["path"]), "sha256": row["sha256"], "locator": encode_identity(row["locator"])})
    return {**deepcopy(original), "references": refs}


def _sequence(value):
    if type(value) is not int:
        raise ValueError("GATE_SEQUENCE")
    return number(value)


def _frame(original, registry):
    _record(original, FRAME)
    _period(original["period"])
    instant(original["cutoff"])
    slots = {row["id"]: index for index, row in enumerate(original["evidence"])}
    result = {"id": encode_identity(original["case_id"]), "period": deepcopy(original["period"]), "cutoff": original["cutoff"],
              "period_start_utc": _midnight(original["period"]["start"]), "period_end_utc": _midnight(original["period"]["end"]),
              "terms_slot": number(slots.get(registry["terms"]["evidence_ref"], -1)), "work_slot": number(slots.get(registry["work"]["evidence_ref"], -1))}
    result.update({key: [] for key in TABLES})
    raw = {"id": result["id"], "period": deepcopy(original["period"]), "raw_original": _raw(original), "originals": {key: [] for key in TABLES}}
    def retain(kind, source, row):
        raw["originals"][kind].append({"id": row["id"], "raw_original": _raw(source),
            **({"slot": row["slot"]} if kind == "evidence" else {}), **({"row_slot": row["row_slot"], "kind": row["kind"]} if kind in {"receipts", "costs"} else {})})
        result[kind].append(row)
    for source in original["evidence"]:
        _record(source, {"id", "scope", "kind", "source_ref", "observed_at", "approved"})
        instant(source["observed_at"])
        row = {"id": encode_identity(source["id"]), "scope": _scope(source["scope"]), "kind": source["kind"], "source_ref": encode_identity(source["source_ref"]),
               "observed_at": source["observed_at"], "approved": source["approved"], "slot": number(slots[source["id"]])}
        retain("evidence", source, row)
    for position, source in enumerate(original["rows"]):
        if type(source) is not dict or source.get("kind") not in {"receipt", "cost"}:
            raise ValueError("GATE_ROW_KIND")
        kind = source["kind"]
        extra = {"received_at", "earned_at", "nonrefundable", "channel", "amount"} if kind == "receipt" else {"incurred_at", "actual_third_party", "gross_amount", "reductions"}
        _record(source, COMMON | {"kind", "sequence", "decision"} | extra)
        decision = source["decision"]
        _record(decision, COMMON | {"event_ref", "eligible", "reason", "channel"})
        row = {**_common(source, slots), "kind": kind, "sequence": _sequence(source["sequence"]), "decision_id": encode_identity(decision["id"]), "row_slot": number(position)}
        retain("decisions", decision, {**_common(decision, slots), "parent_event_id": row["id"], "event_ref": encode_identity(decision["event_ref"]),
            "eligible": decision["eligible"], "reason": encode_identity(decision["reason"]), "channel": decision["channel"]})
        if kind == "receipt":
            for field in ["received_at", "earned_at"]: instant(source[field])
            row.update(amount=money(_q(source["amount"])), received_at=source["received_at"], earned_at=source["earned_at"], nonrefundable=source["nonrefundable"], channel=source["channel"])
            retain("receipts", source, row)
        else:
            instant(source["incurred_at"])
            row.update(gross_amount=money(_q(source["gross_amount"])), incurred_at=source["incurred_at"], actual_third_party=source["actual_third_party"], reduction_ids=[])
            for item in source["reductions"]:
                _record(item, COMMON | {"category", "amount"})
                reduced = {**_common(item, slots), "parent_event_id": row["id"], "category": item["category"], "amount": money(_q(item["amount"]))}
                row["reduction_ids"].append(reduced["id"])
                retain("reductions", item, reduced)
            retain("costs", source, row)
    for source in original["populations"]:
        _record(source, COMMON | {"period", "kind", "complete", "event_ids", "raw_total"})
        retain("populations", source, {**_common(source, slots), "period": _period(source["period"]), "kind": source["kind"], "complete": source["complete"],
            "event_ids": [encode_identity(value) for value in source["event_ids"]], "raw_total": money(_q(source["raw_total"]))})
    source = original["ordering_authority"]
    _record(source, COMMON | {"period", "keys"})
    keys = []
    for key in source["keys"]:
        _record(key, {"event_id", "occurred_at", "sequence"})
        instant(key["occurred_at"])
        keys.append({"event_id": encode_identity(key["event_id"]), "occurred_at": key["occurred_at"], "sequence": _sequence(key["sequence"])})
    retain("ordering_authorities", source, {**_common(source, slots), "period": _period(source["period"]), "keys": keys})
    source = original["aggregate_hurdle"]
    _record(source, COMMON | {"effective_date", "attained"})
    _midnight(source["effective_date"])
    retain("aggregate_hurdles", source, {**_common(source, slots), "effective_date": source["effective_date"], "attained": source["attained"]})
    source = original["net_worksheet"]
    _record(source, COMMON | {"period", "member_asset_ids", "amount"})
    retain("net_worksheets", source, {**_common(source, slots), "period": _period(source["period"]), "member_asset_ids": [encode_identity(value) for value in source["member_asset_ids"]], "amount": money(_q(source["amount"]))})
    return result, raw


def _ordinal_instant(value):
    """Pure representation change of an already supplied/derived Instant."""
    return instant(value).seconds + 86400


def _from_ordinal(value):
    original = _derived(value, signed=True)
    seconds = original - 86400
    whole = seconds.numerator // seconds.denominator
    days, tick = divmod(whole, 86400)
    local = date(1, 1, 1) + timedelta(days=days)
    fraction = number(seconds - whole)
    if not isinstance(fraction, str):
        raise ValueError("GATE_TIME_TRANSPORT")
    stamp = f"{local.year:04d}-{local.month:02d}-{local.day:02d}T{tick // 3600:02d}:{tick // 60 % 60:02d}:{tick % 60:02d}" + (fraction[1:] if fraction != "0" else "") + "Z"
    if _ordinal_instant(stamp) != original:
        raise ValueError("GATE_TIME_TRANSPORT")
    return stamp


def _path(original, positions):
    _record(original, {"original", "occurred_at_exact", "sequence", *PATH_MONEY, "latch_before", "latch_after", "gross_branch_applicable", "reason", "proxy_factor"})
    result = {key: deepcopy(original[key]) for key in ["latch_before", "latch_after", "gross_branch_applicable", "reason"]}
    identity = original["original"]["id"]
    if identity not in positions: raise ValueError("GATE_PATH_ORIGINAL_REFERENCE")
    result.update(id=encode_identity(identity), kind=original["original"]["kind"], row_slot=number(positions[identity]), original=_raw(original["original"]),
                  economic_instant=_from_ordinal(original["occurred_at_exact"]), sequence=_sequence(original["sequence"]),
                  proxy_factor=number(_derived(original["proxy_factor"])))
    for key in PATH_MONEY: result[key] = money(_derived(original[key], signed=True))
    return result


def _result(original, facts):
    required = {"source_case_id", "period", "status", *RESULT_MONEY, "opening_latch", "closing_latch", "continuous_current_history", "gross_status", "net_status", "selected_branch", "path", "aggregate_hurdle", "net_worksheet", "population_records", "payment_evidence_status", "bank_movement_created"}
    _record(original, required)
    result = deepcopy(original)
    result["source_case_id"] = encode_identity(original["source_case_id"])
    for key in RESULT_MONEY: result[key] = money(_derived(original[key]))
    positions = {row["id"]: index for index, row in enumerate(facts["rows"])}
    result["path"] = [_path(item, positions) for item in original["path"]]
    for key in ["aggregate_hurdle", "net_worksheet"]: result[key] = _raw(original[key])
    result["population_records"] = [_raw(item) for item in original["population_records"]]
    return result


def _state(original, context):
    if type(original) is not dict or original.get("origin") not in {"genesis", "original_history", "prior_result"}:
        raise ValueError("GATE_OPENING")
    result = {"transport_profile": TRANSPORT, "identity_codec": IDENTITY_CODEC, "scope": _work_scope(context["scope"]),
              "policy": deepcopy(context["policy"]), "registry": _registry(context["registry"]), "research": _research(context["research"]),
              "registry_original": _raw(context["registry"]), "research_original": _raw(context["research"]),
              "origin": original["origin"], "boundary": original["boundary"], "source_case_id": {"none": True}, "original_frames": [], "detail": {"none": True}}
    if original["origin"] == "genesis":
        _record(original, {"origin", "boundary"})
        return result
    if original["origin"] == "original_history":
        _record(original, {"origin", "boundary", "frames"})
        for frame in original["frames"]:
            typed, raw = _frame(frame, context["registry"])
            _validate_frame_transport(typed, raw, context["registry"])
            result["original_frames"].append({key: raw[key] for key in ["id", "period", "raw_original"]})
        return result
    _record(original, {"schema_version", "origin", "scope", "policy", "registry", "research", "source_case_id", "boundary", "receipts", "costs", "latched", "history", *SEEN, "recognized_entitlement"})
    _registry(original["registry"]); _research(original["research"])
    result.update(scope=_work_scope(original["scope"]), policy=deepcopy(original["policy"]), registry=_registry(original["registry"]), research=_research(original["research"]),
                  registry_original=_raw(original["registry"]), research_original=_raw(original["research"]),
                  source_case_id={"some": encode_identity(original["source_case_id"])})
    records = []
    for record in original["history"]:
        _record(record, {"facts", "result"})
        typed, raw = _frame(record["facts"], original["registry"])
        _validate_frame_transport(typed, raw, original["registry"])
        records.append({"facts": raw["raw_original"], "result": _result(record["result"], record["facts"])})
    result["detail"] = {"some": {"schema_version": original["schema_version"], "receipts": money(_derived(original["receipts"])), "costs": money(_derived(original["costs"])),
        "latched": original["latched"], "history": records, "recognized_entitlement": money(_derived(original["recognized_entitlement"])),
        **{key: [encode_identity(item) for item in original[key]] for key in SEEN}}}
    return result


def _validate_frame_transport(typed, raw, registry):
    # Mechanical re-encoding of complete originals, never a financial oracle.
    restored = json.loads(raw["raw_original"])
    expected_typed, expected_raw = _frame(restored, registry)
    if typed != expected_typed or raw != expected_raw:
        raise ValueError("GATE_TYPED_RAW_MISMATCH")


def _wire_number(value, *, signed=True):
    if isinstance(value, dict) and set(value) == {"value", "currency"}:
        if value["currency"] != "USD": raise ValueError("GATE_CURRENCY")
        value = value["value"]
    return _q(value, signed=signed) if isinstance(value, str) else exact(value)


def neutral_result(value):
    if isinstance(value, list): return [neutral_result(item) for item in value]
    if not isinstance(value, dict): return value
    if set(value) in [{"value", "currency"}, {"numerator", "denominator"}]: return str(_wire_number(value))
    result = {}
    is_path = "economic_instant" in value
    if is_path:
        original = json.loads(value["original"])
        if encode_identity(original["id"]) != value["id"] or original["kind"] != value["kind"]:
            raise ValueError("GATE_PATH_ORIGINAL_REFERENCE")
    for key, item in value.items():
        if is_path and key in {"id", "kind", "row_slot"}: continue
        if key in {"original", "aggregate_hurdle", "net_worksheet"}: result[key] = json.loads(item)
        elif key == "population_records": result[key] = [json.loads(record) for record in item]
        elif key == "source_case_id": result[key] = decode_identity(item)
        elif key == "economic_instant": result["occurred_at_exact"] = str(_ordinal_instant(item))
        elif key == "sequence":
            sequence = _wire_number(item)
            if sequence.denominator != 1: raise ValueError("GATE_SEQUENCE")
            result[key] = sequence.numerator
        elif key in RESULT_MONEY | PATH_MONEY | {"proxy_factor"}: result[key] = str(_wire_number(item))
        else: result[key] = neutral_result(item)
    return result


def neutral_state(value):
    if value["transport_profile"] != TRANSPORT or value["identity_codec"] != IDENTITY_CODEC:
        raise ValueError("GATE_STATE_TRANSPORT")
    result = {"origin": value["origin"], "boundary": value["boundary"]}
    if value["origin"] == "original_history":
        result["frames"] = []
        for record in value["original_frames"]:
            frame = json.loads(record["raw_original"])
            if encode_identity(frame["case_id"]) != record["id"] or frame["period"] != record["period"]:
                raise ValueError("GATE_ORIGINAL_FRAME_TRANSPORT")
            result["frames"].append(frame)
    elif value["origin"] == "prior_result":
        detail = value["detail"]["some"]
        scope = {key: item if key in {"currency", "purpose"} else decode_identity(item) for key, item in value["scope"].items()}
        result.update(schema_version=detail["schema_version"], scope=scope, policy=deepcopy(value["policy"]), registry=json.loads(value["registry_original"]), research=json.loads(value["research_original"]),
            source_case_id=decode_identity(value["source_case_id"]["some"]), receipts=str(_wire_number(detail["receipts"])), costs=str(_wire_number(detail["costs"])), latched=detail["latched"],
            history=[{"facts": json.loads(record["facts"]), "result": neutral_result(record["result"])} for record in detail["history"]], recognized_entitlement=str(_wire_number(detail["recognized_entitlement"])),
            **{key: [decode_identity(item) for item in detail[key]] for key in SEEN})
    context = {"scope": {key: item if key in {"currency", "purpose"} else decode_identity(item) for key, item in value["scope"].items()},
               "policy": value["policy"], "registry": json.loads(value["registry_original"]), "research": json.loads(value["research_original"])}
    if _state(result, context) != value:
        raise ValueError("GATE_RESTORED_STATE_TRANSPORT")
    return result


def register_ordered_gates():
    reference = _descriptor("ordered-gates", "ordered-gates.spl", "policy.md",
        {"policy": "parameter", "cutoff": "parameter", "comparison": "result", "stage_summary": "detail", "reconciliation": "reconciliation"}, folder=FOLDER,
        state=[{"opening": "history", "closing": "history", "purpose": PURPOSE, "unit": "structured", "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"],
                "movement_kinds": ["transition"], "history_required": False}])
    path = ROOT / reference["locator"]
    descriptor = read_json(path)
    descriptor["id"] = "synthetic:ordered-gates"
    descriptor["policy"].update(id=POLICY, discriminating_cases=["split-reopen6", "latch8-full7-opening0-closing11", "authorized-tie-reversal4", "current-prefix-continuous", "full-gate-video-proxy", "actual-three-period-cumulative8", "unknown-not-zero"])
    for field in ["agreement_id", "participant_id", "pool_id"]:
        descriptor["constraints"].append({"kind": "equals", "path": "inputs.fact_scope." + field, "fields": [], "target": "scope." + ("participant_ids" if field == "participant_id" else field), "value": ""})
    # The participant target is a list in the generic outer interface.
    descriptor["constraints"][-2].update(kind="member_of")
    descriptor["constraints"].append({"kind": "equals", "path": "inputs.fact_scope.asset_id", "fields": [], "target": "inputs.project", "value": ""})
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": "1", **_pin(path)}


def ordered_gate_package(fixture=None, *, reference=None, state_cells=None, mode="final"):
    data = deepcopy(json.loads((FOLDER / "neutral.json").read_text()) if fixture is None else fixture)
    _record(data, {"schema_version", "scope", "policy", "research", "registry", "opening_state", *FRAME}, {"prior_result"})
    if data["schema_version"] != "ordered-gates-neutral/1" or mode not in {"final", "preview"}: raise ValueError("GATE_SCHEMA")
    reference = reference or register_ordered_gates()
    registry = _registry(data["registry"])
    opening = _state(data["opening_state"], data)
    history = data["opening_state"].get("frames", []) if data["opening_state"]["origin"] == "original_history" else [record["facts"] for record in data["opening_state"].get("history", [])]
    frames, originals = [], []
    for source in [*history, {key: data[key] for key in FRAME}]:
        typed, raw = _frame(source, data["registry"])
        _validate_frame_transport(typed, raw, data["registry"])
        frames.append(typed); originals.append(raw)
    scope = _work_scope(data["scope"])
    execution = {key: scope[key] for key in ["agreement_id", "participant_id", "pool_id", "asset_id"]}
    inputs = {"scope": {key: value for key, value in execution.items() if key != "asset_id"} | {"period": data["period"]}, "project": scope["asset_id"], "fact_scope": scope,
              "frames": frames, "original_frames": originals, "registry": registry, "registry_original": _raw(data["registry"]), "research": _research(data["research"]),
              "research_original": _raw(data["research"]), "supplied_opening": opening, "predecessor": {"none": True}}
    cell = {"opening_port": "history", "state_key": canonical({**execution, "purpose": PURPOSE}), "purpose": PURPOSE, "unit": "structured", "scope": execution,
            "boundary": data["period"]["start"], "quantity": opening, "provenance_ref": "disclosed-original-work-history", "scenario_id": "SYNTHETIC-ORDERED-GATES"}
    if "prior_result" in data:
        prior = data["prior_result"]
        _record(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if not isinstance(prior.get("result_ref"), str) or not re.fullmatch(r"result@sha256:[0-9a-f]{64}", prior["result_ref"]):
            raise ValueError("GATE_CANONICAL_PREDECESSOR_REQUIRED")
        inputs["predecessor"] = {"some": {"source_case_id": encode_identity(prior["source_case_id"]), "period": _period(prior["period"]), "closing_state": _state(prior["closing_state"], data)}}
        cell["prior_result_ref"] = prior["result_ref"]
    cells = deepcopy(state_cells) if state_cells is not None else [cell]
    if "prior_result" in data and any(row.get("prior_result_ref") != cell["prior_result_ref"] for row in cells): raise ValueError("GATE_CANONICAL_PREDECESSOR_MISMATCH")
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": "ordered-gate-run", "scenario_id": "SYNTHETIC-ORDERED-GATES", "mode": mode, "period": data["period"], "cutoff": data["cutoff"],
            "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [], "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": {"agreement_id": scope["agreement_id"], "participant_ids": [scope["participant_id"]], "pool_id": scope["pool_id"], "asset_ids": [scope["asset_id"]], "purpose": PURPOSE},
        "inputs": inputs, "parameters": {"policy": deepcopy(data["policy"]), "cutoff": data["cutoff"]}, "evidence": {}, "state_cells": cells,
        "decisions": [{"decision_id": name, "policy_id": POLICY, "policy_revision": "1", "status": "proposed", "evidence_ref": "selected-synthetic-work-gate-policy"}
            for entry in resolve_module(reference, ROOT).closure for name in entry["descriptor"]["policy"]["decision_ids"]]}
    return bind_module_package(package, ROOT)


def _original_json(value):
    """Strict canonical escaped JSON custody, without economic interpretation."""
    def reject(_):
        raise ValueError("GATE_ORIGINAL_JSON")
    def pairs(items):
        result = {}
        for key, item in items:
            if key in result:
                raise ValueError("GATE_ORIGINAL_JSON")
            result[key] = item
        return result
    if type(value) is not str:
        raise ValueError("GATE_ORIGINAL_JSON")
    restored = json.loads(value, parse_float=reject, parse_constant=reject, object_pairs_hook=pairs)
    if _raw(restored) != value:
        raise ValueError("GATE_ORIGINAL_JSON")
    return restored


def validate_prepared_package(package):
    """Recheck full original/typed correspondence at the case execution seam.

    Re-encoding checks custody and duplicated references only. SPL still replays
    all financial results, observations, authority and eligibility predicates.
    """
    inputs, parameters = package["inputs"], package["parameters"]
    _record(inputs, {"scope", "project", "fact_scope", "frames", "original_frames", "registry", "registry_original",
                     "research", "research_original", "supplied_opening", "predecessor"})
    _record(parameters, {"policy", "cutoff"})
    work = inputs["fact_scope"]
    _record(work, SCOPE)
    scope = {key: item if key in {"currency", "purpose"} else decode_identity(item) for key, item in work.items()}
    registry = _original_json(inputs["registry_original"])
    research = _original_json(inputs["research_original"])
    if _work_scope(scope) != work or _registry(registry) != inputs["registry"] or _research(research) != inputs["research"]:
        raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")
    context = {"scope": scope, "policy": parameters["policy"], "registry": registry, "research": research}
    opening = neutral_state(inputs["supplied_opening"])
    if _state(opening, context) != inputs["supplied_opening"]:
        raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")
    cells = package["state_cells"]
    if type(cells) is not list or len(cells) != 1 or cells[0]["quantity"] != inputs["supplied_opening"]:
        raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")
    # Every history original is part of the re-encoded input prefix, not merely
    # a list of retained IDs. The last full original is the current frame.
    if not inputs["original_frames"]:
        raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")
    current = _original_json(inputs["original_frames"][-1]["raw_original"])
    history = opening.get("frames", []) if opening["origin"] == "original_history" else [row["facts"] for row in opening.get("history", [])]
    typed, originals = [], []
    for frame in [*history, current]:
        row, raw = _frame(frame, registry)
        typed.append(row); originals.append(raw)
    if inputs["frames"] != typed or inputs["original_frames"] != originals:
        raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")
    predecessor = inputs["predecessor"]
    if predecessor != {"none": True}:
        _record(predecessor, {"some"})
        prior = predecessor["some"]
        _record(prior, {"source_case_id", "period", "closing_state"})
        neutral_state(prior["closing_state"])
        if (prior["closing_state"] != inputs["supplied_opening"] or not history or
                prior["source_case_id"] != inputs["supplied_opening"]["source_case_id"]["some"] or prior["period"] != history[-1]["period"]):
            raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")
        if not isinstance(cells[0].get("prior_result_ref"), str) or not re.fullmatch(r"result@sha256:[0-9a-f]{64}", cells[0]["prior_result_ref"]):
            raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")
    execution = {key: work[key] for key in ["agreement_id", "participant_id", "pool_id", "asset_id"]}
    _record(cells[0], {"opening_port", "state_key", "purpose", "unit", "scope", "boundary", "quantity", "provenance_ref", "scenario_id"}, {"prior_result_ref"})
    cell_metadata = {"opening_port": "history", "purpose": PURPOSE, "unit": "structured", "scope": execution,
                     "boundary": current["period"]["start"], "state_key": canonical({**execution, "purpose": PURPOSE}),
                     "scenario_id": package["manifest"]["scenario_id"]}
    if opening["boundary"] != current["period"]["start"] or any(cells[0][key] != value for key, value in cell_metadata.items()):
        raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")
    expected_scope = {"agreement_id": work["agreement_id"], "participant_ids": [work["participant_id"]], "pool_id": work["pool_id"], "asset_ids": [work["asset_id"]], "purpose": PURPOSE}
    if (inputs["scope"] != {key: value for key, value in execution.items() if key != "asset_id"} | {"period": current["period"]} or
            inputs["project"] != work["asset_id"] or package["scope"] != expected_scope or parameters["cutoff"] != current["cutoff"] or
            package["manifest"]["period"] != current["period"] or package["manifest"]["cutoff"] != current["cutoff"] or
            package["manifest"]["mode"] not in {"final", "preview"} or package["profile"] != "spl-module/1" or package["evidence"] != {} or
            package["module_ref"]["id"] != "synthetic:ordered-gates" or package["module_ref"]["revision"] != "1"):
        raise ValueError("GATE_PREPARED_PACKAGE_MISMATCH")


def run_ordered_gate_package(package, registry_root=None, *, backend="compare", artifact_dir=None, audit_profile="array-v1"):
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
    except (KeyError, IndexError, TypeError, ValueError, OverflowError, PublicationError):
        compact = audit_profile == "compact-v2"
        result = {"status": "blocked", "results": {}, "statements": [], "detail": [], "closing_state": [],
            "trace": unavailable_trace() if compact else [], "reconciliation": {}, "policy_review": {},
            "manifest": snapshot.get("manifest", {}) if isinstance(snapshot, dict) else {}, "issuance_status": "unissued", "payment_evidence_status": "not_assessed",
            "diagnostics": [{"code": "GATE_PREPARED_PACKAGE_MISMATCH", "message": "Canonical transport rejected bindings that differ from retained complete original facts and opening", "pointer": "inputs.original_frames"}]}
        if artifact_dir is not None:
            publication = (AuditedPublication if compact else ArtifactPublication)(artifact_dir)
            return publication.finish(result, {"results.json": "results", "statement.json": "statements", "detail.json": "detail", "trace.json": "trace", "closing-state.json": "closing_state", "reconciliation.json": "reconciliation", "diagnostics.json": "diagnostics", "policy-review.json": "policy_review"})
        return result
    except BaseException:
        # A cancelled preparation is a new, incomplete invocation. It must not
        # leave the reused destination's older success consumable as this run.
        if artifact_dir is not None:
            (AuditedPublication if audit_profile == "compact-v2" else ArtifactPublication)(artifact_dir)
        raise
    return run_module_package(snapshot, registry_root or ROOT, backend=backend, artifact_dir=artifact_dir, audit_profile=audit_profile)


if __name__ == "__main__":
    reference = register_ordered_gates()
    for mode, name in [("final", "canonical-package.json"), ("preview", "preview-canonical-package.json")]:
        package = ordered_gate_package(reference=reference, mode=mode)
        package["manifest"].update(compiler_build="unbound", runtime_build="unbound", module_closure=[])
        write_json(FOLDER / name, package)
