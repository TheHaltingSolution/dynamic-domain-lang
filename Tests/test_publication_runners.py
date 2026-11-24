"""Real canonical publication boundaries, including interrupted reruns.

Compare mode is explicit for the two positive runners and the settlement
missing-population path. Other lifecycle cases use the actual reference runner.
Imported fixture modules are composed, never inherited or re-exported as tests.
OBSERVATIONS lets an external test launcher retain actual stage evidence.
"""
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.r1 import build_modules as registration
from cases.settlement import build_modules as settlement
from spl_compiler import artifacts
from spl_compiler import run as legacy_runner
from spl_compiler.codecs import DataError, read_json
from spl_compiler.fixtures import sv_package
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import run_module_package
from spl_compiler.run import bind_package, carry_state, run_package
from Tests import test_modules as module_fixtures
from Tests import test_settlement_oracle as settlement_fixtures


OBSERVATIONS = []


class PublicationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.generic = module_fixtures.ModuleTests()
        self.generic.setUp()
        self.addCleanup(self.generic.doCleanups)
        self.generic.add_state()
        self.sv_source = ROOT / "cases/sv/sv01-readable.spl"

    def package(self, family):
        if family == "generic":
            return bind_package(deepcopy(self.generic.package), self.generic.root)
        return bind_package(sv_package(), self.sv_source)

    def run_family(self, family, package, output, backend="reference"):
        if family == "generic":
            return run_module_package(package, self.generic.root, backend=backend, artifact_dir=output)
        return run_package(package, self.sv_source, backend=backend, artifact_dir=output)

    def record(self, **values):
        OBSERVATIONS.append({"test": self.id(), **values})

    def completed(self, output, expected):
        loaded = artifacts.load_completed_result(output)
        self.assertEqual(loaded, expected)
        marker = read_json(output / "completion.json")
        self.assertEqual(marker["status"], "completed")
        self.assertTrue(marker["result_path"].startswith(".runs/" + marker["invocation_id"] + "/"))
        self.assertEqual(read_json(output / "result.json"), loaded)
        return marker, loaded

    def empty_finance(self, result):
        self.assertEqual(result["status"], "blocked", result["diagnostics"])
        for field in ("statements", "detail", "closing_state"):
            self.assertEqual(result[field], [], field)
        self.assertEqual(result["reconciliation"], {})
        if "results" in result:
            self.assertEqual(result["results"], {})
        self.assertNotIn("result_digest", result)
        with self.assertRaises(DataError):
            carry_state(result)

    def test_generic_native_compare_commits_real_state_and_serialized_successor(self):
        output = self.root / "generic-first"
        first = run_package(self.package("generic"), self.generic.root, backend="compare", artifact_dir=output)
        self.assertEqual(first["diagnostics"], [])
        self.assertEqual(first["trace_origin"], "native_ir_interpreter")
        self.assertEqual(first["verification"]["backend"], "compare")
        self.assertTrue(first["verification"]["reference_agrees"])
        self.assertEqual(first["statements"], ["20"])
        self.assertEqual(first["closing_state"][0]["quantity"], "25")
        marker, loaded = self.completed(output, first)
        stored = read_json(output / ".runs" / marker["invocation_id"] / "closing-state.json")
        self.assertEqual(stored, loaded["closing_state"])
        next_package = self.package("generic")
        next_package["manifest"].update(run_id="serialized-successor", period={"start": "2026-04-01", "end": "2026-07-01"},
                                        cutoff="2026-07-03T00:00:00Z")
        next_package["state_cells"] = carry_state({**loaded, "closing_state": stored})
        next_package = bind_package(next_package, self.generic.root)
        following = self.run_family("generic", next_package, self.root / "generic-next")
        self.assertEqual(following["diagnostics"], [])
        self.assertEqual(following["closing_state"][0]["quantity"], "45")
        self.assertEqual(following["closing_state"][0]["movement"]["opening"], "25")
        self.completed(self.root / "generic-next", following)
        self.record(family="generic", backend="compare", status=first["status"], successor_backend="reference",
                    opening="5", first_closing="25", successor_closing="45", manifest=marker)

    def test_legacy_sv_native_compare_retains_policy_source_and_exact_result(self):
        output = self.root / "legacy"
        package = self.package("legacy")
        result = self.run_family("legacy", package, output, backend="compare")
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["statements"][0]["payable"], "18000")
        self.assertEqual(result["trace_origin"], "native_ir_interpreter")
        self.assertTrue(result["verification"]["reference_agrees"])
        marker, _ = self.completed(output, result)
        owned = output / ".runs" / marker["invocation_id"]
        self.assertEqual((output / "source.spl").read_bytes(), self.sv_source.read_bytes())
        self.assertEqual((owned / "source.spl").read_bytes(), self.sv_source.read_bytes())
        for policy in package["incorporated_policies"]:
            for dependency in (policy["document"], policy["registry"]):
                source = (ROOT / dependency["locator"]).read_bytes()
                self.assertEqual((owned / "review-sources" / dependency["locator"]).read_bytes(), source)
                self.assertEqual((output / "review-sources" / dependency["locator"]).read_bytes(), source)
        self.record(family="legacy", backend="compare", status=result["status"], payable="18000", manifest=marker)

    def test_both_wrappers_invalidate_success_at_every_financial_publication_stage(self):
        for family in ("generic", "legacy"):
            names = ["statement.json", "detail.json", "closing-state.json", "reconciliation.json", "result.json"]
            if family == "generic":
                names.insert(0, "results.json")
            stages = [(location, name) for location in ("private", "mirror") for name in names]
            stages.append(("marker", "completion.json"))
            for index, (location, name) in enumerate(stages):
                with self.subTest(family=family, location=location, file=name):
                    output = self.root / f"{family}-interrupt-{index}"
                    package = self.package(family)
                    first = self.run_family(family, package, output)
                    self.assertEqual(first["status"], "calculated", first["diagnostics"])
                    previous, _ = self.completed(output, first)
                    previous_result = output / previous["result_path"]
                    previous_bytes = previous_result.read_bytes()
                    original = artifacts._atomic_bytes
                    hits = []

                    def interrupt(path, payload):
                        path = Path(path)
                        private = ".runs" in path.relative_to(output).parts
                        selected = ((location == "private" and private) or
                                    (location in {"mirror", "marker"} and path.parent == output))
                        # The initial running marker and blocked compatibility
                        # envelope must be published before this injected stop.
                        final_marker = path.name != "completion.json" or json.loads(payload)["status"] == "completed"
                        initial_envelope = name == "result.json" and not private and b"RUN_IN_PROGRESS" in payload
                        if path.name == name and selected and final_marker and not initial_envelope:
                            hits.append(str(path.relative_to(output)))
                            raise KeyboardInterrupt("injected runner publication interruption")
                        return original(path, payload)

                    with patch.object(artifacts, "_atomic_bytes", side_effect=interrupt):
                        with self.assertRaises(KeyboardInterrupt):
                            self.run_family(family, package, output)
                    self.assertEqual(len(hits), 1)
                    self.assertEqual(previous_result.read_bytes(), previous_bytes)
                    running = read_json(output / "completion.json")
                    self.assertEqual(running["status"], "running")
                    self.assertNotEqual(previous["invocation_id"], running["invocation_id"])
                    with self.assertRaises(artifacts.PublicationError) as rejected:
                        artifacts.load_completed_result(output)
                    self.record(family=family, backend="reference", stage=location, file=name, interruption="KeyboardInterrupt",
                                prior_result_sha256=sha256(previous_bytes).hexdigest(), running_marker=running,
                                loader_error=str(rejected.exception), injected_path=hits[0])

    def test_legacy_financial_finalize_oserror_propagates_without_blocked_republication(self):
        output = self.root / "legacy-io"
        package = self.package("legacy")
        previous = self.run_family("legacy", package, output)
        marker, _ = self.completed(output, previous)
        prior = (output / marker["result_path"]).read_bytes()
        original = artifacts._atomic_bytes
        hits = []
        direct_writes = []
        original_write = legacy_runner.write_json

        def forbid_direct_finalize(path, value):
            if Path(path).name == "statement.json":
                direct_writes.append(str(path))
                raise OSError("financial finalization bypassed central publisher")
            return original_write(path, value)

        def fail_once(path, payload):
            path = Path(path)
            if path.name == "statement.json" and ".runs" in path.relative_to(output).parts and not hits:
                hits.append(str(path.relative_to(output)))
                raise OSError("injected transient private financial write failure")
            return original(path, payload)

        with patch.object(artifacts, "_atomic_bytes", side_effect=fail_once), \
                patch.object(legacy_runner, "write_json", side_effect=forbid_direct_finalize):
            with self.assertRaises(artifacts.PublicationError):
                self.run_family("legacy", package, output)
        self.assertEqual(len(hits), 1)
        self.assertEqual(direct_writes, [], "artifact runs must finalize exclusively through the publication helper")
        self.assertEqual((output / marker["result_path"]).read_bytes(), prior)
        self.assertEqual(read_json(output / "completion.json")["status"], "running")
        with self.assertRaises(artifacts.PublicationError):
            artifacts.load_completed_result(output)
        self.record(family="legacy", backend="reference", injected_path=hits[0], error="PublicationError", completed=False)

    def test_completed_failed_reruns_empty_finances_and_preserve_predecessors(self):
        for family in ("generic", "legacy"):
            with self.subTest(family=family):
                output = self.root / (family + "-failed")
                package = self.package(family)
                previous = self.run_family(family, package, output)
                marker, _ = self.completed(output, previous)
                prior_path = output / marker["result_path"]
                prior_bytes = prior_path.read_bytes()
                package["manifest"]["compiler_build"] = "stale-implementation"
                blocked = self.run_family(family, package, output)
                self.empty_finance(blocked)
                self.assertEqual(blocked["diagnostics"][0]["code"], "MANIFEST_DIGEST_MISMATCH")
                following, _ = self.completed(output, blocked)
                self.assertNotEqual(marker["invocation_id"], following["invocation_id"])
                self.assertEqual(prior_path.read_bytes(), prior_bytes)
                for name in ("statement.json", "detail.json", "closing-state.json"):
                    self.assertEqual(read_json(output / name), [])
                self.assertEqual(read_json(output / "reconciliation.json"), {})
                if family == "generic":
                    self.assertEqual(read_json(output / "results.json"), {})
                self.record(family=family, backend="reference", status="blocked", code="MANIFEST_DIGEST_MISMATCH",
                            previous_invocation=marker["invocation_id"], completed_manifest=following)

    def test_completed_preview_is_inspectable_but_cannot_supply_state(self):
        for family in ("generic", "legacy"):
            with self.subTest(family=family):
                package = self.package(family)
                package["manifest"]["mode"] = "preview"
                result = self.run_family(family, package, self.root / (family + "-preview"))
                self.assertEqual(result["status"], "provisional", result["diagnostics"])
                self.assertEqual(result["closing_state"], [])
                _, loaded = self.completed(self.root / (family + "-preview"), result)
                with self.assertRaises(DataError):
                    carry_state(loaded)
                self.record(family=family, backend="reference", status="provisional", carry_rejected=True)

    def test_settlement_population_label_precedes_native_compare_commit(self):
        registry = self.root / "settlement"
        folder = registry / "cases/settlement"
        folder.mkdir(parents=True)
        for name in ("amounts.spl", "settlement.spl", "policy.md", "neutral.json"):
            shutil.copyfile(ROOT / "cases/settlement" / name, folder / name)
        with ExitStack() as stack:
            for owner, name, value in ((settlement, "ROOT", registry), (settlement, "FOLDER", folder), (registration, "ROOT", registry)):
                stack.enter_context(patch.object(owner, name, value))
            reference = settlement.register_settlement()
            data = settlement_fixtures.fixture()
            data["evidence"] = data["evidence"][:1]
            package = settlement.settlement_package(data, reference=reference)
            original = artifacts.ArtifactPublication.finish
            before_commit = []

            def inspect_finish(publication, result, fields):
                before_commit.append(deepcopy(result))
                self.assertEqual(result["payment_evidence_status"], "no_event_supplied")
                self.empty_finance(result)
                return original(publication, result, fields)

            output = self.root / "settlement-published"
            with patch.object(artifacts.ArtifactPublication, "finish", new=inspect_finish):
                result = settlement.run_settlement_package(package, registry, backend="compare", artifact_dir=output)
            self.assertEqual(len(before_commit), 1)
            self.assertEqual(result["diagnostics"][0]["code"], "SETTLEMENT_PAYMENT_POPULATION_REQUIRED")
            self.assertEqual(result["trace_origin"], "native_ir_interpreter")
            self.completed(output, result)
            self.record(family="settlement", backend="compare", status="blocked", label_before_finish="no_event_supplied",
                        code=result["diagnostics"][0]["code"])

    def test_unknown_evidence_labels_are_bounded_and_never_change_success(self):
        package = self.package("generic")
        allowed = {"payment_evidence_status": "no_event_supplied", "funding_evidence_status": "not_assessed",
                   "recovery_evidence_status": "no_event_supplied"}
        labels = {"MANIFEST_DIGEST_MISMATCH": allowed}
        baseline = run_module_package(package, self.generic.root, backend="reference")
        labelled_success = run_module_package(package, self.generic.root, backend="reference", blocked_evidence_labels=labels)
        self.assertEqual(labelled_success, baseline)
        self.assertEqual(baseline["status"], "calculated")
        self.assertEqual(baseline["result_digest"], labelled_success["result_digest"])
        package["manifest"]["compiler_build"] = "stale-implementation"
        output = self.root / "unknown-labels"
        blocked = run_module_package(package, self.generic.root, backend="reference", artifact_dir=output,
                                     blocked_evidence_labels=labels)
        self.empty_finance(blocked)
        for field, value in allowed.items():
            self.assertEqual(blocked[field], value)
        self.completed(output, blocked)
        forbidden = [{"X": {field: "no_event_supplied"}} for field in
                     ("status", "results", "statements", "closing_state", "result_digest", "semantic_run_digest", "issuance_status", "payable")]
        forbidden += [{"X": {field: value}} for field in allowed for value in
                      (False, 1, "calculated", "complete_with_events", "verified", "", None)]
        forbidden += [[], {1: allowed}, {"X": {}}, {"X": []}]
        for values in forbidden:
            with self.subTest(labels=values), self.assertRaisesRegex(ValueError, "INVALID_BLOCKED_EVIDENCE_LABELS"):
                run_module_package(package, self.generic.root, backend="reference", blocked_evidence_labels=values)
        self.record(family="generic", backend="reference", success_unchanged=True, allowed_unknown_labels=allowed,
                    forbidden_mappings_rejected=len(forbidden))


if __name__ == "__main__":
    unittest.main()
