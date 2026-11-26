"""Controls for financial expectations and for the mutation reporting harness."""
import ast
from copy import deepcopy
from pathlib import Path
import tempfile
import sys
import unittest

from validation.semantic_mutations import BACKENDS, POLICY, bindings, cases, classify, mutants, oracle, population, source


def completed(value):
    return {backend: {"execution": "completed", "observable": deepcopy(value)} for backend in BACKENDS}


class SemanticMutationTests(unittest.TestCase):
    def setUp(self):
        self.original = cases()[0]
        self.expected = oracle(self.original)
        self.baseline = completed(self.expected)
        self.mutants = {row["id"]: row for row in mutants()}

    def test_hand_stage_base_equality_and_state_intermediates(self):
        e = self.expected["emissions"]
        self.assertEqual(e, {"gross": "1000", "cost": "500", "fee_base": "1000", "fee": "100", "after_cost": "500",
                             "after_fee": "900", "pre_share": "400", "share_amount": "320", "eligible": True,
                             "unrounded_earned": "320", "earned": "320", "contribution_count": "2",
                             "original_ids": [row["id"] for row in self.original["receipts"]]})
        self.assertEqual(self.expected["closing"], {"balance": "370"})
        # Independently worked alternatives: net fee50 ->450*.8=360;
        # after-share gross fee100 ->500*.8-100=300.
        self.assertEqual((500 - 50) * 8 // 10, 360)
        self.assertEqual(500 * 8 // 10 - 100, 300)

    def test_original_below_and_tie_controls(self):
        outputs = [oracle(case) for case in cases()]
        below = outputs[1]
        self.assertEqual(below["emissions"]["fee"], "99.999")
        self.assertEqual(below["emissions"]["pre_share"], "399.991")
        self.assertEqual(below["emissions"]["share_amount"], "319.9928")
        self.assertFalse(below["emissions"]["eligible"])
        self.assertEqual((below["emissions"]["earned"], below["closing"]), ("0", {"balance": "50"}))
        self.assertEqual([output["emissions"]["earned"] for output in outputs[2:]], ["1", "1.02"])

    def test_second_phase_preserves_originals_and_adds_independent_boundary_controls(self):
        expanded = cases("strengthened")
        self.assertEqual(expanded[:4], cases())
        at, beyond = map(oracle, expanded[4:])
        self.assertEqual((at["emissions"]["fee"], at["emissions"]["pre_share"], at["emissions"]["earned"], at["closing"]),
                         ("200", "1300", "1040", {"balance": "1090"}))
        self.assertEqual((beyond["emissions"]["fee"], beyond["emissions"]["pre_share"], beyond["emissions"]["earned"], beyond["closing"]),
                         ("300", "2200", "1760", {"balance": "1810"}))
        self.assertEqual((3000 - 500 - 330) * 8 // 10, 1736)  # Previously uncovered mutant.

    def test_original_parent_identity_scope_and_completeness(self):
        for kind in ("alias", "scope", "missing_complete", "wrong_total"):
            bad = deepcopy(self.original)
            if kind == "alias": bad["receipts"][1]["source_ref"] = bad["receipts"][0]["source_ref"]
            if kind == "scope": bad["receipts"][0]["scope"]["pool_id"] = "foreign"
            if kind == "missing_complete": bad["population"]["complete"] = False
            if kind == "wrong_total": bad["population"]["gross_total"] = "2000"
            with self.assertRaises(ValueError): oracle(bad)

    def test_source_independent_oracle_and_finite_reproducible_population(self):
        self.assertEqual(population(), population())
        self.assertEqual(len(cases()), 4); self.assertEqual(len(mutants()), 12)
        tree = ast.parse((Path(__file__).resolve().parents[1] / "validation/semantic_mutations.py").read_text(encoding="utf-8"))
        imported = {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        imported |= {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertEqual(imported, {"copy", "decimal", "fractions", "hashlib", "re"})
        calls = [node.func.id for node in ast.walk(next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "oracle"))
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        self.assertFalse(set(calls) & {"source", "bindings", "parse", "evaluate"})
        self.assertEqual(bindings(self.original)["inputs"]["receipts"][0]["amount"], {"value": "600", "currency": "USD"})

    def test_wrong_oracle_cannot_turn_correct_source_into_financial_kill(self):
        wrong = deepcopy(self.expected); wrong["emissions"]["earned"] = "999"
        result = classify(self.mutants["fee-base-net"], wrong, self.baseline, self.baseline)
        self.assertEqual(result["classification"], "unexecuted")
        self.assertIn("baseline", result["reason"])

    def test_missing_backend_and_partial_mismatch_have_no_financial_credit(self):
        partial = completed(self.expected); del partial["python_emitted"]
        partial["reference"]["observable"]["emissions"]["earned"] = "360"
        result = classify(self.mutants["fee-base-net"], self.expected, self.baseline, partial)
        self.assertEqual(result["classification"], "unexecuted")
        self.assertIn("partial_observations", result)
        self.assertNotEqual(result["partial_observations"]["reference"]["observable"], self.expected)
        baseline = deepcopy(self.baseline); del baseline["native_ir"]
        self.assertEqual(classify(self.mutants["fee-base-net"], self.expected, baseline, completed(self.expected))["classification"], "unexecuted")

    def test_invalid_frontend_is_invalid_not_killed(self):
        result = classify(self.mutants["invalid-type"], self.expected, self.baseline, {},
                          validation={"status": "invalid", "stage": "reference_frontend", "reason": "TYPE_MISMATCH",
                                      "native_frontend_observation": {"status": "rejected", "execution": "process_failed", "command_id": "002", "diagnostic_codes": ["TYPE_MISMATCH"]}})
        self.assertEqual((result["classification"], result["stage"]), ("invalid", "frontend_consistency"))

    def test_invalid_reference_requires_actual_native_rejection_consistency(self):
        for native in ({}, {"status": "accepted", "execution": "completed"},
                       {"status": "incomplete", "execution": "timeout"}, {"status": "incomplete", "execution": "output_limit"},
                       {"status": "rejected", "execution": "unexecuted", "command_id": "fake", "diagnostic_codes": ["TYPE_MISMATCH"]},
                       {"status": "rejected", "execution": "process_failed", "command_id": "004", "diagnostic_codes": ["OUT_OF_MEMORY"]}):
            result = classify(self.mutants["invalid-type"], self.expected, self.baseline, {},
                              validation={"status": "invalid", "stage": "reference_frontend", "reason": "TYPE_MISMATCH", "native_frontend_observation": native})
            self.assertEqual(result["classification"], "unexecuted")
            self.assertIn(result["stage"], {"frontend_disagreement", "frontend_incomplete"})

    def test_equivalence_requires_pinned_algebraic_policy_not_equal_samples(self):
        item = self.mutants["commuted-exact-pre-stages"]
        self.assertEqual(classify(item, self.expected, self.baseline, completed(self.expected))["classification"], "equivalent")
        wrong = deepcopy(item); wrong["source"] += "\n// changed source pin"
        self.assertEqual(classify(wrong, self.expected, self.baseline, completed(self.expected))["classification"], "invalid")
        policy = deepcopy(POLICY); policy["intermediate_rounding"] = "cents"
        self.assertEqual(classify(item, self.expected, self.baseline, completed(self.expected), policy=policy)["classification"], "invalid")
        semantic = self.mutants["uncovered-high-gross-rate"]
        self.assertEqual(classify(semantic, self.expected, self.baseline, completed(self.expected))["classification"], "survived")

    def test_equivalence_contradiction_and_backend_disagreement_are_not_kills(self):
        changed = deepcopy(self.expected); changed["closing"]["balance"] = "0"
        result = classify(self.mutants["commuted-exact-pre-stages"], self.expected, self.baseline, completed(changed))
        self.assertEqual(result["classification"], "unexecuted")
        mixed = completed(self.expected); mixed["native_ir"]["observable"] = changed
        self.assertEqual(classify(self.mutants["drop-opening-state"], self.expected, self.baseline, mixed)["classification"], "unexecuted")

    def test_weak_final_only_comparison_misses_lost_state(self):
        changed = deepcopy(self.expected); changed["closing"]["balance"] = "320"
        result = classify(self.mutants["drop-opening-state"], self.expected, self.baseline, completed(changed))
        self.assertEqual(result["classification"], "killed")
        self.assertTrue(result["weak_final_only_survives"])
        self.assertEqual(result["differences"]["reference"], ["closing.balance"])

    def test_reserved_fx_and_quotes_remain_unexecuted(self):
        for identity in ("fx-conversion-reserved", "quote-selection-reserved"):
            result = classify(self.mutants[identity], self.expected, {}, {})
            self.assertEqual((result["classification"], result["stage"]), ("unexecuted", "reserved"))
            self.assertIsNone(self.mutants[identity]["source"])

    def test_reference_sources_match_independent_controls_and_named_mutations(self):
        from spl_compiler.checker import check_schedule
        from spl_compiler.evaluator import evaluate
        from spl_compiler.model import SPLException
        from spl_compiler.parser import parse
        from scripts.spl_mutation_campaign import observable
        programs = {}
        for item in [population()["baseline"], *mutants()]:
            if item["source"] is None: continue
            if item.get("kind") == "frontend_negative":
                with self.assertRaises(SPLException): check_schedule(parse(item["source"]))
            else: programs[item["id"]] = check_schedule(parse(item["source"]))
        expected_alternatives = {"fee-base-net": "360", "fee-after-share": "300", "strict-threshold": "0"}
        for case in cases():
            expected = oracle(case)
            baseline = observable(evaluate(programs["baseline"], **bindings(case)).to_dict())
            self.assertEqual(baseline, expected)
            equivalent = observable(evaluate(programs["commuted-exact-pre-stages"], **bindings(case)).to_dict())
            self.assertEqual(equivalent, expected)
        for identity, earned in expected_alternatives.items():
            actual = observable(evaluate(programs[identity], **bindings(self.original)).to_dict())
            self.assertEqual(actual["emissions"]["earned"], earned)
        high_rate = programs["uncovered-high-gross-rate"]
        self.assertEqual([observable(evaluate(high_rate, **bindings(case)).to_dict())["emissions"]["earned"]
                          for case in cases("strengthened")[4:]], ["1040", "1736"])

    def test_runner_fresh_output_and_reference_only_are_explicitly_partial(self):
        from scripts.spl_mutation_campaign import run_campaign
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new"
            report = run_campaign(output, mutant_ids=["drop-opening-state"], case_ids=[self.original["id"]], backends=("reference",))
            self.assertEqual(report["status"], "partial")
            self.assertEqual(report["classifications"], {"unexecuted": 1})
            self.assertEqual(report["processes_executed"], 0)
            with self.assertRaisesRegex(ValueError, "MUTATION_FRESH_OUTPUT_REQUIRED"):
                run_campaign(output)
            reserved = run_campaign(Path(temporary) / "reserved-only", mutant_ids=["fx-conversion-reserved"],
                                    case_ids=[self.original["id"]], backends=("reference",))
            self.assertEqual(reserved["status"], "partial")
            self.assertFalse(reserved["baseline_prerequisite_satisfied"])
            self.assertEqual(reserved["classification_count_unit"], "mutant_case_pair")
            self.assertEqual(reserved["distinct_mutant_summaries"][0]["summary"], "reserved_unexecuted")

    def test_capture_output_and_process_budgets_preserve_unexecuted_status(self):
        from scripts.spl_mutation_campaign import Processes
        with tempfile.TemporaryDirectory() as temporary:
            runner = Processes(Path(temporary), max_processes=1, max_bytes=1024)
            runner.exe = sys.executable
            result = runner.run(["-c", "print('x'*20000)"], "harness-output-limit")
            self.assertEqual(result["execution"], "output_limit")
            self.assertEqual((Path(temporary) / result["stdout"]).stat().st_size, 1024)
            self.assertEqual(runner.run(["-c", "print('must not execute')"], "harness-process-limit")["execution"], "unexecuted")

    def test_capture_timeout_is_incomplete_not_financial_failure(self):
        from scripts.spl_mutation_campaign import Processes
        with tempfile.TemporaryDirectory() as temporary:
            runner = Processes(Path(temporary), process_seconds=1, total_seconds=5)
            runner.exe = sys.executable
            result = runner.run(["-c", "import time;time.sleep(5)"], "harness-timeout")
            self.assertEqual(result["execution"], "timeout")


if __name__ == "__main__":
    unittest.main()
