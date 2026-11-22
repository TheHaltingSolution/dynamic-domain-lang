"""Pinned Lean invocation helpers; no security policy or global PATH changes."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from .codecs import fail

ROOT = Path(__file__).resolve().parent.parent
LIB = ROOT / ".lake" / "build" / "lib" / "lean"
MODULES = ["SPL/Instant", "SPL/Calendar", "SPL/Runtime", "SPL/Fold", "SPL/Syntax", "SPL/Parser", "SPL/Check", "SPL/Link", "SPL/IR", "SPL/Elaborate", "SPL/ValidateIR",
           "SPL/Bindings", "SPL/Emit", "SPL/Core", "SPL/Proofs", "SPL/Trace", "SPL/Interpret", "SPL/Readable", "SPL"]


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


def lean(args, timeout=180):
    exe, env = lean_environment()
    try:
        proc = subprocess.run([exe, *map(str, args)], cwd=ROOT, env=env,
                              text=True, encoding="utf-8", capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail("LEAN_RESOURCE_LIMIT", "Lean invocation exceeded declared 180-second limit")
    if proc.returncode:
        import json
        try:
            payload = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            payload = {}
        if isinstance(payload, dict) and payload.get("status") == "blocked" and payload.get("diagnostics"):
            from .codecs import DataError
            d = payload["diagnostics"][0]
            raise DataError(d.get("code", "LEAN_FAILED"), d.get("message", "Native compilation failed"),
                            d.get("source", ""), d.get("span"))
        fail("LEAN_FAILED", (proc.stdout + proc.stderr).strip() or f"Lean exited {proc.returncode}")
    return proc.stdout


def build_native():
    """Direct checking fallback; normal CI additionally uses lake build/exe smoke."""
    for module in MODULES:
        source = ROOT / (module + ".lean")
        target = LIB / (module + ".olean")
        if not source.exists():
            fail("COMPILER_INCOMPLETE", "Missing module " + str(source))
        target.parent.mkdir(parents=True, exist_ok=True)
        lean(["-DwarningAsError=true", "-o", target, source])


def compile_schedule(source, output, *, link=None):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    lean(["--run", ROOT / "SPL/Main.lean", "compile", source, output, *(["--link",link] if link else [])])
    return output


def interpret_schedule(source, bindings, *, link=None):
    from .codecs import loads
    return loads(lean(["--run", ROOT / "SPL/Main.lean", "interpret", source, bindings, *(["--link",link] if link else [])]))


def export_ir(source, output, *, link=None):
    lean(["--run", ROOT / "SPL/Main.lean", "ir", source, output, *(["--link",link] if link else [])])
    return Path(output)
