"""Repeat the bounded RR03 workflow and verify four actual SV closes per size."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shutil
import statistics
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oracles.skouras import exact_json, skouras
from scripts.spl_mixed_benchmark import check_projection, check_target, target_expected
from spl_compiler import audited_artifacts, compact_execution, run
from spl_compiler.bounded_process import _child_resources
from spl_compiler.codecs import file_digest, number, write_json
from spl_compiler.lean_tools import LIB, lean_environment
from validation.mixed_workloads import canonical_bytes, generate_mixed

SOURCE = ROOT / "cases/sv/sv01.spl"
SEED = 20261123
CHAIN_PROFILE = "RR03-CARRY-2026/1"
PERIOD_STARTS = [date(2026, month, 1) for month in (1, 4, 7, 10)] + [date(2027, 1, 1)]
GRAPH_STAGES = ("audit-validation", "owned-attach", "precommit-publish",
                "validated-return", "consumer-reload")
TIMINGS = ("api_seconds", "consumer_seconds", "through_consumer_seconds")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def chain_workload(records, close, opening):
    """Generate the disclosed annual synthetic profile with unchanged terms."""
    workload = generate_mixed(records, seed=SEED)
    neutral = workload["neutral"]
    package = neutral["package"]
    start, end = PERIOD_STARTS[close - 1:close + 1]
    period = {"start": start.isoformat(), "end": end.isoformat()}
    horizon = {"start": PERIOD_STARTS[0].isoformat(), "end": PERIOD_STARTS[-1].isoformat()}
    cutoff = (end + timedelta(days=2)).isoformat() + "T00:00:00Z"
    scenario = f"{CHAIN_PROFILE}-{records}-{SEED}"
    package["manifest"].update(scenario_id=scenario, run_id=f"{scenario}-Q{close}",
                               period=period, cutoff=cutoff)
    package["parameters"]["policy"]["period"] = period
    package["parameters"]["funding_snapshot"]["as_of"] = period["start"]
    for row in package["agreements"] + package["roles"] + package["mappings"]:
        row["effective"] = horizon
    package["agreements"][0]["version"] = CHAIN_PROFILE
    interpretation = package["interpretations"][0]
    interpretation["version"] = f"rr03-carry-2026-q{close}-v1"
    package["agreements"][0]["interpretation_ref"] = (
        interpretation["interpretation_id"] + "@" + interpretation["version"]
    )

    # The first fact set retains its original identities. Later fact sets are
    # fresh synthetic deliveries. The cumulative funding roster stays frozen.
    suffix = "" if close == 1 else f"-Q{close}"

    def identity(value):
        return value + suffix

    def in_quarter(value):
        previous = date.fromisoformat(value)
        return date(start.year, start.month + previous.month - 1, previous.day).isoformat()

    for row in package["financial_facts"]:
        row["fact_id"] = identity(row["fact_id"])
        row["source_row"] = identity(row["source_row"])
        row["batch_ref"]["version"] = identity(row["batch_ref"]["version"])
        for field in ("parent_fact_id", "external_event_ref"):
            if field in row:
                row[field] = identity(row[field])
        row["dates"] = {key: in_quarter(value) for key, value in row["dates"].items()}
        row["temporal_basis"]["date"] = in_quarter(row["temporal_basis"]["date"])
    for row in package["parameters"]["cost_decisions"]:
        row["fact_id"] = identity(row["fact_id"])
    for row in interpretation["decisions"]:
        row["discriminating_case_ref"] = scenario
        # Pool, funding and other standing authorities exist for the full
        # horizon from Q1. Scoped allocation selections cover their own quarter.
        row["effective"] = period if "allocation_terms" in row else horizon
        for term in row.get("cost_terms", []):
            term["fact_id"] = identity(term["fact_id"])
        if "allocation_terms" in row:
            row["decision_id"] = identity(row["decision_id"])
    for row in package["allocations"] + neutral["allocation_authorities"]:
        row.update(scenario_id=scenario, effective=period)
        for field in ("source_fact_id", "allocation_group_id", "authority_ref", "policy_ref", "allocation_id"):
            if field in row:
                row[field] = identity(row[field])
    batch = package["source_batches"][0]
    batch.update(version=identity(batch["version"]), ingested_at=cutoff,
                 snapshot_locator="financial-facts.json",
                 sha256=hashlib.sha256(canonical_bytes(package["financial_facts"])).hexdigest())
    package["adapter"].update(source_fixture=scenario,
                              source_digest=hashlib.sha256(canonical_bytes(workload["source_records"])).hexdigest())

    if close == 1:
        require(opening is None, "Q1 requires the authored initial advance")
        package["state_cells"][0]["scenario_id"] = scenario
    else:
        require(len(opening or []) == 1 and opening[0]["boundary"] == period["start"]
                and opening[0]["scenario_id"] == scenario and opening[0].get("prior_result_ref")
                and "movement" not in opening[0], "Successor requires the actual preceding close")
        package["state_cells"] = deepcopy(opening)
    return workload


def predecessor_opening(previous):
    """Use the export just obtained from the prior close's public consumer."""
    previous = Path(previous)
    receipt = json.loads((previous / "sample.json").read_bytes())
    require(receipt["status"] == "passed" and
            file_digest(previous / "canonical/completion.json") == receipt["completion_sha256"],
            "Predecessor receipt failed or completion marker changed")
    return receipt["next_opening"]


class ProcessObserver:
    """Observe the production stages without substituting for any worker."""

    def __init__(self, output):
        self.output = output
        self.stages = []
        self.in_consumer = False

    def stage(self, original, command, folder, *, compiler=False):
        folder = Path(folder)
        label = folder.name
        transient = folder.is_relative_to(ROOT / ".lake/audit-readers")
        if transient:
            label = ("owned-attach" if label == "validate" else
                     "consumer-reload" if self.in_consumer else "validated-return")
        if len(command) > 2 and str(command[1]) == str(compact_execution.WORKER) and command[2] == "publish":
            label = "precommit-publish"
        row = {"stage": label, "command": list(map(str, command)), "compiler_only": compiler,
               "temporary_reader": transient}
        self.stages.append(row)
        started = time.perf_counter()
        try:
            return original(command, folder, compiler=compiler)
        finally:
            row["stage_elapsed_seconds"] = time.perf_counter() - started
            receipt = folder / "process.json"
            if receipt.is_file():
                row["process"] = json.loads(receipt.read_bytes())
            if transient and folder.is_dir():
                retained = self.output / label
                retained.mkdir(parents=True)
                for name in ("process.json", "stdout.bin", "stderr.bin"):
                    if (folder / name).is_file():
                        shutil.copyfile(folder / name, retained / name)


def check_outputs(workload, oracle, package, result):
    require(result["status"] == "calculated", "Expected a positive calculated result")
    require(result["trace"]["status"] == "complete" and result["audit_profile"] == "compact-v2",
            "Canonical audit did not complete")
    require(result["issuance_status"] == oracle["issuance_status"] and
            result["payment_evidence_status"] == oracle["payment_evidence_status"],
            "Calculation authority disagrees with originals")
    expected = target_expected(oracle)
    statement, = result["statements"]
    closing, = result["closing_state"]
    pool = {key: statement[key] for key in expected["emissions"]["pool"]}
    check_target({"status": "calculated", "emissions": {"pool": pool, "titles": result["detail"]},
                  "closing": {"prepayment": closing["quantity"]}, "diagnostics": result["diagnostics"]}, expected)
    expected_cell = {**oracle["closing_state"], "quantity": expected["closing"]["prepayment"],
                     "prior_result_ref": "result@sha256:" + result["semantic_run_digest"]}
    movement = {"opening": number(oracle["pool"]["opening_prepayment"]),
                "net_change": number(-oracle["pool"]["recovered"]), "closing": expected_cell["quantity"]}
    require(closing == {**expected_cell, "movement": movement}, "Closing cell identity or movement differs")
    require(result["reconciliation"] == {
        "settlement": {"earned": pool["earned"], "payable": pool["payable"], "pool_recovered": pool["recouped"]},
        "source_controls": [{"batch_id": row["batch_id"], "controls": row["control_totals"]}
                            for row in package["source_batches"]],
        "state": [movement], "amount_spaces_are_separate": True,
    }, "Reconciliation differs from independent controls")
    inputs, aliases, lineage, dispositions = run.project(package)
    require(len(aliases) == 1, "Expected one authored opening alias")
    require(lineage == result["source_to_target_lineage"] and dispositions == result["input_dispositions"],
            "Public lineage or dispositions disagree with projected original controls")
    return check_projection(workload, oracle, inputs, {"prepayment": next(iter(aliases.values()))},
                            lineage, dispositions)


def sample(output, records, *, close=None, previous=None):
    output.mkdir(parents=True, exist_ok=False)
    observer = ProcessObserver(output / "reader-logs")
    report = {"status": "failed", "records": records, "close": close,
              "pid": os.getpid(), "stages": observer.stages}
    cpu_start = time.process_time()
    try:
        opening = predecessor_opening(previous) if previous else None
        workload = (generate_mixed(records, seed=SEED) if close is None else
                    chain_workload(records, close, opening))
        neutral = workload["neutral"]
        report["counts"] = workload["counts"]
        report["period"] = neutral["package"]["manifest"]["period"]
        original = output / "neutral-original.json"
        write_json(original, neutral)
        batch = neutral["package"]["source_batches"][0]
        snapshot = output / batch["snapshot_locator"]
        snapshot.write_bytes(canonical_bytes(workload["source_records"]["financial_facts"]))
        require(file_digest(snapshot) == batch["sha256"], "Original source-batch bytes differ from declared hash")
        report["original_sha256"] = file_digest(original)
        report["original_bytes"] = original.stat().st_size
        report["funding_sha256"] = hashlib.sha256(
            canonical_bytes(workload["source_records"]["evidence_events"])).hexdigest()
        report["original_fact_ids"] = sorted(row["fact_id"] for row in workload["source_records"]["financial_facts"])
        report["funding_ids"] = sorted(row["event_id"] for row in workload["source_records"]["evidence_events"])
        oracle = skouras(neutral)
        write_json(output / "independent-oracle.json", exact_json(oracle))
        if close is not None:
            require(oracle["pool"]["recovered"] == (250 if close == 1 else 0), "Unexpected carry recovery")
        original_stage = compact_execution._stage

        def observe(command, folder, *, compiler=False):
            return observer.stage(original_stage, command, folder, compiler=compiler)

        destination = output / "canonical"
        with patch.object(compact_execution, "_stage", observe):
            started = time.perf_counter()
            package = run.bind_package(json.loads(original.read_bytes())["package"], SOURCE)
            bound = time.perf_counter()
            result = run.run_package(package, SOURCE, backend="compare", audit_profile="compact-v2",
                                     artifact_dir=destination)
            returned = time.perf_counter()
            report.update(api_seconds=returned - started, read_bind_seconds=bound - started,
                          canonical_status=result["status"], diagnostics=result["diagnostics"])
            observer.in_consumer = True
            loaded = audited_artifacts.load_completed_audited_result(destination)
            reloaded = time.perf_counter()
        report.update(consumer_seconds=reloaded - returned, through_consumer_seconds=reloaded - started)
        require(loaded == result, "Direct API return differs from independent public reload")
        report["projection_controls"] = check_outputs(workload, oracle, package, loaded)
        graph = [row["stage"] for row in observer.stages if row["stage"] in GRAPH_STAGES]
        require(tuple(graph) == GRAPH_STAGES, "Unexpected complete graph-validation sequence")
        compiled = [row["stage"] for row in observer.stages if row["compiler_only"]]
        require(not compiled or compiled == ["compile-lean-codegen", "compile-c-object", "compile-link"],
                "Unexpected target compilation sequence")
        report["target_cache"] = "miss_compiled" if compiled else "hit"
        require(file_digest(original) == report["original_sha256"], "Original delivery bytes changed")
        marker = destination / "completion.json"
        committed = json.loads(marker.read_bytes())
        report.update(status="passed", completion_sha256=file_digest(marker),
                      result_bytes=(destination / committed["result_path"]).stat().st_size,
                      input_bytes=len(canonical_bytes(package)), trace=loaded["trace"],
                      settlement=loaded["statements"][0], next_opening=run.carry_state(loaded))
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    report["parent_cpu_seconds"] = time.process_time() - cpu_start
    # -1 is the Windows pseudo-handle for the current process. This is its
    # process-lifetime high-water, separate from the bounded child samples.
    report["parent_resources"] = _child_resources(SimpleNamespace(_handle=-1))
    write_json(output / "sample.json", report)
    return report


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def build_pins():
    _, _, _, pins = compact_execution._compiler_inputs()
    return pins


def sample_stats(values):
    ordered = sorted(values)
    return {"n": len(ordered), "median": statistics.median(ordered),
            "p95_nearest_rank": ordered[math.ceil(.95 * len(ordered)) - 1], "max": ordered[-1]}


def host_info():
    host = {"platform": platform.platform(), "processor": platform.processor(),
            "logical_processors": os.cpu_count()}
    if os.name == "nt":
        import winreg

        key = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as processor:
            host["processor_name"] = winreg.QueryValueEx(processor, "ProcessorNameString")[0].strip()
    return host


def campaign(output, repeats, host_load_note, *, records=(100, 1000)):
    require(not output.is_relative_to(ROOT), "Keep large evidence outside the source checkout")
    require(not git("status", "--porcelain"), "Measure a clean committed source tree")
    output.mkdir(parents=True, exist_ok=False)
    executable, env = lean_environment()
    require(all(Path(module.__file__).resolve().is_relative_to(ROOT)
                for module in (run, audited_artifacts, compact_execution)) and
            run.ROOT.resolve() == ROOT and compact_execution.ROOT.resolve() == ROOT and
            LIB.resolve() == ROOT / ".lake/build/lib/lean" and
            env["LEAN_PATH"].split(os.pathsep) == [str(LIB), str(ROOT)], "Lean or repository root mismatch")
    pins = build_pins()
    commit = git("rev-parse", "HEAD")
    report = {"format": "spl-canonical-capacity/1", "status": "running", "git_commit": commit,
              "git_tree": git("rev-parse", "HEAD^{tree}"), "root": str(ROOT), "seed": SEED,
              "chain_profile": CHAIN_PROFILE, "host_load_note": host_load_note,
              "argv": sys.argv, "working_directory": str(Path.cwd()), "worker_count": 1,
              "python": sys.version, "python_executable": sys.executable,
              "host": host_info(),
              "lean": subprocess.check_output([executable, "--version"], env=env, text=True).strip(),
              "lean_path": env["LEAN_PATH"], "identities": list(run.identities()),
              "source_sha256": file_digest(SOURCE), "repeats_per_size": repeats,
              "guards": {"compiler_child_bytes": compact_execution.COMPILER_BYTES,
                         "compiler_child_seconds": 180, "runtime_child_bytes": compact_execution.RUNTIME_BYTES,
                         "runtime_child_seconds": 60, "result_or_wire_bytes": compact_execution.OUTPUT_BYTES,
                         "logical_bytes": 1024 ** 3, "native_observations": 100_000,
                         "raw_facts_plus_evidence": 100_000},
              "preexisting_target_manifests": len(list((ROOT / ".lake/compact-native").glob("*/cache.json"))),
              "cohorts": {}}
    for size in records:
        report["cohorts"][str(size)] = {
            "single_closes": [{"path": f"{size}-r{index}", "status": "not_executed"}
                              for index in range(1, repeats + 1)],
            "chain": [{"path": f"{size}-q{index}", "status": "not_executed"} for index in range(1, 5)],
        }
    write_json(output / "build-pins.json", pins)
    write_json(output / "campaign.json", report)
    try:
        for size in records:
            cohort = report["cohorts"][str(size)]
            jobs = [("single_closes", index, None) for index in range(1, repeats + 1)]
            jobs += [("chain", index, index) for index in range(1, 5)]
            previous = None
            for group, index, close in jobs:
                entry = cohort[group][index - 1]
                destination = output / entry["path"]
                command = [sys.executable, "-B", __file__, "--output", str(destination),
                           "--sample-records", str(size)]
                if close:
                    command.extend(["--close", str(close)])
                if close and previous:
                    command.extend(["--previous", str(previous)])
                process = subprocess.run(command, cwd=ROOT, env=env, check=False)
                result_path = destination / "sample.json"
                result = json.loads(result_path.read_bytes()) if result_path.is_file() else {"status": "failed"}
                entry.update(status=result["status"], exit_code=process.returncode, command=command)
                write_json(output / "campaign.json", report)
                require(process.returncode == 0 and result["status"] == "passed", f"Sample failed: {destination.name}")
                if close:
                    previous = destination
            singles = [json.loads((output / row["path"] / "sample.json").read_bytes()) for row in cohort["single_closes"]]
            cached = [row for row in singles if row["target_cache"] == "hit"]
            cohort["cached_seconds"] = {field: sample_stats([row[field] for row in cached]) for field in TIMINGS} if cached else {}
            cohort["successful_cached_samples"] = len(cached)
            cohort["compile_miss_samples"] = len(singles) - len(cached)
            chain = [json.loads((output / row["path"] / "sample.json").read_bytes()) for row in cohort["chain"]]
            facts = set().union(*(set(row["original_fact_ids"]) for row in chain))
            funding_count = size // 20
            require(len(facts) == 4 * (size - funding_count) and
                    len({row["funding_sha256"] for row in chain}) == 1 and
                    all(len(row["funding_ids"]) == funding_count for row in chain),
                    "Chain reused or lost original facts or changed funding")
            cohort["distinct_chain_originals"] = len(facts) + funding_count
        report["status"] = "passed"
    except Exception as error:
        report.update(status="failed", error={"type": type(error).__name__, "message": str(error)})
    report["unchanged_source"] = commit == git("rev-parse", "HEAD") and not git("status", "--porcelain")
    report["unchanged_build"] = pins == build_pins()
    if not report["unchanged_build"] or not report["unchanged_source"]:
        report["status"] = "failed"
    write_json(output / "campaign.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=lambda value: Path(value).resolve(), required=True)
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--host-load-note")
    parser.add_argument("--sample-records", type=int, choices=(100, 1000), help=argparse.SUPPRESS)
    parser.add_argument("--close", type=int, choices=range(1, 5), help=argparse.SUPPRESS)
    parser.add_argument("--previous", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    require(not args.output.is_relative_to(ROOT), "Keep large evidence outside the source checkout")
    if args.sample_records:
        require(bool(args.previous) == (args.close is not None and args.close > 1),
                "A predecessor is required for closes 2 through 4")
        result = sample(args.output, args.sample_records, close=args.close, previous=args.previous)
    else:
        require(args.host_load_note and 2 <= args.repeats <= 31, "Supply host conditions and 2 to 31 repeats")
        result = campaign(args.output, args.repeats, args.host_load_note)
    print(f"{result['status']} {args.output}", flush=True)
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
