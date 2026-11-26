"""Bounded, retained semantic mutation campaign; never rebuild dependencies."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path[:1]:
    sys.path.insert(0, str(ROOT))

from validation.semantic_mutations import BACKENDS, bindings, classify, oracle, population


def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Processes:
    def __init__(self, output, *, process_seconds=30, total_seconds=300, max_processes=224, max_bytes=1048576):
        if not (1 <= process_seconds <= 180 and 1 <= total_seconds <= 600 and 1 <= max_processes <= 256 and 1024 <= max_bytes <= 8 * 1048576):
            raise ValueError("MUTATION_RESOURCE_BOUNDS")
        from spl_compiler.lean_tools import ROOT as build_root, lean_environment
        if build_root.resolve() != ROOT:
            raise ValueError("MUTATION_BUILD_ROOT")
        self.exe, self.env = lean_environment()
        self.output, self.commands = Path(output), []
        self.process_seconds, self.deadline = process_seconds, time.monotonic() + total_seconds
        self.max_processes, self.max_bytes = max_processes, max_bytes

    def run(self, arguments, label):
        if len(self.commands) >= self.max_processes or time.monotonic() >= self.deadline:
            return {"execution": "unexecuted", "reason": "campaign process/time budget exhausted"}
        identity = str(len(self.commands)).zfill(3)
        folder = self.output / "commands" / identity; folder.mkdir(parents=True)
        record = {"id": identity, "label": label, "argv": [self.exe, *map(str, arguments)], "cwd": str(ROOT),
                  "LEAN_PATH": self.env.get("LEAN_PATH"), "timeout_seconds": min(self.process_seconds, self.deadline - time.monotonic()),
                  "stdout": str((folder / "stdout.txt").relative_to(self.output)), "stderr": str((folder / "stderr.txt").relative_to(self.output)),
                  "max_bytes_per_stream": self.max_bytes}
        self.commands.append(record)
        started = time.monotonic(); exceeded = threading.Event()
        proc = subprocess.Popen(record["argv"], cwd=ROOT, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def drain(stream, path):
            written = 0
            with path.open("wb") as target:
                while chunk := stream.read(4096):
                    keep = chunk[:max(0, self.max_bytes - written)]
                    target.write(keep); written += len(keep)
                    if len(keep) < len(chunk):
                        exceeded.set()
                        try: proc.kill()
                        except OSError: pass
                        break
            stream.close()

        threads = [threading.Thread(target=drain, args=(stream, folder / name), daemon=True)
                   for stream, name in ((proc.stdout, "stdout.txt"), (proc.stderr, "stderr.txt"))]
        for thread in threads: thread.start()
        status = "completed"
        try:
            proc.wait(timeout=record["timeout_seconds"])
        except subprocess.TimeoutExpired:
            status = "timeout"; proc.kill(); proc.wait()
        for thread in threads: thread.join(timeout=2)
        if exceeded.is_set(): status = "output_limit"
        if any(thread.is_alive() for thread in threads): status = "capture_incomplete"
        record.update(execution=status, returncode=proc.returncode, elapsed_seconds=round(time.monotonic() - started, 6))
        if proc.returncode and status == "completed": record["execution"] = "process_failed"
        record["stdout_sha256"] = sha(folder / "stdout.txt"); record["stderr_sha256"] = sha(folder / "stderr.txt")
        write(folder / "command.json", record)
        return record

    def json_outcome(self, arguments, label):
        from spl_compiler.codecs import loads
        record = self.run(arguments, label)
        result = {"execution": record["execution"], "command_id": record.get("id"), "reason": record.get("reason", "")}
        if record["execution"] == "completed":
            try:
                raw = loads((self.output / record["stdout"]).read_bytes())
                result.update(observable=observable(raw), raw=raw)
            except (ValueError, KeyError, TypeError) as error:
                result.update(execution="invalid_backend_output", reason=str(error))
        return result


def observable(raw):
    from spl_compiler.run import normalize_target
    value = normalize_target(raw)
    if value["status"] not in {"calculated", "blocked"} or not isinstance(value["emissions"], dict) or not isinstance(value["closing"], dict):
        raise ValueError("MUTATION_BACKEND_OUTCOME_SHAPE")
    return {"status": value["status"], "emissions": value["emissions"], "closing": value["closing"],
            "diagnostic_codes": [row["code"] for row in value["diagnostics"]]}


def native_frontend_observation(record, output, target):
    """Compilation evidence, never a financial outcome or inferred rejection."""
    from spl_compiler.codecs import loads
    result = {"status": "incomplete", "execution": record["execution"], "command_id": record.get("id"),
              "diagnostic_codes": [], "reason": record.get("reason", record["execution"])}
    if record["execution"] == "completed" and Path(target).is_file():
        return {**result, "status": "accepted", "reason": "native compilation produced a target"}
    if record["execution"] in {"completed", "process_failed"} and "stdout" in record:
        try:
            raw = loads((Path(output) / record["stdout"]).read_bytes())
            codes = [row["code"] for row in raw.get("diagnostics", [])]
            if raw.get("status") == "blocked" and codes and set(codes) <= {"TYPE_MISMATCH", "SYNTAX_ERROR"}:
                return {**result, "status": "rejected", "diagnostic_codes": codes, "reason": "actual selected frontend diagnostics", "raw": raw}
        except (ValueError, KeyError, TypeError):
            pass
    return {**result, "reason": "native frontend did not supply a selected actual rejection: " + result["reason"]}


def run_campaign(output, *, phase="initial", mutant_ids=None, case_ids=None, backends=BACKENDS, process_seconds=30,
                 total_seconds=300, max_processes=224, max_bytes=1048576):
    from spl_compiler import checker, evaluator, emitter, parser
    from spl_compiler.codecs import DataError, loads
    from spl_compiler.model import SPLException
    from spl_compiler.run import identities
    output = Path(output).resolve()
    if output.is_relative_to(ROOT):
        raise ValueError("MUTATION_EXTERNAL_OUTPUT_REQUIRED")
    if output.exists():
        raise ValueError("MUTATION_FRESH_OUTPUT_REQUIRED")
    declared = population(phase)
    selected_cases = [case for case in declared["cases"] if case_ids is None or case["id"] in case_ids]
    selected = [mutant for mutant in declared["mutants"] if mutant_ids is None or mutant["id"] in mutant_ids]
    if not selected_cases or not selected or not set(backends) <= set(BACKENDS) or len(set(backends)) != len(backends):
        raise ValueError("MUTATION_SELECTED_POPULATION")
    if case_ids and set(case_ids) != {case["id"] for case in selected_cases}:
        raise ValueError("MUTATION_UNKNOWN_CASE")
    if mutant_ids and set(mutant_ids) != {mutant["id"] for mutant in selected}:
        raise ValueError("MUTATION_UNKNOWN_MUTANT")
    if any(len(item["source"].encode("utf-8")) > 32768 for item in [declared["baseline"], *selected] if item["source"] is not None) or any(
            len(json.dumps(case).encode("utf-8")) > 32768 for case in selected_cases):
        raise ValueError("MUTATION_SOURCE_OR_FACT_BYTE_BOUND")
    for module in (checker, evaluator, emitter, parser):
        if not Path(module.__file__).resolve().is_relative_to(ROOT):
            raise ValueError("MUTATION_MODULE_ORIGIN")
    output.mkdir(parents=True)
    proc = Processes(output, process_seconds=process_seconds, total_seconds=total_seconds, max_processes=max_processes, max_bytes=max_bytes)
    originals = {case["id"]: oracle(case, declared["policy"]) for case in selected_cases}
    write(output / "population.json", declared)
    write(output / "selected-population.json", {"cases": [case["id"] for case in selected_cases], "mutants": [item["id"] for item in selected],
          "required_backends": list(BACKENDS), "effective_requested_backends": list(backends)})
    write(output / "independent-controls.json", originals)
    files = set((ROOT / "SPL").glob("*.lean")) | set((ROOT / "spl_compiler").glob("*.py")) | set((ROOT / "schemas").glob("*.json"))
    files |= {ROOT / name for name in ("SPL.lean", "lean-toolchain", "validation/semantic_mutations.py", "scripts/spl_mutation_campaign.py",
                                      "Tests/test_semantic_mutations.py", "docs/spl/semantic-mutation-campaign.md")}
    pins = {path.relative_to(ROOT).as_posix(): sha(path) for path in files}
    for name in pins:
        target = output / "source-snapshot" / name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes((ROOT / name).read_bytes())
    original_identities = identities()
    all_results, validations = {}, {}
    started = time.monotonic()
    sources = [declared["baseline"], *[item for item in selected if item["source"] is not None]]
    for item in sources:
        identity = item["id"]; folder = output / "sources" / identity; folder.mkdir(parents=True)
        authored = folder / "Source.spl"; authored.write_bytes(item["source"].encode("utf-8"))
        write(folder / "source-record.json", item)
        checked = None
        try:
            checked = checker.check_schedule(parser.parse(item["source"], str(authored)))
            validation = {"status": "valid", "stage": "reference_typecheck"}
        except SPLException as error:
            validation = {"status": "invalid", "stage": "reference_frontend", "reason": error.code, "diagnostics": [d.to_dict() for d in error.diagnostics]}
        validations[identity] = validation
        target = folder / "Native.lean"
        compiled = {"execution": "unexecuted", "reason": "native emitted backend not requested or invalid reference source"}
        if "native_emitted" in backends or (checked is None and {"native_ir", "native_emitted"} & set(backends)):
            compiled = proc.run(["--run", ROOT / "SPL/Main.lean", "compile", authored, target], identity + ":native_frontend_compile")
        validation["native_frontend"] = compiled
        validation["native_frontend_observation"] = native_frontend_observation(compiled, output, target)
        if checked is not None and ("native_ir" in backends or "native_emitted" in backends):
            validation["native_ir_export"] = proc.run(["--run", ROOT / "SPL/Main.lean", "ir", authored, folder / "typed-ir.json"], identity + ":native_ir_export")
        write(folder / "validation.json", validation)
        all_results[identity] = {}
        for case in selected_cases:
            cid = case["id"]; case_folder = folder / cid; case_folder.mkdir()
            supplied = bindings(case); bound = case_folder / "bindings.json"
            write(case_folder / "original-facts.json", case); write(bound, supplied); write(case_folder / "expected.json", originals[cid])
            outcomes = {}
            if checked is not None:
                if "reference" in backends:
                    try:
                        raw = evaluator.evaluate(checked, **supplied).to_dict()
                        outcomes["reference"] = {"execution": "completed", "observable": observable(raw), "raw": raw}
                    except Exception as error:
                        outcomes["reference"] = {"execution": "reference_failed", "reason": type(error).__name__ + ": " + str(error)}
                if "native_ir" in backends:
                    outcomes["native_ir"] = proc.json_outcome(["--run", ROOT / "SPL/Main.lean", "interpret", authored, bound], identity + ":" + cid + ":native_ir")
                if "native_emitted" in backends:
                    outcomes["native_emitted"] = (proc.json_outcome(["--run", target, bound], identity + ":" + cid + ":native_emitted")
                        if compiled["execution"] == "completed" else {"execution": "unexecuted", "reason": "native compilation incomplete"})
                if "python_emitted" in backends:
                    try:
                        typed_inputs = {name: evaluator.decode_value(value, checked.types[name]) for name, value in supplied["inputs"].items()}
                        typed_openings = {name: evaluator.decode_value(value, checked.types[name]) for name, value in supplied["openings"].items()}
                        mirror = case_folder / "PythonEmitted.lean"
                        mirror.write_bytes(emitter.emit_module(checked, typed_inputs, typed_openings).encode("utf-8"))
                        outcomes["python_emitted"] = proc.json_outcome(["--run", mirror], identity + ":" + cid + ":python_emitted")
                    except Exception as error:
                        outcomes["python_emitted"] = {"execution": "emission_failed", "reason": type(error).__name__ + ": " + str(error)}
            all_results[identity][cid] = outcomes
            write(case_folder / "outcomes.json", outcomes)
    classifications = []
    for item in selected:
        for case in selected_cases:
            cid = case["id"]
            result = classify(item, originals[cid], all_results.get("baseline", {}).get(cid, {}),
                              all_results.get(item["id"], {}).get(cid, {}), validation=validations.get(item["id"]), policy=declared["policy"])
            classifications.append({"mutant_id": item["id"], "case_id": cid, **result})
    write(output / "classifications.json", classifications)
    counts = dict(Counter(row["classification"] for row in classifications))
    distinct = []
    for item in selected:
        rows = [row for row in classifications if row["mutant_id"] == item["id"]]
        case_counts = dict(Counter(row["classification"] for row in rows))
        if item["kind"] == "reserved": label = "reserved_unexecuted"
        elif case_counts.get("unexecuted"): label = "incomplete_evidence"
        elif case_counts.get("killed"): label = "killed_in_at_least_one_declared_case"
        elif case_counts.get("survived"): label = "survived_all_declared_cases"
        elif case_counts.get("invalid"): label = "invalid_source_consistent_frontends"
        else: label = "certified_equivalent_under_declared_assumptions"
        distinct.append({"mutant_id": item["id"], "kind": item["kind"], "summary": label, "case_counts": case_counts,
                         "killed_case_ids": [row["case_id"] for row in rows if row["classification"] == "killed"],
                         "surviving_case_ids": [row["case_id"] for row in rows if row["classification"] == "survived"]})
    baseline_checks = {case["id"]: {backend: all_results["baseline"][case["id"]].get(backend, {}).get("execution") == "completed"
                       and all_results["baseline"][case["id"]].get(backend, {}).get("observable") == originals[case["id"]]
                       for backend in BACKENDS} for case in selected_cases}
    baseline_ok = all(all(checks.values()) for checks in baseline_checks.values())
    changed = [name for name, pin in pins.items() if sha(ROOT / name) != pin]
    final_identities = identities()
    report = {"format": "spl-semantic-mutation-campaign/1", "phase": phase, "status": "partial" if not baseline_ok or changed or original_identities != final_identities or
              any(row["classification"] == "unexecuted" and row["stage"] != "reserved" for row in classifications) else "completed_with_reserved_unexecuted",
              "population": {"source_variants_including_baseline": len(sources), "mutants": len(selected), "cases": len(selected_cases), "mutant_case_pairs": len(classifications)},
              "classifications": counts, "classification_count_unit": "mutant_case_pair", "distinct_mutant_summaries": distinct,
              "baseline_prerequisite_satisfied": baseline_ok, "baseline_backend_checks": baseline_checks,
              "no_adequacy_percentage": True, "elapsed_seconds": round(time.monotonic() - started, 6),
              "backend_flags": {"required": list(BACKENDS), "effective_requested": list(backends)}, "process_limits": {"per_process_seconds": process_seconds,
              "campaign_seconds": total_seconds, "max_processes": max_processes, "max_bytes_per_stream": max_bytes},
              "processes_executed": len(proc.commands), "commands": proc.commands, "root": str(ROOT),
              "module_origins": {module.__name__: module.__file__ for module in (checker, evaluator, emitter, parser)},
              "initial_identities": original_identities, "final_identities": final_identities, "changed_sources": changed,
              "source_sha256": pins, "source_tree_sha256": hashlib.sha256(''.join(name+'\0'+pins[name]+'\n' for name in sorted(pins)).encode()).hexdigest(),
              "scope": "disclosed finite synthetic population; no global mutation adequacy, legal policy, bank payment or FX execution claim"}
    write(output / "report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--phase", choices=["initial", "strengthened"], default="initial")
    parser.add_argument("--mutant", action="append")
    parser.add_argument("--case", action="append")
    parser.add_argument("--backends", default=",".join(BACKENDS))
    parser.add_argument("--process-seconds", type=int, default=30)
    parser.add_argument("--total-seconds", type=int, default=300)
    parser.add_argument("--max-processes", type=int, default=224)
    parser.add_argument("--max-bytes", type=int, default=1048576)
    args = parser.parse_args(argv)
    report = run_campaign(args.output, phase=args.phase, mutant_ids=args.mutant, case_ids=args.case, backends=tuple(args.backends.split(",")),
                          process_seconds=args.process_seconds, total_seconds=args.total_seconds, max_processes=args.max_processes, max_bytes=args.max_bytes)
    print(json.dumps({key: report[key] for key in ("status", "population", "classifications", "processes_executed", "elapsed_seconds")}))
    return 0 if report["status"] == "completed_with_reserved_unexecuted" else 2


if __name__ == "__main__":
    raise SystemExit(main())
