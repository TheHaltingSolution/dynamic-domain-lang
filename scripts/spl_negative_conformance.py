"""Retain separate frontend, fabricated-IR and canonical rejection witnesses."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import read_json, write_json
from spl_compiler.lean_tools import lean, lean_environment
from spl_compiler.model import SPLException
from spl_compiler.modules import bind_module_package, run_module_package
from spl_compiler.parser import parse
from validation.rejection_cases import IR_DRIVER, frontend_cases


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_frontends(output, binary):
    results = []
    _, env = lean_environment()
    for case in frontend_cases():
        work = output / "frontend" / case["id"]
        work.mkdir(parents=True)
        source = work / "Source.spl"
        source.write_bytes(case["source"].encode("utf-8"))
        row = {**case, "status": "failed", "backends": {}}
        try:
            check_schedule(parse(case["source"], str(source)))
            row["backends"]["python_frontend"] = {"code": "accepted"}
        except SPLException as error:
            row["backends"]["python_frontend"] = error.to_dict()
        for command in ["check", "compile"]:
            target = work / "MustNotExist.lean"
            args = [str(binary), command, str(source), *([str(target)] if command == "compile" else [])]
            proc = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, timeout=60)
            (work / (command + ".stdout.json")).write_bytes(proc.stdout)
            (work / (command + ".stderr.log")).write_bytes(proc.stderr)
            response = json.loads(proc.stdout)
            diagnostic = response.get("diagnostics", [{"code": "accepted"}])[0]
            row["backends"]["native_" + command] = {"command": args, "exit_code": proc.returncode,
                "diagnostic": diagnostic, "emitted_artifact_exists": target.exists()}
        python = row["backends"]["python_frontend"]
        native = [row["backends"]["native_" + command] for command in ["check", "compile"]]
        row["status"] = "passed" if (python["code"] == case["expected_code"] and "span" in python
            and all(n["exit_code"] != 0 and n["diagnostic"]["code"] == case["expected_code"]
                    and "span" in n["diagnostic"] and not n["emitted_artifact_exists"] for n in native)) else "failed"
        write_json(work / "check.json", row)
        results.append(row)
    return results


def run_ir(output):
    source = output / "native-ir" / "Constructors.lean"
    source.parent.mkdir()
    source.write_bytes(IR_DRIVER.encode("utf-8"))
    payload = lean(["--run", source])
    (source.parent / "outcomes.json").write_text(payload, encoding="utf-8", newline="\n")
    rows = json.loads(payload)
    for row in rows:
        expected = "accepted" if row["id"] == "valid-control" else "INVALID_IR"
        expected_interpret = "calculated" if expected == "accepted" else expected
        row["status"] = "passed" if (row["validation"] == row["native_emitter"] == row["native_library_emitter"] == expected
            and row["native_interpretation"] == expected_interpret) else "failed"
        row["stage"] = "public_native_ir_boundary"
    return rows


def run_canonical(output):
    original = read_json(ROOT / "cases/modules/priority-rates/package.json")
    package = deepcopy(original)
    package["inputs"]["participant_b"] = "outside-participant"
    package = bind_module_package(package, ROOT)
    work = output / "canonical"
    write_json(work / "original-package.json", original)
    write_json(work / "mutated-package.json", package)
    result = run_module_package(package, ROOT, backend="compare", artifact_dir=work)
    return {"id": "cedar-participant-outside-scope", "stage": "canonical_validation",
            "status": "passed" if result["status"] == "blocked" and result["diagnostics"][0]["code"] == "MODULE_REFERENCE_SCOPE"
                and not result["statements"] and not result["closing_state"] and not result["results"] else "failed",
            "diagnostics": result["diagnostics"], "calculation_backends": "not_executed_precalculation_rejection"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    binary = ROOT / ".lake/build/bin" / ("spl.exe" if sys.platform == "win32" else "spl")
    if not binary.is_file():
        parser.error("Run the pinned lake build before this command")
    args.output.mkdir(parents=True, exist_ok=False)
    paths = [*sorted((ROOT / "SPL").glob("*.lean")), *sorted((ROOT / "spl_compiler").glob("*.py")),
             *sorted((ROOT / "schemas").glob("*.json")), ROOT / "SPL.lean", ROOT / "lean-toolchain", ROOT / "lakefile.toml",
             Path(__file__).resolve(), ROOT / "validation/rejection_cases.py", *sorted((ROOT / "cases/modules/priority-rates").glob("*"))]
    paths = [p for p in paths if p.is_file()]
    pins = {p.relative_to(ROOT).as_posix(): fingerprint(p) for p in paths}
    binary_pin = fingerprint(binary)
    for path in paths:
        target = args.output / "source-freeze" / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    started = time.perf_counter()
    rows, stage, stage_error = [], "frontend", {}
    try:
        rows.extend(run_frontends(args.output, binary))
        stage = "native_ir"
        rows.extend(run_ir(args.output))
        stage = "canonical"
        rows.append(run_canonical(args.output))
    except Exception as error:
        stage_error = {"stage": stage, "type": type(error).__name__, "message": str(error)}
        if hasattr(error, "diagnostic"):
            stage_error["diagnostic"] = error.diagnostic()
    changed = [name for name, digest in pins.items() if fingerprint(ROOT / name) != digest]
    if fingerprint(binary) != binary_pin:
        changed.append("native_frontend_executable")
    result = {"format": "spl-negative-conformance/1", "status": "passed" if not stage_error and not changed and len(rows) == 8 and all(r["status"] == "passed" for r in rows) else "failed",
              "source_pins": pins, "changed_sources": changed, "native_frontend_sha256": binary_pin,
              "checks": rows, "stage_error": stage_error, "elapsed_seconds": f"{time.perf_counter()-started:.6f}",
              "limits": ["Finite selected mutations, not exhaustive malformed programs or all diagnostics.",
                         "Fabricated IR uses public Lean constructors; no exported-IR-JSON execution is claimed.",
                         "Canonical out-of-scope rejection supplies no native settlement execution credit."]}
    write_json(args.output / "summary.json", result)
    print(json.dumps({"status": result["status"], "checks": len(rows), "output": str(args.output)}))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
