"""Per-artifact certification for the approved two-receipt Readable SPL pilot."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import tempfile

from .codecs import DataError, canonical, digest, fail, loads
from .lean_tools import LIB, ROOT, compile_schedule, lean


PILOT = ROOT / "cases" / "certification"
POLICIES = ROOT / "cases" / "numeric-precision"
CERTIFICATE_FORMAT = "spl-readable-certificate/1"
TOOLCHAIN = "leanprover/lean4:v4.35.0"
MAX_SOURCE_BYTES = 64 * 1024
MAX_LINK_BYTES = 64 * 1024
MAX_ARTIFACT_BYTES = 128 * 1024
MAX_CERTIFICATE_BYTES = 16 * 1024
MAX_BINDINGS_BYTES = 1024 * 1024

SOURCE_PINS = {
    "aggregate": "551d30aeda92669d22d9eaecdc0daa8ffa7cbf9537ed7cdb918185dad03c4a5d",
    "row": "5aa2d1adc5fa0eb66973cfc5b84da8213c81c5cb4b11fc03091fd00a554c1498",
}
POLICY_PINS = {
    "money-rounding-module.json": "fa2522052102db7b5e6367a9793448e8ef28349cce5be560b0673bedc342070a",
    "money-rounding.spl": "93db1dbbc048469bd804a790a6b02ee2b2221c39a7318e96731a9961bc685b2e",
    "policy.md": "2f9459ee9acea59428fa76092e94aa307c3077dbc426042ccb62e00194e59b34",
}


@dataclass(frozen=True)
class _Prepared:
    profile: str
    source: bytes
    approved_sources: dict[str, bytes]
    link: bytes
    policy: bytes
    approved_policy: bytes


def _sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def _read(path: Path, limit: int, code: str) -> bytes:
    try:
        with Path(path).open("rb") as stream:
            contents = stream.read(limit + 1)
    except OSError as error:
        fail(code, f"Cannot read {path}: {error}")
    if len(contents) > limit:
        fail("CERT_RESOURCE_LIMIT", f"{path} exceeds the {limit}-byte limit")
    return contents


def _pin(path: Path, expected: str, limit: int, code: str) -> bytes:
    data = _read(path, limit, code)
    if _sha(data) != expected:
        fail(code, f"Approved profile contents changed at {path}")
    return data


def _policy_artifacts() -> tuple[dict, bytes]:
    files = {
        name: _pin(POLICIES / name, expected, MAX_LINK_BYTES, "CERT_POLICY_MISMATCH")
        for name, expected in POLICY_PINS.items()
    }
    name = "money-rounding-module.json"
    descriptor = loads(files[name])
    source = files["money-rounding.spl"]
    reference = {
        "id": descriptor["id"],
        "revision": descriptor["revision"],
        "locator": f"cases/numeric-precision/{name}",
        "sha256": POLICY_PINS[name],
    }
    manifest = {
        "modules": [{"reference": reference, "descriptor": descriptor, "source": source.decode("utf-8")}],
        "imports": [{
            "module_ref": reference,
            "alias": "money_rounding",
            "symbols": [{"local": "round_usd", "export": "round"}],
        }],
    }
    return manifest, source


def default_link() -> dict:
    """Return the native manifest for the approved existing rounding policy."""
    return _policy_artifacts()[0]


def _approved_sources() -> dict[str, bytes]:
    return {
        profile: _pin(PILOT / f"{profile}-readable.spl", expected, MAX_SOURCE_BYTES, "CERT_SPEC_MISMATCH")
        for profile, expected in SOURCE_PINS.items()
    }


def _prepare(source: Path, link: Path | None) -> _Prepared:
    source_bytes = _read(source, MAX_SOURCE_BYTES, "CERT_SOURCE_MISSING")
    approved_sources = _approved_sources()
    profile = next((name for name, approved in approved_sources.items() if source_bytes == approved), None)
    if profile is None:
        fail("CERT_SOURCE_UNSUPPORTED", "No approved meaning for these exact Readable SPL bytes")
    policy_manifest, approved_policy = _policy_artifacts()
    if link is None:
        link_bytes = canonical(policy_manifest).encode("utf-8")
        supplied = policy_manifest
    else:
        link_bytes = _read(link, MAX_LINK_BYTES, "CERT_POLICY_MISMATCH")
        try:
            supplied = loads(link_bytes)
        except DataError as error:
            fail("CERT_POLICY_MISMATCH", str(error))
        if supplied != policy_manifest:
            fail("CERT_POLICY_MISMATCH", "The linked rounding policy differs from the approved policy")
    policy = supplied["modules"][0]["source"].encode("utf-8")
    return _Prepared(profile, source_bytes, approved_sources, link_bytes, policy, approved_policy)


def identify(source: Path, *, link: Path | None = None) -> str:
    """Check exact authored source and link contents and return the reviewed profile."""
    return _prepare(source, link).profile


def _runtime_identity() -> str:
    version = lean(["--version"]).strip()
    if (ROOT / "lean-toolchain").read_text().strip() != TOOLCHAIN or "version 4.35.0," not in version:
        fail("CERT_TOOLCHAIN_MISMATCH", f"Expected {TOOLCHAIN}, got {version}")
    prefix = Path(lean(["--print-prefix"]).strip())
    binaries = sorted(path for path in (prefix / "bin").glob("lean*") if path.name in {"lean", "lean.exe"})
    shared = sorted(
        path for directory in (prefix / "lib" / "lean", prefix / "bin")
        for path in directory.glob("*leanshared*")
        if path.suffix in {".dll", ".so", ".dylib"}
    )
    library = sorted((LIB / "SPL").rglob("*.olean"))
    if not binaries or not (LIB / "SPL" / "Runtime.olean").is_file():
        fail("CERT_RUNTIME_MISSING", "Build the SPL library with the pinned Lean toolchain")
    files = (*binaries, *shared, *library)
    identities = [_runtime_file_hash(path) for path in files]
    return digest({"lean_version": version, "loaded_libraries": identities})


def _runtime_file_hash(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            value = sha256()
            while chunk := stream.read(1024 * 1024):
                value.update(chunk)
    except OSError as error:
        fail("CERT_RUNTIME_MISSING", f"Cannot read Lean runtime dependency {path}: {error}")
    return {"file": path.name, "sha256": value.hexdigest()}


def _stage(work: Path, prepared: _Prepared) -> tuple[Path, Path, Path]:
    proof = _read(PILOT / "KernelProof.lean", MAX_ARTIFACT_BYTES, "CERT_SPEC_MISMATCH")
    files = {
        "SuppliedSource.spl": prepared.source,
        "SuppliedPolicy.spl": prepared.policy,
        "ApprovedAggregate.spl": prepared.approved_sources["aggregate"],
        "ApprovedRow.spl": prepared.approved_sources["row"],
        "ApprovedPolicy.spl": prepared.approved_policy,
        "Link.json": prepared.link,
        "KernelProof.lean": proof.replace(b"PILOT_PROFILE", prepared.profile.encode("ascii")),
    }
    for name, data in files.items():
        (work / name).write_bytes(data)
    return work / "SuppliedSource.spl", work / "Link.json", work / "KernelProof.lean"


def _check_proof(work: Path, artifact: Path, proof: Path) -> None:
    try:
        lean(["-DwarningAsError=true", f"--root={work}", "-o", work / "CertifiedArtifact.olean", artifact])
        lean(["-DwarningAsError=true", f"--root={work}", proof], search_paths=(work,))
    except DataError as error:
        if error.code == "LEAN_RESOURCE_LIMIT":
            raise
        fail("CERT_PROOF_FAILED", str(error))


def _receipt(prepared: _Prepared, generated: bytes, proof: Path, runtime: str) -> dict:
    return {
        "format": CERTIFICATE_FORMAT,
        "profile": prepared.profile,
        "language": "spl/0.1-draft",
        "core": "spl-core/0.1-draft",
        "schema": "spl-data/0.1-draft",
        "toolchain": TOOLCHAIN,
        "source_sha256": _sha(prepared.source),
        "link_sha256": _sha(prepared.link),
        "policy_sha256": dict(POLICY_PINS),
        "artifact_sha256": _sha(generated),
        "proof_sha256": _sha(proof.read_bytes()),
        "lean_runtime_sha256": runtime,
        "theorems": ["PilotCertificate.source_and_artifact", "PilotCertificate.entry"],
    }


def _publish(path: Path, contents: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(contents)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def certify(source: Path, artifact: Path, certificate: Path, *, link: Path | None = None) -> dict:
    """Compile through the ordinary emitter and publish a receipt after kernel checking."""
    paths = [Path(path).resolve() for path in (source, artifact, certificate, link) if path is not None]
    if len(paths) != len(set(paths)):
        fail("CERT_PATH_COLLISION", "Source, link, artifact, and certificate paths must be distinct")
    prepared = _prepare(source, link)
    runtime = _runtime_identity()
    with tempfile.TemporaryDirectory(prefix="spl-cert-") as temporary:
        work = Path(temporary)
        authored, manifest, proof = _stage(work, prepared)
        target = compile_schedule(authored, work / "CertifiedArtifact.lean", link=manifest)
        generated = _read(target, MAX_ARTIFACT_BYTES, "CERT_ARTIFACT_MISSING")
        _check_proof(work, target, proof)
        if _runtime_identity() != runtime:
            fail("CERT_RUNTIME_MISMATCH", "The Lean runtime changed during certification")
        receipt = _receipt(prepared, generated, proof, runtime)
    _publish(artifact, generated)
    _publish(certificate, (canonical(receipt) + "\n").encode("utf-8"))
    return receipt


def _verify(
    work: Path, source: Path, artifact: Path, certificate: Path, link: Path | None
) -> tuple[dict, Path]:
    prepared = _prepare(source, link)
    encoded = _read(certificate, MAX_CERTIFICATE_BYTES, "CERT_CERTIFICATE_MISSING")
    try:
        claimed = loads(encoded)
    except DataError as error:
        fail("CERT_CERTIFICATE_MISMATCH", str(error))
    actual = _read(artifact, MAX_ARTIFACT_BYTES, "CERT_ARTIFACT_MISSING")
    authored, manifest, proof = _stage(work, prepared)
    if not isinstance(claimed, dict) or claimed.get("format") != CERTIFICATE_FORMAT:
        fail("CERT_CERTIFICATE_MISMATCH", "Expected a pilot certificate receipt")
    if claimed.get("artifact_sha256") != _sha(actual):
        fail("CERT_ARTIFACT_MISMATCH", "The artifact bytes differ from the certificate receipt")
    runtime = _runtime_identity()
    if claimed.get("lean_runtime_sha256") != runtime:
        fail("CERT_RUNTIME_MISMATCH", "The Lean runtime differs from the certificate receipt")
    expected = _receipt(prepared, actual, proof, runtime)
    if claimed != expected:
        fail("CERT_CERTIFICATE_MISMATCH", "The receipt does not match the authored source, link, and proof")
    target = compile_schedule(authored, work / "CertifiedArtifact.lean", link=manifest)
    if _read(target, MAX_ARTIFACT_BYTES, "CERT_ARTIFACT_MISSING") != actual:
        fail("CERT_ARTIFACT_MISMATCH", "The artifact differs from the current approved emitter output")
    _check_proof(work, target, proof)
    if _runtime_identity() != runtime:
        fail("CERT_RUNTIME_MISMATCH", "The Lean runtime changed during certificate checking")
    return expected, target


def verify(source: Path, artifact: Path, certificate: Path, *, link: Path | None = None) -> dict:
    """Re-establish the receipt from fresh checks of staged input and output bytes."""
    with tempfile.TemporaryDirectory(prefix="spl-cert-") as temporary:
        return _verify(Path(temporary), source, artifact, certificate, link)[0]


def run_certified(
    source: Path, artifact: Path, certificate: Path, bindings: Path, *,
    link: Path | None = None, include_certificate: bool = False
) -> dict:
    """Check the certificate and execute the same staged artifact with native admission."""
    binding_bytes = _read(bindings, MAX_BINDINGS_BYTES, "CERT_BINDINGS_MISSING")
    with tempfile.TemporaryDirectory(prefix="spl-cert-") as temporary:
        work = Path(temporary)
        receipt, target = _verify(work, source, artifact, certificate, link)
        staged = work / "Bindings.json"
        staged.write_bytes(binding_bytes)
        outcome = loads(lean(["--run", target, staged]))
        if _runtime_identity() != receipt["lean_runtime_sha256"]:
            fail("CERT_RUNTIME_MISMATCH", "The Lean runtime changed during settlement")
        if include_certificate:
            return {**outcome, "certificate": receipt}
        return outcome
