"""Build and run the full regression in a fresh, immutable Git checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import unittest


BACKEND_OVERRIDES = (
    "QUEST_REFERENCE_ONLY", "SPL_QUANTITIES_REFERENCE_ONLY",
    "SPL_REVISION_REFERENCE_ONLY", "SPL_M1_BACKEND", "SPL_WATERFALL_BACKEND",
)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, data):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def capture(*command):
    return subprocess.check_output(command, encoding="utf-8").strip()


def source_pins(root):
    names = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    return {name: sha256(root / name) for name in names if name}


def build_pins(root):
    build = root / ".lake" / "build"
    paths = list((build / "bin").glob("*"))
    for directory in (build / "lib" / "lean", build / "ir"):
        paths.extend(path for path in directory.rglob("*")
                     if path.name.endswith((".olean", ".o", ".o.export", ".o.noexport", ".obj", ".a", ".rsp")))
    return {p.relative_to(root).as_posix(): sha256(p) for p in sorted(set(paths)) if p.is_file()}


def module_origins(root, foreign_roots):
    project_packages = {"spl_compiler", "cases", "oracles", "Tests", "scripts"}
    origins = {}
    for name, module in list(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename is None or module is sys.modules["__main__"]:
            continue
        path = Path(filename).resolve()
        project_name = name.split(".")[0] in project_packages or name.startswith("test_")
        if any(path.is_relative_to(other) for other in foreign_roots) or (
            project_name and not path.is_relative_to(root)
        ):
            raise RuntimeError(f"Cross-checkout import {name}: {path}")
        if path.is_relative_to(root):
            origins[name] = str(path)
    return origins


def test_cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from test_cases(item)
        else:
            yield item


def reject_unless(condition, message):
    if not condition:
        raise RuntimeError(message)


def summarize(out, directories):
    """Require each selector exactly once across isolated receipts of one commit."""
    receipts = [(p, json.loads((p / "verification.json").read_text(encoding="utf-8")))
                for p in directories]
    first_dir, first = receipts[0]
    shards = first["shards"]
    reject_unless(sorted(r["shard_index"] for _, r in receipts) == list(range(shards)),
                  "Expected one receipt for each shard")
    expected = json.loads((first_dir / "test-selectors.json").read_text(encoding="utf-8"))
    source = (first_dir / "source-before.json").read_bytes()
    fields = ("commit", "tree", "shards", "identities", "lean_version", "python_sha256", "toolchain")
    details = []
    for directory, receipt in receipts:
        reject_unless(receipt["status"] == "passed", f"Shard failed: {directory}")
        reject_unless(all(receipt[key] == first[key] for key in fields), f"Shard identity mismatch: {directory}")
        reject_unless((directory / "source-before.json").read_bytes() == source,
                      f"Shard source mismatch: {directory}")
        discovered = json.loads((directory / "test-selectors.json").read_text(encoding="utf-8"))
        selected = json.loads((directory / "shard-selectors.json").read_text(encoding="utf-8"))
        reject_unless(discovered == expected and selected == expected[receipt["shard_index"]::shards]
                      and receipt["tests"]["run"] == len(selected), f"Shard selection mismatch: {directory}")
        details.append({"directory": str(directory.resolve()), "index": receipt["shard_index"],
                        "tests": receipt["tests"], "test_seconds": receipt["test_seconds"],
                        "receipt_sha256": sha256(directory / "verification.json")})
    reject_unless(len({r["checkout"] for _, r in receipts}) == shards,
                  "Each shard needs its own clean checkout and registry")
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "verification.json", {
        **{key: first[key] for key in fields}, "status": "passed", "methods": len(expected),
        "shard_receipts": sorted(details, key=lambda row: row["index"]),
    })


def run(args):
    root, out, lean_bin = (path.resolve() for path in (args.checkout, args.output, args.lean_bin))
    reject_unless(not out.is_relative_to(root), "Evidence must be outside the frozen checkout")
    out.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    state = {
        "status": "running", "stage": "initialize", "checkout": str(root),
        "commit": args.commit, "pid": os.getpid(), "started_unix": time.time(),
        "python": sys.executable, "python_sha256": sha256(Path(sys.executable)),
        "runner_sha256": sha256(Path(__file__).resolve()), "commands": [],
        "shards": args.shards, "shard_index": args.shard_index,
    }

    def progress(**fields):
        state.update(fields, elapsed_seconds=time.perf_counter() - started)
        write_json(out / "progress.json", state)

    def command(label, argv):
        progress(stage=label)
        stamp = time.perf_counter()
        with (out / (label + ".log")).open("w", encoding="utf-8") as log:
            result = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        state["commands"].append({"label": label, "argv": argv, "returncode": result.returncode,
                                  "seconds": time.perf_counter() - stamp})
        progress()
        result.check_returncode()

    try:
        progress()
        os.chdir(root)
        checkout_roots = {
            Path(line.removeprefix("worktree ")).resolve()
            for line in capture("git", "worktree", "list", "--porcelain").splitlines()
            if line.startswith("worktree ")
        }
        foreign_roots = checkout_roots - {root}
        rejected_roots = checkout_roots | {Path(__file__).resolve().parent}
        sys.path[:] = [str(root)] + [
            entry for entry in sys.path
            if not any(Path(entry or root).resolve().is_relative_to(p) for p in rejected_roots)
        ]
        state["sys_path"] = sys.path[:]
        reject_unless(capture("git", "rev-parse", "HEAD") == args.commit, "Unexpected commit")
        reject_unless(capture("git", "status", "--porcelain") == "", "Checkout has local files or changes")
        reject_unless(not (root / ".lake").exists(), "Use a fresh checkout with no .lake directory")
        state["tree"] = capture("git", "rev-parse", "HEAD^{tree}")
        archive = out / "source.zip"
        subprocess.run(["git", "archive", "--format=zip", "-o", str(archive), args.commit], check=True)
        state["archive_sha256"] = sha256(archive)
        sources = source_pins(root)
        write_json(out / "source-before.json", sources)
        state["source_count"] = len(sources)
        os.environ["SPL_LEAN_BIN"] = str(lean_bin)
        suffix = ".exe" if os.name == "nt" else ""
        os.environ["SPL_LEAN"] = str(lean_bin / ("lean" + suffix))
        state["removed_backend_overrides"] = {
            name: os.environ.pop(name) for name in BACKEND_OVERRIDES if name in os.environ
        }

        from spl_compiler.lean_tools import LIB, ROOT, lean_environment
        from spl_compiler.modules import module_identities
        from spl_compiler.run import identities

        lean, lean_env = lean_environment()
        lake = lean_bin / ("lake" + suffix)
        reject_unless(Path(lean).resolve() == Path(os.environ["SPL_LEAN"]),
                      f"Wrong Lean executable: {lean}")
        reject_unless(ROOT == root and LIB == root / ".lake/build/lib/lean", "Wrong Lean import root")
        reject_unless(lean_env["LEAN_PATH"].split(os.pathsep) == [str(LIB), str(root)],
                      "Wrong LEAN_PATH")
        os.environ.update(lean_env)
        state["lean_path"] = os.environ["LEAN_PATH"]
        state["lean_version"] = capture(lean, "--version")
        expected_version = (root / "lean-toolchain").read_text().strip().split(":v")[-1]
        reject_unless(f"version {expected_version}," in state["lean_version"], "Wrong Lean version")
        state["toolchain"] = {str(path): sha256(path) for path in (Path(lean), lake)}
        state["identities"] = {"canonical": identities(), "module": module_identities()}
        write_json(out / "origins-initial.json", module_origins(root, foreign_roots))

        command("build-default", [str(lake), "build"])
        command("build-indexed", [str(lake), "build", "spl_sv_indexed"])
        command("smoke", [str(lake), "exe", "smoke"])
        command("spl-smoke", [str(lake), "exe", "spl_smoke"])
        builds = build_pins(root)
        write_json(out / "build-before.json", builds)
        state["build_count"] = len(builds)
        reject_unless(bool(builds), "Missing Lake build artifacts")

        progress(stage="discovery")
        loader = unittest.TestLoader()
        suite = loader.discover(str(root / "Tests"), pattern="test_*.py")
        cases = list(test_cases(suite))
        discovered = [case.id() for case in cases]
        chosen = cases[args.shard_index::args.shards]
        write_json(out / "test-selectors.json", discovered)
        write_json(out / "shard-selectors.json", [case.id() for case in chosen])
        state["discovered"] = len(discovered)
        state["selected"] = len(chosen)
        reject_unless(not loader.errors, "\n".join(loader.errors))
        reject_unless(bool(chosen) and len(set(discovered)) == len(discovered), "Empty or duplicate test selectors")
        write_json(out / "origins-discovery.json", module_origins(root, foreign_roots))

        class ProgressResult(unittest.TextTestResult):
            def startTest(self, test):
                super().startTest(test)
                progress(current_test=test.id(), tests_started=self.testsRun)

            def stopTest(self, test):
                super().stopTest(test)
                progress(tests_completed=self.testsRun, errors=len(self.errors),
                         failures=len(self.failures), skips=len(self.skipped))

        progress(stage="regression")
        stamp = time.perf_counter()
        with (out / "tests.log").open("w", encoding="utf-8", buffering=1) as log:
            runner = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=ProgressResult)
            result = runner.run(suite if args.shards == 1 else unittest.TestSuite(chosen))
        state["test_seconds"] = time.perf_counter() - stamp
        outcomes = {name: [(test.id(), detail) for test, detail in getattr(result, name)]
                    for name in ("errors", "failures", "skipped", "expectedFailures")}
        outcomes["unexpectedSuccesses"] = [test.id() for test in result.unexpectedSuccesses]
        write_json(out / "test-outcomes.json", outcomes)
        state["tests"] = {"run": result.testsRun, **{name: len(rows) for name, rows in outcomes.items()}}

        progress(stage="final-audit")
        final_sources, final_builds = source_pins(root), build_pins(root)
        write_json(out / "source-after.json", final_sources)
        write_json(out / "build-after.json", final_builds)
        write_json(out / "origins-final.json", module_origins(root, foreign_roots))
        state["source_drift"] = sorted(p for p in sources.keys() | final_sources.keys()
                                       if sources.get(p) != final_sources.get(p))
        state["compiled_drift"] = sorted(p for p in builds.keys() | final_builds.keys()
                                         if builds.get(p) != final_builds.get(p))
        state["git_status_after"] = capture("git", "status", "--porcelain")
        reject_unless(not state["source_drift"] and not state["compiled_drift"] and not state["git_status_after"],
                      "Frozen checkout or compiled artifacts drifted")
        reject_unless(state["identities"] == {"canonical": identities(), "module": module_identities()},
                      "Compiler identities drifted")
        state["status"] = "passed" if (
            result.testsRun == len(chosen) and result.wasSuccessful() and not any(outcomes.values())
        ) else "failed"
        state["stage"] = "complete"
    except BaseException:
        state.update(status="failed", exception=traceback.format_exc())
    finally:
        progress()
        write_json(out / "verification.json", state)
    return 0 if state["status"] == "passed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path)
    parser.add_argument("--commit", help="Full Git commit hash")
    parser.add_argument("--lean-bin", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="New external evidence directory")
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0, help="Zero-based index")
    parser.add_argument("--summarize", nargs="+", type=Path, metavar="EVIDENCE_DIRECTORY")
    args = parser.parse_args()
    if args.summarize:
        summarize(args.output, args.summarize)
    else:
        if not (args.checkout and args.commit and args.lean_bin and 0 <= args.shard_index < args.shards):
            parser.error("A run needs --checkout, --commit, --lean-bin and a valid shard index")
        sys.exit(run(args))
