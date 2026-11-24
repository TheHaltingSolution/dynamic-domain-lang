"""Independent original-fact LG controls through canonical/native execution."""
from copy import deepcopy
from fractions import Fraction
import unittest

from oracles.lionsgate import LionsgateOracleError, lionsgate
from spl_compiler.codecs import exact
from spl_compiler.run import ROOT, bind_package, project, run_package
from Tests.test_lionsgate_oracle import allocated, cost, event, fixture


class LionsgatePipelineTests(unittest.TestCase):
    def compare(self, data, source="cases/lg/lg01-readable.spl"):
        original = deepcopy(data)
        expected = lionsgate(data)
        path = ROOT / source
        package = bind_package(data["package"], path)
        result = run_package(package, path, backend="compare")
        self.assertEqual(data, original)
        self.assertIn(result["status"], {"calculated", "calculated_zero"}, result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        self.assertTrue(result["verification"]["reference_agrees"])
        comparison, statement = result["detail"][0], result["statements"][0]
        for name in ["cash_measure", "payout_base", "gross_candidate", "net_candidate", "earned"]:
            self.assertEqual(exact(comparison[name]), expected[name], name)
        self.assertEqual(comparison["selected_label"], expected["selected_label"])
        self.assertEqual(exact(statement["payable"]), expected["payable"])
        self.assertEqual(exact(statement["payment_holdback_addition"]), expected["holdback_addition"])
        self.assertEqual(exact(statement["payment_holdback_release"]), expected["holdback_release"])
        cells = {cell["state_key"]: exact(cell["quantity"]) for cell in result["closing_state"]}
        for opening in package["opening_aliases"]:
            actual = cells[opening["state_key"]]
            expected_name = ("closing_gate_gross" if opening["alias"].endswith("cumulative-gross") else
                             "closing_gate_cost" if opening["alias"].endswith("cumulative-cost") else "closing_payment_holdback")
            self.assertEqual(actual, expected[expected_name])
        # Projection itself is under test. These expected values came from raw
        # source records, rather than being fed back into the independent oracle.
        inputs, openings, _, _ = project(package)
        for actual_name, expected_name in [("crossed_net_subtotal", "crossed_net_subtotal"),
                                            ("producer_fee_offset", "producer_fee_offset"),
                                            ("payment_holdback_addition", "holdback_addition"),
                                            ("payment_holdback_release", "holdback_release")]:
            self.assertEqual(exact(inputs[actual_name]["value"]), expected[expected_name])
        self.assertEqual(result["payment_evidence_status"], "no_event_supplied")
        self.assertEqual(result["issuance_status"], "unissued")
        return result, expected

    def test_original_and_readable_compare_all_published_intermediates(self):
        for source in ["cases/lg/lg01.spl", "cases/lg/lg01-readable.spl"]:
            with self.subTest(source=source):
                _, expected = self.compare(fixture(), source)
                self.assertEqual(expected["payable"], 35)

    def test_gross_and_tie_are_independently_selected(self):
        for amount, label in [("100", "gross"), ("150", "tie")]:
            with self.subTest(label=label):
                data = fixture()
                event(data, "crossed_net_worksheet")["amount"]["value"] = amount
                result, expected = self.compare(data)
                self.assertEqual(expected["selected_label"], label)
                self.assertEqual(exact(result["statements"][0]["payable"]), 30)

    def test_work_gate_equality_and_original_allocated_parent(self):
        data = fixture()
        cost(data, "300")
        _, expected = self.compare(data)
        self.assertEqual(expected["closing_gate_gross"], expected["closing_gate_cost"])
        _, allocated_expected = self.compare(allocated(fixture()))
        self.assertEqual(allocated_expected["cash_measure"], 300)
        self.assertEqual(allocated_expected["payable"], 35)

    def test_strict_outside_hurdle_equality_is_atomic(self):
        data = fixture()
        event(data, "hurdle_attestation")["effective_date"] = data["package"]["manifest"]["period"]["start"]
        with self.assertRaises(LionsgateOracleError):
            lionsgate(data)
        path = ROOT / "cases/lg/lg01-readable.spl"
        result = run_package(bind_package(data["package"], path), path, backend="compare")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["diagnostics"][0]["code"], "LG_HURDLE_TIMING_POLICY_REQUIRED")
        self.assertEqual(result["statements"], [])
        self.assertEqual(result["closing_state"], [])

    def test_allocated_video_keeps_proxy_and_missing_channel_blocks(self):
        data = fixture()
        facts = data["package"]["financial_facts"]
        facts[0], facts[1] = facts[1], facts[0]
        allocated(data)
        _, expected = self.compare(data)
        self.assertEqual(expected["home_video_receipts"], 120)
        self.assertEqual(expected["payout_base"], 210)
        parent = data["package"]["financial_facts"][0]
        del parent["channel"]
        with self.assertRaises(LionsgateOracleError):
            lionsgate(data)
        path = ROOT / "cases/lg/lg01-readable.spl"
        result = run_package(bind_package(data["package"], path), path, backend="compare")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["diagnostics"][0]["code"], "REQUIRED_CHANNEL_MAPPING")
        self.assertEqual(result["statements"], [])
        self.assertEqual(result["closing_state"], [])


if __name__ == "__main__":
    unittest.main()
