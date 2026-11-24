"""Actual opt-in canonical wrappers; fixture classes are composed, not inherited."""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import sys
from unittest.mock import patch

from Tests import test_modules as fixtures
from spl_compiler.artifacts import PublicationError, load_completed_result
from spl_compiler.audited_artifacts import (load_completed_audited_result, iter_audited_trace,
                                           carry_audited_state, iter_v1_compatible_audited_trace)
from spl_compiler.codecs import DataError, file_digest, read_json
from spl_compiler.fixtures import sv_package
from spl_compiler.lean_tools import ROOT, lean_environment
from spl_compiler.modules import bind_module_package, run_module_package
from spl_compiler.run import bind_package, carry_state, run_package

OBSERVATIONS = []


class CompactPublicationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.fixture = fixtures.ModuleTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.add_state()

    def package(self):
        return bind_module_package(deepcopy(self.fixture.package), self.fixture.root)

    def execute(self, package, name, profile="compact-v2"):
        result = run_module_package(package, self.fixture.root, backend="compare",
                                    artifact_dir=self.work / name, audit_profile=profile)
        self.assertEqual(result["diagnostics"], [], result)
        loaded = (load_completed_audited_result if profile == "compact-v2" else load_completed_result)(self.work / name)
        self.assertEqual(loaded, result)
        OBSERVATIONS.append({"test": self.id(), "name": name, "profile": profile,
                             "status": result["status"], "closing_state": result["closing_state"]})
        return loaded

    def advance(self, package, cells, number):
        package = deepcopy(package)
        starts = ["2026-01-01", "2026-04-01", "2026-07-01", "2026-10-01"]
        ends = ["2026-04-01", "2026-07-01", "2026-10-01", "2027-01-01"]
        package["manifest"].update(run_id=f"carry-{number}", period={"start": starts[number], "end": ends[number]},
                                    cutoff=ends[number] + "T00:00:00Z")
        package["state_cells"] = cells
        return bind_module_package(package, self.fixture.root)

    def test_actual_v1_state_into_v2_and_v2_into_v2_successor(self):
        package = self.package()
        first = self.execute(package, "old", "array-v1")
        second_package = self.advance(package, carry_state(first), 1)
        second = self.execute(second_package, "new")
        self.assertEqual(second["closing_state"][0]["movement"]["opening"], "25")
        self.assertEqual(second["closing_state"][0]["quantity"], "45")
        third_package = self.advance(package, carry_audited_state(self.work / "new"), 2)
        third = self.execute(third_package, "next")
        self.assertEqual(third["closing_state"][0]["quantity"], "65")
        self.assertEqual(third["closing_state"][0]["movement"]["opening"], "45")
        self.assertEqual(third_package["state_cells"][0]["prior_result_ref"], second["closing_state"][0]["prior_result_ref"])

    def test_legacy_actual_finance_and_exact_native_array_nodes(self):
        source = ROOT / "cases/sv/sv01-readable.spl"
        package = bind_package(sv_package(), source)
        folder = self.work / "legacy"
        result = run_package(package, source, artifact_dir=folder, audit_profile="compact-v2")
        self.assertEqual(result["diagnostics"], [], result)
        self.assertEqual((result["statements"][0]["earned"], result["statements"][0]["payable"]), ("33000", "18000"))
        self.assertEqual(load_completed_audited_result(folder), result)
        marker = read_json(folder / "completion.json")
        owned = folder / ".runs" / marker["invocation_id"]
        _, env = lean_environment()
        native = subprocess.run([str(ROOT / ".lake/build/bin/spl.exe"), "interpret", str(owned / "consumed.source.spl"),
                                 str(owned / "bindings.json")], cwd=ROOT, env=env, capture_output=True, timeout=60)
        self.assertEqual(native.returncode, 0, native.stderr)
        old_array = json.loads(native.stdout)
        self.assertEqual(list(iter_audited_trace(folder)), old_array["trace"])
        streamed = subprocess.run([str(ROOT / ".lake/build/bin/spl_trace_stream.exe"), str(owned / "consumed.source.spl"),
                                    str(owned / "bindings.json"), "--compact-v2"], cwd=ROOT, env=env,
                                   capture_output=True, timeout=60)
        self.assertEqual(streamed.returncode, 0, streamed.stderr)
        self.assertEqual(streamed.stdout, (owned / "audit.native.jsonl").read_bytes())
        old_result = run_package(package, source, artifact_dir=self.work / "legacy-v1")
        self.assertEqual(old_result["diagnostics"], [])
        self.assertEqual(list(iter_v1_compatible_audited_trace(folder)), old_result["trace"])
        with self.assertRaises(PublicationError):
            load_completed_result(folder)

    def test_preview_and_preflight_block_are_nonconsumable(self):
        package = self.package()
        package["manifest"]["mode"] = "preview"
        result = self.execute(package, "preview")
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["closing_state"], [])
        with self.assertRaises(DataError):
            carry_audited_state(self.work / "preview")
        package = self.package()
        package["inputs"]["cash"]["value"] = "-1"
        package = bind_module_package(package, self.fixture.root)
        folder = self.work / "blocked"
        result = run_module_package(package, self.fixture.root, artifact_dir=folder, audit_profile="compact-v2")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["trace"]["status"], "unavailable")
        self.assertEqual(result["closing_state"], [])
        self.assertEqual(load_completed_audited_result(folder), result)

    def test_reference_backend_rejected_and_old_success_invalidated(self):
        self.execute(self.package(), "rerun")
        with self.assertRaisesRegex(ValueError, "COMPACT_AUDIT_REQUIRES_NATIVE_PUBLICATION"):
            run_module_package(self.package(), self.fixture.root, backend="reference",
                               artifact_dir=self.work / "rerun", audit_profile="compact-v2")
        with self.assertRaises(PublicationError):
            load_completed_audited_result(self.work / "rerun")

    def test_actual_runtime_memory_guard_never_publishes_finance(self):
        from spl_compiler import compact_execution
        original = compact_execution._stage
        def limited(command, folder, **kwargs):
            if Path(folder).name == "audit-process":
                command = [sys.executable, "-c", "import time; allocation=bytearray(280*1024*1024); time.sleep(5)"]
            return original(command, folder, **kwargs)
        folder = self.work / "memory-limited"
        with patch.object(compact_execution, "_stage", side_effect=limited):
            result = run_module_package(self.package(), self.fixture.root, artifact_dir=folder, audit_profile="compact-v2")
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["diagnostics"][0]["code"], "AUDIT_RESOURCE_LIMIT")
        self.assertEqual(result["results"], {})
        self.assertEqual(result["closing_state"], [])
        self.assertEqual(load_completed_audited_result(folder), result)
        marker = read_json(folder / "completion.json")
        report = read_json(folder / ".runs" / marker["invocation_id"] / "audit-process/process.json")
        self.assertEqual(report["working_set_budget_bytes"], 256*1024*1024)
        self.assertTrue(report["working_set_budget_exceeded"])
        self.assertEqual(report["status"], "failed")

    def test_native_error_retains_complete_graph_and_discards_state(self):
        source = self.fixture.source
        text = source.read_text(encoding="utf-8")
        text = text.replace('define earned =', 'define choice=if rate > 0.5 then USD 1 else USD 2; require rate > 0.5 else "SELECTED_FAILURE"; define earned =')
        source.write_text(text, encoding="utf-8")
        self.fixture.repin()
        folder = self.work / "native-error"
        result = run_module_package(self.package(), self.fixture.root, artifact_dir=folder, audit_profile="compact-v2")
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["diagnostics"][0]["code"], "SELECTED_FAILURE")
        self.assertEqual(result["trace"]["status"], "complete")
        self.assertEqual(result["results"], {})
        self.assertEqual(result["closing_state"], [])
        nodes = list(iter_audited_trace(folder))
        self.assertTrue(any(node["status"] == "failed" for node in nodes))
        self.assertTrue(any(node["status"] == "not_evaluated" for node in nodes))
        self.assertEqual(load_completed_audited_result(folder), result)

    def test_literals_resembling_number_or_unit_metadata_remain_records(self):
        source = self.fixture.source
        source.write_text('schedule Literal language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" '
                          '{ input original:{numerator:Text,denominator:Text,unit:Text,meta:Text}; emit "result"=original; }', encoding="utf-8")
        literal = {"numerator": "original", "denominator": "not-a-number", "unit": "UsageHour", "meta": "owner_context"}
        typ = {"name": "Record", "args": [], "fields": [[name, fixtures.typ("Text")] for name in sorted(literal)]}
        self.fixture.descriptor["interface"]["ports"] = [fixtures.port("original", "input", typ), fixtures.port("result", "result", typ)]
        self.fixture.descriptor["state"] = []
        self.fixture.package.update(inputs={"original": literal}, parameters={}, state_cells=[])
        self.fixture.repin()
        result = self.execute(self.package(), "literal")
        self.assertEqual(result["results"], {"result": literal})
        self.assertTrue(any(node.get("result") == literal for node in iter_audited_trace(self.work / "literal")))

    def test_imported_and_unused_extended_owner_contexts(self):
        adapter = importlib.import_module("cases.usage-conversion.build_modules")
        registry = self.work / "usage"
        refs = adapter.register_all(registry)
        for name in ("minute-meter", "hour-meter", "inferred-import", "unused-extended"):
            with self.subTest(name=name):
                package = adapter.usage_package(name, root=registry, reference=refs[name], bind=True)
                folder = self.work / name
                result = run_module_package(package, registry, artifact_dir=folder, audit_profile="compact-v2")
                self.assertEqual(result["diagnostics"], [], result)
                self.assertEqual(load_completed_audited_result(folder), result)
                if name in {"minute-meter", "hour-meter"}:
                    self.assertEqual(result["results"]["earned"], "18")
                if name == "inferred-import":
                    self.assertEqual(result["results"]["quantity"], {"value": "3", "unit": "UsageHour"})
                if name == "unused-extended":
                    self.assertEqual(result["results"], {"earned": "1"})


if __name__ == "__main__":
    unittest.main()
