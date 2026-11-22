"""Measured native receipt probes, separate from the proposed RR-03 workload mix.

The executable includes process startup, strict binding decode and JSON output;
these timings are not pure-settlement or production service-level claims.
"""
from __future__ import annotations

import argparse
import ctypes
from fractions import Fraction
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, exact, file_digest, loads, money, number, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import lean_environment
from spl_compiler.parser import parse
from spl_compiler.run import identities, normalize_target


def receipt_probe(rows: int, pictures: int):
    """Explicit synthetic unfunded pictures: each USD 1 earns 0.75 * 0.20."""
    if not 0 <= rows <= 100000 or not 1 <= pictures <= 1000:
        raise ValueError("Probe bounds: 0..100000 receipts and 1..1000 pictures")
    period = {"start": "2026-01-01", "end": "2026-04-01"}
    assets = [f"probe-picture-{i:04d}" for i in range(pictures)]
    return {"inputs": {
        "policy": {"agreement_id": "probe-agreement", "participant_id": "probe-participant",
                   "pool_id": "probe-pool", "period": period},
        "pictures": [{"asset_id": asset, "contribution_present": False, "funding_share": "0"} for asset in assets],
        "receipts": [{"fact_id": f"probe-receipt-{i:07d}", "asset_id": assets[i % pictures],
                      "amount": money("1"), "cash_received_date": "2026-02-01"} for i in range(rows)],
        "eligible_costs": []}, "openings": {"prepayment": money("0")}}


def _child_resources(process):
    if os.name != "nt":
        return {"resource_metrics": "unavailable on this harness platform"}
    from ctypes import wintypes

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
            (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
            "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
            "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]

    handle = wintypes.HANDLE(int(process._handle))
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    result = {}
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
    if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        result["peak_working_set_bytes"] = counters.PeakWorkingSetSize
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    creation, finish, kernel, user = [wintypes.FILETIME() for _ in range(4)]
    if kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(finish), ctypes.byref(kernel), ctypes.byref(user)):
        ticks = lambda value: (value.dwHighDateTime << 32) + value.dwLowDateTime
        result["cpu_seconds"] = number(Fraction(ticks(kernel) + ticks(user), 10000000))
    if not result:
        result["resource_metrics"] = "unavailable from completed child process"
    return result


def measured_command(command, env, timeout):
    started = time.perf_counter()
    child = subprocess.Popen(list(map(str, command)), cwd=ROOT, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timed_out = False
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        child.kill()
        stdout, stderr = child.communicate()
    metrics = {"wall_seconds": format(time.perf_counter() - started, ".6f"),
               "stdout_bytes": len(stdout), "stderr_bytes": len(stderr),
               "exit_code": child.returncode, "timed_out": timed_out,
               **_child_resources(child)}
    if timed_out or child.returncode:
        return metrics, {"status": "blocked", "diagnostics": [{
            "code": "BENCHMARK_TIMEOUT" if timed_out else "BENCHMARK_PROCESS_FAILED",
            "message": stderr.decode("utf-8", errors="replace")[-2000:]}]}
    return metrics, loads(stdout)


def assert_expected(result, rows):
    expected = Fraction(rows * 3, 20)
    if result.get("status") != "calculated" or result.get("diagnostics"):
        raise ValueError("Unsuccessful benchmark calculation: " + str(result.get("diagnostics")))
    line = result["emissions"]["pool"]
    if any(exact(line[key]) != expected for key in ["earned", "payable"]):
        raise ValueError("Independent per-receipt expectation failed")
    if exact(line["recouped"]) != 0 or exact(result["closing"]["prepayment"]) != 0:
        raise ValueError("Unexpected state consumption")


def benchmark(rows, pictures, repeats, audit, output, timeout, env):
    work = output / f"receipts-{rows}-pictures-{pictures}"
    work.mkdir(parents=True, exist_ok=True)
    bindings = receipt_probe(rows, pictures)
    write_json(work / "bindings.json", bindings)
    source = ROOT / "cases/sv/sv01.spl"
    checked = check_schedule(parse(source.read_text(encoding="utf-8"), source.name))
    tracemalloc.start()
    started = time.perf_counter()
    reference = evaluate(checked, bindings["inputs"], bindings["openings"]).to_dict()
    reference_seconds = time.perf_counter() - started
    _, reference_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert_expected(reference, rows)
    native_executable = ROOT / ".lake/build/bin/spl_sv.exe"
    samples = []
    for index in range(repeats):
        metrics, result = measured_command([native_executable, work / "bindings.json"], env, timeout)
        assert_expected(result, rows)
        for key in ["emissions", "closing"]:
            if canonical(normalize_target(result[key])) != canonical(reference[key]):
                raise ValueError("Native/reference disagreement: " + key)
        samples.append({"sample": index + 1, **metrics})
    report = {"generator": "unfunded-receipt-probe/1", "rows": rows, "pictures": pictures,
              "canonical_package": False,
              "counts": {"typed_receipts": rows, "costs": 0, "funding_events": 0,
                         "allocations": 0, "canonical_guard_count": "not applicable: direct typed bindings"},
              "expected": {"cash": str(rows), "fee": number(Fraction(rows, 4)),
                           "earned_and_payable": number(Fraction(rows * 3, 20)), "closing_prepayment": "0"},
              "binding_bytes": (work / "bindings.json").stat().st_size,
              "native_execution_mode": "prebuilt native executable: startup + decode + settlement + JSON output",
              "native_executable_sha256": file_digest(native_executable), "native_samples": samples,
              "native_median_wall_seconds": format(statistics.median(float(item["wall_seconds"]) for item in samples), ".6f"),
              "native_empirical_p95_wall_seconds": format(sorted(float(item["wall_seconds"]) for item in samples)[math.ceil(len(samples) * 0.95) - 1], ".6f"),
              "python_reference": {"wall_seconds": format(reference_seconds, ".6f"),
                                   "peak_python_traced_bytes": reference_peak},
              "trace_status": "native IR audit not requested", "capacity_claim": "observations for this synthetic workload only"}
    if audit:
        metrics, interpreted = measured_command([ROOT / ".lake/build/bin/spl.exe", "interpret", source, work / "bindings.json"], env, timeout)
        report["native_ir_audit"] = metrics
        report["trace_status"] = interpreted.get("status", "blocked")
        if interpreted.get("status") == "calculated":
            assert_expected(interpreted, rows)
            for key in ["emissions", "closing"]:
                if canonical(normalize_target(interpreted[key])) != canonical(reference[key]):
                    raise ValueError("IR/reference disagreement: " + key)
            trace = interpreted.get("trace", [])
            report["trace_counts"] = {"nodes": len(trace), "edges": sum(len(n.get("dependencies", [])) for n in trace)}
        else:
            report["audit_diagnostics"] = interpreted.get("diagnostics", [])
    write_json(work / "measurement.json", report)
    return report


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--rows", type=int, nargs="+", default=[100, 1000])
    cli.add_argument("--pictures", type=int, default=2)
    cli.add_argument("--repeats", type=int, default=3)
    cli.add_argument("--audit", action="store_true")
    cli.add_argument("--timeout", type=int, default=180)
    cli.add_argument("--output", type=Path, default=Path("C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/r1-benchmarks"))
    args = cli.parse_args()
    if args.repeats < 1 or args.timeout < 1:
        cli.error("positive repeats and timeout required")
    _, env = lean_environment()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    lake = Path(lean_environment()[0]).with_name("lake.exe")
    subprocess.run([str(lake), "build", "spl", "spl_sv"], cwd=ROOT, env=env, check=True)
    preparation = time.perf_counter() - started
    compiler, runtime = identities()
    reports = [benchmark(rows, args.pictures, args.repeats, args.audit, args.output, args.timeout, env) for rows in args.rows]
    write_json(args.output / "summary.json", {
        "format": "spl-performance-observations/1", "compiler_build": compiler, "runtime_build": runtime,
        "source_sha256": file_digest(ROOT / "cases/sv/sv01.spl"),
        "hardware": {"os": os.name, "machine": os.environ.get("PROCESSOR_IDENTIFIER", "unspecified"), "logical_cpus": os.cpu_count() or 1},
        "incremental_build_wall_seconds": format(preparation, ".6f"), "measurements": reports,
        "limitations": ["Receipt-only typed-binding probes; not the RR-03 mixed canonical generator.",
                        "No pure-settlement-only timer, storage throughput or distributed worker measurement.",
                        "Few repetitions characterize behavior; they do not establish a production p95 service target."]})
    for report in reports:
        print(f"{report['rows']} receipts/{report['pictures']} pictures: native median {report['native_median_wall_seconds']} s; audit {report['trace_status']}")


if __name__ == "__main__":
    main()
