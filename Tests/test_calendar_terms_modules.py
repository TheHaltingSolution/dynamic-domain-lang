"""Finite calendar canonical execution against independent original-row controls."""
import ast
from copy import deepcopy
from fractions import Fraction
from importlib import import_module
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.r1 import build_modules as registration
from oracles.calendar_terms import CalendarTermsOracleError, calendar_terms, validate_calendar
from spl_compiler.codecs import exact, read_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import run_module_package
from Tests.test_calendar_terms_oracle import fixture

calendar = import_module("cases.calendar-terms.build_modules")


class CalendarTermsModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = ROOT / ".lake" / "calendar-terms-tests"
        work.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=work)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/calendar-terms"
        cls.folder.mkdir(parents=True)
        for name in ["calendar-terms.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/calendar-terms" / name, cls.folder / name)
        for owner, name, value in [(calendar, "ROOT", cls.root), (calendar, "FOLDER", cls.folder),
                                   (registration, "ROOT", cls.root)]:
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = calendar.register_calendar_terms()

    def package(self, data):
        return calendar.calendar_package(data, reference=self.reference)

    def run_fixture(self, data, backend="reference", output=None):
        return run_module_package(self.package(data), self.root, backend=backend, artifact_dir=output)

    def same(self, actual, expected):
        if type(expected) in {int, Fraction}:
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
        expected = calendar_terms(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        comparison = result["results"]["comparison"]
        self.same(comparison, {key: expected[key] for key in comparison})
        actual_days = [{("date" if key == "calendar_date" else key): value for key, value in row.items()}
                       for row in result["results"]["day_lines"]]
        self.same(actual_days, expected["day_lines"])
        self.same(result["results"]["term_lines"], expected["term_lines"])
        self.assertTrue(result["results"]["reconciliation"])
        self.assertEqual(result["closing_state"], [])
        self.assertEqual(result["issuance_status"], "unissued")
        observed = result["results"]["observations"]
        self.assertEqual(observed["calendar"]["id"], data["calendar"]["id"])
        self.assertEqual(observed["calendar"]["version"], data["calendar"]["version"])
        self.assertEqual(observed["fact_scope"], data["scope"])
        self.assertEqual([row["source_ref"] for row in observed["terms"]], [row["source_ref"] for row in data["terms"]])
        self.assertEqual([row["source_kind"] for row in observed["evidence"]], [row["kind"] for row in data["evidence"]])
        return expected

    def blocked(self, data, code=None, backend="reference"):
        with self.assertRaises(CalendarTermsOracleError):
            calendar_terms(data)
        result = self.run_fixture(data, backend)
        self.assertEqual(result["status"], "blocked", result.get("diagnostics"))
        self.assertTrue(result["diagnostics"])
        if code:
            self.assertEqual(result["diagnostics"][0]["code"], code)
        for field in ["results", "detail", "statements", "closing_state"]:
            self.assertFalse(result[field])
        return result

    def test_native_baseline_30_10_100_and_actual_original_rows(self):
        data = fixture()
        with tempfile.TemporaryDirectory(dir=self.root) as output:
            result = self.run_fixture(data, "compare", output)
            self.controls(data, result)
            self.assertTrue(result["verification"]["reference_agrees"])
            self.assertEqual(result["trace_origin"], "native_ir_interpreter")
            self.assertTrue((Path(output) / "Settlement.lean").is_file())
            self.assertTrue((Path(output) / "typed-ir.json").is_file())
            bindings = read_json(Path(output) / "bindings.json")
            self.assertEqual(len(bindings["inputs"]["days"]), 40)
            self.assertFalse({"denominator", "numerator", "amount", "rolled_deadline"} & bindings["inputs"].keys())
            self.assertFalse(any("amount" in row for row in bindings["inputs"]["days"]))

    def test_native_before_recording_and_preceding_roll(self):
        data = fixture()
        data["as_of"] = "2026-04-19"
        data["deadline"]["roll"] = "preceding"
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual((result["results"]["comparison"]["amount"], result["results"]["comparison"]["rolled_deadline"]), ("80", "2026-04-30"))

    def test_native_partial_amendment_is_150_with_per_term_lines(self):
        data = fixture()
        amendment = deepcopy(data["terms"][1])
        amendment.update(id="term-v3", revision=3, predecessor_id="term-v2", monthly_amount="600",
                         effective={"start": "2026-05-01", "end": "2026-05-06"}, source_ref="synthetic-amendment-3")
        data["terms"].append(amendment)
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        self.assertEqual(result["results"]["comparison"]["amount"], "150")
        self.assertEqual([(row["term_id"], row["amount"]) for row in result["results"]["term_lines"]], [("term-v2", "50"), ("term-v3", "100")])

    def test_native_exact_fraction_and_changed_eligible_population(self):
        variants = []
        data = fixture()
        data["terms"][1]["monthly_amount"] = "1/7"
        variants.append((data, Fraction(1, 21)))
        for changed_day, amount in [("2026-04-06", Fraction(3000, 29)), ("2026-04-26", Fraction(2700, 29))]:
            data = fixture()
            next(row for row in data["days"] if row["date"] == changed_day)["proration_eligible"] = False
            variants.append((data, amount))
        for data, amount in variants:
            with self.subTest(amount=amount):
                result = self.run_fixture(data, "compare")
                self.controls(data, result)
                self.assertEqual(exact(result["results"]["comparison"]["amount"]), amount)

    def test_native_inactive_zero_is_distinct_from_selected_zero(self):
        for active in [False, True]:
            data = fixture()
            if active:
                data["terms"][1]["monthly_amount"] = "0"
            else:
                data["terms"] = []
            result = self.run_fixture(data, "compare")
            self.controls(data, result)
            self.assertEqual(result["results"]["comparison"]["amount"], "0")
            self.assertEqual(result["results"]["comparison"]["active_eligible_day_count"], "10" if active else "0")

    def test_native_ambiguous_amendment_and_zero_denominator_are_atomic(self):
        data = fixture()
        data["terms"].append({**deepcopy(data["terms"][1]), "id": "competing-v2"})
        result = self.blocked(data, "CALENDAR_AMBIGUOUS_AMENDMENT", "compare")
        self.assertEqual(result["trace_origin"], "native_ir_interpreter")
        data = fixture()
        for row in data["days"]:
            row["proration_eligible"] = False
        result = self.blocked(data, "CALENDAR_ZERO_ELIGIBLE_DAYS", "compare")
        self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_mechanical_missing_duplicate_ordinal_flags_and_partition_errors(self):
        changes = [
            ("CALENDAR_INCOMPLETE_POPULATION", lambda d: d["days"].pop()),
            ("CALENDAR_DUPLICATE_ID", lambda d: d["days"].append(deepcopy(d["days"][0]))),
            ("CALENDAR_ORDINAL", lambda d: d["days"][0].update(ordinal=1)),
            ("CALENDAR_WEEKDAY", lambda d: d["days"][0].update(weekday=7)),
            ("CALENDAR_CLOSED_FLAGS", lambda d: d["days"][0].update(closed=True)),
            ("CALENDAR_BOOLEAN_FLAGS", lambda d: d["days"][0].update(holiday_closed=0)),
            ("CALENDAR_FISCAL_OVERLAP", lambda d: d["fiscal_periods"][1]["period"].update(start="2026-04-05")),
            ("CALENDAR_FISCAL_GAP", lambda d: d["fiscal_periods"].pop(0)),
            ("CALENDAR_COVERAGE_LIMIT", lambda d: d["calendar"]["coverage"].update(end="2028-05-11")),
            ("CALENDAR_ID_VERSION", lambda d: d["days"][0].update(calendar_version="2")),
            ("CALENDAR_FACT_SCOPE", lambda d: d["days"][0]["scope"].update(asset_id="other")),
            ("CALENDAR_EVIDENCE_REQUIRED", lambda d: d["fiscal_periods"][0].update(evidence_ref="missing")),
        ]
        for code, change in changes:
            data = fixture()
            change(data)
            with self.subTest(code=code):
                with self.assertRaises(CalendarTermsOracleError):
                    validate_calendar(data)
                with self.assertRaisesRegex(ValueError, code):
                    self.package(data)

    def test_reference_predecessor_policy_scope_cutoff_and_negative_money(self):
        changes = [
            lambda d: d["terms"][1].update(predecessor_id="missing"),
            lambda d: d["terms"][0].update(predecessor_id="term-v2"),
            lambda d: d["terms"][1].update(predecessor_id=""),
            lambda d: d["terms"][1].update(signed_date="2026-04-21"),
            lambda d: d["terms"][1].update(monthly_amount="-1"),
            lambda d: d["terms"][0]["scope"].update(pool_id="other"),
            lambda d: d["terms"][1].update(observed_at=d["cutoff"]),
            lambda d: d["policy"].update(no_term="guess_a_default"),
        ]
        for i, change in enumerate(changes):
            data = fixture()
            change(data)
            with self.subTest(variant=i):
                self.blocked(data)

    def test_reference_business_margin_and_no_invented_outside_date(self):
        for due, code in [("2026-05-09", "CALENDAR_BUSINESS_RELATION_UNAVAILABLE"),
                          ("2026-05-11", "CALENDAR_DEADLINE_OUTSIDE_COVERAGE")]:
            data = fixture()
            data["deadline"]["date"] = due
            self.blocked(data, code)
        data = fixture()
        data["deadline"]["roll"] = "modified_following"
        self.blocked(data, "CALENDAR_ROLL_POLICY")
        for roll in ["following", "preceding"]:
            data = fixture()
            data["deadline"].update(date="2026-04-30", roll=roll)
            result = self.run_fixture(data)
            self.controls(data, result)
            self.assertEqual(result["results"]["comparison"]["rolled_deadline"], "2026-04-30")

    def test_reference_asof_equality_is_not_observed_knowledge_reconstruction(self):
        for as_of, amount in [("2026-04-09", "0"), ("2026-04-10", "80"), ("2026-04-19", "80"), ("2026-04-20", "100")]:
            data = fixture()
            data["as_of"] = as_of
            result = self.run_fixture(data)
            self.controls(data, result)
            self.assertEqual(result["results"]["comparison"]["amount"], amount)
        data = fixture()
        data["terms"][1]["observed_at"] = "2026-05-11T00:00:00Z"
        self.controls(data, self.run_fixture(data))

    def test_transport_preserves_original_rows_and_imports_no_oracle(self):
        data = fixture()
        package = self.package(data)
        self.assertEqual(len(package["inputs"]["days"]), len(data["days"]))
        self.assertEqual([row["calendar_date"] for row in package["inputs"]["days"]], [row["date"] for row in data["days"]])
        self.assertEqual(package["inputs"]["selected_period_id"], data["selected_period_id"])
        self.assertNotIn("eligible_day_count", package["inputs"])
        self.assertNotIn("rolled_deadline", package["inputs"]["deadline"])
        tree = ast.parse((ROOT / "cases/calendar-terms/build_modules.py").read_text(encoding="utf-8"))
        imported = [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        self.assertFalse(any(name and name.startswith("oracles") for name in imported))
        invalid = fixture()
        invalid["terms"][1]["monthly_amount"] = "-1"
        self.assertIsNone(calendar.validate_calendar_inputs(invalid))
        self.assertEqual(self.package(invalid)["inputs"]["terms"][1]["monthly_amount"]["value"], "-1")


if __name__ == "__main__":
    unittest.main()
