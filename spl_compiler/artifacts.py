"""Single-process publication with bounded, validated artifact consumption.

Completion manifests bind immutable invocation files. SHA-256 detects changed
bytes relative to that manifest; it does not authenticate external facts.
"""
from hashlib import sha256
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

from .codecs import encode

FORMAT = "spl-artifact-publication/1"
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_RESULT_BYTES = 64 * 1024 * 1024


class PublicationError(RuntimeError):
    pass


def _json_bytes(value, *, compact=False):
    layout = {"separators": (",", ":")} if compact else {"indent": 2}
    return (json.dumps(encode(value), ensure_ascii=False, sort_keys=True,
                       allow_nan=False, **layout) + "\n").encode("utf-8")


def _atomic_bytes(path, payload):
    """Same-directory replacement after flushing file bytes; no power-loss proof."""
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix="." + path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix="." + destination.name + ".", suffix=".tmp", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "wb") as target, source.open("rb") as origin:
            while chunk := origin.read(1024 * 1024):
                target.write(chunk)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _file_hash(path):
    value = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def _read_bounded(path, maximum):
    with path.open("rb") as stream:
        payload = stream.read(maximum + 1)
    if len(payload) > maximum:
        raise PublicationError("PUBLICATION_RESOURCE_LIMIT")
    return payload


def _strict_json(payload):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise PublicationError("PUBLICATION_DUPLICATE_FIELD")
            result[key] = value
        return result
    def finite_float(text):
        value = float(text)
        if not math.isfinite(value):
            raise PublicationError("PUBLICATION_NONFINITE")
        return value
    return json.loads(payload, object_pairs_hook=pairs, parse_float=finite_float,
                      parse_constant=lambda value: (_ for _ in ()).throw(PublicationError("PUBLICATION_NONFINITE")))


class ArtifactPublication:
    format = FORMAT

    def __init__(self, destination):
        self.root = Path(destination).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        runs = self.root / ".runs"
        runs.mkdir(exist_ok=True)
        if runs.is_symlink() or runs.resolve() != runs:
            raise PublicationError("PUBLICATION_PATH")
        self.work = Path(tempfile.mkdtemp(prefix="", dir=runs))
        self.invocation_id = self.work.name
        self.closed = False
        self.running = _json_bytes({"format": self.format, "status": "running", "invocation_id": self.invocation_id})
        # This is the sole consumption authority. Invalidate before computation.
        _atomic_bytes(self.root / "completion.json", self.running)
        _atomic_bytes(self.root / "result.json", _json_bytes({
            "status": "blocked", "results": {}, "statements": [], "detail": [],
            "closing_state": [], "trace": [], "reconciliation": {},
            "diagnostics": [{"code": "RUN_IN_PROGRESS", "message": "Invocation has no completed publication"}]}))

    def finish(self, result, fields):
        """Commit once. Publication errors propagate, leaving no completed marker."""
        if self.closed:
            raise PublicationError("PUBLICATION_ALREADY_CLOSED")
        self.closed = True
        try:
            if _read_bounded(self.root / "completion.json", MAX_MANIFEST_BYTES) != self.running:
                raise PublicationError("PUBLICATION_INVOCATION_CHANGED")
            mirrors = {}
            for filename, field in fields.items():
                if not re.fullmatch(r"[a-z][a-z-]*\.json", filename):
                    raise PublicationError("PUBLICATION_FILENAME")
                payload = _json_bytes(result[field])
                _atomic_bytes(self.work / filename, payload)
                mirrors[filename] = payload
            # Budget the complete logical result without indentation overhead.
            # Separate field mirrors remain readable; no values are omitted.
            payload = _json_bytes(result, compact=True)
            if len(payload) > MAX_RESULT_BYTES:
                raise PublicationError("PUBLICATION_RESULT_RESOURCE_LIMIT")
            _atomic_bytes(self.work / "result.json", payload)
            mirrors["result.json"] = payload
            entries = []
            auxiliary = []
            for path in sorted(self.work.rglob("*")):
                if path.is_symlink() or not path.resolve().is_relative_to(self.work):
                    raise PublicationError("PUBLICATION_SYMLINK")
                if path.relative_to(self.work).parts[0] in {".runs", "completion.json"}:
                    raise PublicationError("PUBLICATION_RESERVED_PATH")
                if path.is_file():
                    with path.open("rb+") as stream:
                        os.fsync(stream.fileno())
                    entries.append({"path": path.relative_to(self.root).as_posix(),
                                    "bytes": path.stat().st_size, "sha256": _file_hash(path)})
                    if path.relative_to(self.work).as_posix() not in mirrors:
                        auxiliary.append(path)
            manifest = {"format": self.format, "status": "completed", "invocation_id": self.invocation_id,
                        "result_path": (self.work / "result.json").relative_to(self.root).as_posix(), "files": entries}
            manifest_bytes = _json_bytes(manifest)
            if len(entries) > 4096 or len(manifest_bytes) > MAX_MANIFEST_BYTES:
                raise PublicationError("PUBLICATION_RESOURCE_LIMIT")
            # Compatibility views are never authoritative and precede commit.
            for path in auxiliary:
                _atomic_copy(path, self.root / path.relative_to(self.work))
            for filename, data in mirrors.items():
                _atomic_bytes(self.root / filename, data)
            if _read_bounded(self.root / "completion.json", MAX_MANIFEST_BYTES) != self.running:
                raise PublicationError("PUBLICATION_INVOCATION_CHANGED")
            _atomic_bytes(self.root / "completion.json", manifest_bytes)
            return result
        except (OSError, ValueError) as error:
            raise PublicationError("PUBLICATION_FAILED: " + str(error)) from error


def _load_completed_bundle(destination, *, max_result_bytes=MAX_RESULT_BYTES, publication_format=FORMAT):
    """Verify every referenced file and a stable marker before returning JSON.

    A completed blocked or preview result remains nonconsumable financial state;
    the caller must still enforce the runner's final-success/carry contract.
    """
    if type(max_result_bytes) is not int or max_result_bytes <= 0:
        raise PublicationError("PUBLICATION_RESOURCE_LIMIT")
    root = Path(destination).resolve()
    try:
        marker = _read_bounded(root / "completion.json", MAX_MANIFEST_BYTES)
        manifest = _strict_json(marker)
        if (type(manifest) is not dict or set(manifest) != {"format", "status", "invocation_id", "result_path", "files"}
                or manifest["format"] != publication_format or manifest["status"] != "completed"
                or type(manifest["invocation_id"]) is not str or not re.fullmatch(r"[a-z0-9_-]{1,32}", manifest["invocation_id"])
                or type(manifest["files"]) is not list or not 1 <= len(manifest["files"]) <= 4096):
            raise PublicationError("PUBLICATION_NOT_COMPLETED")
        prefix = PurePosixPath(".runs") / manifest["invocation_id"]
        observed = set()
        result_payload = None
        for entry in manifest["files"]:
            if (type(entry) is not dict or set(entry) != {"path", "bytes", "sha256"}
                    or type(entry["path"]) is not str or type(entry["bytes"]) is not int or entry["bytes"] < 0
                    or type(entry["sha256"]) is not str or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])):
                raise PublicationError("PUBLICATION_ENTRY")
            relative = PurePosixPath(entry["path"])
            if (relative.is_absolute() or relative.as_posix() != entry["path"] or ".." in relative.parts
                    or "\\" in entry["path"] or not relative.is_relative_to(prefix) or entry["path"] in observed):
                raise PublicationError("PUBLICATION_PATH")
            path = root.joinpath(*relative.parts)
            if not path.resolve().is_relative_to(root / prefix) or path.is_symlink():
                raise PublicationError("PUBLICATION_PATH")
            if entry["path"] == manifest["result_path"]:
                # Decode the exact bytes whose digest was checked, never reread
                # the financial result after hashing a different file snapshot.
                result_payload = _read_bounded(path, max_result_bytes)
                if len(result_payload) != entry["bytes"] or sha256(result_payload).hexdigest() != entry["sha256"]:
                    raise PublicationError("PUBLICATION_DIGEST")
            elif path.stat().st_size != entry["bytes"] or _file_hash(path) != entry["sha256"]:
                raise PublicationError("PUBLICATION_DIGEST")
            observed.add(entry["path"])
        if result_payload is None:
            raise PublicationError("PUBLICATION_RESULT_REQUIRED")
        result = _strict_json(result_payload)
        if type(result) is not dict or _read_bounded(root / "completion.json", MAX_MANIFEST_BYTES) != marker:
            raise PublicationError("PUBLICATION_INVOCATION_CHANGED")
        return result, manifest, marker
    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise PublicationError("PUBLICATION_INVALID: " + str(error)) from error


def load_completed_result(destination, *, max_result_bytes=MAX_RESULT_BYTES):
    """Load only v1 publications; unsupported completion versions are rejected."""
    return _load_completed_bundle(destination, max_result_bytes=max_result_bytes)[0]
