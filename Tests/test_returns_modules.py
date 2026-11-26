"""Canonical original-rate returns against separately authored neutral controls."""
import ast
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.returns import build_modules as returns
from cases.r1 import build_modules as registration
from oracles.returns_losses import ReturnsOracleError, exact_json, returns_losses
from spl_compiler.codecs import exact, read_json, write_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import run_module_package
from Tests.test_returns_oracle import fixture, successor, add_old_return


class ReturnsModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake" / "returns-module-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/returns"
        cls.folder.mkdir(parents=True)
        for name in ["returns.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/returns" / name, cls.folder / name)
        for owner, name, value in [(returns, "ROOT", cls.root), (returns, "FOLDER", cls.folder),
                                   (registration, "ROOT", cls.root)]:
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = returns.register_returns()

    def package(self, data, cells=None):
        return returns.returns_package(data, reference=self.reference, state_cells=cells)

    def run_fixture(self, data, backend="reference", *, cells=None, output=None):
        return run_module_package(self.package(data, cells), self.root, backend=backend, artifact_dir=output)

    def same(self, actual, expected):
        if type(expected) in {Fraction, int}:
            self.assertEqual(exact(actual), expected)
        elif isinstance(expected, dict):
            self.assertEqual(set(actual), set(expected))
            for key, value in expected.items():
                with self.subTest(field=key):
                    self.same(actual[key], value)
        elif isinstance(expected, list):
            self.assertEqual(len(actual), len(expected))
            for a, b in zip(actual, expected):
                self.same(a, b)
        else:
            self.assertEqual(actual, expected)

    def controls(self, data, result):
        expected = returns_losses(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        values = result["results"]
        self.same(values["comparison"], {key: expected[key] for key in values["comparison"]})
        for port, key in [("titles", "titles"), ("sale_lines", "sales"), ("return_lines", "returns"), ("original_lines", "originals")]:
            with self.subTest(port=port):
                self.same(values[port], expected[key])
        self.assertEqual(returns.neutral_state(result["closing_state"][0]["quantity"]), exact_json(expected["closing_state"]))
        self.assertTrue(values["reconciliation"])
        self.assertEqual(result["issuance_status"], "unissued")
        self.assertFalse({"actual_paid", "bank_refund", "payable"} & values["comparison"].keys())
        return expected

    def blocked(self, data, code=None, backend="reference", *, cells=None):
        with self.assertRaises(ReturnsOracleError):
            returns_losses(data)
        result = self.run_fixture(data, backend, cells=cells)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code)
        for field in ["results", "detail", "statements", "closing_state"]:
            self.assertFalse(result[field])
        return result

    def carried(self, previous_data, previous, quarter=2, sale_basis="30"):
        expected = returns_losses(previous_data)
        data = successor(expected, previous_data, quarter=quarter, sale_basis=sale_basis)
        path = self.root / f"actual-state-q{quarter}.json"
        write_json(path, previous["closing_state"])
        cell = read_json(path)[0]
        cell.pop("movement")
        data["opening_state"] = returns.neutral_state(cell["quantity"])
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        data["prior_result"]["result_ref"] = cell["prior_result_ref"]
        return data, [cell]

    def test_native_three_selected_methods_signed60_floor100(self):
        for method, amount in [("signed_pool", "60"), ("per_title_floor", "100"), ("pooled_loss_carry", "60")]:
            with self.subTest(method=method), tempfile.TemporaryDirectory(dir=self.root) as output:
                data = fixture(method)
                result = self.run_fixture(data, "compare", output=output)
                self.controls(data, result)
                self.assertEqual(result["results"]["comparison"]["recognized_entitlement"], amount)
                self.assertTrue(result["verification"]["reference_agrees"])
                self.assertTrue((Path(output) / "typed-ir.json").is_file())
                self.assertTrue((Path(output) / "Settlement.lean").is_file())

    def test_native_actual_loss_carry_40_10_0_and_credit10(self):
        first_data = fixture("pooled_loss_carry")
        first_data["sales"] = []
        first = self.run_fixture(first_data, "compare")
        self.controls(first_data, first)
        second_data, cells = self.carried(first_data, first)
        second = self.run_fixture(second_data, "compare", cells=cells)
        self.controls(second_data, second)
        third_data, cells = self.carried(second_data, second, quarter=3, sale_basis="20")
        third = self.run_fixture(third_data, "compare", cells=cells)
        self.controls(third_data, third)
        self.assertEqual([r["results"]["comparison"]["closing_loss"] for r in [first, second, third]], ["40", "10", "0"])
        self.assertEqual(third["results"]["comparison"]["recognized_entitlement"], "10")

    def test_native_partial_measurement_30_plus50_and_overreturn(self):
        first_data = fixture()
        first_data["sales"] = []
        first_data["returns"][0]["returned_basis"] = "30"
        first = self.run_fixture(first_data, "compare")
        self.controls(first_data, first)
        self.assertEqual(first["results"]["comparison"]["recognized_entitlement"], "-15")
        second_data, cells = self.carried(first_data, first, sale_basis=None)
        add_old_return(second_data, magnitude="50")
        second = self.run_fixture(second_data, "compare", cells=cells)
        self.controls(second_data, second)
        old = next(row for row in second["results"]["original_lines"] if row["original_id"] == "old-b")
        self.assertEqual((old["opening_returned_basis"], old["current_returned_basis"], old["closing_returned_basis"], old["remaining_basis"]), ("30", "50", "80", "0"))
        self.assertIn("old-b", [row["id"] for row in second["closing_state"][0]["quantity"]["original_registry"]])
        third_data, cells = self.carried(second_data, second, quarter=3, sale_basis=None)
        add_old_return(third_data, magnitude="0.01", identity="return-b-q3")
        result = self.blocked(third_data, "RETURNS_ORIGINAL_OVERRETURN", "compare", cells=cells)
        self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_native_current_sale_return_and_observation_order(self):
        data = fixture()
        row = {**deepcopy(data["returns"][0]), "id": "current-return-a", "original_id": "sale-a-q1",
               "asset_id": "picture-a", "returned_basis": "25", "source_ref": "synthetic-current-return-a"}
        data["returns"].append(row)
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(result["results"]["comparison"]["recognized_entitlement"], "35")
        data["returns"][-1]["observed_at"] = "2026-02-28T23:59:59Z"
        self.blocked(data, "RETURNS_OBSERVATION_ORDER", "compare")

    def test_native_exact_original_rate_fraction(self):
        data = fixture()
        data["originals"][0]["rate"] = "1/3"
        data["returns"][0]["returned_basis"] = "1/7"
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(exact(result["results"]["return_lines"][0]["signed_effect"]), Fraction(-1, 21))
        self.assertEqual(exact(result["results"]["comparison"]["recognized_entitlement"]), Fraction(2099, 21))

    def test_native_scope_reference_cutoff_failures_are_atomic(self):
        for code, change in [
                ("RETURNS_ORIGINAL_REQUIRED", lambda d: d["returns"][0].update(original_id="missing")),
                ("RETURNS_ORIGINAL_SCOPE", lambda d: d["returns"][0].update(asset_id="picture-a")),
                ("RETURNS_FACT_CUTOFF", lambda d: d["returns"][0].update(observed_at=d["cutoff"]))]:
            data = fixture()
            change(data)
            with self.subTest(code=code):
                result = self.blocked(data, code, "compare")
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_reference_current_rates_do_not_reprice_old_original(self):
        for rate in ["0", "0.1", "0.8", "1"]:
            data = fixture()
            data["current_rates"][1]["rate"] = rate
            result = self.run_fixture(data)
            self.controls(data, result)
            self.assertEqual(result["results"]["return_lines"][0]["original_rate"], "0.5")
            self.assertEqual(result["results"]["comparison"]["reversed_earned"], "40")

    def test_reference_duplicate_categories_registration_and_consumed_history(self):
        for key in ["originals", "sales", "returns", "evidence"]:
            data = fixture()
            data[key].append(deepcopy(data[key][0]))
            self.blocked(data)
        data = fixture()
        data["sales"][0]["id"] = "old-b"
        self.blocked(data, "RETURNS_ORIGINAL_ALREADY_REGISTERED")
        first_data = fixture()
        first = self.run_fixture(first_data)
        data, cells = self.carried(first_data, first, sale_basis=None)
        add_old_return(data, magnitude="0", identity="return-b-q1")
        self.blocked(data, "RETURNS_ALREADY_RECOGNIZED", cells=cells)
        data, cells = self.carried(first_data, first, sale_basis=None)
        data["originals"] = deepcopy(first_data["originals"])
        self.blocked(data, "RETURNS_ORIGINAL_ALREADY_REGISTERED", cells=cells)

    def test_reference_opening_scope_method_boundary_snapshot_and_predecessor(self):
        first_data = fixture("pooled_loss_carry")
        first_data["sales"] = []
        first = self.run_fixture(first_data)
        for change in [lambda d: d["policy"].update(method="signed_pool"),
                       lambda d: d["opening_state"].update(purpose="prepayment"),
                       lambda d: d["opening_state"].update(loss_carry="0"),
                       lambda d: d["prior_result"]["period"].update(end="2026-03-31")]:
            data, cells = self.carried(first_data, first)
            change(data)
            self.blocked(data, cells=cells)
        data, cells = self.carried(first_data, first)
        data.pop("prior_result")
        self.blocked(data, "RETURNS_PREDECESSOR_REQUIRED", cells=cells)
        data, cells = self.carried(first_data, first)
        data["prior_result"].pop("result_ref")
        with self.assertRaisesRegex(ValueError, "RETURNS_CANONICAL_PREDECESSOR_REQUIRED"):
            self.run_fixture(data, cells=cells)
        data, cells = self.carried(first_data, first)
        data["prior_result"]["result_ref"] = "result@sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "RETURNS_CANONICAL_PREDECESSOR_MISMATCH"):
            self.run_fixture(data, cells=cells)

    def test_reference_historical_import_zero_activity_and_zero_rate_meter(self):
        data = fixture()
        data["sales"], data["returns"] = [], []
        self.controls(data, self.run_fixture(data))
        data = fixture()
        data["originals"][0]["rate"] = "0"
        result = self.run_fixture(data)
        self.controls(data, result)
        old = next(row for row in result["results"]["original_lines"] if row["original_id"] == "old-b")
        self.assertEqual((old["closing_returned_basis"], old["remaining_basis"]), ("80", "0"))
        self.assertEqual(result["results"]["comparison"]["recognized_entitlement"], "100")

    def test_reference_original_date_recognition_and_rate_domains(self):
        for change in [lambda d: d["returns"][0].update(return_date="2025-12-14"),
                       lambda d: d["returns"][0].update(return_date="2026-02-16"),
                       lambda d: d["returns"][0].update(recognition_date="2026-04-01"),
                       lambda d: d["originals"][0].update(measurement_date="2026-01-01"),
                       lambda d: d["current_rates"][0].update(rate="1.1"),
                       lambda d: d["current_rates"].pop()]:
            data = fixture()
            change(data)
            self.blocked(data)

    def test_adapter_exact_transport_tuple_history_and_no_oracle_import(self):
        data = fixture()
        package = self.package(data)
        self.assertEqual(package["inputs"]["originals"][0]["basis"], {"value": "80", "currency": "USD"})
        self.assertNotIn("recognized_entitlement", package["inputs"])
        tree = ast.parse((ROOT / "cases/returns/build_modules.py").read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("oracles") for node in ast.walk(tree)))
        for value in [0.5, True, "1e-1", "-1"]:
            data = fixture()
            data["originals"][0]["rate"] = value
            with self.assertRaisesRegex(ValueError, "RETURNS_EXACT_NONNEGATIVE_VALUE"):
                self.package(data)
        data = fixture()
        data["sales"][0]["id"] = "sale:\u00e9"
        first = self.run_fixture(data)
        self.controls(data, first)
        self.assertIn(["sales", "sale:\u00e9"], first["closing_state"][0]["quantity"]["recognized_ids"])


if __name__ == "__main__":
    unittest.main()
