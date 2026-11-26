"""Native Date selection from original finite named-zone interval relations."""
import ast
from copy import deepcopy
from datetime import datetime, timedelta
from importlib import import_module
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.r1 import build_modules as registration
from oracles.civil_dates import CivilDateOracleError, civil_dates
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import read_json
from spl_compiler.emitter import run_generated
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import resolve_module, run_module_package, validate_module_package
from spl_compiler.run import normalize_target
from Tests.test_civil_date_oracle import fixture, event, cell

civil = import_module("cases.civil-dates.build_modules")


def second_version(data):
    old = next(row for row in data["zones"] if row["id"] == "Synthetic/East-Fixed")
    data["zones"].append({**deepcopy(old), "version": "synthetic-v2", "source_ref": "synthetic-east-v2"})
    cells = []
    for old_cell in data["days"]:
        if old_cell["zone_id"] != "Synthetic/East-Fixed":
            continue
        changed = deepcopy(old_cell)
        changed.update(id=old_cell["id"] + "/v2", zone_version="synthetic-v2", start_offset_minutes=180, end_offset_minutes=180,
                       source_ref="synthetic-east-v2/" + old_cell["local_date"])
        for field in ["utc_start", "utc_end"]:
            value = datetime.fromisoformat(changed[field].replace("Z", "+00:00")) - timedelta(hours=1)
            changed[field] = value.isoformat().replace("+00:00", "Z")
        cells.append(changed)
    data["days"].extend(cells)
    original = deepcopy(event(data, "same-instant-east"))
    original.update(id="version-old", occurred_at="2026-03-06T21:30:00Z")
    data["events"] = [original, {**deepcopy(original), "id": "version-new", "zone_version": "synthetic-v2"}]


class CivilDateModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / ".lake/cd-tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(dir=parent)
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.folder = cls.root / "cases/civil-dates"
        cls.folder.mkdir(parents=True)
        for name in ["civil-dates.spl", "policy.md", "neutral.json"]:
            shutil.copyfile(ROOT / "cases/civil-dates" / name, cls.folder / name)
        for owner, name, value in [(civil, "ROOT", cls.root), (civil, "FOLDER", cls.folder), (registration, "ROOT", cls.root)]:
            control = patch.object(owner, name, value)
            control.start()
            cls.addClassCleanup(control.stop)
        cls.reference = civil.register_civil_dates()

    def package(self, data):
        return civil.civil_date_package(data, reference=self.reference)

    def run_package(self, package, backend="reference", output=None):
        result = run_module_package(package, self.root, backend=backend, artifact_dir=output)
        if backend == "compare" and result.get("trace_origin") == "native_ir_interpreter":
            checked, inputs, openings = validate_module_package(package, resolve_module(self.reference, self.root))
            reference = normalize_target(evaluate(checked, inputs, openings).to_dict())
            generated = normalize_target(run_generated(checked,
                {key: decode_value(value, checked.types[key]) for key, value in inputs.items()}, {}))
            for field in ["status", "emissions", "closing"]:
                self.assertEqual(generated[field], reference[field], field)
            self.assertEqual([row["code"] for row in generated["diagnostics"]], [row["code"] for row in reference["diagnostics"]])
        return result

    def run_fixture(self, data, backend="reference", output=None):
        return self.run_package(self.package(data), backend, output)

    def controls(self, data, result):
        expected = civil_dates(data)
        self.assertEqual(result["status"], "calculated", result["diagnostics"])
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(civil.neutral_value(result["results"]["event_results"]), expected["events"])
        self.assertEqual(result["results"]["coverage"], expected["coverage"])
        self.assertEqual(result["results"]["comparison"], {"status_meaning": expected["status_meaning"]})
        self.assertTrue(result["results"]["reconciliation"])
        self.assertEqual(result["closing_state"], [])
        self.assertEqual(result["reconciliation"]["state"], [])
        self.assertFalse({"amount", "currency", "payable", "actual_paid", "payment_status"} & result["results"].keys())

    def blocked(self, data, code, backend="reference"):
        with self.assertRaises(CivilDateOracleError):
            civil_dates(data)
        result = self.run_fixture(data, backend)
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        self.assertEqual(result["diagnostics"][0]["code"], code)
        self.assertFalse(result["results"])
        self.assertFalse(result["closing_state"])
        return result

    def test_native_original_midnight_short_long_and_two_zone_dates(self):
        data = fixture()
        with tempfile.TemporaryDirectory(dir=self.root) as output:
            result = self.run_fixture(data, "compare", output)
            self.controls(data, result)
            expected = {"before-midnight": "2026-03-06", "at-midnight": "2026-03-07", "before-short-end": "2026-03-07",
                "at-short-end": "2026-03-08", "before-long-end": "2026-03-09", "at-long-end": "2026-03-10",
                "same-instant-west": "2026-03-07", "same-instant-east": "2026-03-08"}
            by_id = {row["event_id"]: row for row in result["results"]["event_results"]}
            self.assertEqual({identity: by_id[identity]["local_date"] for identity in expected}, expected)
            self.assertEqual(read_json(Path(output) / "result.json"), result)
            self.assertEqual(load_completed_result(output), result)
            self.assertTrue((Path(output) / "typed-ir.json").is_file())
            self.assertTrue((Path(output) / "Settlement.lean").is_file())

    def test_native_submicrosecond_and_original_offset_spelling(self):
        data = fixture()
        event(data)["occurred_at"] = "2026-03-07T00:00:00-08:00"
        event(data, "before-midnight")["occurred_at"] = "2026-03-07T08:59:59.9999999999999999999+01:00"
        data["cutoff"] = "2026-03-13T00:00:00.0000002Z"
        event(data)["observed_at"] = "2026-03-13T01:00:00.0000001+01:00"
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        by_id = {row["event_id"]: row for row in result["results"]["event_results"]}
        self.assertEqual(by_id["at-midnight"]["occurred_at"], "2026-03-07T00:00:00-08:00")
        self.assertEqual(by_id["before-midnight"]["local_date"], "2026-03-06")

    def test_native_explicit_zone_version_changes_selected_day(self):
        data = fixture()
        second_version(data)
        result = self.run_fixture(data, "compare")
        self.controls(data, result)
        by_id = {row["event_id"]: row for row in result["results"]["event_results"]}
        self.assertEqual((by_id["version-old"]["local_date"], by_id["version-new"]["local_date"]), ("2026-03-06", "2026-03-07"))

    def test_native_exact_utc_coverage_end_is_exclusive(self):
        data = fixture()
        only = deepcopy(event(data))
        data["events"] = [only]
        only["occurred_at"] = "2026-03-11T07:59:59.9999999Z"
        self.controls(data, self.run_fixture(data, "compare"))
        only["occurred_at"] = "2026-03-11T08:00:00Z"
        result = self.blocked(data, "CIVIL_EVENT_OUTSIDE_COVERAGE", "compare")
        self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_native_observation_cutoff_unknown_version_and_missing_event_evidence(self):
        for code, change in [("CIVIL_EVENT_CUTOFF", lambda d: event(d).update(observed_at=d["cutoff"])),
                ("CIVIL_ZONE_VERSION", lambda d: event(d).update(zone_version="unknown-version")),
                ("CIVIL_EVIDENCE_REQUIRED", lambda d: event(d).update(evidence_ref="missing"))]:
            data = fixture()
            change(data)
            result = self.blocked(data, code, "compare")
            self.assertEqual(result["trace_origin"], "native_ir_interpreter")

    def test_native_physical_guard_rejects_ambiguous_or_missing_cell(self):
        # Deliberately bypass the neutral mechanical table validator after
        # binding, solely to exercise source uniqueness guards on physical input.
        for end, code in [("2026-03-07T09:00:00Z", "CIVIL_AMBIGUOUS_DAY"), ("2026-03-07T07:00:00Z", "CIVIL_EVENT_OUTSIDE_COVERAGE")]:
            data = fixture()
            data["events"] = [deepcopy(event(data))]
            if code == "CIVIL_EVENT_OUTSIDE_COVERAGE":
                data["events"][0]["occurred_at"] = "2026-03-07T07:59:59Z"
            package = self.package(data)
            previous = next(row for row in package["inputs"]["days"] if row["zone_id"] == "Synthetic/West-Shift" and row["local_date"] == "2026-03-06")
            previous.update(utc_end=end, source_utc_end=end)
            result = self.run_package(package, "compare")
            self.assertEqual(result["status"], "blocked", result["diagnostics"])
            self.assertEqual(result["diagnostics"][0]["code"], code)
            self.assertEqual(result["trace_origin"], "native_ir_interpreter")
            self.assertFalse(result["results"])
            self.assertFalse(result["closing_state"])

    def test_reference_metadata_envelope_has_no_financial_domain_scope(self):
        data = fixture()
        package = self.package(data)
        self.assertEqual(package["inputs"]["fact_scope"], data["scope"])
        self.assertEqual(package["scope"]["purpose"], "civil_date_evidence_envelope_only")
        self.assertEqual(package["manifest"]["period"], {"start": "2026-03-06", "end": "2026-03-11"})
        self.assertEqual(package["state_cells"], [])
        self.assertFalse({"currency", "participant_id", "pool_id"} & package["inputs"]["fact_scope"].keys())
        self.controls(data, self.run_fixture(data))
        distinct = fixture()
        second_version(distinct)
        next(row for row in distinct["zones"] if row["version"] == "synthetic-v2")["local_coverage"]["start"] = "2026-03-07"
        distinct["days"] = [row for row in distinct["days"] if not (row["zone_version"] == "synthetic-v2" and row["local_date"] == "2026-03-06")]
        differentiated = self.package(distinct)
        self.assertEqual(differentiated["manifest"]["period"], {"start": "2026-03-06", "end": "2026-03-11"})
        self.assertEqual(next(row for row in differentiated["inputs"]["zones"] if row["version"] == "synthetic-v2")["local_coverage"]["start"], "2026-03-07")
        self.controls(distinct, self.run_package(differentiated))
        for key, value in [("contract", "wrong-contract"), ("project", "wrong-asset")]:
            package = self.package(data)
            package["inputs"][key] = value
            result = self.run_package(package)
            self.assertEqual(result["status"], "blocked")
            self.assertNotIn("trace_origin", result)  # Generic scope boundary, before source evaluation.

    def test_mechanical_population_offset_gregorian_and_continuity_errors(self):
        for code, change in [("CIVIL_INCOMPLETE_LOCAL_POPULATION", lambda d: d["days"].pop()),
                ("CIVIL_DUPLICATE_LOCAL_DATE", lambda d: d["days"].append({**deepcopy(d["days"][0]), "id": "new-id"})),
                ("CIVIL_DUPLICATE_ZONE_VERSION", lambda d: d["zones"].append(deepcopy(d["zones"][0]))),
                ("CIVIL_MIDNIGHT_OFFSET_RELATION", lambda d: cell(d).update(utc_end="2026-03-08T07:00:01Z")),
                ("CIVIL_OFFSET_MINUTES", lambda d: cell(d).update(start_offset_minutes=True)),
                ("CIVIL_DATE", lambda d: cell(d).update(local_date="2026-02-29")),
                ("CIVIL_OFFSET_CONTINUITY", lambda d: cell(d).update(end_offset_minutes=-480, utc_end="2026-03-08T08:00:00Z"))]:
            data = fixture()
            change(data)
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, code):
                self.package(data)

    def test_reference_empty_events_and_row_permutation(self):
        data = fixture()
        expected = self.run_fixture(data)
        self.controls(data, expected)
        for field in ["zones", "days", "events", "evidence"]:
            data[field].reverse()
        actual = self.run_fixture(data)
        self.controls(data, actual)
        self.assertEqual(expected["results"], actual["results"])
        data["events"] = []
        result = self.run_fixture(data)
        self.controls(data, result)
        self.assertEqual(result["results"]["event_results"], [])

    def test_reference_original_zone_and_event_evidence_scope(self):
        for change in [lambda d: event(d)["scope"].update(contract_id="outside"),
                       lambda d: event(d).update(observed_at="2026-03-07T07:59:59Z")]:
            data = fixture()
            change(data)
            with self.assertRaises(CivilDateOracleError):
                civil_dates(data)
            result = self.run_fixture(data)
            self.assertEqual(result["status"], "blocked")
            self.assertFalse(result["results"])
        data = fixture()
        data["evidence"][0]["scope"]["asset_id"] = "outside"
        with self.assertRaisesRegex(ValueError, "CIVIL_EVIDENCE_SCOPE"):
            self.package(data)

    def test_adapter_validates_original_tables_without_classifying_events(self):
        data = fixture()
        event(data)["occurred_at"] = "not-an-instant"
        relation = civil.validate_original_relation(data)
        self.assertEqual(set(relation), {"zones", "days", "evidence"})
        self.assertNotIn("events", relation)
        tree = ast.parse((ROOT / "cases/civil-dates/build_modules.py").read_text(encoding="utf-8"))
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        imports.extend(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertFalse(any(name.startswith("oracles") or name in {"zoneinfo", "time"} for name in imports))
        data = fixture()
        package = self.package(data)
        self.assertTrue(all("local_date" not in row and "cell_id" not in row for row in package["inputs"]["events"]))
        event(data)["local_date"] = "2026-03-07"
        with self.assertRaisesRegex(ValueError, "CIVIL_RECORD_FIELDS"):
            self.package(data)


if __name__ == "__main__":
    unittest.main()
