"""Comparative SPL compilation certificates, independent of the pilot allowlist."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile

from .artifacts import ArtifactPublication, PublicationError
from .certification import _runtime_identity
from .codecs import DataError, digest, fail, file_digest, loads, write_json
from .lean_tools import compile_schedule, export_ir, lean
from .source_verification import check_native_ir, check_source
from .target_verification import check_target


FORMAT = "spl-comparative-certificate/1"
MAX_BYTES = 64 * 1024 * 1024


class VerificationError(DataError):
    """A gate failure with the original diagnostic and its verification stage."""

    def __init__(self, stage, code, message, pointer="", span=None):
        super().__init__(code, message, pointer, span)
        self.stage = stage

    def diagnostic(self):
        return {**super().diagnostic(), "stage": self.stage}


@contextmanager
def _at(stage, paths=None):
    try:
        yield
    except VerificationError:
        raise
    except (OSError, ValueError, RecursionError) as error:
        if isinstance(error, DataError):
            code, pointer, span = error.code, error.pointer, error.span
            stage = getattr(error, "stage", None) or stage
        elif isinstance(error, RecursionError):
            code, pointer, span = "VERIFICATION_RESOURCE_LIMIT", "", None
        else:
            code, pointer, span = "VERIFICATION_FAILED", "", None
        if "RESOURCE_LIMIT" in code:
            stage = "resource"
        message = str(error)
        for private, original in (paths or {}).items():
            for spelling in {str(private), private.as_posix()}:
                message = message.replace(spelling, str(original))
                if isinstance(pointer, str):
                    pointer = pointer.replace(spelling, str(original))
        raise VerificationError(stage, code, message, pointer, span) from error


def _read(path):
    with Path(path).open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        fail("VERIFICATION_RESOURCE_LIMIT", f"File exceeds verification limit: {path}")
    return data


def _prepare(work, source, link):
    authored = work / "consumed.source.spl"
    with _at("source"):
        authored.write_bytes(_read(source))
    manifest = None
    if link is not None:
        manifest = work / "consumed.link.json"
        with _at("link"):
            manifest.write_bytes(_read(link))
    return authored, manifest


def _check(work, source, link, *, mode, expected=None, paths=None):
    with _at("certificate" if expected is not None else "unsupported"):
        if mode not in ("single", "series"):
            fail("VERIFICATION_MODE", "Choose single or series settlement")
    with _at("runtime"):
        runtime = _runtime_identity()
    with _at("source", paths):
        pins = {source.name: file_digest(source)}
    if link is not None:
        with _at("link", paths):
            pins[link.name] = file_digest(link)
    typed = work / "typed-ir.json"
    with _at("ir", paths):
        export_ir(source, typed, link=link)
        typed_bytes = _read(typed)
    with _at("source", paths):
        checked = check_source(source, link=link)
    with _at("ir", paths):
        witness = check_native_ir(checked, loads(typed_bytes))
    artifact = work / "Settlement.lean"
    with _at("emit", paths):
        pins[typed.name] = sha256(typed_bytes).hexdigest()
        compile_schedule(source, artifact, link=link, series=(mode == "series"))
        pins[artifact.name] = sha256(_read(artifact)).hexdigest()
    with _at("certificate"):
        if expected is not None and (pins != expected["files"] or runtime != expected.get("lean_runtime_sha256")):
            fail("VERIFICATION_IDENTITY_MISMATCH", "Source, linked inputs, emitted artifact or Lean runtime changed")
    with _at("proof", paths):
        proof = check_target(work / "proof", artifact, checked, mode=mode)
        if proof["artifact_sha256"] != pins[artifact.name]:
            fail("VERIFICATION_PROOF_ARTIFACT_CHANGED", "Kernel proof checked a different emitted artifact")
        if any(file_digest(work / name) != pin for name, pin in pins.items()):
            fail("VERIFICATION_PROOF_ARTIFACT_CHANGED", "Staged files changed during the kernel proof")
    with _at("runtime"):
        if _runtime_identity() != runtime:
            fail("VERIFICATION_RUNTIME_CHANGED", "Lean runtime changed during the check")
    receipt = {"format": FORMAT, "mode": mode, "files": pins, "lean_runtime_sha256": runtime,
               "source_witness": witness, "target_proof": proof}
    with _at("certificate"):
        if expected is not None and receipt != expected:
            fail("VERIFICATION_CERTIFICATE_MISMATCH", "Fresh proof evidence differs from the certificate")
    return receipt


def _release(work, bundle, receipt):
    bundle = Path(bundle)
    bundle.parent.mkdir(parents=True, exist_ok=True)
    if bundle.exists() or bundle.is_symlink():
        fail("VERIFICATION_BUNDLE_EXISTS", f"Bundle destination already exists: {bundle}")
    # The public name first becomes visible after the complete bundle is staged
    # on the same filesystem. A process interruption before rename leaves no
    # partial directory under that name.
    with tempfile.TemporaryDirectory(prefix=".spl-release-", dir=bundle.parent) as directory:
        staged = Path(directory) / "bundle"
        staged.mkdir()
        for name, pin in receipt["files"].items():
            data = _read(work / name)
            if sha256(data).hexdigest() != pin:
                fail("VERIFICATION_IDENTITY_MISMATCH", f"Checked file changed before release: {name}")
            (staged / name).write_bytes(data)
        write_json(staged / "certificate.json", receipt)
        if (any(file_digest(staged / name) != pin for name, pin in receipt["files"].items()) or
                loads(_read(staged / "certificate.json")) != receipt):
            fail("VERIFICATION_RELEASE_MISMATCH", "Staged release differs from checked bundle")
        os.rename(staged, bundle)


def certify(source, bundle, *, link=None, mode="single"):
    """Publish one new bundle after independent checks and kernel proof succeed."""
    with tempfile.TemporaryDirectory(prefix="spl-verification-") as directory:
        work = Path(directory)
        authored, manifest = _prepare(work, source, link)
        paths = {authored: source}
        if manifest is not None:
            paths[manifest] = link
        receipt = _check(work, authored, manifest, mode=mode, paths=paths)
        with _at("release"):
            _release(work, bundle, receipt)
        return receipt


def _verify(work, bundle):
    bundle = Path(bundle)
    with _at("certificate"):
        receipt_path = bundle / "certificate.json"
        try:
            certificate = loads(_read(receipt_path))
        except FileNotFoundError:
            fail("VERIFICATION_CERTIFICATE_MISSING", f"Certificate is missing: {receipt_path}")
        if type(certificate) is not dict or certificate.get("format") != FORMAT:
            fail("VERIFICATION_CERTIFICATE_FORMAT", "Expected a comparative SPL certificate")
        names = {"consumed.source.spl", "typed-ir.json", "Settlement.lean"}
        files = certificate.get("files")
        if type(files) is not dict or set(files) not in (names, names | {"consumed.link.json"}):
            fail("VERIFICATION_CERTIFICATE_FORMAT", "Certificate has an invalid artifact inventory")
        retained = {}
        for name, expected in files.items():
            try:
                payload = _read(bundle / name)
            except FileNotFoundError:
                fail("VERIFICATION_BUNDLE_FILE_MISSING", f"Bundle file missing: {name}")
            if sha256(payload).hexdigest() != expected:
                fail("VERIFICATION_IDENTITY_MISMATCH", f"Bundle file changed: {name}")
            if name.startswith("consumed."):
                path = work / name
                path.write_bytes(payload)
                retained[name] = path
    source = retained["consumed.source.spl"]
    manifest = retained.get("consumed.link.json")
    paths = {path: bundle / name for name, path in retained.items()}
    return _check(work, source, manifest, mode=certificate.get("mode"), expected=certificate, paths=paths)


def verify(bundle):
    with tempfile.TemporaryDirectory(prefix="spl-verification-") as directory:
        return _verify(Path(directory), bundle)


def _execute(bundle, bindings, *, native, evidence_dir=None):
    with tempfile.TemporaryDirectory(prefix="spl-verification-") as directory:
        work = Path(directory)
        inputs = work / "bindings.json"
        with _at("bindings"):
            inputs.write_bytes(_read(bindings))
        receipt = _verify(work, bundle)
        evidence = {"certificate_sha256": digest(receipt), "bindings_sha256": file_digest(inputs)}
        if native:
            with _at("native-build"):
                if os.name != "nt":
                    fail("VERIFICATION_NATIVE_PLATFORM", "The pinned ahead-of-time build currently uses Windows Lake")
                from .compact_execution import _stage, compiled_target
                executable = compiled_target(work)
                expected = file_digest(work / "Settlement.exe")
                if file_digest(executable) != expected:
                    fail("VERIFICATION_EXECUTABLE_CHANGED", "Native executable differs from the recorded build")
            with _at("execution"):
                output = loads(_read(_stage([executable, inputs], work / "execution")))
                if file_digest(executable) != expected:
                    fail("VERIFICATION_EXECUTABLE_CHANGED", "Native executable changed during execution")
                evidence.update(execution="pinned-native", executable_sha256=expected,
                                native_build_sha256=file_digest(work / "native-build.json"))
        else:
            with _at("execution", {inputs: bindings}):
                output = loads(lean(["--run", work / "Settlement.lean", inputs]))
            evidence["execution"] = "pinned-lean"
        with _at("runtime"):
            if _runtime_identity() != receipt["lean_runtime_sha256"]:
                fail("VERIFICATION_RUNTIME_CHANGED", "Lean runtime changed during execution")
        if evidence_dir is not None:
            with _at("publication"):
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
    if isinstance(error, PublicationError):
        return {"code": str(error).split(":", 1)[0], "message": str(error), "stage": "publication"}
    return {"code": "VERIFICATION_FAILED", "message": str(error)}


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
