"""Independent controls for generic canonical synthetic mechanism registrations.

Expected quantities below are hand-authored controls, not results obtained from
the registration builder or either execution backend. CORR checks a supplied
revision reconciliation; it does not test full historical restatement.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from spl_compiler.codecs import file_digest, money, read_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

FOLDER = ROOT / "cases/mechanisms"
NAMES = ["advance-issues", "reserve-vintage", "correction-payments"]


class CanonicalMechanismTests(unittest.TestCase):
    def package(self, name):
        return read_json(FOLDER / (name + "-module-package.json"))

    def run_reference(self, name, package=None, artifact_dir=None):
        package = self.package(name) if package is None else package
        return run_module_package(bind_module_package(package, ROOT), ROOT,
                                  backend="reference", artifact_dir=artifact_dir)

    def assert_blocked(self, result, code):
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        for field, expected in [("results", {}), ("statements", []), ("detail", []),
                                ("closing_state", []), ("reconciliation", {})]:
            self.assertEqual(result[field], expected)

    def assert_baseline(self, name, result):
        self.assertEqual(result["diagnostics"], [], result)
        self.assertEqual(result["status"], "calculated")
        self.assertEqual(result["issuance_status"], "unissued")
        if name == "advance-issues":
            line = result["results"]["advances"]
            self.assertEqual({key: line[key] for key in ["opening_balance", "additions", "available", "earned", "recovered", "payable", "closing_balance"]},
                {"opening_balance": "0", "additions": "15000", "available": "15000", "earned": "10000", "recovered": "10000", "payable": "0", "closing_balance": "5000"})
            self.assertEqual(result["closing_state"][0]["quantity"], "5000")
            self.assertEqual(result["closing_state"][0]["movement"],
                {"kind": "net_change", "opening": "0", "net_change": "5000", "closing": "5000"})
        elif name == "reserve-vintage":
            self.assertEqual(result["results"]["reserve_ledger"]["closing_balance"], "20")
            self.assertEqual({row["vintage_id"]: row["closing_balance"] for row in result["results"]["reserve_vintage_ledger"]},
                {"vintage-1": "0", "vintage-2": "20"})
            self.assertEqual({row["vintage_id"]: row["balance"] for row in result["closing_state"][0]["quantity"]},
                {"vintage-1": money("0"), "vintage-2": money("20")})
            self.assertEqual(result["closing_state"][0]["movement"]["kind"], "transition")
            self.assertNotIn("payable", result["results"]["reserve_ledger"])
        else:
            line = result["results"]["obligation_reconciliation"]
            self.assertEqual({key: line[key] for key in ["original_issued", "revised_entitlement", "correction_delta", "actual_paid", "remaining_obligation"]},
                {"original_issued": "100", "revised_entitlement": "90", "correction_delta": "-10", "actual_paid": "80", "remaining_obligation": "10"})
            self.assertEqual(result["closing_state"], [])
            self.assertNotIn("payable", line)

    def test_registered_pins_complete_policy_and_reference_controls(self):
        for name in NAMES:
            with self.subTest(name=name):
                package = self.package(name)
                resolved = resolve_module(package["module_ref"], ROOT)
                policy = resolved.descriptor["policy"]
                self.assertEqual(policy["review_status"], "proposed")
                self.assertEqual(policy["evidence_class"], "synthetic")
                self.assertEqual({row["decision_id"] for row in package["decisions"]}, set(policy["decision_ids"]))
                self.assertEqual(resolved.descriptor["source"]["sha256"], file_digest(FOLDER / (name + ".spl")))
                self.assertEqual(package["manifest"]["module_closure"], resolved.references)
                self.assert_baseline(name, self.run_reference(name))

    def test_native_interpreter_generated_and_reference_controls(self):
        for name in NAMES:
            with self.subTest(name=name):
                package = bind_module_package(self.package(name), ROOT)
                result = run_module_package(package, ROOT, backend="compare")
                self.assert_baseline(name, result)
                self.assertTrue(result["verification"]["reference_agrees"])

    def test_published_advance_state_carries_to_next_quarter(self):
        first = self.run_reference("advance-issues")
        self.assert_baseline("advance-issues", first)
        package = self.package("advance-issues")
        package["inputs"]["issues"] = []
        package["inputs"]["evidence"] = []
        package["inputs"]["earned"] = money("2000")
        package["inputs"]["scope"]["period"] = {"start": "2026-07-01", "end": "2026-10-01"}
        package["manifest"]["period"] = deepcopy(package["inputs"]["scope"]["period"])
        package["parameters"]["observation_cutoff"] = package["manifest"]["cutoff"] = "2026-10-03T00:00:00Z"
        cell = deepcopy(first["closing_state"][0])
        cell.pop("movement")
        package["state_cells"] = [cell]
        result = self.run_reference("advance-issues", package)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["results"]["advances"]["opening_balance"], "5000")
        self.assertEqual(result["results"]["advances"]["recovered"], "2000")
        self.assertEqual(result["closing_state"][0]["quantity"], "3000")
        self.assertEqual(cell["prior_result_ref"], "result@sha256:" + first["semantic_run_digest"])

    def test_structured_reserve_state_carries_and_liquidates(self):
        first = self.run_reference("reserve-vintage")
        self.assert_baseline("reserve-vintage", first)
        package = self.package("reserve-vintage")
        package["inputs"]["scope"]["period"] = {"start": "2026-07-01", "end": "2026-10-01"}
        package["manifest"]["period"] = deepcopy(package["inputs"]["scope"]["period"])
        package["parameters"]["observation_cutoff"] = package["manifest"]["cutoff"] = "2026-10-15T00:00:00Z"
        for collection in ["movements", "evidence"]:
            package["inputs"][collection] = package["inputs"][collection][1:]
            for row, value in zip(package["inputs"][collection], ["8", "12"]):
                row.update(vintage_id="vintage-2", effective_date="2026-08-01", observed_at="2026-08-02T00:00:00Z", amount=money(value))
        cell = deepcopy(first["closing_state"][0])
        cell.pop("movement")
        package["state_cells"] = [cell]
        result = self.run_reference("reserve-vintage", package)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["results"]["reserve_ledger"]["closing_balance"], "0")
        self.assertEqual([row["balance"] for row in result["closing_state"][0]["quantity"]], [money("0"), money("0")])
        self.assertEqual(cell["prior_result_ref"], "result@sha256:" + first["semantic_run_digest"])

    def test_wrong_scope_purpose_currency_and_evidence_are_atomic(self):
        for name, collection in [("advance-issues", "issues"), ("reserve-vintage", "movements"), ("correction-payments", "payments")]:
            with self.subTest(name=name):
                package = self.package(name)
                package["inputs"][collection][0]["pool_id"] = "unrelated"
                self.assert_blocked(self.run_reference(name, package), "MODULE_REFERENCE_SCOPE")
                package = self.package(name)
                package["scope"]["purpose"] = "another-purpose"
                self.assert_blocked(self.run_reference(name, package), "MODULE_SCOPE_MISMATCH")
                package = self.package(name)
                package["inputs"][collection][0]["amount"]["currency"] = "EUR"
                self.assert_blocked(self.run_reference(name, package), "CURRENCY_MISMATCH")
        for name, error in [("advance-issues", "ADV_ELIGIBLE_EVIDENCE_REQUIRED"), ("reserve-vintage", "RES_AUTHORITY_REQUIRED")]:
            package = self.package(name)
            package["inputs"]["evidence"][0]["approved"] = False
            self.assert_blocked(self.run_reference(name, package), error)
        package = self.package("correction-payments")
        package["inputs"]["payments"][0]["approved"] = False
        self.assert_blocked(self.run_reference("correction-payments", package), "CORR_PAYMENT_AUTHORITY_REQUIRED")

    def test_missing_evidence_and_undeclared_approval_are_atomic(self):
        for name, error in [("advance-issues", "ADV_FUNDING_EVIDENCE_REQUIRED"), ("reserve-vintage", "RES_EVIDENCE_REQUIRED")]:
            package = self.package(name)
            package["inputs"]["evidence"] = []
            self.assert_blocked(self.run_reference(name, package), error)
            package = self.package(name)
            package["parameters"]["authority"] = "invented-approval"
            self.assert_blocked(self.run_reference(name, package), "MODULE_PARAMETER_DOMAIN")

    def test_state_purpose_scope_boundary_and_duplicate_writer_are_atomic(self):
        for name in ["advance-issues", "reserve-vintage"]:
            for field, value, code in [("purpose", "unpaid_obligation", "MODULE_STATE_PURPOSE"),
                                      ("boundary", "2025-01-01", "MODULE_STATE_BOUNDARY")]:
                package = self.package(name)
                package["state_cells"][0][field] = value
                self.assert_blocked(self.run_reference(name, package), code)
            package = self.package(name)
            package["state_cells"][0]["scope"]["pool_id"] = "other-pool"
            self.assert_blocked(self.run_reference(name, package), "MODULE_STATE_SCOPE")
            package = self.package(name)
            package["state_cells"].append(deepcopy(package["state_cells"][0]))
            self.assert_blocked(self.run_reference(name, package), "MODULE_DUPLICATE_STATE_WRITER")

    def test_duplicate_events_and_unselected_overpayment_are_atomic(self):
        for name, collection in [("advance-issues", "issues"), ("reserve-vintage", "movements"), ("correction-payments", "payments")]:
            package = self.package(name)
            package["inputs"][collection].append(deepcopy(package["inputs"][collection][0]))
            self.assert_blocked(self.run_reference(name, package), "MODULE_DUPLICATE_KEY")
        package = self.package("correction-payments")
        package["inputs"]["revised_entitlement"] = money("70")
        self.assert_blocked(self.run_reference("correction-payments", package), "CORR_OVERPAYMENT_POLICY_REQUIRED")

    def test_source_specific_purpose_and_evidence_matches_remain_checked(self):
        for name, collection, field, error in [
            ("advance-issues", "issues", "balance_purpose", "ADV_ISSUE_WRONG_BALANCE"),
            ("reserve-vintage", "movements", "purpose", "RES_WRONG_PURPOSE")]:
            package = self.package(name)
            package["inputs"][collection][0][field] = "unpaid_obligation"
            self.assert_blocked(self.run_reference(name, package), error)
        for name, error in [("advance-issues", "ADV_EVIDENCE_MISMATCH"), ("reserve-vintage", "RES_EVIDENCE_MISMATCH")]:
            package = self.package(name)
            package["inputs"]["evidence"][0]["amount"] = money("1")
            self.assert_blocked(self.run_reference(name, package), error)

    def test_instant_cutoff_and_preserved_correction_date_policy(self):
        package = self.package("advance-issues")
        package["inputs"]["issues"][0]["observed_at"] = package["parameters"]["observation_cutoff"]
        result = self.run_reference("advance-issues", package)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["results"]["advances"]["additions"], "0")
        self.assertFalse(result["results"]["advance_issue_audit"][0]["included"])
        package = self.package("reserve-vintage")
        package["inputs"]["evidence"][0]["observed_at"] = package["parameters"]["observation_cutoff"]
        self.assert_blocked(self.run_reference("reserve-vintage", package), "RES_EVIDENCE_NOT_AVAILABLE")
        package = self.package("correction-payments")
        self.assertNotIn("observed_at", package["inputs"]["payments"][0])
        package["inputs"]["payments"][0]["paid_date"] = package["parameters"]["payment_cutoff"]
        self.assert_blocked(self.run_reference("correction-payments", package), "CORR_PAYMENT_AFTER_CUTOFF")

    def test_stale_decision_and_manifest_revisions_are_atomic(self):
        for name in NAMES:
            package = self.package(name)
            package["decisions"][0]["policy_revision"] = "obsolete"
            self.assert_blocked(self.run_reference(name, package), "MODULE_POLICY_MISMATCH")
            package = self.package(name)
            package["decisions"] = []
            self.assert_blocked(self.run_reference(name, package), "MODULE_POLICY_REQUIRED")
            package = bind_module_package(self.package(name), ROOT)
            package["manifest"]["compiler_build"] = "obsolete"
            self.assert_blocked(run_module_package(package, ROOT, backend="reference"), "MANIFEST_DIGEST_MISMATCH")

    def test_stale_file_pin_overwrites_published_outputs_atomically(self):
        name = "advance-issues"
        package = self.package(name)
        resolved = resolve_module(package["module_ref"], ROOT)
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "registry"
            output = Path(directory) / "published"
            for entry in resolved.closure:
                for field in ["descriptor_path", "source_path", "policy_path"]:
                    source = entry[field]
                    target = registry / source.relative_to(ROOT)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(source.read_bytes())
            package = bind_module_package(package, registry)
            self.assert_baseline(name, run_module_package(package, registry, backend="reference", artifact_dir=output))
            policy = registry / resolved.policy_path.relative_to(ROOT)
            policy.write_bytes(policy.read_bytes() + b"\nChanged revision without a new pin.\n")
            result = run_module_package(package, registry, backend="reference", artifact_dir=output)
            self.assert_blocked(result, "MODULE_DEPENDENCY_DIGEST")
            self.assertEqual(read_json(output / "statement.json"), [])
            self.assertEqual(read_json(output / "closing-state.json"), [])
            self.assertEqual(read_json(output / "result.json")["status"], "blocked")


if __name__ == "__main__":
    unittest.main()
