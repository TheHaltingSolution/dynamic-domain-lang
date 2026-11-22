"""Canonical dimensional registration, recursive transport and actual carry."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from cases.quantities import adapter
from oracles.quantities import quantity_participation
from spl_compiler.codecs import (DataError, canonical, dimensional_amount, encode, exact,
                                 file_digest, quantity, rate, read_json, write_json)
from spl_compiler.lean_tools import ROOT
from spl_compiler.model import QuantityValue, RateValue, SPLException, Type
from spl_compiler.modules import dimensioned_state_unit, resolve_module
from spl_compiler.run import bind_package, run_package


class QuantityModuleTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        shutil.copytree(ROOT / "cases/quantities", self.root / "cases/quantities", ignore=shutil.ignore_patterns("__pycache__"))
        self.addCleanup(patch.stopall)
        patch.object(adapter, "ROOT", self.root).start()
        self.reference = adapter.register_quantities()
        self.package = adapter.quantity_package(reference=self.reference)
        self.descriptor_path = self.root / "cases/quantities/descriptor.json"
        self.descriptor = read_json(self.descriptor_path)

    def repin(self):
        write_json(self.descriptor_path, self.descriptor)
        self.package["module_ref"]["sha256"] = file_digest(self.descriptor_path)

    def run_reference(self, package=None):
        package = self.package if package is None else package
        return run_package(bind_package(package, self.root), self.root, backend="reference")

    def assert_blocked(self, package, code):
        result = self.run_reference(package)
        self.assertEqual(result["status"], "blocked", result)
        self.assertEqual(result["diagnostics"][0]["code"], code, result)
        self.assertEqual(result["results"], {})
        self.assertEqual(result["closing_state"], [])

    def test_exact_registered_witness_and_actual_successor_carry(self):
        first = self.run_reference()
        self.assertEqual(first["diagnostics"], [])
        self.assertEqual(first["results"]["gross"], "150")
        self.assertEqual(first["results"]["earned"], "75")
        self.assertEqual(first["results"]["period_quantity"], {"value": "100", "unit": "Download"})
        cell = deepcopy(first["closing_state"][0])
        self.assertEqual(cell["movement"]["opening"], {"value": "0", "unit": "Download"})
        self.assertEqual(cell["quantity"], {"value": "100", "unit": "Download"})
        self.assertEqual(cell["scope"]["unit"], cell["unit"])
        self.assertEqual(read_json(self.root / "cases/quantities/package.json")["manifest"]["compiler_build"], "unbound")
        cell.pop("movement")
        successor = deepcopy(self.package)
        successor["state_cells"] = [cell]
        successor["manifest"].update(run_id="successor", period={"start": "2026-04-01", "end": "2026-07-01"}, cutoff="2026-07-03T00:00:00Z")
        successor["inputs"].update(accounting_period=deepcopy(successor["manifest"]["period"]), observation_cutoff=successor["manifest"]["cutoff"])
        successor["inputs"]["usage"][0].update(quantity={"value": "0.5", "unit": "Download"}, effective_date="2026-05-01", observed_at="2026-07-02T00:00:00Z")
        successor["evidence"]["attestations"][0]["observed_at"] = "2026-07-02T00:00:00Z"
        second = self.run_reference(successor)
        self.assertEqual(second["diagnostics"], [])
        self.assertEqual(second["results"]["earned"], "0.375")
        self.assertEqual(second["closing_state"][0]["quantity"], {"value": "100.5", "unit": "Download"})
        self.assertEqual(second["closing_state"][0]["prior_result_ref"], "result@sha256:" + second["semantic_run_digest"])

    def test_zero_fractional_and_signed_case_policy(self):
        for value, gross, earned in [("0", "0", "0"), ("0.5", "0.75", "0.375"),
                                    ({"numerator": "1", "denominator": "3"}, "0.5", "0.25")]:
            package = deepcopy(self.package)
            package["inputs"]["usage"][0]["quantity"]["value"] = value
            result = self.run_reference(package)
            self.assertEqual(result["diagnostics"], [])
            self.assertEqual((result["results"]["gross"], result["results"]["earned"]), (gross, earned))
        for target in ["usage", "rate", "opening"]:
            package = deepcopy(self.package)
            value = (package["inputs"]["usage"][0]["quantity"] if target == "usage" else
                     package["parameters"]["unit_rate"] if target == "rate" else package["state_cells"][0]["quantity"])
            value["value"] = "-0.5"
            self.assert_blocked(package, "Q_NONNEGATIVE")
        package = deepcopy(self.package)
        package["inputs"]["usage"] = []
        package["evidence"]["attestations"] = []
        result = self.run_reference(package)
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["results"]["period_quantity"], {"value": "0", "unit": "Download"})
        package["inputs"]["usage"] = deepcopy(self.package["inputs"]["usage"])
        self.assert_blocked(package, "Q_EVIDENCE_REQUIRED")

    def test_independent_neutral_oracle_controls_split_and_permutation(self):
        fixture = read_json(self.root / "cases/quantities/neutral.json")
        for amounts in [("100",), ("0",), (), ("0.5",), ("1/3",), ("25", "75"), ("75", "25")]:
            neutral = deepcopy(fixture)
            neutral["usage"] = [{**deepcopy(fixture["usage"][0]), "record_id": "usage-" + str(index), "quantity": value}
                                for index, value in enumerate(amounts)]
            controls = quantity_participation(neutral)
            result = self.run_reference(adapter.quantity_package(neutral, self.reference))
            self.assertEqual(result["diagnostics"], [])
            for key in ["gross", "earned"]:
                self.assertEqual(exact(result["results"][key]), controls[key])
            self.assertEqual(exact(result["results"]["period_quantity"]["value"]), controls["period_quantity"])
            self.assertEqual(exact(result["closing_state"][0]["quantity"]["value"]), controls["closing_quantity"])

    def test_native_registered_witness_matches_neutral_controls(self):
        fixture = read_json(self.root / "cases/quantities/neutral.json")
        for value in ["100", "0", "1/3"]:
            neutral = deepcopy(fixture)
            neutral["usage"][0]["quantity"] = value
            controls = quantity_participation(neutral)
            package = adapter.quantity_package(neutral, self.reference)
            result = run_package(bind_package(package, self.root), self.root, backend="compare")
            self.assertEqual(result["diagnostics"], [])
            self.assertTrue(result["verification"]["reference_agrees"])
            self.assertEqual(exact(result["results"]["earned"]), controls["earned"])
            self.assertEqual(exact(result["results"]["gross"]), controls["gross"])
            self.assertEqual(exact(result["results"]["period_quantity"]["value"]), controls["period_quantity"])
            self.assertEqual(exact(result["closing_state"][0]["quantity"]["value"]), controls["closing_quantity"])
            if value == "100":
                following = deepcopy(neutral)
                following.update(case_id="native-successor", period={"start": "2026-04-01", "end": "2026-07-01"}, cutoff="2026-07-03T00:00:00Z")
                following["opening_state"]["quantity"] = "100"
                following["usage"][0].update(quantity="0.5", effective_date="2026-05-01", observed_at="2026-07-02T00:00:00Z")
                following["evidence"][0]["observed_at"] = "2026-07-02T00:00:00Z"
                controls = quantity_participation(following)
                successor = adapter.quantity_package(following, self.reference)
                actual_cell = deepcopy(result["closing_state"][0])
                actual_cell.pop("movement")
                successor["state_cells"] = [actual_cell]
                carried = run_package(bind_package(successor, self.root), self.root, backend="compare")
                self.assertEqual(carried["diagnostics"], [])
                self.assertEqual(exact(carried["results"]["earned"]), controls["earned"])
                self.assertEqual(exact(carried["closing_state"][0]["quantity"]["value"]), controls["closing_quantity"])

    def test_missing_capability_codec_dictionary_and_unknown_units(self):
        mutations = [(lambda: self.descriptor["compatibility"]["capabilities"].remove("spl.quantities/1"), "MODULE_CAPABILITY_UNDECLARED"),
                     (lambda: self.descriptor["compatibility"]["codecs"].remove("spl-quantity/1"), "MODULE_CODEC_VERSION"),
                     (lambda: self.descriptor["interface"]["dictionaries"].pop("spl.units/1"), "MODULE_UNIT_UNDECLARED"),
                     (lambda: self.descriptor["interface"]["dictionaries"]["spl.units/1"].append("download"), "UNSUPPORTED_UNIT")]
        original = deepcopy(self.descriptor)
        for mutate, code in mutations:
            self.descriptor = deepcopy(original)
            mutate()
            self.repin()
            with self.assertRaises(DataError) as raised:
                resolve_module(self.package["module_ref"], self.root)
            self.assertEqual(raised.exception.code, code)

    def test_all_closure_descriptors_validate_units_including_unused_exports(self):
        library = deepcopy(self.descriptor)
        library.update(id="synthetic:unused-units", constraints=[], state=[], imports=[])
        library["compatibility"]["capabilities"].append("spl.modules/1")
        library["interface"] = {"ports": [], "schemas": [], "exports": [], "dictionaries": {"spl.units/1": ["Bogus"]}}
        write_json(self.root / "library.json", library)
        self.descriptor["imports"] = [{"module_ref": {"id": library["id"], "revision": "1", "locator": "library.json", "sha256": file_digest(self.root / "library.json")}, "alias": "unused", "symbols": []}]
        self.descriptor["compatibility"]["capabilities"].append("spl.modules/1")
        self.repin()
        with self.assertRaises(DataError) as raised:
            resolve_module(self.package["module_ref"], self.root)
        self.assertEqual(raised.exception.code, "UNSUPPORTED_UNIT")

    def test_unused_imported_schema_and_export_signatures_are_fully_admitted(self):
        original = deepcopy(self.descriptor)
        for foreign, expected in [(adapter.typ("Quantity", adapter.typ("Bogus")), "UNSUPPORTED_UNIT"),
                                  (adapter.typ("Rate", adapter.typ("Download"), adapter.typ("EUR")), "UNSUPPORTED_CURRENCY")]:
            for location in ["schema", "export"]:
                self.descriptor = deepcopy(original)
                library = deepcopy(original)
                library.update(id="synthetic:unused-types", constraints=[], state=[], imports=[])
                library["compatibility"]["capabilities"].append("spl.modules/1")
                library["interface"] = {"ports": [], "schemas": [], "exports": [], "dictionaries": {"spl.units/1": ["Download"]}}
                if location == "schema":
                    library["interface"]["schemas"] = [{"name": "Unused", "fields": {"value": foreign}}]
                else:
                    library["interface"]["exports"] = [{"name": "unused", "parameters": [], "result": foreign, "definition": "unused"}]
                write_json(self.root / "library.json", library)
                self.descriptor["imports"] = [{"module_ref": {"id": library["id"], "revision": "1", "locator": "library.json", "sha256": file_digest(self.root / "library.json")}, "alias": "unused", "symbols": []}]
                self.descriptor["compatibility"]["capabilities"].append("spl.modules/1")
                self.repin()
                with self.assertRaises(SPLException) as raised:
                    resolve_module(self.package["module_ref"], self.root)
                self.assertEqual(raised.exception.code, expected)

    def test_dimensional_domain_bounds_require_matching_explicit_tags(self):
        port = next(port for port in self.descriptor["interface"]["ports"] if port["name"] == "unit_rate")
        port["domain"] = {"minimum": {"value": "0", "per_unit": "Download", "currency": "USD"},
                          "maximum": {"value": "2", "per_unit": "Download", "currency": "USD"}}
        self.repin()
        self.assertEqual(self.run_reference()["diagnostics"], [])
        for bound in ["0", {"value": "0", "unit": "Download"}, {"value": "0", "per_unit": "UsageMinute", "currency": "USD"}]:
            port["domain"]["minimum"] = bound
            self.repin()
            self.assert_blocked(self.package, "MODULE_PARAMETER_DIMENSION")
        port["domain"]["minimum"] = {"value": "2", "per_unit": "Download", "currency": "USD"}
        self.repin()
        self.assert_blocked(self.package, "MODULE_PARAMETER_DOMAIN")

    def test_conservation_target_retains_dimension_for_mixed_and_empty_rows(self):
        source = self.root / "cases/quantities/download-participation.spl"
        original_source = source.read_text(encoding="utf-8")
        original_descriptor = deepcopy(self.descriptor)
        for source_type, type_ast, tagged, expected in [
            ("Quantity<Download>", adapter.typ("Quantity", adapter.typ("Download")), {"value": "100", "unit": "Download"}, None),
            ("Quantity<UsageMinute>", adapter.typ("Quantity", adapter.typ("UsageMinute")), {"value": "100", "unit": "UsageMinute"}, "MODULE_CONSERVATION_DIMENSION"),
            ("Rate<Download,USD>", adapter.typ("Rate", adapter.typ("Download"), adapter.typ("USD")), {"value": "100", "per_unit": "Download", "currency": "USD"}, "MODULE_CONSERVATION_DIMENSION"),
            ("Ratio", adapter.typ("Ratio"), "100", "MODULE_CONSERVATION_DIMENSION")]:
            self.descriptor = deepcopy(original_descriptor)
            source.write_text(original_source.replace("input participation: Ratio;", "input declared_total: " + source_type + "; input participation: Ratio;"), encoding="utf-8", newline="\n")
            self.descriptor["source"]["sha256"] = file_digest(source)
            self.descriptor["interface"]["ports"].append({"name": "declared_total", "role": "input", "type": type_ast, "domain": {}, "dimensions": []})
            self.descriptor["interface"]["dictionaries"]["spl.units/1"] = ["Download", "UsageMinute"]
            self.descriptor["constraints"].append({"kind": "conservation", "path": "inputs.usage", "fields": ["quantity"], "target": "inputs.declared_total", "value": ""})
            self.package["inputs"]["declared_total"] = tagged
            self.repin()
            if expected:
                self.assert_blocked(self.package, expected)
                empty = deepcopy(self.package)
                empty["inputs"]["usage"] = []
                empty["evidence"]["attestations"] = []
                empty["inputs"]["declared_total"] = ({**tagged, "value": "0"} if isinstance(tagged, dict) else "0")
                self.assert_blocked(empty, expected)
            else:
                self.assertEqual(self.run_reference()["diagnostics"], [])
                zero = deepcopy(self.package)
                zero["inputs"]["usage"] = []
                zero["evidence"]["attestations"] = []
                zero["inputs"]["declared_total"] = {"value": "0", "unit": "Download"}
                result = self.run_reference(zero)
                self.assertEqual(result["diagnostics"], [])
                self.assertEqual(result["results"]["period_quantity"], {"value": "0", "unit": "Download"})
                zero["inputs"]["declared_total"]["value"] = "1"
                self.assert_blocked(zero, "MODULE_CONSERVATION")

    def test_transport_dimensions_period_scope_evidence_and_cutoff_block_atomically(self):
        mutations = [
            (lambda p: p["inputs"]["usage"][0]["quantity"].update(unit="UsageMinute"), "UNIT_MISMATCH"),
            (lambda p: p["parameters"]["unit_rate"].update(per_unit="UsageMinute"), "UNIT_MISMATCH"),
            (lambda p: p["parameters"]["unit_rate"].update(currency="EUR"), "CURRENCY_MISMATCH"),
            (lambda p: p["inputs"]["usage"][0].update(quantity="100"), "INVALID_QUANTITY"),
            (lambda p: p["parameters"].update(unit_rate="1.5"), "INVALID_RATE"),
            (lambda p: p["inputs"]["usage"][0]["quantity"].update(unknown="tag"), "INVALID_QUANTITY"),
            (lambda p: p["inputs"]["usage"][0].update(effective_date="2026-04-01"), "Q_OUTSIDE_PERIOD"),
            (lambda p: p["inputs"]["usage"][0].update(observed_at=p["manifest"]["cutoff"]), "Q_USAGE_AFTER_CUTOFF"),
            (lambda p: p["evidence"]["attestations"][0].update(observed_at=p["manifest"]["cutoff"]), "EVIDENCE_AFTER_CUTOFF"),
            (lambda p: p["inputs"]["usage"][0].update(evidence_ref="missing"), "Q_EVIDENCE_REQUIRED"),
            (lambda p: p["inputs"].update(agreement="foreign-agreement"), "MODULE_REFERENCE_SCOPE")]
        for mutate, code in mutations:
            package = deepcopy(self.package)
            mutate(package)
            self.assert_blocked(package, code)

    def test_dimensioned_state_scope_key_and_complete_structural_identity(self):
        from spl_compiler.checker import type_from_ast
        quantity_type = Type("Quantity", (Type("Download"),))
        rate_type = Type("Rate", (Type("Download"), Type("USD")))
        other_type = Type("Quantity", (Type("UsageMinute"),))
        nested = Type("Record", fields=(("z", Type("List", (quantity_type,))), ("a", rate_type)))
        reordered = Type("Record", fields=tuple(reversed(nested.fields)))
        self.assertEqual(dimensioned_state_unit(nested), dimensioned_state_unit(reordered))
        self.assertEqual(len({dimensioned_state_unit(t) for t in [quantity_type, rate_type, other_type, nested]}), 4)
        compound_ast = {"name": "Record", "args": [], "fields": [
            ["quantity", adapter.typ("Quantity", adapter.typ("Download"))], ["period", adapter.typ("Period")],
            ["quotes", adapter.typ("List", adapter.typ("Rate", adapter.typ("Download"), adapter.typ("USD")))]]}
        self.assertEqual(dimensioned_state_unit(compound_ast), dimensioned_state_unit(type_from_ast(compound_ast)))
        self.assertEqual(dimensioned_state_unit(adapter.typ("Quantity", adapter.typ("Download"))),
                         "dimensioned:495808ae9a33038bcc29cf5b3fc3c7cff8da359bf26c7daf90e0e5852e171978")
        for mutate, code in [
            (lambda p: p["state_cells"][0]["scope"].pop("unit"), "MODULE_STATE_TYPE"),
            (lambda p: p["state_cells"][0]["scope"].update(unit="structured"), "MODULE_STATE_TYPE"),
            (lambda p: p["state_cells"][0].update(unit="structured"), "MODULE_STATE_TYPE"),
            (lambda p: p["state_cells"][0].update(state_key="legacy-undimensioned-key"), "MODULE_STATE_KEY")]:
            package = deepcopy(self.package)
            mutate(package)
            self.assert_blocked(package, code)
        self.descriptor["state"][0]["key_fields"].remove("unit")
        self.repin()
        self.assert_blocked(self.package, "MODULE_STATE_KEY")

    def test_nested_dimensional_state_cannot_use_legacy_structured_identity(self):
        source = self.root / "cases/quantities/download-participation.spl"
        source.write_text('schedule Nested language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" { '
                          'opening payload: {quantities: List<Quantity<Download>>, quote: Option<Rate<Download,USD>>} from "nested"; '
                          'closing payload = payload; emit "result" = payload; }', encoding="utf-8", newline="\n")
        nested = {"name": "Record", "args": [], "fields": [["quantities", adapter.typ("List", adapter.typ("Quantity", adapter.typ("Download")))],
            ["quote", adapter.typ("Option", adapter.typ("Rate", adapter.typ("Download"), adapter.typ("USD")))]]}
        self.descriptor["source"]["sha256"] = file_digest(source)
        self.descriptor["compatibility"]["capabilities"].append("spl.tuple-map/1")
        self.descriptor["interface"].update(ports=[{"name": name, "role": role, "type": nested, "dimensions": ["unit"], "domain": {}}
                                                  for name, role in [("payload", "opening"), ("result", "result")]], schemas=[])
        slot = self.descriptor["state"][0]
        slot.update(opening="payload", closing="payload", unit="structured", key_fields=["agreement_id", "participant_id", "pool_id", "asset_id", "purpose"])
        cell = self.package["state_cells"][0]
        cell.update(opening_port="payload", unit="structured", quantity={"quantities": [{"value": "0.5", "unit": "Download"}],
                     "quote": {"some": {"value": "1.5", "per_unit": "Download", "currency": "USD"}}})
        cell["scope"].pop("unit")
        cell["state_key"] = canonical({**cell["scope"], "purpose": cell["purpose"]})
        self.package.update(inputs={}, parameters={}, evidence={})
        self.descriptor["constraints"] = []
        self.repin()
        self.assert_blocked(self.package, "MODULE_STATE_TYPE")
        unit = dimensioned_state_unit(nested)
        slot["unit"] = cell["unit"] = cell["scope"]["unit"] = unit
        slot["key_fields"].append("unit")
        cell["state_key"] = canonical({**cell["scope"], "purpose": cell["purpose"]})
        self.repin()
        result = self.run_reference()
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["results"]["result"], cell["quantity"])
        self.assertEqual(result["closing_state"][0]["quantity"], cell["quantity"])

    def test_exact_tagged_codec_and_adapter_scope_validation(self):
        self.assertEqual(encode(QuantityValue(Fraction(1, 3), "Download")), {"value": {"numerator": "1", "denominator": "3"}, "unit": "Download"})
        self.assertEqual(encode(RateValue(Fraction(3, 2), "Download")), rate(Fraction(3, 2), "Download"))
        self.assertEqual(dimensional_amount(quantity(Fraction(1, 2), "Download"), "Download"), QuantityValue(Fraction(1, 2), "Download"))
        fixture = read_json(self.root / "cases/quantities/neutral.json")
        fixture["scope"]["unit"] = "UsageMinute"
        with self.assertRaises(DataError) as raised:
            adapter.quantity_package(fixture, self.reference)
        self.assertEqual(raised.exception.code, "Q_SCOPE_DIMENSION")


if __name__ == "__main__":
    unittest.main()
