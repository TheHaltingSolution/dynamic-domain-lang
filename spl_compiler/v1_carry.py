"""Bounded partial extraction from an unchanged completed v1 publication.

Every result byte/token and owned-file hash is validated. This receipt is not
a canonical result, a replacement audit, or a semantic-result-digest proof.
The default v1 loader remains unchanged.
"""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import math
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

from .artifacts import (FORMAT as V1_FORMAT, MAX_MANIFEST_BYTES, MAX_RESULT_BYTES,
                        PublicationError, _file_hash, _read_bounded, _strict_json)

FORMAT = "spl-validated-v1-carry-receipt/1"
MAX_DEPTH = 128
MAX_NODES = 100000
SELECTED = frozenset({"status", "results", "closing_state", "manifest", "result_digest", "verification"})
_NUMBER = re.compile(rb"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")
_SHA = re.compile(r"[0-9a-f]{64}")
_STRING_SPECIAL = re.compile(rb'["\\\x00-\x1f]')


def _need(condition, code):
    if not condition:
        raise PublicationError(code)


class _Reader:
    """Strict UTF8 JSON reader with one trace node resident at a time."""
    def __init__(self, stream):
        self.stream, self.buffer, self.position = stream, b"", 0
        self.bytes = 0
        self.hash = sha256()
        self.node_count, self.edges, self.seen = 0, 0, set()
        self.graph_error = None
        self.trace_present = False
        self.strings = {}

    def peek(self):
        if self.position == len(self.buffer):
            self.buffer = self.stream.read(min(65536, MAX_RESULT_BYTES + 1 - self.bytes))
            self.position = 0
            self.bytes += len(self.buffer)
            _need(self.bytes <= MAX_RESULT_BYTES, "V1_RECEIPT_RESULT_LIMIT")
            self.hash.update(self.buffer)
        return self.buffer[self.position] if self.position < len(self.buffer) else None

    def take(self):
        value = self.peek()
        _need(value is not None, "V1_RECEIPT_TRUNCATED_JSON")
        self.position += 1
        return value

    def expect(self, value):
        _need(self.take() == value, "V1_RECEIPT_JSON")

    def whitespace(self):
        while self.peek() in (9, 10, 13, 32):
            self.take()

    def string(self):
        self.expect(34)
        raw = bytearray(b'"')
        while True:
            _need(self.peek() is not None, "V1_RECEIPT_TRUNCATED_JSON")
            match = _STRING_SPECIAL.search(self.buffer, self.position)
            if match is None:
                raw.extend(self.buffer[self.position:])
                self.position = len(self.buffer)
                continue
            raw.extend(self.buffer[self.position:match.end()])
            self.position = match.end()
            value = match[0][0]
            if value == 34:
                break
            _need(value == 92, "V1_RECEIPT_JSON")
            raw.append(self.take())
        try:
            encoded = bytes(raw)
            if encoded in self.strings:
                return self.strings[encoded]
            result = _strict_json(encoded.decode("utf-8", errors="strict"))
            if len(encoded) <= 256 and len(self.strings) < 4096:
                self.strings[encoded] = result
            return result
        except (ValueError, UnicodeError) as error:
            raise PublicationError("V1_RECEIPT_STRING") from error

    def value(self, depth=0, capture=True):
        _need(depth <= MAX_DEPTH, "V1_RECEIPT_DEPTH_LIMIT")
        self.whitespace()
        token = self.peek()
        if token == 34:
            value = self.string()
        elif token == 123:
            _need(depth < MAX_DEPTH, "V1_RECEIPT_DEPTH_LIMIT")
            self.take()
            value, keys = {}, set()
            self.whitespace()
            if self.peek() != 125:
                while True:
                    self.whitespace()
                    key = self.string()
                    _need(key not in keys, "PUBLICATION_DUPLICATE_FIELD")
                    keys.add(key)
                    self.whitespace(); self.expect(58)
                    child = self.value(depth + 1, capture)
                    if capture:
                        value[key] = child
                    self.whitespace()
                    if self.peek() != 44:
                        break
                    self.take()
            self.expect(125)
        elif token == 91:
            _need(depth < MAX_DEPTH, "V1_RECEIPT_DEPTH_LIMIT")
            self.take()
            value = []
            self.whitespace()
            if self.peek() != 93:
                while True:
                    child = self.value(depth + 1, capture)
                    if capture:
                        value.append(child)
                    self.whitespace()
                    if self.peek() != 44:
                        break
                    self.take()
            self.expect(93)
        elif token in (116, 102, 110):
            literal, value = {116: (b"true", True), 102: (b"false", False), 110: (b"null", None)}[token]
            for byte in literal:
                self.expect(byte)
        else:
            raw = bytearray()
            while self.peek() is not None and self.peek() not in (9, 10, 13, 32, 44, 93, 125):
                raw.append(self.take())
            _need(_NUMBER.fullmatch(bytes(raw)) is not None, "V1_RECEIPT_JSON_NUMBER")
            try:
                value = _strict_json(bytes(raw))
            except ValueError as error:
                raise PublicationError("V1_RECEIPT_JSON_NUMBER") from error
        return value if capture else None

    def trace(self):
        self.trace_present = True
        self.whitespace(); self.expect(91); self.whitespace()
        if self.peek() != 93:
            while True:
                _need(self.node_count < MAX_NODES, "V1_RECEIPT_NODE_LIMIT")
                node = self.value(2)
                self._node(node)
                self.node_count += 1
                self.whitespace()
                if self.peek() != 44:
                    break
                self.take()
        self.expect(93)

    def _node(self, node):
        # Only these schema-defined trace fields are references. Ordinary
        # operand/result/state records with similar keys remain opaque values.
        def references(detail):
            if type(detail) is dict:
                for key, child in detail.items():
                    if key in {"predicate_node", "skipped_node", "decision_node"}:
                        if type(child) is not str:
                            self.graph_error = "V1_RECEIPT_DETAIL_REFERENCE"
                        else:
                            yield child
                    else:
                        yield from references(child)
            elif type(detail) is list:
                for child in detail:
                    yield from references(child)
        if type(node) is not dict:
            self.graph_error = "V1_RECEIPT_NODE"
            return
        identity, dependencies = node.get("node_id"), node.get("dependencies")
        if type(identity) is not str or not identity or identity in self.seen:
            self.graph_error = "V1_RECEIPT_NODE_ID"
            return
        if type(dependencies) is not list or not all(type(value) is str for value in dependencies):
            self.graph_error = "V1_RECEIPT_DEPENDENCIES"
        else:
            detail = set(references(node.get("detail", {})))
            if not all(value in self.seen for value in dependencies) or not detail <= set(dependencies):
                self.graph_error = "V1_RECEIPT_REFERENCE_ORDER"
            self.edges += len(dependencies)
        self.seen.add(identity)

    def root(self):
        self.whitespace(); self.expect(123)
        fields, selected, origin = set(), {}, None
        self.whitespace()
        if self.peek() != 125:
            while True:
                self.whitespace(); key = self.string()
                _need(key not in fields, "PUBLICATION_DUPLICATE_FIELD")
                fields.add(key)
                self.whitespace(); self.expect(58)
                if key == "trace":
                    self.trace()
                elif key in SELECTED:
                    selected[key] = self.value(1)
                elif key == "trace_origin":
                    origin = self.value(1)
                else:
                    self.value(1, capture=False)
                self.whitespace()
                if self.peek() != 44:
                    break
                self.take()
        self.expect(125); self.whitespace()
        _need(self.peek() is None, "V1_RECEIPT_TRAILING_JSON")
        if origin == "native_ir_interpreter":
            _need(self.trace_present and self.graph_error is None, self.graph_error or "V1_RECEIPT_TRACE_REQUIRED")
        return selected, {"trace_origin": origin, "node_count": self.node_count, "edge_count": self.edges,
                          "validation": "native_node_references" if origin == "native_ir_interpreter" else "complete_json_tokens_only"}


def _load_v1_inline(destination):
    root = Path(destination).resolve()
    try:
        marker = _read_bounded(root / "completion.json", MAX_MANIFEST_BYTES)
        manifest = _strict_json(marker)
        _need(type(manifest) is dict and set(manifest) == {"format", "status", "invocation_id", "result_path", "files"}
              and manifest["format"] == V1_FORMAT and manifest["status"] == "completed"
              and type(manifest["invocation_id"]) is str and re.fullmatch(r"[a-z0-9_-]{1,32}", manifest["invocation_id"])
              and type(manifest["files"]) is list and 1 <= len(manifest["files"]) <= 4096,
              "PUBLICATION_NOT_COMPLETED")
        prefix = PurePosixPath(".runs") / manifest["invocation_id"]
        observed, result, trace = set(), None, None
        result_hash, result_bytes = None, None
        for entry in manifest["files"]:
            _need(type(entry) is dict and set(entry) == {"path", "bytes", "sha256"}
                  and type(entry["path"]) is str and type(entry["bytes"]) is int and entry["bytes"] >= 0
                  and type(entry["sha256"]) is str and _SHA.fullmatch(entry["sha256"]), "PUBLICATION_ENTRY")
            relative = PurePosixPath(entry["path"])
            _need(not relative.is_absolute() and relative.as_posix() == entry["path"] and ".." not in relative.parts
                  and "\\" not in entry["path"] and relative.is_relative_to(prefix) and entry["path"] not in observed,
                  "PUBLICATION_PATH")
            path = root.joinpath(*relative.parts)
            _need(path.resolve().is_relative_to(root / prefix) and not path.is_symlink(), "PUBLICATION_PATH")
            if entry["path"] == manifest["result_path"]:
                _need(entry["bytes"] <= MAX_RESULT_BYTES, "V1_RECEIPT_RESULT_LIMIT")
                with path.open("rb") as stream:
                    reader = _Reader(stream)
                    result, trace = reader.root()
                    result_hash, result_bytes = reader.hash.hexdigest(), reader.bytes
                _need(result_bytes == entry["bytes"] and result_hash == entry["sha256"], "PUBLICATION_DIGEST")
            else:
                _need(path.stat().st_size == entry["bytes"] and _file_hash(path) == entry["sha256"], "PUBLICATION_DIGEST")
            observed.add(entry["path"])
        _need(result is not None, "PUBLICATION_RESULT_REQUIRED")
        _need(_read_bounded(root / "completion.json", MAX_MANIFEST_BYTES) == marker, "PUBLICATION_INVOCATION_CHANGED")
        return {"format": FORMAT, "publication_format": V1_FORMAT, "invocation_id": manifest["invocation_id"],
                "completion_sha256": sha256(marker).hexdigest(), "result_sha256": result_hash,
                "result_bytes": result_bytes, "selected_values": result, "trace_validation": trace,
                "scope": "Partial extraction after complete byte/token/owned-file validation; result_digest copied, not semantically proved"}
    except (OSError, ValueError, TypeError, RecursionError) as error:
        raise PublicationError("V1_RECEIPT_INVALID: " + str(error)) from error


@dataclass(frozen=True)
class V1CarryReceipt:
    """Immutable encoded receipt; callers receive fresh copies of actual cells."""
    _payload: bytes

    def to_dict(self):
        return _strict_json(self._payload)

    def opening_cells(self):
        report = self.to_dict()
        _need(type(report) is dict and type(report.get("selected_values")) is dict, "V1_RECEIPT_VALUES")
        values = report["selected_values"]
        status = values.get("status")
        _need(type(status) is str and status in {"calculated", "calculated_zero"}, "NONCONSUMABLE_STATE")
        if "manifest" in values:
            _need(type(values["manifest"]) is dict and values["manifest"].get("mode", "final") == "final", "NONCONSUMABLE_STATE")
        cells = values.get("closing_state")
        _need(type(cells) is list and all(type(cell) is dict for cell in cells), "V1_RECEIPT_CELLS")
        return [{key: value for key, value in cell.items() if key != "movement"} for cell in cells]


def load_completed_v1_carry_receipt(destination):
    """Read old owned bytes in a256MiB/60s worker, without a whole audit array."""
    from .compact_execution import _stage, WORKER
    from .lean_tools import ROOT
    from .codecs import DataError
    base = ROOT / ".lake/v1-receipt-readers"
    base.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=base) as directory:
            output = _stage([sys.executable, WORKER, "v1-carry", Path(destination).resolve()], Path(directory) / "read")
            payload = _read_bounded(output, MAX_RESULT_BYTES)
            value = _strict_json(payload)
            _need(type(value) is dict and value.get("format") == FORMAT, "V1_RECEIPT_FORMAT")
            return V1CarryReceipt(payload)
    except DataError as error:
        raise PublicationError("V1_RECEIPT_WORKER_FAILED: " + str(error)) from error
