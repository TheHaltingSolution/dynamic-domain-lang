"""Measure bounded original-record RR-03 mixes through independent controls.

The canonical source boundary is measured separately from native calculation
and compact audit transport. This is not the default finalization wrapper or an
isolated pure-settlement benchmark. Build native binaries before running.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oracles.skouras import exact_json, skouras
from scripts.spl_stage_benchmark import measured_python, run_process
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, exact, file_digest, loads, money, number, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import lean_environment
from spl_compiler.parser import parse
from spl_compiler.run import bind_package, identities, normalize_target, project, semantic_digest
from spl_compiler.schema import validate_package
from validation.mixed_workloads import canonical_bytes, generate_mixed


def target_expected(oracle):
    """Format independent answers for comparison; never supply them to inputs."""
    pool = oracle["pool"]
    fields = ("asset_id", "cash", "fee", "allowed_cost", "basis", "share", "earned")
    return {"status": "calculated", "emissions": {
        "titles": [{key: number(row[key]) if isinstance(row[key], Fraction) else row[key] for key in fields} for row in oracle["titles"]],
        "pool": {**{key: pool[key] for key in ("agreement_id", "participant_id", "pool_id", "period")},
                 "earned": number(pool["earned"]), "recouped": number(pool["recovered"]), "payable": number(pool["payable"])}},
        "closing": {"prepayment": number(pool["closing_prepayment"])}, "diagnostic_codes": []}


def check_target(outcome, expected):
    actual = normalize_target(outcome)
    actual = {"status": actual["status"], "emissions": actual["emissions"], "closing": actual["closing"],
              "diagnostic_codes": [row["code"] for row in actual["diagnostics"]]}
    if canonical(actual) != canonical(expected):
        raise ValueError("MIXED_INDEPENDENT_TITLE_POOL_SCOPE_STATE_CONTROL")


def check_projection(workload, oracle, inputs, openings, lineage, dispositions):
    """Check projection against independent original-fact answers and identities."""
    package = workload["neutral"]["package"]
    original = {row["fact_id"]: row for row in package["financial_facts"]}
    if canonical(inputs["policy"]) != canonical(package["parameters"]["policy"]):
        raise ValueError("MIXED_PROJECTED_POLICY")
    receipts = {row["fact_id"]: row for row in inputs["receipts"]}
    expected_receipts = {}
    for row in oracle["receipt_contributions"]:
        identity = row["allocation_id"] or row["source_fact_id"]
        expected_receipts[identity] = {"fact_id": identity, "asset_id": row["asset_id"],
                                       "amount": money(row["amount"]), "cash_received_date": row["cash_received_date"]}
        if row["parent_fact_id"] != original[row["source_fact_id"]].get("parent_fact_id", ""):
            raise ValueError("MIXED_ORIGINAL_PARENT_LINK")
    if len(receipts) != len(inputs["receipts"]) or canonical(receipts) != canonical(expected_receipts):
        raise ValueError("MIXED_PROJECTED_RECEIPTS")
    selected = {row["fact_id"]: row for row in package["parameters"]["cost_decisions"] if row["eligible"]}
    expected_costs = {identity: {"fact_id": identity, "asset_id": original[identity]["asset_id"],
                                "amount": original[identity]["amount"], "incurred_date": original[identity]["dates"]["incurred_date"],
                                "eligibility_decision_id": selection["decision_id"]} for identity, selection in selected.items()}
    costs = {row["fact_id"]: row for row in inputs["eligible_costs"]}
    if len(costs) != len(inputs["eligible_costs"]) or canonical(costs) != canonical(expected_costs):
        raise ValueError("MIXED_PROJECTED_COSTS")
    expected_pictures = [{"asset_id": row["asset_id"], "contribution_present": row["branch"] == "funded",
                          "funding_share": number(row["share"] if row["branch"] == "funded" else Fraction())} for row in oracle["titles"]]
    if canonical(inputs["pictures"]) != canonical(expected_pictures):
        raise ValueError("MIXED_PROJECTED_FUNDING")
    if canonical(openings) != canonical({"prepayment": money(oracle["pool"]["opening_prepayment"])}):
        raise ValueError("MIXED_PROJECTED_OPENING")
    lineage_by_id = {row["view_id"]: row for row in lineage}
    if len(lineage_by_id) != len(lineage) or set(lineage_by_id) != set(receipts) | set(costs):
        raise ValueError("MIXED_PROJECTED_LINEAGE_POPULATION")
    contribution_by_id = {(row["allocation_id"] or row["source_fact_id"]): row for row in oracle["receipt_contributions"]}
    for identity, row in lineage_by_id.items():
        source = contribution_by_id[identity]["source_fact_id"] if identity in contribution_by_id else identity
        if row["fact_ids"] != [source] or row["source_rows"] != [original[source]["source_row"]]:
            raise ValueError("MIXED_PROJECTED_LINEAGE_SOURCE")
        if identity in contribution_by_id and contribution_by_id[identity]["allocation_id"]:
            allocation = next(a for a in package["allocations"] if a["allocation_id"] == identity)
            if row.get("allocation_id") != identity or row.get("policy_ref") != allocation["authority_ref"] or exact(row["weight"]) != exact(allocation["weight"]):
                raise ValueError("MIXED_PROJECTED_ALLOCATION_LINEAGE")
    actual_dispositions = {row["fact_id"]: row for row in dispositions}
    if len(actual_dispositions) != len(dispositions) or set(actual_dispositions) != set(original):
        raise ValueError("MIXED_FACT_DISPOSITION_POPULATION")
    excluded_cash = {row["fact_id"] for row in oracle["excluded_receipts"]}
    cost_controls = {row["fact_id"]: row for row in oracle["cost_dispositions"]}
    for identity, fact in original.items():
        disposition = actual_dispositions[identity]
        included = (identity not in excluded_cash if fact["event_kind"] == "cash_receipt" else
                    cost_controls[identity]["included"] if fact["event_kind"] == "incurred_cost" else False)
        expected_measure = "eligible_costs" if fact["event_kind"] == "incurred_cost" else "cash_receipts"
        if disposition["disposition"] != ("included" if included else "excluded") or disposition["measure"] != expected_measure:
            raise ValueError("MIXED_FACT_DISPOSITION_CONTROL")
    return {"status": "passed", "projected_receipts": len(receipts), "projected_eligible_costs": len(costs),
            "projected_pictures": len(inputs["pictures"]), "source_to_target_lineage_rows": len(lineage),
            "original_fact_dispositions": len(dispositions),
            "verified_cash_to_invoice_parent_links": sum("parent_fact_id" in row for row in original.values()),
            "parent_scope": "invoice ancestry remains in the validated original graph; projected typed receipts retain original cash IDs/lineage joins"}


def dependency_files():
    files = [ROOT / path for path in ["validation/mixed_workloads.py", "scripts/spl_mixed_benchmark.py",
             "scripts/spl_stage_benchmark.py", "scripts/spl_benchmark.py", "scripts/spl_native_trace_transport.py", "scripts/spl_trace_transport.py",
             "oracles/skouras.py", "cases/sv/neutral-oracle.json", "cases/sv/sv01.spl", "Demos/SV.lean", "Demos/TraceStream.lean", "SPL.lean", "lean-toolchain", "lakefile.toml"]]
    files += sorted((ROOT / "SPL").glob("*.lean")) + sorted((ROOT / "spl_compiler").glob("*.py"))
    files += sorted((ROOT / "schemas").glob("*.json"))
    return sorted(set(files))


def check_prerequisite(previous, pins, seed, budgets, transport="compact-v1", profile_stages=False, required_records=100):
    if required_records not in {100, 1000}:
        raise ValueError("MIXED_PREREQUISITE_COHORT")
    if (not isinstance(previous, dict) or previous.get("format") != "spl-mixed-performance/1"
            or previous.get("status") != "passed" or previous.get("counts", {}).get("raw_original_records") != required_records
            or previous.get("required_audit_completed") is not True or previous.get("seed") != seed
            or previous.get("transport") != transport
            or previous.get("profile_stages", False) != profile_stages
            or previous.get("dependency_pins") != pins or previous.get("budgets") != budgets
            or not isinstance(previous.get("native_samples"), list) or not previous["native_samples"]
            or any(not isinstance(sample, dict) or sample.get("status") != "passed"
                   or any(sample.get(stage, {}).get("status") != "passed" for stage in ("target", "audit", "reader"))
                   or any(sample.get(stage, {}).get("independent_control") != "passed" for stage in ("target", "audit"))
                   for sample in previous["native_samples"])):
        raise ValueError(f"MIXED_{1000 if required_records == 100 else 10000}_REQUIRES_SUCCESSFUL_MATCHING_{required_records}_COHORT")


def validate_profile(profile, node_count, payload_count):
    """Strict complete compact-run profile; nested intervals are never summed."""
    fields = {"format", "status", "run_elapsed_ns", "clock_pairs", "empty_clock_probe", "intervals", "scope"}
    if (not isinstance(profile, dict) or set(profile) != fields
            or profile["format"] != "spl-native-audit-profile/1" or profile["status"] != "completed"
            or not isinstance(profile["scope"], str) or not profile["scope"]):
        raise ValueError("MIXED_NATIVE_PROFILE_ENVELOPE")

    def natural(value):
        if type(value) is not int or value < 0:
            raise ValueError("MIXED_NATIVE_PROFILE_CLOCK")
        return value

    elapsed = natural(profile["run_elapsed_ns"])
    stages = {}
    if not isinstance(profile["intervals"], list):
        raise ValueError("MIXED_NATIVE_PROFILE_INTERVALS")
    for row in profile["intervals"]:
        if (not isinstance(row, dict) or set(row) != {"stage", "calls", "elapsed_ns"}
                or not isinstance(row["stage"], str) or row["stage"] in stages
                or natural(row["calls"]) == 0 or natural(row["elapsed_ns"]) > elapsed):
            raise ValueError("MIXED_NATIVE_PROFILE_INTERVAL")
        stages[row["stage"]] = row
    once = {"frontend_source_read", "frontend_manifest_read", "frontend_parse", "frontend_link", "frontend_check",
            "frontend_elaborate", "frontend_validate_ir", "interpreter_elaborate", "binding_read", "binding_parse_decode",
            "interpreter_graph", "graph_validate", "outcome_head_json", "graph_order", "stdout_flush", "transport_total"}
    per_node = {"node_json", "field_encoding_accounting", "dependency_indices", "sharing_and_payload_records", "index_update"}
    expected = {**dict.fromkeys(once, 1), **dict.fromkeys(per_node, node_count),
                "record_format": node_count + payload_count + 2, "stdout_write": node_count + payload_count + 2}
    if set(stages) != set(expected) or any(stages[name]["calls"] != calls for name, calls in expected.items()):
        raise ValueError("MIXED_NATIVE_PROFILE_STAGE_COUNTS")
    if natural(profile["clock_pairs"]) != sum(row["calls"] for row in stages.values()):
        raise ValueError("MIXED_NATIVE_PROFILE_CLOCK_COUNTS")
    probe = profile["empty_clock_probe"]
    if (not isinstance(probe, dict) or set(probe) != {"pairs", "pair_span_ns", "elapsed_ns"}
            or natural(probe["pairs"]) != 1000 or natural(probe["pair_span_ns"]) > natural(probe["elapsed_ns"])):
        raise ValueError("MIXED_NATIVE_PROFILE_PROBE")
    # Each named transport child is bounded by its inclusive transport parent.
    transport_children = per_node | {"graph_validate", "outcome_head_json", "graph_order", "record_format", "stdout_write", "stdout_flush"}
    if any(stages[name]["elapsed_ns"] > stages["transport_total"]["elapsed_ns"] for name in transport_children):
        raise ValueError("MIXED_NATIVE_PROFILE_NESTING")
    return profile


def equal_wire_files(actual, expected):
    """Compare complete files directly with constant-size parent buffers."""
    digest = hashlib.sha256()
    with Path(actual).open("rb") as left, Path(expected).open("rb") as right:
        while True:
            chunk = left.read(65536)
            if chunk != right.read(65536):
                raise ValueError("MIXED_AUDIT_WIRE_CHANGED")
            if not chunk:
                return digest.hexdigest()
            digest.update(chunk)


def reference_worker(source, bindings):
    """Evaluate inside the bounded child; serialize financial outputs, not trace.

    The evaluator still builds its ordinary complete-or-resource-limited trace.
    Omitting that trace from this diagnostic summary is not native audit credit.
    """
    from spl_compiler.model import encode_value
    checked = check_schedule(parse(Path(source).read_text(encoding="utf-8")))
    values = loads(Path(bindings).read_bytes())
    outcome = evaluate(checked, values["inputs"], values["openings"])
    return {"format": "spl-mixed-reference-summary/1", "trace_nodes_observed": len(outcome.trace),
            "scope": "ordinary evaluator trace built in child; summary serializes financial outputs and diagnostics only",
            "outcome": {"status": outcome.status, "emissions": encode_value(outcome.emissions),
                        "closing": encode_value(outcome.closing), "diagnostics": outcome.diagnostics}}


def check_reference_worker(summary, expected):
    if (not isinstance(summary, dict) or set(summary) != {"format", "trace_nodes_observed", "scope", "outcome"}
            or summary["format"] != "spl-mixed-reference-summary/1" or not isinstance(summary["scope"], str)
            or type(summary["trace_nodes_observed"]) is not int or not 0 <= summary["trace_nodes_observed"] <= 100000):
        raise ValueError("MIXED_REFERENCE_SUMMARY")
    outcome = summary["outcome"]
    if (isinstance(outcome, dict) and outcome.get("status") == "blocked"
            and outcome.get("emissions") == {} and outcome.get("closing") == {}
            and [row.get("code") for row in outcome.get("diagnostics", [])] == ["RESOURCE_LIMIT"]):
        return "resource_limited"
    check_target(outcome, expected)
    return "passed"


def audit_head(path):
    """Inspect bounded first-record evidence, never credit an incomplete trace."""
    with Path(path).open("rb") as stream:
        first = stream.readline(8 * 1024 * 1024 + 1)
    if len(first) > 8 * 1024 * 1024 or not first.endswith(b"\n"):
        raise ValueError("MIXED_AUDIT_HEADER_LIMIT_OR_INCOMPLETE")
    header = loads(first)
    if (not isinstance(header, dict) or header.get("record") != "header"
            or header.get("format") not in {"spl-native-trace-stream/0.1", "spl-native-trace-stream/0.2"}
            or not isinstance(header.get("head"), dict)):
        raise ValueError("MIXED_AUDIT_HEADER")
    head = header["head"]
    return {"head": head, "scope": "first record only; trace completion/nodes unverified here",
            "blocked_without_money_or_state": head.get("status") == "blocked" and head.get("emissions") == {} and head.get("closing") == {}}


def sequential_dependency_plan(first_complete):
    """No successor can be inferred from an incomplete first close."""
    return {str(count): [{"close": 1, "status": "completed" if first_complete else "failed"}] +
                        [{"close": index, "status": "not_executed", "closing_state": [],
                          "reason": "requires_actual_audited_predecessor_and_separate_execution" if first_complete else "audited_predecessor_not_completed"}
                         for index in range(2, count + 1)] for count in (4, 8)}


def benchmark(output, records=100, *, seed=20261123, repeats=1, timeout=60,
              max_output_bytes=64 * 1024 * 1024, max_working_set_bytes=256 * 1024 * 1024, prerequisite=None, transport="compact-v1",
              profile_stages=False, wire_reference=None):
    if records not in {100, 1000, 10000} or not 1 <= repeats <= 3 or not 0 < timeout <= 180:
        raise ValueError("Mixed bounds: records100/1000/10000,repeats1..3,timeout1..180")
    if records == 10000 and repeats != 1:
        raise ValueError("Initial mixed10000 probe permits exactly one sample")
    if not 1024 <= max_output_bytes <= 64 * 1024 * 1024 or not 1024 * 1024 <= max_working_set_bytes <= 1024 * 1024 * 1024:
        raise ValueError("Mixed budgets require stdout1KiB..64MiB,working set1MiB..1GiB")
    if records >= 1000 and os.name != "nt":
        raise ValueError("Mixed1000/10000 require sampled Windows memory-budget enforcement")
    if transport not in {"compact-v1", "compact-v2"}:
        raise ValueError("Mixed transport must be compact-v1 or compact-v2")
    if type(profile_stages) is not bool:
        raise ValueError("Mixed profiling flag must be boolean")
    suffix = ".exe" if os.name == "nt" else ""
    binaries = {name: ROOT / ".lake/build/bin" / (name + suffix) for name in ("spl", "spl_sv", "spl_trace_stream")}
    if any(not path.is_file() for path in binaries.values()):
        raise ValueError("Build pinned spl,spl_sv,spl_trace_stream before measurement")
    sources = dependency_files()
    pins = {path.relative_to(ROOT).as_posix(): file_digest(path) for path in sources}
    pins.update({"binary:" + name: file_digest(path) for name, path in binaries.items()})
    pins["python_executable"] = file_digest(Path(sys.executable))
    budgets = {"child_timeout_seconds": timeout, "child_stdout_bytes": max_output_bytes,
               "child_sampled_working_set_bytes": max_working_set_bytes}
    if records >= 1000:
        required_records = 100 if records == 1000 else 1000
        if prerequisite is None:
            raise ValueError(f"MIXED_{records}_REQUIRES_SUCCESSFUL_MATCHING_{required_records}_COHORT")
        check_prerequisite(json.loads(Path(prerequisite).read_text(encoding="utf-8")), pins, seed, budgets,
                           transport, profile_stages, required_records)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    for path in sources:
        destination = output / "sources" / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    source = output / "Source.spl"
    source.write_bytes((ROOT / "cases/sv/sv01.spl").read_bytes())
    before = identities()
    _, env = lean_environment()
    report = {"format": "spl-mixed-performance/1", "status": "running", "seed": seed, "transport": transport, "profile_stages": profile_stages,
              "dependency_pins": pins, "budgets": budgets, "kernel_identities": list(before),
              "python": sys.version, "platform": platform.platform(), "logical_cpus": os.cpu_count(),
              "processor": os.environ.get("PROCESSOR_IDENTIFIER", platform.processor()),
              "lean_toolchain": (ROOT / "lean-toolchain").read_text().strip(), "lean_executable": lean_environment()[0],
              "lean_version": subprocess.run([lean_environment()[0], "--version"], env=env, capture_output=True,
                                              text=True, check=True, timeout=10).stdout.strip(),
              "stages": {}, "native_samples": [], "required_audit_completed": False, "reference_control": "not_executed",
              "audited_financial_outputs": {}, "audited_closing_state": [],
              "parent_preparation_scope": "Finite generated cohort100/1000/10000; per-stage Python traced peaks, not an enforced whole-parent256MiB cap. Child caps exclude parent, retained inputs and filesystem cache.",
              "prerequisite": str(Path(prerequisite).resolve()) if prerequisite else None,
              "limitations": ["Synthetic original-record development mix, not production distribution or capacity.",
                              "Lineage bracket is invoice financial facts, a separate amount space and actual guard-counted objects.",
                              "Native target includes startup,decode,settlement and result serialization; pure timer absent.",
                              "Current native emission must equal Demos/SV.lean; executable/source correspondence relies on the prior pinned Lake build.",
                              "Native compact audit and independent reader are separate timed child processes.",
                              "Canonical binding/validation/projection are measured; default wrapper finalization is not executed.",
                              "Python traced allocation peaks and child peak working sets have different scopes.",
                              "Financial fact availability is the supplied full snapshot, without invented observed_at fields.",
                              "Sampled20ms Windows memory budget permits transient overshoot; unavailable enforcement is labelled."]}
    write_json(output / "summary.json", report)
    started = time.perf_counter()
    try:
        workload, report["stages"]["original_record_generation"] = measured_python(lambda: generate_mixed(records, seed=seed))
        report["counts"] = workload["counts"]
        original_bytes = canonical_bytes(workload["neutral"])
        if len(original_bytes) > 64 * 1024 * 1024:
            raise ValueError("MIXED_ORIGINAL_INPUT_BYTE_LIMIT")
        write_json(output / "neutral-original.json", workload["neutral"])
        write_json(output / "workload-counts.json", {"counts": workload["counts"], "scope": workload["count_scope"], "limits": workload["limitations"]})
        (output / "generated-source-batch.json").write_bytes(canonical_bytes(workload["neutral"]["package"]["financial_facts"]))
        (output / "original-source-records.json").write_bytes(canonical_bytes(workload["source_records"]))
        oracle, report["stages"]["independent_original_fact_oracle"] = measured_python(lambda: skouras(workload["neutral"]))
        write_json(output / "independent-oracle.json", exact_json(oracle))
        expected = target_expected(oracle)
        write_json(output / "independent-target-expected.json", expected)
        bound, report["stages"]["canonical_binding_and_dependency_hashes"] = measured_python(lambda: bind_package(workload["neutral"]["package"], source))
        _, report["stages"]["canonical_schema_validation"] = measured_python(lambda: validate_package(bound))
        rebound, report["stages"]["manifest_hash_verification"] = measured_python(lambda: bind_package(bound, source))
        if rebound["manifest"] != bound["manifest"] or rebound["incorporated_policies"] != bound["incorporated_policies"]:
            raise ValueError("MIXED_MANIFEST_VERIFICATION")
        projected, report["stages"]["canonical_projection"] = measured_python(lambda: project(bound))
        inputs, aliases, lineage, dispositions = projected
        checked, report["stages"]["python_frontend"] = measured_python(lambda: check_schedule(parse(source.read_text(encoding="utf-8"))))
        alias_names = {row["alias"]: row["name"] for row in checked.schedule["declarations"] if row["kind"] == "opening"}
        if set(alias_names) != set(aliases):
            raise ValueError("MIXED_OPENING_ALIAS")
        openings = {alias_names[name]: value for name, value in aliases.items()}
        report["projection_control"], report["stages"]["independent_projection_controls"] = measured_python(lambda: check_projection(workload, oracle, inputs, openings, lineage, dispositions))
        semantic, report["stages"]["canonical_semantic_hash"] = measured_python(lambda: semantic_digest(bound, inputs, openings))
        report["semantic_run_digest"] = semantic
        write_json(output / "canonical-package.json", bound)
        write_json(output / "bindings.json", {"inputs": inputs, "openings": openings})
        write_json(output / "source-to-target-lineage.json", lineage)
        write_json(output / "input-dispositions.json", dispositions)
        report["input_bytes"] = {name: (output / name).stat().st_size for name in ["neutral-original.json", "canonical-package.json", "bindings.json", "generated-source-batch.json", "original-source-records.json"]}
        if file_digest(output / "generated-source-batch.json") != bound["source_batches"][0]["sha256"] or file_digest(output / "original-source-records.json") != bound["adapter"]["source_digest"]:
            raise ValueError("MIXED_ARCHIVED_SOURCE_BYTES")
        if records == 10000:
            measurement = run_process([sys.executable, ROOT / "scripts/spl_mixed_benchmark.py", "--reference-worker",
                                       source, output / "bindings.json"], output / "reference-child", env,
                                      timeout, max_output_bytes, max_working_set_bytes)
            report["stages"]["python_reference_evaluation"] = measurement
            if measurement["status"] == "passed":
                try:
                    summary = loads((output / "reference-child/stdout.bin").read_bytes())
                    report["reference_control"] = check_reference_worker(summary, expected)
                    report["reference_summary"] = summary
                except Exception as error:
                    report["reference_control"] = "failed"
                    measurement["validation_error"] = {"type": type(error).__name__, "message": str(error)}
            else:
                report["reference_control"] = "resource_or_process_failure"
        else:
            reference, report["stages"]["python_reference_evaluation"] = measured_python(lambda: evaluate(checked, inputs, openings).to_dict())
            check_target(reference, expected)
            report["reference_control"] = "passed"
            write_json(output / "reference-result.json", reference)
        preparation = run_process([binaries["spl"], "compile", source, output / "Generated.lean"], output / "native-emission", env, timeout, max_output_bytes, max_working_set_bytes)
        report["native_emission"] = preparation
        if preparation["status"] != "passed" or (output / "Generated.lean").read_bytes() != (ROOT / "Demos/SV.lean").read_bytes():
            raise ValueError("MIXED_EMITTED_SOURCE_OR_PREBUILT_TARGET_MISMATCH")
        for index in range(repeats):
            sample = {"sample": index + 1, "status": "failed"}
            report["native_samples"].append(sample)
            audit_command = [binaries["spl_trace_stream"], source, output / "bindings.json",
                             "--compact-v2" if transport == "compact-v2" else "--compact"]
            for phase, command in (("target", [binaries["spl_sv"], output / "bindings.json"]),
                                   ("audit", audit_command + (["--profile-stages"] if profile_stages else []))):
                if phase == "audit" and profile_stages:
                    sample["audit_unprofiled"] = run_process(audit_command, output / f"audit-unprofiled-{index:02d}",
                                                             env, timeout, max_output_bytes, max_working_set_bytes)
                destination = output / f"{phase}-{index:02d}"
                measurement = run_process(command, destination, env, timeout, max_output_bytes, max_working_set_bytes)
                sample[phase] = measurement
                measurement["independent_control"] = "not_checked"
                if phase == "audit":
                    try:
                        sample["audit_first_record_evidence"] = audit_head(destination / "stdout.bin")
                    except Exception as error:
                        sample["audit_first_record_evidence"] = {"status": "unavailable", "error": str(error)}
                if measurement["status"] == "passed":
                    try:
                        if phase == "audit":
                            reader = run_process([sys.executable, ROOT / "scripts/spl_native_trace_transport.py", destination / "stdout.bin",
                                                  "--max-input-bytes", str(max_output_bytes)], destination / "reader", env, timeout, 1024 * 1024, max_working_set_bytes)
                            sample["reader"] = reader
                            if reader["status"] != "passed":
                                raise ValueError("MIXED_COMPACT_READER_FAILED_OR_RESOURCE_LIMITED")
                            validation = loads((destination / "reader/stdout.bin").read_bytes())
                            expected_format = "spl-native-trace-stream/" + ("0.2" if transport == "compact-v2" else "0.1")
                            if validation["format"] != expected_format:
                                raise ValueError("MIXED_COMPACT_TRANSPORT_VERSION")
                            sample["trace_validation"] = validation
                            if profile_stages:
                                baseline = sample["audit_unprofiled"]
                                if baseline["status"] != "passed":
                                    raise ValueError("MIXED_UNPROFILED_AUDIT_FAILED")
                                baseline_wire = output / f"audit-unprofiled-{index:02d}" / "stdout.bin"
                                wire_sha = equal_wire_files(destination / "stdout.bin", baseline_wire)
                                if (baseline_wire.parent / "stderr.bin").stat().st_size:
                                    raise ValueError("MIXED_UNPROFILED_UNEXPECTED_STDERR")
                                baseline["independent_control"] = "passed_via_identical_complete_wire"
                                sample["audit_profile"] = validate_profile(loads((destination / "stderr.bin").read_bytes()),
                                                                           validation["node_count"], validation["payload_count"])
                                sample["profile_wire_equality"] = {"status": "passed", "sha256": wire_sha}
                                sample["instrumentation_wall_observation_seconds"] = str(
                                    Fraction(measurement["wall_seconds"]) - Fraction(baseline["wall_seconds"]))
                            if wire_reference is not None:
                                previous_sha = equal_wire_files(destination / "stdout.bin", wire_reference)
                                sample["prior_wire_equality"] = {"status": "passed", "path": str(Path(wire_reference).resolve()),
                                                                 "sha256": previous_sha}
                            outcome = validation["head"]
                        else:
                            outcome = loads((destination / "stdout.bin").read_bytes())
                        check_target(outcome, expected)
                        measurement["independent_control"] = "passed"
                    except Exception as error:
                        measurement["status"] = "failed"
                        measurement["independent_control"] = "failed"
                        measurement["error"] = {"type": type(error).__name__, "message": str(error)}
            sample["status"] = "passed" if all(sample.get(stage, {}).get("status") == "passed" for stage in ("target", "audit", "reader")) else "failed"
            if "reader" not in sample:
                sample["reader"] = {"status": "not_executed", "reason": "native audit did not complete within its budgets"}
            write_json(output / f"sample-{index:02d}.json", sample)
            print(f"mixed{records} sample{index+1}: {sample['status']}; target={sample['target']['status']} audit={sample['audit']['status']} reader={sample['reader']['status']}", flush=True)
        report["required_audit_completed"] = bool(report["native_samples"]) and all(sample["status"] == "passed" for sample in report["native_samples"])
        report["original_neutral_unchanged"] = canonical_bytes(workload["neutral"]) == original_bytes
        current = {path.relative_to(ROOT).as_posix(): file_digest(path) for path in sources}
        current.update({"binary:" + name: file_digest(path) for name, path in binaries.items()})
        current["python_executable"] = file_digest(Path(sys.executable))
        report["unchanged_dependency_pins"] = current == pins and identities() == before
        report["status"] = "passed" if (report["required_audit_completed"] and report["reference_control"] == "passed"
                                        and report["original_neutral_unchanged"] and report["unchanged_dependency_pins"]) else "failed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    report["elapsed_seconds"] = f"{time.perf_counter()-started:.6f}"
    if records == 10000:
        report["sequential_close_dependency_plan"] = sequential_dependency_plan(report["status"] == "passed")
        report["sequential_close_scope"] = "First close only. Successors require actual audited predecessor state; none were executed or credited by this probe."
    write_json(output / "summary.json", report)
    return report


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--reference-worker":
        if len(argv) != 3:
            raise ValueError("Reference worker requires source and bindings")
        print(json.dumps(reference_worker(argv[1], argv[2]), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, choices=(100, 1000, 10000), default=100)
    parser.add_argument("--seed", type=int, default=20261123)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-output-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--max-working-set-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--prerequisite", type=Path)
    parser.add_argument("--transport", choices=("compact-v1", "compact-v2"), default="compact-v1")
    parser.add_argument("--profile-stages", action="store_true")
    parser.add_argument("--wire-reference", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = benchmark(args.output, args.records, seed=args.seed, repeats=args.repeats, timeout=args.timeout,
                           max_output_bytes=args.max_output_bytes, max_working_set_bytes=args.max_working_set_bytes,
                           prerequisite=args.prerequisite, transport=args.transport,
                           profile_stages=args.profile_stages, wire_reference=args.wire_reference)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    print(f"Mixed benchmark {report['status']}: {args.output / 'summary.json'}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
