"""Generic opt-in native audit preparation and separately bounded calculation.

No contract dispatch: every emitted target comes from the Program captured by
the generic native audit driver. Compilation has an explicit compiler-only
1GiB/180s profile; runtime/reference/readers keep 256MiB/60s limits.
"""
from pathlib import Path
import json
import os
import shutil
import sys

from .bounded_process import run_process
from .codecs import canonical, digest, exact, fail, file_digest, number, write_json
from .lean_tools import ROOT, lean_environment
from .model import encode_value
from .native_trace import NativeLimits, read_compact
from .trace_transport import Limits, loads

RUNTIME_BYTES = 256 * 1024 * 1024
COMPILER_BYTES = 1024 * 1024 * 1024
OUTPUT_BYTES = 64 * 1024 * 1024
WORKER = ROOT / "scripts/spl_audit_worker.py"


def require_profile(profile, backend, destination):
    if profile not in {"array-v1", "compact-v2"}:
        raise ValueError("UNSUPPORTED_AUDIT_PROFILE")
    if profile == "compact-v2" and (destination is None or backend not in {"compare", "lean"}):
        raise ValueError("COMPACT_AUDIT_REQUIRES_NATIVE_PUBLICATION")


def metadata(path, maximum=OUTPUT_BYTES):
    with Path(path).open("rb") as stream:
        raw = stream.read(maximum + 1)
    if len(raw) > maximum:
        fail("AUDIT_RESOURCE_LIMIT", "Worker metadata byte limit")
    return loads(raw, Limits(max_input_bytes=maximum))


def checked_head(raw, checked):
    """Decode by actual checked output types; user record keys remain data."""
    from .modules import _decode_output
    result = dict(raw)
    for field, kind in (("emissions", "emit"), ("closing", "closing")):
        types = {declaration["name"]: declaration["expr"]["_type"]
                 for declaration in checked.schedule["declarations"] if declaration["kind"] == kind}
        values = raw[field]
        if raw["status"] != "blocked" and values.keys() != types.keys():
            fail("AUDIT_OUTPUT_PORTS", field)
        result[field] = {name: encode_value(_decode_output(value, types[name], checked.meanings))
                         for name, value in values.items()}
    return result


def _stage(command, folder, *, compiler=False):
    _, env = lean_environment()
    report = run_process(command, folder, env=env, timeout=180 if compiler else 60,
                         max_output_bytes=OUTPUT_BYTES,
                         max_working_set_bytes=COMPILER_BYTES if compiler else RUNTIME_BYTES)
    report["profile"] = "compiler1g180" if compiler else "runtime256"
    write_json(Path(folder) / "process.json", report)
    if report["status"] != "passed":
        resource = any(report[key] for key in ("timed_out", "output_budget_exceeded", "working_set_budget_exceeded"))
        fail("AUDIT_RESOURCE_LIMIT" if resource else "AUDIT_STAGE_FAILED", Path(folder).name)
    return Path(folder) / "stdout.bin"


def _compiler_inputs():
    executable, _ = lean_environment()
    toolbin = Path(executable).parent
    trace = ROOT / ".lake/build/ir/SPL/AuditMain.c.o.noexport.trace"
    data = metadata(trace)
    commands = [row["message"][3:].split() for row in data["log"]
                if row.get("level") == "trace" and row.get("message", "").startswith(".> ")]
    if len(commands) != 1:
        fail("AUDIT_COMPILER_CONFIGURATION", "Expected one pinned Lake C command")
    command = commands[0]
    if (len(command) < 7 or any('"' in arg or "'" in arg for arg in command) or
            Path(command[0]).resolve() != (toolbin / "clang.exe").resolve() or
            command[1:3] != ["-c", "-o"] or
            Path(command[4]).resolve() != (ROOT / ".lake/build/ir/SPL/AuditMain.c").resolve()):
        fail("AUDIT_COMPILER_CONFIGURATION", "Unsupported Lake C command shape")
    flags = command[5:]
    response = ROOT / ".lake/build/bin/spl_audit.exe.rsp"
    link = [json.loads(line) for line in response.read_text(encoding="utf-8").splitlines() if line.strip()]
    if Path(link[0]).resolve() != (ROOT / ".lake/build/ir/SPL/AuditMain.c.o.noexport").resolve():
        fail("AUDIT_COMPILER_CONFIGURATION", "Unexpected generic driver anchor")
    files = set(sorted((ROOT / "SPL").glob("*.lean")) + sorted((ROOT / "spl_compiler").glob("*.py")))
    files.update([ROOT / "lean-toolchain", ROOT / "lakefile.toml", ROOT / "SPL.lean", trace, response,
                  Path(executable), toolbin / "clang.exe", ROOT / ".lake/build/bin/spl_audit.exe"])
    # Imported .olean and native link objects must match the same Lake context.
    files.update((ROOT / ".lake/build/lib/lean/SPL").glob("*.olean"))
    files.update(path for arg in link[1:] if (path := Path(arg)).is_absolute() and path.is_file())
    files.update(toolbin.glob("*.dll"))
    files.update((toolbin.parent / "include").rglob("*.h"))
    for pattern in ("*.olean", "*.a", "*.lib", "*.dll"):
        files.update((toolbin.parent / "lib").rglob(pattern))
    pins = {str(path.resolve()): file_digest(path) for path in sorted(files)}
    return toolbin, flags, link[1:], pins


def _verify_pins(pins):
    if any(not Path(path).is_file() or file_digest(path) != expected for path, expected in pins.items()):
        fail("AUDIT_DEPENDENCY_CHANGED", "Compiler/build closure changed")


def compiled_target(work):
    """Compile this exact emitted program, using a full pinned cache key."""
    work = Path(work)
    toolbin, flags, libraries, pins = _compiler_inputs()
    emitted = work / "Settlement.lean"
    key_data = {"format": "spl-native-target-cache/1", "emitted_sha256": file_digest(emitted),
                "typed_ir_sha256": file_digest(work / "typed-ir.json"), "pins": pins,
                "source_sha256": file_digest(work / "consumed.source.spl"),
                "link_sha256": file_digest(work / "consumed.link.json") if (work / "consumed.link.json").exists() else None,
                "c_flags": flags, "link_arguments": libraries, "lean_flags": ["-DwarningAsError=true", "-R", "PRIVATE", "-c"]}
    key = digest(key_data)
    cache = ROOT / ".lake/compact-native" / key
    manifest = cache / "cache.json"
    if cache.exists() and (cache.resolve() != cache or cache.is_symlink()):
        fail("AUDIT_CACHE_MISMATCH", "Cache ownership changed")
    if manifest.is_file():
        recorded = metadata(manifest)
        outputs = {"Candidate.lean", "Candidate.c", "Candidate.o", "Candidate.exe", "link.rsp"}
        if (type(recorded) is not dict or set(recorded) != {"inputs", "outputs"} or
                recorded["inputs"] != key_data or type(recorded["outputs"]) is not dict or
                set(recorded["outputs"]) != outputs):
            fail("AUDIT_CACHE_MISMATCH", "Cache input closure differs")
        for name, expected in recorded["outputs"].items():
            if ((cache / name).is_symlink() or (cache / name).resolve().parent != cache or
                    file_digest(cache / name) != expected):
                fail("AUDIT_CACHE_MISMATCH", name)
    else:
        # Exclusive creation: another writer cannot replace a cache being used.
        cache.mkdir(parents=True, exist_ok=False)
        source, cfile, obj, target = (cache / name for name in ("Candidate.lean", "Candidate.c", "Candidate.o", "Candidate.exe"))
        source.write_bytes(emitted.read_bytes())
        response = cache / "link.rsp"
        response.write_text("\n".join(json.dumps(arg) for arg in [str(obj), *libraries]), encoding="utf-8")
        commands = [("lean-codegen", [toolbin / "lean.exe", "-DwarningAsError=true", "-R", cache, "-c", cfile, source]),
                    ("c-object", [toolbin / "clang.exe", "-c", "-o", obj, cfile, *flags]),
                    ("link", [toolbin / "clang.exe", "-o", target, "@" + str(response)])]
        for name, command in commands:
            _stage(command, work / ("compile-" + name), compiler=True)
        _verify_pins(pins)
        write_json(manifest, {"inputs": key_data, "outputs": {path.name: file_digest(path)
                    for path in (source, cfile, obj, target, response)}})
    _verify_pins(pins)
    archived_target = work / "Settlement.exe"
    shutil.copyfile(cache / "Candidate.exe", archived_target)
    write_json(work / "native-build.json", metadata(manifest))
    # Execute immutable cache bytes; the invocation-owned identical copy is
    # never image-mapped. Windows can retain an executed image's write lock
    # briefly after exit, which prevents the publication fsync/open(rb+) step.
    return cache / "Candidate.exe"


def execute_compact(source, work, checked, *, link=None):
    """Return exact typed financial head only after all audit/native/reference gates."""
    work = Path(work)
    consumed = work / "consumed.source.spl"
    consumed.write_bytes(Path(source).read_bytes())
    source_pin = file_digest(consumed)
    link_args = []
    if link:
        consumed_link = work / "consumed.link.json"
        consumed_link.write_bytes(Path(link).read_bytes())
        link_args = ["--link", consumed_link]
    # This single native call produces IR, emitted calculation and audit from
    # one checked Program; all exact consumed inputs are invocation-owned.
    output = _stage([ROOT / ".lake/build/bin/spl_audit.exe", consumed, work / "bindings.json",
                     work / "typed-ir.json", work / "Settlement.lean", *link_args], work / "audit-process")
    shutil.copyfile(output, work / "audit.native.jsonl")
    summary_path = _stage([sys.executable, WORKER, "validate", work / "audit.native.jsonl"], work / "audit-validation")
    summary = metadata(summary_path)
    head = checked_head(summary["head"], checked)
    target = compiled_target(work)
    target_pin = file_digest(target)
    if target_pin != file_digest(work / "Settlement.exe"):
        fail("AUDIT_DEPENDENCY_CHANGED", "Archived native target differs")
    native_path = _stage([target, work / "bindings.json"], work / "target-process")
    native = checked_head(metadata(native_path), checked)
    if file_digest(target) != target_pin:
        fail("AUDIT_DEPENDENCY_CHANGED", "Executed native target changed")
    source_name = checked.schedule["span"]["source"]
    reference_args = [sys.executable, WORKER, "reference", consumed, work / "bindings.json", source_name, *link_args]
    reference = metadata(_stage(reference_args, work / "reference-process"))
    for other in (head, reference):
        for field in ("status", "emissions", "closing"):
            if canonical(native[field]) != canonical(other[field]):
                fail("AUDIT_DIFFERENTIAL_MISMATCH", field)
        if [d["code"] for d in native["diagnostics"]] != [d["code"] for d in other["diagnostics"]]:
            fail("AUDIT_DIFFERENTIAL_MISMATCH", "diagnostics")
    if file_digest(consumed) != source_pin:
        fail("AUDIT_DEPENDENCY_CHANGED", "Private consumed source changed")
    pins = {"source_sha256": source_pin, "bindings_sha256": file_digest(work / "bindings.json"),
            "typed_ir_sha256": file_digest(work / "typed-ir.json"), "emitted_sha256": file_digest(work / "Settlement.lean"),
            "target_sha256": file_digest(target), "build_sha256": file_digest(work / "native-build.json")}
    if link:
        pins["link_sha256"] = file_digest(work / "consumed.link.json")
    # The reference adds an explanation and any authored span after all three
    # paths have agreed the failure codes. The native graph stays unchanged.
    return {**native, "diagnostics": reference["diagnostics"]}, pins, summary
