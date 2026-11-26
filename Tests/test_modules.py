"""Registration, generic canonical finalization and independent Cedar witnesses."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from spl_compiler.codecs import DataError, canonical, file_digest, read_json, write_json
from spl_compiler.lean_tools import ROOT
from spl_compiler.modules import (bind_module_package, resolve_module,
                                 run_module_package, validate_module_package)
from spl_compiler.run import bind_package, run_package


def typ(name, *args):
    return {"name": name, "args": list(args)}


def port(name, role, type_, domain=None):
    return {"name": name, "role": role, "type": type_, "domain": domain or {}, "dimensions": []}


class ModuleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "calculation.spl"
        self.source.write_text('schedule Generic language "spl/0.1-draft" core "spl-core/0.1-draft" '
            'schema "spl-data/0.1-draft" { input cash: Money<USD>; input rate: Ratio; '
            'define earned = cash * rate; emit "result" = earned; }', encoding="utf-8")
        (self.root / "policy.md").write_text("Explicit synthetic policy: exact cash times supplied rate. No rounding or payment.", encoding="utf-8")
        self.descriptor = {"schema_version": "spl-module-descriptor/1", "id": "test:generic", "revision": "1",
            "compatibility": {"surface": "spl/0.1-draft", "core": "spl-core/0.1-draft", "ir": "spl-ir/0.1",
                "package": "spl-module/1", "toolchain": "leanprover/lean4:v4.35.0", "codecs": ["spl-exact/1", "spl-instant/1"],
                "capabilities": ["spl.core/1"]},
            "source": {"locator": "calculation.spl", "sha256": file_digest(self.source)}, "imports": [],
            "interface": {"ports": [port("cash", "input", typ("Money", typ("USD")), {"minimum": "0"}),
                                    port("rate", "parameter", typ("Ratio"), {"minimum": "0", "maximum": "1", "methodology": False}),
                                    port("result", "result", typ("Money", typ("USD")))],
                          "schemas": [], "dictionaries": {}, "exports": []},
            "policy": {"id": "test:policy", "revision": "1", "readable": {"locator": "policy.md", "sha256": file_digest(self.root / "policy.md")},
                       "decision_ids": ["D1"], "evidence_class": "synthetic", "review_status": "proposed", "discriminating_cases": ["cash100-rate20"]},
            "constraints": [], "state": []}
        self.package = {"profile": "spl-module/1", "module_ref": {},
            "manifest": {"run_id": "first", "scenario_id": "synthetic", "mode": "final",
                         "period": {"start": "2026-01-01", "end": "2026-04-01"}, "cutoff": "2026-04-03T00:00:00Z",
                         "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
                         "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
            "scope": {"agreement_id": "new-agreement", "participant_ids": ["new-participant"],
                      "pool_id": "new-pool", "purpose": "synthetic-entitlement", "asset_ids": ["new-film"]},
            "inputs": {"cash": {"value": "100", "currency": "USD"}}, "parameters": {"rate": "0.2"}, "evidence": {},
            "state_cells": [], "decisions": [{"decision_id": "D1", "policy_id": "test:policy", "policy_revision": "1",
                                              "status": "proposed", "evidence_ref": "explicit-synthetic-assumption"}]}
        self.repin()

    def repin(self):
        self.descriptor["source"]["sha256"] = file_digest(self.source)
        write_json(self.root / "descriptor.json", self.descriptor)
        self.package["module_ref"] = {"id": self.descriptor["id"], "revision": self.descriptor["revision"],
                                      "locator": "descriptor.json", "sha256": file_digest(self.root / "descriptor.json")}

    def run_reference(self, package=None, artifact_dir=None):
        package = self.package if package is None else package
        return run_package(bind_package(package, self.root), self.root, backend="reference", artifact_dir=artifact_dir)

    def assert_blocked(self, result, code):
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        self.assertEqual(result["statements"], [])
        self.assertEqual(result["closing_state"], [])

    def test_generic_dispatch_terms_identity_and_original_source_policy_requirement(self):
        first = self.run_reference()
        self.assertEqual(first["diagnostics"], [])
        self.assertEqual(first["statements"], ["20"])
        self.package["parameters"]["rate"] = "0.4"
        second = self.run_reference()
        self.assertEqual(second["statements"], ["40"])
        self.assertNotEqual(first["terms_digest"], second["terms_digest"])
        self.assertEqual(first["method_digest"], second["method_digest"])
        self.package["decisions"] = []
        self.assert_blocked(self.run_reference(), "MODULE_POLICY_REQUIRED")

    def test_invocation_label_does_not_change_semantics_trace_or_candidate_state(self):
        self.add_state()
        first = self.run_reference()
        self.package["manifest"]["run_id"] = "another-invocation"
        second = self.run_reference()
        self.assertEqual(first["diagnostics"], [])
        self.assertEqual(second["diagnostics"], [])
        self.assertEqual(first["semantic_run_digest"], second["semantic_run_digest"])
        for field in ["results", "trace", "statements", "detail", "closing_state", "reconciliation", "policy_review"]:
            self.assertEqual(first[field], second[field], field)
        self.assertNotEqual(first["manifest"]["run_id"], second["manifest"]["run_id"])
        self.assertNotEqual(first["result_digest"], second["result_digest"])

    def test_semantic_identity_retains_method_terms_source_policy_and_evidence_dependencies(self):
        self.descriptor["interface"]["ports"][1]["domain"]["methodology"] = True
        self.repin()
        original = self.run_reference()
        self.package["parameters"]["rate"] = "0.4"
        terms = self.run_reference()
        self.assertNotEqual(original["semantic_run_digest"], terms["semantic_run_digest"])
        self.assertNotEqual(original["method_digest"], terms["method_digest"])
        self.package["parameters"]["rate"] = "0.2"
        self.source.write_text(self.source.read_text() + "\n", encoding="utf-8")
        self.repin()
        source = self.run_reference()
        self.assertEqual(original["results"], source["results"])
        self.assertNotEqual(original["semantic_run_digest"], source["semantic_run_digest"])
        policy_path = self.root / "policy.md"
        policy_path.write_text(policy_path.read_text() + "\n", encoding="utf-8")
        self.descriptor["policy"]["readable"]["sha256"] = file_digest(policy_path)
        self.repin()
        policy = self.run_reference()
        self.assertNotEqual(source["semantic_run_digest"], policy["semantic_run_digest"])
        self.package["decisions"][0]["evidence_ref"] = "another-exact-evidence-reference"
        evidence = self.run_reference()
        self.assertEqual(policy["results"], evidence["results"])
        self.assertNotEqual(policy["semantic_run_digest"], evidence["semantic_run_digest"])

    def test_domain_undeclared_parameters_unsupported_capability_and_schema(self):
        for mutate, code in [
            (lambda: self.package["parameters"].update(rate="1.0001"), "MODULE_PARAMETER_DOMAIN"),
            (lambda: self.package["parameters"].update(secret="1"), "MODULE_BINDING_PORTS"),
            (lambda: self.package["inputs"]["cash"].update(currency="EUR"), "CURRENCY_MISMATCH")]:
            saved = deepcopy(self.package)
            mutate()
            self.assert_blocked(self.run_reference(), code)
            self.package = saved
        self.descriptor["compatibility"]["capabilities"].append("host.execute")
        self.repin()
        with self.assertRaises(DataError) as error:
            resolve_module(self.package["module_ref"], self.root)
        self.assertEqual(error.exception.code, "MODULE_UNSUPPORTED_CAPABILITY")

    def test_stale_descriptor_source_policy_and_manifest_block(self):
        bound = bind_module_package(self.package, self.root)
        for filename in ["descriptor.json", "calculation.spl", "policy.md"]:
            path = self.root / filename
            previous = path.read_bytes()
            path.write_bytes(previous + b"\n")
            result = run_module_package(bound, self.root, backend="reference")
            self.assert_blocked(result, "MODULE_DEPENDENCY_DIGEST")
            path.write_bytes(previous)
        bound["manifest"]["compiler_build"] = "stale"
        self.assert_blocked(run_module_package(bound, self.root, backend="reference"), "MANIFEST_DIGEST_MISMATCH")

    def test_registered_output_ports_and_atomic_rerun_publication(self):
        output = self.root / "published"
        self.assertEqual(self.run_reference(artifact_dir=output)["statements"], ["20"])
        self.descriptor["interface"]["ports"][-1]["name"] = "missing-result"
        self.repin()
        self.assert_blocked(run_module_package(self.package, self.root, backend="reference", artifact_dir=output), "MODULE_SCHEMA_PATTERN")
        self.descriptor["interface"]["ports"][-1]["name"] = "missing_result"
        self.repin()
        self.assert_blocked(self.run_reference(artifact_dir=output), "MODULE_OUTPUT_PORTS")
        self.assertEqual(read_json(output / "statement.json"), [])
        self.assertEqual(read_json(output / "closing-state.json"), [])
        self.assertEqual(read_json(output / "result.json")["status"], "blocked")

    def test_scope_constraints_keys_references_conservation(self):
        self.descriptor["constraints"] = [{"kind": "equals", "path": "scope.agreement_id", "fields": [], "target": "", "value": "new-agreement"}]
        self.repin()
        self.assertEqual(self.run_reference()["status"], "calculated")
        self.package["scope"]["agreement_id"] = "unauthorized-pool"
        self.assert_blocked(self.run_reference(), "MODULE_SCOPE_MISMATCH")

    def add_state(self):
        text = self.source.read_text()
        text = text.replace('define earned', 'opening balance: Money<USD> from "synthetic-balance"; define earned')
        text = text.replace('emit "result"', 'closing balance = balance + earned; emit "result"')
        self.source.write_text(text, encoding="utf-8")
        self.descriptor["interface"]["ports"].append(port("balance", "opening", typ("Money", typ("USD"))))
        self.descriptor["state"] = [{"opening": "balance", "closing": "balance", "purpose": "synthetic-entitlement", "unit": "USD",
             "key_fields": ["agreement_id", "participant_id", "pool_id", "purpose"], "movement_kinds": ["net_change"], "history_required": True}]
        key = {"agreement_id": "new-agreement", "participant_id": "new-participant", "pool_id": "new-pool", "purpose": "synthetic-entitlement"}
        self.package["state_cells"] = [{"state_key": canonical(key), "opening_port": "balance", "purpose": "synthetic-entitlement",
            "unit": "USD", "scope": {k: v for k, v in key.items() if k != "purpose"}, "boundary": "2026-01-01", "quantity": "5",
            "provenance_ref": "explicit-opening", "scenario_id": "synthetic", "prior_result_ref": "result@sha256:" + "1" * 64}]
        self.repin()

    def test_state_scope_purpose_lineage_and_single_writer(self):
        self.add_state()
        good = self.run_reference()
        self.assertEqual(good["diagnostics"], [])
        self.assertEqual(good["closing_state"][0]["quantity"], "25")
        self.assertEqual(good["closing_state"][0]["boundary"], "2026-04-01")
        for field, value, code in [("purpose", "reserve", "MODULE_STATE_PURPOSE"), ("scenario_id", "another", "MODULE_STATE_SCOPE"),
                                  ("boundary", "2025-01-01", "MODULE_STATE_BOUNDARY"), ("state_key", "wrong", "MODULE_STATE_KEY")]:
            saved = deepcopy(self.package)
            self.package["state_cells"][0][field] = value
            self.assert_blocked(self.run_reference(), code)
            self.package = saved
        self.package["state_cells"][0].pop("prior_result_ref")
        self.assert_blocked(self.run_reference(), "MODULE_STATE_LINEAGE")
        self.package["state_cells"].append(deepcopy(self.package["state_cells"][0]))
        self.assert_blocked(self.run_reference(), "MODULE_DUPLICATE_STATE_WRITER")

    def test_preview_has_no_consumable_state(self):
        self.add_state()
        self.package["manifest"]["mode"] = "preview"
        result = self.run_reference()
        self.assertEqual(result["status"], "provisional")
        self.assertEqual(result["closing_state"], [])

    def test_structured_state_roundtrips_nested_money_and_successor_lineage(self):
        row_type = {"name": "Record", "args": [], "fields": [["id", typ("Id", typ("Payment"))],
                    ["amount", typ("Money", typ("USD"))], ["disputed", typ("Bool")]]}
        text = self.source.read_text().replace('define earned',
            'opening registry: List<{id: Id<Payment>, amount: Money<USD>, disputed: Bool}> from "registry"; define earned')
        self.source.write_text(text.replace('emit "result"', 'closing registry = registry; emit "result"'), encoding="utf-8")
        self.descriptor["interface"]["ports"].append(port("registry", "opening", typ("List", row_type)))
        self.descriptor["state"] = [{"opening": "registry", "closing": "registry", "purpose": "payment-registry", "unit": "structured",
             "key_fields": ["agreement_id", "participant_id", "pool_id", "purpose"], "movement_kinds": ["transition"], "history_required": True}]
        key = {"agreement_id": "new-agreement", "participant_id": "new-participant", "pool_id": "new-pool", "purpose": "payment-registry"}
        payload = [{"id": "payment-1", "amount": {"value": "80.00000000000000000001", "currency": "USD"}, "disputed": True}]
        self.package["state_cells"] = [{"state_key": canonical(key), "opening_port": "registry", "purpose": "payment-registry",
            "unit": "structured", "scope": {k: v for k, v in key.items() if k != "purpose"}, "boundary": "2026-01-01", "quantity": payload,
            "provenance_ref": "original-opening", "scenario_id": "synthetic", "prior_result_ref": "result@sha256:" + "1" * 64}]
        self.repin()
        result = self.run_reference()
        self.assertEqual(result["diagnostics"], [])
        closing = result["closing_state"][0]
        self.assertEqual(closing["quantity"], payload)
        self.assertEqual(closing["movement"], {"kind": "transition", "opening": payload, "closing": payload})
        self.assertEqual(closing["prior_result_ref"], "result@sha256:" + result["semantic_run_digest"])
        next_cell = {key: value for key, value in closing.items() if key != "movement"}
        self.package["state_cells"] = [next_cell]
        self.package["manifest"]["period"] = {"start": "2026-04-01", "end": "2026-07-01"}
        successor = self.run_reference()
        self.assertEqual(successor["diagnostics"], [])
        self.assertEqual(successor["closing_state"][0]["quantity"], payload)

    def test_declarative_uniqueness_reference_conservation_and_postcondition(self):
        row_type = {"name": "Record", "args": [], "fields": [["key", typ("Id", typ("Item"))], ["amount", typ("Money", typ("USD"))]]}
        self.source.write_text(self.source.read_text().replace('define earned',
            'input rows: List<{key: Id<Item>, amount: Money<USD>}>; input allowed: List<Id<Item>>; input total: Money<USD>; define earned'), encoding="utf-8")
        self.descriptor["interface"]["ports"].extend([port("rows", "input", typ("List", row_type)),
            port("allowed", "input", typ("List", typ("Id", typ("Item")))), port("total", "input", typ("Money", typ("USD")))])
        self.package["inputs"].update(rows=[{"key": "a", "amount": {"value": "40", "currency": "USD"}},
                                              {"key": "b", "amount": {"value": "60", "currency": "USD"}}],
                                       allowed=["a", "b"], total={"value": "100", "currency": "USD"})
        self.descriptor["constraints"] = [
            {"kind": "unique", "path": "inputs.rows", "fields": ["key"], "target": "", "value": ""},
            {"kind": "references", "path": "inputs.rows", "fields": ["key"], "target": "inputs.allowed", "value": ""},
            {"kind": "conservation", "path": "inputs.rows", "fields": ["amount"], "target": "inputs.total", "value": ""},
            {"kind": "equals", "path": "outputs.result", "fields": [], "target": "", "value": "20"}]
        self.repin()
        self.assertEqual(self.run_reference()["diagnostics"], [])
        for mutate, code in [(lambda p: p["inputs"]["rows"][1].update(key="a"), "MODULE_DUPLICATE_KEY"),
                             (lambda p: p["inputs"]["rows"][1].update(key="outside"), "MODULE_REFERENCE_SCOPE"),
                             (lambda p: p["inputs"]["total"].update(value="101"), "MODULE_CONSERVATION"),
                             (lambda p: p["parameters"].update(rate="0.3"), "MODULE_SCOPE_MISMATCH")]:
            package = deepcopy(self.package)
            mutate(package)
            result = self.run_reference(package)
            self.assert_blocked(result, code)
            if code == "MODULE_REFERENCE_SCOPE":
                self.assertEqual(result["diagnostics"][0]["pointer"], "/inputs/rows/1/key")

    def test_evidence_cutoff_authority_and_missing_required_attestation(self):
        row_type = {"name": "Record", "args": [], "fields": [["event_id", typ("Id", typ("Event"))],
            ["observed_at", typ("Instant")], ["approval_ref", typ("Id", typ("Decision"))],
            ["evidence_ref", typ("Text")], ["kind", typ("Text")]]}
        self.source.write_text(self.source.read_text().replace('define earned',
            'input attestations: List<{event_id: Id<Event>, observed_at: Instant, approval_ref: Id<Decision>, evidence_ref: Text, kind: Text}>; define earned'), encoding="utf-8")
        self.descriptor["interface"]["ports"].append(port("attestations", "evidence", typ("List", row_type)))
        self.descriptor["compatibility"]["capabilities"].append("spl.instant/1")
        self.descriptor["constraints"] = [{"kind": "evidence", "path": "evidence.attestations", "fields": [], "target": "", "value": "complete-population"}]
        self.package["manifest"]["cutoff"] = "2026-04-03T00:00:00.0000002Z"
        self.package["evidence"] = {"attestations": [{"event_id": "att-1", "observed_at": "2026-04-03T00:00:00.0000001Z",
            "approval_ref": "D1", "evidence_ref": "supplied-completeness", "kind": "complete-population"}]}
        self.repin()
        self.assertEqual(self.run_reference()["diagnostics"], [])
        for mutate, code in [(lambda p: p["evidence"]["attestations"][0].update(observed_at=p["manifest"]["cutoff"]), "EVIDENCE_AFTER_CUTOFF"),
                             (lambda p: p["evidence"]["attestations"][0].update(approval_ref="not-D1"), "MODULE_EVIDENCE_AUTHORITY"),
                             (lambda p: p["evidence"].update(attestations=[]), "MODULE_EVIDENCE_REQUIRED")]:
            package = deepcopy(self.package)
            mutate(package)
            self.assert_blocked(self.run_reference(package), code)

    def test_dependency_closure_export_collisions_cycles_and_path_bounds(self):
        child = deepcopy(self.descriptor)
        child["id"] = "test:child"
        child["compatibility"]["capabilities"].append("spl.modules/1")
        self.descriptor["compatibility"]["capabilities"].append("spl.modules/1")
        child["interface"]["ports"] = [port("cash", "input", typ("Money", typ("USD"))), port("rate", "input", typ("Ratio"))]
        child["interface"]["exports"] = [{"name": "calculate", "definition": "earned",
             "parameters": [{"name": "cash", "type": typ("Money", typ("USD"))}, {"name": "rate", "type": typ("Ratio")}],
             "result": typ("Money", typ("USD"))}]
        write_json(self.root / "child.json", child)
        child_ref = {"id": "test:child", "revision": "1", "locator": "child.json", "sha256": file_digest(self.root / "child.json")}
        imported = {"module_ref": child_ref, "alias": "fees", "symbols": [{"export": "calculate", "local": "calculate_fee"}]}
        self.descriptor["imports"] = [imported]
        self.repin()
        resolved = resolve_module(self.package["module_ref"], self.root)
        self.assertEqual([ref["id"] for ref in resolved.references], ["test:child", "test:generic"])
        self.descriptor["imports"].append({**imported, "alias": "other"})
        self.repin()
        with self.assertRaises(DataError) as collision:
            resolve_module(self.package["module_ref"], self.root)
        self.assertEqual(collision.exception.code, "MODULE_IMPORT_COLLISION")
        self.descriptor["imports"] = [{"module_ref": {**self.package["module_ref"], "sha256": "0" * 64}, "alias": "self", "symbols": []}]
        self.repin()
        with self.assertRaises(DataError) as cycle:
            resolve_module(self.package["module_ref"], self.root)
        self.assertEqual(cycle.exception.code, "MODULE_IMPORT_CYCLE")
        self.descriptor["imports"] = []
        self.descriptor["source"]["locator"] = "../outside.spl"
        self.repin()
        with self.assertRaises(DataError) as outside:
            resolve_module(self.package["module_ref"], self.root)
        self.assertEqual(outside.exception.code, "MODULE_DEPENDENCY_MISSING")

    def add_function_dependency(self):
        child_source = self.root / "fee.spl"
        child_source.write_text('schedule Fee language "spl/0.1-draft" core "spl-core/0.1-draft" '
            'schema "spl-data/0.1-draft" { input amount: Money<USD>; input rate: Ratio; '
            'require rate >= 0.0 else "FEE_NEGATIVE_RATE"; define fee_value = amount * rate; }', encoding="utf-8")
        child = deepcopy(self.descriptor)
        child["id"] = "test:fee"
        child["compatibility"]["capabilities"].append("spl.modules/1")
        self.descriptor["compatibility"]["capabilities"].append("spl.modules/1")
        child["source"] = {"locator": "fee.spl", "sha256": file_digest(child_source)}
        child["interface"]["ports"] = [port("amount", "input", typ("Money", typ("USD"))), port("rate", "input", typ("Ratio"))]
        child["interface"]["exports"] = [{"name": "fee", "definition": "fee_value",
            "parameters": [{"name": "amount", "type": typ("Money", typ("USD"))}, {"name": "rate", "type": typ("Ratio")}],
            "result": typ("Money", typ("USD"))}]
        child["policy"].update(id="test:fee-policy", decision_ids=["D2"])
        write_json(self.root / "fee.json", child)
        child_ref = {"id": "test:fee", "revision": "1", "locator": "fee.json", "sha256": file_digest(self.root / "fee.json")}
        self.descriptor["imports"] = [{"module_ref": child_ref, "alias": "fee_tools", "symbols": [{"export": "fee", "local": "calculate_fee"}]}]
        self.package["decisions"].append({"decision_id": "D2", "policy_id": "test:fee-policy", "policy_revision": "1",
                                            "status": "proposed", "evidence_ref": "explicit-fee-method"})
        text = self.source.read_text().replace('define earned = cash * rate;', 'define amount = USD 999; define earned = calculate_fee(cash, rate);')
        self.source.write_text(text, encoding="utf-8")
        self.repin()
        return child

    def test_function_import_uses_pinned_body_without_capturing_caller_names(self):
        self.add_function_dependency()
        result = self.run_reference()
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["results"]["result"], "20")
        self.assertEqual([ref["id"] for ref in result["module_closure"]], ["test:fee", "test:generic"])
        review = result["policy_review"]
        self.assertEqual(review["actual_parameters"], {"rate": "0.2"})
        parameter = review["parameters"][0]
        self.assertEqual((parameter["name"], parameter["value"], parameter["methodology"]), ("rate", "0.2", False))
        self.assertIn("input rate: Ratio", parameter["declaration_location"]["text"])
        self.assertEqual([entry["module_ref"]["id"] for entry in review["modules"]], ["test:fee", "test:generic"])
        imported = review["modules"][0]
        exported = imported["exports"][0]
        self.assertEqual(exported["function"], "test:fee@1:fee")
        self.assertIn("define fee_value = amount * rate", exported["definition_location"]["text"])
        self.assertIn("input amount: Money<USD>", exported["parameter_locations"]["amount"]["text"])
        mapped = review["function_sources"]["test:fee@1:fee"]
        self.assertEqual(mapped["source"], imported["source"])
        self.assertEqual(mapped["span"], exported["definition_location"]["span"])
        self.assertEqual(imported["policy"]["readable"]["sha256"], file_digest(self.root / "policy.md"))
        self.package["decisions"].pop()
        self.assert_blocked(self.run_reference(), "MODULE_POLICY_REQUIRED")

    def test_imported_domains_are_not_silently_ignored(self):
        child = self.add_function_dependency()
        child["interface"]["ports"][1]["domain"] = {"minimum": "0"}
        write_json(self.root / "fee.json", child)
        self.descriptor["imports"][0]["module_ref"]["sha256"] = file_digest(self.root / "fee.json")
        self.repin()
        with self.assertRaises(DataError) as error:
            resolve_module(self.package["module_ref"], self.root)
        self.assertEqual(error.exception.code, "MODULE_FUNCTION_CONSTRAINT_UNSUPPORTED")

    def test_registered_function_native_link_and_strict_argument_failure(self):
        self.add_function_dependency()
        success = run_module_package(bind_module_package(self.package, self.root), self.root)
        self.assertEqual(success["diagnostics"], [])
        self.assertEqual(success["results"]["result"], "20")
        self.assertTrue(success["verification"]["reference_agrees"])
        self.source.write_text(self.source.read_text().replace('calculate_fee(cash, rate)', 'calculate_fee(cash / 0.0, rate)'), encoding="utf-8")
        self.repin()
        failure = run_module_package(bind_module_package(self.package, self.root), self.root)
        self.assert_blocked(failure, "DIVISION_BY_ZERO")
        self.assertEqual(failure["results"], {})

    def test_required_source_capabilities_cannot_be_underdeclared(self):
        self.source.write_text(self.source.read_text().replace('define earned = cash * rate;',
            'define earned = choose priority { rule "selected" priority 1 when true => cash * rate; };'), encoding="utf-8")
        self.repin()
        failure = run_module_package(self.package, self.root, backend="reference")
        self.assert_blocked(failure, "MODULE_CAPABILITY_UNDECLARED")

    def test_generic_array_guard_never_calculates_a_truncated_prefix(self):
        package = deepcopy(self.package)
        package["inputs"]["oversized"] = ["0"] * 100001
        result = run_module_package(package, self.root, backend="reference")
        self.assert_blocked(result, "RESOURCE_LIMIT")
        self.assertEqual(result["results"], {})

    def test_required_audit_resource_failure_preserves_prefix_without_false_differential(self):
        from spl_compiler.fixtures import sv_package
        exhausted = {"status": "blocked", "emissions": {}, "closing": {},
                     "diagnostics": [{"code": "RESOURCE_LIMIT", "message": "Native trace observation quota exhausted"}],
                     "trace": [{"node_id": "prefix"}], "trace_origin": "native_ir_interpreter", "trace_format": "spl-trace-dag/0.1"}
        bound = bind_module_package(self.package, self.root)
        with patch("spl_compiler.lean_tools.export_ir"), patch("spl_compiler.lean_tools.interpret_schedule", return_value=exhausted), \
                patch("spl_compiler.lean_tools.compile_schedule") as compile_target:
            result = run_module_package(bound, self.root)
        self.assert_blocked(result, "RESOURCE_LIMIT")
        self.assertEqual(result["trace"], [{"node_id": "prefix"}])
        self.assertFalse(result["verification"]["required_audit_completed"])
        compile_target.assert_not_called()
        schedule = ROOT / "cases/sv/sv01.spl"
        bound_legacy = bind_package(sv_package(), schedule)
        with patch("spl_compiler.run.export_ir"), patch("spl_compiler.run.interpret_schedule", return_value=exhausted), \
                patch("spl_compiler.run.compile_schedule") as compile_legacy:
            legacy = run_package(bound_legacy, schedule)
        self.assert_blocked(legacy, "RESOURCE_LIMIT")
        self.assertEqual(legacy["trace"], [{"node_id": "prefix"}])
        compile_legacy.assert_not_called()


class RegisteredPriorityTests(unittest.TestCase):
    def package(self):
        return read_json(ROOT / "cases/modules/priority-rates/package.json")

    def run_reference(self, package):
        return run_package(bind_package(package, ROOT), ROOT, backend="reference")

    def test_independent_two_participant_rate_and_zero_witnesses(self):
        for territory, expected in [("US", ["10", "10"]), ("CA", ["20", "20"]), ("FR", ["0", "0"])]:
            with self.subTest(territory=territory):
                package = self.package()
                package["inputs"]["territory"] = territory
                result = self.run_reference(package)
                self.assertEqual(result["diagnostics"], [])
                self.assertEqual([row["earned"] for row in result["statements"]], expected)
                self.assertEqual([row["participant_id"] for row in result["statements"]], ["oak-participant", "pine-participant"])

    def test_tie_no_rule_effective_end_and_unauthorized_scope_are_atomic(self):
        for mutate, code in [(lambda p: p["parameters"].update(competing_canada=True), "AMBIGUOUS_RULE"),
                             (lambda p: p["inputs"].update(territory="ZZ"), "NO_APPLICABLE_RULE"),
                             (lambda p: p["inputs"].update(source_date="2026-07-01"), "NO_APPLICABLE_RULE"),
                             (lambda p: p["inputs"].update(participant_b="outside-participant"), "MODULE_REFERENCE_SCOPE")]:
            package = self.package()
            mutate(package)
            result = self.run_reference(package)
            self.assertEqual(result["status"], "blocked", result)
            self.assertEqual(result["diagnostics"][0]["code"], code)
            self.assertEqual(result["statements"], [])
            self.assertEqual(result["closing_state"], [])

    def test_registered_priority_native_interpreter_generated_and_reference(self):
        package = self.package()
        result = run_package(bind_package(package, ROOT), ROOT)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual([row["earned"] for row in result["statements"]], ["20", "20"])
        self.assertTrue(result["verification"]["reference_agrees"])


if __name__ == "__main__":
    unittest.main()
