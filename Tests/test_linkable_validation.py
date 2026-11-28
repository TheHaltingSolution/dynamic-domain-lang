"""Check versioned SPL validation appendices through the real linked artifact."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from cases.validation.link_manifest import FOLDER, example_module
from spl_compiler.codecs import DataError, loads, read_json, write_json
from spl_compiler.lean_tools import compile_schedule, lean
from spl_compiler.modules import linking_manifest
from spl_compiler.source_verification import check_source
from spl_compiler.verification import certify, run


class LinkableValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directory = TemporaryDirectory(prefix="spl-validation-")
        cls.addClassCleanup(directory.cleanup)
        cls.work = Path(directory.name)
        cls.module = example_module()
        cls.link = cls.work / "link.json"
        cls.fixture = read_json(FOLDER / "bindings.json")
        write_json(cls.link, linking_manifest(cls.module))
        cls.artifact = compile_schedule(cls.module.source_path, cls.work / "Settlement.lean", link=cls.link)

    def execute(self, envelope):
        bindings = self.work / "bindings.json"
        write_json(bindings, envelope)
        return loads(lean(["--run", self.artifact, bindings]))

    def assertBlocked(self, envelope, code):
        self.assertEqual(self.execute(envelope), {
            "status": "blocked", "emissions": {}, "closing": {}, "diagnostics": [{"code": code}],
        })

    def test_two_module_formats_validate_and_calculate(self):
        self.assertEqual(self.execute(self.fixture), {
            "status": "calculated", "emissions": {"participation": {"numerator": "25", "denominator": "1"}},
            "closing": {}, "diagnostics": [],
        })
        envelope = deepcopy(self.fixture)
        envelope["inputs"].update(receipts=[], costs=[])
        self.assertEqual(self.execute(envelope)["emissions"]["participation"], {
            "numerator": "0", "denominator": "1",
        })

    def test_repeat_identity_across_distinct_dates_fails_in_each_format(self):
        for port, date_field, code in [
            ("receipts", "cash_received_date", "RECEIPT_DUPLICATE_FACT_ID"),
            ("costs", "recognition_date", "POSTING_COST_DUPLICATE_FACT_ID"),
        ]:
            with self.subTest(port=port):
                envelope = deepcopy(self.fixture)
                rows = envelope["inputs"][port]
                rows.append({**rows[0], date_field: "2026-02-01"})
                self.assertBlocked(envelope, code)

    def test_outside_period_fails_using_each_format_date_field(self):
        for port, date_field, code in [
            ("receipts", "cash_received_date", "RECEIPT_OUTSIDE_PERIOD"),
            ("costs", "recognition_date", "POSTING_COST_OUTSIDE_PERIOD"),
        ]:
            for date in ["2025-12-31", "2026-04-01"]:
                with self.subTest(port=port, date=date):
                    envelope = deepcopy(self.fixture)
                    envelope["inputs"][port][0][date_field] = date
                    self.assertBlocked(envelope, code)

    def test_changed_validator_bytes_fail_the_source_pin(self):
        manifest = linking_manifest(self.module)
        manifest["modules"][0]["source"] += "// changed validator\n"
        link = self.work / "changed-link.json"
        write_json(link, manifest)
        with self.assertRaisesRegex(DataError, "Changed linked source"):
            check_source(self.module.source_path, link=link)

    def test_verified_series_reports_later_validation_failure_atomically(self):
        bundle = self.work / "certified-series"
        receipt = certify(self.module.source_path, bundle, link=self.link, mode="series")
        self.assertIn("consumed.link.json", receipt["files"])
        invalid = deepcopy(self.fixture["inputs"])
        invalid["costs"][0]["recognition_date"] = "2026-04-01"
        bindings = self.work / "series.json"
        write_json(bindings, {"periods": [self.fixture["inputs"], invalid], "openings": {}})
        outcome = run(bundle, bindings)
        self.assertEqual(outcome["status"], "blocked")
        self.assertEqual(outcome["diagnostics"], [{"code": "POSTING_COST_OUTSIDE_PERIOD", "period_index": 1}])
        self.assertEqual(outcome["periods"], [])
        self.assertEqual(outcome["closing"], {})


if __name__ == "__main__":
    unittest.main()
