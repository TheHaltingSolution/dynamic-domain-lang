"""Owner-local unit registration, canonical transport and definition-bound carry."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
import importlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from oracles.usage_conversion import usage_conversion
from spl_compiler import modules
from spl_compiler.checker import type_from_ast
from spl_compiler.codecs import DataError, canonical, exact, file_digest, read_json, write_json
from spl_compiler.dimensions import (BASE_ADMISSION, BASE_MEANINGS, UNIT_DEFINITIONS, USAGE_FEATURE,
                                     admission, meanings)
from spl_compiler.lean_tools import ROOT as BUILD_ROOT
from spl_compiler.model import SPLException, Type

adapter = importlib.import_module("cases.usage-conversion.build_modules")
ROOT = Path(__file__).resolve().parents[1]


class UsageUnitModuleTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(Path(modules.__file__).resolve().parents[1], ROOT)
        self.assertEqual(BUILD_ROOT.resolve(), ROOT)
        self.assertEqual(adapter.ROOT.resolve(), ROOT)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.registry = Path(self.temp.name)
        self.refs = adapter.register_all(self.registry)
        self.original = read_json(ROOT / "cases/usage-conversion/neutral.json")

    def descriptor(self, name):
        return read_json(self.registry / self.refs[name]["locator"])

    def repin(self, name, descriptor):
        path = self.registry / self.refs[name]["locator"]
        write_json(path, descriptor)
        self.refs[name]["sha256"] = file_digest(path)

    def package(self, name="minute-meter", neutral=None):
        return adapter.usage_package(name, neutral, root=self.registry, reference=self.refs[name], bind=False)

    def register_uses_alias(self):
        source = adapter.HEADER + ' { input original:{value:Ratio}; define answer=original.value; }'
        exported = {"name": "uses", "parameters": [{"name": "original", "type": {"name": "Record", "args": [],
                    "fields": [["value", {"name": "Ratio", "args": []}]]}}], "result": {"name": "Ratio", "args": []}, "definition": "answer"}
        with patch.dict(adapter.SOURCES, {"uses-library": source}):
            self.refs["uses-library"] = adapter.register("uses-library", self.registry, exports=[exported])
        descriptor = self.descriptor("uses-library")
        descriptor["interface"]["schemas"] = [{"name": "uses", "fields": {"value": {"name": "Ratio", "args": []}}}]
        descriptor["interface"]["exports"][0]["parameters"][0]["type"] = {"name": "uses", "args": []}
        self.repin("uses-library", descriptor)
        imports = [{"module_ref": self.refs["uses-library"], "alias": "uses", "symbols": []}]
        with patch.dict(adapter.SOURCES, {"unused-uses": adapter.SOURCES["unused-extended"]}):
            self.refs["unused-uses"] = adapter.register("unused-uses", self.registry, imports=imports)
        package = self.package("unused-extended"); package["module_ref"] = self.refs["unused-uses"]
        return package

    def run_case(self, package, backend="reference"):
        return modules.run_module_package(modules.bind_module_package(package, self.registry), self.registry, backend=backend)

    def blocked(self, package, code):
        # Registration may reject before binding. Such a rejection has no backend
        # execution claim, whereas runtime blocks use canonical atomic finalization.
        try:
            result = self.run_case(package)
        except (DataError, SPLException) as error:
            self.assertEqual(error.code, code)
            return
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        self.assertEqual(result["results"], {})
        self.assertEqual(result["closing_state"], [])

    def test_registration_owns_header_and_exact_catalog_dictionaries(self):
        for name in self.refs:
            resolved = modules.resolve_module(self.refs[name], self.registry)
            descriptor = resolved.descriptor
            extended = name not in {"base-minute-meter", "base-download-meter", "base-library", "base-custom-import"}
            self.assertEqual(descriptor["compatibility"]["ir"], "spl-ir/0.2" if extended else "spl-ir/0.1")
        dictionary = self.descriptor("minute-meter")["interface"]["dictionaries"]
        self.assertEqual(dictionary, {"spl.units/1": ["UsageMinute"], "spl.units.usage-time/1": ["UsageHour"],
                                      "spl.conversions.usage-time/1": ["spl.usage-time/1:minute-hour"]})

    def test_original_transport_and_independent_hand_controls(self):
        for value in ("90", "0", "1/3", "-30"):
            neutral = deepcopy(self.original); neutral["source_quantity"]["value"] = value
            control = usage_conversion(neutral)
            package = self.package(neutral=neutral)
            self.assertEqual(exact(package["inputs"]["original"]["value"]), F(value))
            self.assertEqual(package["inputs"]["original"]["unit"], "UsageMinute")
            self.assertNotIn("converted", package["inputs"])
            result = self.run_case(package)
            self.assertEqual(result["diagnostics"], [], result)
            self.assertEqual(exact(result["results"]["quantity"]["value"]), control["converted_quantity"]["value"])
            self.assertEqual(exact(result["results"]["earned"]), control["earned"]["value"])

    def test_adapter_rejects_solved_fields_and_binary_float_original(self):
        for value in (90.0, True, "1/0"):
            neutral = deepcopy(self.original); neutral["source_quantity"]["value"] = value
            with self.assertRaisesRegex(ValueError, "^USAGE_EXACT_ORIGINAL_NUMBER$"):
                self.package(neutral=neutral)
        neutral = deepcopy(self.original); neutral["converted_quantity"] = {"value": "1.5", "unit": "UsageHour"}
        with self.assertRaisesRegex(ValueError, "^USAGE_ORIGINAL_RECORD_FIELDS$"):
            self.package(neutral=neutral)

    def test_missing_capability_codec_unit_relation_and_endpoint(self):
        mutations = [
            (lambda d: d["compatibility"]["capabilities"].remove(USAGE_FEATURE), "MODULE_CAPABILITY_UNDECLARED"),
            (lambda d: d["compatibility"]["codecs"].remove("spl-quantity/1"), "MODULE_CODEC_VERSION"),
            (lambda d: d["interface"]["dictionaries"].pop("spl.units.usage-time/1"), "MODULE_UNIT_UNDECLARED"),
            (lambda d: d["interface"]["dictionaries"].pop("spl.conversions.usage-time/1"), "MODULE_CONVERSION_UNDECLARED"),
            (lambda d: d["interface"]["dictionaries"].pop("spl.units/1"), "MODULE_UNIT_UNDECLARED")]
        baseline = self.descriptor("minute-meter")
        for mutate, code in mutations:
            descriptor = deepcopy(baseline); mutate(descriptor); self.repin("minute-meter", descriptor)
            self.blocked(self.package(), code)

    def test_unknown_dictionary_entry_version_and_wrong_base_dictionary(self):
        baseline = self.descriptor("minute-meter")
        for kind in ("entry", "version", "base"):
            descriptor = deepcopy(baseline)
            if kind == "entry": descriptor["interface"]["dictionaries"]["spl.units.usage-time/1"] = ["UsageDay"]
            if kind == "version": descriptor["interface"]["dictionaries"]["spl.units.usage-time/999"] = ["UsageHour"]
            if kind == "base": descriptor["interface"]["dictionaries"]["spl.units/1"].append("UsageHour")
            self.repin("minute-meter", descriptor)
            self.blocked(self.package(), "UNSUPPORTED_UNIT" if kind == "base" else "MODULE_DIMENSION_DICTIONARY")

    def test_descriptor_capability_does_not_enable_base_source_input(self):
        descriptor = self.descriptor("base-minute-meter")
        descriptor["compatibility"]["capabilities"].append(USAGE_FEATURE)
        descriptor["interface"]["ports"][0]["type"]["args"][0]["name"] = "UsageHour"
        descriptor["interface"]["dictionaries"]["spl.units.usage-time/1"] = ["UsageHour"]
        self.repin("base-minute-meter", descriptor)
        self.blocked(self.package("base-minute-meter"), "UNSUPPORTED_UNIT")

    def test_unused_local_schemas_and_exports_stay_owner_local(self):
        baseline = self.descriptor("base-library")
        for location in ("schema", "export"):
            descriptor = deepcopy(baseline)
            foreign = {"name": "Quantity", "args": [{"name": "UsageHour", "args": []}]}
            if location == "schema": descriptor["interface"]["schemas"] = [{"name": "Unused", "fields": {"quantity": foreign}}]
            else: descriptor["interface"]["exports"][0]["result"] = foreign
            self.repin("base-library", descriptor)
            self.blocked(self.package("base-library"), "UNSUPPORTED_UNIT")

    def test_same_owner_admitted_unit_and_local_alias_collision(self):
        descriptor = self.descriptor("minute-meter")
        descriptor["interface"]["schemas"] = [{"name": "UsageHour", "fields": {"label": {"name": "Text", "args": []}}}]
        self.repin("minute-meter", descriptor)
        self.blocked(self.package(), "MODULE_UNIT_OWNERSHIP_CONFLICT")

    def test_old_future_named_domain_dictionary_is_not_reinterpreted(self):
        descriptor = self.descriptor("base-minute-meter")
        descriptor["interface"]["dictionaries"]["spl.units.usage-time/999"] = ["an-old-domain-token"]
        self.repin("base-minute-meter", descriptor)
        self.assertEqual(modules.resolve_module(self.refs["base-minute-meter"], self.registry).descriptor, descriptor)

    def test_contextual_uses_local_schema_and_unused_export_alias(self):
        package = self.register_uses_alias()
        resolved = modules.resolve_module(package["module_ref"], self.registry)
        manifest = modules.linking_manifest(resolved)
        self.assertEqual(manifest["modules"][0]["descriptor"]["interface"]["exports"][0]["parameters"][0]["type"]["name"], "Record")
        self.assertEqual(resolved.descriptor["compatibility"]["ir"], "spl-ir/0.1")
        result = self.run_case(package)
        self.assertEqual(result["diagnostics"], [], result)
        self.assertEqual(result["results"], {"earned": "1"})

    def test_root_closure_version_includes_unused_extended_usd_dependency(self):
        descriptor = self.descriptor("unused-extended")
        self.assertEqual(descriptor["compatibility"]["ir"], "spl-ir/0.2")
        self.assertEqual(self.descriptor("usd-library")["interface"]["dictionaries"], {})
        descriptor["compatibility"]["ir"] = "spl-ir/0.1"; self.repin("unused-extended", descriptor)
        self.blocked(self.package("unused-extended"), "MODULE_IR_VERSION")

    def test_base_library_remains_v1_inside_v2_root(self):
        resolved = modules.resolve_module(self.refs["extended-base-import"], self.registry)
        self.assertEqual([item["descriptor"]["compatibility"]["ir"] for item in resolved.closure], ["spl-ir/0.1", "spl-ir/0.2"])
        self.assertEqual(self.run_case(self.package("extended-base-import"))["results"], {"earned": "45"})
        self.assertEqual(self.run_case(self.package("base-custom-import"))["results"], {"earned": "45"})

    def test_base_root_infers_foreign_hour_arithmetic_without_spelling_permission(self):
        result = self.run_case(self.package("inferred-import"))
        self.assertEqual(result["diagnostics"], [], result)
        self.assertEqual(result["results"], {"quantity": {"value": "3", "unit": "UsageHour"}})
        resolved = modules.resolve_module(self.refs["inferred-import"], self.registry)
        checked = modules._checked_source(resolved)
        self.assertEqual(checked.admission, BASE_ADMISSION)
        self.assertEqual(checked.meanings.features, (USAGE_FEATURE,))
        with self.assertRaises(SPLException) as raised:
            type_from_ast({"name": "Quantity", "args": [{"name": "UsageHour", "args": []}]}, checked.admission)
        self.assertEqual(raised.exception.code, "UNSUPPORTED_UNIT")

    def test_foreign_result_contract_requires_actual_inference(self):
        descriptor = self.descriptor("unused-extended")
        descriptor["compatibility"]["capabilities"].append("spl.quantities/1")
        descriptor["interface"]["dictionaries"] = {"spl.units.usage-time/1": ["UsageHour"]}
        descriptor["interface"]["ports"][0]["type"] = {"name": "Quantity", "args": [{"name": "UsageHour", "args": []}]}
        self.repin("unused-extended", descriptor)
        self.blocked(self.package("unused-extended"), "MODULE_OUTPUT_TYPE")

    def test_inferred_result_does_not_legalize_unused_schema(self):
        descriptor = self.descriptor("inferred-import")
        descriptor["interface"]["schemas"] = [{"name": "Unused", "fields": {"hour": {"name": "Quantity", "args": [{"name": "UsageHour", "args": []}]}}}]
        self.repin("inferred-import", descriptor)
        self.blocked(self.package("inferred-import"), "UNSUPPORTED_UNIT")

    def test_foreign_closure_does_not_enable_root_annotation_or_builtin(self):
        path = self.registry / self.descriptor("inferred-import")["source"]["locator"]
        original = path.read_text(encoding="utf-8")
        for replacement, code in [
            ('define h:Quantity<UsageHour> = to_hour(original);', "UNSUPPORTED_UNIT"),
            ('define h = convert_quantity(original,"UsageHour","spl.usage-time/1:minute-hour");', "UNSUPPORTED_BUILTIN")]:
            path.write_bytes(original.replace('define h = to_hour(original);', replacement).encode("utf-8"))
            descriptor = self.descriptor("inferred-import"); descriptor["source"]["sha256"] = file_digest(path)
            self.repin("inferred-import", descriptor)
            self.blocked(self.package("inferred-import"), code)

    def test_recursive_state_identity_pins_only_used_definitions(self):
        extended = meanings([admission([USAGE_FEATURE])])
        q = lambda name: Type("Quantity", (Type(name),))
        self.assertEqual(modules.dimensioned_state_unit(q("Download")), "dimensioned:495808ae9a33038bcc29cf5b3fc3c7cff8da359bf26c7daf90e0e5852e171978")
        self.assertEqual(modules.dimensioned_state_unit(q("UsageMinute")), modules.dimensioned_state_unit(q("UsageMinute"), extended))
        named_field = Type("Record", fields=(("UsageHour", q("UsageMinute")),))
        self.assertEqual(modules.dimensioned_state_unit(named_field), modules.dimensioned_state_unit(named_field, extended))
        self.assertTrue(modules.dimensioned_state_unit(named_field, extended).startswith("dimensioned:"))
        compound = Type("Record", fields=(
            ("nested", Type("List", (Type("Option", (Type("Tuple", (Type("Id", (Type("UsageHour"),)), q("UsageHour"))),)),))),
            ("mapping", Type("Map", (Type("Id", (Type("Original"),)), q("UsageHour"))))))
        identity = modules.dimensioned_state_unit(compound, extended)
        self.assertTrue(identity.startswith("dimensioned-v2:"))
        ast = adapter.ast_type(compound)
        self.assertEqual(modules.dimensioned_state_unit(ast, extended), identity)
        with patch("spl_compiler.dimensions.UNIT_DEFINITIONS", tuple(unit for unit in UNIT_DEFINITIONS if unit.name != "Download")):
            self.assertEqual(modules.dimensioned_state_unit(compound, extended), identity)
        changed = tuple(replace(unit, scale=F(59)) if unit.name == "UsageHour" else unit for unit in UNIT_DEFINITIONS)
        with patch("spl_compiler.dimensions.UNIT_DEFINITIONS", changed):
            self.assertNotEqual(modules.dimensioned_state_unit(compound, extended), identity)

    def test_actual_v1_id_alias_recursion_and_frozen_state_hashes(self):
        descriptor = self.descriptor("base-minute-meter")
        ast = {"name": "Record", "args": [], "fields": [["marker", {"name": "Id", "args": [{"name": "UsageHour", "args": []}]}],
                ["quantity", {"name": "Quantity", "args": [{"name": "UsageMinute", "args": []}]}]]}
        plain = modules._type_ast(ast, descriptor)
        self.assertEqual(modules.dimensioned_state_unit(plain), "dimensioned:035d54d28564df0f1e648dff57028a59231fd29ebd0e90fd20749e327edf3352")
        descriptor["interface"]["schemas"] = [{"name": "UsageHour", "fields": {"label": {"name": "Text", "args": []}}}]
        aliased = modules._type_ast(ast, descriptor)
        self.assertEqual(aliased["fields"][0][1]["args"][0]["name"], "Record")
        self.assertEqual(modules.dimensioned_state_unit(aliased), "dimensioned:29742617b381396f64a215c88e7153b3b3dbf4a972f3b95168f5985aaca1a4be")

    def test_actual_canonical_v1_id_alias_acceptance_and_rejection(self):
        self.alias_controls()

    def alias_controls(self, backend="reference"):
        for source_kind, alias, expected_hash, expected_code in [
            ("UsageHour", False, "035d54d28564df0f1e648dff57028a59231fd29ebd0e90fd20749e327edf3352", None),
            ("UsageHour", True, "035d54d28564df0f1e648dff57028a59231fd29ebd0e90fd20749e327edf3352", "MODULE_PORT_MISMATCH"),
            ("Record", True, "29742617b381396f64a215c88e7153b3b3dbf4a972f3b95168f5985aaca1a4be", None)]:
            name = "alias-" + source_kind.lower() + str(alias).lower()
            source = adapter.HEADER + ''' {
  input original: Quantity<UsageMinute>;
  opening meter: {marker:Id<''' + source_kind + '''>,quantity:Quantity<UsageMinute>} from "original-meter";
  emit "quantity" = original;
  closing meter = {marker:meter.marker,quantity:meter.quantity + original};
}'''
            with patch.dict(adapter.SOURCES, {name: source}):
                ref = adapter.register(name, self.registry)
            self.refs[name] = ref
            descriptor = self.descriptor(name)
            if alias:
                descriptor["interface"]["schemas"] = [{"name": "UsageHour", "fields": {"label": {"name": "Text", "args": []}}}]
                opening = next(p for p in descriptor["interface"]["ports"] if p["role"] == "opening")
                opening["type"]["fields"][0][1]["args"][0]["name"] = "UsageHour"
            self.repin(name, descriptor)
            package = self.package("base-minute-meter")
            package["module_ref"] = self.refs[name]
            package["inputs"].pop("price")
            cell = package["state_cells"][0]
            cell["quantity"] = {"marker": "old-token", "quantity": {"value": "0", "unit": "UsageMinute"}}
            cell["unit"] = cell["scope"]["unit"] = "dimensioned:" + expected_hash
            cell["state_key"] = canonical({**cell["scope"], "purpose": cell["purpose"]})
            if expected_code:
                self.blocked(package, expected_code)
            else:
                result = self.run_case(package, backend)
                self.assertEqual(result["diagnostics"], [], result)
                self.assertEqual(result["closing_state"][0]["unit"], "dimensioned:" + expected_hash)
                self.assertEqual(result["closing_state"][0]["quantity"], {"marker": "old-token", "quantity": {"value": "90", "unit": "UsageMinute"}})

    def test_opaque_id_quantity_rate_keep_actual_v1_dimension_classification(self):
        from spl_compiler.dimensions import contains_dimension, used_unit_definitions
        old_hashes = {"Quantity": "e1498a6dd6f3463b985a83f5f64f20751015ef1d8b5a8a3b8470e44bcdc7e492",
                      "Rate": "ab64b6cb597aceb0c167f02379c051900483a4a55df066002647d963f328367c",
                      "UsageHour": "78dfbca9a09277ca9d64ecf9e4f48f5df2601807c00786bfa700dc5147ca1858"}
        for kind in ("Quantity", "Rate", "UsageHour"):
            typ = Type("Id", (Type(kind),))
            self.assertEqual(used_unit_definitions(typ, meanings([admission([USAGE_FEATURE])])), ())
            # Existing v1 classification is deliberately frozen, even though
            # Quantity/Rate here are only opaque namespace names.
            self.assertEqual(contains_dimension(typ), kind in {"Quantity", "Rate"})
            self.assertEqual(modules.dimensioned_state_unit(typ), "dimensioned:" + old_hashes[kind])
            self.assertEqual(modules.dimensioned_state_unit(typ), modules.dimensioned_state_unit(typ, meanings([admission([USAGE_FEATURE])])) )
            if kind == "UsageHour":
                continue
            name = "opaque-id-" + kind.lower()
            source = adapter.HEADER + ' { input original: Quantity<UsageMinute>; opening meter: Id<' + kind + '> from "old-id-meter"; emit "quantity" = original; closing meter = meter; }'
            with patch.dict(adapter.SOURCES, {name: source}):
                ref = adapter.register(name, self.registry)
            package = self.package("base-minute-meter"); package["module_ref"] = ref; package["inputs"].pop("price")
            cell = package["state_cells"][0]
            cell["quantity"] = "old-token"
            cell["unit"] = cell["scope"]["unit"] = modules.dimensioned_state_unit(typ)
            cell["state_key"] = canonical({**cell["scope"], "purpose": cell["purpose"]})
            result = self.run_case(package)
            self.assertEqual(result["diagnostics"], [], result)
            self.assertEqual(result["closing_state"][0]["quantity"], "old-token")
            self.assertEqual(result["closing_state"][0]["unit"], modules.dimensioned_state_unit(typ))
            cell["unit"] = cell["scope"]["unit"] = "structured"
            self.blocked(package, "MODULE_STATE_TYPE")

    def test_forged_state_pin_codec_and_scope_reject_before_finalization(self):
        for field in ("unit", "missing_pin", "codec", "scope"):
            package = self.package("hour-meter")
            if field == "unit": package["state_cells"][0]["unit"] = "dimensioned-v2:" + "0" * 64
            if field == "missing_pin": package["state_cells"][0]["unit"] = "structured"
            if field == "codec": package["state_cells"][0]["quantity"]["unit"] = "UsageMinute"
            if field == "scope": package["state_cells"][0]["scope"]["pool_id"] = "foreign-pool"
            self.blocked(package, {"unit": "MODULE_STATE_TYPE", "missing_pin": "MODULE_STATE_TYPE", "codec": "UNIT_MISMATCH", "scope": "MODULE_STATE_SCOPE"}[field])

    def test_actual_base_minute_carry_to_extended_output_keeps_unit(self):
        neutral = deepcopy(self.original); neutral["price"].update(value="0.20", per_unit="UsageMinute")
        first = self.run_case(self.package("base-minute-meter", neutral))
        self.assertEqual(first["diagnostics"], [], first)
        second = self.package()
        second["state_cells"] = [deepcopy(first["closing_state"][0])]
        second["state_cells"][0].pop("movement")
        second["manifest"].update(run_id="minute-successor", period={"start": "2026-04-01", "end": "2026-07-01"}, cutoff="2026-07-03T00:00:00Z")
        carried = self.run_case(second)
        self.assertEqual(carried["diagnostics"], [], carried)
        self.assertEqual(first["closing_state"][0]["unit"], carried["closing_state"][0]["unit"])
        self.assertEqual(carried["closing_state"][0]["quantity"], {"value": "180", "unit": "UsageMinute"})
        self.assertEqual(carried["results"], {"quantity": {"value": "1.5", "unit": "UsageHour"}, "earned": "18"})

    def test_actual_new_hour_genesis_and_successor(self):
        first = self.run_case(self.package("hour-meter"))
        self.assertEqual(first["diagnostics"], [], first)
        self.assertTrue(first["closing_state"][0]["unit"].startswith("dimensioned-v2:"))
        second = self.package("hour-meter")
        second["state_cells"] = [deepcopy(first["closing_state"][0])]; second["state_cells"][0].pop("movement")
        second["inputs"]["original"]["value"] = "60"
        second["manifest"].update(run_id="hour-successor", period={"start": "2026-04-01", "end": "2026-07-01"}, cutoff="2026-07-03T00:00:00Z")
        carried = self.run_case(second)
        self.assertEqual(carried["diagnostics"], [], carried)
        self.assertEqual(carried["closing_state"][0]["quantity"], {"value": "2.5", "unit": "UsageHour"})
        self.assertEqual(carried["closing_state"][0]["prior_result_ref"], "result@sha256:" + carried["semantic_run_digest"])

    def test_actual_base_download_carry_keeps_payload_and_identity(self):
        neutral = deepcopy(self.original)
        neutral["source_quantity"].update(value="100", unit="Download")
        neutral["price"].update(value="1.5", per_unit="Download")
        package = self.package("base-download-meter", neutral)
        first = self.run_case(package)
        self.assertEqual(first["diagnostics"], [], first)
        self.assertEqual(first["results"]["earned"], "150")
        cell = deepcopy(first["closing_state"][0]); cell.pop("movement")
        package["state_cells"] = [cell]; package["inputs"]["original"]["value"] = "0.5"
        package["manifest"].update(run_id="legacy-download-successor", period={"start": "2026-04-01", "end": "2026-07-01"}, cutoff="2026-07-03T00:00:00Z")
        carried = self.run_case(package)
        self.assertEqual(carried["diagnostics"], [], carried)
        self.assertEqual(carried["results"]["earned"], "0.75")
        self.assertEqual(carried["closing_state"][0]["quantity"], {"value": "100.5", "unit": "Download"})
        self.assertEqual(carried["closing_state"][0]["unit"], "dimensioned:495808ae9a33038bcc29cf5b3fc3c7cff8da359bf26c7daf90e0e5852e171978")

    def test_native_canonical_conversion_carries_and_inferred_closure(self):
        # Native commands only after the coordinated core release. There is no
        # reference-only environment switch that silently claims these ran.
        for name in ("minute-meter", "hour-meter", "inferred-import", "unused-extended"):
            package = self.package(name)
            first_package = package
            if name == "minute-meter":
                legacy = deepcopy(self.original); legacy["price"].update(value="0.20", per_unit="UsageMinute")
                first_package = self.package("base-minute-meter", legacy)
            first = self.run_case(first_package, "compare")
            self.assertEqual(first["diagnostics"], [], first)
            self.assertTrue(first["verification"]["reference_agrees"])
            if name in {"minute-meter", "hour-meter"}:
                self.assertEqual(first["results"]["earned"], "18")
                second = deepcopy(package)
                second["state_cells"] = [deepcopy(first["closing_state"][0])]; second["state_cells"][0].pop("movement")
                second["manifest"].update(run_id=name + "-native-successor", period={"start": "2026-04-01", "end": "2026-07-01"}, cutoff="2026-07-03T00:00:00Z")
                carried = self.run_case(second, "compare")
                self.assertEqual(carried["diagnostics"], [], carried)
                self.assertEqual(carried["results"]["quantity"], {"value": "1.5", "unit": "UsageHour"})
                self.assertEqual(carried["closing_state"][0]["quantity"], {"value": "180" if name == "minute-meter" else "3", "unit": "UsageMinute" if name == "minute-meter" else "UsageHour"})
            elif name == "inferred-import":
                self.assertEqual(first["results"], {"quantity": {"value": "3", "unit": "UsageHour"}})
            else:
                self.assertEqual(first["results"], {"earned": "1"})
        uses = self.run_case(self.register_uses_alias(), "compare")
        self.assertEqual(uses["diagnostics"], [], uses)
        self.assertEqual(uses["results"], {"earned": "1"})
        self.alias_controls("compare")


if __name__ == "__main__":
    unittest.main()
