"""Exact canonical/native chronology, including the LD-02 T10 counterexample."""
from copy import deepcopy
from datetime import date
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from spl_compiler.adapter import rq07
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import (DataError, canonical, instant, instant_utc_day,
                                 loads, write_json)
from spl_compiler.evaluator import evaluate
from spl_compiler.fixtures import sv_package
from spl_compiler.instant import parse_instant
from spl_compiler.lean_tools import (ROOT, compile_schedule, interpret_schedule,
                                     lean)
from spl_compiler.model import SPLException
from spl_compiler.parser import parse
from spl_compiler.run import bind_package, project, run_package
from spl_compiler.schema import validate_package


CUTOFF = "2026-07-03T00:00:00.0000002Z"
# Expected membership is authored independently of either timestamp parser.
OBSERVATIONS = [
    ("2026-07-03T00:00:00.0000001Z", True),
    ("2026-07-03T00:00:00.0000002Z", False),
    ("2026-07-03T00:00:00.0000003Z", False),
    ("2026-07-02T23:00:00.00000010000000000000000001-01:00", True),
    ("2026-07-03T01:00:00.00000020000000000000000000+01:00", False),
    ("2026-07-02T23:30:00-01:00", False),
    ("2026-07-03T00:30:00+01:00", True),
]
INVALID = [
    "2026-07-03", "2026-07-03T00:00:00", "2026-07-03T00:00:00-00:00",
    "2026-07-03T00:00:60Z", "2025-02-29T00:00:00Z",
    "2026-07-03T24:00:00Z", "2026-07-03T00:00:00+24:00",
    "2026-07-03T00:00:00+00:60", "2026-07-03T00:00:00+01:99",
    "0001-01-01T00:00:00+00:01", "9999-12-31T23:59:59-00:01",
    "2026-07-03T00:00:00.Z", "2026-07-03 00:00:00Z",
    "2026-07-03T00:00:00Z\n", "0000-01-01T00:00:00Z", None, 42,
]


def package_at(observed):
    package = sv_package()
    package["manifest"]["cutoff"] = CUTOFF
    package["evidence_events"][0]["observed_at"] = observed
    return package


class CanonicalPrecisionTests(unittest.TestCase):
    def test_ledger_counterexample_and_arbitrary_decimal_precision(self):
        before = instant(OBSERVATIONS[0][0])
        cutoff = instant(CUTOFF)
        self.assertLess(before, cutoff)
        self.assertEqual(cutoff.seconds - before.seconds, Fraction(1, 10 ** 7))
        for observed, included in OBSERVATIONS:
            with self.subTest(observed=observed):
                self.assertEqual(instant(observed) < cutoff, included)
                self.assertEqual(instant(observed), parse_instant(observed))
        a = instant("2026-07-03T00:00:00.00000000000000000001Z")
        b = instant("2026-07-03T00:00:00.00000000000000000002Z")
        self.assertEqual(b.seconds - a.seconds, Fraction(1, 10 ** 20))
        self.assertLess(a, b)

    def test_offset_normalization_transport_and_calendar_boundaries(self):
        examples = [
            ("2024-03-01T00:30:00.0000001000+01:00", "2024-02-29T23:30:00.0000001Z"),
            ("2026-12-31T23:30:00.0000001-01:00", "2027-01-01T00:30:00.0000001Z"),
            ("2026-07-03t00:00:00.000z", "2026-07-03T00:00:00Z"),
            ("0001-01-01T00:00:00Z", "0001-01-01T00:00:00Z"),
            ("9999-12-31T23:59:59.99999999999999999999Z", "9999-12-31T23:59:59.99999999999999999999Z"),
        ]
        for raw, expected in examples:
            with self.subTest(raw=raw):
                value = instant(raw)
                self.assertEqual(value.canonical, expected)
                self.assertEqual(instant(expected), value)
                self.assertEqual(loads(canonical({"observed": value})), {"observed": expected})
                self.assertEqual(instant_utc_day(raw), date.fromisoformat(expected[:10]))

    def test_invalid_profile_matches_reference_parser_and_preserves_pointer(self):
        for invalid in INVALID:
            with self.subTest(invalid=invalid):
                with self.assertRaises(SPLException) as reference:
                    parse_instant(invalid)
                with self.assertRaises(DataError) as canonical_error:
                    instant(invalid, "/observed_at")
                self.assertEqual(canonical_error.exception.code, reference.exception.code)
                self.assertEqual(canonical_error.exception.code, "INVALID_INSTANT")
                self.assertEqual(canonical_error.exception.pointer, "/observed_at")

    def test_all_canonical_timestamp_fields_use_the_same_strict_profile(self):
        fields = [("manifest", "cutoff", "/manifest/cutoff"),
                  ("evidence_events", "observed_at", "/evidence_events/0/observed_at"),
                  ("source_batches", "ingested_at", "/source_batches/0/ingested_at")]
        for group, field, pointer in fields:
            for invalid in [x for x in INVALID if isinstance(x, str)]:
                with self.subTest(group=group, invalid=invalid):
                    package = sv_package()
                    target = package[group] if group == "manifest" else package[group][0]
                    target[field] = invalid
                    with self.assertRaises(DataError) as error:
                        validate_package(package)
                    self.assertEqual(error.exception.code, "INVALID_INSTANT")
                    self.assertEqual(error.exception.pointer, pointer)
        package = package_at(OBSERVATIONS[0][0])
        package["source_batches"][0]["ingested_at"] = "2026-11-20T01:00:00.00000000000000000001+01:00"
        validate_package(package)

    def test_canonical_validation_and_atomic_run_use_strict_exact_cutoff(self):
        schedule = ROOT / "cases/sv/sv01.spl"
        for observed, included in OBSERVATIONS:
            with self.subTest(observed=observed):
                package = package_at(observed)
                original = deepcopy(package)
                if included:
                    validate_package(package)
                else:
                    with self.assertRaises(DataError) as error:
                        validate_package(package)
                    self.assertEqual(error.exception.code, "EVIDENCE_AFTER_CUTOFF")
                self.assertEqual(package, original)
                result = run_package(bind_package(package, schedule), schedule, backend="reference")
                if included:
                    self.assertEqual(result["diagnostics"], [])
                    self.assertEqual(result["statements"][0]["payable"], "18000")
                else:
                    self.assertEqual(result["status"], "blocked")
                    self.assertEqual(result["diagnostics"][0]["code"], "EVIDENCE_AFTER_CUTOFF")
                    self.assertEqual(result["statements"], [])
                    self.assertEqual(result["closing_state"], [])

    def test_rq07_retains_explicit_utc_date_precision_policy(self):
        package = rq07(ROOT / "cases/rq07/source", observed_at="2026-04-03T00:00:00.0000001Z",
                       ingested_at="2026-11-20T00:00:00.00000000000000000001Z")
        # July 3 locally is July 2 UTC. Subsecond precision must not make a
        # date-only July 2 posting available under the existing strict day rule.
        package["manifest"]["cutoff"] = "2026-07-03T00:30:00.0000001+01:00"
        receipt = next(f for f in package["financial_facts"] if f["event_kind"] == "cash_receipt")
        receipt["dates"]["posting_date"] = "2026-07-01"
        project(package)
        receipt["dates"]["posting_date"] = "2026-07-02"
        with self.assertRaises(DataError) as error:
            project(package)
        self.assertEqual(error.exception.code, "SOURCE_AFTER_CUTOFF")


class CanonicalNativePrecisionTests(unittest.TestCase):
    def test_canonical_validation_agrees_with_native_and_generated_instant_comparison(self):
        source = ('schedule Timestamp language "spl/0.1-draft" core "spl-core/0.1-draft" '
                  'schema "spl-data/0.1-draft" { input moments: List<Instant>; input cutoff: Instant; '
                  'define rows = for each moment in moments { yield { included: moment < cutoff, observed: moment }; }; '
                  'emit "observations" = rows; }')
        values = {"inputs": {"moments": [x for x, _ in OBSERVATIONS], "cutoff": CUTOFF}, "openings": {}}
        expected = [{"included": included, "observed": parse_instant(observed).canonical}
                    for observed, included in OBSERVATIONS]
        reference = evaluate(check_schedule(parse(source)), **values).to_dict()
        self.assertEqual(reference["emissions"]["observations"], expected)
        with tempfile.TemporaryDirectory() as directory:
            schedule = Path(directory) / "timestamp.spl"
            bindings = Path(directory) / "bindings.json"
            schedule.write_text(source, encoding="utf-8")
            write_json(bindings, values)
            native = interpret_schedule(schedule, bindings)
            generated_path = compile_schedule(schedule, Path(directory) / "Timestamp.lean")
            generated = loads(lean(["--run", generated_path, bindings]))
        for result in [native, generated]:
            self.assertEqual(result["status"], "calculated", result)
            self.assertEqual(result["emissions"]["observations"], expected)
        for observed, included in OBSERVATIONS:
            package = package_at(observed)
            if included:
                validate_package(package)
            else:
                with self.assertRaises(DataError) as error:
                    validate_package(package)
                self.assertEqual(error.exception.code, "EVIDENCE_AFTER_CUTOFF")


if __name__ == "__main__":
    unittest.main()
