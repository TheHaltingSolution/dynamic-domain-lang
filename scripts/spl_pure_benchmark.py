"""Time actual compiled settlement with decoded inputs, outside process overhead.

The native driver separates kernel/result retention, JSON serialization and full
independent outcome verification. Repeated opening nonces produce real output
changes. This harness performs no build and issues no canonical payment result.
"""
from copy import deepcopy
from fractions import Fraction
import argparse
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oracles.skouras import exact_json, skouras
from scripts.spl_mixed_benchmark import check_projection
from scripts.spl_stage_benchmark import measured_python, run_process
from spl_compiler.codecs import canonical, file_digest, money, number, write_json
from spl_compiler.lean_tools import lean_environment
from spl_compiler.run import bind_package, identities, project
from spl_compiler.schema import validate_package
from validation.mixed_workloads import generate_mixed


OFFSET = 14695981039346656037
PRIME = 1099511628211
MASK = (1 << 64) - 1


def native_json_bytes(value):
    """Independent encoding of Lean4.35 compact JSON, including control escapes."""
    if type(value) is str:
        def escape(character):
            if character == '"': return '\\"'
            if character == '\\': return '\\\\'
            if character == '\n': return '\\n'
            if character == '\r': return '\\r'
            if ord(character) < 32: return '\\u' + format(ord(character), '04x')
            return character
        return ('"' + ''.join(escape(c) for c in value) + '"').encode('utf-8')
    if type(value) is dict:
        if not all(type(key) is str for key in value):
            raise ValueError("PURE_JSON_KEY")
        return b'{' + b','.join(native_json_bytes(key) + b':' + native_json_bytes(value[key]) for key in sorted(value)) + b'}'
    if type(value) is list:
        return b'[' + b','.join(map(native_json_bytes, value)) + b']'
    if value is True: return b'true'
    if value is False: return b'false'
    if value is None: return b'null'
    if type(value) is int: return str(value).encode('ascii')
    raise ValueError("PURE_JSON_VALUE")


def fnv1a64(previous, encoded):
    for byte in encoded:
        previous = ((previous ^ byte) * PRIME) & MASK
    return previous


def native_expected(oracle):
    def value(item):
        if isinstance(item, Fraction):
            return {"numerator": str(item.numerator), "denominator": str(item.denominator)}
        if isinstance(item, dict): return {key: value(child) for key, child in item.items()}
        if isinstance(item, list): return [value(child) for child in item]
        return item
    pool = oracle["pool"]
    fields = ("asset_id", "cash", "fee", "allowed_cost", "basis", "share", "earned")
    return value({"status": "calculated", "diagnostics": [], "emissions": {
        "titles": [{key: row[key] for key in fields} for row in oracle["titles"]],
        "pool": {**{key: pool[key] for key in ("agreement_id", "participant_id", "pool_id", "period")},
                 "earned": pool["earned"], "recouped": pool["recovered"], "payable": pool["payable"]}},
        "closing": {"prepayment": pool["closing_prepayment"]}})


def prepare_case(records=100, *, seed=20261123, variants=64, initial_iterations=128,
                 maximum_iterations=8192, minimum_span_ns=100000000, warmups=8, samples=3):
    if type(variants) is not int or not 2 <= variants <= 128:
        raise ValueError("PURE_VARIANTS_2_TO_128")
    if not 2 <= initial_iterations <= maximum_iterations <= 8192 or not 1 <= minimum_span_ns <= 1000000000 or not 0 <= warmups <= 128 or not 1 <= samples <= 10:
        raise ValueError("PURE_PLAN_RESOURCE_LIMIT")
    workload = generate_mixed(records, seed=seed)
    baseline = skouras(workload["neutral"])
    rows = []
    for nonce in range(variants):
        # Exogenous benchmark openings are supplied original-state values. No
        # solved earnings or target answer is fed back into calculation inputs.
        original = deepcopy(workload["neutral"])
        opening = nonce * 1000
        original["package"]["state_cells"][0]["quantity"] = str(opening)
        controlled = skouras(original)
        rows.append({"nonce": str(nonce), "openings": {"prepayment": money(opening)}, "expected": native_expected(controlled)})
    bound = bind_package(workload["neutral"]["package"], ROOT / "cases/sv/sv01.spl")
    validate_package(bound)
    inputs, aliases, lineage, dispositions = project(bound)
    openings = {"prepayment": aliases["sv/participant-prepayment/main-pool"]}
    check_projection(workload, baseline, inputs, openings, lineage, dispositions)
    plan = {"format": "spl-pure-benchmark-plan/1", "initial_iterations": str(initial_iterations),
            "maximum_iterations": str(maximum_iterations), "minimum_span_ns": str(minimum_span_ns),
            "warmups": str(warmups), "samples": str(samples), "variants": rows}
    return {"workload": workload, "canonical_package": bound, "bindings": {"inputs": inputs, "openings": openings},
            "baseline_oracle": baseline, "plan": plan}


def check_observations(result, plan):
    if result.get("format") != "spl-pure-settlement-observations/1" or result.get("status") != "passed":
        raise ValueError("PURE_NATIVE_OBSERVATION_FAILED")
    variants = plan["variants"]
    encodings = [native_json_bytes(row["expected"]) for row in variants]
    if result["first_outcome"] != variants[0]["expected"] or result["variant_count"] != len(variants):
        raise ValueError("PURE_FIRST_OR_VARIANT_CONTROL")
    if result["warmup_calls"] != int(plan["warmups"]):
        raise ValueError("PURE_WARMUP_CONTROL")
    warm_checksum = fnv1a64(OFFSET, encodings[0])
    for index in range(int(plan["warmups"])):
        warm_checksum = fnv1a64(warm_checksum, encodings[(index + 1) % len(variants)])
    if result["warmup_checksum_fnv1a64"] != str(warm_checksum):
        raise ValueError("PURE_WARMUP_CHECKSUM")
    if len(result["samples"]) != int(plan["samples"]):
        raise ValueError("PURE_SAMPLE_COUNT")
    for sample in [*result["calibration"], *result["samples"]]:
        count = sample["iterations"]
        if type(count) is not int or not 2 <= count <= int(plan["maximum_iterations"]):
            raise ValueError("PURE_ITERATION_CONTROL")
        checksum, size = OFFSET, 0
        for index in range(count):
            encoded = encodings[index % len(variants)]
            checksum = fnv1a64(checksum, encoded)
            size += len(encoded)
        if sample["checksum_fnv1a64"] != str(checksum) or sample["serialized_bytes"] != size or sample["independent_outcome_control"] != "passed":
            raise ValueError("PURE_BATCH_CHECKSUM_OR_BYTES")
        if any(type(sample[key]) is not int or sample[key] < 0 for key in ("settlement_ns", "serialization_ns", "verification_ns")):
            raise ValueError("PURE_CLOCK_OBSERVATION")
    resolution = result["samples"][0]["settlement_ns"] >= int(plan["minimum_span_ns"])
    if result["resolution_span_reached"] != resolution:
        raise ValueError("PURE_RESOLUTION_CONTROL")
    return {"status": "passed", "checked_batches": len(result["calibration"]) + len(result["samples"]),
            "checksum_scope": "independently encoded complete original-fact oracle outcomes, nonce order and byte counts; FNV is consumption evidence, not authentication"}


def source_files():
    paths = ["Demos/SVBenchmarkLibrary.lean", "Demos/PureSettlementBenchmark.lean", "scripts/spl_pure_benchmark.py",
             "scripts/spl_mixed_benchmark.py", "scripts/spl_stage_benchmark.py", "scripts/spl_benchmark.py",
             "validation/mixed_workloads.py", "oracles/skouras.py", "cases/sv/neutral-oracle.json", "cases/sv/sv01.spl", "SPL.lean", "lean-toolchain", "lakefile.toml"]
    result = [ROOT / path for path in paths]
    result += sorted((ROOT / "SPL").glob("*.lean")) + sorted((ROOT / "spl_compiler").glob("*.py")) + sorted((ROOT / "schemas").glob("*.json"))
    return sorted(set(result))


def benchmark(output, records=(100, 1000), *, process_repeats=3, seed=20261123, timeout=60,
              variants=64, initial_iterations=128, maximum_iterations=8192, minimum_span_ns=100000000,
              warmups=8, samples=3):
    if not 1 <= process_repeats <= 5 or not records or any(record not in {100, 1000} for record in records) or len(set(records)) != len(records):
        raise ValueError("PURE_PROCESS_OR_COHORT_LIMIT")
    output = Path(output).resolve()
    suffix = ".exe" if os.name == "nt" else ""
    binaries = {name: ROOT / ".lake/build/bin" / (name + suffix) for name in ("spl", "spl_pure_benchmark")}
    if any(not path.is_file() for path in binaries.values()):
        raise ValueError("Build spl_pure_benchmark with the pinned toolchain first")
    sources = source_files()
    pins = {path.relative_to(ROOT).as_posix(): file_digest(path) for path in sources}
    pins.update({"binary:" + name: file_digest(path) for name, path in binaries.items()})
    before = identities()
    _, env = lean_environment()
    output.mkdir(parents=True, exist_ok=False)
    for path in sources:
        destination = output / "sources" / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    report = {"format": "spl-pure-performance/1", "status": "running", "dependency_pins": pins,
              "kernel_identities": list(before), "python": sys.version, "seed": seed,
              "lean_toolchain": (ROOT / "lean-toolchain").read_text().strip(), "logical_cpus": os.cpu_count(),
              "budgets": {"child_timeout_seconds": timeout, "child_stdout_bytes": 1024 * 1024,
                          "child_sampled_working_set_bytes": 256 * 1024 * 1024}, "cohorts": [],
              "limits": ["Cached decoded inputs and varied supplied openings; no canonical finalization or audit is timed.",
                         "Kernel batch includes nonce lookup, noinline IO-call and strict result retention overhead.",
                         "First decoded calls do not establish cold OS/CPU caches; child process wall includes all setup/checks/output.",
                         "Serialization and verification/checksum are separately timed; no whole-process subtraction is used.",
                         "Three child processes/batches are disclosed observations, not production p95 or RR03 latency acceptance.",
                         "Generated library must match authoritative native compile-library output; source/binary correspondence additionally relies on pinned Lake build."]}
    write_json(output / "summary.json", report)
    started = time.perf_counter()
    try:
        emission = run_process([binaries["spl"], "compile-library", ROOT / "cases/sv/sv01.spl", output / "NativeLibrary.lean"],
                               output / "library-emission", env, timeout, 1024 * 1024)
        report["native_library_emission"] = emission
        if emission["status"] != "passed" or (output / "NativeLibrary.lean").read_bytes() != (ROOT / "Demos/SVBenchmarkLibrary.lean").read_bytes():
            raise ValueError("PURE_LIBRARY_NATIVE_EMISSION_MISMATCH")
        for record_count in records:
            work = output / f"mixed-{record_count}"
            work.mkdir()
            case, preparation = measured_python(lambda: prepare_case(record_count, seed=seed, variants=variants,
                initial_iterations=initial_iterations, maximum_iterations=maximum_iterations, minimum_span_ns=minimum_span_ns,
                warmups=warmups, samples=samples))
            write_json(work / "neutral-original.json", case["workload"]["neutral"])
            write_json(work / "canonical-package.json", case["canonical_package"])
            write_json(work / "baseline-independent-oracle.json", exact_json(case["baseline_oracle"]))
            write_json(work / "bindings.json", case["bindings"])
            write_json(work / "plan.json", case["plan"])
            cohort = {"records": record_count, "counts": case["workload"]["counts"], "preparation": preparation,
                      "bindings_sha256": file_digest(work / "bindings.json"), "plan_sha256": file_digest(work / "plan.json"),
                      "binding_bytes": (work / "bindings.json").stat().st_size, "plan_bytes": (work / "plan.json").stat().st_size,
                      "processes": [], "status": "running"}
            report["cohorts"].append(cohort)
            per_call = []
            serialization = []
            for repeat in range(process_repeats):
                destination = work / f"process-{repeat:02d}"
                process = run_process([binaries["spl_pure_benchmark"], work / "bindings.json", work / "plan.json"],
                                      destination, env, timeout, 1024 * 1024)
                cohort["processes"].append(process)
                if process["status"] == "passed":
                    try:
                        observation = json.loads((destination / "stdout.bin").read_bytes())
                        process["independent_control"] = check_observations(observation, case["plan"])
                        process["observation"] = observation
                        for sample in observation["samples"]:
                            per_call.append(Fraction(sample["settlement_ns"], sample["iterations"]))
                            serialization.append(Fraction(sample["serialization_ns"], sample["iterations"]))
                    except Exception as error:
                        process["status"] = "failed"
                        process["error"] = {"type": type(error).__name__, "message": str(error)}
                write_json(destination / "checked-process.json", process)
            cohort["control_status"] = "passed" if all(process["status"] == "passed" for process in cohort["processes"]) else "failed"
            cohort["inner_sample_count"] = len(per_call)
            cohort["settlement_ns_per_call_median"] = number(statistics.median(per_call)) if per_call else None
            cohort["serialization_ns_per_call_median"] = number(statistics.median(serialization)) if serialization else None
            cohort["timer_span_reached_all"] = all(process.get("observation", {}).get("resolution_span_reached") is True for process in cohort["processes"])
            cohort["status"] = "passed" if cohort["control_status"] == "passed" and cohort["timer_span_reached_all"] else "failed"
            if cohort["control_status"] == "passed" and not cohort["timer_span_reached_all"]:
                cohort["timing_limit"] = "PURE_MINIMUM_SPAN_NOT_REACHED_AT_FIXED_ITERATION_CAP"
            write_json(work / "measurement.json", cohort)
            write_json(output / "summary.json", report)
            print(f"pure mixed{record_count}: {cohort['status']}; median settlement ns/call={cohort['settlement_ns_per_call_median']}; samples={cohort['inner_sample_count']}", flush=True)
        current = {path.relative_to(ROOT).as_posix(): file_digest(path) for path in sources}
        current.update({"binary:" + name: file_digest(path) for name, path in binaries.items()})
        report["unchanged_dependency_pins"] = current == pins and identities() == before
        report["status"] = "passed" if report["unchanged_dependency_pins"] and all(row["status"] == "passed" for row in report["cohorts"]) else "failed"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    report["elapsed_seconds"] = f"{time.perf_counter()-started:.6f}"
    write_json(output / "summary.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records", type=int, nargs="+", choices=(100, 1000), default=[100, 1000])
    parser.add_argument("--process-repeats", type=int, default=3)
    parser.add_argument("--variants", type=int, default=64)
    parser.add_argument("--initial-iterations", type=int, default=128)
    parser.add_argument("--maximum-iterations", type=int, default=8192)
    parser.add_argument("--minimum-span-ns", type=int, default=100000000)
    parser.add_argument("--warmups", type=int, default=8)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args(argv)
    try:
        result = benchmark(args.output, args.records, process_repeats=args.process_repeats, variants=args.variants,
            initial_iterations=args.initial_iterations, maximum_iterations=args.maximum_iterations,
            minimum_span_ns=args.minimum_span_ns, warmups=args.warmups, samples=args.samples, timeout=args.timeout)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    print(f"Pure benchmark {result['status']}: {args.output / 'summary.json'}")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
