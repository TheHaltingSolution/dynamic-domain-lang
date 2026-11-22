"""Readable source, whole-program IR, emitted execution and native audit checks."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from spl_compiler.codecs import canonical, read_json, loads, write_json
from spl_compiler.fixtures import sv_package, lg_package
from spl_compiler.run import ROOT, bind_package, run_package, project, normalize_target
from spl_compiler.checker import check_schedule
from spl_compiler.readable import parse_readable
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import compile_schedule, interpret_schedule, lean
from spl_compiler.adapter import rq07


class PipelineTests(unittest.TestCase):
    def run_case(self, package, path, output=None):
        return run_package(bind_package(package, path), path, artifact_dir=output)

    def assert_dag(self, result):
        self.assertEqual(result["trace_origin"], "native_ir_interpreter")
        self.assertEqual(result["trace_format"], "spl-trace-dag/0.1")
        seen = set()
        for node in result["trace"]:
            self.assertNotIn(node["node_id"], seen)
            self.assertTrue(set(node["dependencies"]) <= seen)
            self.assertIn("value_type", node)
            self.assertIn("outcome", node)
            def references(value):
                if isinstance(value, dict):
                    for key, child in value.items():
                        if key in {"predicate_node", "decision_node", "skipped_node"}:
                            self.assertIn(child, seen)
                        else:
                            references(child)
                elif isinstance(value, list):
                    for child in value:
                        references(child)
            references(node.get("detail", {}))
            seen.add(node["node_id"])
        self.assertTrue(seen)

    def test_readable_cases_all_three_backends_and_native_dag(self):
        cases = [(sv_package(), ROOT / "cases/sv/sv01-readable.spl", "18000"),
                 (lg_package(), ROOT / "cases/lg/lg01-readable.spl", "35"),
                 (rq07(ROOT / "cases/rq07/source", observed_at="2026-04-03T00:00:00Z", ingested_at="2026-11-20T00:00:00Z"),
                  ROOT / "cases/sv/rq07-readable.spl", "18000")]
        for package, path, payable in cases:
            with self.subTest(path=path):
                result = self.run_case(package, path)
                self.assertEqual(result["diagnostics"], [])
                self.assertEqual(result["statements"][0]["payable"], payable)
                self.assertEqual(result["source_format"], "spl-readable/0.1-dev")
                self.assert_dag(result)

    def test_typed_ir_artifact_is_complete_and_has_no_untyped_nodes(self):
        directory = ROOT / ".lake" / "pipeline-tests"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temp:
            result = self.run_case(sv_package(), ROOT / "cases/sv/sv01-readable.spl", temp)
            self.assertEqual(result["diagnostics"], [])
            ir = read_json(Path(temp) / "typed-ir.json")
            self.assertEqual(ir["format"], "spl-ir/0.1")
            nodes = []
            def walk(value):
                if isinstance(value, dict):
                    if "meta" in value:
                        self.assertIn("type", value["meta"])
                        self.assertIn("span", value["meta"])
                        nodes.append(value)
                    for child in value.values():
                        walk(child)
                elif isinstance(value, list):
                    for child in value:
                        walk(child)
            walk(ir)
            self.assertGreater(len(nodes), 50)
            self.assertEqual(len(nodes), len({n["meta"]["id"] for n in nodes}))
            self.assertTrue(any(n.get("kind") == "for_each" and "binder_type" in n for n in nodes))
            self.assertTrue(any(n["meta"].get("citation") == "SV-7-POOL-RECOVERY" for n in nodes))

    def test_calendar_quarter_wording_enforces_actual_boundaries(self):
        p = sv_package(start="2026-01-01", end="2026-07-01")
        result = self.run_case(p, ROOT / "cases/sv/sv01-readable.spl")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["diagnostics"][0]["code"], "READABLE_CALENDAR_QUARTER_REQUIRED")
        self.assertEqual(result["closing_state"], [])
        self.assertEqual(result["statements"], [])
        self.assert_dag(result)

    def test_readable_reference_only_debug_mode_has_distinct_nested_nodes(self):
        source = ROOT / "cases/sv/sv01-readable.spl"
        r = run_package(bind_package(sv_package(), source), source, backend="reference")
        self.assertEqual(r["diagnostics"], [])
        self.assertEqual(r["statements"][0]["payable"], "18000")
        self.assertEqual(len(r["trace"]), len({n["node_id"] for n in r["trace"]}))

    def test_readable_parameter_and_method_changes_are_compositional(self):
        original = (ROOT / "cases/sv/sv01-readable.spl").read_text(encoding="utf-8")
        # These are deliberately new, unincorporated schedule variants. Reusing
        # the fixed SV policy identity after changing its method must be blocked.
        original = original.replace('Incorporate policy "sv-incurred@1".\n', '')
        variants = [(original.replace("25% of Cash Receipts", "30% of Cash Receipts"), "17000"),
                    (original.replace("Net Profits are Cash Receipts less Distribution Fee less Allowed Deductions",
                                      "Net Profits are Cash Receipts less Allowed Deductions"), "23000")]
        work = ROOT / ".lake" / "pipeline-tests"
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as temporary:
            for i, (source, expected) in enumerate(variants):
                path = Path(temporary) / f"variant-{i}.spl"
                path.write_text(source, encoding="utf-8", newline="\n")
                inputs, openings, *_ = project(sv_package(scenario=f"READABLE-VARIANT-{i}"))
                checked = check_schedule(parse_readable(source, path.name))
                reference = evaluate(checked, inputs, openings).to_dict()
                bindings = Path(temporary) / f"bindings-{i}.json"
                write_json(bindings, {"inputs": inputs, "openings": {"prepayment": next(iter(openings.values()))}})
                interpreted = normalize_target(interpret_schedule(path, bindings))
                target = compile_schedule(path, Path(temporary) / f"Settlement-{i}.lean")
                emitted = normalize_target(loads(lean(["--run", target, bindings])))
                for result in [reference, interpreted, emitted]:
                    self.assertEqual(result["diagnostics"], [])
                    self.assertEqual(result["emissions"]["pool"]["payable"], expected)

    def test_native_trace_is_invariant_to_unordered_source_permutation(self):
        p = sv_package()
        path = ROOT / "cases/sv/sv01-readable.spl"
        first = self.run_case(p, path)
        changed = deepcopy(p)
        changed["financial_facts"].reverse()
        changed["evidence_events"].reverse()
        changed["manifest"]["run_id"] = "second-invocation"
        second = self.run_case(changed, path)
        self.assertEqual(first["diagnostics"], [])
        self.assertEqual(second["diagnostics"], [])
        self.assertEqual(first["semantic_run_digest"], second["semantic_run_digest"])
        self.assertEqual(canonical(first["trace"]), canonical(second["trace"]))


if __name__ == "__main__":
    unittest.main()
