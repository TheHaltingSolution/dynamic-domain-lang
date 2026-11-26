"""Actual bounded SV audit-stage predecessors; never canonical carry credit."""
from collections import Counter
from copy import deepcopy
from datetime import date
from fractions import Fraction
import hashlib
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oracles.skouras import exact_json, skouras
from scripts import spl_mixed_benchmark as mixed
from scripts import spl_performance_protocol as protocol
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, exact, file_digest, loads, write_json
from spl_compiler.lean_tools import lean_environment
from spl_compiler.parser import parse
from spl_compiler.run import bind_package, project, semantic_digest
from spl_compiler.schema import validate_package
from validation.mixed_workloads import canonical_bytes, generate_mixed


def _shift_day(text, months):
    value = date.fromisoformat(text)
    year, month = divmod(value.year * 12 + value.month - 1 + months, 12)
    return date(year, month + 1, value.day).isoformat()


def funding_control(workload, oracle, original_events):
    """Old funding is an unchanged valuation population, never new cash issues."""
    events = workload["neutral"]["package"]["evidence_events"]
    if canonical_bytes(events) != canonical_bytes(original_events):
        raise ValueError("CHAIN_ORIGINAL_FUNDING_CHANGED")
    used = [identity for row in oracle["titles"] for identity in row["funding_event_ids"]]
    expected = [row["event_id"] for row in original_events]
    if Counter(used) != Counter(expected) or any(count != 1 for count in Counter(used).values()):
        raise ValueError("CHAIN_FUNDING_VALUATION_NOT_ONCE")
    return [{key: exact_json(row[key]) for key in ("asset_id", "participant_funding", "distributor_funding", "total_funding", "funding_event_ids")} for row in oracle["titles"]]


def chain_profile(base):
    """New explicitly authorized synthetic horizon, from the FIRST close."""
    result=deepcopy(base)
    package=result["neutral"]["package"]
    horizon={"start":"2026-01-01","end":"2027-01-01"}
    authority={"profile":"rr03-stage-chain/1","evidence_class":"research_assumption","approved":True,
               "approved_date":"2025-12-15","observed_at":"2025-12-15T00:00:00Z","effective":horizon,
               "scope":{"agreement_id":"sv","pool_id":"pool-1"},
               "selected_assumptions":["continuing synthetic agreement, roles, pool membership and selected interpretation authority over four quarters",
                                       "same economic terms, no intervening amendments or funding changes",
                                       "original funding events remain valuation evidence, never fresh cash issues"],
               "original_horizon":{"start":"2026-01-01","end":"2026-04-01"}}
    identity="rr03-stage-chain-authority@sha256:"+hashlib.sha256(canonical_bytes(authority)).hexdigest()
    package["references"].append({"reference_id":identity,"kind":"source","description":canonical_bytes(authority).decode('utf-8')})
    for agreement in package["agreements"]:
        agreement.update(effective=deepcopy(horizon),version="synthetic-stage-chain-v1",interpretation_ref="rr03-stage-chain-interpretation@1")
        agreement["document_refs"].append(identity)
    for row in package["roles"]:
        row["effective"]=deepcopy(horizon)
    for row in package["mappings"]:
        row.update(effective=deepcopy(horizon),mapping_version="stage-chain-1")
    for interpretation in package["interpretations"]:
        interpretation.update(interpretation_id="rr03-stage-chain-interpretation",version="1")
        for decision in interpretation["decisions"]:
            decision.update(effective=deepcopy(horizon),document_ref=identity)
    result["stage_chain_authority"]={"document":authority,"reference_id":identity,
                                      "sha256":hashlib.sha256(canonical_bytes(authority)).hexdigest()}
    return result


def successor_workload(base, previous_head, previous_wire_sha256, close_index):
    """New original financial rows plus reused original funding valuation facts.

    The caller must obtain previous_head from a completed bounded audit reader;
    this mechanical generator is not a provenance verifier or canonical API.
    """
    if type(close_index) is not int or not 2 <= close_index <= 4:
        raise ValueError("CHAIN_CLOSE_INDEX_2_TO_4")
    if type(previous_wire_sha256) is not str or not re.fullmatch(r"[0-9a-f]{64}", previous_wire_sha256):
        raise ValueError("CHAIN_PREDECESSOR_WIRE_HASH")
    if (previous_head.get("status") != "calculated" or previous_head.get("diagnostics") != []
            or set(previous_head.get("closing", {})) != {"prepayment"}):
        raise ValueError("CHAIN_PREDECESSOR_NOT_CALCULATED")
    result = deepcopy(base)
    neutral = result["neutral"]
    package = neutral["package"]
    old_period = package["manifest"]["period"]
    months = (close_index - 1) * 3
    period = {key: _shift_day(value, months) for key, value in old_period.items()}
    previous_pool=previous_head.get("emissions",{}).get("pool",{})
    policy=package["parameters"]["policy"]
    if any(previous_pool.get(key)!=policy[key] for key in ("agreement_id","participant_id","pool_id")):
        raise ValueError("CHAIN_PREDECESSOR_SCOPE")
    expected_prior_period={key:_shift_day(value,months-3) for key,value in old_period.items()}
    if previous_pool.get("period")!=expected_prior_period or previous_pool["period"]["end"]!=period["start"]:
        raise ValueError("CHAIN_PREDECESSOR_PERIOD_NOT_ADJACENT")
    rename = {}
    for row in package["financial_facts"]:
        for key in ("fact_id", "source_row", "external_event_ref"):
            if key in row:
                rename[row[key]] = f"close-{close_index}:" + row[key]
    for row in package["allocations"]:
        for key in ("allocation_id", "allocation_group_id"):
            rename[row[key]] = f"close-{close_index}:" + row[key]
    for interpretation in package["interpretations"]:
        for decision in interpretation["decisions"]:
            if decision["decision_id"].startswith("RR03-ALLOCATION-"):
                rename[decision["decision_id"]] = f"close-{close_index}:" + decision["decision_id"]
    def transport(value):
        if isinstance(value, dict): return {key: transport(item) for key, item in value.items()}
        if isinstance(value, list): return [transport(item) for item in value]
        return rename.get(value, value) if isinstance(value, str) else value
    neutral = transport(neutral)
    result["neutral"] = neutral
    package = neutral["package"]
    scenario = package["manifest"]["scenario_id"] + f"-close-{close_index}"
    package["manifest"].update(period=period, scenario_id=scenario, run_id=scenario + "-run",
                               cutoff=_shift_day(package["manifest"]["cutoff"][:10], months) + package["manifest"]["cutoff"][10:])
    package["parameters"]["policy"]["period"] = deepcopy(period)
    package["parameters"]["funding_snapshot"]["as_of"] = period["start"]
    for row in package["financial_facts"]:
        row["temporal_basis"]["date"] = _shift_day(row["temporal_basis"]["date"], months)
        row["dates"] = {key: _shift_day(value, months) for key, value in row["dates"].items()}
        row["batch_ref"]["batch_id"] = f"close-{close_index}:authored"
    for rows in (package["allocations"], neutral["allocation_authorities"]):
        for row in rows:
            row.update(effective=deepcopy(period), scenario_id=scenario)
    quantity = previous_head["closing"]["prepayment"]
    # Actual native IR outcome JSON encodes this checked Money<USD> port as a
    # canonical Rat, unlike tagged input bindings. Its unit comes from the
    # pinned checked SV source and the unchanged canonical USD state slot.
    if type(quantity) is not dict or set(quantity) != {"numerator", "denominator"} or exact(quantity)<0:
        raise ValueError("CHAIN_PREDECESSOR_NATIVE_RAT_SHAPE")
    reference = "audited-stage-wire@sha256:" + previous_wire_sha256
    package["references"].append({"reference_id": reference, "kind": "source", "description": "Actual completed prior audit-stage output; not a canonical financial publication"})
    for cell in package["state_cells"]:
        cell.update(quantity=deepcopy(quantity), boundary=period["start"], scenario_id=scenario, provenance_ref=reference)
    batch = package["source_batches"][0]
    batch.update(batch_id=f"close-{close_index}:authored", ingested_at=package["manifest"]["cutoff"],
                 sha256=hashlib.sha256(canonical_bytes(package["financial_facts"])).hexdigest())
    sources = {key: package[key] for key in ("financial_facts", "evidence_events", "allocations")}
    package["adapter"].update(source_fixture=scenario, source_digest=hashlib.sha256(canonical_bytes(sources)).hexdigest())
    result["source_records"] = sources
    result["stage_predecessor"] = {"wire_sha256": previous_wire_sha256, "period": previous_head["emissions"]["pool"]["period"],
                                    "scope": "actual audited stage state only; no canonical result/carry authority"}
    return result


def close_counts(workload, index):
    counts = workload["counts"]
    facts, funding = counts["financial_facts"], counts["funding_evidence_events"]
    return {**counts, "close_index": index, "new_financial_originals": facts,
            "new_funding_originals": funding if index == 1 else 0, "reused_funding_originals": 0 if index == 1 else funding,
            "distinct_originals_in_chain_through_close": index * facts + funding,
            "stage_chain_authority_metadata_records":1,"predecessor_reference_metadata_records":0 if index==1 else 1}


def run_close(output, workload, pins, original_funding):
    """Reuse public helpers, with independent controls before all projection."""
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    report = {"status": "failed", "stages": {}, "audited_head": {}, "audited_closing_state": [], "canonical_close_credit": False,
              "scope": "standalone audit-stage close, not canonical finalization"}
    _, env = lean_environment()
    source = ROOT / "cases/sv/sv01.spl"
    def stage(name, action):
        started = time.perf_counter(); cpu = time.process_time_ns()
        try:
            value = action()
        except Exception as error:
            report["stages"][name]={"status":"failed","error":{"type":type(error).__name__,"message":str(error)}}
            report.setdefault("first_failure",name)
            raise
        report["stages"][name] = {"status": "passed", "wall_seconds": str(time.perf_counter()-started), "parent_cpu_seconds": str(Fraction(time.process_time_ns()-cpu,1000000000)),
                                  "memory_scope": "parent preparation, outside per-child256MiB guard"}
        return value
    try:
        protocol.require_pins(pins)
        oracle = stage("independent_original_fact_oracle", lambda: skouras(workload["neutral"]))
        report["funding_valuation_control"] = funding_control(workload,oracle,original_funding)
        expected = mixed.target_expected(oracle)
        write_json(output / "neutral-original.json", workload["neutral"])
        write_json(output / "independent-oracle.json", exact_json(oracle))
        write_json(output / "independent-target-expected.json", expected)
        bound = stage("canonical_binding", lambda: bind_package(workload["neutral"]["package"],source))
        stage("canonical_schema_validation",lambda:validate_package(bound))
        rebound = stage("manifest_hash_recheck",lambda:bind_package(bound,source))
        if rebound["manifest"] != bound["manifest"]:
            raise ValueError("CHAIN_MANIFEST_CHANGED")
        inputs, aliases, lineage, dispositions = stage("projection", lambda:project(bound))
        openings = {"prepayment":aliases["sv/participant-prepayment/main-pool"]}
        stage("independent_projection_control",lambda:mixed.check_projection(workload,oracle,inputs,openings,lineage,dispositions))
        report["semantic_digest"] = stage("semantic_hash",lambda:semantic_digest(bound,inputs,openings))
        write_json(output / "canonical-package.json",bound)
        write_json(output / "bindings.json",{"inputs":inputs,"openings":openings})
        write_json(output / "source-to-target-lineage.json",lineage)
        write_json(output / "input-dispositions.json",dispositions)
        (output / "generated-source-batch.json").write_bytes(canonical_bytes(workload["neutral"]["package"]["financial_facts"]))
        (output / "original-source-records.json").write_bytes(canonical_bytes(workload["source_records"]))
        if file_digest(output/"generated-source-batch.json")!=bound["source_batches"][0]["sha256"] or file_digest(output/"original-source-records.json")!=bound["adapter"]["source_digest"]:
            raise ValueError("CHAIN_ORIGINAL_SOURCE_BYTES_CHANGED")
        report["input_bytes"] = {name:(output/name).stat().st_size for name in ("neutral-original.json","bindings.json","canonical-package.json")}
        reference = protocol.measured([sys.executable, ROOT / "scripts/spl_mixed_benchmark.py", "--reference-worker", source, output / "bindings.json"],output/"reference",env)
        report["stages"]["reference"] = reference
        if reference["status"]=="passed":
            report["reference_control"] = mixed.check_reference_worker(loads((output/"reference/stdout.bin").read_bytes()),expected)
        else:
            report["reference_control"] = "resource_or_process_failure"
        if report["reference_control"]!="passed":report.setdefault("first_failure","reference")
        target = protocol.measured([ROOT / ".lake/build/bin/spl_sv.exe",output/"bindings.json"],output/"target",env)
        report["stages"]["target"] = target
        if target["status"]=="passed":
            mixed.check_target(loads((output/"target/stdout.bin").read_bytes()),expected)
            target["independent_control"]="passed"
        else:report.setdefault("first_failure","target")
        audit = protocol.measured([ROOT / ".lake/build/bin/spl_trace_stream.exe",source,output/"bindings.json","--compact-v2"],output/"audit",env)
        report["stages"]["audit"] = audit
        if audit["status"]!="passed":
            report.setdefault("first_failure","audit")
            raise ValueError("CHAIN_REQUIRED_AUDIT_FAILED")
        reader = protocol.measured([sys.executable,ROOT/"scripts/spl_native_trace_transport.py",output/"audit/stdout.bin"],output/"reader",env)
        report["stages"]["reader"] = reader
        if reader["status"]!="passed":
            report.setdefault("first_failure","reader")
            raise ValueError("CHAIN_REQUIRED_READER_FAILED")
        validated = loads((output/"reader/stdout.bin").read_bytes())
        mixed.check_target(validated["head"],expected)
        audit["independent_control"]="passed"
        report["trace_validation"]=validated
        if target["status"]!="passed" or report["reference_control"]!="passed":
            report.setdefault("first_failure","target_or_reference")
            raise ValueError("CHAIN_REQUIRED_FINANCIAL_CONTROL_FAILED")
        protocol.require_pins(pins)
        report.update(status="passed",audited_head=validated["head"],audited_closing_state=validated["head"]["closing"],
                      predecessor_wire_sha256=validated["transport_sha256"])
    except Exception as error:
        report["error"]={"type":type(error).__name__,"message":str(error)}
    for name in ("reference","target","audit","reader"):
        report["stages"].setdefault(name,{"status":"not_executed","reason":"earlier_required_stage_failed"})
    write_json(output/"summary.json",report)
    return report


def run_chain(output, records, count, pins, *, prerequisite, seed=20261123):
    if records not in {100,1000} or count!=4:
        raise ValueError("CHAIN_BOUNDS_100_OR_1000_FOUR_CLOSES")
    protocol.validate_mixed_report(protocol.load_report(prerequisite),protocol.mixed_pins(pins),records,seed)
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    original=generate_mixed(records,seed=seed)
    original_bytes=canonical_bytes(original)
    base=chain_profile(original)
    write_json(output/"stage-chain-authority.json",base["stage_chain_authority"])
    write_json(output/"base-default-original.json",original)
    funding=deepcopy(base["neutral"]["package"]["evidence_events"])
    report={"status":"running","records":records,"closes":[],"canonical_close_credit":False,
            "prerequisite":str(Path(prerequisite).resolve()),
            "scope":"four actual sequential audited-stage closes; no canonical finalization/carry credit",
            "funding_assumption":"same complete original funding valuation, explicitly no intervening funding changes; old50/5 events reused without fresh financial IDs"}
    previous=None;failed=False;baseline_funding=None
    for index in range(1,count+1):
        if failed:
            report["closes"].append({"close":index,"status":"not_executed","audited_closing_state":[],"reason":"actual_audited_predecessor_not_completed"})
            continue
        workload=base if index==1 else successor_workload(base,previous["audited_head"],previous["predecessor_wire_sha256"],index)
        current=run_close(output/f"close-{index}",workload,pins,funding)
        current.update(close=index,counts=close_counts(workload,index))
        report["closes"].append(current)
        if current["status"]!="passed":
            failed=True
        else:
            if baseline_funding is None:baseline_funding=current["funding_valuation_control"]
            if current["funding_valuation_control"]!=baseline_funding:
                current.update(status="failed",error={"message":"CHAIN_FUNDING_VALUATION_CHANGED"},audited_head={},audited_closing_state=[])
                failed=True
            previous=current
        write_json(output/"summary.json",report)
    if canonical_bytes(original)!=original_bytes or canonical_bytes(generate_mixed(records,seed=seed))!=original_bytes:raise ValueError("CHAIN_DEFAULT_GENERATOR_MUTATED")
    report.update(status="failed" if failed else "passed",default_generator_unchanged=True)
    write_json(output/"summary.json",report)
    return report
