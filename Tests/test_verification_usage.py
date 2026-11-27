"""Compare a certified dimensional settlement with independent exact amounts."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from spl_compiler.codecs import exact, write_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.verification import certify, run


SOURCE = ROOT / "cases/verification-usage/metered-period.spl"


class VerificationUsageTests(unittest.TestCase):
    def test_series_filters_converts_rounds_and_carries_through_typed_zero(self):
        price = {"currency": "USD", "per_unit": "UsageHour", "value": "1.0025"}
        first = {
            "activity": [
                {"usage_day": date, "duration": {"unit": "UsageMinute", "value": minutes}}
                for date, minutes in [("2026-01-01", "30"), ("2026-03-31", "90"), ("2026-04-01", "45")]
            ],
            "period": {"start": "2026-01-01", "end": "2026-04-01"},
            "price": price,
        }
        second = {"activity": [], "period": {"start": "2026-04-01", "end": "2026-07-01"}, "price": price}
        opening = {"meter": {"unit": "UsageHour", "value": {"numerator": "1", "denominator": "3"}}}
        with tempfile.TemporaryDirectory(prefix="spl-verify-usage-") as directory:
            work = Path(directory)
            bundle = work / "certificate"
            certify(SOURCE, bundle, mode="series")
            bindings = work / "periods.json"
            write_json(bindings, {"periods": [first, second], "openings": opening})
            outcome = run(bundle, bindings)
            self.assertEqual(outcome["status"], "calculated", outcome)
            self.assertEqual(len(outcome["periods"]), 2)
            for result, hours, dollars in zip(outcome["periods"], [2, 0], [2, 0], strict=True):
                self.assertEqual(result["emissions"]["hours"]["unit"], "UsageHour")
                self.assertEqual(exact(result["emissions"]["hours"]["value"]), hours)
                self.assertEqual(exact(result["emissions"]["payable"]), dollars)
                self.assertEqual(result["closing"]["meter"]["unit"], "UsageHour")
                self.assertEqual(exact(result["closing"]["meter"]["value"]), Fraction(7, 3))
            self.assertEqual(outcome["closing"], outcome["periods"][-1]["closing"])

            wrong_rate = deepcopy(second)
            wrong_rate["price"]["per_unit"] = "UsageMinute"
            write_json(bindings, {"periods": [first, wrong_rate], "openings": opening})
            blocked = run(bundle, bindings)
            self.assertEqual(blocked["status"], "blocked")
            self.assertEqual((blocked["periods"], blocked["closing"]), ([], {}))
            self.assertEqual(blocked["diagnostics"], [{"code": "UNIT_MISMATCH", "period_index": 1}])
