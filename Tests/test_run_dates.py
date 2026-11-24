"""Optional presentation dates retain financial recognition and state semantics."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from Tests import test_modules as module_fixtures
from spl_compiler.artifacts import load_completed_result
from spl_compiler.codecs import DataError, digest
from spl_compiler.fixtures import sv_package
from spl_compiler.lean_tools import ROOT
from spl_compiler.run import bind_package, carry_state, project, run_package


OBSERVATIONS = []


class DateFixture:
    def setUp(self):
        self.generic = module_fixtures.ModuleTests()
        self.generic.setUp()
        self.addCleanup(self.generic.doCleanups)
        self.generic.add_state()
        (ROOT / ".lake").mkdir(exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(prefix="dates-", dir=ROOT / ".lake")
        self.addCleanup(self.directory.cleanup)
        self.output_root = Path(self.directory.name)
        self.count = 0

    def package(self, family):
        return deepcopy(self.generic.package) if family == "module" else sv_package()

    def source(self, family):
        return self.generic.root if family == "module" else ROOT / "cases/sv/sv01-readable.spl"

    def run_saved(self, family, package, backend="reference"):
        self.count += 1
        output = self.output_root / str(self.count)
        bound = bind_package(package, self.source(family))
        result = run_package(bound, self.source(family), backend=backend, artifact_dir=output)
        loaded = load_completed_result(output)
        self.assertEqual(loaded, result)
        # Failed input manifests may legitimately retain the rejected null.
        # The completed-artifact reader validates JSON and durable hashes;
        # canonical input read_json intentionally rejects null even in metadata.
        self.assertEqual(json.loads((output / "result.json").read_text(encoding="utf-8")), result)
        OBSERVATIONS.append({"test": self.id(), "family": family, "backend": backend, "bound": deepcopy(bound), "result": deepcopy(result), "output": str(output)})
        return result, output

    def calculated(self, result):
        self.assertEqual(result["diagnostics"], [], result["diagnostics"])
        self.assertIn(result["status"], {"calculated", "calculated_zero", "provisional"})
        self.assertEqual(result["issuance_status"], "unissued")

    def same_economics(self, left, right):
        for result in (left, right): self.calculated(result)
        for field in ("semantic_run_digest", "statements", "detail", "trace", "closing_state", "reconciliation", "policy_review"):
            self.assertEqual(left[field], right[field], field)
        if "results" in left: self.assertEqual(left["results"], right["results"])

    def add_recognition_input(self):
        source = self.generic.source.read_text(encoding="utf-8")
        source = source.replace("define earned = cash * rate;", "input recognition_date: Date; input economic_period: Period; define earned = if in_period(recognition_date, economic_period) then cash * rate else USD 0;")
        self.generic.source.write_text(source, encoding="utf-8", newline="\n")
        self.generic.descriptor["interface"]["ports"].extend([
            module_fixtures.port("recognition_date", "input", module_fixtures.typ("Date")),
            module_fixtures.port("economic_period", "input", module_fixtures.typ("Period"))])
        self.generic.package["inputs"].update(recognition_date="2026-02-01", economic_period={"start": "2026-01-01", "end": "2026-04-01"})
        self.generic.repin()


class RunDateReferenceTests(DateFixture, unittest.TestCase):
    def test_optional_each_or_both_dates_preserve_economics_and_identity_contracts(self):
        for family in ("module", "bounded"):
            package = self.package(family); first, _ = self.run_saved(family, package)
            self.assertNotIn("report_date", first["manifest"]); self.assertNotIn("issue_date", first["manifest"])
            for dates in ({"report_date": "2026-07-01"}, {"issue_date": "2025-01-01"}, {"report_date": "2026-07-01", "issue_date": "2025-01-01"}):
                changed = deepcopy(package); changed["manifest"].update(dates); second, _ = self.run_saved(family, changed)
                self.same_economics(first, second)
                self.assertEqual({key: second["manifest"][key] for key in dates}, dates)
                self.assertEqual(first["manifest"]["compiler_build"], second["manifest"]["compiler_build"])
                self.assertEqual(first["result_digest"] == second["result_digest"], family == "bounded")
                self.assertNotEqual(digest(first), digest(second))
            self.assertNotIn("report_date", package["manifest"])

    def test_dates_are_strict_calendar_dates_not_instants_or_nullable_defaults(self):
        invalid = (None, True, 20260401, {}, [], "", "2026-4-01", "0000-01-01", "10000-01-01", "2026-02-29", "2026-04-31", "2026-04-01T00:00:00Z", " 2026-04-01")
        for family in ("module", "bounded"):
            for field in ("report_date", "issue_date"):
                for value in invalid:
                    with self.subTest(family=family, field=field, value=value):
                        package = self.package(family); package["manifest"][field] = value
                        result, _ = self.run_saved(family, package)
                        self.assertEqual(result["status"], "blocked"); self.assertTrue(result["diagnostics"])
                        self.assertEqual(result["statements"], []); self.assertEqual(result["closing_state"], []); self.assertNotIn("result_digest", result)

    def test_valid_extreme_and_leap_dates_have_no_invented_temporal_order(self):
        for family in ("module", "bounded"):
            package = self.package(family); first, _ = self.run_saved(family, package)
            for report, issue in (("0001-01-01", "9999-12-31"), ("9999-12-31", "0001-01-01"), ("2024-02-29", "2024-02-29")):
                package["manifest"].update(report_date=report, issue_date=issue)
                result, _ = self.run_saved(family, package); self.same_economics(first, result)

    def test_report_and_intended_issue_do_not_override_explicit_economic_date_ports(self):
        self.add_recognition_input(); package = self.package("module")
        first, _ = self.run_saved("module", package); self.assertEqual(first["results"]["result"], "20")
        package["manifest"].update(report_date="2027-01-01", issue_date="2024-01-01")
        metadata, _ = self.run_saved("module", package); self.same_economics(first, metadata)
        package["inputs"]["recognition_date"] = "2026-04-01"
        economic, _ = self.run_saved("module", package); self.calculated(economic)
        self.assertEqual(economic["results"]["result"], "0"); self.assertNotEqual(metadata["semantic_run_digest"], economic["semantic_run_digest"])

    def test_bounded_original_effective_date_still_controls_recognition(self):
        package = self.package("bounded"); first, _ = self.run_saved("bounded", package)
        package["manifest"].update(report_date="2027-01-01", issue_date="2024-01-01")
        metadata, _ = self.run_saved("bounded", package); self.same_economics(first, metadata)
        before = project(bind_package(package, self.source("bounded")))[0]
        package["financial_facts"][2]["temporal_basis"]["date"] = "2026-04-01"
        package["financial_facts"][2]["dates"]["incurred_date"] = "2026-04-01"
        package["source_batches"][0]["sha256"] = digest(package["financial_facts"])
        economic, _ = self.run_saved("bounded", package); self.calculated(economic)
        after = project(bind_package(package, self.source("bounded")))[0]
        self.assertNotEqual(before, after); self.assertNotEqual(metadata["semantic_run_digest"], economic["semantic_run_digest"])
        self.assertNotEqual(metadata["statements"], economic["statements"])

    def test_explicit_economic_port_named_report_date_is_still_semantic(self):
        self.add_recognition_input()
        self.generic.source.write_text(self.generic.source.read_text(encoding="utf-8").replace("recognition_date", "report_date"), encoding="utf-8", newline="\n")
        next(row for row in self.generic.descriptor["interface"]["ports"] if row["name"] == "recognition_date")["name"] = "report_date"
        self.generic.package["inputs"]["report_date"] = self.generic.package["inputs"].pop("recognition_date")
        self.generic.repin(); package = self.package("module"); package["manifest"].update(report_date="9999-12-31", issue_date="0001-01-01")
        first, _ = self.run_saved("module", package); self.calculated(first)
        package["inputs"]["report_date"] = "2026-04-01"
        changed, _ = self.run_saved("module", package); self.calculated(changed)
        self.assertEqual((first["results"]["result"], changed["results"]["result"]), ("20", "0"))
        self.assertNotEqual(first["semantic_run_digest"], changed["semantic_run_digest"])

    def test_preview_keeps_dates_but_has_no_consumable_state(self):
        for family in ("module", "bounded"):
            package = self.package(family); package["manifest"].update(mode="preview", report_date="2026-07-02", issue_date="2026-07-03")
            result, _ = self.run_saved(family, package); self.calculated(result)
            self.assertEqual(result["status"], "provisional"); self.assertEqual(result["closing_state"], [])
            with self.assertRaises(DataError): carry_state(result)

    def test_actual_saved_predecessor_carry_and_metadata_variants_are_identical(self):
        package = self.package("module"); package["manifest"].update(report_date="2026-07-02", issue_date="2026-07-03")
        first, output = self.run_saved("module", package); original = deepcopy(first)
        successor = deepcopy(package); successor["state_cells"] = carry_state(load_completed_result(output))
        successor["manifest"].update(period={"start": "2026-04-01", "end": "2026-07-01"}, cutoff="2026-07-04T00:00:00Z", report_date="2026-07-05", issue_date="2026-07-06")
        carried, _ = self.run_saved("module", successor); self.calculated(carried)
        self.assertEqual(carried["closing_state"][0]["quantity"], "45")
        self.assertEqual(successor["state_cells"][0]["prior_result_ref"], "result@sha256:" + first["semantic_run_digest"])
        successor["manifest"].update(report_date="0001-01-01", issue_date="9999-12-31")
        changed, _ = self.run_saved("module", successor); self.same_economics(carried, changed)
        self.assertEqual(first, original); self.assertEqual(load_completed_result(output), original)

    def test_invalid_dated_rerun_atomically_replaces_success_without_numeric_state(self):
        for family in ("module", "bounded"):
            package = self.package(family); first, output = self.run_saved(family, package); self.calculated(first)
            package["manifest"]["report_date"] = "2026-02-30"
            invalid = run_package(bind_package(package, self.source(family)), self.source(family), backend="reference", artifact_dir=output)
            self.assertEqual(load_completed_result(output), invalid)
            self.assertEqual(invalid["status"], "blocked"); self.assertEqual(invalid["statements"], []); self.assertEqual(invalid["closing_state"], []); self.assertNotIn("result_digest", invalid)

    def test_run_label_stays_independent_with_dates_present(self):
        for family in ("module", "bounded"):
            package = self.package(family); package["manifest"].update(report_date="2026-07-01", issue_date="2026-07-02")
            first, _ = self.run_saved(family, package); package["manifest"]["run_id"] = "other-invocation"
            second, _ = self.run_saved(family, package); self.calculated(second)
            self.assertEqual(first["semantic_run_digest"], second["semantic_run_digest"])
            self.assertEqual(first["trace"], second["trace"]); self.assertEqual(first["closing_state"], second["closing_state"])

    def test_new_capability_does_not_silently_repin_old_build_bound_package(self):
        package = bind_package(self.package("module"), self.source("module")); package["manifest"].update(report_date="2026-07-01", compiler_build="old-implementation")
        result = run_package(package, self.source("module"), backend="reference")
        self.assertEqual(result["status"], "blocked"); self.assertEqual(result["diagnostics"][0]["code"], "MANIFEST_DIGEST_MISMATCH")
        self.assertEqual(result["closing_state"], [])


class RunDateNativeTests(DateFixture, unittest.TestCase):
    def test_compact_native_metadata_keeps_graph_financials_and_state(self):
        from spl_compiler.audited_artifacts import load_completed_audited_result, iter_audited_trace
        for family in ("module", "bounded"):
            package = self.package(family); results = []; graphs = []
            for position, dates in enumerate(({}, {"report_date": "9999-12-31", "issue_date": "0001-01-01"})):
                original = deepcopy(package); original["manifest"].update(dates); bound = bind_package(original, self.source(family))
                output = self.output_root / (family + "-compact-" + str(position))
                result = run_package(bound, self.source(family), backend="compare", artifact_dir=output, audit_profile="compact-v2")
                self.assertEqual(load_completed_audited_result(output), result); self.calculated(result)
                results.append(result); graphs.append(list(iter_audited_trace(output)))
                OBSERVATIONS.append({"test": self.id(), "family": family, "backend": "compare", "audit_profile": "compact-v2", "bound": deepcopy(bound), "result": deepcopy(result), "output": str(output)})
            self.assertEqual(graphs[0], graphs[1])
            self.assertEqual(results[0]["result_digest"], results[1]["result_digest"])
            for field in ("semantic_run_digest", "statements", "detail", "closing_state", "reconciliation", "policy_review"):
                self.assertEqual(results[0][field], results[1][field], field)

    def test_native_dates_preserve_all_backend_economics_and_actual_saved_carry(self):
        self.add_recognition_input(); package = self.package("module")
        first, original_output = self.run_saved("module", package, "compare"); original = deepcopy(first)
        package["manifest"].update(report_date="9999-12-31", issue_date="0001-01-01")
        dated, _ = self.run_saved("module", package, "compare"); self.same_economics(first, dated)
        successor = deepcopy(package); successor["state_cells"] = carry_state(load_completed_result(original_output))
        successor["manifest"].update(period={"start": "2026-04-01", "end": "2026-07-01"}, cutoff="2026-07-04T00:00:00Z")
        successor["inputs"].update(recognition_date="2026-05-01", economic_period={"start": "2026-04-01", "end": "2026-07-01"})
        next_result, _ = self.run_saved("module", successor, "compare"); self.calculated(next_result)
        self.assertEqual(next_result["closing_state"][0]["quantity"], "45")
        preview_package = deepcopy(successor); preview_package["manifest"].update(mode="preview", report_date="2024-02-29")
        preview, _ = self.run_saved("module", preview_package, "compare"); self.calculated(preview)
        self.assertEqual(preview["status"], "provisional"); self.assertEqual(preview["closing_state"], []); self.assertEqual(preview["results"], next_result["results"])
        successor["inputs"]["recognition_date"] = "2026-07-01"
        changed, _ = self.run_saved("module", successor, "compare"); self.calculated(changed); self.assertEqual(changed["results"]["result"], "0")
        self.assertNotEqual(next_result["semantic_run_digest"], changed["semantic_run_digest"])
        self.assertEqual(first, original); self.assertEqual(load_completed_result(original_output), original)

    def test_native_bounded_metadata_preserves_financials_and_publication(self):
        package = self.package("bounded"); first, _ = self.run_saved("bounded", package, "compare")
        package["manifest"].update(report_date="0001-01-01", issue_date="9999-12-31")
        second, _ = self.run_saved("bounded", package, "compare"); self.same_economics(first, second)
        self.assertEqual(first["result_digest"], second["result_digest"])


if __name__ == "__main__": unittest.main()
