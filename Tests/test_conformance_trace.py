"""Native observation evidence keeps source identity and coverage claims scoped."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from validation.trace_coverage import summarize_trace


SOURCE_HASH = "a" * 64


def node(ir_id, kind="literal", dependencies=None, status="evaluated", detail=None, **fields):
    identity = json.dumps(["Observed", ir_id, ir_id + 1, "result", "root", f"{kind}:ir:{ir_id}"], separators=(",", ":"))
    result = {
        "node_id": identity, "kind": kind, "rule_id": "result", "instance_scope": "root",
        "source_span": {"start": ir_id, "stop": ir_id + 1, "line": 1, "column": ir_id},
        "value_type": {"kind": "atom", "name": "Bool"},
        "status": status, "outcome": {"not_evaluated": "not_evaluated", "failed": "blocked",
                                      "discarded": "discarded"}.get(status, "calculated"),
        "dependencies": dependencies or [], "operands": [], "result": True,
    }
    if detail is not None:
        result["detail"] = detail
    result.update(fields)
    return result


class ConformanceTraceTests(unittest.TestCase):
    def test_source_qualification_and_observation_counts_without_denominator(self):
        predicate = node(0)
        skipped = node(1, "binary", [predicate["node_id"]], "not_evaluated", {"reason": "unselected_branch"})
        branch = node(2, "branch", [predicate["node_id"], skipped["node_id"]],
                      detail={"selected": "then", "skipped_node": skipped["node_id"]})
        trace = [predicate, skipped, branch]
        before = deepcopy(trace)
        report = summarize_trace(trace, SOURCE_HASH)
        self.assertEqual(trace, before)
        self.assertEqual(report["counts"]["decisions"], 1)
        self.assertEqual(report["counts"]["not_evaluated"], 1)
        self.assertEqual(report["decisions"][0]["source_span"], branch["source_span"])
        self.assertIsNone(report["coverage_denominator"])
        self.assertEqual(report["emitted_target_coverage"]["status"], "not_instrumented")
        other = summarize_trace(trace, "b" * 64)
        self.assertNotEqual(report["decisions"][0]["observation_id"], other["decisions"][0]["observation_id"])
        self.assertNotEqual(report["decisions"][0]["expression_id"], other["decisions"][0]["expression_id"])
        json.dumps(report)

    def test_selection_short_circuit_assertion_failure_and_discarded_output(self):
        predicate = node(0)
        selection = node(1, "selection_decision", [predicate["node_id"]], detail={
            "tie": True, "reason": "ambiguous_applicable_rules",
            "candidates": [{"predicate_node": predicate["node_id"], "applicable": True}]})
        short = node(2, "binary", detail={"operator": "and"}, result=False)
        assertion = node(3, "assertion", status="failed", detail={"code": "POLICY"}, result=False)
        discarded = node(4, "emit", status="discarded")
        report = summarize_trace([predicate, selection, short, assertion, discarded], SOURCE_HASH)
        self.assertEqual(report["counts"]["decisions"], 3)
        self.assertEqual(report["failures"][0]["code"], "POLICY")
        self.assertEqual(report["counts"]["discarded_outputs"], 1)
        self.assertTrue(report["decisions"][0]["detail"]["tie"])

    def test_rejects_malformed_hash_identity_dependencies_and_references(self):
        good = node(0)
        for value in ("", "A" * 64, "g" * 64, None):
            with self.subTest(hash=value), self.assertRaises(ValueError):
                summarize_trace([], value)
        bad_cases = [
            [good, good],
            [{**good, "node_id": "arbitrary"}],
            [{**good, "dependencies": ["missing"]}],
            [{**good, "source_span": {**good["source_span"], "stop": 7}}],
            [{**good, "instance_scope": "other"}],
            [good, node(1, "branch", detail={"skipped_node": good["node_id"]})],
            [good, node(1, "branch", [good["node_id"]], detail={"predicate_node": False})],
            [good, node(1, "branch", [good["node_id"], good["node_id"]])],
        ]
        for trace in bad_cases:
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                summarize_trace(trace, SOURCE_HASH)

    def test_empty_trace_has_no_observed_decisions(self):
        report = summarize_trace([], SOURCE_HASH)
        self.assertEqual(report["counts"]["observations"], 0)
        self.assertEqual(report["decisions"], [])
        self.assertIsNone(report["coverage_denominator"])

    def test_real_native_trace_keeps_branch_skip_and_atomic_failure(self):
        from spl_compiler.codecs import write_json
        from spl_compiler.lean_tools import ROOT, interpret_schedule

        header = 'schedule Observed language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'
        sources = [
            header + 'define result = if true then 0 else 1.0 / 0.0; emit "x" = result;}',
            header + 'emit "first" = 1; emit "second" = 1.0 / 0.0;}',
        ]
        work = ROOT / ".lake" / "conformance-trace-tests"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            directory = Path(temporary)
            bindings = directory / "bindings.json"
            write_json(bindings, {"inputs": {}, "openings": {}})
            reports = []
            for index, source in enumerate(sources):
                path = directory / f"case-{index}.spl"
                path.write_bytes(source.encode("utf-8"))
                result = interpret_schedule(path, bindings)
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")
                reports.append(summarize_trace(result["trace"], hashlib.sha256(path.read_bytes()).hexdigest()))
            self.assertEqual(reports[0]["decisions"][0]["detail"]["selected"], "then")
            self.assertEqual(reports[0]["counts"]["not_evaluated"], 1)
            self.assertEqual(reports[0]["failures"], [])
            self.assertEqual(reports[1]["failures"][0]["code"], "DIVISION_BY_ZERO")
            self.assertEqual(reports[1]["counts"]["discarded_outputs"], 1)


if __name__ == "__main__":
    unittest.main()
