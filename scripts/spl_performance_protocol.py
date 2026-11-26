"""Bounded repeated stage protocol; no builds of shared Lake artifacts.

Fresh/reused output directories do not control operating-system caches. Mixed
stage audits and generic IR artifact publication are not canonical close credit.
"""
from copy import deepcopy
from fractions import Fraction
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oracles.skouras import skouras
from scripts import spl_mixed_benchmark as mixed
from scripts.spl_stage_benchmark import run_process
from scripts.spl_trace_transport import Limits as JsonLimits, loads as metadata_loads
from spl_compiler.codecs import canonical, file_digest, loads, write_json
from spl_compiler.lean_tools import lean_environment
from validation.mixed_workloads import generate_mixed

FORMAT = "spl-performance-protocol/1"
BUDGETS = {"native_timeout_seconds": 60, "stdout_bytes": 64 * 1024 * 1024,
           "sampled_child_working_set_bytes": 256 * 1024 * 1024,
           "logical_expanded_trace_bytes": 1024 * 1024 * 1024, "native_ir_observations": 100000,
           "orchestrator_worker_timeout_seconds": 240}
BYPASSES = ("QUEST_REFERENCE_ONLY", "SPL_QUANTITIES_REFERENCE_ONLY", "SPL_REVISION_REFERENCE_ONLY", "SPL_M1_BACKEND", "SPL_WATERFALL_BACKEND")
COMPILER_PROFILES = {
    "runtime256": {"id": "spl-compiler-budget/runtime256/1", "timeout_seconds": 60, "sampled_child_working_set_bytes": 256 * 1024 * 1024},
    "compiler1g180": {"id": "spl-compiler-budget/1g180/1", "timeout_seconds": 180, "sampled_child_working_set_bytes": 1024 * 1024 * 1024},
}


def make_plan(*, first_samples=3, warm_samples=30, records=(100, 1000), host_load_note, compiler_profile="runtime256"):
    if type(first_samples) is not int or not 1 <= first_samples <= 3 or type(warm_samples) is not int or not 0 <= warm_samples <= 30:
        raise ValueError("PROTOCOL_SAMPLE_BOUNDS")
    if tuple(records) not in ((100,), (100, 1000)) or any(type(v) is not int for v in records):
        raise ValueError("PROTOCOL_REQUIRES_100_THEN_OPTIONAL_1000")
    if type(host_load_note) is not str or not 1 <= len(host_load_note) <= 1024:
        raise ValueError("PROTOCOL_HOST_LOAD_REQUIRED")
    if type(compiler_profile) is not str or compiler_profile not in COMPILER_PROFILES:
        raise ValueError("PROTOCOL_COMPILER_PROFILE")
    return {"format": FORMAT, "worker_count": 1, "records": list(records), "first_samples": first_samples,
            "warm_samples": warm_samples, "full_repetition_protocol": first_samples == 3 and warm_samples == 30,
            "implementation": "legacy", "transport": "compact-v2", "seed": 20261123,
            "budgets": deepcopy(BUDGETS), "host_load_note": host_load_note,
            "compiler_profile": deepcopy(COMPILER_PROFILES[compiler_profile]),
            "cache_scope": "pinned compiled runtime closure reused; OS and CPU caches uncontrolled",
            "first_process_scope": "fresh process and fresh output directory; not a controlled cold-cache sample",
            "warm_process_scope": "later fresh processes under host-cache-warm scheduling; process startup remains included",
            "known_10000": "not_executed: retained first-close audit/resource failures remain authoritative; no retry in this protocol",
            "canonical_close_credit": False}


def sample_labels(plan):
    return ([{"class": "fresh_output", "index": index + 1} for index in range(plan["first_samples"])] +
            [{"class": "later_host_cache_warm", "index": index + 1} for index in range(plan["warm_samples"])])


def observations(samples):
    """Empirical nearest-rank summaries; never hide failed/censored samples."""
    if not isinstance(samples, list):
        raise ValueError("PROTOCOL_SAMPLE_LIST")
    passed, failures = [], []
    for index, row in enumerate(samples):
        if not isinstance(row, dict) or row.get("status") not in {"passed", "failed", "not_executed"}:
            raise ValueError("PROTOCOL_SAMPLE_STATUS")
        if row["status"] != "passed":
            failures.append({"index": index, "status": row["status"], "reason": row.get("reason")})
            continue
        value = row.get("wall_seconds")
        if type(value) is not str:
            raise ValueError("PROTOCOL_EXACT_TIMER_STRING")
        duration = Fraction(value)
        if duration < 0:
            raise ValueError("PROTOCOL_NEGATIVE_TIMER")
        passed.append(duration)
    result = {"samples": len(samples), "successful_samples": len(passed), "failures_or_unexecuted": failures,
              "quantile_scope": "empirical nearest-rank of successful disclosed samples; no population percentile or SLA claim"}
    if passed:
        values = sorted(passed)
        for name, percentile in (("p50", Fraction(1, 2)), ("p95", Fraction(95, 100)), ("max", Fraction(1))):
            index = math.ceil(percentile * len(values)) - 1
            result[name + "_seconds_successful_only"] = str(values[index])
    return result


def dependency_pins():
    paths = set(mixed.dependency_files())
    paths.update([Path(__file__), ROOT / "scripts/spl_pure_benchmark.py", ROOT / "Demos/PureSettlementBenchmark.lean",
                  ROOT / "scripts/spl_audited_stage_chain.py",
                  ROOT / "Demos/SVBenchmarkLibrary.lean", ROOT / ".lake/build/bin/spl_sv.exe.rsp",
                  ROOT / ".lake/build/ir/Demos/SV.c.o.noexport.trace"])
    for name in ("spl", "spl_sv", "spl_trace_stream", "spl_pure_benchmark"):
        paths.add(ROOT / ".lake/build/bin" / (name + (".exe" if os.name == "nt" else "")))
    paths.update((ROOT / ".lake/build/lib/lean/SPL").glob("*.olean"))
    paths.add(ROOT / ".lake/build/lib/lean/SPL.olean")
    # Exact link closure inputs, including cached runtime objects and flags.
    rsp = ROOT / ".lake/build/bin/spl_sv.exe.rsp"
    response_args = []
    if rsp.is_file():
        for line in rsp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                arg = json.loads(line)
                response_args.append(arg)
                if Path(arg).is_file():
                    paths.add(Path(arg).resolve())
    lean, _ = lean_environment()
    toolbin = Path(lean).parent
    paths.update(toolbin / name for name in ("lean.exe", "lake.exe", "clang.exe", "leanc.exe", "ld.lld.exe"))
    toolroot = toolbin.parent
    paths.update(path for path in (toolroot / "include").rglob("*") if path.is_file())
    paths.update((toolroot / "lib").glob("*.o"))
    paths.update((toolroot / "lib/lean").glob("*.dll"))
    library_dirs = [Path(response_args[index + 1]) for index, arg in enumerate(response_args[:-1]) if arg == "-L"]
    for arg in response_args:
        if arg.startswith("-l") and len(arg) > 2:
            # Lake's actual response explicitly selects static archives. Pin
            # every existing candidate when an import-library alternative is
            # present, rather than guessing which linker search wins.
            candidates = [directory / ("lib" + arg[2:] + suffix) for directory in library_dirs for suffix in (".a", ".dll.a")]
            found = [path for path in candidates if path.is_file()]
            if not found:
                raise ValueError("PROTOCOL_UNRESOLVED_LINK_LIBRARY:" + arg)
            paths.update(found)
    paths.add(Path(sys.executable))
    if any(not path.is_file() for path in paths):
        raise ValueError("PROTOCOL_MISSING_BUILD_INPUT")
    return {str(path.resolve()): file_digest(path) for path in sorted(paths)}


def require_pins(expected):
    if dependency_pins() != expected:
        raise ValueError("PROTOCOL_DEPENDENCY_CLOSURE_CHANGED")


def load_report(path, *, max_bytes=8*1024*1024):
    # Performance metadata legitimately uses optional nulls. Financial input
    # codecs stay strict; observational JSON still rejects duplicates/floats.
    with Path(path).open('rb') as stream:raw=stream.read(max_bytes+1)
    return metadata_loads(raw,JsonLimits(max_input_bytes=max_bytes))


def snapshot_inputs(output,pins):
    output=Path(output)
    for name,expected in pins.items():
        path=Path(name)
        if path.is_relative_to(ROOT):
            target=output/"pinned-checkout"/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
            if file_digest(target)!=expected:raise ValueError("PROTOCOL_SNAPSHOT_CHANGED")


def hardware():
    row = {"platform": platform.platform(), "logical_cpus": os.cpu_count(), "worker_count": 1,
           "processor_identifier": os.environ.get("PROCESSOR_IDENTIFIER", platform.processor()),
           "python": sys.version, "python_executable": sys.executable,
           "memory_scope": "per-child sampled peak working set; excludes siblings, descendants, parent preparation and filesystem cache"}
    if os.name == "nt":
        import ctypes
        class Memory(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [(key, ctypes.c_ulonglong) for key in ("total_physical", "available_physical", "total_page", "available_page", "total_virtual", "available_virtual", "available_extended")]
        memory = Memory(); memory.length = ctypes.sizeof(memory)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)):
            row.update(total_physical_memory_bytes=memory.total_physical, available_physical_memory_bytes_at_start=memory.available_physical)
    return row


def measured(command, destination, env, *, orchestration=False, compiler_profile=None):
    timeout = BUDGETS["orchestrator_worker_timeout_seconds"] if orchestration else BUDGETS["native_timeout_seconds"]
    memory = BUDGETS["sampled_child_working_set_bytes"]
    if compiler_profile is not None:
        if compiler_profile not in COMPILER_PROFILES.values():
            raise ValueError("PROTOCOL_COMPILER_PROFILE")
        timeout = compiler_profile["timeout_seconds"]
        memory = compiler_profile["sampled_child_working_set_bytes"]
    return run_process(command, destination, env,
                       timeout=timeout, max_output_bytes=BUDGETS["stdout_bytes"], max_working_set_bytes=memory)


def mixed_pins(pins):
    result = {path.relative_to(ROOT).as_posix(): pins[str(path.resolve())] for path in mixed.dependency_files()}
    result.update({"binary:" + name: pins[str((ROOT / ".lake/build/bin" / (name + ".exe")).resolve())] for name in ("spl", "spl_sv", "spl_trace_stream")})
    result["python_executable"] = pins[str(Path(sys.executable).resolve())]
    return result


def validate_mixed_report(report, expected_pins, records, seed):
    mixed.check_prerequisite(report, expected_pins, seed,
                             {"child_timeout_seconds": BUDGETS["native_timeout_seconds"], "child_stdout_bytes": BUDGETS["stdout_bytes"],
                              "child_sampled_working_set_bytes": BUDGETS["sampled_child_working_set_bytes"]},
                             "compact-v2", False, records, "legacy")
    if (report.get("reference_control") != "passed" or report.get("original_neutral_unchanged") is not True
            or report.get("unchanged_dependency_pins") is not True or report.get("native_emission", {}).get("status") != "passed"):
        raise ValueError("PROTOCOL_INCOMPLETE_MIXED_CONTROL")
    for sample in report["native_samples"]:
        validation = sample.get("trace_validation", {})
        if (validation.get("format") != "spl-native-trace-stream/0.2"
                or type(validation.get("transport_sha256")) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", validation["transport_sha256"])
                or type(validation.get("node_count")) is not int or not 0 <= validation["node_count"] <= BUDGETS["native_ir_observations"]
                or type(validation.get("expanded_trace_bytes")) is not int or not 2 <= validation["expanded_trace_bytes"] <= BUDGETS["logical_expanded_trace_bytes"]):
            raise ValueError("PROTOCOL_COMPLETE_AUDIT_EVIDENCE")


def c_compile_flags(trace, expected_toolbin):
    """Reuse the actual pinned Lake command; do not invent compiler options."""
    data = loads(Path(trace).read_bytes())
    messages = [row.get("message", "") for row in data.get("log", []) if row.get("level") == "trace"]
    candidates = [message[3:].split() for message in messages if message.startswith(".> ") and " -c -o " in message]
    if len(candidates) != 1:
        raise ValueError("PROTOCOL_LAKE_C_TRACE_COMMAND")
    args = candidates[0]
    # The pinned physical paths contain no spaces or shell quoting. Reject an
    # unsupported trace representation instead of guessing Windows tokenization.
    if (len(args) < 7 or any('"' in arg or "'" in arg for arg in args)
            or Path(args[0]).resolve() != (Path(expected_toolbin) / "clang.exe").resolve()
            or args[1:3] != ["-c", "-o"] or not args[4].endswith("/SV.c") and not args[4].endswith("\\SV.c")):
        raise ValueError("PROTOCOL_LAKE_C_TRACE_SHAPE")
    return args[5:]


def compile_samples(output, plan, pins, bindings, expected):
    """Force actual schedule compilation; never overwrite shared .olean files."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    lean, env = lean_environment()
    toolbin = Path(lean).parent
    flags = c_compile_flags(ROOT / ".lake/build/ir/Demos/SV.c.o.noexport.trace", toolbin)
    link_args = [json.loads(line) for line in (ROOT / ".lake/build/bin/spl_sv.exe.rsp").read_text(encoding="utf-8").splitlines() if line.strip()]
    source = output / "Source.spl"
    source.write_bytes((ROOT / "cases/sv/sv01.spl").read_bytes())
    write_json(output / "bindings.json", bindings)
    write_json(output / "expected.json", expected)
    rows = []
    failed = None
    for sequence, label in enumerate(sample_labels(plan)):
        row = {**label, "sequence": sequence + 1, "status": "not_executed"}
        rows.append(row)
        if failed:
            row["reason"] = "earlier_compilation_stage_failed"
            continue
        require_pins(pins)
        work = output / (f"fresh-{sequence:02d}" if label["class"] == "fresh_output" else "reused-output")
        work.mkdir(exist_ok=True)
        generated, c_file, obj, executable = (work / name for name in ("Candidate.lean", "Candidate.c", "Candidate.o", "Candidate.exe"))
        response = work / "link.rsp"
        response.write_text("\n".join(json.dumps(arg) for arg in [str(obj), *link_args[1:]]), encoding="utf-8")
        commands = [("frontend_to_lean", [ROOT / ".lake/build/bin/spl.exe", "compile", source, generated]),
                    ("lean_elaboration_codegen", [lean, "-DwarningAsError=true", "-R", work, "-c", c_file, generated]),
                    ("c_object", [toolbin / "clang.exe", "-c", "-o", obj, c_file, *flags]),
                    ("native_link", [toolbin / "clang.exe", "-o", executable, "@" + str(response)]),
                    ("compiled_financial_control", [executable, output / "bindings.json"])]
        sample_dir = output / f"observation-{sequence:02d}"
        sample_dir.mkdir()
        row["stages"] = {}
        for stage, command in commands:
            if failed:
                row["stages"][stage] = {"status": "not_executed", "reason": "prior_stage_failed"}
                continue
            result = measured(command, sample_dir / stage, env,
                              compiler_profile=plan["compiler_profile"] if stage != "compiled_financial_control" else None)
            row["stages"][stage] = result
            try:
                if result["status"] != "passed":
                    raise ValueError("PROTOCOL_COMPILE_PROCESS_RESOURCE_OR_EXIT")
                if stage == "frontend_to_lean" and generated.read_bytes() != (ROOT / "Demos/SV.lean").read_bytes():
                    raise ValueError("PROTOCOL_FRESH_EMISSION_DIFFERS")
                if stage == "compiled_financial_control":
                    mixed.check_target(loads((sample_dir / stage / "stdout.bin").read_bytes()), expected)
                    result["independent_control"] = "passed"
            except Exception as error:
                result.update(status="failed", error={"type": type(error).__name__, "message": str(error)})
                failed = {"sample": sequence + 1, "stage": stage}
        row.update(status="failed" if failed else "passed", output_mode="forced compilation into fresh/reused outputs; no artifact cache-hit shortcut",
                   artifacts={path.name: file_digest(path) for path in (generated, c_file, obj, response, executable) if path.is_file()})
        write_json(output / "summary.json", {"samples": rows, "first_failure": failed})
    return {"status": "failed" if failed else "passed", "samples": rows, "first_failure": failed, "compiler_profile": plan["compiler_profile"],
            "scope": "schedule compilation only; cached runtime/toolchain imports and link closure pinned; OS cache uncontrolled"}


def repeated_mixed(output, plan, pins):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    _, env = lean_environment()
    rows, gate100, first_failure = [], None, None
    for records in plan["records"]:
        for index, label in enumerate(sample_labels(plan)):
            row = {"records": records, **label, "status": "not_executed"}
            rows.append(row)
            if first_failure:
                row["reason"] = "earlier_required_cohort_or_sample_failed"
                continue
            require_pins(pins)
            destination = output / f"mixed-{records}-{index:02d}"
            command = [sys.executable, ROOT / "scripts/spl_mixed_benchmark.py", "--records", str(records), "--repeats", "1",
                       "--transport", "compact-v2", "--host-load-note", plan["host_load_note"], "--output", destination]
            if records == 1000:
                command += ["--prerequisite", gate100]
            process = measured(command, output / f"worker-{records}-{index:02d}", env, orchestration=True)
            row.update(worker=process, summary_path=str(destination / "summary.json"), worker_memory_scope="orchestration Python process only; each native/reader child retains its separate fixed256MiB/60s guard")
            if (destination / "summary.json").is_file():
                report = load_report(destination / "summary.json")
                row["mixed_status"] = report.get("status")
                try:
                    if process["status"] != "passed":
                        raise ValueError("PROTOCOL_MIXED_WORKER_FAILED")
                    validate_mixed_report(report, mixed_pins(pins), records, plan["seed"])
                    row["status"] = "passed"
                    row["wall_seconds"] = process["wall_seconds"]
                    row["mixed_pipeline_seconds_excluding_worker_startup"] = report["elapsed_seconds"]
                    row["audit_wire_sha256"] = report["native_samples"][0]["trace_validation"]["transport_sha256"]
                    if records == 100 and gate100 is None:
                        gate100 = destination / "summary.json"
                except Exception as error:
                    row["status"] = "failed"
                    row["error"] = {"type": type(error).__name__, "message": str(error)}
            else:
                row["status"] = "failed"
                row["reason"] = "worker_did_not_complete_report"
            if row["status"] != "passed":
                first_failure = {"records": records, **label, "reason": row.get("reason", "required_stage_or_control_failed")}
            write_json(output / "summary.json", {"samples": rows, "first_failure": first_failure})
    return {"status": "failed" if first_failure else "passed", "samples": rows, "first_failure": first_failure,
            "statistics": {str(records): observations([row for row in rows if row["records"] == records]) for records in plan["records"]},
            "publication": "not_executed by the mixed driver; no canonical close credit"}


def publication_worker(wire, expected, destination, expected_sha256=None):
    """Publish the genuine fully reconstructed native IR outcome, unchanged.

    This generic artifact path supports that object. No canonical financial
    fields, state cells, result digest or statements are fabricated.
    """
    from scripts.spl_native_trace_transport import NativeLimits, read_compact
    from spl_compiler.artifacts import ArtifactPublication, load_completed_result
    report = {"format": "spl-ir-publication-observation/1", "status": "failed", "canonical_close_credit": False,
              "scope": "generic publication of exact reconstructed legacy native IR outcome; not a canonical financial result",
              "stages": {}, "financial_outputs": {}, "closing_state": []}
    stage = "reconstruction"
    publication = ArtifactPublication(destination)
    try:
        start = time.perf_counter()
        restored = read_compact(wire, NativeLimits(), reconstruct=True, expected_sha256=expected_sha256)
        report["stages"][stage] = {"status": "passed", "wall_seconds": str(time.perf_counter() - start)}
        outcome = restored.pop("outcome")
        report["trace_validation"] = restored
        stage = "financial_control"
        mixed.check_target(outcome, loads(Path(expected).read_bytes()))
        report["stages"][stage] = {"status": "passed"}
        stage = "publication"
        start = time.perf_counter()
        returned = publication.finish(outcome, {})
        report["stages"][stage] = {"status": "passed", "wall_seconds": str(time.perf_counter() - start)}
        stage = "validated_reload"
        start = time.perf_counter()
        loaded = load_completed_result(destination)
        if canonical(loaded) != canonical(returned):
            raise ValueError("PROTOCOL_PUBLISHED_IR_CHANGED")
        report["stages"][stage] = {"status": "passed", "wall_seconds": str(time.perf_counter() - start)}
        report.update(status="passed", result_bytes=(Path(destination) / "result.json").stat().st_size,
                      exact_reconstructed_ir_preserved=True)
    except Exception as error:
        report["stages"][stage] = {"status": "failed", "error": {"type": type(error).__name__, "message": str(error)}}
        report["first_failure"] = stage
    names = ("reconstruction", "financial_control", "publication", "validated_reload")
    for name in names:
        report["stages"].setdefault(name, {"status": "not_executed", "reason": "earlier_required_stage_failed"})
    return report


def pure_samples(output, plan, pins):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    require_pins(pins)
    _,env=lean_environment()
    command=[sys.executable,ROOT/"scripts/spl_pure_benchmark.py","--records",*map(str,plan["records"]),
             "--process-repeats","3","--samples","10","--output",output/"measurements"]
    worker=measured(command,output/"worker",env,orchestration=True)
    result={"status":"failed","worker":worker,"scope":"three first decoded calls and30actual in-process warm batches per cohort; fresh processes, OS caches uncontrolled"}
    path=output/"measurements/summary.json"
    if path.is_file():
        report=load_report(path)
        result["summary_path"]=str(path)
        try:
            validate_pure_report(report,plan["records"])
            if worker["status"]!="passed":raise ValueError("PROTOCOL_PURE_WORKER_FAILED")
            result["status"]="passed"
        except Exception as error:
            result["error"]={"type":type(error).__name__,"message":str(error)}
    return result


def validate_pure_report(report, records):
    if (report.get("format")!="spl-pure-performance/1" or report.get("status")!="passed"
            or report.get("unchanged_dependency_pins") is not True
            or not isinstance(report.get("cohorts"),list) or [row.get("records") for row in report["cohorts"]]!=list(records)):
        raise ValueError("PROTOCOL_PURE_COMPLETE_REPORT")
    for cohort in report["cohorts"]:
        if (cohort.get("status")!="passed" or cohort.get("control_status")!="passed" or cohort.get("inner_sample_count")!=30
                or cohort.get("timer_span_reached_all") is not True or len(cohort.get("processes",[]))!=3):
            raise ValueError("PROTOCOL_PURE_REPETITIONS")
        for process in cohort["processes"]:
            if (process.get("status")!="passed" or process.get("independent_control",{}).get("status")!="passed"
                    or len(process.get("observation",{}).get("samples",[]))!=10
                    or process.get("observation",{}).get("resolution_span_reached") is not True):
                raise ValueError("PROTOCOL_PURE_PROCESS_CONTROL")


def publication_samples(output, mixed_report, plan, pins):
    """Each observation uses its actual complete audit; no failed-prefix credit."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    _, env = lean_environment()
    rows, first_failure = [], {}
    for index, sample in enumerate(mixed_report["samples"]):
        records = sample["records"]
        row = {"records": records, "class": sample["class"], "index": sample["index"], "status": "not_executed"}
        rows.append(row)
        if str(records) in first_failure:
            row["reason"] = "earlier_publication_in_this_cohort_failed"
            continue
        if sample["status"] != "passed":
            row["reason"] = "actual_audited_predecessor_not_completed"
            continue
        require_pins(pins)
        work = Path(sample["summary_path"]).parent
        worker = measured([sys.executable, Path(__file__), "--publication-worker", work / "audit-00/stdout.bin",
                           work / "independent-target-expected.json", output / f"published-{index:02d}", sample["audit_wire_sha256"]],
                          output / f"worker-{index:02d}", env)
        row["worker"] = worker
        try:
            observation = load_report(output / f"worker-{index:02d}/stdout.bin")
            if observation.get("format") != "spl-ir-publication-observation/1" or observation.get("canonical_close_credit") is not False:
                raise ValueError("PROTOCOL_PUBLICATION_OBSERVATION")
            row["observation"] = observation
            row["status"] = "passed" if worker["status"] == "passed" and observation.get("status") == "passed" else "failed"
        except Exception as error:
            row.update(status="failed", error={"type": type(error).__name__, "message": str(error)})
        if row["status"] != "passed":
            first_failure[str(records)] = {"index": sample["index"], "class": sample["class"], "first_failure": row.get("observation", {}).get("first_failure", "worker_resource_or_process")}
        write_json(output / "summary.json", {"samples": rows, "first_failures": first_failure})
    return {"status": "failed" if first_failure else "passed", "samples": rows, "first_failures": first_failure,
            "scope": "genuine generic IR artifact publication only; canonical result/carry remain out of scope"}


def run_protocol(output, plan, *, compilation=True, mixed_stages=True, pure=True, chain=True):
    if os.name != "nt":
        raise ValueError("PROTOCOL_WINDOWS_RESOURCE_ENFORCEMENT_REQUIRED")
    if any(os.environ.get(key) for key in BYPASSES):
        raise ValueError("PROTOCOL_BACKEND_BYPASS_FORBIDDEN")
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    pins = dependency_pins()
    write_json(output / "dependency-pins.json", pins)
    snapshot_inputs(output,pins)
    report = {"format": FORMAT, "status": "running", "plan": plan, "hardware": hardware(), "stages": {},
              "canonical_close_credit": False, "capacity_credit": False, "pid": os.getpid()}
    write_json(output / "summary.json", report)
    started = time.perf_counter()
    active_stage="compilation"
    try:
        if compilation:
            # Independent original-fact control exists before compiler projection.
            workload = generate_mixed(100, seed=plan["seed"])
            expected = mixed.target_expected(skouras(workload["neutral"]))
            from spl_compiler.run import bind_package, project
            from spl_compiler.schema import validate_package
            bound = bind_package(workload["neutral"]["package"], ROOT / "cases/sv/sv01.spl")
            validate_package(bound)
            inputs, aliases, lineage, dispositions = project(bound)
            openings = {"prepayment": aliases["sv/participant-prepayment/main-pool"]}
            mixed.check_projection(workload, skouras(workload["neutral"]), inputs, openings, lineage, dispositions)
            report["stages"]["compilation"] = compile_samples(output / "compilation", plan, pins, {"inputs": inputs, "openings": openings}, expected)
        else:
            report["stages"]["compilation"] = {"status": "not_executed", "reason": "explicit stage selection"}
        # Cached-target measurements do not depend on this disposable AOT
        # attempt. Their own frontend/source-byte and financial controls remain
        # mandatory; never substitute them for the failed fresh compilation.
        active_stage="mixed"
        if mixed_stages:
            report["stages"]["mixed"] = repeated_mixed(output / "mixed", plan, pins)
        else:
            report["stages"]["mixed"] = {"status": "not_executed", "reason": "explicit selection"}
        active_stage="ir_publication"
        if mixed_stages:
            report["stages"]["ir_publication"] = publication_samples(output / "ir-publication", report["stages"]["mixed"], plan, pins)
        else:
            report["stages"]["ir_publication"] = {"status": "not_executed", "reason": "actual audited input was not executed"}
        active_stage="pure"
        report["stages"]["pure"] = pure_samples(output/"pure",plan,pins) if pure else {"status":"not_executed","reason":"explicit selection"}
        active_stage="stage_chain"
        if chain and mixed_stages and report["stages"]["mixed"]["status"]=="passed":
            from scripts.spl_audited_stage_chain import run_chain
            report["stages"]["stage_chain"] = {str(records):run_chain(output/f"chain-{records}",records,4,pins,
                    prerequisite=next(row["summary_path"] for row in report["stages"]["mixed"]["samples"] if row["records"]==records and row["status"]=="passed"),
                    seed=plan["seed"]) for records in plan["records"]}
            report["stages"]["stage_chain"]["status"] = "passed" if all(report["stages"]["stage_chain"][str(records)]["status"]=="passed" for records in plan["records"]) else "failed"
        else:
            report["stages"]["stage_chain"] = {"status":"not_executed","reason":"required actual matching100/1000audits not complete or explicit selection","audited_closing_state":[]}
        require_pins(pins)
        report["unchanged_dependency_pins"] = True
        report["status"] = "failed" if any(row["status"] == "failed" for row in report["stages"].values()) else "passed"
        report["selected_repetition_completed"] = plan["full_repetition_protocol"] and all(row["status"] == "passed" for row in report["stages"].values())
        report["compilation_repetitions_completed"] = plan["full_repetition_protocol"] and report["stages"]["compilation"]["status"]=="passed"
        report["mixed_repetitions_completed"] = plan["full_repetition_protocol"] and report["stages"]["mixed"]["status"]=="passed"
        report["protocol_completed"] = report["selected_repetition_completed"]
        report["remaining_stages"] = [name for name,row in report["stages"].items() if row["status"]!="passed"]
    except Exception as error:
        report.update(status="failed", error={"type": type(error).__name__, "message": str(error)},first_failure=active_stage)
        report["stages"].setdefault(active_stage,{"status":"failed","error":report["error"]})
    for name in ("compilation","mixed","ir_publication","pure","stage_chain"):
        report["stages"].setdefault(name,{"status":"not_executed","reason":"earlier_required_orchestration_stage_failed"})
    if report["status"]=="failed":
        report.setdefault("first_failure",next((name for name,row in report["stages"].items() if row["status"]=="failed"),"dependency_validation"))
    report["elapsed_seconds"] = str(time.perf_counter() - started)
    write_json(output / "summary.json", report)
    return report


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "--publication-worker":
        if len(argv) != 5:
            raise ValueError("PROTOCOL_PUBLICATION_WORKER_ARGUMENTS")
        result = publication_worker(*argv[1:])
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
        return 0 if result["status"] == "passed" else 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--first-samples", type=int, default=3)
    parser.add_argument("--warm-samples", type=int, default=30)
    parser.add_argument("--records", nargs="+", type=int, choices=(100, 1000), default=[100, 1000])
    parser.add_argument("--host-load-note", required=True)
    parser.add_argument("--compiler-profile", choices=tuple(COMPILER_PROFILES), default="runtime256")
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)
    plan = make_plan(first_samples=args.first_samples, warm_samples=args.warm_samples, records=args.records, host_load_note=args.host_load_note, compiler_profile=args.compiler_profile)
    if args.plan_only:
        args.output.mkdir(parents=True, exist_ok=False)
        write_json(args.output / "plan.json", plan)
        return 0
    return 0 if run_protocol(args.output, plan)["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
