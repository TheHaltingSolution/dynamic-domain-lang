"""Actual emitted series, resumed state, certificate identity and trusted AOT."""
from copy import deepcopy
from datetime import date, timedelta
import os
from pathlib import Path
import tempfile
import unittest

from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import DataError, exact, file_digest, read_json, write_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.verification import certify, run, verify


class SeriesVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        scratch = tempfile.TemporaryDirectory(prefix="spl-series-tests-")
        cls.addClassCleanup(scratch.cleanup)
        cls.work = Path(scratch.name)
        cls.bundle = cls.work / "rq07"
        cls.certificate = certify(ROOT / "cases/sv/rq07-readable.spl", cls.bundle, mode="series")
        original = read_json(ROOT / "cases/rq07/readable/bindings.json")
        cls.first = original["inputs"]
        cls.next = deepcopy(cls.first)
        cls.next["policy"]["period"] = {"start": "2026-04-01", "end": "2026-07-01"}
        for collection, field in (("receipts", "cash_received_date"), ("eligible_costs", "recognition_date")):
            for row in cls.next[collection]:
                if field in row:
                    row[field] = (date.fromisoformat(row[field]) + timedelta(days=90)).isoformat()
        cls.opening = {"prepayment": {"currency": "USD", "value": "50000"}}

    def bindings(self, name, periods, *, opening=None):
        path = self.work / (name + ".json")
        write_json(path, {"periods": periods, "openings": self.opening if opening is None else opening})
        return path

    def test_verified_rq07_periods_match_resume_with_real_closing_amount(self):
        self.assertEqual(verify(self.bundle), self.certificate)
        full = run(self.bundle, self.bindings("full", [self.first, self.next]))
        first, second = full["periods"]
        self.assertEqual(exact(first["emissions"]["pool"]["earned"]), 33000)
        self.assertEqual(exact(first["emissions"]["pool"]["payable"]), 0)
        self.assertEqual(exact(first["closing"]["prepayment"]), 17000)
        self.assertEqual(exact(second["emissions"]["pool"]["earned"]), 33000)
        self.assertEqual(exact(second["emissions"]["pool"]["payable"]), 16000)
        self.assertEqual(exact(full["closing"]["prepayment"]), 0)

        publication = self.work / "published"
        prefix = run(self.bundle, self.bindings("prefix", [self.first]), output=publication)
        previous = load_completed_result(publication)
        self.assertEqual(previous, prefix)
        opening = {"prepayment": {"currency": "USD", "value": previous["closing"]["prepayment"]}}
        resumed = run(self.bundle, self.bindings("resume", [self.next], opening=opening))
        self.assertEqual(previous["periods"] + resumed["periods"], full["periods"])
        self.assertEqual(resumed["closing"], full["closing"])

    def test_failed_middle_period_discards_every_result_and_reports_first_failure(self):
        invalid = deepcopy(self.next)
        invalid["pictures"][0]["funding_share"] = "2"
        publication = self.work / "blocked-publication"
        outcome = run(self.bundle, self.bindings("failed", [self.first, invalid, {}]), output=publication)
        self.assertEqual(outcome["status"], "blocked")
        self.assertEqual(outcome["periods"], [])
        self.assertEqual(outcome["closing"], {})
        self.assertEqual(outcome["diagnostics"], [{"code": "INVALID_FUNDING_SHARE", "period_index": 1}])
        self.assertEqual(load_completed_result(publication), outcome)

    def test_changed_artifact_fails_before_execution(self):
        target = self.bundle / "Settlement.lean"
        original = target.read_bytes()
        self.addCleanup(target.write_bytes, original)
        target.write_bytes(original + b"\n-- changed\n")
        with self.assertRaisesRegex(DataError, "Bundle file changed: Settlement.lean"):
            verify(self.bundle)

    def test_series_envelope_requires_at_least_one_period(self):
        result = run(self.bundle, self.bindings("empty", []))
        self.assertEqual(result["diagnostics"], [{"code": "SERIES_EMPTY"}])
        self.assertEqual((result["periods"], result["closing"]), ([], {}))

    @unittest.skipUnless(os.name == "nt", "Pinned audited AOT build is currently Windows-specific")
    def test_ahead_of_time_executable_matches_verified_lean_series(self):
        bindings = self.bindings("aot", [self.first, self.next])
        lean = run(self.bundle, bindings)
        publication = self.work / "aot-publication"
        native = run(self.bundle, bindings, native=True, output=publication)
        self.assertEqual(load_completed_result(publication), native)
        native_evidence = native.pop("verification")
        lean_evidence = lean.pop("verification")
        self.assertEqual(native, lean)
        self.assertEqual(native_evidence["execution"], "pinned-native")
        self.assertEqual(native_evidence["certificate_sha256"], lean_evidence["certificate_sha256"])
        self.assertRegex(native_evidence["executable_sha256"], r"^[0-9a-f]{64}$")
        marker = read_json(publication / "completion.json")
        evidence = publication / ".runs" / marker["invocation_id"]
        self.assertEqual(file_digest(evidence / "native-build.json"), native_evidence["native_build_sha256"])
