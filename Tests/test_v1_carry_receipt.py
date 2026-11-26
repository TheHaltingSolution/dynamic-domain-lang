"""V1 partial extraction validates skipped data; it never invents a result."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spl_compiler.artifacts import ArtifactPublication, PublicationError, load_completed_result
from spl_compiler.v1_carry import (_Reader, _load_v1_inline, load_completed_v1_carry_receipt,
                                   V1CarryReceipt, FORMAT)


def success():
    return {"status": "calculated", "manifest": {"mode": "final"}, "results": {"value": "1"},
            "closing_state": [{"quantity": {"literal": "1/3", "owner_context": "opaque"},
                               "prior_result_ref": "result@sha256:" + "1" * 64, "movement": {"ignored": True}}],
            "trace_origin": "native_ir_interpreter", "trace": [
                {"node_id": "n0", "dependencies": [], "result": {"predicate_node": "ordinary"}},
                {"node_id": "n1", "dependencies": ["n0"], "detail": {"predicate_node": "n0"}}]}


class V1CarryReceiptTests(unittest.TestCase):
    def test_actual_v1_publication_matches_default_loader_and_preserves_cells(self):
        with tempfile.TemporaryDirectory() as folder:
            result = success()
            original = deepcopy(result)
            publication = ArtifactPublication(folder)
            publication.finish(result, {})
            receipt = load_completed_v1_carry_receipt(folder)
            self.assertIsInstance(receipt, V1CarryReceipt)
            report = receipt.to_dict()
            self.assertEqual(report["format"], FORMAT)
            self.assertNotIn("trace", report["selected_values"])
            self.assertEqual(report["trace_validation"]["node_count"], 2)
            self.assertEqual(report["trace_validation"]["validation"], "native_node_references")
            expected = [{key: value for key, value in cell.items() if key != "movement"} for cell in result["closing_state"]]
            self.assertEqual(receipt.opening_cells(), expected)
            changed = receipt.opening_cells(); changed[0]["quantity"]["literal"] = "changed"
            self.assertEqual(receipt.opening_cells(), expected)
            self.assertEqual(load_completed_result(folder), original)

    def test_every_skipped_object_rejects_duplicate_nonfinite_utf8_trailing_and_depth(self):
        bad = [b'{"status":"calculated","unused":{"a":1,"a":2}}',
               b'{"unused":[NaN]}', b'{"unused":1e999}', b'{"unused":"\xff"}',
               b'{"unused":"\\q"}', b'{"unused":"unterminated}', b'{} {}',
               b'{"unused":' + b'['*128 + b'0' + b']'*128 + b'}',
               b'{"unused":01}', b'{"unused":truex}', b'{"unused":[1,]}']
        for raw in bad:
            with self.subTest(raw=raw[:70]), self.assertRaises((PublicationError, ValueError)):
                _Reader(BytesIO(raw)).root()

    def test_chunk_boundaries_escapes_unicode_and_finite_metadata_are_exact(self):
        value = {"status": "calculated", "manifest": {"mode": "final", "finite_metadata": 1.25},
                 "closing_state": [], "unknown": "x"*65530 + '\\"\t\u00e9\U0001f3ac',
                 "trace": [], "trace_origin": "independent_reference_evaluator"}
        reader = _Reader(BytesIO(json.dumps(value, ensure_ascii=False).encode()))
        selected, trace = reader.root()
        self.assertEqual(selected["manifest"], value["manifest"])
        self.assertEqual(trace["validation"], "complete_json_tokens_only")
        self.assertEqual(reader.bytes, len(json.dumps(value, ensure_ascii=False).encode()))

    def test_native_reference_fields_only_and_forward_duplicate_nodes_reject(self):
        baseline = success()
        for change in (lambda x: x["trace"][1].update(dependencies=["future"]),
                       lambda x: x["trace"][1].update(node_id="n0"),
                       lambda x: x["trace"][1].update(detail={"decision_node": "future"}),
                       lambda x: x["trace"][1].update(dependencies=[True])):
            value = deepcopy(baseline); change(value)
            with self.subTest(value=value), self.assertRaises(PublicationError):
                _Reader(BytesIO(json.dumps(value).encode())).root()
        selected, trace = _Reader(BytesIO(json.dumps(baseline).encode())).root()
        self.assertEqual(trace["node_count"], 2)

    def test_preview_blocked_and_wrong_manifest_mode_cannot_supply_openings(self):
        for status, mode in (("provisional", "preview"), ("blocked", "final"), ("calculated", "preview")):
            value = success(); value.update(status=status, manifest={"mode": mode})
            payload = json.dumps({"selected_values": value}).encode()
            with self.subTest(status=status, mode=mode), self.assertRaises(PublicationError):
                V1CarryReceipt(payload).opening_cells()

    def test_stale_missing_changed_unowned_manifest_entries_fail(self):
        for mode in ("running", "missing", "changed", "unowned"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                publication = ArtifactPublication(folder); publication.finish(success(), {})
                if mode == "running":
                    ArtifactPublication(folder)
                elif mode == "missing":
                    (publication.work / "result.json").unlink()
                elif mode == "changed":
                    with (publication.work / "result.json").open("ab") as f: f.write(b" ")
                else:
                    marker = Path(folder) / "completion.json"
                    value = json.loads(marker.read_bytes()); value["files"][0]["path"] = "../unowned"
                    marker.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(PublicationError):
                    _load_v1_inline(folder)

    def test_byte_and_node_budget_guards_are_explicit(self):
        import spl_compiler.v1_carry as module
        raw = json.dumps(success()).encode()
        with patch.object(module, "MAX_RESULT_BYTES", len(raw)-1):
            with self.assertRaisesRegex(PublicationError, "RESULT_LIMIT"):
                _Reader(BytesIO(raw)).root()
        with patch.object(module, "MAX_NODES", 1):
            with self.assertRaisesRegex(PublicationError, "NODE_LIMIT"):
                _Reader(BytesIO(raw)).root()

    def test_malformed_receipt_selected_status_and_cell_shapes_are_controlled(self):
        values = [[], {}, None, {"selected_values": []}, {"selected_values": None}]
        for status in ([], {}, None, True, 1, "unknown"):
            values.append({"selected_values": {"status": status, "closing_state": []}})
        for cells in (None, {}, "cells", [1]):
            values.append({"selected_values": {"status": "calculated", "closing_state": cells}})
        for value in values:
            with self.subTest(value=value), self.assertRaises(PublicationError):
                V1CarryReceipt(json.dumps(value).encode()).opening_cells()
