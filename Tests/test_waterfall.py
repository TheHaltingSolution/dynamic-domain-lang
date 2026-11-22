"""Canonical C03/C07 composition against a neutral, independent financial oracle."""
from copy import deepcopy
from fractions import Fraction
import os
import re
import tempfile
import unittest

from cases.waterfall.build_modules import FOLDER, ROOT, register_waterfall, waterfall_package
from oracles.waterfall import OracleError, exact_json, waterfall
from spl_compiler.codecs import canonical, exact, read_json
from spl_compiler.modules import bind_module_package, run_module_package


def numeric_values(value):
    """Compare exact values while allowing decimal and reduced rational codecs."""
    if isinstance(value, str) and re.fullmatch(r"-?\d+(?:\.\d+|/[1-9]\d*)?", value):
        return Fraction(value)
    if isinstance(value, dict):
        return {key: numeric_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [numeric_values(item) for item in value]
    return value


class WaterfallTests(unittest.TestCase):
    backend = os.environ.get("SPL_WATERFALL_BACKEND", "compare")

    @classmethod
    def setUpClass(cls):
        cls.reference = register_waterfall()

    def fixture(self, name="roundlake-like-p1"):
        return read_json(FOLDER / (name + ".json"))

    def package(self, fixture):
        return waterfall_package(fixture, reference=self.reference)

    def run_package(self, package, output=None):
        return run_module_package(package, ROOT, backend=self.backend, artifact_dir=output)

    def calculate(self, fixture, package=None, output=None):
        result = self.run_package(package or self.package(fixture), output)
        self.assertEqual(result["diagnostics"], [], result)
        self.assertEqual(result["status"], "calculated", result)
        expected = exact_json(waterfall(fixture))
        for name in ["control", "claim_movements", "residual_lines"]:
            self.assertEqual(numeric_values(result["results"][name]), numeric_values(expected[name]), name)
        ledger = result["closing_state"][0]["quantity"]
        normalized = [{**row, "priority": int(row["priority"]), "sequence": int(row["sequence"]),
                       "principal": str(exact(row["principal"]["value"])), "balance": str(exact(row["balance"]["value"]))} for row in ledger]
        self.assertEqual(normalized, expected["claim_ledger"])
        self.assertEqual(len(result["statements"]), len(fixture["beneficiaries"]))
        self.assertEqual(sum(exact(row["payable"]) for row in result["statements"]), exact(expected["control"]["available_funds"]))
        self.assertEqual(len(result["module_closure"]), 2)
        return result

    def blocked(self, fixture, code):
        with self.assertRaises(OracleError):
            waterfall(fixture)
        result = self.run_package(self.package(fixture))
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        self.assertEqual(result["results"], {})
        self.assertEqual(result["statements"], [])
        self.assertEqual(result["closing_state"], [])

    def test_checked_in_independent_intermediate_controls(self):
        for name in ["roundlake-like-p1", "roundlake-like-p2", "priority-120", "pro-rata-120"]:
            with self.subTest(name=name):
                self.assertEqual(exact_json(waterfall(self.fixture(name))), read_json(FOLDER / (name + "-expected.json")))

    def test_competing_claim_methods_are_distinct(self):
        priority = self.calculate(self.fixture("priority-120"))
        proportional = self.calculate(self.fixture("pro-rata-120"))
        self.assertEqual([row["recovered"] for row in priority["results"]["claim_movements"]], ["100", "20"])
        self.assertEqual([row["recovered"] for row in proportional["results"]["claim_movements"]], ["60", "60"])
        self.assertNotEqual(priority["method_digest"], proportional["method_digest"])

    def test_pre_basis_fee_period_carry_and_residual_split(self):
        first = self.fixture()
        with tempfile.TemporaryDirectory() as output:
            initial = self.calculate(first, output=output)
            self.assertEqual(initial["results"]["control"]["fee"], "25")
            self.assertEqual([row["recovered"] for row in initial["results"]["claim_movements"]], ["48", "12"])
            self.assertEqual([row["closing_balance"] for row in initial["results"]["claim_movements"]], ["32", "8"])
            # Carry exactly the published serialized state, including source-result linkage.
            from pathlib import Path
            cells = read_json(Path(output) / "closing-state.json")
        second = self.fixture("roundlake-like-p2")
        package = self.package(second)
        package["state_cells"] = [{key: value for key, value in cell.items() if key != "movement"} for cell in cells]
        successor = self.calculate(second, bind_module_package(package, ROOT))
        self.assertEqual([row["recovered"] for row in successor["results"]["claim_movements"]], ["32", "8"])
        self.assertEqual(successor["results"]["control"]["residual"], "35")
        self.assertEqual([exact(row["residual"]) for row in successor["results"]["residual_lines"]], [Fraction(35, 2), Fraction(35, 2)])
        self.assertTrue(all("prior_result_ref" in cell for cell in successor["closing_state"]))
        self.assertEqual(successor["closing_state"][0]["scope"]["participant_id"], first["scope"]["participant_group"])

    def test_physical_input_permutation_does_not_set_claim_priority(self):
        fixture = self.fixture("priority-120")
        fixture["opening_claims"].reverse()
        fixture["beneficiaries"].reverse()
        result = self.calculate(fixture)
        self.assertEqual([row["id"] for row in result["results"]["claim_movements"]], ["capital-claim-A", "capital-claim-B"])

    def test_boundary_empty_claims_zero_cash_and_fully_recovered(self):
        for variant in ["empty_claims", "zero_cash", "zero_claims"]:
            with self.subTest(variant=variant):
                fixture = self.fixture()
                fixture["costs"] = []
                if variant == "empty_claims":
                    fixture["opening_claims"] = []
                elif variant == "zero_cash":
                    fixture["cash_records"] = []
                else:
                    for claim in fixture["opening_claims"]:
                        claim["balance"] = "0"
                self.calculate(fixture)

    def test_overapplication_duplicate_and_order_fail_atomically(self):
        mutations = [
            (lambda f: f["costs"][0].update(amount="76"), "WF_DEDUCTIONS_EXCEED_CASH"),
            (lambda f: f["opening_claims"][0].update(balance="81"), "WF_CLAIM_OVERAPPLICATION"),
            (lambda f: f["opening_claims"][0].update(balance="-1"), "WF_CLAIM_OVERAPPLICATION"),
            (lambda f: f["opening_claims"].append(deepcopy(f["opening_claims"][0])), "DUPLICATE_MAP_KEY"),
            (lambda f: f["opening_claims"][1].update(priority=1, sequence=1), "UNRESOLVED_EVENT_ORDER"),
            (lambda f: f["beneficiaries"][0].update(residual_weight="0") or f["beneficiaries"][1].update(residual_weight="0"), "WF_ZERO_DENOMINATOR")]
        for mutate, code in mutations:
            with self.subTest(code=code):
                fixture = self.fixture()
                mutate(fixture)
                self.blocked(fixture, code)

    def test_fact_scope_evidence_and_cost_eligibility_are_required(self):
        mutations = [
            (lambda f: f["cash_records"][0].update(pool_id="other-pool"), "MODULE_REFERENCE_SCOPE"),
            (lambda f: f["costs"][0].update(currency="EUR"), "WF_COST_SCOPE"),
            (lambda f: f["costs"][0].update(participant_group="capital-A"), "WF_COST_SCOPE"),
            (lambda f: f["costs"][0].update(eligible=False), "WF_COST_ELIGIBILITY"),
            (lambda f: f["cash_records"][0].update(evidence_id="missing-evidence"), "WF_EVIDENCE_REQUIRED"),
            (lambda f: f["cash_records"][0].update(effective_date=f["period"]["end"]), "WF_CASH_PERIOD")]
        for mutate, code in mutations:
            with self.subTest(code=code):
                fixture = self.fixture()
                mutate(fixture)
                self.blocked(fixture, code)

    def test_missing_neutral_scope_is_not_inferred(self):
        fixture = self.fixture()
        fixture["cash_records"][0].pop("purpose")
        with self.assertRaises(OracleError):
            waterfall(fixture)
        result = self.run_package(self.package(fixture))
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["statements"], [])
        self.assertEqual(result["closing_state"], [])

    def test_canonical_group_scope_cannot_be_narrowed_to_beneficiary(self):
        for mutation in ["state_owner", "group_missing", "asset", "purpose", "cutoff", "beneficiary_missing"]:
            with self.subTest(mutation=mutation):
                package = self.package(self.fixture())
                if mutation == "state_owner":
                    cell = package["state_cells"][0]
                    cell["scope"]["participant_id"] = "capital-A"
                    cell["state_key"] = canonical({**cell["scope"], "purpose": cell["purpose"]})
                elif mutation == "group_missing":
                    package["scope"]["participant_ids"].remove("capital-beneficiary-group")
                elif mutation == "asset":
                    package["inputs"]["project"] = "another-film"
                elif mutation == "purpose":
                    package["scope"]["purpose"] = "reserve"
                elif mutation == "cutoff":
                    package["parameters"]["cutoff"] = "2026-02-02T00:00:00Z"
                else:
                    package["scope"]["participant_ids"].remove("capital-B")
                result = self.run_package(package)
                self.assertEqual(result["status"], "blocked", result)
                self.assertEqual(result["statements"], [])
                self.assertEqual(result["closing_state"], [])


if __name__ == "__main__":
    unittest.main()
