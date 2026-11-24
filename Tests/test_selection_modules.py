"""Independent hand controls for registered scoped unique/fallback selections."""
import ast
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.r1 import build_modules as registration
from cases.selection import build_modules as selection_module
from spl_compiler.codecs import canonical, loads, read_json, write_json
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
from spl_compiler.modules import resolve_module, run_module_package, validate_module_package
from spl_compiler.run import normalize_target


def fixture(method="unique_no_fallback"):
    data = read_json(Path(selection_module.__file__).parent / "neutral.json")
    data["policy"]["method"] = method
    return data


def witnesses():
    """Amounts/errors are original hand controls, not another backend's output."""
    output = []
    for method in selection_module.METHODS:
        output.append((method + "-baseline", fixture(method), "20", "primary", None))
        data = fixture(method)
        data["rules"]["primary"]["enabled"] = False
        output.append((method + "-absent", data, None if method == "unique_no_fallback" else "10", None if method == "unique_no_fallback" else "fallback", "NO_APPLICABLE_RULE" if method == "unique_no_fallback" else None))
    data = fixture("unique_explicit_fallback")
    data["rules"]["primary"]["rate"] = "0"
    output.append(("selected-zero", data, "0", "primary", None))
    for method in ("unique_no_fallback", "priority_explicit_fallback"):
        data = fixture(method)
        data["rules"]["competing"]["enabled"] = True
        data["rules"]["primary"]["body_divisor"] = "0"
        output.append((method + "-ambiguous-before-body", data, None, None, "AMBIGUOUS_RULE"))
    data = fixture("priority_explicit_fallback")
    data["rules"]["unsafe"]["enabled"] = True
    output.append(("lazy-unselected-body", data, "20", "primary", None))
    data = fixture("priority_explicit_fallback")
    data["rules"]["unsafe"].update(enabled=True, predicate_divisor="0")
    output.append(("demanded-low-priority-predicate", data, None, None, "DIVISION_BY_ZERO"))
    data = fixture("unique_explicit_fallback")
    data["rules"]["primary"]["body_divisor"] = "0"
    output.append(("selected-body-failure", data, None, "primary", "DIVISION_BY_ZERO"))
    data = fixture("unique_explicit_fallback")
    data["fallback"]["body_divisor"] = "0"
    output.append(("lazy-unused-fallback", data, "20", "primary", None))
    data = fixture("unique_explicit_fallback")
    data["fallback"]["body_divisor"] = "0"
    data["rules"]["primary"]["enabled"] = False
    output.append(("demanded-fallback-failure", data, None, "fallback", "DIVISION_BY_ZERO"))
    for field, value, label in (("channel", "physical", "channel-near-miss"),
                                ("effective", {"start": "2026-05-02", "end": "2026-07-01"}, "effective-start-near-miss"),
                                ("effective", {"start": "2026-04-01", "end": "2026-05-01"}, "effective-end-near-miss"),
                                ("observed_at", "2026-07-03T00:00:00Z", "rule-cutoff-near-miss")):
        data = fixture()
        data["rules"]["primary"][field] = value
        output.append((label, data, None, None, "NO_APPLICABLE_RULE"))
    data = fixture()
    data["evidence"][1]["approved"] = False
    output.append(("source-evidence-authority-failure", data, None, None, "SELECTION_RULE_AUTHORITY"))
    return output


class SelectionModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/selection-module-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/selection"
        cls.folder.mkdir(parents=True)
        original = Path(selection_module.__file__).parent
        for name in ("selection.spl", "neutral.json", "policy.md"):
            shutil.copyfile(original / name, cls.folder / name)
        for owner, name, value in ((selection_module, "ROOT", cls.root), (selection_module, "FOLDER", cls.folder), (registration, "ROOT", cls.root)):
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.references = {method: selection_module.register_selection(method) for method in selection_module.METHODS}

    def package(self, data):
        return selection_module.selection_package(data, reference=self.references[data["policy"]["method"]])

    def run_reference(self, data):
        return run_module_package(self.package(data), self.root, backend="reference")

    def controls(self, result, data, amount, rule, code):
        self.assertEqual([row["code"] for row in result["diagnostics"]], [code] if code else [], result)
        self.assertEqual(result["closing_state"], [])
        if code:
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["results"], {})
            self.assertEqual(result["statements"], [])
            self.assertNotIn("result_digest", result)
        else:
            self.assertEqual(result["status"], "calculated")
            self.assertEqual(Fraction(result["results"]["statement"]["earned"]), Fraction(amount))
            detail = result["results"]["selection_detail"]
            self.assertEqual(detail["rule_id"], rule)
            self.assertEqual(detail["module_id"], "synthetic:selection-" + data["policy"]["method"])
            self.assertEqual(detail["receipt_source"], data["receipt"]["source_ref"])
            original = data["fallback"] if rule == "fallback" else data["rules"][rule]
            self.assertEqual(detail["rule_source"], original["source_ref"])
            self.assertEqual(detail["rule_evidence"], original["evidence_ref"])

    def test_original_hand_matrix_reference(self):
        for label, data, amount, rule, code in witnesses():
            with self.subTest(label=label):
                self.controls(self.run_reference(data), data, amount, rule, code)

    def test_one_field_rule_scope_effective_and_observation_near_misses(self):
        changes = [("agreement_id", "different-agreement"), ("asset_id", "different-title"), ("channel", "physical"),
                   ("effective", {"start": "2026-05-02", "end": "2026-07-01"}),
                   ("effective", {"start": "2026-04-01", "end": "2026-05-01"}),
                   ("observed_at", "2026-07-03T00:00:00Z")]
        for field, value in changes:
            data = fixture()
            data["rules"]["primary"][field] = value
            code = "MODULE_REFERENCE_SCOPE" if field in ("agreement_id", "asset_id") else "NO_APPLICABLE_RULE"
            with self.subTest(field=field, value=value):
                result = self.run_reference(data)
                self.controls(result, data, None, None, code)
                if code == "MODULE_REFERENCE_SCOPE":
                    self.assertEqual(result["trace"], [])
            data["policy"]["method"] = "unique_explicit_fallback"
            if code == "MODULE_REFERENCE_SCOPE":
                self.controls(self.run_reference(data), data, None, None, code)
            else:
                self.controls(self.run_reference(data), data, "10", "fallback", None)
        data = fixture()
        data["rules"]["primary"]["effective"]["start"] = data["receipt"]["effective_date"]
        self.controls(self.run_reference(data), data, "20", "primary", None)

    def test_canonical_evidence_and_scope_rejections_report_actual_stage(self):
        data = fixture()
        data["receipt"]["agreement_id"] = "outside-agreement"
        result = self.run_reference(data)
        self.controls(result, data, None, None, "MODULE_REFERENCE_SCOPE")
        self.assertEqual(result["trace"], [])
        data = fixture()
        data["receipt"]["asset_id"] = "outside-title"
        result = self.run_reference(data)
        self.controls(result, data, None, None, "MODULE_REFERENCE_SCOPE")
        self.assertEqual(result["trace"], [])
        data = fixture()
        data["evidence"][1]["agreement_id"] = "outside-agreement"
        result = self.run_reference(data)
        self.controls(result, data, None, None, "MODULE_REFERENCE_SCOPE")
        self.assertEqual(result["trace"], [])
        data = fixture()
        data["evidence"][1]["authority_rule_id"] = "competing"
        self.controls(self.run_reference(data), data, None, None, "SELECTION_RULE_AUTHORITY")
        data = fixture()
        data["evidence"][1]["observed_at"] = data["cutoff"]
        result = self.run_reference(data)
        self.controls(result, data, None, None, "EVIDENCE_AFTER_CUTOFF")
        self.assertEqual(result["trace"], [])
        package = self.package(fixture())
        package["evidence"]["evidence"][1]["approval_ref"] = "unknown-authority"
        result = run_module_package(package, self.root, backend="reference")
        self.controls(result, fixture(), None, None, "MODULE_EVIDENCE_AUTHORITY")
        self.assertEqual(result["trace"], [])

    def test_zero_empty_and_strict_receipt_boundaries(self):
        data = fixture()
        data["receipt"]["amount"] = "0"
        self.controls(self.run_reference(data), data, "0", "primary", None)
        data = fixture()
        data["evidence"] = []
        self.controls(self.run_reference(data), data, None, None, "MODULE_EVIDENCE_REQUIRED")
        data = fixture()
        data["receipt"]["observed_at"] = data["cutoff"]
        self.controls(self.run_reference(data), data, None, None, "SELECTION_RECEIPT_CUTOFF")
        data["receipt"]["observed_at"] = "2026-07-02T23:59:59.999999999999Z"
        self.controls(self.run_reference(data), data, "20", "primary", None)

    def test_named_descriptor_methods_cannot_be_silently_switched(self):
        package = self.package(fixture())
        package["parameters"]["method"] = "unique_explicit_fallback"
        result = run_module_package(package, self.root, backend="reference")
        self.controls(result, fixture(), None, None, "MODULE_PARAMETER_DOMAIN")
        self.assertEqual(len({reference["id"] for reference in self.references.values()}), 3)

    def test_adapter_has_no_selection_or_financial_answer_projection(self):
        path = Path(selection_module.__file__)
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("oracles", source)
        syntax = ast.parse(source)
        calls = {node.func.id for node in ast.walk(syntax) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & {"evaluate", "sum", "filter", "max", "min"})
        original = fixture()
        package = self.package(original)
        self.assertEqual(package["inputs"]["unsafe"]["body_divisor"], "0")
        self.assertEqual(package["inputs"]["primary"]["agreement_id"], original["rules"]["primary"]["agreement_id"])
        self.assertNotIn("selected_rule_id", canonical(package))


class NativeSelectionModuleTests(SelectionModuleTests):
    # Inherit source setup, not the reference test methods, via the loader below.
    def test_native_ir_emitted_and_python_emitter_hand_controls(self):
        work = self.root / "native"
        work.mkdir()
        source = self.folder / "selection.spl"
        target = compile_schedule(source, work / "Settlement.lean")
        for index, (label, data, amount, rule, code) in enumerate(witnesses()):
            with self.subTest(label=label):
                package = self.package(data)
                checked, inputs, openings = validate_module_package(package, resolve_module(package["module_ref"], self.root))
                bindings = work / (str(index) + "-bindings.json")
                write_json(bindings, {"inputs": inputs, "openings": openings})
                reference = normalize_target(evaluate(checked, inputs, openings).to_dict())
                interpreted = normalize_target(interpret_schedule(source, bindings))
                emitted = normalize_target(loads(lean(["--run", target, bindings])))
                for observed in (reference, interpreted, emitted):
                    self.assertEqual([row["code"] for row in observed["diagnostics"]], [code] if code else [])
                    self.assertEqual(observed["status"], "blocked" if code else "calculated")
                    self.assertEqual(observed["closing"], {})
                    if code:
                        self.assertEqual(observed["emissions"], {})
                    else:
                        self.assertEqual(Fraction(observed["emissions"]["statement"]["earned"]), Fraction(amount))
                        self.assertEqual(observed["emissions"]["selection_detail"]["rule_id"], rule)
                for field in ("status", "emissions", "closing"):
                    self.assertEqual(canonical(reference[field]), canonical(interpreted[field]))
                    self.assertEqual(canonical(reference[field]), canonical(emitted[field]))
                selections = [node for node in interpreted["trace"] if node["kind"] == "selection"]
                if not selections:
                    self.assertEqual(code, "SELECTION_RULE_AUTHORITY")
                    continue
                selection = selections[-1]
                detail = selection["detail"]
                self.assertTrue(selection["source_span"]["stop"] > selection["source_span"]["start"])
                if rule:
                    self.assertEqual(detail["selected_rule_id"], rule)
                if "ambiguous" in label or "demanded-low" in label:
                    span = selection["source_span"]
                    body_nodes = [node for node in interpreted["trace"] if node["kind"] == "record"
                                  and span["start"] <= node["source_span"]["start"] < node["source_span"]["stop"] <= span["stop"]]
                    self.assertGreaterEqual(len(body_nodes), 3)
                    self.assertTrue(all(node["status"] == "not_evaluated" for node in body_nodes))
                if "demanded-low" in label:
                    self.assertEqual(detail["failed_rule_id"], "unsafe")
                if label in ("selected-zero", "selected-body-failure"):
                    mirror = work / (str(index) + "-PythonEmitter.lean")
                    mirror.write_text(emit_module(checked, {key: decode_value(value, checked.types[key]) for key, value in inputs.items()}, {}), encoding="utf-8")
                    mirror_result = normalize_target(loads(lean(["--run", mirror])))
                    for field in ("status", "emissions", "closing"):
                        self.assertEqual(canonical(reference[field]), canonical(mirror_result[field]))
                    self.assertEqual([row["code"] for row in mirror_result["diagnostics"]], [code] if code else [])

    def test_canonical_native_finalization_and_preflight_stage(self):
        names = {"unique_no_fallback-baseline", "unique_explicit_fallback-absent", "selected-zero", "priority_explicit_fallback-ambiguous-before-body",
                 "demanded-low-priority-predicate", "selected-body-failure", "channel-near-miss", "effective-end-near-miss", "source-evidence-authority-failure"}
        selected = [row for row in witnesses() if row[0] in names]
        for label, data, amount, rule, code in selected:
            with self.subTest(label=label):
                result = run_module_package(self.package(data), self.root)
                self.controls(result, data, amount, rule, code)
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")
                if not code:
                    self.assertTrue(result["verification"]["reference_agrees"])
        data = fixture()
        data["receipt"]["agreement_id"] = "outside-agreement"
        result = run_module_package(self.package(data), self.root)
        self.controls(result, data, None, None, "MODULE_REFERENCE_SCOPE")
        self.assertEqual(result["trace"], [])


def load_tests(loader, tests, pattern):
    suite = loader.loadTestsFromTestCase(SelectionModuleTests)
    suite.addTest(NativeSelectionModuleTests("test_native_ir_emitted_and_python_emitter_hand_controls"))
    suite.addTest(NativeSelectionModuleTests("test_canonical_native_finalization_and_preflight_stage"))
    return suite


if __name__ == "__main__":
    unittest.main()
