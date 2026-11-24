"""Original-measurement controls independent of the SPL conversion engine."""
import ast
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
import unittest

from oracles.usage_conversion import UsageConversionError, exact_json, usage_conversion


ROOT = Path(__file__).resolve().parents[1]


class UsageConversionOracleTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT / "cases/usage-conversion/neutral.json").read_text(encoding="utf-8"))

    def test_original_ninety_minutes_and_full_lineage(self):
        data = self.fixture()
        original = deepcopy(data)
        result = usage_conversion(data)
        self.assertEqual(result["base_minutes"], 90)
        self.assertEqual(result["converted_quantity"], {"value": Fraction(3, 2), "unit": "UsageHour"})
        self.assertEqual(result["earned"], {"value": 18, "currency": "USD"})
        self.assertEqual(result["original_quantity"], data["source_quantity"])
        self.assertEqual(result["original_price"], data["price"])
        self.assertEqual(data, original)
        result["original_quantity"]["value"] = "changed"
        self.assertEqual(data, original)

    def test_zero_fraction_signed_and_lexeme_controls(self):
        for original, hours, earned in [("0", Fraction(0), Fraction(0)),
                                       ("1/3", Fraction(1, 180), Fraction(1, 15)),
                                       ("-90", Fraction(-3, 2), Fraction(-18)),
                                       ("090.00", Fraction(3, 2), Fraction(18))]:
            with self.subTest(original=original):
                data = self.fixture()
                data["source_quantity"]["value"] = original
                result = usage_conversion(data)
                self.assertEqual(result["converted_quantity"]["value"], hours)
                self.assertEqual(result["earned"]["value"], earned)
                self.assertEqual(result["original_quantity"]["value"], original)

    def test_inverse_and_round_trip(self):
        data = self.fixture()
        data["source_quantity"].update(value="1.5", unit="UsageHour")
        data["target_unit"] = "UsageMinute"
        data["price"].update(value="0.20", per_unit="UsageMinute")
        result = usage_conversion(data)
        self.assertEqual(result["converted_quantity"], {"value": 90, "unit": "UsageMinute"})
        self.assertEqual(result["earned"]["value"], 18)
        for minutes in ("0", "1/3", "-17/11", "150", "1000001/99991"):
            with self.subTest(minutes=minutes):
                forward = self.fixture()
                forward["source_quantity"]["value"] = minutes
                forward["price"] = None
                hours = usage_conversion(forward)["converted_quantity"]["value"]
                reverse = deepcopy(forward)
                reverse["source_quantity"].update(value=str(hours), unit="UsageHour")
                reverse["target_unit"] = "UsageMinute"
                self.assertEqual(usage_conversion(reverse)["converted_quantity"]["value"], Fraction(minutes))

    def test_old_minute_encoding_remains_financially_equivalent(self):
        data = self.fixture()
        data["source_quantity"]["value"] = "150"
        result = usage_conversion(data)
        old_quantity = Fraction("150")
        old_original_price = Fraction("0.20")
        self.assertEqual(result["converted_quantity"]["value"], Fraction(5, 2))
        self.assertEqual(result["earned"]["value"], 30)
        self.assertEqual(result["earned"]["value"], old_quantity * old_original_price)

    def test_quantity_only_and_exact_serialization(self):
        data = self.fixture()
        data["price"] = None
        result = usage_conversion(data)
        self.assertIsNone(result["earned"])
        self.assertEqual(exact_json(result)["converted_quantity"]["value"], "3/2")

    def test_unit_relation_version_price_and_evidence_failures(self):
        mutations = [
            ("unsupported_feature", lambda d: d.update(feature="spl.usage-time/999")),
            ("unsupported_relation", lambda d: d.update(relation_id="invented:minute-hour")),
            ("unsupported_unit", lambda d: d["source_quantity"].update(unit="Download")),
            ("unsupported_unit", lambda d: d.update(target_unit="CivilHour")),
            ("opposite_endpoint_required", lambda d: d.update(target_unit="UsageMinute")),
            ("price_unit_mismatch", lambda d: d["price"].update(per_unit="UsageMinute")),
            ("unsupported_currency", lambda d: d["price"].update(currency="EUR")),
            ("missing_measurement_evidence", lambda d: d["source_quantity"].update(evidence_ref="")),
            ("missing_price_evidence", lambda d: d["price"].update(quote_id="")),
            ("unexpected_shape", lambda d: d.update(conversion_factor="59")),
        ]
        for code, mutate in mutations:
            with self.subTest(code=code):
                data = self.fixture()
                mutate(data)
                with self.assertRaisesRegex(UsageConversionError, "^" + code + "$"):
                    usage_conversion(data)

    def test_inexact_or_malformed_numbers_fail(self):
        for raw in (90, 90.0, True, "nan", "inf", "1/0", " 90", "1e2", "1.5/2"):
            with self.subTest(raw=raw):
                data = self.fixture()
                data["source_quantity"]["value"] = raw
                with self.assertRaisesRegex(UsageConversionError, "^exact_number_required$"):
                    usage_conversion(data)

    def test_only_standard_library_dependencies(self):
        path = ROOT / "oracles/usage_conversion.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertTrue(all(alias.name.split(".")[0] in sys.stdlib_module_names
                                    for alias in node.names))
            if isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                self.assertIn(node.module.split(".")[0], sys.stdlib_module_names)


if __name__ == "__main__":
    unittest.main()
