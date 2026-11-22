"""Reproducible CLI; `compile` always invokes the native Lean frontend."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .adapter import rq07
from .codecs import DataError, read_json, write_json
from .fixtures import lg_package, sv_package
from .lean_tools import ROOT, build_native, lean
from .run import bind_package, run_package


def main():
    parser = argparse.ArgumentParser(prog="python -m spl_compiler")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build-native", help="Check native modules with pinned Lean (Lake remains the normal build)")
    for action in ["check", "compile"]:
        p = commands.add_parser(action)
        p.add_argument("schedule")
        if action == "compile":
            p.add_argument("output")
    p = commands.add_parser("fixture")
    p.add_argument("case", choices=["sv", "lg"])
    p.add_argument("output")
    p = commands.add_parser("adapt-rq07")
    p.add_argument("source")
    p.add_argument("output")
    p.add_argument("--observed-at", required=True, help="Explicit synthetic observation policy; never inferred from funding dates")
    p.add_argument("--ingested-at", required=True)
    p = commands.add_parser("run")
    p.add_argument("schedule")
    p.add_argument("package")
    p.add_argument("--output", required=True, help="Review bundle directory (immutable run identity recommended)")
    p.add_argument("--backend", choices=["compare", "lean", "reference"], default="compare")
    p = commands.add_parser("mechanism")
    p.add_argument("case", choices=["advance-issues", "reserve-vintage", "correction-payments"])
    p.add_argument("bindings")
    p.add_argument("--output", required=True)
    p = commands.add_parser("module-bind", help="Deliberately pin a registered module run before execution")
    p.add_argument("package")
    p.add_argument("output")
    p.add_argument("--registry", default=str(ROOT))
    p = commands.add_parser("module-run", help="Validate and execute an already pinned module package")
    p.add_argument("package")
    p.add_argument("--registry", default=str(ROOT))
    p.add_argument("--output", required=True)
    p.add_argument("--backend", choices=["compare", "lean", "reference"], default="compare")
    args = parser.parse_args()
    try:
        if args.command == "build-native":
            build_native()
            print("Native Lean modules and scoped proof checked.")
        elif args.command in {"check", "compile"}:
            tail = [args.schedule] + ([args.output] if args.command == "compile" else [])
            print(lean(["--run", ROOT / "SPL/Main.lean", args.command, *tail]).strip())
        elif args.command == "fixture":
            kind = args.case
            path = ROOT / ("cases/sv/sv01.spl" if kind == "sv" else "cases/lg/lg01.spl")
            write_json(args.output, bind_package(sv_package() if kind == "sv" else lg_package(), path))
            print("Wrote pinned synthetic package " + args.output)
        elif args.command == "adapt-rq07":
            p = rq07(args.source, observed_at=args.observed_at, ingested_at=args.ingested_at)
            p = bind_package(p, ROOT / "cases/sv/rq07.spl")
            from .schema import validate_package
            validate_package(p)
            write_json(args.output, p)
            print("Wrote validated canonical RQ-07 package " + args.output)
        elif args.command == "mechanism":
            from .mechanisms import run_mechanism
            result = run_mechanism(args.case, read_json(args.bindings), artifact_dir=args.output)
            print(json.dumps({k: result[k] for k in ["status", "emissions", "closing", "diagnostics"]}, indent=2))
            return 1 if result["status"] == "blocked" else 0
        elif args.command == "module-bind":
            from .modules import bind_module_package
            write_json(args.output, bind_module_package(read_json(args.package), args.registry))
            print("Wrote pinned module package " + args.output)
        elif args.command == "module-run":
            from .modules import run_module_package
            result = run_module_package(read_json(args.package), args.registry, backend=args.backend, artifact_dir=args.output)
            print(json.dumps({key: result[key] for key in ["status", "statements", "diagnostics"]}, indent=2))
            return 1 if result["status"] == "blocked" else 0
        else:
            result = run_package(read_json(args.package), args.schedule, backend=args.backend, artifact_dir=args.output)
            write_json(Path(args.output) / "result.json", result)
            print(json.dumps({"status": result["status"], "statements": result["statements"], "diagnostics": result["diagnostics"]}, indent=2))
            return 1 if result["status"] == "blocked" else 0
        return 0
    except (DataError, OSError) as exc:
        diagnostic = exc.diagnostic() if isinstance(exc, DataError) else {"code": "IO_ERROR", "message": str(exc)}
        print(json.dumps({"status": "blocked", "diagnostics": [diagnostic]}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
