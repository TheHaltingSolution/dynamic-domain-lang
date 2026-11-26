"""Small generated corpus with neutral controls, native IR and emitted Lean."""
import ast
import json
from pathlib import Path
import tempfile
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import loads, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target
from validation.generated_cases import generate_cases


def observable(result):
    result = normalize_target(result)
    return {"status": result["status"], "emissions": result["emissions"],
            "closing": result["closing"],
            "diagnostic_codes": [d["code"] for d in result["diagnostics"]]}


class GeneratedCorpusTests(unittest.TestCase):
    def test_seed_replay_and_explicit_boundaries(self):
        cases = generate_cases()
        self.assertEqual(cases, generate_cases())
        self.assertNotEqual(cases, generate_cases(seed=7))
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({case["id"] for case in cases}), 8)
        self.assertEqual(len({case["source"] for case in cases}), 1)
        self.assertEqual(json.loads(json.dumps(cases)), cases)
        self.assertEqual([c["expected"]["emissions"].get("reached") for c in cases[:3]],
                         [False, True, True])
        self.assertEqual([c["expected"]["emissions"].get("included") for c in cases[:3]],
                         [True, False, False])
        self.assertEqual(cases[1]["expected"]["emissions"]["rounded"], "1.01")
        self.assertEqual(cases[3]["expected"]["emissions"]["rounded"], "-1.01")
        self.assertEqual(cases[4]["expected"]["emissions"]["total"], "0")
        self.assertEqual(cases[5]["expected"]["emissions"]["total"],
                         {"numerator": "2", "denominator": "3"})

    def test_bounds_and_neutral_oracle_imports(self):
        for kwargs in ({"count": 7}, {"count": 65}, {"count": True},
                       {"seed": -1}, {"seed": 2 ** 32}, {"seed": False}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                generate_cases(**kwargs)
        path = ROOT / "validation" / "generated_cases.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports += [alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names]
        self.assertFalse(any(name and (name.startswith("spl_compiler") or name.startswith("oracles"))
                             for name in imports))

    def test_reference_matches_independent_controls(self):
        cases = generate_cases(seed=7, count=12)
        program = check_schedule(parse(cases[0]["source"]))
        for case in cases:
            with self.subTest(case=case["id"]):
                result = evaluate(program, **case["bindings"]).to_dict()
                self.assertEqual(observable(result), case["expected"])


class GeneratedNativeTests(unittest.TestCase):
    def test_generated_boundaries_reference_ir_and_emitted(self):
        cases = generate_cases()
        directory = ROOT / ".lake" / "generated-conformance-tests"
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            work = Path(temporary)
            schedule = work / "Source.spl"
            schedule.write_text(cases[0]["source"], encoding="utf-8", newline="\n")
            target = compile_schedule(schedule, work / "Settlement.lean")
            program = check_schedule(parse(cases[0]["source"]))
            for index, case in enumerate(cases):
                bindings = work / f"bindings-{index}.json"
                write_json(bindings, case["bindings"])
                outcomes = {
                    "reference": evaluate(program, **case["bindings"]).to_dict(),
                    "native_ir": interpret_schedule(schedule, bindings),
                    "native_emitted": loads(lean(["--run", target, bindings])),
                }
                for backend, actual in outcomes.items():
                    with self.subTest(case=case["id"], backend=backend):
                        self.assertEqual(observable(actual), case["expected"])


if __name__ == "__main__":
    unittest.main()
