"""One bounded actual canonical compact close at100 or1000, never10000.

Independent original-fact controls precede projection. A matching current-a0
baseline and fresh same-candidate100 gate are required; failures retain every
artifact and do not authorize a successor or any larger retry.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from oracles.skouras import skouras, exact_json
from scripts.spl_mixed_benchmark import target_expected, check_target, check_projection
from spl_compiler.audited_artifacts import load_completed_audited_result
from spl_compiler.codecs import canonical, file_digest, write_json
from spl_compiler.checker import check_schedule
from spl_compiler.parser import parse
from spl_compiler.compact_execution import metadata
from spl_compiler.lean_tools import ROOT as BUILD_ROOT
from spl_compiler.run import bind_package, identities, project, run_package
from validation.mixed_workloads import generate_mixed, canonical_bytes

BASE_COMPILER = "a0e5b77dd654c936ec8fe5278537ee6b186ab021c1df289d73d290f874d396a4"
BASE_RUNTIME = "a7e4f8e55815ea72abfb1903b2578a5db95d6f505f582f8a67ded9880ac119ba"


def dependencies():
    paths = [*sorted((ROOT / "SPL").glob("*.lean")), *sorted((ROOT / "spl_compiler").glob("*.py"))]
    paths += [ROOT / path for path in ("SPL.lean", "lean-toolchain", "lakefile.toml",
              "scripts/spl_audit_worker.py", "scripts/spl_compact_publication_probe.py",
              "scripts/spl_mixed_benchmark.py", "scripts/spl_stage_benchmark.py", "scripts/spl_benchmark.py",
              "validation/mixed_workloads.py", "oracles/skouras.py", "cases/sv/neutral-oracle.json", "cases/sv/sv01.spl")]
    paths += [ROOT / ".lake/build/bin" / name for name in ("spl_audit.exe", "spl.exe", "spl_trace_stream.exe")]
    return {path.relative_to(ROOT).as_posix(): file_digest(path) for path in paths}


def qualify_baseline(baseline_path, records, seed, source, neutral_bytes):
    baseline_path = Path(baseline_path)
    baseline = metadata(baseline_path)
    if (baseline.get("status") != "passed" or not baseline.get("unchanged_dependency_pins") or
            baseline.get("kernel_identities") != [BASE_COMPILER, BASE_RUNTIME] or
            baseline.get("seed") != seed or baseline.get("counts", {}).get("raw_original_records") != records or
            baseline.get("implementation") != "legacy" or baseline.get("transport") != "compact-v2" or
            not baseline.get("required_audit_completed")):
        raise ValueError("COMPACT_BASELINE_QUALIFICATION")
    root = baseline_path.parent
    if ((root / "Source.spl").read_bytes() != Path(source).read_bytes() or
            canonical_bytes(metadata(root / "neutral-original.json")) != neutral_bytes):
        raise ValueError("COMPACT_BASELINE_SOURCE_OR_ORIGINAL_INPUT")
    samples = baseline.get("native_samples")
    if type(samples) is not list or len(samples) != 1 or samples[0].get("status") != "passed":
        raise ValueError("COMPACT_BASELINE_SAMPLE")
    wire = root / "audit-00/stdout.bin"
    trace = samples[0]["trace_validation"]
    if file_digest(wire) != trace["transport_sha256"] or wire.stat().st_size != trace["wire_bytes"]:
        raise ValueError("COMPACT_BASELINE_WIRE_CHANGED")
    return baseline, trace


def probe(output, *, records, baseline, prerequisite=None, seed=20261123, host_load_note):
    if BUILD_ROOT.resolve() != ROOT or records not in {100, 1000}:
        raise ValueError("COMPACT_PROBE_ROOT_OR_SCALE")
    if type(host_load_note) is not str or not host_load_note.strip():
        raise ValueError("COMPACT_PROBE_HOST_LOAD_REQUIRED")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    source = ROOT / "cases/sv/sv01.spl"
    pins = dependencies()
    report = {"format": "spl-compact-canonical-probe/1", "status": "running", "records": records,
              "seed": seed, "dependency_pins": pins, "kernel_identities": list(identities()),
              "host_load_note": host_load_note, "baseline": str(Path(baseline).resolve()),
              "prerequisite": str(Path(prerequisite).resolve()) if prerequisite else None,
              "stages": {}, "required_audit_completed": False,
              "parent_scope": "Finite100/1000 original preparation and returned small financial head; no total-parent256MiB claim.",
              "budgets": {"runtime_child_seconds": 60, "runtime_sampled_child_bytes": 256*1024*1024,
                          "wire_result_bytes": 64*1024*1024, "logical_bytes": 1024*1024*1024, "nodes": 100000,
                          "compiler_profile": "compiler1g180"}}
    started = time.perf_counter()
    try:
        if records == 1000:
            gate = metadata(prerequisite) if prerequisite else {}
            if (gate.get("status") != "passed" or gate.get("records") != 100 or
                    gate.get("dependency_pins") != pins or gate.get("seed") != seed or
                    not gate.get("required_audit_completed")):
                raise ValueError("COMPACT_FRESH100_GATE_REQUIRED")
        workload = generate_mixed(records, seed=seed)
        original_bytes = canonical_bytes(workload["neutral"])
        write_json(output / "neutral-original.json", workload["neutral"])
        write_json(output / "workload-counts.json", workload["counts"])
        original_hash = hashlib.sha256(original_bytes).hexdigest()
        report["counts"] = workload["counts"]
        report["original_sha256"] = original_hash
        _, old_trace = qualify_baseline(baseline, records, seed, source, original_bytes)
        report["stages"]["baseline"] = {"status": "passed", "source_sha256": file_digest(source)}
        oracle = skouras(workload["neutral"])
        expected = target_expected(oracle)
        write_json(output / "independent-oracle.json", exact_json(oracle))
        write_json(output / "expected.json", expected)
        report["stages"]["oracle_before_projection"] = {"status": "passed"}
        package = bind_package(workload["neutral"]["package"], source)
        projected = project(package)
        inputs, aliases, lineage, dispositions = projected
        checked = check_schedule(parse(source.read_text(encoding="utf-8")))
        alias_names = {row["alias"]: row["name"] for row in checked.schedule["declarations"] if row["kind"] == "opening"}
        if set(alias_names) != set(aliases):
            raise ValueError("COMPACT_OPENING_ALIAS")
        openings = {alias_names[name]: value for name, value in aliases.items()}
        check_projection(workload, oracle, inputs, openings, lineage, dispositions)
        write_json(output / "canonical-package.json", package)
        report["stages"]["projection"] = {"status": "passed"}
        result = run_package(package, source, backend="compare", audit_profile="compact-v2",
                             artifact_dir=output / "canonical")
        report["canonical_status"] = result["status"]
        report["diagnostics"] = result["diagnostics"]
        if result["status"] not in {"calculated", "calculated_zero"}:
            raise ValueError("COMPACT_CANONICAL_CLOSE_BLOCKED")
        trace = result["trace"]
        for key in ("logical_sha256", "transport_sha256", "node_count", "edge_count", "wire_bytes",
                    "expanded_trace_bytes", "canonical_expanded_trace_bytes"):
            if trace[key] != old_trace[key]:
                raise ValueError("COMPACT_BASELINE_LOGICAL_OR_WIRE_MISMATCH:" + key)
        statement = result["statements"][0]
        actual_pool = {key: statement[key] for key in expected["emissions"]["pool"]}
        actual = {"status": "calculated", "emissions": {"pool": actual_pool, "titles": result["detail"]},
                  "closing": {"prepayment": result["closing_state"][0]["quantity"]}, "diagnostics": result["diagnostics"]}
        check_target(actual, expected)
        if (canonical(result["source_to_target_lineage"]) != canonical(projected[2]) or
                canonical(result["input_dispositions"]) != canonical(projected[3])):
            raise ValueError("COMPACT_CANONICAL_ORIGINAL_LINEAGE")
        report["stages"]["financial_controls"] = {"status": "passed"}
        loaded = load_completed_audited_result(output / "canonical")
        if loaded != result:
            raise ValueError("COMPACT_LOADER_RETURNED_DIFFERENT_FINANCE")
        report["stages"]["validated_publication_loader"] = {"status": "passed"}
        report["trace"] = trace
        report["closing_state"] = result["closing_state"]
        report["required_audit_completed"] = True
        if canonical_bytes(workload["neutral"]) != original_bytes:
            raise ValueError("COMPACT_ORIGINAL_FACTS_CHANGED")
        report["status"] = "passed"
    except Exception as error:
        report.update(status="failed", error={"type": type(error).__name__, "message": str(error)})
    report["unchanged_dependency_pins"] = dependencies() == pins
    if not report["unchanged_dependency_pins"]:
        report["status"] = "failed"
    for stage in ("baseline", "oracle_before_projection", "projection", "financial_controls", "validated_publication_loader"):
        report["stages"].setdefault(stage, {"status": "not_executed", "reason": "earlier required stage failed"})
    report["elapsed_seconds"] = f"{time.perf_counter()-started:.6f}"
    report["successor"] = {"status": "not_executed", "reason": "single-close capacity probe; no automatic successor credit"}
    write_json(output / "summary.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records", type=int, choices=(100, 1000), required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--prerequisite", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-load-note", required=True)
    args = parser.parse_args()
    report = probe(**vars(args))
    print(report["status"], args.output / "summary.json")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
