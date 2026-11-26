"""Bounded receipt stage measurements; build spl and spl_sv before running.

No build is performed here. Native target execution and native IR audit are
separate processes; neither timer is an isolated pure-settlement timer.
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
import statistics
import subprocess
import sys
import threading
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.spl_benchmark import _child_resources, receipt_probe
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, exact, file_digest, loads, number, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import lean_environment
from spl_compiler.parser import parse
from spl_compiler.run import identities, normalize_target


def run_process(command, output, env=None, timeout=60, max_output_bytes=64 * 1024 * 1024,
                max_working_set_bytes=256 * 1024 * 1024):
    """Stream bounded output to disk; record overflow/timeout as failed stages.

    Peak working set and CPU refer to this process only, not its descendants.
    On unsupported hosts memory is explicitly unavailable. No output is retained
    in an unbounded PIPE buffer in the parent.
    """
    if timeout <= 0 or max_output_bytes < 1 or max_working_set_bytes < 1:
        raise ValueError("Positive process timeout, output and working-set budgets required")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    limits = {"stdout": max_output_bytes, "stderr": min(max_output_bytes, 1024 * 1024)}
    counts = Counter()
    over_budget = threading.Event()
    started = time.perf_counter()
    process = subprocess.Popen(list(map(str, command)), cwd=ROOT, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def consume(stream, name):
        with stream, (output / (name + ".bin")).open("wb") as destination:
            while chunk := stream.read(65536):
                previous = counts[name]
                counts[name] += len(chunk)
                destination.write(chunk[:max(0, limits[name] - previous)])
                if counts[name] > limits[name]:
                    over_budget.set()
                    try:
                        process.kill()
                    except OSError:
                        pass

    readers = [threading.Thread(target=consume, args=(stream, name), daemon=True)
               for name, stream in (("stdout", process.stdout), ("stderr", process.stderr))]
    for reader in readers:
        reader.start()
    timed_out, memory_over_budget = False, False
    sampled_peak = 0
    while process.poll() is None:
        remaining = timeout - (time.perf_counter() - started)
        if remaining <= 0:
            timed_out = True
            process.kill()
            process.wait()
            break
        try:
            process.wait(timeout=min(remaining, 0.02))
        except subprocess.TimeoutExpired:
            sampled_peak = max(sampled_peak, _child_resources(process).get("peak_working_set_bytes", 0))
            if sampled_peak > max_working_set_bytes:
                memory_over_budget = True
                process.kill()
                process.wait()
                break
    for reader in readers:
        reader.join()
    elapsed = time.perf_counter() - started
    resources = _child_resources(process)
    sampled_peak = max(sampled_peak, resources.get("peak_working_set_bytes", 0))
    memory_over_budget = memory_over_budget or sampled_peak > max_working_set_bytes
    resources["memory_scope"] = "child process peak working set; excludes descendants and parent JSON decoding"
    if "peak_working_set_bytes" not in resources:
        resources["peak_working_set_status"] = "unavailable"
    else:
        resources["peak_working_set_status"] = "measured_windows_GetProcessMemoryInfo"
    result = {"command": list(map(str, command)), "wall_seconds": f"{elapsed:.6f}",
              "status": "passed" if process.returncode == 0 and not timed_out and not over_budget.is_set() and not memory_over_budget else "failed",
              "exit_code": process.returncode, "timed_out": timed_out,
              "output_budget_exceeded": over_budget.is_set(),
              "working_set_budget_bytes": max_working_set_bytes,
              "working_set_budget_exceeded": memory_over_budget,
              "working_set_budget_enforcement": "sampled_Windows_peak_at_20ms_intervals" if os.name == "nt" else "unavailable_on_this_platform",
              "stdout_observed_bytes": counts["stdout"], "stderr_observed_bytes": counts["stderr"],
              "stdout_retained_bytes": (output / "stdout.bin").stat().st_size,
              "stderr_retained_bytes": (output / "stderr.bin").stat().st_size,
              "output_limits_bytes": limits, **resources}
    write_json(output / "process.json", result)
    return result


def independent_expected(bindings):
    """Neutral unit-dollar receipt controls; no compiler calculation helpers.

    This deliberately finite fixture requires all receipts in the quarter,
    unfunded pictures, no costs and zero opening advance. Original fact IDs and
    title scope are checked before calculating the expected intermediates.
    """
    inputs = bindings["inputs"]
    pictures = inputs["pictures"]
    assets = [p["asset_id"] for p in pictures]
    if len(assets) != len(set(assets)) or inputs["eligible_costs"]:
        raise ValueError("Independent receipt probe requires unique pictures and no costs")
    if exact(bindings["openings"]["prepayment"]["value"]) != 0:
        raise ValueError("Independent receipt probe requires zero advance")
    for picture in pictures:
        if picture["contribution_present"] or Fraction(picture["funding_share"]) != 0:
            raise ValueError("Independent receipt probe requires unfunded pictures")
    receipts = inputs["receipts"]
    if len({r["fact_id"] for r in receipts}) != len(receipts):
        raise ValueError("Duplicate neutral receipt identity")
    cash = Counter({asset: Fraction(0) for asset in assets})
    period = inputs["policy"]["period"]
    for receipt in receipts:
        if (receipt["asset_id"] not in cash or receipt["amount"]["currency"] != "USD"
                or Fraction(receipt["amount"]["value"]) != 1
                or not period["start"] <= receipt["cash_received_date"] < period["end"]):
            raise ValueError("Receipt outside the independently declared unit-dollar domain")
        cash[receipt["asset_id"]] += 1
    titles = [{"asset_id": asset, "cash": number(cash[asset]), "fee": number(cash[asset] / 4),
               "allowed_cost": "0", "basis": number(cash[asset] * Fraction(3, 4)),
               "share": "0.2", "earned": number(cash[asset] * Fraction(3, 20))} for asset in assets]
    policy = inputs["policy"]
    pool = {**policy, "earned": number(Fraction(len(receipts) * 3, 20)),
            "recouped": "0", "payable": number(Fraction(len(receipts) * 3, 20))}
    return {"status": "calculated", "emissions": {"titles": titles, "pool": pool},
            "closing": {"prepayment": "0"}, "diagnostic_codes": []}


def compare_expected(outcome, expected):
    normalized = normalize_target(outcome)
    actual = {"status": normalized["status"], "emissions": normalized["emissions"],
              "closing": normalized["closing"],
              "diagnostic_codes": [d["code"] for d in normalized["diagnostics"]]}
    if canonical(actual) != canonical(expected):
        raise ValueError("Independent title/pool/scope/state/intermediate expectation failed")


def measured_python(operation):
    tracemalloc.start()
    started = time.perf_counter()
    try:
        result = operation()
        _, peak = tracemalloc.get_traced_memory()
        metrics = {"status": "passed", "wall_seconds": f"{time.perf_counter() - started:.6f}",
                   "peak_python_traced_bytes": peak,
                   "memory_scope": "Python allocations traced within this stage; not process RSS"}
        return result, metrics
    finally:
        tracemalloc.stop()


def validate_arguments(rows, pictures, repeats, timeout, max_output_bytes, stress=False):
    maximum = 1000 if stress else 100
    if not rows or any(type(n) is not int or not 0 <= n <= maximum for n in rows):
        raise ValueError(f"Receipt cohorts are bounded to 0..{maximum} rows; --stress explicitly admits up to 1000")
    if stress and os.name != "nt":
        raise ValueError("Initial stress mode requires Windows working-set budget enforcement")
    if len(rows) != len(set(rows)):
        raise ValueError("Duplicate receipt cohorts are not permitted")
    if not 1 <= pictures <= 8 or not 1 <= repeats <= 10 or not 0 < timeout <= 180:
        raise ValueError("Bounds: 1..8 pictures, 1..10 repeats, timeout 1..180 seconds")
    if not 1024 <= max_output_bytes <= 128 * 1024 * 1024:
        raise ValueError("Output byte budget must be 1KiB..128MiB")


def benchmark(output, rows=(0, 10, 100), pictures=2, repeats=3, timeout=60,
              max_output_bytes=64 * 1024 * 1024, stress=False,
              max_working_set_bytes=256 * 1024 * 1024, audit_driver="legacy"):
    validate_arguments(rows, pictures, repeats, timeout, max_output_bytes, stress)
    if not 1024 * 1024 <= max_working_set_bytes <= 1024 * 1024 * 1024:
        raise ValueError("Working-set budget must be 1MiB..1GiB")
    output = Path(output).resolve()
    suffix = ".exe" if os.name == "nt" else ""
    frontend = ROOT / ".lake" / "build" / "bin" / ("spl" + suffix)
    target = frontend.with_name("spl_sv" + suffix)
    if audit_driver not in {"legacy", "stream", "compact", "compact-v2"}:
        raise ValueError("Audit driver must be legacy, stream, compact or compact-v2")
    audit_executable = frontend if audit_driver == "legacy" else frontend.with_name("spl_trace_stream" + suffix)
    if not frontend.is_file() or not target.is_file() or not audit_executable.is_file():
        raise ValueError("Build the pinned native binaries first: lake build spl spl_sv spl_trace_stream")
    _, env = lean_environment()
    output.mkdir(parents=True, exist_ok=False)
    source = output / "Source.spl"
    source.write_bytes((ROOT / "cases/sv/sv01.spl").read_bytes())
    pins = {"source_sha256": file_digest(source), "target_lean_sha256": file_digest(ROOT / "Demos/SV.lean"),
            "frontend_executable_sha256": file_digest(frontend), "target_executable_sha256": file_digest(target),
            "audit_executable_sha256": file_digest(audit_executable),
            "harness_sha256": file_digest(Path(__file__)), "probe_generator_sha256": file_digest(ROOT / "scripts/spl_benchmark.py"),
            "toolchain_sha256": file_digest(ROOT / "lean-toolchain")}
    retained_sources = [Path(__file__), ROOT / "scripts/spl_benchmark.py", ROOT / "Demos/SV.lean"]
    if audit_driver in {"stream", "compact", "compact-v2"}:
        pins["audit_driver_source_sha256"] = file_digest(ROOT / "Demos/TraceStream.lean")
        retained_sources.append(ROOT / "Demos/TraceStream.lean")
    if audit_driver in {"compact", "compact-v2"}:
        pins["compact_reader_sha256"] = file_digest(ROOT / "scripts/spl_native_trace_transport.py")
        pins["archive_transport_sha256"] = file_digest(ROOT / "scripts/spl_trace_transport.py")
        retained_sources.extend([ROOT / "scripts/spl_native_trace_transport.py", ROOT / "scripts/spl_trace_transport.py"])
    for path in retained_sources:
        destination = output / "sources" / path.name
        destination.parent.mkdir(exist_ok=True)
        destination.write_bytes(path.read_bytes())
    before = identities()
    report = {"format": "spl-stage-performance/1", "status": "running", "pins": pins,
              "compiler_build": before[0], "runtime_build": before[1],
              "python": sys.version, "lean_toolchain": (ROOT / "lean-toolchain").read_text().strip(),
              "lean_executable": lean_environment()[0],
              "lean_version": subprocess.run([lean_environment()[0], "--version"], env=env,
                                              capture_output=True, text=True, check=True).stdout.strip(),
              "hardware": {"platform": platform.platform(), "processor": os.environ.get("PROCESSOR_IDENTIFIER", platform.processor()),
                           "logical_cpus": os.cpu_count()},
              "budgets": {"timeout_seconds": timeout, "per_stage_stdout_bytes": max_output_bytes,
                          "child_working_set_bytes": max_working_set_bytes, "stress_mode": stress},
              "native_build_precondition": "Prebuilt lake build spl spl_sv; hashes identify binaries, not a proof of source/binary correspondence.",
              "workload": "unfunded unit-dollar receipts, zero-cost/zero-advance output titles; direct typed bindings",
              "audit_driver": audit_driver,
              "audit_transport": {"legacy": "legacy whole-outcome JSON", "stream": "legacy-equivalent node-by-node expanded JSON",
                                  "compact": "spl-native-trace-stream/0.1 JSONL with mandatory completion and independent bounded reader",
                                  "compact-v2": "spl-native-trace-stream/0.2 JSONL with exact indexed dependencies and32-byte eligible-field interning"}[audit_driver],
              "preparation": [], "cohorts": [],
              "limitations": ["Receipt-only probes are not the RR-03 mixed canonical workload or a capacity claim.",
                              "Native target stage includes startup, file I/O, strict decode, settlement and output serialization.",
                              "Native audit stage additionally includes frontend and full native IR trace materialization/serialization.",
                              "Pure-settlement-only and audit-generation-only timers are not instrumented.",
                              "Python traced allocations and child peak working set measure different scopes.",
                              "Windows working-set budget is sampled every 20ms; transient overshoot is possible, not a hard OS limit.",
                              "First sample and subsequent process samples do not establish cold-cache or production p95 latency."]}
    write_json(output / "summary.json", report)
    started = time.perf_counter()
    try:
        for mode in ("check", "compile"):
            destination = output / "Generated.lean"
            command = [frontend, mode, source, *([destination] if mode == "compile" else [])]
            stage = run_process(command, output / ("native_frontend_" + mode), env, timeout, max_output_bytes, max_working_set_bytes)
            stage["phase"] = "native_frontend_" + mode
            report["preparation"].append(stage)
            if stage["status"] != "passed":
                raise ValueError("Native frontend " + mode + " failed")
        emitted_matches = (output / "Generated.lean").read_bytes() == (ROOT / "Demos/SV.lean").read_bytes()
        report["emitted_source_matches_prebuilt_target_source"] = emitted_matches
        report["generated_lean_sha256"] = file_digest(output / "Generated.lean")
        if not emitted_matches:
            raise ValueError("Current native emission differs from prebuilt target source; rebuild/refresh deliberately")
        checked, frontend_metrics = measured_python(lambda: check_schedule(parse(source.read_text(encoding="utf-8"))))
        report["python_frontend"] = frontend_metrics
        for count in rows:
            work = output / f"receipts-{count}-pictures-{pictures}"
            work.mkdir()
            bindings = receipt_probe(count, pictures)
            write_json(work / "bindings.json", bindings)
            expected = independent_expected(bindings)
            write_json(work / "independent-expected.json", expected)
            cohort = {"rows": count, "pictures": pictures, "bindings_sha256": file_digest(work / "bindings.json"),
                      "binding_bytes": (work / "bindings.json").stat().st_size,
                      "counts": {"receipt_parents": count, "projected_receipts": count, "costs": 0,
                                 "evidence_events": 0, "allocations": 0, "guard_count": "not canonical"},
                      "target": [], "audit": [], "status": "running"}
            report["cohorts"].append(cohort)
            reference, metrics = measured_python(lambda: evaluate(checked, bindings["inputs"], bindings["openings"]).to_dict())
            write_json(work / "reference.json", reference)
            compare_expected(reference, expected)
            cohort["python_reference"] = metrics
            for index in range(repeats):
                audit_command = ([frontend, "interpret", source, work / "bindings.json"] if audit_driver == "legacy"
                                 else [audit_executable, source, work / "bindings.json", *(
                                     ["--compact"] if audit_driver == "compact" else ["--compact-v2"] if audit_driver == "compact-v2" else [])])
                for phase, command in (("target", [target, work / "bindings.json"]),
                                       ("audit", audit_command)):
                    stage_path = work / (phase + f"-{index:02d}")
                    stage = run_process(command, stage_path, env, timeout, max_output_bytes, max_working_set_bytes)
                    stage["sample"] = index + 1
                    stage["artifact"] = stage_path.relative_to(output).as_posix()
                    stage["independent_control"] = "not_checked"
                    cohort[phase].append(stage)
                    if stage["status"] == "passed":
                        try:
                            if phase == "audit" and audit_driver in {"compact", "compact-v2"}:
                                reader_path = stage_path / "reader"
                                reader = run_process([sys.executable, ROOT / "scripts/spl_native_trace_transport.py",
                                                      stage_path / "stdout.bin", "--max-input-bytes", str(max_output_bytes)],
                                                     reader_path, env, timeout, 1024 * 1024, max_working_set_bytes)
                                stage["compact_reader_process"] = reader
                                if reader["status"] != "passed":
                                    raise ValueError("Independent compact reader failed its validation/resource budget")
                                validation = loads((reader_path / "stdout.bin").read_bytes())
                                expected_format = "spl-native-trace-stream/" + ("0.2" if audit_driver == "compact-v2" else "0.1")
                                if validation["format"] != expected_format:
                                    raise ValueError("Independent reader reported the wrong compact transport version")
                                stage["compact_validation"] = validation
                                outcome = validation["head"]
                                stage["trace_nodes"] = validation["node_count"]
                                stage["trace_edges"] = validation["edge_count"]
                            else:
                                outcome = loads((stage_path / "stdout.bin").read_bytes())
                            compare_expected(outcome, expected)
                            stage["independent_control"] = "passed"
                            if phase == "audit":
                                if outcome.get("trace_origin") != "native_ir_interpreter":
                                    raise ValueError("Missing native interpreter audit origin")
                                if audit_driver not in {"compact", "compact-v2"}:
                                    trace = outcome["trace"]
                                    stage["trace_nodes"] = len(trace)
                                    stage["trace_edges"] = sum(len(n["dependencies"]) for n in trace)
                        except Exception as error:
                            stage["status"] = "failed"
                            stage["independent_control"] = "failed"
                            stage["error"] = str(error)
                    write_json(stage_path / "checked-stage.json", stage)
            cohort["status"] = "passed" if all(s["status"] == "passed" for p in ("target", "audit") for s in cohort[p]) else "failed"
            for phase in ("target", "audit"):
                successful = [float(s["wall_seconds"]) for s in cohort[phase] if s["status"] == "passed"]
                cohort[phase + "_median_wall_seconds"] = f"{statistics.median(successful):.6f}" if successful else None
            write_json(work / "measurement.json", cohort)
            write_json(output / "summary.json", report)
            print(f"{count} receipts: {cohort['status']}; target {cohort['target_median_wall_seconds']}s; audit {cohort['audit_median_wall_seconds']}s", flush=True)
        current = {"source_sha256": file_digest(ROOT / "cases/sv/sv01.spl"),
                   "target_lean_sha256": file_digest(ROOT / "Demos/SV.lean"),
                   "frontend_executable_sha256": file_digest(frontend), "target_executable_sha256": file_digest(target),
                   "audit_executable_sha256": file_digest(audit_executable),
                   "harness_sha256": file_digest(Path(__file__)), "probe_generator_sha256": file_digest(ROOT / "scripts/spl_benchmark.py"),
                   "toolchain_sha256": file_digest(ROOT / "lean-toolchain")}
        if audit_driver in {"stream", "compact", "compact-v2"}:
            current["audit_driver_source_sha256"] = file_digest(ROOT / "Demos/TraceStream.lean")
        if audit_driver in {"compact", "compact-v2"}:
            current["compact_reader_sha256"] = file_digest(ROOT / "scripts/spl_native_trace_transport.py")
            current["archive_transport_sha256"] = file_digest(ROOT / "scripts/spl_trace_transport.py")
        report["unchanged_pins"] = current == pins and identities() == before
        report["status"] = "passed" if report["unchanged_pins"] and all(c["status"] == "passed" for c in report["cohorts"]) else "failed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    report["elapsed_seconds"] = f"{time.perf_counter() - started:.6f}"
    write_json(output / "summary.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, nargs="+", default=[0, 10, 100])
    parser.add_argument("--pictures", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-output-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--max-working-set-bytes", type=int, default=256 * 1024 * 1024)
    parser.add_argument("--stress", action="store_true", help="explicitly admit up to 1000 receipts with Windows sampled memory enforcement")
    parser.add_argument("--audit-driver", choices=("legacy", "stream", "compact", "compact-v2"), default="legacy")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = benchmark(args.output, args.rows, args.pictures, args.repeats, args.timeout, args.max_output_bytes,
                           args.stress, args.max_working_set_bytes, args.audit_driver)
    except ValueError as error:
        parser.error(str(error))
    print(f"Stage benchmark {report['status']}: {args.output / 'summary.json'}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
