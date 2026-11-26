"""Comparative SPL compilation certificates, independent of the pilot allowlist."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile

from .artifacts import ArtifactPublication, PublicationError
from .certification import _runtime_identity
from .codecs import DataError, digest, fail, file_digest, loads, read_json, write_json
from .lean_tools import compile_schedule, export_ir, lean
from .source_verification import check_native_ir, check_source
from .target_verification import check_target


FORMAT = "spl-comparative-certificate/1"
MAX_BYTES = 64 * 1024 * 1024


def _read(path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        fail("VERIFICATION_RESOURCE_LIMIT", f"File exceeds verification limit: {path}")
    return data


def _prepare(work, source, link):
    authored = work / "consumed.source.spl"
    authored.write_bytes(_read(source))
    manifest = None
    if link is not None:
        manifest = work / "consumed.link.json"
        manifest.write_bytes(_read(link))
    return authored, manifest


def _check(work, source, link, *, mode, expected=None):
    if mode not in ("single", "series"):
        fail("VERIFICATION_MODE", "Choose single or series settlement")
    runtime = _runtime_identity()
    checked = check_source(source, link=link)
    typed = work / "typed-ir.json"
    export_ir(source, typed, link=link)
    witness = check_native_ir(checked, read_json(typed))
    artifact = work / "Settlement.lean"
    compile_schedule(source, artifact, link=link, series=(mode == "series"))
    pins = {path.name: file_digest(path) for path in (source, typed, artifact)}
    if link is not None:
        pins[link.name] = file_digest(link)
    if expected is not None:
        if pins != expected.get("files") or runtime != expected.get("lean_runtime_sha256"):
            fail("VERIFICATION_IDENTITY_MISMATCH", "Source, linked inputs, emitted artifact or Lean runtime changed")
    proof = check_target(work / "proof", artifact, checked, mode=mode)
    if _runtime_identity() != runtime:
        fail("VERIFICATION_RUNTIME_CHANGED", "Lean runtime changed during the check")
    receipt = {"format": FORMAT, "mode": mode, "files": pins, "lean_runtime_sha256": runtime,
               "source_witness": witness, "target_proof": proof}
    if expected is not None and receipt != expected:
        fail("VERIFICATION_CERTIFICATE_MISMATCH", "Fresh proof evidence differs from the certificate")
    return receipt


def certify(source, bundle, *, link=None, mode="single"):
    """Write a new bundle only after independent checks and kernel proof succeed."""
    with tempfile.TemporaryDirectory(prefix="spl-verification-") as directory:
        work = Path(directory)
        authored, manifest = _prepare(work, source, link)
        receipt = _check(work, authored, manifest, mode=mode)
        bundle = Path(bundle)
        bundle.mkdir(parents=True)
        for name in receipt["files"]:
            (bundle / name).write_bytes(_read(work / name))
        # The receipt is written last. Partial bundles cannot verify.
        write_json(bundle / "certificate.json", receipt)
        return receipt


def _verify(work, bundle):
    bundle = Path(bundle)
    certificate = loads(_read(bundle / "certificate.json"))
    if type(certificate) is not dict or certificate.get("format") != FORMAT:
        fail("VERIFICATION_CERTIFICATE_FORMAT", "Expected a comparative SPL certificate")
    names = {"consumed.source.spl", "typed-ir.json", "Settlement.lean"}
    files = certificate.get("files")
    if type(files) is not dict or set(files) not in (names, names | {"consumed.link.json"}):
        fail("VERIFICATION_CERTIFICATE_FORMAT", "Certificate has an invalid artifact inventory")
    retained = {}
    for name in files:
        payload = _read(bundle / name)
        if sha256(payload).hexdigest() != files[name]:
            fail("VERIFICATION_IDENTITY_MISMATCH", f"Bundle file changed: {name}")
        if name.startswith("consumed."):
            path = work / name
            path.write_bytes(payload)
            retained[name] = path
    source = retained["consumed.source.spl"]
    manifest = retained.get("consumed.link.json")
    return _check(work, source, manifest, mode=certificate.get("mode"), expected=certificate)


def verify(bundle):
    with tempfile.TemporaryDirectory(prefix="spl-verification-") as directory:
        return _verify(Path(directory), bundle)


def _execute(bundle, bindings, *, native, evidence_dir=None):
    with tempfile.TemporaryDirectory(prefix="spl-verification-") as directory:
        work = Path(directory)
        inputs = work / "bindings.json"
        inputs.write_bytes(_read(bindings))
        receipt = _verify(work, bundle)
        evidence = {"certificate_sha256": digest(receipt), "bindings_sha256": file_digest(inputs)}
        if native:
            if os.name != "nt":
                fail("VERIFICATION_NATIVE_PLATFORM", "The pinned ahead-of-time build currently uses Windows Lake")
            from .compact_execution import _stage, compiled_target
            executable = compiled_target(work)
            expected = file_digest(work / "Settlement.exe")
            if file_digest(executable) != expected:
                fail("VERIFICATION_EXECUTABLE_CHANGED", "Native executable differs from the recorded build")
            output = loads(_read(_stage([executable, inputs], work / "execution")))
            if file_digest(executable) != expected:
                fail("VERIFICATION_EXECUTABLE_CHANGED", "Native executable changed during execution")
            evidence.update(execution="pinned-native", executable_sha256=expected,
                            native_build_sha256=file_digest(work / "native-build.json"))
        else:
            output = loads(lean(["--run", work / "Settlement.lean", inputs]))
            evidence["execution"] = "pinned-lean"
        if _runtime_identity() != receipt["lean_runtime_sha256"]:
            fail("VERIFICATION_RUNTIME_CHANGED", "Lean runtime changed during execution")
        if evidence_dir is not None:
            write_json(evidence_dir / "certificate.json", receipt)
            if native:
                shutil.copyfile(work / "native-build.json", evidence_dir / "native-build.json")
                shutil.copyfile(work / "execution/process.json", evidence_dir / "execution.json")
        return {**output, "verification": evidence}


def run(bundle, bindings, *, native=False, output=None):
    """Execute a fresh checked artifact, optionally committing its result for public reload."""
    if output is None:
        return _execute(bundle, bindings, native=native)
    publication = ArtifactPublication(output)
    try:
        result = _execute(bundle, bindings, native=native, evidence_dir=publication.work)
    except (ValueError, OSError, RecursionError) as error:
        result = {"status": "blocked", "emissions": {}, "periods": [], "closing": {},
                  "diagnostics": [_diagnostic(error)]}
    return publication.finish(result, {"closing-state.json": "closing", "diagnostics.json": "diagnostics"})


def _diagnostic(error):
    if isinstance(error, DataError):
        return error.diagnostic()
    code = str(error).split(":", 1)[0] if isinstance(error, PublicationError) else "VERIFICATION_FAILED"
    return {"code": code, "message": str(error)}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m spl_compiler.verification")
    commands = parser.add_subparsers(dest="command", required=True)
    compile_command = commands.add_parser("certify")
    compile_command.add_argument("source", type=Path)
    compile_command.add_argument("bundle", type=Path)
    compile_command.add_argument("--link", type=Path)
    compile_command.add_argument("--mode", choices=["single", "series"], default="single")
    commands.add_parser("verify").add_argument("bundle", type=Path)
    run_command = commands.add_parser("run")
    run_command.add_argument("bundle", type=Path)
    run_command.add_argument("bindings", type=Path)
    run_command.add_argument("--native", action="store_true")
    run_command.add_argument("--output", type=Path, help="Commit the result for the public publication reader")
    args = vars(parser.parse_args(argv))
    command = args.pop("command")
    try:
        result = {"certify": certify, "verify": verify, "run": run}[command](**args)
    except (ValueError, OSError, RecursionError, PublicationError) as error:
        result = {"status": "blocked", "diagnostics": [_diagnostic(error)]}
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return int(result.get("status") == "blocked")


if __name__ == "__main__":
    raise SystemExit(main())
