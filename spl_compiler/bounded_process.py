"""Sampled child-only process budgets for opt-in native audit publication.

The Windows working-set sampler is observational enforcement, not an OS job
limit; descendants and parent preparation memory are outside this scope.
"""
from collections import Counter
import ctypes
from fractions import Fraction
import os
from pathlib import Path
import subprocess
import threading
import time
from .codecs import number, write_json
from .lean_tools import ROOT

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
    try:
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
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        for reader in readers:
            reader.join()
    elapsed = time.perf_counter() - started
    resources = _child_resources(process)
    # Release the exited Windows process object's image handle before owned
    # executable bytes are flushed/hashed by the publication worker.
    if os.name == "nt":
        process._handle.Close()
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
