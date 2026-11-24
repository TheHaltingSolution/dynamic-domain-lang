"""Independent decision cells and actual three-backend observation witnesses."""
import ast
from pathlib import Path
import tempfile
import unittest

from scripts.spl_conformance import run_generated
from spl_compiler.checker import check_schedule
from spl_compiler.evaluator import evaluate
from spl_compiler.parser import parse
from Tests.test_generated_conformance import observable
from validation.decision_cases import generate_decision_cases


class DecisionCorpusTests(unittest.TestCase):
    def test_finite_cells_and_independent_imports(self):
        cases = generate_decision_cases(seed=7)
        self.assertEqual(len(cases), 12)
        self.assertEqual(len({c["id"] for c in cases}), 12)
        self.assertEqual(len({c["source"] for c in cases}), 6)
        self.assertEqual(cases, generate_decision_cases(seed=7))
        tree = ast.parse((Path(__file__).resolve().parents[1] / "validation/decision_cases.py").read_text())
        self.assertFalse(any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(tree)))
        for seed in (-1, True, 2 ** 32):
            with self.assertRaises(ValueError):
                generate_decision_cases(seed=seed)

    def test_reference_agrees_with_hand_decision_table(self):
        for case in generate_decision_cases():
            with self.subTest(case=case["id"]):
                checked = check_schedule(parse(case["source"]))
                self.assertEqual(observable(evaluate(checked, **case["bindings"]).to_dict()), case["expected"])

    def test_native_ir_and_emitted_agree_and_expose_observed_outcomes(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            results = run_generated(generate_decision_cases(), output)
            self.assertEqual([row["status"] for row in results], ["passed"] * 12)
            reports = {row["id"]: json.loads((output / row["artifact"] / "native-ir-observations.json").read_text())
                       for row in results}
            self.assertTrue(any(d.get("detail", {}).get("selected") == "else"
                                for d in reports["decision-else"]["decisions"]))
            self.assertTrue(any(d["kind"] == "selection_decision"
                                for d in reports["decision-priority-zero"]["decisions"]))
            self.assertGreater(reports["decision-boolean-skips"]["counts"]["not_evaluated"], 0)
            self.assertGreater(reports["decision-or-demanded-discard"]["counts"]["discarded_outputs"], 0)


if __name__ == "__main__":
    unittest.main()
