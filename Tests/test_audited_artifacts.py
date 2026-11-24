"""V2 consistency/ownership controls; synthetic nodes grant no native credit."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spl_compiler import artifacts as old
from spl_compiler import audited_artifacts as audit
from spl_compiler.native_trace import iter_compact_nodes, read_compact
from spl_compiler.trace_transport import canonical_json, TransportError


def wire(path):
    literal = {"numerator": "business", "denominator": "literal", "owner_context": "opaque"}
    nodes = [{"node_id": "n0", "dependencies": [], "kind": "literal", "status": "evaluated", "result": literal},
             {"node_id": "n1", "dependencies": ["n0"], "kind": "emit", "status": "evaluated", "result": literal}]
    head = {"status": "calculated", "emissions": {"answer": literal}, "closing": {}, "diagnostics": [],
            "trace_origin": "native_ir_interpreter", "trace_format": "spl-trace-dag/0.1"}
    records = [{"record": "header", "format": "spl-native-trace-stream/0.2", "logical_format": "spl-trace-dag/0.1", "head": head},
               {"record": "payload", "id": "p0", "value": literal}]
    records += [{"record": "node", "inline": {k: v for k, v in node.items() if k not in {"result", "dependencies"}},
                 "shared": {"result": "p0"}, "dependencies": [] if index == 0 else [0]} for index, node in enumerate(nodes)]
    records += [{"record": "complete", "node_count": 2, "payload_count": 1,
                 "expanded_bytes": len(canonical_json(nodes).encode())}]
    path.write_bytes(b"".join(canonical_json(row).encode() + b"\n" for row in records))
    return nodes, head


def consumed(publication):
    result = {}
    for label, name in audit._CONSUMED.items():
        if label == "link_sha256":
            continue
        payload = (name + "\n").encode()
        (publication.work / name).write_bytes(payload)
        result[label] = sha256(payload).hexdigest()
    return result


class AuditedArtifactTests(unittest.TestCase):
    def complete(self, folder, status="calculated"):
        publication = audit.AuditedPublication(folder)
        nodes, head = wire(publication.work / "audit.native.jsonl")
        trace, observed = publication.attach(publication.work / "audit.native.jsonl", bindings=consumed(publication))
        self.assertEqual(observed, head)
        result = {"status": status, "statements": [head["emissions"]], "results": head["emissions"],
                  "detail": [], "closing_state": [], "reconciliation": {}, "trace": trace}
        publication.finish(result, {"trace.json": "trace", "statement.json": "statements"})
        return publication, result, nodes

    def test_full_sidecar_load_iterator_and_v1_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            _, result, nodes = self.complete(folder)
            self.assertEqual(audit.load_completed_audited_result(folder), result)
            self.assertEqual(list(audit.iter_audited_trace(folder)), nodes)
            with self.assertRaises(old.PublicationError):
                old.load_completed_result(folder)
            self.assertEqual(json.loads((Path(folder) / "trace.json").read_bytes()), result["trace"])

    def test_iterator_isolates_shared_payloads(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "wire"
            nodes, _ = wire(path)
            iterator = iter_compact_nodes(path)
            first = next(iterator)
            first["result"]["owner_context"] = "changed"
            self.assertEqual(next(iterator), nodes[1])
            self.assertEqual(list(iterator), [])

    def test_missing_completion_and_trailing_bytes_never_publish(self):
        for mutate in (lambda b: b.rsplit(b'\n', 2)[0] + b'\n', lambda b: b + b'{}\n'):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as folder:
                publication = audit.AuditedPublication(folder)
                path = publication.work / "audit.native.jsonl"
                wire(path)
                path.write_bytes(mutate(path.read_bytes()))
                with self.assertRaises(old.PublicationError):
                    publication.attach(path, bindings=consumed(publication))
                with self.assertRaises(old.PublicationError):
                    audit.load_completed_audited_result(folder)

    def test_tamper_cross_invocation_and_stale_rerun(self):
        with tempfile.TemporaryDirectory() as folder:
            previous, result, _ = self.complete(folder)
            following = audit.AuditedPublication(folder)
            with self.assertRaises(old.PublicationError):
                following.attach(previous.work / "audit.native.jsonl", bindings=consumed(following))
            with self.assertRaises(old.PublicationError):
                audit.load_completed_audited_result(folder)
            self.assertTrue((previous.work / "result.json").exists())
        with tempfile.TemporaryDirectory() as folder:
            publication, _, _ = self.complete(folder)
            path = publication.work / "audit.native.jsonl"
            path.write_bytes(path.read_bytes().replace(b'opaque', b'OPAQUE'))
            with self.assertRaises(old.PublicationError):
                audit.load_completed_audited_result(folder)

    def test_incomplete_only_empty_blocked_metadata(self):
        for status in ("calculated", "provisional", "blocked"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
                publication = audit.AuditedPublication(folder)
                value = {"status": status, "trace": audit.unavailable_trace("incomplete"), "results": {"amount": "1"}}
                with self.assertRaises(old.PublicationError):
                    publication.finish(value, {})
        with tempfile.TemporaryDirectory() as folder:
            publication = audit.AuditedPublication(folder)
            value = {"status": "blocked", "trace": audit.unavailable_trace(), "results": {}, "closing_state": []}
            publication.finish(value, {})
            self.assertEqual(audit.load_completed_audited_result(folder), value)

    def test_interruption_and_descriptor_mismatch_leave_running_marker(self):
        with tempfile.TemporaryDirectory() as folder:
            self.complete(folder)
            following = audit.AuditedPublication(folder)
            wire(following.work / "audit.native.jsonl")
            trace, _ = following.attach(following.work / "audit.native.jsonl", bindings=consumed(following))
            trace["node_count"] += 1
            with self.assertRaises(old.PublicationError):
                following.finish({"status": "calculated", "trace": trace}, {})
            with self.assertRaises(old.PublicationError):
                audit.load_completed_audited_result(folder)

    def test_postcommit_validation_failure_invalidates_direct_runner_return(self):
        with tempfile.TemporaryDirectory() as folder:
            publication = audit.AuditedPublication(folder)
            wire(publication.work / "audit.native.jsonl")
            trace, _ = publication.attach(publication.work / "audit.native.jsonl", bindings=consumed(publication))
            value = {"status": "calculated", "trace": trace, "statements": ["1"]}
            with patch.object(audit, "load_completed_audited_result", side_effect=old.PublicationError("late validation failed")):
                with self.assertRaises(old.PublicationError):
                    publication.finish(value, {})
            self.assertTrue((publication.work / "result.json").is_file(), "child actually committed before injected failure")
            self.assertEqual(json.loads((Path(folder) / "completion.json").read_bytes())["status"], "running")
            with self.assertRaises(old.PublicationError):
                audit.load_completed_audited_result(folder)

    def test_publication_cancel_after_actual_commit_is_nonconsumable(self):
        with tempfile.TemporaryDirectory() as folder:
            publication = audit.AuditedPublication(folder)
            wire(publication.work / "audit.native.jsonl")
            trace, _ = publication.attach(publication.work / "audit.native.jsonl", bindings=consumed(publication))
            with patch.object(audit, "load_completed_audited_result", side_effect=KeyboardInterrupt("cancel after child commit")):
                with self.assertRaises(KeyboardInterrupt):
                    publication.finish({"status": "calculated", "trace": trace, "statements": ["1"]}, {})
            with self.assertRaises(old.PublicationError):
                audit.load_completed_audited_result(folder)

    def test_unlisted_consumed_file_and_changed_consumed_bytes_rejected(self):
        for mode in ("unlisted", "changed"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                publication, _, _ = self.complete(folder)
                if mode == "changed":
                    (publication.work / "consumed.source.spl").write_bytes(b"changed")
                else:
                    marker = Path(folder) / "completion.json"
                    value = json.loads(marker.read_bytes())
                    value["files"] = [entry for entry in value["files"] if not entry["path"].endswith("/consumed.source.spl")]
                    marker.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(old.PublicationError):
                    audit.load_completed_audited_result(folder)


if __name__ == "__main__":
    unittest.main()
