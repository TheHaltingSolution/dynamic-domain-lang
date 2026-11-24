"""Bounded reader for opt-in native compact JSONL audit transport.

The wire reuses archival inline/shared wrappers and opaque SHARE_FIELDS. It is
a different, streaming format: consecutive payload IDs, a financial outcome
head, node records and mandatory completion. Validation retains unique payloads
and identity sets, never an expanded node array unless explicitly requested.
File and reconstructed trace SHA256 values are evidence, not custody proofs.
"""
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import sys

from .trace_transport import Limits, SHARE_FIELDS, TransportError, canonical_json, loads


FORMAT = "spl-native-trace-stream/0.1"
INDEXED_FORMAT = "spl-native-trace-stream/0.2"
LOGICAL_FORMAT = "spl-trace-dag/0.1"


@dataclass(frozen=True)
class NativeLimits:
    max_input_bytes: int = 64 * 1024 * 1024
    max_record_bytes: int = 8 * 1024 * 1024
    max_payload_bytes: int = 32 * 1024 * 1024
    max_expanded_bytes: int = 1024 * 1024 * 1024
    max_nodes: int = 100000
    max_payloads: int = 100000
    max_depth: int = 128
    max_reconstruction_bytes: int = 64 * 1024 * 1024

    def __post_init__(self):
        if any(type(value) is not int or value <= 0 for value in vars(self).values()):
            raise TransportError("INVALID_LIMIT")
        if self.max_nodes > 100000 or self.max_payloads > 100000 or self.max_depth > 256:
            raise TransportError("INVALID_LIMIT")


def _need(condition, message):
    if not condition:
        raise TransportError(message)


def _bytes(value):
    return canonical_json(value).encode("utf-8")


def _native_escape_delta(value):
    """Lean 4.35 Json.compress uses Unicode escapes for tab/backspace/formfeed.

    Python's canonical encoder uses the two-byte short escapes for those three
    controls. Their logical values/digests agree, but native byte metadata must
    account for four extra bytes per occurrence, including object keys.
    """
    if type(value) is str:
        return 4 * sum(value.count(character) for character in ("\t", "\b", "\f"))
    if type(value) is list:
        return sum(_native_escape_delta(child) for child in value)
    if type(value) is dict:
        return sum(_native_escape_delta(key) + _native_escape_delta(child) for key, child in value.items())
    return 0


def _detail_references(value):
    if type(value) is dict:
        for key, child in value.items():
            if key in {"predicate_node", "skipped_node", "decision_node"}:
                _need(type(child) is str, "INVALID_DETAIL_REFERENCE")
                yield child
            else:
                yield from _detail_references(child)
    elif type(value) is list:
        for child in value:
            yield from _detail_references(child)


def _read_nodes(path, limits=NativeLimits(), *, reconstruct=False, expected_sha256=None):
    """Validate every record/node and hash the exact reconstructed logical trace.

    Shared payload values remain immutable aliases during validation. Explicit
    reconstruction deep-copies them and is separately bounded to avoid accidental
    expansion of a small transport into a giant mutable result.
    """
    if expected_sha256 is not None:
        _need(type(expected_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", expected_sha256), "INVALID_FILE_HASH")
    parse_limits = Limits(max_nodes=limits.max_nodes, max_depth=limits.max_depth,
                          max_input_bytes=limits.max_record_bytes + 1,
                          max_expanded_bytes=limits.max_expanded_bytes)
    payloads, payload_bytes, payload_deltas, used_payloads, unique_values = {}, {}, {}, set(), set()
    seen, ordered_ids, nodes, kinds, statuses = set(), [], [], Counter(), Counter()
    head, completed, transport_format = None, False, None
    wire_bytes, expanded_bytes, canonical_expanded_bytes, unique_bytes, node_count, edge_count = 0, 2, 2, 0, 0, 0
    wire_hash, logical_hash = hashlib.sha256(), hashlib.sha256()
    logical_hash.update(b"[")
    with Path(path).open("rb") as stream:
        while raw := stream.readline(limits.max_record_bytes + 2):
            _need(not completed, "TRAILING_RECORD_AFTER_COMPLETION")
            _need(len(raw) <= limits.max_record_bytes + 1, "RECORD_BYTE_LIMIT")
            _need(raw.endswith(b"\n"), "TRUNCATED_RECORD")
            wire_bytes += len(raw)
            _need(wire_bytes <= limits.max_input_bytes, "INPUT_BYTE_LIMIT")
            wire_hash.update(raw)
            record = loads(raw, parse_limits)
            _need(type(record) is dict, "RECORD_OBJECT_REQUIRED")
            tag = record.get("record")
            if head is None:
                _need(set(record) == {"record", "format", "logical_format", "head"} and tag == "header", "HEADER_REQUIRED")
                _need(type(record["format"]) is str and record["format"] in {FORMAT, INDEXED_FORMAT}
                      and record["logical_format"] == LOGICAL_FORMAT, "UNSUPPORTED_FORMAT")
                transport_format = record["format"]
                head = record["head"]
                _need(type(head) is dict and "trace" not in head, "INVALID_OUTCOME_HEAD")
                _need(head.get("trace_origin") == "native_ir_interpreter" and head.get("trace_format") == LOGICAL_FORMAT, "INVALID_TRACE_ORIGIN")
            elif tag == "payload":
                _need(set(record) == {"record", "id", "value"}, "INVALID_PAYLOAD_RECORD")
                reference = record["id"]
                _need(type(reference) is str and reference == "p" + str(len(payloads)), "INVALID_OR_DUPLICATE_PAYLOAD_ID")
                _need(len(payloads) < limits.max_payloads, "PAYLOAD_LIMIT")
                encoded = _bytes(record["value"])
                _need(encoded not in unique_values, "DUPLICATE_PAYLOAD_VALUE")
                native_delta = _native_escape_delta(record["value"])
                unique_bytes += len(encoded) + native_delta
                _need(unique_bytes <= limits.max_payload_bytes, "PAYLOAD_BYTE_LIMIT")
                unique_values.add(encoded)
                payloads[reference], payload_bytes[reference] = record["value"], encoded
                payload_deltas[reference] = native_delta
            elif tag == "node":
                expected_fields = {"record", "inline", "shared"} | ({"dependencies"} if transport_format == INDEXED_FORMAT else set())
                _need(set(record) == expected_fields, "INVALID_NODE_RECORD")
                inline, shared = record["inline"], record["shared"]
                _need(type(inline) is dict and type(shared) is dict, "INVALID_NODE_WRAPPER")
                _need(not set(inline) & set(shared), "OVERLAPPING_NODE_FIELDS")
                _need(set(shared) <= SHARE_FIELDS, "UNSUPPORTED_SHARED_FIELD")
                _need(node_count < limits.max_nodes, "NODE_LIMIT")
                node, encodings, deltas = dict(inline), {}, {}
                if transport_format == INDEXED_FORMAT:
                    _need("dependencies" not in inline and "dependencies" not in shared, "OVERLAPPING_DEPENDENCY_ENCODING")
                    indices = record["dependencies"]
                    _need(type(indices) is list and all(type(index) is int and 0 <= index < node_count for index in indices), "INVALID_DEPENDENCY_INDEX")
                    node["dependencies"] = [ordered_ids[index] for index in indices]
                for field, reference in shared.items():
                    _need(type(reference) is str and reference in payloads, "DANGLING_OR_FORWARD_PAYLOAD")
                    node[field], encodings[field] = payloads[reference], payload_bytes[reference]
                    deltas[field] = payload_deltas[reference]
                    used_payloads.add(reference)
                identity, dependencies = node.get("node_id"), node.get("dependencies")
                _need(type(identity) is str and bool(identity), "NODE_ID_REQUIRED")
                _need(identity not in seen, "DUPLICATE_NODE_ID")
                _need(type(dependencies) is list and all(type(d) is str for d in dependencies), "DEPENDENCIES_REQUIRED")
                _need(all(d in seen for d in dependencies), "INVALID_DAG_ORDER")
                references = set(_detail_references(node.get("detail", {})))
                _need(references <= set(dependencies), "DETAIL_REFERENCE_MISSING_DEPENDENCY")
                _need(references <= seen, "INVALID_DETAIL_REFERENCE_ORDER")
                _need(type(node.get("kind")) is str and type(node.get("status")) is str, "NODE_KIND_STATUS_REQUIRED")
                # Hash canonical expanded node bytes directly from cached field
                # encodings. Never serialize/copy a shared collection per node.
                parts = [b"{"]
                for index, field in enumerate(sorted(node)):
                    if index:
                        parts.append(b",")
                    parts.extend((_bytes(field), b":", encodings[field] if field in encodings else _bytes(node[field])))
                parts.append(b"}")
                size = sum(map(len, parts))
                native_delta = sum(_native_escape_delta(field) + (deltas[field] if field in deltas else _native_escape_delta(node[field])) for field in node)
                canonical_expanded_bytes += (1 if node_count else 0) + size
                expanded_bytes += (1 if node_count else 0) + size + native_delta
                _need(expanded_bytes <= limits.max_expanded_bytes, "EXPANDED_BYTE_LIMIT")
                if reconstruct:
                    _need(expanded_bytes <= limits.max_reconstruction_bytes, "RECONSTRUCTION_BYTE_LIMIT")
                    nodes.append(deepcopy(node))
                if node_count:
                    logical_hash.update(b",")
                for part in parts:
                    logical_hash.update(part)
                seen.add(identity)
                ordered_ids.append(identity)
                node_count += 1
                edge_count += len(dependencies)
                kinds[node["kind"]] += 1
                statuses[node["status"]] += 1
                yield node
            elif tag == "complete":
                _need(set(record) == {"record", "node_count", "payload_count", "expanded_bytes"}, "INVALID_COMPLETION_FIELDS")
                _need(all(type(record[k]) is int for k in ("node_count", "payload_count", "expanded_bytes")), "INVALID_COMPLETION_COUNTS")
                _need(record["node_count"] == node_count and record["payload_count"] == len(payloads), "COMPLETION_COUNT_MISMATCH")
                _need(record["expanded_bytes"] == expanded_bytes, "EXPANDED_SIZE_MISMATCH")
                _need(used_payloads == set(payloads), "UNUSED_PAYLOAD")
                completed = True
            else:
                raise TransportError("UNKNOWN_OR_OUT_OF_ORDER_RECORD")
    _need(head is not None and completed, "MISSING_COMPLETION")
    logical_hash.update(b"]")
    digest = wire_hash.hexdigest()
    _need(expected_sha256 is None or digest == expected_sha256, "FILE_HASH_MISMATCH")
    result = {"format": transport_format, "head": head, "node_count": node_count, "edge_count": edge_count,
              "payload_count": len(payloads), "unique_payload_bytes": unique_bytes,
              "wire_bytes": wire_bytes, "expanded_trace_bytes": expanded_bytes,
              "canonical_expanded_trace_bytes": canonical_expanded_bytes,
              "logical_sha256": logical_hash.hexdigest(), "transport_sha256": digest,
              "kinds": dict(sorted(kinds.items())), "statuses": dict(sorted(statuses.items())),
              "validation_scope": "all records/nodes/references/completion and canonical expanded trace hash; shared immutable payloads, no expanded node array"}
    if reconstruct:
        result["outcome"] = {**deepcopy(head), "trace": nodes}
    return result


def read_compact(path, limits=NativeLimits(), *, reconstruct=False, expected_sha256=None):
    """Validate the complete graph before returning its bounded head and summary."""
    nodes = _read_nodes(path, limits, reconstruct=reconstruct, expected_sha256=expected_sha256)
    while True:
        try:
            next(nodes)
        except StopIteration as completed:
            return completed.value


def iter_compact_nodes(path, limits=NativeLimits(), *, expected_sha256=None):
    """Yield isolated logical nodes after a full first-pass validation.

    Each yielded node is a fresh mutable value, independent of shared payloads.
    The second pass also verifies framing/completion and the first-pass file hash;
    callers must exhaust the iterator. No prefix grants financial authority.
    """
    summary = read_compact(path, limits, expected_sha256=expected_sha256)
    for node in _read_nodes(path, limits, expected_sha256=summary["transport_sha256"]):
        yield deepcopy(node)


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--max-input-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--max-expanded-bytes", type=int, default=1024 * 1024 * 1024)
    parser.add_argument("--expected-sha256")
    args = parser.parse_args(argv)
    try:
        summary = read_compact(args.input, NativeLimits(max_input_bytes=args.max_input_bytes,
                                                        max_expanded_bytes=args.max_expanded_bytes),
                               expected_sha256=args.expected_sha256)
        print(canonical_json(summary))
        return 0
    except (TransportError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
