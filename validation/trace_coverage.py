"""Observed native-IR decision evidence, without an invented coverage denominator.

The supplied hash qualifies the exact invocation source. For linked programs the
caller must also retain its complete dependency manifest; this function cannot
derive or verify source bytes, original library spans, or target execution from
an interpreter trace alone.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
import hashlib
import json
import re


_REFERENCES = frozenset({"predicate_node", "skipped_node", "decision_node"})
_STATUSES = frozenset({"evaluated", "not_evaluated", "failed", "discarded", "passed", "calculated"})


def _references(value):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in _REFERENCES:
                if not isinstance(child, str):
                    raise ValueError("Trace detail reference must be a node ID")
                yield child
            else:
                yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)


def _hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _identity(node, source_sha256):
    """Read the actual Trace.key tuple, including the IR metadata suffix."""
    raw_id = node.get("node_id")
    if not isinstance(raw_id, str) or not raw_id:
        raise ValueError("Missing native trace node_id")
    try:
        key = json.loads(raw_id)
    except (ValueError, TypeError) as error:
        raise ValueError("Native trace ID must be a Trace.key JSON tuple") from error
    if (not isinstance(key, list) or len(key) != 6
            or not all(isinstance(key[i], str) for i in (0, 3, 4, 5))
            or any(type(key[i]) is not int or key[i] < 0 for i in (1, 2))
            or key[2] < key[1]):
        raise ValueError("Malformed native Trace.key tuple")
    role, delimiter, number = key[5].rpartition(":ir:")
    if not delimiter or not role or not re.fullmatch(r"[0-9]+", number):
        raise ValueError("Native trace ID lacks an IR metadata ID")
    span = node.get("source_span")
    if not isinstance(span, dict) or any(type(span.get(k)) is not int or span[k] < 0
                                         for k in ("start", "stop", "line", "column")):
        raise ValueError("Missing or malformed native source span")
    if (span["start"], span["stop"]) != (key[1], key[2]):
        raise ValueError("Native trace ID and source span disagree")
    if node.get("rule_id") != key[3] or node.get("instance_scope") != key[4]:
        raise ValueError("Native trace ID and rule/scope disagree")
    ir_id = int(number)
    expression_key = json.dumps([key[0], ir_id], ensure_ascii=False, separators=(",", ":"))
    return {
        "observation_id": source_sha256 + ":node:" + _hash(raw_id),
        "expression_id": source_sha256 + ":ir:" + _hash(expression_key),
        "node_id": raw_id,
        "schedule": key[0],
        "ir_id": ir_id,
        "role": role,
        "source_span": deepcopy(span),
        "rule_id": key[3],
        "instance_scope": key[4],
        "kind": node["kind"],
        "status": node["status"],
        "outcome": node["outcome"],
    }


def summarize_trace(trace, source_sha256):
    """Validate and summarize one serialized native interpreter DAG.

    Raises ValueError on malformed identity, order, dependency or decision
    references. Empty traces are valid (e.g. rejected IR) and supply no decision
    evidence. Results describe observations, not all potential source paths.
    """
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("source_sha256 must be a lowercase SHA256 hex digest")
    if not isinstance(trace, list):
        raise ValueError("Native trace must be a list")
    seen = set()
    kinds, statuses = Counter(), Counter()
    decisions, skipped, failures, discarded = [], [], [], []
    expression_ids = set()
    for node in trace:
        if not isinstance(node, dict):
            raise ValueError("Native trace node must be an object")
        if not isinstance(node.get("kind"), str) or not node["kind"]:
            raise ValueError("Missing native trace node kind")
        if node.get("status") not in _STATUSES or not isinstance(node.get("outcome"), str):
            raise ValueError("Malformed native trace status/outcome")
        entry = _identity(node, source_sha256)
        node_id = node["node_id"]
        if node_id in seen:
            raise ValueError("Duplicate native trace node identity")
        dependencies = node.get("dependencies")
        if (not isinstance(dependencies, list) or any(not isinstance(d, str) for d in dependencies)
                or len(dependencies) != len(set(dependencies))):
            raise ValueError("Malformed native trace dependencies")
        if not set(dependencies) <= seen:
            raise ValueError("Native trace dependency is missing, cyclic, or out of order")
        detail = node.get("detail", {})
        if not isinstance(detail, dict):
            raise ValueError("Native trace detail must be an object when present")
        references = set(_references(detail))
        if not references <= set(dependencies):
            raise ValueError("Native decision reference omitted from dependencies")
        if not references <= seen:
            raise ValueError("Native decision reference is missing or out of order")
        kinds[node["kind"]] += 1
        statuses[node["status"]] += 1
        expression_ids.add(entry["expression_id"])
        if node["status"] == "not_evaluated":
            skipped.append({**entry, "reason": detail.get("reason")})
        elif node["kind"] in {"branch", "selection_decision", "assertion"} or (
                node["kind"] == "binary" and detail.get("operator") in {"and", "or"}):
            decisions.append({**entry, "detail": deepcopy(detail),
                              **({"result": deepcopy(node["result"])} if "result" in node else {})})
        if node["status"] == "failed":
            failures.append({**entry, "code": detail.get("code"), "detail": deepcopy(detail)})
        if node["status"] == "discarded" and node["kind"] in {"emit", "closing"}:
            discarded.append(entry)
        seen.add(node_id)
    return {
        "format": "spl-observed-decisions/1",
        "trace_origin": "native_ir_interpreter",
        "source_sha256": source_sha256,
        "scope": "one invocation; observed native IR decisions and skips",
        "counts": {"observations": len(trace), "observed_ir_ids": len(expression_ids),
                   "decisions": len(decisions), "not_evaluated": len(skipped),
                   "failures": len(failures), "discarded_outputs": len(discarded),
                   "kinds": dict(sorted(kinds.items())), "statuses": dict(sorted(statuses.items()))},
        "decisions": decisions,
        "not_evaluated": skipped,
        "failures": failures,
        "discarded_outputs": discarded,
        "coverage_denominator": None,
        "emitted_target_coverage": {"status": "not_instrumented", "observations": None},
        "limitations": [
            "No percentage: unobserved source/IR decisions are not inventoried.",
            "Interpreter observations do not establish emitted-Lean branch or compiler line coverage.",
            "A skipped expression root does not enumerate its skipped descendants.",
            "Source hash is supplied by the caller; retain exact source bytes and linked dependency pins.",
            "IR IDs and spans are snapshot-local; linked/readable spans need their source mapping.",
        ],
    }
