"""Pinned Lean invocation helpers; no security policy or global PATH changes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from .codecs import DataError, fail

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / ".lake" / "build" / "lib" / "lean"
MODULES = ["SPL/Instant", "SPL/Calendar", "SPL/Dimensions", "SPL/Runtime", "SPL/Fold", "SPL/Syntax", "SPL/Parser", "SPL/Check", "SPL/Link", "SPL/IR", "SPL/Elaborate", "SPL/IRSource", "SPL/IRArtifact", "SPL/ValidateIR",
           "SPL/Series", "SPL/Bindings", "SPL/ContextProofs", "SPL/Emit", "SPL/Core", "SPL/Proofs", "SPL/ValidationProofs", "SPL/Trace", "SPL/Interpret", "SPL/Readable", "SPL"]


class FrontendDiagnostic(DataError):
    """A compiler diagnostic with its authored path, span and phase."""

    def __init__(self, code, message, *, source, span, stage):
        super().__init__(code, message, source, span)
        self.stage = stage

    def diagnostic(self):
        return {**super().diagnostic(), "stage": self.stage}


def lean_environment():
    env = os.environ.copy()
    choices = []
    if env.get("SPL_LEAN_BIN"):
        choices.append(Path(env["SPL_LEAN_BIN"]))
    elan = env.get("ELAN_HOME")
    if elan:
        choices.append(Path(elan) / "toolchains" / "leanprover--lean4---v4.35.0" / "bin")
    choices.append(Path("C:/Projects/Film_TV_participation_dynamic_DSL/environment/elan/toolchains/leanprover--lean4---v4.35.0/bin"))
    exe = next((x / "lean.exe" for x in choices if (x / "lean.exe").is_file()), None)
    if exe is None:
        candidate = shutil.which("lean")
        if candidate is None:
            fail("LEAN_NOT_FOUND", "Install the pinned lean-toolchain (see README.md)")
        exe = Path(candidate)
    env["PATH"] = str(exe.parent) + os.pathsep + env.get("PATH", "")
    env["LEAN_PATH"] = str(LIB) + os.pathsep + str(ROOT)
    return str(exe), env


def lean(args, timeout=180, *, search_paths=()):
    exe, env = lean_environment()
    if search_paths:
        env["LEAN_PATH"] = os.pathsep.join([*map(str, search_paths), env["LEAN_PATH"]])
    try:
        proc = subprocess.run([exe, *map(str, args)], cwd=ROOT, env=env,
                              text=True, encoding="utf-8", capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail("LEAN_RESOURCE_LIMIT", f"Lean invocation exceeded declared {timeout:g}-second limit")
    if proc.returncode:
        import json
        try:
            payload = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        if isinstance(payload, dict) and payload.get("status") == "blocked" and payload.get("diagnostics"):
            d = payload["diagnostics"][0]
            if isinstance(d.get("stage"), str) and d["stage"]:
                raise FrontendDiagnostic(d.get("code", "LEAN_FAILED"),
                                         d.get("message", "Native compilation failed"),
                                         source=d.get("source", ""), span=d.get("span"), stage=d["stage"])
            raise DataError(d.get("code", "LEAN_FAILED"), d.get("message", "Native compilation failed"),
                            d.get("source", ""), d.get("span"))
        fail("LEAN_FAILED", (proc.stdout + proc.stderr).strip() or f"Lean exited {proc.returncode}")
    return proc.stdout


def build_native():
    """Keep Lake's .olean package identities and native objects coherent.

    Direct lean -o into Lake's library directory changes imported C symbol names
    and breaks a later native link against Lake objects, even for the same source.
    """
    for module in MODULES:
        source = ROOT / (module + ".lean")
        if not source.exists():
            fail("COMPILER_INCOMPLETE", "Missing module " + str(source))
    executable, env = lean_environment()
    lake = Path(executable).with_name("lake.exe" if os.name == "nt" else "lake")
    process = subprocess.run([str(lake), "build", "SPL"], cwd=ROOT, env=env,
                             text=True, encoding="utf-8", capture_output=True, timeout=180)
    if process.returncode:
        fail("LEAN_FAILED", (process.stdout + process.stderr).strip())
    # The pinned Lake file also enables warningAsError. Retain the public
    # helper's explicit warning policy even if a caller adjusts Lake options;
    # these strict source checks deliberately have no -o/-i/-c output paths.
    for module in MODULES:
        lean(["-DwarningAsError=true", ROOT / (module + ".lean")])


def compile_schedule(source, output, *, link=None, series=False):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    command = "compile-series" if series else "compile"
    lean(["--run", ROOT / "SPL/Main.lean", command, source, output, *(["--link",link] if link else [])])
    return output


def preflight_schedule(source, *, link=None):
    """Run the native frontend through checked IR without emitting Lean."""
    from .codecs import loads
    return loads(lean(["--run", ROOT / "SPL/Main.lean", "check", source, *(["--link", link] if link else [])]))


def interpret_schedule(source, bindings, *, link=None):
    from .codecs import loads
    return loads(lean(["--run", ROOT / "SPL/Main.lean", "interpret", source, bindings, *(["--link",link] if link else [])]))


def export_ir(source, output, *, link=None):
    lean(["--run", ROOT / "SPL/Main.lean", "ir", source, output, *(["--link",link] if link else [])])
    from .codecs import read_json
    from .ir_artifacts import validate_ir_artifact
    validate_ir_artifact(read_json(output))
    return Path(output)
