"""CORR-01 neutral oracle, registered source and canonical restatement boundary."""
from copy import deepcopy
import os
import unittest

from cases.revision.build_modules import FOLDER, ROOT, register_revision, revision_package
from oracles.revision import RevisionError, restate
from spl_compiler.codecs import exact, read_json
from spl_compiler.modules import bind_module_package, run_module_package


class RevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = register_revision()

    def fixture(self):
        return read_json(FOLDER / "neutral.json")

    def run_case(self, fixture=None, package=None, *, output=None):
        # Set SPL_REVISION_REFERENCE_ONLY=1 while another agent changes native code.
        backend = "reference" if os.environ.get("SPL_REVISION_REFERENCE_ONLY") == "1" else "compare"
        return run_module_package(package or revision_package(fixture, reference=self.reference), ROOT,
                                  backend=backend, artifact_dir=output)

    def blocked(self, result, code):
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        for field in ["statements", "closing_state"]:
            self.assertEqual(result[field], [])
        self.assertEqual(result["results"], {})

    def test_neutral_original_and_revised_with_actual_cash(self):
        fixture = self.fixture()
        expected = restate(fixture)
        self.assertEqual([expected[key] for key in ["original_recomputed", "revised_entitlement", "correction_delta", "actual_paid_asof", "outstanding_asof"]], [100, 90, -10, 80, 10])
        result = self.run_case(fixture)
        self.assertEqual(result["status"], "calculated", result)
        self.assertEqual(result["diagnostics"], [])
        comparison = result["results"]["comparison"]
        for key, value in expected.items():
            if key != "recognized":
                self.assertEqual(exact(comparison[key]), value, key)
        self.assertEqual(comparison["original_run_id"], fixture["original"]["run_id"])
        self.assertEqual(comparison["opening_snapshot_id"], fixture["original"]["opening_snapshot_id"])
        cells = {row["opening_port"]: row for row in result["closing_state"]}
        self.assertEqual(exact(cells["entitlement"]["quantity"]), 90)
        self.assertEqual(cells["recognized"]["quantity"], ["correction-01"])
        self.assertEqual(cells["entitlement"]["boundary"], fixture["period"]["end"])
        self.assertEqual(comparison["actual_payment_at"], fixture["payment"]["disbursed_at"])
        self.assertEqual(result["results"]["observations"]["authorization"]["observed_at"], fixture["authorization"]["observed_at"])
        self.assertEqual(result["issuance_status"], "unissued")

    def test_unauthorized_prospective_and_missing_evidence(self):
        for mutation, code in [
            (lambda f: f["authorization"].update(authorized=False), "REV_AUTHORIZATION_REQUIRED"),
            (lambda f: f["authorization"].update(route="prospective_adjustment"), "REV_AUTHORIZATION_REQUIRED"),
            (lambda f: f["original"].update(opening_prepaid="1"), "REV_ORIGINAL_OPENING_REQUIRED"),
            (lambda f: f["payment"].update(evidence_id="missing"), "REV_EVIDENCE_REQUIRED")]:
            with self.subTest(code=code):
                fixture = self.fixture()
                mutation(fixture)
                with self.assertRaises(RevisionError):
                    restate(fixture)
                self.blocked(self.run_case(fixture), code)

    def test_stale_original_replacement_obligation_and_bank_refs(self):
        for section, field, code in [
            ("authorization", "original_run_id", "REV_ORIGINAL_LINEAGE"),
            ("authorization", "original_opening_id", "REV_ORIGINAL_LINEAGE"),
            ("authorization", "replacement_id", "REV_REPLACEMENT_LINEAGE"),
            ("payment", "obligation_id", "REV_PAYMENT_LINEAGE"),
            ("payment", "original_run_id", "REV_PAYMENT_LINEAGE"),
            ("application", "bank_id", "REV_APPLICATION_LINEAGE")]:
            with self.subTest(field=field):
                fixture = self.fixture()
                fixture[section][field] = "stale-identity"
                with self.assertRaises(RevisionError):
                    restate(fixture)
                self.blocked(self.run_case(fixture), code)

    def test_no_duplicate_or_replayed_correction(self):
        fixture = self.fixture()
        fixture["corrections"].append(deepcopy(fixture["corrections"][0]))
        with self.assertRaises(RevisionError):
            restate(fixture)
        self.blocked(self.run_case(fixture), "DUPLICATE_MAP_KEY")
        fixture = self.fixture()
        fixture["recognized"] = ["correction-01"]
        with self.assertRaises(RevisionError):
            restate(fixture)
        self.blocked(self.run_case(fixture), "REV_CORRECTION_ALREADY_RECOGNIZED")
        fixture = self.fixture()
        extra = deepcopy(fixture["corrections"][0])
        extra["id"] = "second-correction"
        fixture["corrections"].append(extra)
        self.blocked(self.run_case(fixture), "REV_ONE_CORRECTION_REQUIRED")

    def test_cash_control_and_overpayment_policy(self):
        for mutate, code in [
            (lambda f: f["corrections"][0].update(reallocated_amount="49"), "REV_CASH_CONSERVATION"),
            (lambda f: f["bank"].update(amount="450"), "REV_ORIGINAL_CASH_CONTROL"),
            (lambda f: f["original"].update(issued="99"), "REV_ORIGINAL_RESULT_MISMATCH"),
            (lambda f: f["payment"].update(amount="91"), "REV_OVERPAYMENT_POLICY_UNSUPPORTED")]:
            fixture = self.fixture()
            mutate(fixture)
            with self.assertRaises(RevisionError):
                restate(fixture)
            self.blocked(self.run_case(fixture), code)

    def test_exact_strict_cutoff_and_affected_period(self):
        fixture = self.fixture()
        fixture["authorization"]["observed_at"] = fixture["cutoff"]
        with self.assertRaises(RevisionError):
            restate(fixture)
        self.blocked(self.run_case(fixture), "REV_AUTHORIZATION_CUTOFF")
        fixture = self.fixture()
        fixture["corrections"][0]["observed_at"] = fixture["cutoff"]
        self.blocked(self.run_case(fixture), "REV_CORRECTION_CUTOFF")
        fixture = self.fixture()
        fixture["cutoff"] = "2027-02-04T11:00:00.0000000002Z"
        self.assertEqual(restate(fixture)["outstanding_asof"], 10)
        result = self.run_case(fixture)
        self.assertEqual(result["status"], "calculated", result)
        fixture = self.fixture()
        fixture["corrections"][0]["effective_date"] = fixture["period"]["end"]
        self.blocked(self.run_case(fixture), "REV_AFFECTED_PERIOD")

    def test_original_opening_provenance_and_prior_closing_cannot_be_used(self):
        package = revision_package(reference=self.reference)
        package["state_cells"][0]["provenance_ref"] = "old-closing-snapshot"
        self.blocked(self.run_case(package=package), "MODULE_SCOPE_MISMATCH")
        package = revision_package(reference=self.reference)
        package["state_cells"][0]["quantity"] = "100"
        self.blocked(self.run_case(package=package), "REV_ORIGINAL_OPENING_REQUIRED")
        package = revision_package(reference=self.reference)
        package["state_cells"][0]["boundary"] = package["manifest"]["period"]["end"]
        self.blocked(self.run_case(package=package), "MODULE_STATE_BOUNDARY")

    def test_authorization_and_actual_cash_keep_exact_selected_scope(self):
        for section in ["original", "authorization", "payment"]:
            fixture = self.fixture()
            fixture[section]["participant_id"] = "unrelated-participant"
            with self.assertRaises(RevisionError):
                restate(fixture)
            package = revision_package(fixture, reference=self.reference)
            package["scope"]["participant_ids"].append("unrelated-participant")
            self.blocked(self.run_case(package=package), "MODULE_SCOPE_MISMATCH")

    def test_deterministic_reconstruction_and_preview_has_no_consumable_state(self):
        fixture = self.fixture()
        first = self.run_case(fixture)
        second = self.run_case(fixture)
        self.assertEqual(first["results"], second["results"])
        self.assertEqual(first["closing_state"], second["closing_state"])
        self.assertEqual(len(next(row for row in second["closing_state"] if row["opening_port"] == "recognized")["quantity"]), 1)
        package = revision_package(reference=self.reference)
        package["manifest"]["mode"] = "preview"
        result = self.run_case(package=bind_module_package(package, ROOT))
        self.assertEqual(result["closing_state"], [])

    def test_replacement_facts_and_rate_are_executed(self):
        fixture = self.fixture()
        fixture["corrections"][0].update(amount="460", reallocated_amount="40")
        self.assertEqual(restate(fixture)["outstanding_asof"], 12)
        result = self.run_case(fixture)
        self.assertEqual(exact(result["results"]["comparison"]["outstanding_asof"]), 12)


if __name__ == "__main__":
    unittest.main()
