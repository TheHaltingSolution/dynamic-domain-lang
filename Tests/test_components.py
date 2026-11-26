"""Finite topology controls and actual canonical component outcomes."""
from copy import deepcopy
from importlib import import_module
from pathlib import Path
import unittest
from unittest.mock import patch
from hashlib import sha256
import json
import shutil

from spl_compiler.lean_tools import ROOT
from spl_compiler.audited_artifacts import carry_audited_state
from oracles.contract_burdens import contract_burdens, exact_json, ContractBurdenOracleError

from spl_compiler.artifacts import PublicationError, load_completed_result
from spl_compiler.codecs import DataError, canonical, file_digest, read_json, write_json
from spl_compiler.components import (plan_components, run_components, load_component_outcomes,
                                     _canonical, _canonical_result)
from spl_compiler.modules import bind_module_package, resolve_module

fixtures = import_module("Tests.test_modules")
components = import_module("spl_compiler.components")


class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ModuleTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        source = self.fixture.source.read_text(encoding="utf-8")
        self.fixture.source.write_text(source.replace("input rate:", "input keys: List<Tuple<Text, Text>>; input rate:"), encoding="utf-8")
        self.fixture.descriptor["interface"]["ports"].append(fixtures.port("keys", "input", fixtures.typ("List", fixtures.typ("Tuple", fixtures.typ("Text"), fixtures.typ("Text")))))
        self.fixture.descriptor["compatibility"]["capabilities"].append("spl.tuple-map/1")
        self.fixture.package["inputs"]["keys"] = []
        self.fixture.repin()
        self.base = bind_module_package(self.fixture.package, self.root)
        self.update_binding()
        self.catalog = self.root / "operator-registry.json"
        self.trusted = []
        self.save_catalog()

    def update_binding(self):
        resolved = resolve_module(self.base["module_ref"], self.root)
        self.binding = {"module_ref": resolved.reference, "source_sha256": file_digest(resolved.source_path),
                        "policy_sha256": file_digest(resolved.policy_path), "module_closure": resolved.references}

    def save_catalog(self):
        write_json(self.catalog, {"format": "spl-dependency-registry/1", "profiles": self.trusted})

    def profile(self, kind="gate", namespace="selected-original-links/1", *, selectors=None):
        name = "profiles/p" + str(len(self.trusted)) + ".json"
        value = {"format": "spl-component-dependencies/1", "binding": deepcopy(self.binding),
                 "selectors": selectors if selectors is not None else [{"kind": kind, "namespace": namespace,
                      "rows": ["inputs", "keys", "*"], "key": [{"from": "row", "path": []}]}]}
        write_json(self.root / name, value)
        ref = {"locator": name, "sha256": file_digest(self.root / name)}
        self.trusted.append(ref)
        self.save_catalog()
        return ref

    def job(self, name, keys=(), *, profile=None, package=None):
        value = deepcopy(self.base if package is None else package)
        if package is None:
            value["scope"]["agreement_id"] = "agreement-" + name
            value["scope"]["pool_id"] = "pool-" + name
            value["manifest"]["run_id"] = name
            value["inputs"]["keys"] = deepcopy(list(keys))
            for cell, slot in zip(value["state_cells"], self.fixture.descriptor["state"]):
                cell["scope"].update(agreement_id=value["scope"]["agreement_id"], pool_id=value["scope"]["pool_id"])
                cell["state_key"] = canonical({key: ({**cell["scope"], "purpose": cell["purpose"]})[key] for key in slot["key_fields"]})
        path = "packages/" + name + ".json"
        write_json(self.root / path, value)
        row = {"id": name, "package_ref": {"locator": path, "sha256": file_digest(self.root / path)}}
        if profile is not None:
            row["dependency_profile_ref"] = deepcopy(profile)
        return row

    def request(self, jobs, edges=()):
        return {"format": "spl-component-request/1", "jobs": jobs, "additional_dependencies": list(edges)}

    def plan(self, request):
        return plan_components(request, self.root, trusted_profiles=self.catalog)

    def execute(self, request, plan=None, output=None):
        return run_components(request, self.plan(request) if plan is None else plan, self.root,
                              trusted_profiles=self.catalog, output=output or self.root / "batch",
                              backend="reference", audit_profile="array-v1")

    def test_transitive_join_all_five_resource_kinds_and_independent_partition(self):
        for kind in ["pool", "gate", "allocation_parent", "correction_chain", "cross_contract"]:
            profile = self.profile(kind)
            jobs = [self.job("A", [["owner", "one"]], profile=profile),
                    self.job("B", [["owner", "one"], ["owner", "two"]], profile=profile),
                    self.job("C", [["owner", "two"]], profile=profile), self.job("D", [], profile=profile)]
            plan = self.plan(self.request(jobs))
            with self.subTest(kind=kind):
                self.assertEqual([v["members"] for v in plan["components"]], [["A", "B", "C"], ["D"]])
                self.assertEqual(plan["components"][0]["disposition"], "coordinator_required")

    def test_unknown_absent_and_self_registered_profiles_join_whole_batch(self):
        profile = self.profile()
        first = self.job("A", profile=profile)
        second = self.job("B")
        plan = self.plan(self.request([first, second]))
        self.assertEqual(plan["components"][0]["members"], ["A", "B"])
        self.assertEqual(plan["unknown_footprints"], ["B"])
        second["dependency_profile_ref"] = {"locator": "untrusted.json", "sha256": "0" * 64}
        self.assertEqual(self.plan(self.request([first, second]))["unknown_footprints"], ["B"])
        untrusted = read_json(self.root / profile["locator"])
        untrusted["reviewed"] = True
        write_json(self.root / "untrusted.json", untrusted)
        self.assertEqual(self.plan(self.request([first, second]))["components"][0]["disposition"], "coordinator_required")

    def test_stale_catalog_profile_and_owner_binding_fail_closed(self):
        profile = self.profile()
        request = self.request([self.job("A", profile=profile)])
        value = read_json(self.root / profile["locator"])
        value["binding"]["source_sha256"] = "0" * 64
        write_json(self.root / profile["locator"], value)
        with self.assertRaisesRegex(DataError, "COMPONENT_REFERENCE_CHANGED"):
            self.plan(request)
        changed = {**profile, "sha256": file_digest(self.root / profile["locator"])}
        self.trusted = [changed]; self.save_catalog()
        request["jobs"][0]["dependency_profile_ref"] = changed
        with self.assertRaisesRegex(DataError, "COMPONENT_PROFILE_OWNER_MISMATCH"):
            self.plan(request)

    def test_structural_keys_namespace_and_original_unicode_are_distinct(self):
        first, second = self.profile(namespace="one"), self.profile(namespace="two")
        jobs = [self.job("A", [["owner", "\u00e9"]], profile=first),
                self.job("B", [["owner", "\u00e9"]], profile=second),
                self.job("C", [["different-owner", "\u00e9"]], profile=first)]
        self.assertEqual([v["members"] for v in self.plan(self.request(jobs))["components"]], [["A"], ["B"], ["C"]])
        self.assertNotEqual(_canonical(["\u00e9"]), _canonical(["e\u0301"]))
        self.assertNotEqual(_canonical([True]), _canonical([1]))

    def test_permutation_and_extra_edges_never_remove_joins(self):
        profile = self.profile()
        jobs = [self.job("B", profile=profile), self.job("A", profile=profile)]
        first = self.plan(self.request(jobs))
        second = self.plan(self.request(list(reversed(jobs))))
        self.assertEqual(first["components"], second["components"])
        joined = self.plan(self.request(jobs, [{"left": "A", "right": "B", "reason": "original correction chain"}]))
        self.assertEqual(joined["components"][0]["members"], ["A", "B"])

    def test_connected_distinct_roots_hold_without_dispatch(self):
        profile = self.profile()
        request = self.request([self.job("A", [["owner", "shared"]], profile=profile), self.job("B", [["owner", "shared"]], profile=profile)])
        with patch.object(components, "run_module_package", side_effect=AssertionError("no partial root may execute")):
            result = self.execute(request)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["components"][0]["status"], "not_executed")
        self.assertEqual(result["components"][0]["diagnostics"][0]["code"], "COMPONENT_COORDINATOR_REQUIRED")
        with self.assertRaises(PublicationError): load_completed_result(self.root / "batch")

    def test_reference_independent_whole_outcomes_and_single_alias_execution(self):
        profile = self.profile()
        first = self.job("A", profile=profile)
        second = self.job("B", profile=profile)
        alias = {**deepcopy(first), "id": "Alias"}
        request = self.request([first, second, alias])
        with patch.object(components, "run_module_package", wraps=components.run_module_package) as called:
            result = self.execute(request)
        self.assertEqual(called.call_count, 2)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(load_component_outcomes(self.root / "batch"), result)
        for component in result["components"]:
            loaded = _canonical_result((self.root / "batch" / component["completion"]["path"]).parent)
            self.assertEqual(loaded["statements"], ["20"])
            self.assertFalse(loaded["closing_state"])

    def test_mutated_plan_or_reference_invalidates_old_batch(self):
        profile = self.profile()
        request = self.request([self.job("A", profile=profile)])
        plan = self.plan(request)
        self.execute(request, plan)
        forged = deepcopy(plan)
        forged["components"][0]["members"] = ["forged"]
        with self.assertRaisesRegex(DataError, "COMPONENT_PLAN_CHANGED"):
            self.execute(request, forged)
        with self.assertRaises(PublicationError): load_component_outcomes(self.root / "batch")
        write_json(self.root / request["jobs"][0]["package_ref"]["locator"], {"forged": True})
        with self.assertRaisesRegex(DataError, "COMPONENT_REFERENCE_CHANGED"):
            self.execute(request, plan)

    def test_profile_cannot_silently_drop_missing_rows_or_use_filters(self):
        profile = self.profile(selectors=[{"kind": "gate", "namespace": "x", "rows": ["inputs", "missing", "*"], "key": [{"from": "row", "path": []}]}])
        with self.assertRaisesRegex(DataError, "COMPONENT_SELECTOR_SHAPE"):
            self.plan(self.request([self.job("A", profile=profile)]))
        value = read_json(self.root / profile["locator"])
        value["selectors"][0]["where"] = {"eligible": True}
        write_json(self.root / profile["locator"], value)
        changed = {**profile, "sha256": file_digest(self.root / profile["locator"])}
        self.trusted = [changed]; self.save_catalog()
        with self.assertRaises(DataError): self.plan(self.request([self.job("A", profile=changed)]))

    def test_state_writer_stays_connected_across_period_and_boundary_changes(self):
        self.fixture.add_state()
        self.base = bind_module_package(self.fixture.package, self.root)
        self.update_binding()
        profile = self.profile(selectors=[])
        first, second = deepcopy(self.base), deepcopy(self.base)
        second["manifest"]["period"] = {"start": "2026-04-01", "end": "2026-07-01"}
        second["state_cells"][0]["boundary"] = "2026-04-01"
        request = self.request([self.job("A", profile=profile, package=first), self.job("B", profile=profile, package=second)])
        plan = self.plan(request)
        self.assertEqual(plan["components"][0]["members"], ["A", "B"])
        state = [resource for resource in plan["resources"] if resource["kind"] == "state"]
        self.assertEqual(len(state), 1)
        self.assertEqual(state[0]["jobs"], ["A", "B"])
        with patch.object(components, "run_module_package", side_effect=AssertionError("no sequential pseudo transaction")):
            self.assertEqual(self.execute(request, plan)["components"][0]["status"], "not_executed")

    def test_one_source_failure_keeps_independent_final_state_and_preview_is_nonconsumable(self):
        self.fixture.add_state()
        source = self.fixture.source.read_text(encoding="utf-8")
        self.fixture.source.write_text(source.replace("define earned", 'require cash < USD 150 else "TEST_CASH_BOUND"; define earned'), encoding="utf-8")
        self.fixture.repin()
        self.base = bind_module_package(self.fixture.package, self.root)
        self.update_binding()
        profile = self.profile(selectors=[])
        bad, good = self.job("A", profile=profile), self.job("B", profile=profile)
        package = read_json(self.root / bad["package_ref"]["locator"])
        package["inputs"]["cash"]["value"] = "200"
        write_json(self.root / bad["package_ref"]["locator"], package)
        bad["package_ref"]["sha256"] = file_digest(self.root / bad["package_ref"]["locator"])
        result = self.execute(self.request([bad, good]))
        self.assertEqual([v["status"] for v in result["components"]], ["blocked", "calculated"])
        self.assertEqual(result["status"], "partial")
        for index, component in enumerate(result["components"]):
            actual = _canonical_result((self.root / "batch" / component["completion"]["path"]).parent)
            if index == 0:
                self.assertEqual(actual["diagnostics"][0]["code"], "TEST_CASH_BOUND")
                self.assertFalse(actual["statements"] or actual["closing_state"])
                self.assertFalse(component["state_consumable"])
            else:
                self.assertEqual(actual["closing_state"][0]["quantity"], "25")
                self.assertTrue(component["state_consumable"])
        preview = deepcopy(self.base); preview["manifest"]["mode"] = "preview"
        result = self.execute(self.request([self.job("Preview", profile=profile, package=preview)]), output=self.root / "preview")
        self.assertEqual(result["components"][0]["status"], "provisional")
        self.assertFalse(result["components"][0]["state_consumable"])

    def test_private_consumed_snapshot_survives_live_registry_mutation(self):
        profile = self.profile(selectors=[])
        request = self.request([self.job("A", profile=profile), self.job("B", profile=profile)])
        plan = self.plan(request)
        original = components.run_module_package
        def changed(package, registry_root, **kwargs):
            self.fixture.source.write_text("deliberately corrupted live source", encoding="utf-8")
            return original(package, registry_root, **kwargs)
        with patch.object(components, "run_module_package", side_effect=changed):
            result = self.execute(request, plan)
        self.assertEqual([v["status"] for v in result["components"]], ["calculated", "calculated"])

    def test_corrupted_private_package_or_cancel_leaves_no_completed_summary(self):
        profile = self.profile(selectors=[])
        request = self.request([self.job("A", profile=profile)])
        plan = self.plan(request)
        self.execute(request, plan)
        with patch.object(components, "run_module_package", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): self.execute(request, plan)
        with self.assertRaises(PublicationError): load_component_outcomes(self.root / "batch")
        original = components.run_module_package
        def changed(package, registry_root, **kwargs):
            private = Path(registry_root).parent / "packages/job-A.json"
            private.write_text("{}", encoding="utf-8")
            return original(package, registry_root, **kwargs)
        with patch.object(components, "run_module_package", side_effect=changed):
            with self.assertRaisesRegex(DataError, "COMPONENT_PACKAGE_CHANGED"): self.execute(request, plan)
        with self.assertRaises(PublicationError): load_component_outcomes(self.root / "batch")

    def test_resource_budgets_reject_without_truncating_or_shortening_keys(self):
        profile = self.profile()
        request = self.request([self.job("A", [["owner", "x" * 2000]], profile=profile)])
        with patch.object(components, "MAX_RESOURCE_KEY_BYTES", 1024):
            with self.assertRaisesRegex(DataError, "COMPONENT_KEY_BYTE_LIMIT"):
                self.plan(request)
        with patch.object(components, "MAX_RESOURCES", 1):
            with self.assertRaisesRegex(DataError, "COMPONENT_RESOURCE_LIMIT"):
                self.plan(request)

    def test_registered_reviewed_flag_and_illegal_selector_tokens_are_rejected(self):
        for field, value in [("reviewed", True), ("selectors", [{"kind": "gate", "namespace": "x", "rows": [False], "key": [{"from": "row", "path": []}]}])]:
            ref = self.profile()
            profile = read_json(self.root / ref["locator"])
            profile[field] = value
            write_json(self.root / ref["locator"], profile)
            ref["sha256"] = file_digest(self.root / ref["locator"])
            self.trusted = [ref]; self.save_catalog()
            with self.subTest(field=field), self.assertRaises(DataError):
                self.plan(self.request([self.job("A", profile=ref)]))

    def test_completed_independent_root_survives_later_batch_interruption(self):
        profile = self.profile(selectors=[])
        request = self.request([self.job("A", profile=profile), self.job("B", profile=profile)])
        original = components.run_module_package
        calls = 0
        def interrupted(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2: raise KeyboardInterrupt
            return original(*args, **kwargs)
        with patch.object(components, "run_module_package", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt): self.execute(request)
        with self.assertRaises(PublicationError): load_component_outcomes(self.root / "batch")
        running = read_json(self.root / "batch/completion.json")
        first = self.root / "batch/.runs" / running["invocation_id"] / "components/0000"
        self.assertEqual(_canonical_result(first)["statements"], ["20"])

    def test_loader_rejects_owned_summary_pointing_to_a_previous_invocation(self):
        profile = self.profile(selectors=[])
        request = self.request([self.job("A", profile=profile)])
        previous = self.execute(request)
        current = self.execute(request)
        root = self.root / "batch"
        marker = read_json(root / "completion.json")
        result_path = root / marker["result_path"]
        forged = deepcopy(current)
        forged["components"][0]["completion"] = previous["components"][0]["completion"]
        payload = (json.dumps(forged, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        result_path.write_bytes(payload)
        for entry in marker["files"]:
            if entry["path"] == marker["result_path"]:
                entry.update(bytes=len(payload), sha256=sha256(payload).hexdigest())
        write_json(root / "completion.json", marker)
        with self.assertRaisesRegex(PublicationError, "COMPONENT_COMPLETION_OWNERSHIP"):
            load_component_outcomes(root)

    def test_loader_rejects_malformed_boolean_summary_even_with_updated_file_hash(self):
        profile = self.profile(selectors=[])
        result = self.execute(self.request([self.job("A", profile=profile)]))
        result["components"][0]["state_consumable"] = 0
        root = self.root / "batch"
        marker = read_json(root / "completion.json")
        payload = (json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        (root / marker["result_path"]).write_bytes(payload)
        for entry in marker["files"]:
            if entry["path"] == marker["result_path"]:
                entry.update(bytes=len(payload), sha256=sha256(payload).hexdigest())
        write_json(root / "completion.json", marker)
        with self.assertRaises(PublicationError): load_component_outcomes(root)


class ComponentNativeTests(unittest.TestCase):
    """One aggregate native witness; no inherited/re-exported test classes."""
    def test_native_coordinated_root_independent_outcome_and_actual_successor(self):
        burden_tests = import_module("Tests.test_contract_burden_modules")
        original_facts = import_module("Tests.test_contract_burden_oracle")
        burden_tests.ContractBurdenModuleTests.setUpClass()
        self.addCleanup(burden_tests.ContractBurdenModuleTests.doClassCleanups)
        root = burden_tests.ContractBurdenModuleTests.root
        owner = burden_tests.burdens
        generic = fixtures.ModuleTests()
        generic.setUp(); self.addCleanup(generic.doCleanups)
        for name in ["calculation.spl", "policy.md", "descriptor.json"]:
            shutil.copyfile(generic.root / name, root / name)
        generic_package = bind_module_package(generic.package, root)
        generic_package["scope"].update(agreement_id="independent-agreement", pool_id="independent-pool")
        source_profile = read_json(ROOT / "cases/component-profiles/entitlement-burdens.json")
        resolved = resolve_module(generic_package["module_ref"], root)
        generic_profile = {"format": "spl-component-dependencies/1", "binding": {
            "module_ref": resolved.reference, "source_sha256": file_digest(resolved.source_path),
            "policy_sha256": file_digest(resolved.policy_path), "module_closure": resolved.references}, "selectors": []}
        profiles = []
        for name, value in [("burden", source_profile), ("independent", generic_profile)]:
            path = "dependency-profiles/" + name + ".json"
            write_json(root / path, value)
            profiles.append({"locator": path, "sha256": file_digest(root / path)})
        catalog = root / "operator-selected-profiles.json"
        write_json(catalog, {"format": "spl-dependency-registry/1", "profiles": profiles})
        controls = []

        def job(name, package, profile):
            path = "native-packages/" + name + ".json"
            write_json(root / path, package)
            return {"id": name, "package_ref": {"locator": path, "sha256": file_digest(root / path)},
                    "dependency_profile_ref": profile}

        def execute(name, data, cells=None):
            package = owner.entitlement_burden_package(data,
                reference=burden_tests.ContractBurdenModuleTests.reference, state_cells=cells)
            # Explicit preparation boundary before generic component execution.
            owner.validate_prepared_package(package)
            request = {"format": "spl-component-request/1", "jobs": [
                job("Burden", package, profiles[0]), job("Independent", generic_package, profiles[1])],
                "additional_dependencies": []}
            plan = plan_components(request, root, trusted_profiles=catalog)
            self.assertEqual([row["members"] for row in plan["components"]], [["Burden"], ["Independent"]])
            output = root / name
            result = run_components(request, plan, root, trusted_profiles=catalog, output=output,
                                    backend="compare", audit_profile="compact-v2")
            self.assertEqual(load_component_outcomes(output), result)
            values = {}
            paths = {}
            for row in result["components"]:
                folder = (output / row["completion"]["path"]).parent
                value = _canonical_result(folder)
                self.assertEqual(value.get("trace_origin"), "native_ir_interpreter", value["diagnostics"])
                values[row["members"][0]], paths[row["members"][0]] = value, folder
            self.assertEqual(values["Independent"]["statements"], ["20"])
            for value in values.values():
                self.assertEqual(value["issuance_status"], "unissued")
            controls.append({"name": name, "original_facts": deepcopy(data), "actual_opening_cells": deepcopy(cells),
                             "summary": result, "paths": {key: str(value) for key, value in paths.items()}})
            return package, values, paths

        original = original_facts.fixture()
        package, first, paths = execute("component-q1", original)
        expected = exact_json(contract_burdens(original))
        self.assertEqual(owner.neutral_result(first["Burden"]["results"]["comparison"]),
                         {key: value for key, value in expected.items() if key != "closing_state"})
        self.assertEqual(owner.neutral_state(first["Burden"]["closing_state"][0]["quantity"]), expected["closing_state"])
        standalone = components.run_module_package(package, root, backend="compare", artifact_dir=root / "standalone", audit_profile="compact-v2")
        for key in ["status", "results", "statements", "detail", "closing_state", "reconciliation"]:
            self.assertEqual(first["Burden"][key], standalone[key], key)
        for key in ["logical_sha256", "transport_sha256", "node_count", "edge_count", "expanded_trace_bytes"]:
            self.assertEqual(first["Burden"]["trace"][key], standalone["trace"][key], key)
        cells = carry_audited_state(paths["Burden"])
        previous = owner.neutral_result(first["Burden"]["results"]["comparison"])
        previous["closing_state"] = owner.neutral_state(cells[0]["quantity"])
        data = original_facts.successor(original, previous, 2)
        data["prior_result"]["result_ref"] = cells[0]["prior_result_ref"]
        _, second, _ = execute("component-q2", data, cells)
        expected = exact_json(contract_burdens(data))
        self.assertEqual(owner.neutral_result(second["Burden"]["results"]["comparison"]),
                         {key: value for key, value in expected.items() if key != "closing_state"})
        self.assertEqual(owner.neutral_state(second["Burden"]["closing_state"][0]["quantity"]), expected["closing_state"])
        bad = original_facts.paid_method(original_facts.remove_payments(original_facts.fixture()))
        with self.assertRaises(ContractBurdenOracleError): contract_burdens(bad)
        _, failed, _ = execute("component-blocked", bad)
        self.assertEqual(failed["Burden"]["diagnostics"][0]["code"], "BURDEN_PAID_BASIS_UNKNOWN")
        self.assertFalse(failed["Burden"]["results"] or failed["Burden"]["closing_state"])
        self.assertEqual(failed["Independent"]["status"], "calculated")
        # External recorder retains this before temporary fixture cleanup.
        self.native_controls = controls
