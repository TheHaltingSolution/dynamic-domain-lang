"""Keep the bounded conformance inventory tied to real requirement/test paths.

These checks validate the inventory, not the execution or completeness of its
witnesses. AST inspection avoids importing fixture builders during inventory.
"""
import ast
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/spl/feature-test-matrix.json"
STAGES = {"parser", "checker", "reference", "native_ir", "native_emitted",
          "python_emitted", "canonical", "state", "audit"}


class FeatureMatrixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))

    def test_schema_unique_ids_and_explicit_scope(self):
        self.assertEqual(self.matrix["format"], "spl-feature-test-matrix/1")
        self.assertTrue(self.matrix["scope"])
        self.assertTrue(self.matrix["limitations"])
        features = self.matrix["features"]
        self.assertTrue(features)
        self.assertEqual(len(features), len({row["id"] for row in features}))
        for row in features:
            with self.subTest(feature=row["id"]):
                self.assertRegex(row["id"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                self.assertTrue(row["description"])
                self.assertTrue(row["requirements"])
                self.assertTrue(row["limitations"])
                self.assertIn(row["status"], {"witnessed", "gap"})
                self.assertEqual(bool(row["witnesses"]), row["status"] == "witnessed")

    def test_requirement_ids_exist_in_current_ledger(self):
        ledger = (ROOT / "docs/spl/conformance-ledger.md").read_text(encoding="utf-8")
        known = set(re.findall(r"^\| ((?:[A-Z]\d{2}|C\d{2}))\b", ledger, re.MULTILINE))
        for row in self.matrix["features"]:
            for requirement in row["requirements"]:
                with self.subTest(feature=row["id"], requirement=requirement):
                    self.assertIn(requirement, known)

    def test_witness_selectors_and_input_paths_exist(self):
        for row in self.matrix["features"]:
            for witness in row["witnesses"]:
                with self.subTest(feature=row["id"], test=witness["test"]):
                    parts = witness["test"].split(".")
                    self.assertEqual(len(parts), 4)
                    self.assertEqual(parts[0], "Tests")
                    module = ROOT / parts[0] / (parts[1] + ".py")
                    tree = ast.parse(module.read_text(encoding="utf-8"))
                    classes = [node for node in tree.body
                               if isinstance(node, ast.ClassDef) and node.name == parts[2]]
                    self.assertEqual(len(classes), 1)
                    self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name == parts[3]
                                        for node in classes[0].body))
                    self.assertTrue(witness["stages"])
                    self.assertEqual(len(witness["stages"]), len(set(witness["stages"])))
                    self.assertLessEqual(set(witness["stages"]), STAGES)
                    self.assertTrue(witness["property"])
                    self.assertTrue(witness["oracle"])
                    self.assertTrue(witness["inputs"])
                    for filename in witness["inputs"]:
                        path = Path(filename)
                        self.assertFalse(path.is_absolute())
                        resolved = (ROOT / path).resolve()
                        self.assertTrue(resolved.is_relative_to(ROOT))
                        self.assertTrue(resolved.is_file(), filename)

    def test_required_initial_families_and_open_gaps_are_visible(self):
        identifiers = {row["id"] for row in self.matrix["features"]}
        self.assertLessEqual({"k1-priority", "k2-maps-relations", "k3-ordered-folds",
                              "m1a-tiers-caps-floor", "quantity-native",
                              "readable-sv-lg", "quest-half-even", "settlement-withholding-deferment",
                              "staged-deductions-caps", "fiscal-calendar-amended-terms",
                              "generated-decisions", "generated-rejection-layers",
                              "current-entitlement-cross-contract-transfer",
                              "original-rate-returns-loss-meters"}, identifiers)
        gaps = {requirement for row in self.matrix["features"] if row["status"] == "gap"
                for requirement in row["requirements"]}
        self.assertLessEqual({"C10", "C15", "U23", "A11"}, gaps)


if __name__ == "__main__":
    unittest.main()
