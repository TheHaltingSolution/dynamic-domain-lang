"""Explicit v2 publication of complete, bounded native compact audit sidecars.

Hashes establish consistency with the committed files, not source authenticity.
The existing v1 helper and loader keep their original default contract.
"""
from copy import deepcopy
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

from .artifacts import (ArtifactPublication, PublicationError, MAX_MANIFEST_BYTES,
                        MAX_RESULT_BYTES, _load_completed_bundle, _read_bounded, _file_hash,
                        _json_bytes, _atomic_bytes)
from .codecs import digest
from .native_trace import INDEXED_FORMAT, LOGICAL_FORMAT, NativeLimits, iter_compact_nodes, read_compact
from .trace_transport import TransportError, canonical_json

FORMAT = "spl-artifact-publication/2"
RESULT_FORMAT = "spl-canonical-result/2"
TRACE_FORMAT = "spl-canonical-trace-reference/1"
PROFILE = "compact-v2"
LIMITS = NativeLimits()
_SHA = re.compile(r"[0-9a-f]{64}")
_COUNTS = ("wire_bytes", "expanded_trace_bytes", "canonical_expanded_trace_bytes",
           "node_count", "edge_count", "payload_count")
_IDENTITY = ("format", "logical_sha256", "transport_sha256", *_COUNTS)
_CONSUMED = {"source_sha256": "consumed.source.spl", "bindings_sha256": "bindings.json",
             "typed_ir_sha256": "typed-ir.json", "emitted_sha256": "Settlement.lean",
             "target_sha256": "Settlement.exe", "build_sha256": "native-build.json",
             "link_sha256": "consumed.link.json"}


def _need(condition, code):
    if not condition:
        raise PublicationError(code)


def unavailable_trace(status="unavailable"):
    _need(status in {"unavailable", "incomplete"}, "AUDIT_STATUS")
    return {"format": TRACE_FORMAT, "profile": PROFILE, "status": status}


def _empty_blocked(result):
    return (result.get("status") == "blocked" and
            all(not result.get(key) for key in
                ("results", "statements", "detail", "closing_state", "reconciliation")))


def semantic_result_digest(result):
    """Physical invocation paths and payload-sharing identities are separate pins."""
    value = deepcopy(result)
    value.pop("result_digest", None)
    value.pop("manifest", None)
    trace = value.get("trace")
    if type(trace) is dict and trace.get("status") == "complete":
        for field in ("path", "transport_sha256", "wire_bytes", "payload_count", "format_native"):
            trace.pop(field, None)
        for field in ("target_sha256", "build_sha256"):
            trace.get("bindings", {}).pop(field, None)
    return digest(value)


class AuditedPublication(ArtifactPublication):
    format = FORMAT

    def attach(self, sidecar, *, bindings, view=None):
        """Validate an already owned complete wire before runner finalization.

        `bindings` records exact consumed inputs and compiler artifacts. It is
        closed to non-string labels and non-SHA256 values; no external locator
        supplied here can become an owned file path.
        """
        path = Path(sidecar)
        _need(path == self.work / "audit.native.jsonl" and
              path.resolve().parent == self.work and not path.is_symlink(), "AUDIT_OWNERSHIP")
        _need(type(bindings) is dict and bindings and
              all(type(key) is str and re.fullmatch(r"[a-z][a-z0-9_]*", key) and
                  type(value) is str and _SHA.fullmatch(value)
                  for key, value in bindings.items()), "AUDIT_BINDINGS")
        _check_consumed(self.work, bindings)
        try:
            summary = _bounded_summary(path)
        except (TransportError, OSError) as error:
            raise PublicationError("AUDIT_INVALID: " + str(error)) from error
        _need(summary["format"] == INDEXED_FORMAT, "AUDIT_FORMAT")
        view = {"format": "spl-native-logical-trace/1"} if view is None else deepcopy(view)
        _validate_view(view)
        from hashlib import sha256
        return {"format": TRACE_FORMAT, "profile": PROFILE, "status": "complete",
                "path": path.relative_to(self.root).as_posix(),
                "format_native": summary["format"],
                "logical_format": LOGICAL_FORMAT,
                **{key: summary[key] for key in _IDENTITY if key != "format"},
                "head_sha256": sha256(canonical_json(summary["head"]).encode()).hexdigest(),
                "bindings": dict(bindings), "view": view}, summary["head"]

    def _finish_inline(self, result, fields):
        _validate_result(result)
        # Revalidate the actual wire immediately before the marker can commit.
        if result["trace"]["status"] == "complete":
            _, summary = _check_trace(self.root, self.invocation_id, result["trace"])
            _check_outcome_authority(result, summary["head"])
        result["result_format"] = RESULT_FORMAT
        result["audit_profile"] = PROFILE
        if not _empty_blocked(result):
            result["result_digest"] = semantic_result_digest(result)
        return super().finish(result, fields)

    def finish(self, result, fields):
        """Finalize in a sampled256MiB/60s worker; invalidate on any failure."""
        _need(not self.closed, "PUBLICATION_ALREADY_CLOSED")
        self.closed = True
        from .compact_execution import _stage, WORKER
        request = _json_bytes({"result": result, "fields": fields}, compact=True)
        _need(len(request) <= MAX_RESULT_BYTES, "PUBLICATION_RESULT_RESOURCE_LIMIT")
        _atomic_bytes(self.work / "publication-request.json", request)
        try:
            log = self.root / ".publication-workers" / self.invocation_id
            try:
                _stage([sys.executable, WORKER, "publish", self.root, self.invocation_id], log)
            except Exception as error:
                raise PublicationError("PUBLICATION_WORKER_FAILED: " + str(error)) from error
            # Revalidate the completed marker/files/graph before exposing any
            # numeric result. A validation-to-manifest file mutation must not
            # bypass the consumer contract through the direct runner return.
            committed = load_completed_audited_result(self.root)
            self.closed = True
            result.clear()
            result.update(committed)
            return result
        except BaseException:
            # The child may have committed before a resource/cancel observation.
            # Never leave that result consumable when this invocation failed.
            try:
                from .artifacts import _strict_json
                marker = _strict_json(_read_bounded(self.root / "completion.json", MAX_MANIFEST_BYTES))
                if marker.get("invocation_id") == self.invocation_id:
                    _atomic_bytes(self.root / "completion.json", self.running)
            finally:
                self.closed = True
            raise


def _validate_view(view):
    _need(type(view) is dict, "AUDIT_VIEW")
    if view.get("format") == "spl-native-logical-trace/1":
        _need(set(view) == {"format"}, "AUDIT_VIEW")
    else:
        _need(set(view) == {"format", "source_sha256", "scope"} and
              view["format"] == "spl-legacy-qualified-trace/1" and
              type(view["source_sha256"]) is str and _SHA.fullmatch(view["source_sha256"]) and
              type(view["scope"]) is dict, "AUDIT_VIEW")


def _validate_result(result):
    _need(type(result) is dict and type(result.get("trace")) is dict, "AUDIT_REFERENCE_REQUIRED")
    _need(result.get("status") in {"blocked", "provisional", "calculated", "calculated_zero"}, "AUDIT_RESULT_STATUS")
    if result["status"] == "blocked":
        _need(_empty_blocked(result) and not result.get("result_digest"), "AUDIT_BLOCKED_FINANCE")
    if result["status"] == "provisional":
        _need(not result.get("closing_state"), "AUDIT_PREVIEW_STATE")
    trace = result["trace"]
    _need(trace.get("format") == TRACE_FORMAT and trace.get("profile") == PROFILE, "AUDIT_PROFILE")
    if trace.get("status") in {"unavailable", "incomplete"}:
        _need(set(trace) == {"format", "profile", "status"} and _empty_blocked(result) and
              not result.get("result_digest"), "AUDIT_INCOMPLETE_FINANCE")
    else:
        _need(trace.get("status") == "complete", "AUDIT_STATUS")


def _check_outcome_authority(result, head):
    _need(type(head) is dict and set(head) == {"status", "emissions", "closing", "diagnostics", "trace_origin", "trace_format"}
          and head["status"] in {"calculated", "blocked"} and type(head["emissions"]) is dict
          and type(head["closing"]) is dict and type(head["diagnostics"]) is list
          and all(type(row) is dict and set(row) == {"code"} and type(row["code"]) is str
                  for row in head["diagnostics"]), "AUDIT_OUTCOME_HEAD")
    if head["status"] == "blocked":
        _need(not head["emissions"] and not head["closing"] and head["diagnostics"], "AUDIT_OUTCOME_HEAD")
    if result["status"] != "blocked":
        _need(head.get("status") == "calculated" and not head.get("diagnostics"), "AUDIT_NATIVE_NOT_CALCULATED")


def _check_trace(root, invocation, trace):
    expected = {"format", "profile", "status", "path", "format_native", "logical_format", "logical_sha256",
                "transport_sha256", "head_sha256", "bindings", "view", *_COUNTS}
    _need(set(trace) == expected and trace["format_native"] == INDEXED_FORMAT and
          trace["logical_format"] == LOGICAL_FORMAT, "AUDIT_REFERENCE")
    relative = PurePosixPath(trace["path"]) if type(trace["path"]) is str else None
    _need(relative == PurePosixPath(".runs") / invocation / "audit.native.jsonl", "AUDIT_OWNERSHIP")
    owned = Path(root) / ".runs" / invocation
    path = Path(root).joinpath(*relative.parts)
    _need(path.resolve().parent == owned and not path.is_symlink(), "AUDIT_OWNERSHIP")
    _need(all(type(trace[key]) is int and trace[key] >= 0 for key in _COUNTS), "AUDIT_COUNTS")
    _need(all(type(trace[key]) is str and _SHA.fullmatch(trace[key])
              for key in ("logical_sha256", "transport_sha256", "head_sha256")), "AUDIT_HASH")
    _need(type(trace["bindings"]) is dict and trace["bindings"] and
          all(type(k) is str and re.fullmatch(r"[a-z][a-z0-9_]*", k) and
              type(v) is str and _SHA.fullmatch(v) for k, v in trace["bindings"].items()), "AUDIT_BINDINGS")
    _check_consumed(owned, trace["bindings"])
    _validate_view(trace["view"])
    try:
        summary = read_compact(path, LIMITS, expected_sha256=trace["transport_sha256"])
    except (TransportError, OSError) as error:
        raise PublicationError("AUDIT_INVALID: " + str(error)) from error
    _need(all(summary[key] == trace[key] for key in _IDENTITY if key != "format"), "AUDIT_IDENTITY")
    from hashlib import sha256
    _need(sha256(canonical_json(summary["head"]).encode()).hexdigest() == trace["head_sha256"], "AUDIT_HEAD")
    return path, summary


def _check_consumed(owned, bindings):
    required = set(_CONSUMED) - {"link_sha256"}
    _need(set(bindings) in (required, set(_CONSUMED)), "AUDIT_BINDINGS")
    for label, expected in bindings.items():
        path = owned / _CONSUMED[label]
        _need(path.resolve().parent == owned and not path.is_symlink() and
              path.is_file() and _file_hash(path) == expected, "AUDIT_CONSUMED_BYTES")


def _load_completed_inline(destination):
    """Return canonical financial/state fields only after full sidecar validation."""
    root = Path(destination).resolve()
    result, manifest, marker = _load_completed_bundle(root, publication_format=FORMAT)
    _need(result.get("result_format") == RESULT_FORMAT and result.get("audit_profile") == PROFILE, "AUDIT_RESULT_FORMAT")
    _validate_result(result)
    if result["trace"]["status"] == "complete":
        paths = {entry["path"]: entry for entry in manifest["files"]}
        _need(manifest["result_path"] == f".runs/{manifest['invocation_id']}/result.json" and
              result["trace"]["path"] in paths, "AUDIT_UNOWNED")
        for label, expected in result["trace"].get("bindings", {}).items():
            _need(label in _CONSUMED, "AUDIT_BINDINGS")
            consumed_path = f".runs/{manifest['invocation_id']}/{_CONSUMED[label]}"
            _need(consumed_path in paths and paths[consumed_path]["sha256"] == expected, "AUDIT_UNOWNED")
        _, summary = _check_trace(root, manifest["invocation_id"], result["trace"])
        _check_outcome_authority(result, summary["head"])
        if not _empty_blocked(result):
            _need(result.get("result_digest") == semantic_result_digest(result), "AUDIT_RESULT_DIGEST")
    _need(_read_bounded(root / "completion.json", MAX_MANIFEST_BYTES) == marker, "PUBLICATION_INVOCATION_CHANGED")
    return result


def _bounded_summary(path):
    from .compact_execution import _stage, metadata, WORKER
    from .lean_tools import ROOT
    base = ROOT / ".lake/audit-readers"
    base.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=base) as directory:
            output = _stage([sys.executable, WORKER, "validate", path], Path(directory) / "validate")
            return metadata(output)
    except Exception as error:
        raise PublicationError("AUDIT_INVALID: " + str(error)) from error


def load_completed_audited_result(destination):
    """Validate v2 files and full audit in a bounded reader worker first."""
    from .compact_execution import _stage, metadata, WORKER
    from .lean_tools import ROOT
    from .codecs import DataError
    base = ROOT / ".lake/audit-readers"
    base.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(dir=base) as directory:
            output = _stage([sys.executable, WORKER, "load", Path(destination).resolve()], Path(directory) / "load")
            return metadata(output)
    except DataError as error:
        raise PublicationError("AUDIT_INVALID: " + str(error)) from error


def iter_audited_trace(destination):
    """Bounded full logical nodes; no codec interpretation of user records."""
    result = load_completed_audited_result(destination)
    trace = result["trace"]
    _need(trace["status"] == "complete", "AUDIT_NOT_COMPLETED")
    path = Path(destination).resolve().joinpath(*PurePosixPath(trace["path"]).parts)
    yield from iter_compact_nodes(path, LIMITS, expected_sha256=trace["transport_sha256"])


def iter_v1_compatible_audited_trace(destination):
    """Historical canonical-array projection, one node at a time.

    Unlike the authoritative native logical view, this reproduces v1's
    ambiguous recursive rational-record normalizer. It is a compatibility
    view, never financial decoding or a universal lossless value relation.
    """
    from .run import normalize_target
    result = load_completed_audited_result(destination)
    trace = result["trace"]
    _need(trace["status"] == "complete", "AUDIT_NOT_COMPLETED")
    view = trace["view"]
    path = Path(destination).resolve().joinpath(*PurePosixPath(trace["path"]).parts)
    prefix = view.get("source_sha256", "") + ":"
    def qualify(value):
        if type(value) is dict:
            return {key: prefix + child if key in {"predicate_node", "skipped_node", "decision_node"}
                    and type(child) is str else qualify(child) for key, child in value.items()}
        if type(value) is list:
            return [qualify(child) for child in value]
        return value
    marker = _read_bounded(Path(destination) / "completion.json", MAX_MANIFEST_BYTES)
    for raw in iter_compact_nodes(path, LIMITS, expected_sha256=trace["transport_sha256"]):
        node = normalize_target(raw)
        if view["format"] == "spl-legacy-qualified-trace/1":
            node["node_id"] = prefix + node["node_id"]
            node["dependencies"] = [prefix + identity for identity in node["dependencies"]]
            if "detail" in node:
                node["detail"] = qualify(node["detail"])
            node["scope"] = deepcopy(view["scope"])
        yield node
    _need(_read_bounded(Path(destination) / "completion.json", MAX_MANIFEST_BYTES) == marker,
          "PUBLICATION_INVOCATION_CHANGED")


def carry_audited_state(destination):
    """Read actual completed publication before exporting next opening cells."""
    from .run import carry_state
    return carry_state(load_completed_audited_result(destination))
