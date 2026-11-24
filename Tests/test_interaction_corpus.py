"""Actual finite interaction denominator and independent control checks."""
import ast
from itertools import product
from pathlib import Path
import tempfile
import unittest

from scripts.spl_conformance import run_generated
from spl_compiler.checker import check_schedule
from spl_compiler.evaluator import evaluate
from spl_compiler.parser import parse
from Tests.test_generated_conformance import observable
from validation.interaction_cases import (DOMAINS, SOURCE, case_for, coverage_contract,
                                           generate_interaction_cases, selected_cells)


class InteractionCorpusTests(unittest.TestCase):
    def test_exact_configuration_pair_and_financial_triple_denominators(self):
        contract = coverage_contract()
        self.assertEqual(contract['feasible_configurations'], 160)
        self.assertEqual(contract['required_pairs'], contract['covered_pairs'])
        self.assertEqual(contract['uncovered_pairs'], [])
        selected = selected_cells()
        self.assertEqual(len(selected), len(set(selected)))
        triples = {(m, s, sign) for m, s, sign, partition, path in selected
                   if partition == 'split' and path == 'safe'}
        self.assertEqual(triples, set(product(DOMAINS['mode'], DOMAINS['stage'], DOMAINS['sign'])))
        self.assertLessEqual(len(selected), 64)
        self.assertEqual(generate_interaction_cases(seed=7), generate_interaction_cases(seed=7))
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'validation/interaction_cases.py').read_text(encoding='utf-8'))
        imports = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name.startswith(('spl_compiler', 'oracles')) for name in imports))

    def test_reference_all_finite_cells_and_policy_conditional_relations(self):
        programs = {case['source']: check_schedule(parse(case['source'])) for case in generate_interaction_cases()}
        for case in generate_interaction_cases():
            with self.subTest(case=case['id']):
                self.assertEqual(observable(evaluate(programs[case['source']], **case['bindings']).to_dict()), case['expected'])
        for mode, stage, sign in product(DOMAINS['mode'], DOMAINS['stage'], DOMAINS['sign']):
            case = case_for((mode, stage, sign, 'split', 'safe'))
            checked = programs[case['source']]
            permuted = case_for((mode, stage, sign, 'split', 'safe'))
            permuted['bindings']['inputs']['amounts'].reverse()
            self.assertEqual(observable(evaluate(checked, **permuted['bindings']).to_dict()), case['expected'])
            if stage == 'aggregate':
                merged = case_for((mode, stage, sign, 'merged', 'safe'))
                self.assertEqual(merged['expected'], case['expected'])
        row_split = case_for(('half_even', 'row', 'positive', 'split', 'safe'))
        row_merged = case_for(('half_even', 'row', 'positive', 'merged', 'safe'))
        self.assertEqual(row_split['expected']['emissions']['selected'], '0')
        self.assertEqual(row_merged['expected']['emissions']['selected'], '0.01')
        # Splitting is deliberately not declared invariant for row rounding.
        self.assertNotEqual(row_split['expected'], row_merged['expected'])

    def test_native_ir_and_emitted_execute_every_selected_configuration(self):
        cases = generate_interaction_cases()
        with tempfile.TemporaryDirectory() as directory:
            results = run_generated(cases, Path(directory))
        self.assertEqual([row['status'] for row in results], ['passed'] * len(cases))


if __name__ == '__main__':
    unittest.main()
