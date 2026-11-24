"""Independent finite named-zone date controls; no timezone database is used."""
import ast
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import unittest

from oracles.civil_dates import CivilDateOracleError, civil_dates, validate_zone_relation


ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return json.loads((ROOT / "cases/civil-dates/neutral.json").read_text(encoding="utf-8"))


def event(data, identity="at-midnight"):
    return next(row for row in data["events"] if row["id"] == identity)


def cell(data, local="2026-03-07", zone="Synthetic/West-Shift"):
    return next(row for row in data["days"] if row["zone_id"] == zone and row["local_date"] == local)


class CivilDateOracleTests(unittest.TestCase):
    def reject(self, data, code, mechanical=False):
        with self.assertRaises(CivilDateOracleError) as raised:
            (validate_zone_relation if mechanical else civil_dates)(data)
        self.assertEqual(str(raised.exception), code)

    def test_hand_boundary_dates_keep_original_occurrence_and_observation(self):
        data = fixture()
        result = {row["event_id"]: row for row in civil_dates(data)["events"]}
        expected = {"before-midnight": "2026-03-06", "at-midnight": "2026-03-07", "after-midnight": "2026-03-07",
                    "before-short-end": "2026-03-07", "at-short-end": "2026-03-08", "before-long-end": "2026-03-09",
                    "at-long-end": "2026-03-10", "same-instant-west": "2026-03-07", "same-instant-east": "2026-03-08"}
        self.assertEqual({key: row["local_date"] for key, row in result.items()}, expected)
        for original in data["events"]:
            classified = result[original["id"]]
            self.assertEqual((classified["occurred_at"], classified["observed_at"], classified["zone_id"], classified["zone_version"]),
                             (original["occurred_at"], original["observed_at"], original["zone_id"], original["zone_version"]))
            self.assertIn(classified["cell_id"], {row["id"] for row in data["days"]})

    def test_supplied_24_23_24_25_24_hour_cells(self):
        data = fixture()
        west = sorted((row for row in data["days"] if row["zone_id"] == "Synthetic/West-Shift"), key=lambda row: row["local_date"])
        lengths = [(datetime.fromisoformat(row["utc_end"].replace("Z", "+00:00")) -
                    datetime.fromisoformat(row["utc_start"].replace("Z", "+00:00"))) // timedelta(hours=1) for row in west]
        self.assertEqual(lengths, [24, 23, 24, 25, 24])
        validate_zone_relation(data)
        self.assertTrue(all("local_date" not in row and "cell_id" not in row for row in data["events"]))

    def test_utc_coverage_has_exact_start_and_end_boundaries(self):
        data = fixture(); only = deepcopy(event(data)); data["events"] = [only]
        for instant, expected in (("2026-03-06T08:00:00Z", "2026-03-06"),
                                  ("2026-03-11T07:59:59.9999999Z", "2026-03-10")):
            only["occurred_at"] = instant
            self.assertEqual(civil_dates(data)["events"][0]["local_date"], expected)
        for instant in ("2026-03-06T07:59:59.9999999Z", "2026-03-11T08:00:00Z"):
            only["occurred_at"] = instant
            self.reject(data, "CIVIL_EVENT_OUTSIDE_COVERAGE")

    def test_arbitrarily_precise_offset_equivalent_instants(self):
        data = fixture()
        event(data)["occurred_at"] = "2026-03-07T00:00:00-08:00"
        event(data, "before-midnight")["occurred_at"] = "2026-03-07T08:59:59.9999999999999999999+01:00"
        result = {row["event_id"]: row for row in civil_dates(data)["events"]}
        self.assertEqual(result["at-midnight"]["local_date"], "2026-03-07")
        self.assertEqual(result["before-midnight"]["local_date"], "2026-03-06")
        self.assertEqual(result["at-midnight"]["occurred_at"], "2026-03-07T00:00:00-08:00")

    def test_multiple_versions_require_explicit_original_version(self):
        data = fixture()
        old = next(row for row in data["zones"] if row["id"] == "Synthetic/East-Fixed")
        data["zones"].append({**deepcopy(old), "version": "synthetic-v2", "source_ref": "synthetic-east-v2"})
        new_cells = []
        for old_cell in data["days"]:
            if old_cell["zone_id"] != "Synthetic/East-Fixed":
                continue
            changed = deepcopy(old_cell)
            changed.update(id=old_cell["id"] + "/v2", zone_version="synthetic-v2", start_offset_minutes=180, end_offset_minutes=180,
                           source_ref="synthetic-east-v2/" + old_cell["local_date"])
            for field in ("utc_start", "utc_end"):
                instant = datetime.fromisoformat(changed[field].replace("Z", "+00:00")) - timedelta(hours=1)
                changed[field] = instant.isoformat().replace("+00:00", "Z")
            new_cells.append(changed)
        data["days"].extend(new_cells)
        original = deepcopy(event(data, "same-instant-east"))
        original.update(id="version-old", occurred_at="2026-03-06T21:30:00Z")
        data["events"] = [original, {**deepcopy(original), "id": "version-new", "zone_version": "synthetic-v2"}]
        results = {row["event_id"]: row for row in civil_dates(data)["events"]}
        self.assertEqual((results["version-old"]["local_date"], results["version-new"]["local_date"]), ("2026-03-06", "2026-03-07"))
        self.assertEqual(results["version-old"]["zone_version"], "synthetic-v1")

    def test_mechanical_validator_returns_original_tables_not_event_answers(self):
        data = fixture(); event(data)["occurred_at"] = "not-an-instant"
        checked = validate_zone_relation(data)
        self.assertEqual(set(checked), {"zones", "days", "evidence"})
        self.assertNotIn("events", checked)
        self.assertNotIn("local_dates", checked)
        self.reject(data, "CIVIL_INSTANT")
        data = fixture(); event(data)["local_date"] = "2026-03-07"
        self.reject(data, "CIVIL_RECORD_FIELDS")

    def test_missing_local_population_extra_dates_and_duplicates_fail(self):
        data = fixture(); data["days"].pop()
        self.reject(data, "CIVIL_INCOMPLETE_LOCAL_POPULATION", mechanical=True)
        data = fixture(); data["days"].append(deepcopy(data["days"][0]))
        self.reject(data, "CIVIL_DUPLICATE_ID", mechanical=True)
        data = fixture(); alias = deepcopy(data["days"][0]); alias["id"] = "different-cell-id"; data["days"].append(alias)
        self.reject(data, "CIVIL_DUPLICATE_LOCAL_DATE", mechanical=True)
        data = fixture(); data["zones"][0]["local_coverage"]["end"] = "2026-03-12"
        self.reject(data, "CIVIL_INCOMPLETE_LOCAL_POPULATION", mechanical=True)
        data = fixture(); data["zones"].append(deepcopy(data["zones"][0]))
        self.reject(data, "CIVIL_DUPLICATE_ZONE_VERSION", mechanical=True)

    def test_overlap_and_gap_within_version_fail_not_across_zones(self):
        validate_zone_relation(fixture())
        data = fixture(); short = cell(data)
        short.update(end_offset_minutes=-480, utc_end="2026-03-08T08:00:00Z")
        self.reject(data, "CIVIL_OFFSET_CONTINUITY", mechanical=True)
        data = fixture(); short = cell(data)
        short.update(end_offset_minutes=-360, utc_end="2026-03-08T06:00:00Z")
        self.reject(data, "CIVIL_OFFSET_CONTINUITY", mechanical=True)

    def test_original_midnight_offset_consistency_and_positive_interval(self):
        for field, value, code in (("utc_start", "2026-03-07T08:00:00.0000001Z", "CIVIL_MIDNIGHT_OFFSET_RELATION"),
                                    ("utc_end", "2026-03-08T07:00:01Z", "CIVIL_MIDNIGHT_OFFSET_RELATION"),
                                    ("end_offset_minutes", -421, "CIVIL_MIDNIGHT_OFFSET_RELATION"),
                                    ("start_offset_minutes", True, "CIVIL_OFFSET_MINUTES"),
                                    ("start_offset_minutes", -1440, "CIVIL_OFFSET_MINUTES"),
                                    ("local_date", "2026-02-29", "CIVIL_DATE")):
            data = fixture(); cell(data)[field] = value
            self.reject(data, code, mechanical=True)
        data = fixture(); cell(data)["utc_end"] = cell(data)["utc_start"]
        self.reject(data, "CIVIL_INTERVAL_POSITIVE", mechanical=True)

    def test_wrong_version_missing_zone_and_no_default_timezone(self):
        data = fixture(); event(data)["zone_version"] = "unknown-version"
        self.reject(data, "CIVIL_ZONE_VERSION")
        data = fixture(); event(data)["zone_id"] = "unknown-zone"
        self.reject(data, "CIVIL_ZONE_VERSION")
        data = fixture(); del event(data)["zone_id"]
        self.reject(data, "CIVIL_RECORD_FIELDS")
        data = fixture(); cell(data)["zone_version"] = "unknown-version"
        self.reject(data, "CIVIL_ZONE_VERSION", mechanical=True)
        data = fixture(); data["zones"].pop(0)
        self.reject(data, "CIVIL_ZONE_VERSION", mechanical=True)

    def test_occurrence_observation_order_and_cutoff_equality(self):
        data = fixture(); event(data)["observed_at"] = event(data)["occurred_at"]
        self.assertEqual(next(row for row in civil_dates(data)["events"] if row["event_id"] == "at-midnight")["local_date"], "2026-03-07")
        data = fixture(); event(data)["observed_at"] = "2026-03-07T07:59:59.9999999Z"
        self.reject(data, "CIVIL_OCCURRENCE_AFTER_OBSERVATION")
        data = fixture(); event(data)["observed_at"] = data["cutoff"]
        self.reject(data, "CIVIL_EVENT_CUTOFF")
        data = fixture(); data["cutoff"] = "2026-03-13T00:00:00.0000002Z"
        event(data)["observed_at"] = "2026-03-13T01:00:00.0000001+01:00"
        self.assertEqual(len(civil_dates(data)["events"]), 9)

    def test_scope_original_source_evidence_and_available_calendar(self):
        changes = [("CIVIL_ZONE_SCOPE", lambda d: d["zones"][0]["scope"].update(asset_id="outside")),
                   ("CIVIL_DAY_SCOPE", lambda d: cell(d)["scope"].update(asset_id="outside")),
                   ("CIVIL_EVENT_SCOPE", lambda d: event(d)["scope"].update(asset_id="outside")),
                   ("CIVIL_EVIDENCE_SCOPE", lambda d: d["evidence"][0]["scope"].update(contract_id="outside")),
                   ("CIVIL_EVIDENCE_REQUIRED", lambda d: cell(d).update(evidence_ref="missing")),
                   ("CIVIL_EVIDENCE_REQUIRED", lambda d: event(d).update(evidence_ref="missing")),
                   ("CIVIL_EVIDENCE_CUTOFF", lambda d: d["evidence"][0].update(observed_at=d["cutoff"]))]
        for code, change in changes:
            data = fixture(); change(data); self.reject(data, code)

    def test_no_events_mechanical_empty_relation_policy_and_resource_limits(self):
        data = fixture(); data["events"] = []
        self.assertEqual(civil_dates(data)["events"], [])
        data = fixture(); data["zones"] = []
        self.reject(data, "CIVIL_RESOURCE_BOUND", mechanical=True)
        data = fixture(); data["zones"][0]["local_coverage"]["end"] = "2026-05-01"
        self.reject(data, "CIVIL_RESOURCE_BOUND", mechanical=True)
        data = fixture(); data["policy"]["selection"] = "ambient_timezone"
        self.reject(data, "CIVIL_SELECTED_POLICY")

    def test_invalid_instants_do_not_default_or_truncate(self):
        for instant in ("2026-03-07", "2026-03-07T08:00:00", "2026-03-07T08:00:00-00:00", "2026-03-07T08:00:60Z", 0.1):
            data = fixture(); event(data)["occurred_at"] = instant
            self.reject(data, "CIVIL_INSTANT")

    def test_original_permutation_replay_and_no_monetary_outputs(self):
        data = fixture(); original = deepcopy(data)
        expected = civil_dates(data)
        self.assertEqual(data, original)
        for field in ("zones", "days", "events", "evidence"):
            data[field].reverse()
        self.assertEqual(civil_dates(data), expected)
        self.assertEqual(civil_dates(original), expected)
        self.assertEqual(set(expected), {"events", "coverage", "status_meaning"})
        self.assertTrue(all("offset_at_event" not in row and "local_time" not in row for row in expected["events"]))
        self.assertEqual(json.loads(json.dumps(expected)), expected)

    def test_oracle_has_no_timezone_database_or_compiler_imports(self):
        tree = ast.parse((ROOT / "oracles/civil_dates.py").read_text(encoding="utf-8"))
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports.update(alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names)
        self.assertEqual(imports, {"datetime", "fractions", "re"})


if __name__ == "__main__":
    unittest.main()
