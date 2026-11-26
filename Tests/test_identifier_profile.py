"""LD03-ID-1: declared typed IDs only; Text business identities stay Text."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from cases.r1.build_modules import _type
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import DataError, canonical, file_digest, loads, write_json
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
from spl_compiler.model import SPLException
from spl_compiler.modules import bind_module_package, run_module_package
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target


HEADER = 'schedule IdentifierProfile language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'
SOURCE = HEADER + '''
 input identity: Id<Item>;
 input other: Id<Item>;
 input asset: Id<Asset>;
 input party: Id<Party>;
 input envelope: {optional: Option<Id<Item>>, rows: List<{id: Text, typed: Id<Item>}>, mapping: Map<Tuple<Id<Item>,Int>,Id<Item>>, pair: Tuple<Id<Item>,Id<Party>>, label: Text};
 opening ledger: List<{id: Id<Item>, event_id: Text}> from "identity-registry";
 closing ledger = ledger;
 emit "result" = {identity: identity, other: other, same_namespace_equal: identity == other, asset: asset, party: party, envelope: envelope};
}'''


def bindings():
    return {"identity": "A", "other": "a", "asset": "x", "party": "x",
            "envelope": {"optional": {"some": "\x00"}, "rows": [{"id": "application:q1-é", "typed": chr(code)} for code in range(128)],
                         "mapping": [{"key": ["\x7f", "0"], "value": " "}], "pair": ["x", "x"], "label": "Café 雪"}}, {
            "ledger": [{"id": "\t\r\n", "event_id": "application:q1-é"}]}


def replace(inputs, openings, location, value):
    target = openings if location[0] == "opening" else inputs
    for key in location[1:-1]:
        target = target[key]
    target[location[-1]] = value


LOCATIONS = [("input", "identity"), ("input", "envelope", "optional", "some"),
             ("input", "envelope", "rows", 0, "typed"), ("input", "envelope", "mapping", 0, "key", 0),
             ("input", "envelope", "mapping", 0, "value"), ("input", "envelope", "pair", 1),
             ("opening", "ledger", 0, "id")]


class IdentifierProfileTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".lake/identifier-profile-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.checked = check_schedule(parse(SOURCE))

    def package(self, inputs=None, openings=None, *, output_id=False):
        inputs, openings = deepcopy(bindings() if inputs is None else (inputs, openings))
        source = SOURCE if not output_id else HEADER + 'input value: Text; emit "result" = value; }'
        checked = self.checked if not output_id else check_schedule(parse(source))
        path = self.work / "profile.spl"
        path.write_text(source, encoding="utf-8")
        policy = self.work / "policy.md"
        policy.write_text("Synthetic boundary echo only. Declared typed IDs retain the existing nonempty 7-bit profile; no payment or normalization.", encoding="utf-8")
        ports = []
        for declaration in checked.schedule["declarations"]:
            kind = declaration["kind"]
            if kind in ("input", "opening"):
                ports.append({"name": declaration["name"], "role": kind, "type": declaration["type"], "domain": {}, "dimensions": []})
            elif kind == "emit":
                ports.append({"name": declaration["name"], "role": "result", "type": {"name": "Id", "args": [{"name": "Item", "args": []}]} if output_id else _type(declaration["expr"]["_type"]), "domain": {}, "dimensions": []})
        state = [] if output_id else [{"opening": "ledger", "closing": "ledger", "purpose": "identity-registry", "unit": "structured",
                 "key_fields": ["agreement_id", "participant_id", "pool_id", "purpose"], "movement_kinds": ["transition"], "history_required": False}]
        descriptor = {"schema_version": "spl-module-descriptor/1", "id": "synthetic:identifier-profile", "revision": "1",
            "compatibility": {"surface": "spl/0.1-draft", "core": "spl-core/0.1-draft", "ir": "spl-ir/0.1", "package": "spl-module/1",
                              "toolchain": "leanprover/lean4:v4.35.0", "codecs": ["spl-exact/1", "spl-instant/1"], "capabilities": ["spl.core/1", "spl.tuple-map/1"]},
            "source": {"locator": "profile.spl", "sha256": file_digest(path)}, "imports": [],
            "interface": {"ports": ports, "schemas": [], "dictionaries": {}, "exports": []},
            "policy": {"id": "SYNTHETIC-IDENTIFIER-PROFILE", "revision": "1", "readable": {"locator": "policy.md", "sha256": file_digest(policy)},
                       "decision_ids": ["ID_PROFILE"], "evidence_class": "synthetic", "review_status": "proposed", "discriminating_cases": ["ASCII128", "Text-é", "nested-ID"]},
            "constraints": [], "state": state}
        descriptor_path = self.work / "descriptor.json"
        write_json(descriptor_path, descriptor)
        scope = {"agreement_id": "agreement", "participant_id": "participant", "pool_id": "pool"}
        cells = [] if output_id else [{"state_key": canonical({**scope, "purpose": "identity-registry"}), "opening_port": "ledger",
                  "purpose": "identity-registry", "unit": "structured", "scope": scope, "boundary": "2026-01-01", "quantity": openings["ledger"],
                  "provenance_ref": "synthetic-original-opening", "scenario_id": "identifier-profile"}]
        result = {"profile": "spl-module/1", "module_ref": {"id": descriptor["id"], "revision": "1", "locator": "descriptor.json", "sha256": file_digest(descriptor_path)},
            "manifest": {"run_id": "identifier-run", "scenario_id": "identifier-profile", "mode": "final", "period": {"start": "2026-01-01", "end": "2026-04-01"},
                         "cutoff": "2026-04-03T00:00:00Z", "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
                         "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
            "scope": {"agreement_id": "agreement", "participant_ids": ["participant"], "pool_id": "pool", "asset_ids": ["x"], "purpose": "identity-registry"},
            "inputs": inputs, "parameters": {}, "evidence": {}, "state_cells": cells,
            "decisions": [{"decision_id": "ID_PROFILE", "policy_id": "SYNTHETIC-IDENTIFIER-PROFILE", "policy_revision": "1", "status": "proposed", "evidence_ref": "explicit-boundary-fixture"}]}
        return bind_module_package(result, self.work)

    def run_reference(self, package):
        return run_module_package(package, self.work, backend="reference")

    def blocked(self, result, code, *, preflight=True):
        self.assertEqual([row["code"] for row in result["diagnostics"]], [code], result)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["results"], {})
        self.assertEqual(result["closing_state"], [])
        if preflight:
            self.assertEqual(result["trace"], [])
        else:
            self.assertTrue(result["trace"])

    def test_all_128_nonempty_single_character_ids_are_valid_and_unmodified(self):
        inputs, openings = bindings()
        result = evaluate(self.checked, inputs, openings).to_dict()
        self.assertEqual(result["status"], "calculated")
        self.assertEqual([row["typed"] for row in result["emissions"]["result"]["envelope"]["rows"]], [chr(code) for code in range(128)])
        self.assertEqual(result["closing"]["ledger"], openings["ledger"])

    def test_exact_case_whitespace_and_embedded_nul_are_not_normalized(self):
        inputs, openings = bindings()
        result = evaluate(self.checked, inputs, openings).to_dict()
        self.assertFalse(result["emissions"]["result"]["same_namespace_equal"])
        for value in (" A ", "A\x00B", "\t", "\x7f"):
            inputs["identity"] = value
            self.assertEqual(evaluate(self.checked, inputs, openings).to_dict()["emissions"]["result"]["identity"], value)

    def test_empty_nfc_and_decomposed_nonascii_reject_at_every_typed_location(self):
        for location in LOCATIONS:
            for value, expected in (("", "INVALID_ID"), ("é", "UNSUPPORTED_IDENTIFIER_PROFILE"), ("e\u0301", "INVALID_ID")):
                inputs, openings = bindings()
                replace(inputs, openings, location, value)
                with self.subTest(location=location, value=value):
                    result = evaluate(self.checked, inputs, openings)
                    self.assertEqual([row["code"] for row in result.diagnostics], [expected])
                    self.assertEqual(result.emissions, {})
                    self.assertEqual(result.closing, {})

    def test_namespace_separation_is_static_not_a_runtime_string_tag(self):
        for expression in ("asset == party", "lookup(make_map([asset], row => row, row => 1), party)"):
            with self.subTest(expression=expression), self.assertRaises(SPLException) as raised:
                check_schedule(parse(HEADER + "input asset:Id<Asset>; input party:Id<Party>; emit \"result\" = " + expression + "; }"))
            self.assertEqual(raised.exception.code, "TYPE_MISMATCH")

    def test_canonical_preflight_nested_profile_and_scope_have_actual_diagnostics(self):
        for location in LOCATIONS:
            for value, expected in (("", "INVALID_ID"), ("é", "UNSUPPORTED_IDENTIFIER_PROFILE"), ("e\u0301", "NON_NFC_TEXT")):
                inputs, openings = bindings()
                replace(inputs, openings, location, value)
                with self.subTest(location=location, value=value):
                    self.blocked(self.run_reference(self.package(inputs, openings)), expected)
        inputs, openings = bindings()
        inputs["asset"] = "outside"
        self.blocked(self.run_reference(self.package(inputs, openings)), "MODULE_REFERENCE_SCOPE")

    def test_nfc_text_named_id_and_text_tuple_keep_unicode_business_identity(self):
        inputs, openings = bindings()
        result = self.run_reference(self.package(inputs, openings))
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["results"]["result"]["envelope"]["rows"][0]["id"], "application:q1-é")
        self.assertEqual(result["results"]["result"]["envelope"]["label"], "Café 雪")
        tuple_source = HEADER + 'input business_id:Text; emit "result"=tuple("earned",business_id); }'
        checked = check_schedule(parse(tuple_source))
        self.assertEqual(evaluate(checked, {"business_id": "application:q1-é"}, {}).to_dict()["emissions"]["result"], ["earned", "application:q1-é"])

    def test_canonical_outer_text_references_are_not_a_global_ascii_profile(self):
        package = self.package()
        package["scope"]["agreement_id"] = "contraté"
        cell = package["state_cells"][0]
        cell["scope"]["agreement_id"] = "contraté"
        cell["state_key"] = canonical({**cell["scope"], "purpose": cell["purpose"]})
        result = self.run_reference(package)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["closing_state"][0]["scope"]["agreement_id"], "contraté")

    def test_canonical_scoped_ids_keep_controls_case_and_whitespace_exact(self):
        package = self.package()
        package["inputs"]["asset"] = "\x00"
        package["scope"]["asset_ids"] = ["\x00"]
        result = self.run_reference(package)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["results"]["result"]["asset"], "\x00")
        for supplied, scoped in (("A", "a"), (" x ", "x")):
            package = self.package()
            package["inputs"]["asset"] = supplied
            package["scope"]["asset_ids"] = [scoped]
            self.blocked(self.run_reference(package), "MODULE_REFERENCE_SCOPE")

    def test_actual_serialized_state_and_returned_nested_ids_preserve_profile(self):
        first = self.run_reference(self.package())
        self.assertEqual(first["diagnostics"], [])
        cell = json.loads(json.dumps(first["closing_state"][0], ensure_ascii=False))
        self.assertEqual(cell["quantity"][0]["event_id"], "application:q1-é")
        self.assertEqual(cell["quantity"][0]["id"], "\t\r\n")
        package = self.package()
        package["state_cells"] = [{key: value for key, value in cell.items() if key != "movement"}]
        package["manifest"]["period"] = {"start": "2026-04-01", "end": "2026-07-01"}
        second = self.run_reference(package)
        self.assertEqual(second["diagnostics"], [])
        self.assertEqual(second["closing_state"][0]["quantity"], cell["quantity"])

    def test_registered_output_contract_checks_ids_after_text_source_executes(self):
        for value, expected in (("é", "UNSUPPORTED_IDENTIFIER_PROFILE"), ("", "INVALID_ID")):
            package = self.package({"value": value}, {}, output_id=True)
            # Source returns Text; this deliberately distinct declared output
            # contract is enforced at finalization, not by source Id coercion.
            self.blocked(self.run_reference(package), expected, preflight=False)

    def test_decomposed_external_identity_requires_raw_provenance_and_explicit_mapping(self):
        raw = "e\u0301".encode("utf-8")
        self.assertNotEqual(raw, "é".encode("utf-8"))
        self.assertNotEqual(hashlib.sha256(raw).hexdigest(), hashlib.sha256("é".encode("utf-8")).hexdigest())
        with self.assertRaises(DataError) as raised:
            loads(json.dumps({"external_id": "e\u0301"}))
        self.assertEqual(raised.exception.code, "NON_NFC_TEXT")
        self.assertEqual(raw, b"e\xcc\x81")


class NativeIdentifierProfileTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / ".lake/identifier-profile-native-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def test_native_ir_emitted_and_python_emitter_preserve_ascii_and_nfc_text(self):
        source = self.work / "profile.spl"
        source.write_text(SOURCE, encoding="utf-8")
        checked = check_schedule(parse(SOURCE))
        inputs, openings = bindings()
        reference = normalize_target(evaluate(checked, inputs, openings).to_dict())
        binding = self.work / "bindings.json"
        write_json(binding, {"inputs": inputs, "openings": openings})
        target = compile_schedule(source, self.work / "Settlement.lean")
        interpreted = normalize_target(interpret_schedule(source, binding))
        emitted = normalize_target(loads(lean(["--run", target, binding])))
        mirror = self.work / "PythonEmitter.lean"
        mirror.write_text(emit_module(checked, {name: decode_value(value, checked.types[name]) for name, value in inputs.items()},
                                     {name: decode_value(value, checked.types[name]) for name, value in openings.items()}), encoding="utf-8")
        mirrored = normalize_target(loads(lean(["--run", mirror])))
        for actual in (interpreted, emitted, mirrored):
            self.assertEqual(actual["diagnostics"], [])
            for field in ("status", "emissions", "closing"):
                self.assertEqual(canonical(actual[field]), canonical(reference[field]))

    def test_native_binding_rejections_have_honest_precedence_differences(self):
        source = self.work / "profile.spl"
        source.write_text(SOURCE, encoding="utf-8")
        target = compile_schedule(source, self.work / "Settlement.lean")
        for index, (location, value, native_code) in enumerate([
                (LOCATIONS[0], "", "EMPTY_IDENTIFIER"), (LOCATIONS[0], "é", "UNSUPPORTED_IDENTIFIER_PROFILE"),
                (LOCATIONS[1], "e\u0301", "UNSUPPORTED_IDENTIFIER_PROFILE"), (LOCATIONS[2], "é", "UNSUPPORTED_IDENTIFIER_PROFILE"),
                (LOCATIONS[3], "", "EMPTY_IDENTIFIER"), (LOCATIONS[4], "é", "UNSUPPORTED_IDENTIFIER_PROFILE"),
                (LOCATIONS[5], "é", "UNSUPPORTED_IDENTIFIER_PROFILE"), (LOCATIONS[6], "é", "UNSUPPORTED_IDENTIFIER_PROFILE")]):
            inputs, openings = bindings()
            replace(inputs, openings, location, value)
            binding = self.work / (str(index) + "-bindings.json")
            write_json(binding, {"inputs": inputs, "openings": openings})
            with self.subTest(location=location, value=value):
                for actual in (normalize_target(interpret_schedule(source, binding)), normalize_target(loads(lean(["--run", target, binding])))):
                    self.assertEqual(actual["status"], "blocked")
                    self.assertEqual(actual["emissions"], {})
                    self.assertEqual(actual["closing"], {})
                    self.assertEqual([row["code"] for row in actual["diagnostics"]], [native_code])

    def test_existing_c16_text_eacute_event_tuple_regression(self):
        suite = unittest.defaultTestLoader.loadTestsFromName("Tests.test_settlement_modules.SettlementModuleTests.test_native_text_identity_and_reference_permutation")
        result = unittest.TestResult()
        suite.run(result)
        self.assertEqual(result.testsRun, 1)
        self.assertTrue(result.wasSuccessful(), result.errors + result.failures)

    def test_actual_canonical_native_state_output_and_preflight_boundaries(self):
        helper = IdentifierProfileTests("test_actual_serialized_state_and_returned_nested_ids_preserve_profile")
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        package = helper.package()
        first = run_module_package(package, helper.work)
        self.assertEqual(first["diagnostics"], [])
        self.assertTrue(first["verification"]["reference_agrees"])
        self.assertEqual(first["trace_origin"], "native_ir_interpreter")
        closing = json.loads(json.dumps(first["closing_state"][0], ensure_ascii=False))
        self.assertEqual(closing["quantity"][0]["id"], "\t\r\n")
        package["state_cells"] = [{key: value for key, value in closing.items() if key != "movement"}]
        package["manifest"]["period"] = {"start": "2026-04-01", "end": "2026-07-01"}
        second = run_module_package(package, helper.work)
        self.assertEqual(second["diagnostics"], [])
        self.assertEqual(second["closing_state"][0]["quantity"], closing["quantity"])
        output = helper.package({"value": "é"}, {}, output_id=True)
        rejected = run_module_package(output, helper.work)
        helper.blocked(rejected, "UNSUPPORTED_IDENTIFIER_PROFILE", preflight=False)
        self.assertEqual(rejected["trace_origin"], "native_ir_interpreter")
        inputs, openings = bindings()
        inputs["identity"] = "é"
        rejected = run_module_package(helper.package(inputs, openings), helper.work)
        helper.blocked(rejected, "UNSUPPORTED_IDENTIFIER_PROFILE", preflight=True)
        self.assertNotIn("trace_origin", rejected)


if __name__ == "__main__":
    unittest.main()
