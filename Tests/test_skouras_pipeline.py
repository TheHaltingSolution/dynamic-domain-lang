"""Compare original-fact SV controls with canonical projection and native paths.

The dedicated financial oracle was authored before this integration test. It
does not consume the projected SPL bindings or calculate from compiler helpers.
"""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import unittest

from oracles.skouras import skouras
from spl_compiler.codecs import exact
from spl_compiler.run import bind_package, run_package
from Tests.test_skouras_oracle import bundle_fixture

ROOT = Path(__file__).resolve().parents[1]


class SkourasPipelineTests(unittest.TestCase):
    def fixture(self):
        return json.loads((ROOT / "cases/sv/neutral-oracle.json").read_text(encoding="utf-8"))

    def compare(self, data, source="cases/sv/sv01-readable.spl"):
        original = deepcopy(data)
        expected = skouras(data)
        path = ROOT / source
        result = run_package(bind_package(data["package"], path), path, backend="compare")
        self.assertEqual(data, original)
        self.assertIn(result["status"], {"calculated", "calculated_zero"}, result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        self.assertTrue(result["verification"]["reference_agrees"])
        self.assertEqual(result["trace_origin"], "native_ir_interpreter")
        actual_titles = {row["asset_id"]: row for row in result["detail"]}
        self.assertEqual(set(actual_titles), {row["asset_id"] for row in expected["titles"]})
        for title in expected["titles"]:
            for field in ["cash", "fee", "allowed_cost", "basis", "share", "earned"]:
                with self.subTest(asset=title["asset_id"], field=field):
                    self.assertEqual(exact(actual_titles[title["asset_id"]][field]), title[field])
        statement = result["statements"][0]
        for field in ["agreement_id", "participant_id", "pool_id", "period"]:
            self.assertEqual(statement[field], expected["pool"][field])
        for actual_field, expected_field in [("earned", "earned"), ("recouped", "recovered"), ("payable", "payable")]:
            self.assertEqual(exact(statement[actual_field]), expected["pool"][expected_field])
        self.assertEqual(exact(result["closing_state"][0]["quantity"]), expected["pool"]["closing_prepayment"])
        self.assertEqual(result["payment_evidence_status"], "no_event_supplied")
        self.assertEqual(result["issuance_status"], "unissued")
        return result, expected

    def test_original_and_readable_match_independent_original_facts(self):
        for path in ["cases/sv/sv01.spl", "cases/sv/sv01-readable.spl"]:
            with self.subTest(source=path):
                result, expected = self.compare(self.fixture(), path)
                self.assertEqual(expected["pool"]["payable"], 18000)

    def test_half_open_date_exclusion_preserves_zero_title_and_pool(self):
        data = self.fixture()
        for row in data["package"]["financial_facts"]:
            if row["asset_id"] == "picture-a":
                field = row["temporal_basis"]["kind"]
                row["dates"][field] = "2026-04-01"
                row["temporal_basis"]["date"] = "2026-04-01"
        result, expected = self.compare(data)
        self.assertEqual(expected["pool"]["payable"], 5000)
        self.assertEqual(next(row for row in result["detail"] if row["asset_id"] == "picture-a")["earned"], "0")

    def test_original_funding_denominator_retains_exact_fraction(self):
        data = self.fixture()
        next(row for row in data["package"]["evidence_events"] if row["event_id"] == "fund-b-dist")["amount"]["value"] = "20000"
        _, expected = self.compare(data)
        self.assertEqual(next(row for row in expected["titles"] if row["asset_id"] == "picture-b")["share"], Fraction(2, 3))
        self.assertEqual(expected["pool"]["payable"], Fraction(94000, 3))

    def test_original_invoice_and_allocated_cash_parent_are_not_added_twice(self):
        data = bundle_fixture()
        authority = data["allocation_authorities"][0]
        # Explicit physical interpretation terms transport the independently
        # supplied authority; the oracle does not derive them from projection.
        decision = next(row for item in data["package"]["interpretations"] for row in item["decisions"]
                        if row["decision_id"] == authority["authority_ref"])
        decision["allocation_terms"] = deepcopy(authority["weights"])
        result, expected = self.compare(data)
        self.assertEqual(sum(row["cash"] for row in expected["titles"]), 160000)
        self.assertEqual(expected["pool"]["payable"], 18000)
        self.assertEqual(len(result["detail"]), 2)


if __name__ == "__main__":
    unittest.main()
