"""Experimental archival transport: exact roundtrips and hostile envelopes."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import spl_trace_transport as transport
from spl_compiler.lean_tools import ROOT, interpret_schedule
from spl_compiler.run import normalize_target


def node(index, **fields):
    return {"node_id": "node-" + str(index),
            "dependencies": [] if index == 0 else ["node-" + str(index - 1)],
            "kind": "expression", "result": "0", **fields}


def repeated(count=8):
    value = [{"fact_id": "receipt-" + str(i), "amount": {"numerator": str(i), "denominator": "3"}}
             for i in range(24)]
    return [node(i, operands=[deepcopy(value), deepcopy(value)], result=deepcopy(value),
                 value_type={"kind": "List", "args": [{"kind": "Money", "currency": "USD"}]},
                 fact_ids=["receipt-" + str(i) for i in range(24)]) for i in range(count)]


class TraceTransportTests(unittest.TestCase):
    def rejects(self, function, value, code, limits=None):
        with self.assertRaisesRegex(transport.TransportError, "^" + code + "$"):
            function(value, limits) if limits else function(value)

    def test_repetition_shares_payloads_and_roundtrips_without_aliases(self):
        trace = repeated()
        packed = transport.pack(trace)
        self.assertTrue(packed["payloads"])
        self.assertLess(len(transport.canonical_json(packed)), len(transport.canonical_json(trace)))
        restored = transport.unpack(packed)
        self.assertEqual(restored, trace)
        self.assertEqual(packed["logical_sha256"], hashlib.sha256(transport.canonical_json(trace).encode("utf-8")).hexdigest())
        self.assertEqual(transport.pack(trace), packed)
        restored[0]["result"][0]["amount"]["numerator"] = "changed"
        self.assertEqual(restored[1]["result"][0]["amount"]["numerator"], "0")
        self.assertEqual(trace[0]["result"][0]["amount"]["numerator"], "0")
        self.assertEqual(transport.unpack(packed), trace)

    def test_opaque_values_null_options_duplicate_occurrences_and_ref_keys(self):
        trace = [node(0, result={"$ref": "not-a-transport-reference", "inline": {"shared": None},
                                 "numerator": 0, "denominator": 1},
                      operands=[{"some": "0"}, {"some": "0"}, {"none": None}],
                      detail=None, source_span=None, custom={"payloads": {"sha256": "anything"}},
                      lineage=["same-source", "same-source"], value_type={"args": [], "name": "Option"},
                      scope={"pool": "opaque", "period": None},
                      inline={"payloads": "user-data"}, shared={"result": "user-data"}),
                 node(1, dependencies=["node-0", "node-0"], result="0", status="discarded")]
        self.assertEqual(transport.unpack(transport.pack(trace)), trace)
        self.assertEqual(transport.unpack(transport.pack([])), [])

    def test_object_key_order_is_canonical_and_array_order_is_significant(self):
        first = [node(0, result={"b": 2, "a": 1})]
        second = [node(0, result={"a": 1, "b": 2})]
        self.assertEqual(transport.pack(first)["logical_sha256"], transport.pack(second)["logical_sha256"])
        first[0]["result"], second[0]["result"] = [1, 2], [2, 1]
        self.assertNotEqual(transport.pack(first)["logical_sha256"], transport.pack(second)["logical_sha256"])

    def test_actual_native_success_and_failure_prefix_raw_and_normalized(self):
        header = 'schedule Transport language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'
        bodies = [
            'define xs=[USD 0,USD 1/3.0,USD 1/3.0]; emit "xs"=xs; emit "zero"=USD 0;',
            'emit "before"=USD 0; emit "after"=USD 1/0.0;',
        ]
        with tempfile.TemporaryDirectory(prefix="trace-transport-", dir=ROOT / ".lake") as temporary:
            work = Path(temporary)
            source, bindings = work / "source.spl", work / "bindings.json"
            bindings.write_text('{"inputs":{},"openings":{}}', encoding="utf-8")
            for index, body in enumerate(bodies):
                with self.subTest(case=index):
                    source.write_text(header + body + "}", encoding="utf-8")
                    native = interpret_schedule(source, bindings)
                    self.assertEqual(native["status"], "calculated" if index == 0 else "blocked")
                    self.assertTrue(native["trace"])
                    for trace in (native["trace"], normalize_target(deepcopy(native))["trace"]):
                        packed = transport.pack(trace)
                        self.assertEqual(transport.unpack(transport.loads(transport.canonical_json(packed))), trace)
                        self.assertEqual(packed["node_count"], len(trace))
                    if index == 1:
                        self.assertTrue(any(n.get("status") == "discarded" for n in native["trace"]))
                        self.assertTrue(any(n.get("status") == "failed" for n in native["trace"]))
                        self.assertEqual(native["diagnostics"][0]["code"], "DIVISION_BY_ZERO")

    def test_dag_forward_missing_self_cycle_duplicate_ids_rejected(self):
        for trace, code in [
            ([node(0, dependencies=["missing"])], "INVALID_DAG_ORDER"),
            ([node(0, dependencies=["node-0"])], "INVALID_DAG_ORDER"),
            ([node(0, dependencies=["node-1"]), node(1)], "INVALID_DAG_ORDER"),
            ([node(0), node(0)], "DUPLICATE_NODE_ID"),
            ([node(0, dependencies="node-1")], "DEPENDENCIES_REQUIRED"),
            ([node(0, node_id="")], "NODE_ID_REQUIRED"),
        ]:
            self.rejects(transport.pack, trace, code)
        packed = transport.pack([node(0), node(1)])
        packed["nodes"][0]["inline"]["dependencies"] = ["node-1"]
        # Keep byte-size metadata consistent to reach independent DAG validation.
        changed = [node(0, dependencies=["node-1"]), node(1)]
        packed["expanded_bytes"] = len(transport.canonical_json(changed).encode("utf-8"))
        self.rejects(transport.unpack, packed, "INVALID_DAG_ORDER")

    def test_closed_envelope_unknown_versions_and_wrapper_fields(self):
        changes = [
            (lambda p: p.update(format="spl-trace-compact/99"), "UNSUPPORTED_FORMAT"),
            (lambda p: p.update(logical_format="unknown"), "UNSUPPORTED_FORMAT"),
            (lambda p: p.update(extra=None), "INVALID_ENVELOPE_FIELDS"),
            (lambda p: p.pop("expanded_bytes"), "INVALID_ENVELOPE_FIELDS"),
            (lambda p: p["nodes"][0].update(extra=None), "INVALID_NODE_WRAPPER"),
            (lambda p: p.update(node_count=True), "NODE_LIMIT"),
            (lambda p: p.update(node_count=2), "NODE_COUNT_MISMATCH"),
            (lambda p: p.update(logical_sha256="bad"), "INVALID_LOGICAL_HASH"),
            (lambda p: p.update(expanded_bytes=-1), "INVALID_EXPANDED_SIZE"),
        ]
        for change, code in changes:
            with self.subTest(code=code):
                packed = transport.pack([node(0)])
                change(packed)
                self.rejects(transport.unpack, packed, code)

    def test_payload_tamper_dangling_unused_hash_and_collision_guards(self):
        packed = transport.pack(repeated())
        reference = next(iter(packed["payloads"]))
        changed = deepcopy(packed)
        changed["payloads"][reference] = {"modified": True}
        self.rejects(transport.unpack, changed, "PAYLOAD_HASH_MISMATCH")
        changed = deepcopy(packed)
        del changed["payloads"][reference]
        self.rejects(transport.unpack, changed, "DANGLING_REFERENCE")
        changed = deepcopy(packed)
        value = {"unused": None}
        extra = hashlib.sha256(transport.canonical_json(value).encode("utf-8")).hexdigest()
        changed["payloads"][extra] = value
        self.rejects(transport.unpack, changed, "UNUSED_PAYLOAD")
        changed = deepcopy(packed)
        field = next(iter(changed["nodes"][0]["shared"]))
        changed["nodes"][0]["inline"][field] = None
        self.rejects(transport.unpack, changed, "OVERLAPPING_NODE_FIELDS")
        changed = deepcopy(packed)
        changed["nodes"][0]["shared"]["node_id"] = reference
        self.rejects(transport.unpack, changed, "OVERLAPPING_NODE_FIELDS")
        changed = deepcopy(packed)
        changed["nodes"][0]["shared"]["custom"] = reference
        self.rejects(transport.unpack, changed, "UNSUPPORTED_SHARED_FIELD")
        changed = deepcopy(packed)
        changed["payloads"]["not-a-hash"] = None
        self.rejects(transport.unpack, changed, "INVALID_PAYLOAD_REFERENCE")

    def test_inline_tamper_and_expanded_length_tamper(self):
        packed = transport.pack([node(0)])
        packed["nodes"][0]["inline"]["result"] = "1"
        self.rejects(transport.unpack, packed, "LOGICAL_HASH_MISMATCH")
        packed = transport.pack([node(0)])
        packed["expanded_bytes"] += 1
        self.rejects(transport.unpack, packed, "EXPANDED_SIZE_MISMATCH")

    def test_json_duplicate_keys_floats_constants_and_nonjson_values(self):
        for raw, code in [(b'{"x":1,"x":2}', "DUPLICATE_JSON_KEY"),
                          (b'{"outer":{"x":1,"x":2}}', "DUPLICATE_JSON_KEY"),
                          (b'[1.0]', "FLOAT_FORBIDDEN"), (b'[1e2]', "FLOAT_FORBIDDEN"),
                          (b'[NaN]', "FLOAT_FORBIDDEN"), (b'[Infinity]', "FLOAT_FORBIDDEN"),
                          (b'\xff', "INVALID_JSON_INPUT"), (b'{', "INVALID_JSON_INPUT")]:
            self.rejects(transport.loads, raw, code)
        for value in [1.0, float("nan"), (1, 2), b"bytes"]:
            self.rejects(transport.pack, [node(0, result=value)], "INVALID_JSON_VALUE")
        self.rejects(transport.pack, [node(0, result={1: "bad"})], "INVALID_JSON_KEY")
        cyclic = []
        cyclic.append(cyclic)
        self.rejects(transport.pack, [node(0, result=cyclic)], "CYCLIC_JSON_VALUE")

    def test_resource_node_depth_input_and_expanded_caps(self):
        self.rejects(transport.pack, [node(0), node(1)], "NODE_LIMIT", transport.Limits(max_nodes=1))
        packed = transport.pack([node(0), node(1)])
        self.rejects(transport.unpack, packed, "NODE_LIMIT", transport.Limits(max_nodes=1))
        self.rejects(transport.loads, b'[[[0]]]', "DEPTH_LIMIT", transport.Limits(max_depth=2))
        self.rejects(transport.loads, b'"long input"', "INPUT_BYTE_LIMIT", transport.Limits(max_input_bytes=4))
        self.rejects(transport.pack, [node(0)], "INPUT_BYTE_LIMIT", transport.Limits(max_input_bytes=10))
        self.rejects(transport.pack, [node(0)], "EXPANDED_BYTE_LIMIT", transport.Limits(max_expanded_bytes=10))
        self.rejects(transport.pack, [node(0, result=[[[0]]])], "DEPTH_LIMIT", transport.Limits(max_depth=4))
        # Brackets and escaped quotes in opaque strings do not count as nesting.
        self.assertEqual(transport.loads(b'["[[[\\\"[[["]', transport.Limits(max_depth=1)), ['[[["[[['])
        for fields in [{"max_nodes": 100001}, {"max_depth": 257}, {"max_input_bytes": 0}, {"max_nodes": True}]:
            with self.assertRaisesRegex(transport.TransportError, "^INVALID_LIMIT$"):
                transport.Limits(**fields)

    def test_unicode_escaping_and_nested_metadata_size_accounting(self):
        trace = [node(i, result={"字": ["café\n\"\\", "零" * 100], "number": -3, "valid": True},
                      **{"quote\"key": {"nested": [None, False]}}) for i in range(4)]
        packed = transport.pack(trace)
        expanded = transport.canonical_json(trace).encode("utf-8")
        self.assertEqual(packed["expanded_bytes"], len(expanded))
        self.assertEqual(transport.unpack(packed), trace)
        self.assertEqual(transport.loads(expanded), trace)

    def test_alias_amplification_rejected_before_payload_copy_even_if_size_lies(self):
        trace = repeated(30)
        packed = transport.pack(trace)
        compact_size = len(transport.canonical_json(packed).encode("utf-8"))
        self.assertLess(compact_size, packed["expanded_bytes"])
        limit = compact_size + 100
        limits = transport.Limits(max_input_bytes=compact_size + 1000, max_expanded_bytes=limit)
        with patch.object(transport, "deepcopy", side_effect=AssertionError("must not inflate")):
            self.rejects(transport.unpack, packed, "EXPANDED_BYTE_LIMIT", limits)
            packed["expanded_bytes"] = 2  # A dishonest header must not bypass actual size accounting.
            self.rejects(transport.unpack, packed, "EXPANDED_BYTE_LIMIT", limits)

    def test_cli_pack_unpack_and_validation_never_overwrites_destination(self):
        script = ROOT / "scripts" / "spl_trace_transport.py"
        with tempfile.TemporaryDirectory(prefix="trace-cli-") as temporary:
            work = Path(temporary)
            source, compact, restored = work / "trace.json", work / "compact.json", work / "restored.json"
            source.write_text(transport.canonical_json(repeated()), encoding="utf-8")
            for operation, incoming, outgoing in [("pack", source, compact), ("unpack", compact, restored)]:
                process = subprocess.run([sys.executable, str(script), operation, str(incoming), str(outgoing),
                                          "--max-nodes", "100", "--max-depth", "64",
                                          "--max-input-bytes", "1000000", "--max-expanded-bytes", "1000000"],
                                         capture_output=True, text=True, timeout=30)
                self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual(transport.loads(restored.read_bytes()), repeated())
            restored.write_bytes(b"existing-result")
            compact.write_text('{"format":"unknown"}', encoding="utf-8")
            process = subprocess.run([sys.executable, str(script), "unpack", str(compact), str(restored)],
                                     capture_output=True, text=True, timeout=30)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(restored.read_bytes(), b"existing-result")


if __name__ == "__main__":
    unittest.main()
