"""Registered staged deductions against independent original-fact controls.

Native-named methods request compare mode explicitly. Other invalid-input
groups exercise the reference canonical boundary and identify that scope.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.deductions import build_modules as deductions
from cases.r1 import build_modules as registration
from oracles.staged_deductions import DeductionOracleError, _instant as independent_instant, exact_json, staged_deductions
from spl_compiler.codecs import digest, exact, read_json, write_json
from spl_compiler.lean_tools import ROOT
from Tests.test_deduction_oracle import fixture, successor


class DeductionModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT / ".lake" / "deduction-module-tests"
        directory.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=directory)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/deductions"
        cls.folder.mkdir(parents=True)
        for name in ["stages.spl", "deductions.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/deductions" / name, cls.folder / name)
        for owner, name, value in [(deductions, "ROOT", cls.root), (deductions, "FOLDER", cls.folder),
                                   (registration, "ROOT", cls.root)]:
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = deductions.register_deductions()

    def run_fixture(self, data, backend="reference", *, cells=None, output=None):
        package = deductions.deduction_package(data, reference=self.reference, state_cells=cells)
        return deductions.run_deduction_package(package, self.root, backend=backend, artifact_dir=output)

    def same(self, actual, expected):
        if isinstance(expected, Fraction) or type(expected) is int:
            self.assertEqual(actual if type(actual) is int else exact(actual), expected)
        elif isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key, value in expected.items():
                with self.subTest(field=key):
                    self.same(actual[key], value)
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for observed, wanted in zip(actual, expected):
                self.same(observed, wanted)
        elif isinstance(expected, str) and len(expected) > 10 and expected[10] in "Tt" and expected[:4].isdigit():
            # Typed Instant transport normalizes offset spellings to UTC. Use
            # the independent exact chronology control, not string spelling.
            self.assertEqual(independent_instant(actual), independent_instant(expected))
        else:
            self.assertEqual(actual, expected)

    def controls(self, data, result):
        expected = staged_deductions(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        self.same(result["results"]["comparison"], {key: value for key, value in expected.items()
                                                   if key not in {"cost_lines", "closing_state"}})
        self.same(result["results"]["cost_lines"], expected["cost_lines"])
        self.assertTrue(result["results"]["reconciliation"])
        self.same(deductions.neutral_state(result["closing_state"][0]["quantity"]), exact_json(expected["closing_state"]))
        self.assertEqual(result["issuance_status"], "unissued")
        return expected

    def blocked(self, data, code=None, backend="reference", *, cells=None):
        with self.assertRaises(DeductionOracleError):
            staged_deductions(data)
        result = self.run_fixture(data, backend, cells=cells)
        self.assertEqual(result["status"], "blocked", result.get("diagnostics"))
        self.assertTrue(result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code, result["diagnostics"])
        for field in ["results", "statements", "detail", "closing_state"]:
            self.assertFalse(result[field], field)
        return result

    def carried(self, previous_data, previous, costs=("30",), quarter=2):
        data = successor(staged_deductions(previous_data), costs=costs, quarter=quarter)
        # Canonical carry consumes the actual serialized closing cell, checked
        # against the independent oracle. Its actual semantic result reference
        # is separate from the original neutral case identity.
        path = self.root / f"actual-cost-state-q{quarter}.json"
        write_json(path, previous["closing_state"])
        cell = read_json(path)[0]
        cell.pop("movement")
        data["opening_state"] = deductions.neutral_state(cell["quantity"])
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        data["prior_result"]["result_ref"] = cell["prior_result_ref"]
        if quarter == 3:
            data["evidence"].append(deepcopy(previous_data["evidence"][-1]))
        return data, [cell]

    def test_native_six_explicit_stage_base_variants_all_intermediates(self):
        expected_earned = {"pre_basis_gross_fee": "320", "pre_basis_net_fee": "360",
                           "pre_share_gross_fee": "320", "pre_share_net_fee": "320",
                           "post_share_gross_fee": "220", "post_share_net_fee": "220"}
        for variant, earned in expected_earned.items():
            with self.subTest(variant=variant), tempfile.TemporaryDirectory(dir=self.root) as output:
                data = fixture(variant=variant, fee_rate="0.1")
                result = self.run_fixture(data, "compare", output=output)
                self.controls(data, result)
                self.assertEqual(result["results"]["comparison"]["earned"], earned)
                self.assertTrue(result["verification"]["reference_agrees"])
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")
                self.assertTrue((Path(output) / "Settlement.lean").is_file())
                self.assertTrue((Path(output) / "typed-ir.json").is_file())
                self.assertEqual(result["result_digest"], digest({key: value for key, value in result.items() if key != "result_digest"}))

    def test_native_cost_stage_400_300_and_gross_net_view_44_5_45(self):
        for variant, earned in [("pre_share_net_fee", "400"), ("post_share_net_fee", "300")]:
            data = fixture(variant=variant)
            result = self.run_fixture(data, "compare")
            self.controls(data, result)
            self.assertEqual(result["results"]["comparison"]["earned"], earned)
        for variant, earned in [("pre_share_gross_fee", "44.5"), ("pre_share_net_fee", "45")]:
            data = fixture(variant=variant, fee_rate="0.1", costs=())
            data["terms"]["share"] = "0.5"
            data["receipts"][0].update(gross_amount="110", net_amount="100")
            result = self.run_fixture(data, "compare")
            self.controls(data, result)
            self.assertEqual(result["results"]["comparison"]["earned"], earned)

    def test_native_three_period_actual_cell_cap_carry_preserves_original_costs(self):
        first_data = fixture(cap="100", costs=("80",))
        first = self.run_fixture(first_data, "compare")
        self.controls(first_data, first)
        second_data, cells = self.carried(first_data, first)
        second = self.run_fixture(second_data, "compare", cells=cells)
        self.controls(second_data, second)
        third_data, cells = self.carried(second_data, second, costs=("5",), quarter=3)
        third = self.run_fixture(third_data, "compare", cells=cells)
        self.controls(third_data, third)
        self.assertEqual([r["results"]["comparison"]["closing_cap_consumed"] for r in (first, second, third)], ["80", "100", "100"])
        self.assertEqual([r["results"]["comparison"]["admitted_deduction"] for r in (first, second, third)], ["80", "20", "0"])
        self.assertEqual([(row["amount"], row["deducted"], row["disposition"]) for row in deductions.neutral_state(third["closing_state"][0]["quantity"])["cost_history"]],
                         [("80", "80", "eligible_full"), ("30", "20", "eligible_capped"), ("5", "0", "eligible_capped")])

    def test_native_sequence_priority_and_physical_permutation(self):
        data = fixture(cap="100", costs=("80", "80"))
        baseline = self.run_fixture(data)
        self.controls(data, baseline)
        data["costs"].reverse()
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(result["results"], baseline["results"])
        self.assertEqual([row["deducted"] for row in result["results"]["cost_lines"]], ["80", "20"])

    def test_native_financial_failures_scope_and_cutoff_are_atomic(self):
        variants = [
            (fixture(variant="pre_basis_net_fee", cap="2000", costs=("1100",)), "DEDUCTION_NEGATIVE_STAGE"),
            (fixture(variant="post_share_net_fee", costs=("900",)), "DEDUCTION_NEGATIVE_EARNINGS"),
        ]
        excluded = fixture(); excluded["costs"][-1]["scope"]["currency"] = "EUR"
        variants.append((excluded, "DEDUCTION_FACT_SCOPE"))
        cutoff = fixture(); cutoff["costs"][0]["observed_at"] = cutoff["cutoff"]
        variants.append((cutoff, "DEDUCTION_FACT_CUTOFF"))
        for data, code in variants:
            with self.subTest(code=code):
                result = self.blocked(data, code, "compare")
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_native_exact_fractional_money_and_submicrosecond_cutoff(self):
        data = fixture(costs=("1/7",))
        data["terms"].update(share="1/3", fee_rate="1/11")
        data["receipts"][0].update(gross_amount="1", net_amount="1")
        data["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        data["costs"][0]["observed_at"] = "2026-04-03T01:00:00.0000001+01:00"
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(exact(result["results"]["comparison"]["earned"]), Fraction(59, 231))

    def test_native_empty_zero_and_opaque_text_identities(self):
        data = fixture(costs=())
        data["receipts"], data["evidence"] = [], []
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(result["results"]["comparison"]["earned"], "0")
        data = fixture()
        data["costs"][0]["id"] = 'original / opaque: "é雪"'
        data["costs"][1]["id"] = "original:excluded:with:separators"
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(result["results"]["cost_lines"][0]["id"], data["costs"][0]["id"])

    def test_reference_original_cost_reuse_including_excluded_and_capped_is_blocked(self):
        for first_data, old_id in [(fixture(), "excluded-q1"), (fixture(cap="100", costs=("130",)), "cost-0")]:
            first = self.run_fixture(first_data)
            next_data, cells = self.carried(first_data, first)
            next_data["costs"][0]["id"] = old_id
            self.blocked(next_data, "DEDUCTION_COST_ALREADY_RECOGNIZED", cells=cells)

    def test_reference_optional_empty_evidence_never_authorizes_nonempty_facts(self):
        data = fixture()
        data["evidence"] = []
        self.blocked(data, "DEDUCTION_FACT_EVIDENCE")

    def test_reference_ordinary_carry_forbids_method_cap_scope_and_history_amendment(self):
        original = fixture(cap="100", costs=("80",))
        first = self.run_fixture(original)
        mutations = [lambda d: d["terms"].update(variant="pre_basis_net_fee"),
                     lambda d: d["terms"].update(cap="200"),
                     lambda d: d["opening_state"].update(purpose="advance"),
                     lambda d: d["opening_state"].update(cap_consumed="0"),
                     lambda d: d["prior_result"].update(source_case_id="other"),
                     lambda d: d["prior_result"]["period"].update(end="2026-03-31")]
        for mutate in mutations:
            data, cells = self.carried(original, first)
            mutate(data)
            self.blocked(data, cells=cells)
        data, cells = self.carried(original, first)
        data["opening_state"]["cap_consumed"] = "79"
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        # Even matching supplied summaries do not replace the actual cell.
        result = self.blocked(data, "DEDUCTION_OPENING_SNAPSHOT", cells=cells)
        self.assertFalse(result["closing_state"])

    def test_reference_all_selected_rows_and_history_validate_even_when_excluded(self):
        changes = [("DEDUCTION_DUPLICATE_ID", lambda d: d["costs"].append(deepcopy(d["costs"][0]))),
                   ("DEDUCTION_SEQUENCE_TIE", lambda d: d["costs"][1].update(sequence=1)),
                   ("DEDUCTION_NEGATIVE_MONEY", lambda d: d["costs"][-1].update(amount="-1")),
                   ("DEDUCTION_FACT_EVIDENCE", lambda d: d["costs"][-1].update(evidence_ref="missing")),
                   ("MODULE_REFERENCE_SCOPE", lambda d: d["costs"][-1]["scope"].update(pool_id="other")),
                   ("DEDUCTION_FACT_PERIOD", lambda d: d["costs"][-1].update(effective_date="2025-12-31")),
                   ("DEDUCTION_RECEIPT_VIEWS", lambda d: d["receipts"][0].update(net_amount="1001")),
                   ("DEDUCTION_CATEGORY_LIST", lambda d: d["terms"]["eligible_categories"].append("distribution"))]
        for code, mutate in changes:
            with self.subTest(code=code):
                data = fixture(); mutate(data)
                self.blocked(data, code)
        original = fixture()
        first = self.run_fixture(original)
        data, cells = self.carried(original, first)
        data["opening_state"]["cost_history"].append(deepcopy(data["opening_state"]["cost_history"][0]))
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        cells[0]["quantity"] = deductions._state(data["opening_state"])
        self.blocked(data, "DEDUCTION_DUPLICATE_ID", cells=cells)
        data, cells = self.carried(original, first)
        data["opening_state"]["cap_consumed"] = "499"
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        cells[0]["quantity"] = deductions._state(data["opening_state"])
        self.blocked(data, "DEDUCTION_CAP_HISTORY_RECONCILIATION", cells=cells)

    def test_reference_actual_predecessor_metadata_and_physical_exactness_are_required(self):
        original = fixture(); first = self.run_fixture(original)
        data, cells = self.carried(original, first)
        data["prior_result"].pop("result_ref")
        with self.assertRaisesRegex(ValueError, "DEDUCTION_CANONICAL_PREDECESSOR_REQUIRED"):
            self.run_fixture(data, cells=cells)
        data, cells = self.carried(original, first)
        cells[0]["prior_result_ref"] = "result@sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "DEDUCTION_CANONICAL_PREDECESSOR_MISMATCH"):
            self.run_fixture(data, cells=cells)
        for value in (0.8, True, "8e-1"):
            data = fixture(); data["terms"]["share"] = value
            with self.assertRaises(ValueError):
                self.run_fixture(data)
        for value in (True, "1"):
            data = fixture(); data["costs"][0]["sequence"] = value
            with self.assertRaisesRegex(ValueError, "DEDUCTION_COST_SEQUENCE"):
                self.run_fixture(data)


if __name__ == "__main__":
    unittest.main()
