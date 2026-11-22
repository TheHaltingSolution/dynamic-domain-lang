"""M1a registered financial recipes against independent neutral-fact controls."""
from copy import deepcopy
from fractions import Fraction
import json
import os
from pathlib import Path
import tempfile
import unittest

from cases.m1.build_modules import FOLDER, ROOT, m1_package, register_m1
from oracles.ordinary_royalties import OracleError, ordinary_royalties
from spl_compiler.codecs import exact, read_json, write_json
from spl_compiler.modules import bind_module_package, run_module_package


class M1ModuleTests(unittest.TestCase):
    backend = os.environ.get("SPL_M1_BACKEND", "compare")

    @classmethod
    def setUpClass(cls):
        cls.reference = register_m1()

    def fixture(self, name="period-marginal"):
        return json.loads((FOLDER / "fixtures" / (name + ".json")).read_text(encoding="utf-8"))

    def test_neutral_schema_and_tier_order_cannot_be_coerced(self):
        for version in ["m1-neutral/99", None, 1, True]:
            fixture = self.fixture()
            fixture["schema_version"] = version
            with self.assertRaises(OracleError):
                ordinary_royalties(fixture)
            with self.assertRaisesRegex(ValueError, "M1_NEUTRAL_SCHEMA_REQUIRED"):
                self.package(fixture)
        fixture = self.fixture()
        del fixture["schema_version"]
        with self.assertRaisesRegex(ValueError, "M1_NEUTRAL_SCHEMA_REQUIRED"):
            self.package(fixture)
        for sequence in ["1", 1.0, True, False, -1]:
            fixture = self.fixture()
            fixture["policy"]["tiers"][0]["sequence"] = sequence
            with self.assertRaises(OracleError):
                ordinary_royalties(fixture)
            with self.assertRaisesRegex(ValueError, "M1_TIER_SEQUENCE_REQUIRED"):
                self.package(fixture)

    def package(self, fixture):
        return m1_package(fixture, reference=self.reference)

    def run_package(self, package, output=None):
        return run_module_package(package, ROOT, backend=self.backend, artifact_dir=output)

    def calculate(self, fixture, package=None, output=None):
        expected = ordinary_royalties(fixture)
        result = self.run_package(package if package is not None else self.package(fixture), output)
        self.assertEqual(result["status"], "calculated", result.get("diagnostics"))
        self.assertEqual(result["diagnostics"], [])
        comparison = result["results"]["comparison"]
        for name in ["basis", "uncapped", "entitlement", "closing_balance"]:
            self.assertEqual(exact(comparison[name]), expected[name], name)
        self.assertEqual(len(result["statements"]), 1)
        self.assertEqual(exact(result["statements"][0]["entitlement"]), expected["entitlement"])
        self.assertEqual(exact(result["closing_state"][0]["quantity"]["balance"]["value"]), expected["closing_balance"])
        self.assertEqual(len(result["module_closure"]), 5)
        if self.backend != "reference":
            self.assertEqual(result["trace_origin"], "native_ir_interpreter")
            self.assertTrue(result["verification"]["reference_agrees"])
        return result

    def blocked(self, fixture, code=None, package=None, oracle=True):
        if oracle:
            with self.assertRaises(OracleError):
                ordinary_royalties(fixture)
        result = self.run_package(package if package is not None else self.package(fixture))
        self.assertEqual(result["status"], "blocked", result.get("diagnostics"))
        self.assertEqual(result["results"], {})
        self.assertEqual(result["statements"], [])
        self.assertEqual(result["closing_state"], [])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code, result["diagnostics"])
        return result

    def test_selected_financial_discriminators_and_linked_artifacts(self):
        controls = {"period-marginal": (20, 0), "period-whole-base": (30, 0),
                    "cumulative-marginal": (12, 150), "cumulative-cap": (30, 100),
                    "period-cap": (30, 100), "period-floor": (100, 0), "tiers-then-cap": (15, 0)}
        for name, (entitlement, balance) in controls.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                result = self.calculate(self.fixture(name), output=directory)
                self.assertEqual(exact(result["results"]["comparison"]["entitlement"]), entitlement)
                self.assertEqual(exact(result["results"]["comparison"]["closing_balance"]), balance)
                if self.backend != "reference":
                    self.assertTrue((Path(directory) / "typed-ir.json").is_file())
                    self.assertTrue((Path(directory) / "Settlement.lean").is_file())
                if name == "tiers-then-cap":
                    self.assertEqual(exact(result["results"]["comparison"]["uncapped"]), 20)

    def test_threshold_equality_is_lower_inclusive_whole_base(self):
        for name, expected in [("period-marginal", 10), ("period-whole-base", 20)]:
            fixture = self.fixture(name)
            fixture["facts"][0]["amount"] = "100"
            result = self.calculate(fixture)
            self.assertEqual(exact(result["results"]["comparison"]["entitlement"]), expected)

    def test_zero_empty_and_exact_fractional_inputs(self):
        for name in ["period-marginal", "period-whole-base", "cumulative-marginal", "cumulative-cap", "period-cap", "period-floor", "tiers-then-cap"]:
            fixture = self.fixture(name)
            fixture["facts"] = []
            self.calculate(fixture)
        fixture = self.fixture()
        fixture["facts"][0]["amount"] = "1/3"
        result = self.calculate(fixture)
        self.assertEqual(exact(result["results"]["comparison"]["entitlement"]), Fraction(1, 30))
        fixture["facts"][0]["amount"] = "0"
        self.calculate(fixture)

    def test_split_and_physical_permutation_preserve_cumulative_earnings(self):
        fixture = self.fixture("cumulative-marginal")
        first = deepcopy(fixture["facts"][0])
        first.update(id="split-a", amount="20")
        second = deepcopy(first)
        second.update(id="split-b", amount="50")
        fixture["facts"] = [first, second]
        result = self.calculate(fixture)
        fixture["facts"].reverse()
        permuted = self.calculate(fixture)
        self.assertEqual(result["results"], permuted["results"])
        self.assertEqual(result["closing_state"][0]["quantity"], permuted["closing_state"][0]["quantity"])

    def successor(self, fixture, result, *, amount="50", reset=False):
        fixture = deepcopy(fixture)
        fixture["opening_state"] = {"scope": deepcopy(fixture["scope"]), "method": fixture["policy"]["method"],
            "balance": result["results"]["comparison"]["closing_balance"], "period": deepcopy(fixture["period"])}
        fixture["period"] = {"start": "2026-02-01", "end": "2026-03-01"}
        fixture["cutoff"] = "2026-03-02T00:00:00Z"
        fixture["facts"][0].update(id="successor-fact", effective_date="2026-02-15", observed_at="2026-02-16T00:00:00Z", amount=amount)
        fixture["evidence"][0]["observed_at"] = "2026-02-16T00:00:00Z"
        fixture["policy"]["reset_period_cap"] = reset
        package = self.package(fixture)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "actual-closing-state.json"
            write_json(path, result["closing_state"])
            package["state_cells"] = [{key: value for key, value in cell.items() if key != "movement"} for cell in read_json(path)]
        return fixture, bind_module_package(package, ROOT)

    def test_actual_serialized_cumulative_basis_carry(self):
        fixture = self.fixture("cumulative-marginal")
        result = self.calculate(fixture)
        fixture, package = self.successor(fixture, result)
        successor = self.calculate(fixture, package)
        self.assertEqual(exact(successor["results"]["comparison"]["entitlement"]), 10)
        self.assertEqual(exact(successor["results"]["comparison"]["closing_balance"]), 200)
        self.assertTrue(successor["closing_state"][0]["prior_result_ref"].startswith("result@sha256:"))

    def test_cumulative_cap_carry_never_resets(self):
        fixture = self.fixture("cumulative-cap")
        result = self.calculate(fixture)
        fixture, package = self.successor(fixture, result)
        successor = self.calculate(fixture, package)
        self.assertEqual(exact(successor["results"]["comparison"]["entitlement"]), 0)
        fixture["policy"]["reset_period_cap"] = True
        package["parameters"]["reset_period_cap"] = True
        self.blocked(fixture, "M1_RESET_METHOD", package=package)

    def test_period_cap_requires_explicit_reset_on_successor(self):
        fixture = self.fixture("period-cap")
        result = self.calculate(fixture)
        successor, package = self.successor(fixture, result)
        self.blocked(successor, "M1_PERIOD_CAP_RESET_REQUIRED", package=package)
        successor["policy"]["reset_period_cap"] = True
        package["parameters"]["reset_period_cap"] = True
        reset = self.calculate(successor, package)
        self.assertEqual(exact(reset["results"]["comparison"]["entitlement"]), 50)
        self.assertEqual(exact(reset["results"]["comparison"]["closing_balance"]), 50)

    def test_bracket_overlap_gap_invalid_range_missing_terminal_and_duplicates(self):
        variants = [("overlap", lambda rows: rows[1].update(lower="99")),
                    ("gap", lambda rows: rows[1].update(lower="101")),
                    ("range", lambda rows: rows[0].update(upper="0")),
                    ("rate", lambda rows: rows[0].update(rate="-1/10")),
                    ("terminal", lambda rows: rows[1].update(upper="200")),
                    ("duplicate-id", lambda rows: rows[1].update(id=rows[0]["id"])),
                    ("duplicate-sequence", lambda rows: rows[1].update(sequence=1))]
        for label, change in variants:
            with self.subTest(label=label):
                fixture = self.fixture()
                change(fixture["policy"]["tiers"])
                self.blocked(fixture)
        fixture = self.fixture()
        fixture["policy"]["tiers"] = []
        self.blocked(fixture, "M1_UNBOUNDED_FINAL_BRACKET_REQUIRED")

    def test_negative_basis_duplicate_fact_and_missing_support_fail(self):
        fixture = self.fixture()
        fixture["facts"][0]["amount"] = "-1"
        self.blocked(fixture, "M1_NEGATIVE_BASIS")
        fixture = self.fixture()
        fixture["facts"].append(deepcopy(fixture["facts"][0]))
        self.blocked(fixture, "DUPLICATE_MAP_KEY")
        fixture = self.fixture()
        fixture["facts"][0]["evidence_id"] = "missing"
        self.blocked(fixture, "M1_FACT_EVIDENCE_REQUIRED")
        fixture = self.fixture()
        fixture["evidence"] = []
        self.blocked(fixture)

    def test_half_open_effective_period_and_strict_fact_evidence_cutoffs(self):
        for field, value in [("effective_date", "2026-02-01"), ("effective_date", "2025-12-31"),
                             ("observed_at", "2026-02-02T00:00:00Z")]:
            fixture = self.fixture()
            fixture["facts"][0][field] = value
            self.blocked(fixture)
        fixture = self.fixture()
        fixture["evidence"][0]["observed_at"] = fixture["cutoff"]
        self.blocked(fixture)
        fixture = self.fixture()
        fixture["evidence"].append(deepcopy(fixture["evidence"][0]))
        self.blocked(fixture)

    def test_meter_method_purpose_and_scope_are_guarded(self):
        fixture = self.fixture("cumulative-marginal")
        fixture["opening_state"]["method"] = "cumulative_cap"
        self.blocked(fixture, "M1_METER_METHOD")
        for field in ["contract_id", "participant_id", "pool_id", "asset_id"]:
            fixture = self.fixture("cumulative-marginal")
            fixture["opening_state"]["scope"][field] = "unrelated"
            self.blocked(fixture)
        fixture = self.fixture()
        package = self.package(fixture)
        package["state_cells"][0]["purpose"] = "advance_balance"
        self.blocked(fixture, package=package, oracle=False)
        fixture = self.fixture()
        fixture["facts"][0]["scope"] = {**fixture["scope"], "pool_id": "unrelated"}
        self.blocked(fixture)

    def test_cap_domain_and_unrelated_period_meter_fail(self):
        fixture = self.fixture("cumulative-cap")
        fixture["opening_state"]["balance"] = "101"
        self.blocked(fixture, "M1_CAP_DOMAIN")
        fixture = self.fixture()
        fixture["opening_state"]["balance"] = "1"
        self.blocked(fixture, "M1_PERIOD_METHOD_METER")
        fixture = self.fixture("cumulative-marginal")
        fixture["opening_state"]["period"] = {"start": "2026-01-15", "end": "2026-02-15"}
        self.blocked(fixture, "M1_METER_PERIOD")
        fixture = self.fixture("period-whole-base")
        fixture["policy"]["method"] = "cumulative_whole_base"
        fixture["opening_state"]["method"] = "cumulative_whole_base"
        self.blocked(fixture)

    def test_unsupported_rounding_loss_policy_and_floating_transport_rejected(self):
        fixture = self.fixture()
        fixture["policy"]["rounding"] = "cents"
        with self.assertRaises(ValueError):
            self.package(fixture)
        for invalid in [1.5, True]:
            fixture = self.fixture()
            fixture["facts"][0]["amount"] = invalid
            with self.assertRaises(ValueError):
                self.package(fixture)

    def test_bracket_permutation_and_exact_subsecond_observation_boundary(self):
        fixture = self.fixture()
        fixture["policy"]["tiers"].reverse()
        self.calculate(fixture)
        fixture["cutoff"] = "2026-02-02T00:00:00.0000000000000000002Z"
        fixture["facts"][0]["observed_at"] = "2026-02-02T00:00:00.0000000000000000001Z"
        fixture["evidence"][0]["observed_at"] = fixture["facts"][0]["observed_at"]
        self.calculate(fixture)
        fixture["facts"][0]["observed_at"] = fixture["cutoff"]
        self.blocked(fixture, "M1_FACT_AFTER_CUTOFF")

    def test_meter_cap_equality_and_floor_above_threshold(self):
        fixture = self.fixture("cumulative-cap")
        fixture["facts"][0]["amount"] = "30"
        self.calculate(fixture)
        fixture["opening_state"]["balance"] = "100"
        self.calculate(fixture)
        fixture = self.fixture("period-floor")
        fixture["facts"][0]["amount"] = "100"
        self.calculate(fixture)
        fixture["facts"][0]["amount"] = "101"
        self.calculate(fixture)

    def test_declared_tiers_validate_for_cap_and_guarantee_methods(self):
        for name in ["period-cap", "cumulative-cap", "period-floor"]:
            with self.subTest(method=name):
                fixture = self.fixture(name)
                self.calculate(fixture)
                fixture["policy"]["tiers"] = []
                self.calculate(fixture)
                fixture = self.fixture(name)
                fixture["policy"]["tiers"][1]["lower"] = "99"
                self.blocked(fixture, "M1_BRACKET_CONTIGUITY")


if __name__ == "__main__":
    unittest.main()
