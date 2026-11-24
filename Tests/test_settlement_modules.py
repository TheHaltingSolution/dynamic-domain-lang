"""Canonical supplied settlement against independently authored neutral controls.

Selected positive and financial-error methods explicitly run compare mode.
Other negative groups exercise the reference canonical boundary and say so.
No environment switch can narrow the requested native comparison paths.
"""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.settlement import build_modules as settlement
from cases.r1 import build_modules as registration
from oracles.settlement_adjustments import SettlementOracleError, exact_json, settlement_adjustments
from spl_compiler.codecs import digest, exact, read_json, write_json
from spl_compiler.lean_tools import ROOT
from Tests.test_settlement_oracle import fixture, successor, unissued


class SettlementModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = ROOT / ".lake" / "settlement-module-tests"
        directory.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=directory)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/settlement"
        cls.folder.mkdir(parents=True)
        for name in ["amounts.spl", "settlement.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/settlement" / name, cls.folder / name)
        for owner, name, value in [(settlement, "ROOT", cls.root), (settlement, "FOLDER", cls.folder),
                                   (registration, "ROOT", cls.root)]:
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = settlement.register_settlement()

    def run_fixture(self, data, backend="reference", *, cells=None, output=None):
        package = settlement.settlement_package(data, reference=self.reference, state_cells=cells)
        return settlement.run_settlement_package(package, self.root, backend=backend, artifact_dir=output)

    def same(self, actual, expected):
        if isinstance(expected, Fraction):
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
        expected = settlement_adjustments(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        comparison = result["results"]["comparison"]
        for key in comparison:
            with self.subTest(control=key):
                self.same(comparison[key], expected[key])
        self.same(result["results"]["obligations"], expected["obligations"])
        self.assertTrue(result["results"]["reconciliation"])
        self.assertEqual(settlement.neutral_state(result["closing_state"][0]["quantity"]),
                         exact_json(expected["closing_state"]))
        self.assertEqual(result["issuance_status"], "unissued")
        return expected

    def blocked(self, data, code=None, backend="reference", *, cells=None):
        with self.assertRaises(SettlementOracleError):
            settlement_adjustments(data)
        result = self.run_fixture(data, backend, cells=cells)
        self.assertEqual(result["status"], "blocked", result.get("diagnostics"))
        self.assertTrue(result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code, result["diagnostics"])
        for field in ["results", "statements", "detail", "closing_state"]:
            self.assertFalse(result[field], field)
        return result

    def carried(self, previous_data, previous, quarter=2, amounts=("10",)):
        expected = settlement_adjustments(previous_data)
        data = successor(expected, quarter=quarter, amounts=amounts)
        # Carry actual serialized canonical state, independently checked against
        # the neutral oracle, and keep its canonical result reference separate.
        path = self.root / f"actual-state-q{quarter}.json"
        write_json(path, previous["closing_state"])
        cell = read_json(path)[0]
        cell.pop("movement")
        data["opening_state"] = settlement.neutral_state(cell["quantity"])
        data["prior_result"]["closing_state"] = deepcopy(data["opening_state"])
        data["prior_result"]["result_ref"] = cell["prior_result_ref"]
        return data, [cell]

    def final_period(self, middle_data, middle):
        data, cells = self.carried(middle_data, middle, quarter=3, amounts=("20",))
        original = fixture()
        data["issued"] = [{**deepcopy(original["issued"][0]), "id": "issue-q3", "amount": "27",
                           "issued_date": "2026-09-29", "observed_at": "2026-09-29T12:00:00Z",
                           "source_ref": "synthetic-issued-q3", "evidence_ref": "source-q3"}]
        data["payments"] = [{**deepcopy(original["payments"][0]), "id": "payment-q3", "amount": "20",
                             "paid_date": "2026-09-30", "observed_at": "2026-10-01T00:00:00Z",
                             "source_ref": "synthetic-bank-q3", "evidence_ref": "source-q3"}]
        data["applications"] = [{**deepcopy(original["applications"][0]), "id": f"application-q3-{i}",
                                 "payment_id": "payment-q3", "issued_id": notice, "amount": "10",
                                 "observed_at": "2026-10-01T01:00:00Z", "evidence_ref": "source-q3",
                                 "source_ref": f"synthetic-remittance-q3-{i}"}
                                for i, notice in enumerate(["issue-q1", "issue-q3"])]
        return data, cells

    def test_native_baseline_all_intermediates_and_artifacts(self):
        with tempfile.TemporaryDirectory(dir=self.root) as output:
            result = self.run_fixture(fixture(), "compare", output=output)
            self.controls(fixture(), result)
            self.assertTrue(result["verification"]["reference_agrees"])
            self.assertEqual(result["result_digest"], digest({key: value for key, value in result.items()
                                                            if key != "result_digest"}))
            self.assertEqual(result["trace_origin"], "native_ir_interpreter")
            self.assertTrue((Path(output) / "Settlement.lean").is_file())
            self.assertTrue((Path(output) / "typed-ir.json").is_file())
            self.assertEqual(result["results"]["comparison"]["closing_unpaid"], "10")

    def test_native_threshold_equality_half_even_and_no_automatic_issue(self):
        for data, withheld, due in [(unissued(("0.01",), rate="0.5"), "0", "0"),
                                    (unissued(("0.03",), rate="0.5"), "0.02", "0"),
                                    (unissued(("25",), rate="0"), "0", "25"),
                                    (unissued((), rate="1", minimum="0"), "0", "0")]:
            with self.subTest(amounts=data["earned"]):
                result = self.run_fixture(data, "compare")
                self.controls(data, result)
                values = result["results"]["comparison"]
                self.assertEqual((values["withheld"], values["new_eligible_due"], values["new_issued"]),
                                 (withheld, due, "0"))
                self.assertEqual(values["payment_evidence_status"], "complete_no_events")

    def test_native_three_period_actual_state_carry_10_19_17(self):
        first_data = fixture()
        first = self.run_fixture(first_data, "compare")
        self.controls(first_data, first)
        middle_data, cells = self.carried(first_data, first)
        middle = self.run_fixture(middle_data, "compare", cells=cells)
        self.controls(middle_data, middle)
        last_data, cells = self.final_period(middle_data, middle)
        last = self.run_fixture(last_data, "compare", cells=cells)
        self.controls(last_data, last)
        self.assertEqual([x["results"]["comparison"]["closing_unpaid"] for x in [first, middle, last]],
                         ["10", "19", "17"])
        self.assertEqual(last["results"]["comparison"]["issuance_candidate"], "27")
        self.assertEqual([x["id"] for x in last["closing_state"][0]["quantity"]["issued_obligations"]], ["issue-q3"])

    def test_native_old_issue_paid_below_new_threshold(self):
        original = fixture()
        first = self.run_fixture(original)
        data, cells = self.carried(original, first, amounts=())
        data["payments"] = [{**deepcopy(original["payments"][0]), "id": "old-payment-q2", "amount": "5",
                             "paid_date": "2026-06-30", "observed_at": "2026-07-01T00:00:00Z", "evidence_ref": "source-q2"}]
        data["applications"] = [{**deepcopy(original["applications"][0]), "id": "old-application-q2", "amount": "5",
                                 "payment_id": "old-payment-q2", "observed_at": "2026-07-01T01:00:00Z", "evidence_ref": "source-q2"}]
        result = self.run_fixture(data, "compare", cells=cells)
        self.controls(data, result)
        self.assertEqual([result["results"]["comparison"][key] for key in
                          ["new_eligible_due", "total_eligible_due", "actual_paid", "closing_unpaid"]],
                         ["0", "10", "5", "5"])

    def test_native_financial_failures_are_atomic_not_zero_paid(self):
        variants = [
            ("SETTLEMENT_DUPLICATE_ID", lambda d: d["earned"].append(deepcopy(d["earned"][0]))),
            ("SETTLEMENT_PAYMENT_POPULATION_REQUIRED", lambda d: d.update(evidence=d["evidence"][:1])),
            ("SETTLEMENT_OBLIGATION_OVERPAYMENT", lambda d: (d["payments"][0].update(amount="91"), d["applications"][0].update(amount="91"))),
            ("SETTLEMENT_MINOR_UNIT", lambda d: d["earned"][0].update(amount="0.006")),
        ]
        for code, mutate in variants:
            with self.subTest(code=code):
                data = fixture()
                mutate(data)
                result = self.blocked(data, code, "compare")
                self.assertEqual(result["trace_origin"], "native_ir_interpreter")
                if code == "SETTLEMENT_PAYMENT_POPULATION_REQUIRED":
                    self.assertEqual(result["payment_evidence_status"], "no_event_supplied")

    def test_reference_duplicate_categories_and_prior_history(self):
        for kind in ["earned", "issued", "payments", "applications", "evidence"]:
            data = fixture()
            data[kind].append(deepcopy(data[kind][0]))
            with self.subTest(kind=kind):
                self.blocked(data, "SETTLEMENT_DUPLICATE_ID")
        original = fixture()
        first = self.run_fixture(original)
        data, cells = self.carried(original, first)
        data["earned"][0]["id"] = "earned-q1-a"
        self.blocked(data, "SETTLEMENT_ALREADY_RECOGNIZED", cells=cells)

    def test_reference_scope_policy_minor_units_and_evidence(self):
        mutations = [
            lambda d: d["payments"][0]["scope"].update(pool_id="other"),
            lambda d: d["evidence"][0]["scope"].update(participant_id="other"),
            lambda d: d["earned"][0].update(evidence_ref="missing"),
            lambda d: d["earned"][0].update(observed_at=d["cutoff"]),
            lambda d: d["evidence"][-1]["period"].update(end="2026-07-01"),
            lambda d: d["terms"].update(rounding="half_away_from_zero"),
            lambda d: d["opening_state"].update(purpose="reserve"),
            lambda d: d["opening_state"].update(policy_revision="2"),
            lambda d: d["opening_state"].update(boundary="2026-01-02"),
            lambda d: d["terms"].update(minimum_payout="0.005"),
        ]
        for mutate in mutations:
            data = fixture()
            mutate(data)
            with self.subTest(data=data):
                self.blocked(data)

    def test_reference_application_links_order_conservation_and_issue_amount(self):
        mutations = [
            lambda d: d["applications"][0].update(payment_id="missing"),
            lambda d: d["applications"][0].update(issued_id="missing"),
            lambda d: d["applications"][0].update(amount="79"),
            lambda d: d.update(applications=[]),
            lambda d: d["issued"][0].update(amount="89"),
            lambda d: d["payments"][0].update(paid_date="2026-03-29"),
            lambda d: d["applications"][0].update(observed_at="2026-03-31T23:00:00Z"),
        ]
        for mutate in mutations:
            data = fixture()
            mutate(data)
            with self.subTest(data=data):
                self.blocked(data)

    def test_native_text_identity_and_reference_permutation(self):
        data = fixture()
        data["earned"][0]["id"] = "application:q1-\u00e9"
        first = self.run_fixture(data, "compare")
        self.controls(data, first)
        data["earned"].reverse()
        second = self.run_fixture(data)
        self.controls(data, second)
        self.assertEqual(first["results"], second["results"])
        self.assertEqual(first["closing_state"][0]["quantity"], second["closing_state"][0]["quantity"])
        self.assertIn(["earned", "application:q1-\u00e9"], first["closing_state"][0]["quantity"]["recognized_ids"])

    def test_missing_population_artifact_matches_unfinalized_status(self):
        data = fixture()
        data["evidence"] = data["evidence"][:1]
        with tempfile.TemporaryDirectory(dir=self.root) as output:
            result = self.run_fixture(data, output=output)
            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["payment_evidence_status"], "no_event_supplied")
            self.assertNotIn("result_digest", result)
            self.assertFalse(result["results"])
            self.assertFalse(result["closing_state"])
            self.assertEqual(read_json(Path(output) / "result.json"), result)
            self.assertEqual(read_json(Path(output) / "results.json"), {})
            self.assertEqual(read_json(Path(output) / "closing-state.json"), [])

    def test_canonical_predecessor_reference_and_exact_snapshot(self):
        original = fixture()
        first = self.run_fixture(original)
        data, cells = self.carried(original, first)
        data["prior_result"].pop("result_ref")
        with self.assertRaisesRegex(ValueError, "SETTLEMENT_CANONICAL_PREDECESSOR_REQUIRED"):
            self.run_fixture(data, cells=cells)
        data, cells = self.carried(original, first)
        data["prior_result"]["result_ref"] = "result@sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "SETTLEMENT_CANONICAL_PREDECESSOR_MISMATCH"):
            self.run_fixture(data, cells=cells)
        data, cells = self.carried(original, first)
        data["opening_state"]["deferred_unissued"] = "1"
        self.blocked(data, "SETTLEMENT_OPENING_SNAPSHOT", cells=cells)
        data, cells = self.carried(original, first)
        data["prior_result"]["period"]["end"] = "2026-03-31"
        self.blocked(data, "SETTLEMENT_PREDECESSOR_MISMATCH", cells=cells)

    def test_adapter_chronology_exact_transport_and_unknown_fields(self):
        data = fixture()
        data["payments"][0]["observed_at"] = "2026-03-30T23:00:00Z"
        with self.assertRaisesRegex(ValueError, "SETTLEMENT_OBSERVATION_BEFORE_EVENT"):
            self.run_fixture(data)
        for value in [0.1, True, 1, "1e-1"]:
            data = unissued()
            data["terms"]["withholding_rate"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "SETTLEMENT_EXACT_VALUE_REQUIRED"):
                self.run_fixture(data)
        data = unissued(("0.03",), rate="2/4")
        self.controls(data, self.run_fixture(data))
        data = fixture()
        data["earned"][0]["unreviewed_field"] = "ignored?"
        with self.assertRaisesRegex(ValueError, "SETTLEMENT_RECORD_FIELDS"):
            self.run_fixture(data)


if __name__ == "__main__":
    unittest.main()
