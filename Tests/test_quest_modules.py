"""Registered Quest transport, exact policy boundaries and provenance checks."""
from copy import deepcopy
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.quest import build_modules as quest
from cases.r1 import build_modules as registration
from oracles.quest import quest_two_flow
from spl_compiler.codecs import DataError, canonical, exact, file_digest, read_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package


class QuestModuleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.folder = self.root / "cases/quest"
        self.folder.mkdir(parents=True)
        for name in ["power.spl", "charge.spl", "policy.md", "calendar-facts.json", "source-index.json", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/quest" / name, self.folder / name)
        self.addCleanup(patch.stopall)
        patch.object(quest, "ROOT", self.root).start()
        patch.object(quest, "FOLDER", self.folder).start()
        patch.object(registration, "ROOT", self.root).start()
        self.reference = quest.register_quest()
        self.neutral = read_json(self.folder / "neutral.json")
        self.package = quest.quest_package(self.neutral, reference=self.reference)

    def run_reference(self, package=None):
        return run_module_package(package or self.package, self.root, backend="reference")

    def blocked(self, package, code):
        result = self.run_reference(package)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        self.assertEqual(result["diagnostics"][0]["code"], code, result["diagnostics"])
        for name in ["results", "statements", "closing_state"]:
            self.assertFalse(result[name])
        return result

    def fixture(self, principal="1000", annual_target="0.2", due="2026-01-01", paid="2026-07-02"):
        data = deepcopy(self.neutral)
        data["case_id"] += "-VARIANT"
        data["terms"]["annual_target"] = annual_target
        data["period"] = {"start": "2026-01-01", "end": "2027-01-03"}
        data["cutoff"] = "2027-01-04T00:00:00Z"
        observed = "2027-01-03T00:00:00Z"
        for collection in ["obligations", "payments", "applications"]:
            data[collection][0].update(amount=principal, observed_at=observed)
        data["obligations"][0]["due_date"] = due
        data["payments"][0]["paid_date"] = paid
        data["applications"][0]["effective_date"] = paid
        data["evidence"] = [{**row, "observed_at": observed} for row in data["evidence"][:3]]
        truth = {row["date"]: row["ordinal"] for row in read_json(self.folder / "calendar-facts.json")["facts"]}
        data["calendar"]["observations"] = []
        for index, day in enumerate(dict.fromkeys([due, paid])):
            evidence = "QE-CALENDAR-" + str(index)
            data["calendar"]["observations"].append({"id": "QCO-" + str(index), "date": day, "ordinal": truth[day],
                "observed_at": observed, "evidence_id": evidence, "source_ref": data["calendar"]["source_ref"]})
            data["evidence"].append({"id": evidence, "observed_at": observed, "source_ref": data["calendar"]["source_ref"]})
        return data

    def assert_controls(self, result, data):
        self.assertEqual(result["diagnostics"], [])
        expected = quest_two_flow(data)
        comparison = result["results"]["comparison"]
        for name in ["additional_charge", "actual_principal_paid", "elapsed_days", "annual_target"]:
            self.assertEqual(exact(comparison[name]), expected[name])
        certificate = result["results"]["certificate"]
        self.assertEqual(exact(certificate["minimum_charge"]), expected["minimum_charge"])
        for name in ["lower_ok", "upper_ok", "minimum_ok", "predecessor_ok"]:
            self.assertTrue(certificate[name], name)
        for name in ["monthly_status", "combined_status", "additional_payment_status", "evidence_class", "policy_status"]:
            self.assertEqual(comparison[name], expected[name])
        self.assertEqual(result["closing_state"], [])
        self.assertEqual(result["issuance_status"], "unissued")

    def test_baseline_exact_oracle_and_preserved_provenance(self):
        result = self.run_reference()
        self.assert_controls(result, self.neutral)
        self.assertEqual(result["results"]["comparison"]["additional_charge"], "95.17")
        self.assertEqual(result["results"]["certificate"]["minimum_charge"], "95.18")
        observations = result["results"]["observations"]
        self.assertEqual(observations["due_date"], self.neutral["obligations"][0]["due_date"])
        self.assertEqual(observations["paid_date"], self.neutral["payments"][0]["paid_date"])
        self.assertEqual(observations["clause_source"], quest.SOURCE_REF)
        self.assertEqual(observations["calendar_source_sha256"], file_digest(self.folder / "calendar-facts.json"))
        self.assertEqual(observations["evidence"], self.package["evidence"]["evidence"])
        self.assertEqual(observations["payments"][0]["economic_event_id"], self.neutral["payments"][0]["economic_event_id"])
        self.assertTrue(result["trace"])
        review = result["policy_review"]
        self.assertIn("quest:power@1:pow", review["function_sources"])
        self.assertEqual(review["modules"][-1]["policy"]["evidence_class"], "synthetic")
        self.assertEqual(review["actual_parameters"]["rounding"], "half_even")
        self.assertEqual([reference["id"] for reference in result["module_closure"]], ["quest:power", "quest:charge"])

    def test_ties_zero_full_year_and_nonzero_due_date(self):
        for principal, rate, due, paid, charge in [
            ("0.01", "0.5", "2026-01-01", "2027-01-01", "0"),
            ("0.03", "0.5", "2026-01-01", "2027-01-01", "0.02"),
            ("1000", "0.2", "2026-01-01", "2026-01-01", "0"),
            ("1000", "0.2", "2026-01-01", "2027-01-01", "200"),
            ("500", "0.1", "2026-01-01", "2026-06-30", "24.06"),
            ("1000", "0.2", "2026-06-30", "2026-07-02", "1")]:
            data = self.fixture(principal, rate, due, paid)
            result = self.run_reference(quest.quest_package(data, reference=self.reference))
            self.assert_controls(result, data)
            self.assertEqual(result["results"]["comparison"]["additional_charge"], charge)
            if due == "2026-06-30":
                self.assertEqual(result["results"]["comparison"]["elapsed_days"], "2")
                self.assertEqual(len(data["calendar"]["observations"]), 2)

    def test_scopes_links_full_payment_and_original_cardinality(self):
        mutations = [
            (lambda p: p["inputs"]["payments"][0]["scope"].update(agreement_id="foreign"), "MODULE_REFERENCE_SCOPE"),
            (lambda p: p["inputs"]["payments"][0]["scope"].update(currency="EUR"), "QUEST_FLOW_SCOPE"),
            (lambda p: p["inputs"]["applications"][0].update(payment_id="foreign"), "MODULE_REFERENCE_SCOPE"),
            (lambda p: p["inputs"]["payments"][0]["amount"].update(value="999"), "QUEST_FULL_PRINCIPAL_REQUIRED"),
            (lambda p: p["inputs"]["applications"][0]["amount"].update(currency="EUR"), "CURRENCY_MISMATCH"),
            (lambda p: p["inputs"]["payments"].append(deepcopy(p["inputs"]["payments"][0])), "MODULE_CARDINALITY"),
            (lambda p: p["inputs"].update(obligations=[]), "MODULE_CARDINALITY"),
            (lambda p: p["inputs"]["applications"][0].update(effective_date="2026-07-01"), "QUEST_FLOW_DATE")]
        for mutate, code in mutations:
            package = deepcopy(self.package)
            mutate(package)
            self.blocked(package, code)

    def test_pinned_policy_calendar_parameters_and_truth(self):
        for name, value in [("rounding", "half_away_from_zero"), ("day_count", "ACT/360"), ("quantum", {"value": "0.02", "currency": "USD"}),
                            ("policy_id", "foreign"), ("policy_revision", "2"), ("clause_source", "unhashed-url"),
                            ("clause_locator", "wrong paragraph"), ("calendar_version", "2"), ("calendar_source_sha256", "0" * 64)]:
            package = deepcopy(self.package)
            package["parameters"][name] = value
            self.blocked(package, "MODULE_PARAMETER_DOMAIN")
        package = deepcopy(self.package)
        package["parameters"]["calendar_truth"][1]["ordinal"] = "181"
        self.blocked(package, "MODULE_PARAMETER_DOMAIN")
        package = deepcopy(self.package)
        package["inputs"]["calendar"][1]["ordinal"] = "183"
        self.blocked(package, "QUEST_CALENDAR_ORDINAL")
        neutral = deepcopy(self.neutral)
        neutral["calendar"]["observations"][1]["ordinal"] = "183"
        with self.assertRaises(DataError) as error:
            quest.quest_package(neutral, reference=self.reference)
        self.assertEqual(error.exception.code, "QUEST_CALENDAR_FACT")

    def test_missing_duplicate_calendar_evidence_sources_and_exact_cutoff(self):
        mutations = [
            (lambda p: p["inputs"]["calendar"].pop(), "QUEST_PAID_CALENDAR_REQUIRED"),
            (lambda p: p["inputs"]["calendar"].append(deepcopy(p["inputs"]["calendar"][0])), "MODULE_DUPLICATE_KEY"),
            (lambda p: p["inputs"]["payments"][0].update(observed_at=p["manifest"]["cutoff"]), "QUEST_FLOW_AFTER_CUTOFF"),
            (lambda p: p["evidence"]["evidence"][0].update(observed_at=p["manifest"]["cutoff"]), "EVIDENCE_AFTER_CUTOFF"),
            (lambda p: p["inputs"]["calendar"][0].update(evidence_id="missing"), "MODULE_REFERENCE_SCOPE"),
            (lambda p: p["evidence"]["evidence"][0].update(source_ref="foreign-source"), "QUEST_EVIDENCE_SOURCE")]
        for mutate, code in mutations:
            package = deepcopy(self.package)
            mutate(package)
            self.blocked(package, code)
        package = deepcopy(self.package)
        package["evidence"]["evidence"].append({**deepcopy(package["evidence"]["evidence"][0]), "evidence_id": "unused", "evidence_ref": "unused",
                                              "observed_at": package["manifest"]["cutoff"]})
        self.blocked(package, "EVIDENCE_AFTER_CUTOFF")

    def test_declared_search_domain_and_clause_policy_pins(self):
        package = deepcopy(self.package)
        package["parameters"]["annual_target"] = "-0.1"
        self.blocked(package, "MODULE_PARAMETER_DOMAIN")
        package = deepcopy(self.package)
        for collection in ["obligations", "payments", "applications"]:
            package["inputs"][collection][0]["amount"]["value"] = "1000000000"
        self.blocked(package, "QUEST_CENT_SEARCH_DOMAIN")
        policy = self.folder / "policy.md"
        policy.write_text(policy.read_text(encoding="utf-8") + "\n", encoding="utf-8", newline="\n")
        self.blocked(self.package, "MODULE_DEPENDENCY_DIGEST")

    def test_transport_contains_no_solved_financial_answer_and_no_state(self):
        self.assertEqual(self.package["state_cells"], [])
        self.assertEqual(resolve_module(self.reference, self.root).descriptor["state"], [])
        bindings = quest.quest_bindings(self.package)
        self.assertEqual(bindings["openings"], {})
        for forbidden in ["additional_charge", "target_power", "chosen_index", "elapsed_days", "minimum_charge"]:
            self.assertNotIn(forbidden, bindings["inputs"])
        neutral = deepcopy(self.neutral)
        neutral["elapsed_days"] = "182"
        with self.assertRaises(DataError) as error:
            quest.quest_package(neutral, reference=self.reference)
        self.assertEqual(error.exception.code, "QUEST_NEUTRAL_SHAPE")

    def test_strict_exact_neutral_codec_and_rational_normalization(self):
        neutral = deepcopy(self.neutral)
        neutral["terms"]["annual_target"] = {"numerator": "1", "denominator": "5"}
        neutral["terms"]["quantum"] = {"numerator": "1", "denominator": "100"}
        for collection in ["obligations", "payments", "applications"]:
            neutral[collection][0]["amount"] = {"numerator": "1000", "denominator": "1"}
        package = quest.quest_package(neutral, reference=self.reference)
        self.assertEqual(package["parameters"]["annual_target"], "0.2")
        self.assertEqual(package["parameters"]["quantum"], {"value": "0.01", "currency": "USD"})
        for collection in ["obligations", "payments", "applications"]:
            self.assertEqual(package["inputs"][collection][0]["amount"], {"value": "1000", "currency": "USD"})
        result = self.run_reference(package)
        self.assert_controls(result, neutral)
        self.assertEqual(result["results"]["comparison"]["additional_charge"], "95.17")
        for target in ["amount", "annual_target", "quantum"]:
            for value, code in [(1, "INVALID_EXACT_NUMBER"), (True, "INVALID_EXACT_NUMBER"), (0.2, "INVALID_EXACT_NUMBER"),
                                ({"numerator": "2", "denominator": "10"}, "NONCANONICAL_RATIONAL")]:
                invalid = deepcopy(self.neutral)
                if target == "amount":
                    invalid["obligations"][0]["amount"] = value
                else:
                    invalid["terms"][target] = value
                with self.assertRaises(DataError) as error:
                    quest.quest_package(invalid, reference=self.reference)
                self.assertEqual(error.exception.code, code, (target, value))

    def test_native_registered_baseline_and_tie_match_independent_controls(self):
        for data in [self.neutral, self.fixture("0.01", "0.5", "2026-01-01", "2027-01-01"),
                     self.fixture("1000", "0.2", "2026-06-30", "2026-07-02")]:
            result = run_module_package(quest.quest_package(data, reference=self.reference), self.root, backend="compare")
            self.assert_controls(result, data)
            self.assertTrue(result["verification"]["reference_agrees"])
            self.assertEqual(result["trace_origin"], "native_ir_interpreter")


if __name__ == "__main__":
    unittest.main()
