"""Run a bounded conformance campaign without changing compiler registrations.

Run from any directory with this checkout's Python. Artifacts must have a new
destination; every generated input and backend outcome is retained for replay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, loads, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import compile_schedule, interpret_schedule, lean, lean_environment
from spl_compiler.parser import parse
from spl_compiler.run import identities, normalize_target
from spl_compiler.modules import module_identities
from validation.generated_cases import generate_cases
from validation.decision_cases import generate_decision_cases
from validation.interaction_cases import generate_interaction_cases, coverage_contract
from validation.trace_coverage import summarize_trace

MATRIX = ROOT / "docs/spl/feature-test-matrix.json"
BYPASSES = ("QUEST_REFERENCE_ONLY", "SPL_QUANTITIES_REFERENCE_ONLY",
            "SPL_REVISION_REFERENCE_ONLY", "SPL_M1_BACKEND", "SPL_WATERFALL_BACKEND")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    # Telemetry is represented as strings; financial transport stays exact.
    write_json(path, value)


def git(*args):
    proc = subprocess.run(["git", *args], cwd=ROOT, capture_output=True)
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))
    return proc.stdout


def source_names():
    names = set(git("ls-files", "-z").decode("utf-8").split("\0")) - {""}
    for folder in (ROOT / "validation", ROOT / "Tests"):
        names.update(p.relative_to(ROOT).as_posix() for p in folder.glob("*.py"))
    for folder in (ROOT / name for name in ("SPL", "spl_compiler", "schemas", "oracles", "cases", "Demos", "scripts", "docs/spl")):
        names.update(p.relative_to(ROOT).as_posix() for p in folder.rglob("*")
                     if p.is_file() and p.suffix in {".lean", ".py", ".json", ".spl", ".md", ".csv"})
    names.update(("scripts/spl_conformance.py", "docs/spl/feature-test-matrix.json"))
    return names


def freeze_sources(output):
    """Snapshot tracked files plus new campaign sources, never ignored data."""
    names = source_names()
    files = {}
    for name in sorted(names):
        source = ROOT / name
        if not source.is_file():
            raise ValueError("Missing campaign source: " + name)
        data = source.read_bytes()
        target = output / "source-freeze" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        files[name] = sha256(data)
    manifest = {"inventory": "git-tracked-and-campaign", "git_head": git("rev-parse", "HEAD").decode().strip(),
                "git_status": git("status", "--short").decode().splitlines(),
                "files": files}
    dump(output / "source-manifest.json", manifest)
    return manifest


def changed_sources(manifest):
    changed = [name for name, digest in manifest["files"].items()
               if not (ROOT / name).is_file() or sha256((ROOT / name).read_bytes()) != digest]
    if manifest.get("inventory") == "git-tracked-and-campaign":
        changed.extend(sorted(source_names() - set(manifest["files"])))
    return changed


def comparable(outcome):
    normalized = normalize_target(outcome)
    return {"status": normalized["status"], "emissions": normalized["emissions"],
            "closing": normalized["closing"],
            "diagnostic_codes": [d["code"] for d in normalized["diagnostics"]]}


def run_generated(cases, output):
    """Preserve each exact case before execution and each result before checking."""
    rows, compiled = [], {}
    for index, case in enumerate(cases):
        work = output / "generated" / f"case-{index:03d}"
        work.mkdir(parents=True)
        dump(work / "case.json", case)
        source = work / "Source.spl"
        source.write_bytes(case["source"].encode("utf-8"))
        digest = sha256(source.read_bytes())
        bindings = work / "bindings.json"
        dump(bindings, case["bindings"])
        row = {"id": case["id"], "seed": case["seed"], "features": case["features"],
               "property": case["property"], "source_sha256": digest,
               "artifact": work.relative_to(output).as_posix(), "backends": {}, "status": "failed"}
        started = time.perf_counter()
        def retain(name, outcome):
            dump(work / (name + ".json"), outcome)
            actual = comparable(outcome)
            row["backends"][name] = {"status": "passed" if canonical(actual) == canonical(expected) else "failed",
                                      "actual": actual}

        try:
            expected = normalize_target(case["expected"])
            program = check_schedule(parse(case["source"]))
            retain("reference", evaluate(program, case["bindings"]["inputs"],
                                          case["bindings"]["openings"]).to_dict())
            native_ir = interpret_schedule(source, bindings)
            retain("native_ir", native_ir)
            coverage = summarize_trace(native_ir["trace"], digest)
            dump(work / "native-ir-observations.json", coverage)
            if digest not in compiled:
                compiled[digest] = compile_schedule(source, work / "Settlement.lean")
            target = compiled[digest]
            if target.parent != work:
                (work / "Settlement.lean").write_bytes(target.read_bytes())
            retain("native_emitted", loads(lean(["--run", target, bindings])))
            row["status"] = "passed" if all(v["status"] == "passed" for v in row["backends"].values()) else "failed"
        except Exception as error:
            row["error"] = {"type": type(error).__name__, "message": str(error)}
            if hasattr(error, "diagnostic"):
                row["error"]["diagnostic"] = error.diagnostic()
            elif hasattr(error, "to_dict"):
                row["error"]["diagnostic"] = error.to_dict()
        row["elapsed_seconds"] = f"{time.perf_counter() - started:.6f}"
        dump(work / "check.json", row)
        rows.append(row)
        print(f"generated {case['id']}: {row['status']}", flush=True)
    return rows


def witness_selectors(matrix):
    return sorted({w["test"] for feature in matrix["features"] for w in feature["witnesses"]})


class RecordedResults(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.setdefault(test.id(), "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records[test.id()] = "failed"

    def addError(self, test, err):
        super().addError(test, err)
        self.records[test.id()] = "error"

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records[test.id()] = "skipped"
        if hasattr(test, "test_case"):
            self.records[test.test_case.id()] = "skipped"

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.records[test.id()] = "expected_failure"

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.records[test.id()] = "unexpected_success"

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.records[test.id()] = "failed"


def witness_worker(selectors, output):
    suite = unittest.defaultTestLoader.loadTestsFromNames(selectors)
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResults).run(suite)
    dump(output, {"tests_run": result.testsRun, "outcomes": result.records,
                  "successful": result.wasSuccessful()})
    return 0 if result.wasSuccessful() else 1


def run_witnesses(selectors, output):
    if not selectors:
        return {"tests_run": 0, "outcomes": {}, "status": "not_executed"}
    request = output / "witness-selectors.json"
    dump(request, selectors)
    result_path = output / "witness-results.json"
    with (output / "witnesses.log").open("wb") as log:
        proc = subprocess.run([sys.executable, __file__, "--worker", str(request), str(result_path)],
                              cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    result = json.loads(result_path.read_text(encoding="utf-8")) if result_path.is_file() else {"tests_run": 0, "outcomes": {}}
    result["exit_code"] = proc.returncode
    result["uncredited_selectors"] = [s for s in selectors if result["outcomes"].get(s) != "passed"]
    result["fixture_outcomes"] = {s: status for s, status in result["outcomes"].items() if s not in selectors}
    if proc.returncode:
        # Fixture errors or interruption may prevent unittest from reporting a
        # requested method. Keep the batch failure visible on its feature row.
        for selector in selectors:
            result["outcomes"].setdefault(selector, "error")
    result["status"] = "passed" if proc.returncode == 0 and not result["uncredited_selectors"] else "failed"
    return result


def matrix_report(matrix, outcomes):
    rows = []
    for feature in matrix["features"]:
        witnesses = [{**w, "execution": outcomes.get(w["test"], "not_executed")}
                     for w in feature["witnesses"]]
        states = [w["execution"] for w in witnesses]
        status = "gap" if feature["status"] == "gap" else (
            "passed" if states and all(s == "passed" for s in states) else
            "failed" if any(s in {"failed", "error", "unexpected_success"} for s in states) else "not_executed")
        rows.append({**feature, "execution": status, "witnesses": witnesses})
    return {"format": "spl-feature-test-execution/1", "features": rows,
            "scope": matrix.get("scope", "bounded witness inventory"),
            "matrix_limitations": matrix.get("limitations", []),
            "limits": ["Witness stages describe inspected paths, not measured compiler line coverage.",
                       "Matrix backend stages are declarations from test inspection, not per-test instrumentation.",
                       "Passing a bounded witness does not establish its whole feature family.",
                       "Skipped, absent and unexecuted witnesses are never passes."]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261123)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--corpus", choices=["boundaries", "decisions", "combined", "interactions"], default="boundaries",
                        help="amount boundaries, finite decisions, both, or the finite rounding interaction cover")
    parser.add_argument("--generated-only", action="store_true", help="leave matrix witnesses explicitly unexecuted")
    parser.add_argument("--replay-cases", type=Path, help="JSON list of retained generated cases; run with --generated-only")
    args = parser.parse_args(argv)
    active = [name for name in BYPASSES if name in os.environ]
    if active:
        parser.error("Clear backend overrides before a campaign: " + ", ".join(active))
    cases = (loads(args.replay_cases.read_bytes()) if args.replay_cases
             else generate_cases(seed=args.seed, count=args.count))
    if not args.replay_cases:
        if args.corpus == "decisions":
            cases = generate_decision_cases(seed=args.seed)
        elif args.corpus == "combined":
            cases += generate_decision_cases(seed=args.seed)
        elif args.corpus == "interactions":
            cases = generate_interaction_cases(seed=args.seed)
    if isinstance(cases, dict):
        cases = [cases]
    if not isinstance(cases, list) or not 1 <= len(cases) <= 64:
        parser.error("A campaign needs 1..64 generated cases")
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    manifest = freeze_sources(args.output)
    dump(args.output / "cases.json", cases)
    if not args.replay_cases and args.corpus == "interactions":
        dump(args.output / "interaction-contract.json", coverage_contract())
    metadata = {"format": "spl-conformance-campaign/1", "status": "running",
                "python": sys.version, "platform": platform.platform(), "argv": sys.argv,
                "lean_toolchain": (ROOT / "lean-toolchain").read_text().strip(),
                "lean_version": lean(["--version"]).strip(),
                "lean_executable": lean_environment()[0],
                "build_identities": {"compiler": identities()[0], "runtime": identities()[1],
                                     "module": module_identities()[0]},
                "backend_overrides": {}, "matrix_sha256": sha256(MATRIX.read_bytes()),
                "generated_backends": ["reference", "native_ir", "native_emitted"],
                "source_manifest": "source-manifest.json", "case_seeds": sorted({c["seed"] for c in cases}),
                "case_count": len(cases), "input_mode": "replay" if args.replay_cases else "generated",
                "corpus": "retained_cases" if args.replay_cases else args.corpus,
                "matrix_execution": "not_executed" if args.generated_only else "requested",
                "source_stability": "Requires a stable checkout before startup; snapshot/end checks are not transactional import isolation.",
                "scope": "Disclosed bounded development validation; not held-out evaluation or a compiler proof."}
    dump(args.output / "campaign.json", metadata)
    generated = run_generated(cases, args.output)
    witnesses = run_witnesses([] if args.generated_only else witness_selectors(matrix), args.output)
    features = matrix_report(matrix, witnesses["outcomes"])
    dump(args.output / "feature-execution.json", features)
    dump(args.output / "compiler-coverage.json", {
        "status": "witness_mapping_only", "feature_execution": "feature-execution.json",
        "measured_line_or_rule_coverage": "not_instrumented"})
    dump(args.output / "settlement-coverage.json", {
        "native_ir": [{"case": row["id"], "source_sha256": row["source_sha256"],
                       "observations": row["artifact"] + "/native-ir-observations.json"}
                      for row in generated if (args.output / row["artifact"] / "native-ir-observations.json").is_file()],
        "native_emitted_decisions": "not_instrumented", "denominator": "not_established"})
    dump(args.output / "domain-coverage.json", {
        "feature_execution": "feature-execution.json",
        "generated_feature_combinations": [{"case": row["id"], "features": row["features"], "status": row["status"]}
                                           for row in generated],
        "finite_configuration_cover": (coverage_contract() if not args.replay_cases and args.corpus == "interactions" else None),
        "limits": ["Only an explicitly attached finite configuration contract receives pair/triple coverage credit; no all-program or emitted-target coverage claim.", "Mutation campaign and workload capacity remain separate work."]})
    changed = changed_sources(manifest)
    metadata.update({"status": "passed" if not changed and all(row["status"] == "passed" for row in generated)
                     and witnesses["status"] in {"passed", "not_executed"} else "failed",
                     "generated": generated, "witnesses": witnesses, "changed_sources": changed,
                     "elapsed_seconds": f"{time.perf_counter() - started:.6f}"})
    dump(args.output / "campaign.json", metadata)
    print(f"Campaign {metadata['status']}: {args.output / 'campaign.json'}", flush=True)
    return 0 if metadata["status"] == "passed" else 1


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        raise SystemExit(witness_worker(json.loads(Path(sys.argv[2]).read_text(encoding="utf-8")), Path(sys.argv[3])))
    raise SystemExit(main())
