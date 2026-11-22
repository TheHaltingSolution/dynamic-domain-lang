"""Experimental lossless archival transport for an ALREADY CREATED JSON trace.

This module does not change native emission, economics, audit observations or
the memory required to produce the original trace. Payload references exist
only in transport wrappers; user values (including ref-like keys and null) are
opaque. Logical identity is canonical JSON with sorted object keys and original
array order, UTF-8, no whitespace, and no floating-point numbers.
"""
import argparse
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import sys


FORMAT = "spl-trace-compact/0.1"
LOGICAL_FORMAT = "spl-trace-dag/0.1"
SHARE_FIELDS = frozenset({"operands", "result", "fact_ids", "value_type", "source_span",
                          "detail", "scope", "instance_scope", "lineage"})
_ENCODER = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


class TransportError(ValueError):
    """Malformed, unsupported, tampered or over-budget transport."""


def _need(condition, code):
    if not condition:
        raise TransportError(code)


@dataclass(frozen=True)
class Limits:
    max_nodes: int = 100000
    max_depth: int = 128
    max_input_bytes: int = 64 * 1024 * 1024
    max_expanded_bytes: int = 256 * 1024 * 1024

    def __post_init__(self):
        for value in (self.max_nodes, self.max_depth, self.max_input_bytes, self.max_expanded_bytes):
            _need(type(value) is int and value > 0, "INVALID_LIMIT")
        _need(self.max_nodes <= 100000 and self.max_depth <= 256, "INVALID_LIMIT")


def _scalar_bytes(value):
    try:
        return _ENCODER.encode(value).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise TransportError("INVALID_JSON_VALUE") from None


def _measure(value, limit, active=None, level=0):
    """Validate JSON types and return canonical byte length/container depth."""
    _need(level <= limit, "DEPTH_LIMIT")
    if value is None or type(value) in {str, int, bool}:
        return len(_scalar_bytes(value)), 0
    _need(type(value) in {dict, list}, "INVALID_JSON_VALUE")
    active = set() if active is None else active
    identity = id(value)
    _need(identity not in active, "CYCLIC_JSON_VALUE")
    active.add(identity)
    size, depth = 2, 1
    _need(level < limit, "DEPTH_LIMIT")
    for index, item in enumerate(value.items() if type(value) is dict else value):
        if index:
            size += 1
        if type(value) is dict:
            key, item = item
            _need(type(key) is str, "INVALID_JSON_KEY")
            size += len(_scalar_bytes(key)) + 1
        child_size, child_depth = _measure(item, limit, active, level + 1)
        size += child_size
        depth = max(depth, child_depth + 1)
    active.remove(identity)
    return size, depth


def canonical_json(value):
    """Canonical logical representation, with strict JSON types and null."""
    _measure(value, 256)
    return _ENCODER.encode(value)


def _digest(value):
    digest = hashlib.sha256()
    for chunk in _ENCODER.iterencode(value):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def _duplicates(pairs):
    result = {}
    for key, value in pairs:
        _need(key not in result, "DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def _invalid_number(_value):
    raise TransportError("FLOAT_FORBIDDEN")


def loads(raw, limits=Limits()):
    """Read strict JSON, guarding byte/depth limits before the JSON parser."""
    _need(type(raw) in {bytes, str}, "INVALID_JSON_INPUT")
    try:
        encoded = raw.encode("utf-8") if type(raw) is str else raw
        _need(len(encoded) <= limits.max_input_bytes, "INPUT_BYTE_LIMIT")
        text = encoded.decode("utf-8")
        depth, quoted, escaped = 0, False, False
        for character in text:
            if quoted:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character in "[{":
                depth += 1
                _need(depth <= limits.max_depth, "DEPTH_LIMIT")
            elif character in "]}":
                depth -= 1
        value = json.loads(text, object_pairs_hook=_duplicates,
                           parse_float=_invalid_number, parse_constant=_invalid_number)
        _measure(value, limits.max_depth)
        return value
    except (ValueError, UnicodeError, RecursionError) as exc:
        if isinstance(exc, TransportError):
            raise
        raise TransportError("INVALID_JSON_INPUT") from exc


def _trace(trace, limits):
    _need(type(trace) is list, "TRACE_LIST_REQUIRED")
    _need(len(trace) <= limits.max_nodes, "NODE_LIMIT")
    seen = set()
    for node in trace:
        _need(type(node) is dict, "TRACE_NODE_REQUIRED")
        identity, dependencies = node.get("node_id"), node.get("dependencies")
        _need(type(identity) is str and bool(identity), "NODE_ID_REQUIRED")
        _need(identity not in seen, "DUPLICATE_NODE_ID")
        _need(type(dependencies) is list and all(type(item) is str for item in dependencies), "DEPENDENCIES_REQUIRED")
        _need(all(item in seen for item in dependencies), "INVALID_DAG_ORDER")
        seen.add(identity)


def pack(trace, limits=Limits()):
    """Pack an existing trace; share only repeated fields with a net size gain."""
    _trace(trace, limits)
    expanded_size, _ = _measure(trace, limits.max_depth)
    _need(expanded_size <= limits.max_input_bytes, "INPUT_BYTE_LIMIT")
    _need(expanded_size <= limits.max_expanded_bytes, "EXPANDED_BYTE_LIMIT")
    candidates, field_refs = {}, []
    for node in trace:
        refs = {}
        for field, value in node.items():
            if field not in SHARE_FIELDS:
                continue
            encoded = _ENCODER.encode(value).encode("utf-8")
            reference = hashlib.sha256(encoded).hexdigest()
            if reference in candidates:
                old = candidates[reference]
                _need(old[0] == encoded, "PAYLOAD_HASH_COLLISION")
                old[2] += 1
            else:
                candidates[reference] = [encoded, value, 1]
            refs[field] = reference
        field_refs.append(refs)
    # A reference is a 66-byte JSON string; table entries cost another 68 bytes.
    selected = {ref for ref, (encoded, _value, count) in candidates.items()
                if count > 1 and (count - 1) * len(encoded) > count * 66 + 68}
    nodes = []
    for node, refs in zip(trace, field_refs):
        shared = {field: ref for field, ref in refs.items() if ref in selected}
        nodes.append({"inline": deepcopy({field: value for field, value in node.items() if field not in shared}),
                      "shared": shared})
    result = {"format": FORMAT, "logical_format": LOGICAL_FORMAT, "node_count": len(trace),
              "expanded_bytes": expanded_size, "logical_sha256": _digest(trace),
              "payloads": {ref: deepcopy(candidates[ref][1]) for ref in sorted(selected)}, "nodes": nodes}
    compact_size, _ = _measure(result, limits.max_depth)
    _need(compact_size <= limits.max_input_bytes, "INPUT_BYTE_LIMIT")
    return result


def unpack(envelope, limits=Limits()):
    """Validate sizes, hashes, DAG and digest BEFORE copying aliased payloads."""
    _need(type(envelope) is dict and set(envelope) == {"format", "logical_format", "node_count", "expanded_bytes", "logical_sha256", "payloads", "nodes"}, "INVALID_ENVELOPE_FIELDS")
    _need(envelope["format"] == FORMAT and envelope["logical_format"] == LOGICAL_FORMAT, "UNSUPPORTED_FORMAT")
    _need(type(envelope["node_count"]) is int and 0 <= envelope["node_count"] <= limits.max_nodes, "NODE_LIMIT")
    _need(type(envelope["expanded_bytes"]) is int and envelope["expanded_bytes"] >= 0, "INVALID_EXPANDED_SIZE")
    _need(envelope["expanded_bytes"] <= limits.max_expanded_bytes, "EXPANDED_BYTE_LIMIT")
    _need(type(envelope["logical_sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", envelope["logical_sha256"]), "INVALID_LOGICAL_HASH")
    input_size, _ = _measure(envelope, limits.max_depth)
    _need(input_size <= limits.max_input_bytes, "INPUT_BYTE_LIMIT")
    payloads, nodes = envelope["payloads"], envelope["nodes"]
    _need(type(payloads) is dict and type(nodes) is list, "INVALID_TABLES")
    _need(len(nodes) == envelope["node_count"], "NODE_COUNT_MISMATCH")
    measurements = {}
    for reference, value in payloads.items():
        _need(re.fullmatch(r"[0-9a-f]{64}", reference) is not None, "INVALID_PAYLOAD_REFERENCE")
        measurements[reference] = _measure(value, limits.max_depth)
        _need(_digest(value) == reference, "PAYLOAD_HASH_MISMATCH")
    expanded_size, used, alias_nodes = 2, set(), []
    for index, wrapper in enumerate(nodes):
        _need(type(wrapper) is dict and set(wrapper) == {"inline", "shared"}, "INVALID_NODE_WRAPPER")
        inline, shared = wrapper["inline"], wrapper["shared"]
        _need(type(inline) is dict and type(shared) is dict, "INVALID_NODE_WRAPPER")
        _need(not (set(inline) & set(shared)), "OVERLAPPING_NODE_FIELDS")
        _need(set(shared) <= SHARE_FIELDS, "UNSUPPORTED_SHARED_FIELD")
        size, depth = _measure(inline, limits.max_depth)
        field_count = len(inline)
        alias = dict(inline)
        for field, reference in shared.items():
            _need(type(reference) is str and reference in payloads, "DANGLING_REFERENCE")
            value_size, value_depth = measurements[reference]
            _need(value_depth + 2 <= limits.max_depth, "DEPTH_LIMIT")
            size += (1 if field_count else 0) + len(_scalar_bytes(field)) + 1 + value_size
            field_count += 1
            depth = max(depth, value_depth + 1)
            alias[field] = payloads[reference]
            used.add(reference)
        _need(depth + 1 <= limits.max_depth, "DEPTH_LIMIT")
        expanded_size += (1 if index else 0) + size
        _need(expanded_size <= limits.max_expanded_bytes, "EXPANDED_BYTE_LIMIT")
        alias_nodes.append(alias)
    _need(used == set(payloads), "UNUSED_PAYLOAD")
    _need(expanded_size == envelope["expanded_bytes"], "EXPANDED_SIZE_MISMATCH")
    _trace(alias_nodes, limits)
    _need(_digest(alias_nodes) == envelope["logical_sha256"], "LOGICAL_HASH_MISMATCH")
    # Sharing here is an encoding detail, not mutable aliasing in the result.
    return [{field: deepcopy(value) for field, value in node.items()} for node in alias_nodes]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("pack", "unpack"))
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-nodes", type=int, default=100000)
    parser.add_argument("--max-depth", type=int, default=128)
    parser.add_argument("--max-input-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--max-expanded-bytes", type=int, default=256 * 1024 * 1024)
    args = parser.parse_args(argv)
    try:
        limits = Limits(args.max_nodes, args.max_depth, args.max_input_bytes, args.max_expanded_bytes)
        with args.input.open("rb") as source:
            raw = source.read(limits.max_input_bytes + 1)
        value = loads(raw, limits)
        result = pack(value, limits) if args.operation == "pack" else unpack(value, limits)
        # Validation completes before the output path is opened or overwritten.
        encoded = canonical_json(result).encode("utf-8")
        args.output.write_bytes(encoded)
        return 0
    except (TransportError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
