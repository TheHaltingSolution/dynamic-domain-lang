"""Finite unit admission, exact controls, both emitters and defensive IR.

No native rebuild is performed here. A coordinator builds this checkout first;
evidence launchers must insert its physical root before importing repository code.
"""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from oracles.usage_conversion import usage_conversion
from spl_compiler import checker, dimensions, emitter, evaluator, lean_tools
from spl_compiler.codecs import DataError, canonical, exact, loads, number, quantity, write_json
from spl_compiler.ir_artifacts import validate_ir_artifact
from spl_compiler.linker import link_schedule
from spl_compiler.model import QuantityValue, RateValue, SPLException, Type
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target
from Tests.test_linking import library, importing
from Tests import test_emitter_memoization as compiled_helpers


ROOT = Path(__file__).resolve().parents[1]
HEADER = 'schedule Usage language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft"'
FEATURE = dimensions.USAGE_FEATURE
RELATION = dimensions.USAGE_RELATION
EVIDENCE_DIR = None
OBSERVATIONS = []


def source(body, features=(FEATURE,)):
    return HEADER + ''.join(' uses ' + json.dumps(item) for item in features) + ' {' + body + '}'


def ast_type(name, *args):
    return {"name": name, "args": list(args)}


MINUTE = ast_type("Quantity", ast_type("UsageMinute"))
HOUR = ast_type("Quantity", ast_type("UsageHour"))


def foreign_fixture(*, usd=False, unused=False, empty_parameter=False, option_parameter=False):
    typ = ast_type("Option", HOUR) if option_parameter else ast_type("List", HOUR) if empty_parameter else MINUTE
    body = ('input n:Option<Quantity<UsageHour>>; define empty:List<Quantity<UsageHour>> = []; define result=get_or(n,sum(empty,item=>item));' if option_parameter else
            'input n:List<Quantity<UsageHour>>; define result=sum(n,item=>item);' if empty_parameter else
            'input n:Quantity<UsageMinute>; define converted=convert_quantity(n,"UsageHour","' + RELATION + '"); '
            + ('define result=USD 1;' if usd else 'define result=converted;'))
    module = library("hours", body, parameters=[{"name": "n", "type": typ}])
    module["source"] = module["source"].replace('schema "spl-data/0.1-draft" {', 'schema "spl-data/0.1-draft" uses "' + FEATURE + '" {')
    module["descriptor"]["interface"]["exports"][0]["result"] = ast_type("Money", ast_type("USD")) if usd else HOUR
    manifest = {"modules": [module], "imports": [importing("hours", local="to_hour")]}
    if unused:
        manifest["imports"][0]["symbols"] = []
    return manifest


def financial(outcome):
    out = normalize_target(outcome)
    return {"status": out["status"], "emissions": out["emissions"], "closing": out["closing"],
            "diagnostics": [row["code"] for row in out["diagnostics"]]}


class UsageAdmissionTests(unittest.TestCase):
    def test_catalog_immutable_scale_authority_and_generic_application(self):
        own = dimensions.admission([FEATURE])
        self.assertEqual(dimensions.UNITS, {"Download", "UsageMinute"})
        self.assertEqual(dimensions.conversion_factor("UsageMinute", "UsageHour", RELATION, own), Fraction(1, 60))
        self.assertEqual(dimensions.conversion_factor("UsageHour", "UsageMinute", RELATION, own), 60)
        minute, hour = dimensions.UNIT_DEFINITIONS[1:]
        with self.assertRaisesRegex(SPLException, "CONVERSION_SCALE_MISMATCH"):
            dimensions.validate_relation(minute, Fraction(59), hour, Fraction(1))
        dimensions.validate_relation(minute, Fraction(120), hour, Fraction(2))
        with self.assertRaisesRegex(SPLException, "UNIT_DEFINITION_MISMATCH"):
            dimensions.validate_relation(minute, Fraction(59), replace(hour, scale=Fraction(59)), Fraction(1))
        for args in [("UsageMinute", "UsageMinute", RELATION), ("Download", "UsageHour", RELATION),
                     ("UsageMinute", "UsageHour", RELATION + ":120-2")]:
            with self.assertRaises(SPLException):
                dimensions.conversion_factor(*args, own)
        for row in [*dimensions.UNIT_DEFINITIONS, *dimensions.CONVERSION_RELATIONS]:
            self.assertEqual(row.pin, hashlib.sha256(json.dumps(row.content, sort_keys=True, separators=(",", ":")).encode()).hexdigest())

    def test_default_wrappers_reject_hour_and_value_equality_ignores_unused_meanings(self):
        meanings = dimensions.meanings([dimensions.admission([FEATURE])])
        for action in [lambda: checker.type_from_ast(HOUR), lambda: quantity("1", "UsageHour"),
                       lambda: evaluator.decode_value({"value": "1", "unit": "UsageHour"}, Type("Quantity", (Type("UsageHour"),))),
                       lambda: QuantityValue(Fraction(1), "UsageHour")]:
            with self.assertRaises((SPLException, DataError)):
                action()
        for action in [lambda: QuantityValue(Fraction(1), "UsageMinute", {}),
                       lambda: dimensions.meanings([{}]),
                       lambda: evaluator.decode_value({"value": "1", "unit": "UsageMinute"}, Type("Quantity", (Type("UsageMinute"),)), context={})]:
            with self.assertRaisesRegex(SPLException, "INVALID_OWNER_CONTEXT"):
                action()
        self.assertEqual(QuantityValue(Fraction(1), "UsageMinute"), QuantityValue(Fraction(1), "UsageMinute", meanings))
        self.assertEqual(RateValue(Fraction(1), "UsageMinute"), RateValue(Fraction(1), "UsageMinute", "USD", meanings))
        self.assertEqual(dimensions.used_unit_definitions(Type("Id", (Type("Quantity"),)), meanings), ())
        with self.assertRaises(SPLException):
            checker.type_from_ast(HOUR, meanings)
        for features in [[FEATURE, FEATURE], [FEATURE + ":unknown"], [True]]:
            with self.assertRaises(SPLException):
                dimensions.admission(features)
            with self.assertRaises(SPLException):
                checker.check_schedule(parse(source('emit "x"=1;', features)))

    def test_per_owner_inference_is_not_lexical_permission(self):
        manifest = foreign_fixture()
        text = source('input n:Quantity<UsageMinute>; define h=to_hour(n); emit "q"=h+h; emit "scale"=h*2.0;', ())
        checked = checker.check_schedule(link_schedule(parse(text), manifest))
        actual = evaluator.evaluate(checked, {"n": {"value": "90", "unit": "UsageMinute"}}, {}).to_dict()
        self.assertEqual(actual["emissions"]["q"], {"value": "3", "unit": "UsageHour"})
        self.assertFalse(checked.admission.features)
        self.assertEqual(checked.meanings.features, (FEATURE,))
        for body in [
            'input n:Quantity<UsageMinute>; define h:Quantity<UsageHour> = to_hour(n); emit "x"=h;',
            'input n:Quantity<UsageMinute>; define h=convert_quantity(n,"UsageHour","' + RELATION + '");',
            'input h:Quantity<UsageHour>; emit "h"=h;',
            'define xs:List<Quantity<UsageHour>> = []; emit "x"=xs;',
            'define x:Option<Quantity<UsageHour>> = none(); emit "x"=x;']:
            with self.subTest(body=body), self.assertRaises(SPLException):
                checker.check_schedule(link_schedule(parse(source(body, ())), manifest))
        contextual = checker.check_schedule(link_schedule(parse(source('emit "x"=to_hour([]);', ())), foreign_fixture(empty_parameter=True)))
        self.assertEqual(evaluator.evaluate(contextual, {}, {}).to_dict()["emissions"]["x"], {"value": "0", "unit": "UsageHour"})

    def test_builtin_and_uses_names_remain_owner_local(self):
        module = library("legacy", 'input n:Ratio; define result=n;', result="Ratio",
                         parameters=[{"name": "n", "type": ast_type("Ratio")}], export="convert_quantity")
        manifest = {"modules": [module], "imports": [importing("legacy", export="convert_quantity", local="convert_quantity")]}
        base = checker.check_schedule(link_schedule(parse(source('emit "v"=convert_quantity(3.0);', ())), manifest))
        self.assertEqual(evaluator.evaluate(base, {}, {}).to_dict()["emissions"]["v"], "3")
        with self.assertRaises(SPLException):
            link_schedule(parse(source('emit "v"=1;')), manifest)
        for body in ['input uses:Ratio; emit "uses"=uses;', 'input uses:Id<uses>; emit "v"={uses:uses,owner_context:uses};']:
            checker.check_schedule(parse(source(body, ())))
        checker.check_schedule(parse(source('emit "v"=1;', ()).replace('schedule Usage ', 'schedule uses ')))
        old = library("legacy", 'input n:Ratio; define result=n;', result="Ratio", parameters=[{"name": "n", "type": ast_type("Ratio")}], export="uses")
        linked = link_schedule(parse(source('emit "v"=uses(2.0);', ())), {"modules": [old], "imports": [importing("legacy", export="uses", local="uses")]})
        self.assertEqual(evaluator.evaluate(checker.check_schedule(linked), {}, {}).to_dict()["emissions"]["v"], "2")

    def test_rejects_dynamic_wrong_endpoint_rate_currency_and_unused_types(self):
        bodies = ['input q:Quantity<UsageMinute>; input t:Text; define h=convert_quantity(q,t,"' + RELATION + '");',
                  'input q:Quantity<UsageMinute>; define h=convert_quantity(q,"UsageMinute","' + RELATION + '");',
                  'input q:Quantity<Download>; define h=convert_quantity(q,"UsageHour","' + RELATION + '");',
                  'input q:Rate<UsageMinute,USD>; define h=convert_quantity(q,"UsageHour","' + RELATION + '");',
                  'input q:Money<USD>; define h=convert_quantity(q,"UsageHour","' + RELATION + '");',
                  'input q:Rate<UsageHour,EUR>;', 'input q:Money<EUR>;',
                  'input q:Quantity<UsageMinute>; define h=convert_quantity(q,"UsageHour","unknown");']
        for body in bodies:
            with self.subTest(body=body), self.assertRaises(SPLException):
                checker.check_schedule(parse(source(body)))
        manifest = foreign_fixture(usd=True, unused=True)
        checked = checker.check_schedule(link_schedule(parse(source('emit "v"=USD 1;', ())), manifest))
        self.assertFalse(checked.admission.features)
        self.assertEqual(checked.meanings.features, (FEATURE,))


class UsageNativeTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(ROOT, lean_tools.ROOT, "Embedded Python must insert this checkout before imports")
        self.assertTrue(Path(checker.__file__).is_relative_to(ROOT))
        self.directory = tempfile.TemporaryDirectory(prefix="spl-usage-")
        self.addCleanup(self.directory.cleanup)
        self.work = Path(self.directory.name)
        self.lean, self.env = lean_tools.lean_environment()
        self.frontend = ROOT / ".lake/build/bin" / ("spl.exe" if os.name == "nt" else "spl")
        self.assertTrue(self.frontend.is_file(), "Coordinated native build required")
        self.counter = 0

    def command(self, args, expected=0):
        result = subprocess.run(list(map(str, args)), cwd=ROOT, env=self.env, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, expected, (result.stdout + result.stderr).decode("utf-8", "replace"))
        self.assertEqual(result.stderr, b"")
        return result.stdout

    def compare(self, label, text, values, *, manifest=None, aot=False):
        self.counter += 1
        work = self.work / str(self.counter)
        work.mkdir()
        src, bindings, generated = work / "Source.spl", work / "bindings.json", work / "Generated.lean"
        src.write_text(text, encoding="utf-8")
        write_json(bindings, values)
        args = []
        ast = parse(text)
        if manifest:
            write_json(work / "link.json", manifest)
            args = ["--link", work / "link.json"]
            ast = link_schedule(ast, manifest)
        checked = checker.check_schedule(ast)
        reference = evaluator.evaluate(checked, values["inputs"], values["openings"]).to_dict()
        self.command([self.frontend, "compile", src, generated, *args])
        self.command([self.frontend, "ir", src, work / "IR.json", *args])
        artifact = loads((work / "IR.json").read_bytes())
        self.assertEqual(validate_ir_artifact(artifact)["execution"], "not_executed")
        outcomes = {"reference": reference,
                    "native_ir": loads(self.command([self.frontend, "interpret", src, bindings, *args])),
                    "native_emitted_lean": loads(self.command([self.lean, "--run", generated, bindings]))}
        decoded = {kind: {name: evaluator.decode_value(value, checked.types[name], context=checked.meanings)
                          for name, value in values[kind].items()} for kind in ("inputs", "openings")}
        mirror = work / "Mirror.lean"
        mirror.write_text(emitter.emit_module(checked, decoded["inputs"], decoded["openings"]), encoding="utf-8")
        outcomes["python_emitted_lean"] = loads(self.command([self.lean, "--run", mirror]))
        if aot:
            helper = compiled_helpers.EmitterMemoizationTests()
            helper.setUp()
            self.addCleanup(helper.doCleanups)
            target = helper.work / "Target.lean"
            target.write_bytes(generated.read_bytes())
            exe = helper.native(target)
            outcomes["native_compiled_target"] = loads(self.command([exe, bindings]))
        for backend, outcome in outcomes.items():
            self.assertEqual(financial(outcome), financial(reference), backend)
        seen = set()
        for node in outcomes["native_ir"]["trace"]:
            self.assertTrue(set(node["dependencies"]) <= seen)
            self.assertNotIn(node["node_id"], seen)
            seen.add(node["node_id"])
        OBSERVATIONS.append({"case": label, "status": reference["status"], "backends": list(outcomes),
                             "ir_format": artifact["format"], "financial": financial(reference),
                             "source_sha256": hashlib.sha256(src.read_bytes()).hexdigest()})
        if EVIDENCE_DIR:
            dest = Path(EVIDENCE_DIR) / label
            dest.mkdir(parents=True, exist_ok=True)
            for path in work.iterdir():
                if path.is_file():
                    (dest / path.name).write_bytes(path.read_bytes())
            write_json(dest / "outcomes.json", outcomes)
        return outcomes, artifact

    def test_original_measurement_price_fraction_signed_inverse_controls(self):
        fixture = json.loads((ROOT / "cases/usage-conversion/neutral.json").read_text())
        for index, (raw, unit, target) in enumerate([("90", "UsageMinute", "UsageHour"), ("150", "UsageMinute", "UsageHour"),
                                                   ("0", "UsageMinute", "UsageHour"), ("1/3", "UsageMinute", "UsageHour"),
                                                   ("-90", "UsageMinute", "UsageHour"), ("1.5", "UsageHour", "UsageMinute")]):
            original = deepcopy(fixture)
            original["source_quantity"].update(value=raw, unit=unit)
            original["target_unit"] = target
            original["price"].update(value="12" if target == "UsageHour" else "0.2", per_unit=target)
            expected = usage_conversion(original)  # Original facts, before typed transport.
            untouched = deepcopy(original)
            text = source(f'input q:Quantity<{unit}>; input price:Rate<{target},USD>; '
                          f'define h=convert_quantity(q,"{target}","{RELATION}"); '
                          f'define back=convert_quantity(h,"{unit}","{RELATION}"); '
                          'emit "original_q"=q; emit "original_price"=price; emit "h"=h; emit "back"=back; emit "earned"=h*price;')
            values = {"inputs": {"q": {"value": number(Fraction(raw)), "unit": unit},
                                  "price": {"value": original["price"]["value"], "per_unit": target, "currency": "USD"}}, "openings": {}}
            outcomes, artifact = self.compare("original-" + str(index), text, values, aot=index in {0, 5})
            out = financial(outcomes["native_ir"])["emissions"]
            self.assertEqual(exact(out["h"]["value"]), expected["converted_quantity"]["value"])
            self.assertEqual(out["h"]["unit"], target)
            self.assertEqual(exact(out["back"]["value"]), Fraction(raw))
            self.assertEqual(exact(out["earned"]), expected["earned"]["value"])
            self.assertEqual(original, untouched)
            self.assertEqual(artifact["format"], "spl-ir/0.2")
            conversion = [row for row in outcomes["native_ir"]["trace"] if row["kind"] == "builtin" and row.get("detail", {}).get("builtin") == "convert_quantity"]
            self.assertTrue(conversion)
            self.assertTrue(all(row["detail"]["relation_id"] == RELATION and row["detail"]["unit_definitions"] for row in conversion))

    def test_foreign_hour_inference_contextual_empty_and_unused_extended_export(self):
        out, artifact = self.compare("foreign-hour", source('input n:Quantity<UsageMinute>; define h=to_hour(n); emit "v"=h+h;', ()),
                                     {"inputs": {"n": {"value": "90", "unit": "UsageMinute"}}, "openings": {}}, manifest=foreign_fixture(), aot=True)
        self.assertEqual(financial(out["reference"])["emissions"]["v"], {"value": "3", "unit": "UsageHour"})
        self.assertEqual(artifact["dimension_admission"]["features"], [])
        self.compare("foreign-empty", source('emit "v"=to_hour([]);', ()), {"inputs": {}, "openings": {}}, manifest=foreign_fixture(empty_parameter=True))
        none, _ = self.compare("foreign-none", source('emit "v"=to_hour(none());', ()), {"inputs": {}, "openings": {}}, manifest=foreign_fixture(option_parameter=True))
        self.assertEqual(financial(none["reference"])["emissions"]["v"], {"value": "0", "unit": "UsageHour"})
        _, unused = self.compare("unused-foreign-usd", source('emit "v"=USD 1;', ()), {"inputs": {}, "openings": {}}, manifest=foreign_fixture(usd=True, unused=True))
        self.assertEqual(unused["format"], "spl-ir/0.2")
        self.assertTrue(unused["dimension_admission"]["signatures"])

    def test_loop_fold_tagged_zero_and_python_memoization_scopes(self):
        text = source('input qs:List<Quantity<UsageMinute>>; input zero:Quantity<UsageHour>; '
                      'define rows=for each q in qs { define h=convert_quantity(q,"UsageHour","' + RELATION + '"); define d=h+h; yield d; }; '
                      'define total=fold qs from zero with s,q { define h=convert_quantity(q,"UsageHour","' + RELATION + '"); define d=h+h; yield s+d; }; '
                      'define empty:List<Quantity<UsageHour>> = []; emit "rows"=rows; emit "total"=total; emit "zero"=sum(empty,h=>h);')
        values = {"inputs": {"qs": [{"value": value, "unit": "UsageMinute"} for value in ("30", "90", "150")],
                              "zero": {"value": "0", "unit": "UsageHour"}}, "openings": {}}
        out, _ = self.compare("loop-fold-zero", text, values, aot=True)
        self.assertEqual(financial(out["reference"])["emissions"], {"rows": [{"value": v, "unit": "UsageHour"} for v in ("1", "3", "5")],
                                                                  "total": {"value": "9", "unit": "UsageHour"}, "zero": {"value": "0", "unit": "UsageHour"}})

    def test_python_emitter_lazy_forward_first_error_and_import_arguments(self):
        cases = [source('require false else "FIRST"; define h=convert_quantity(q,"UsageHour","' + RELATION + '"); input q:Quantity<UsageMinute>;'),
                 source('define doubled=h+h; define h=convert_quantity(q,"UsageHour","' + RELATION + '"); input q:Quantity<UsageMinute>; emit "v"=doubled;'),
                 source('define v=if true then USD 1 else USD 1/0.0; emit "v"=v;')]
        for index, text in enumerate(cases):
            inputs = {"q": {"value": "90", "unit": "UsageMinute"}} if index < 2 else {}
            out, _ = self.compare("memo-parity-" + str(index), text, {"inputs": inputs, "openings": {}})
            if index == 0:
                self.assertEqual(financial(out["reference"])["diagnostics"], ["FIRST"])

    def test_native_typed_ir_owner_signature_grounding_and_json_shape_preflight(self):
        fixtures = {
            "extended": source('input q:Quantity<UsageMinute>; define h=convert_quantity(q,"UsageHour","' + RELATION + '"); emit "v"=h;'),
            "foreign": source('input n:Quantity<UsageMinute>; define h=to_hour(n); emit "v"=h+h;', ()),
            "unused": source('emit "v"=USD 1;', ()),
        }
        for name, text in fixtures.items():
            (self.work / (name + ".spl")).write_text(text, encoding="utf-8")
        write_json(self.work / "foreign.json", foreign_fixture())
        write_json(self.work / "unused.json", foreign_fixture(usd=True, unused=True))
        legacy = library("legacy", 'input n:Quantity<UsageMinute>; define result=n;', parameters=[{"name": "n", "type": MINUTE}], export="convert_quantity")
        legacy["descriptor"]["interface"]["exports"][0]["result"] = MINUTE
        write_json(self.work / "legacy.json", {"modules": [legacy], "imports": [importing("legacy", export="convert_quantity", local="convert_quantity")]})
        (self.work / "legacy.spl").write_text(source('input n:Quantity<UsageMinute>; emit "v"=convert_quantity(n);', ()), encoding="utf-8")
        self.command([self.frontend, "ir", self.work / "legacy.spl", self.work / "legacy-ir.json", "--link", self.work / "legacy.json"])
        helper = compiled_helpers.EmitterMemoizationTests()
        helper.setUp()
        self.addCleanup(helper.doCleanups)
        driver = helper.work / "Hostile.lean"
        driver.write_bytes((ROOT / "Tests/SPLUsageUnits.lean").read_bytes())
        executable = helper.native(driver, link_template="spl")
        arguments = [self.work / "extended.spl", self.work / "foreign.spl", self.work / "foreign.json",
                     self.work / "unused.spl", self.work / "unused.json", self.work / "legacy-ir.json"]
        raw = self.command([executable, *arguments])
        rows = [loads(line) for line in raw.splitlines()]
        self.assertEqual(len([row for row in rows if row.get("stage") == "typed_ir_preflight"]), 19)
        self.assertEqual(len([row for row in rows if row.get("stage") == "artifact_shape_preflight"]), 2)
        self.assertEqual(len([row for row in rows if row.get("stage") == "catalog_validation"]), 3)
        catalog = next(row for row in rows if row["case"] == "catalog-payload")
        expected = [dict(row.content, pin=row.pin) for row in dimensions.UNIT_DEFINITIONS]
        self.assertEqual(catalog["units"], expected)
        OBSERVATIONS.extend(rows)
        if EVIDENCE_DIR:
            dest = Path(EVIDENCE_DIR) / "hostile-ir"
            dest.mkdir(parents=True, exist_ok=True)
            for path in self.work.iterdir():
                if path.is_file():
                    (dest / path.name).write_bytes(path.read_bytes())
            (dest / "native-stdout.jsonl").write_bytes(raw)
            for path in helper.work.iterdir():
                if path.is_file():
                    (dest / path.name).write_bytes(path.read_bytes())

    def test_serialized_v1_v2_shape_and_signature_qualifiers(self):
        out, artifact = self.compare("artifact-qualifiers", source('input n:Quantity<UsageMinute>; define h=to_hour(n); emit "v"=h;', ()),
                                     {"inputs": {"n": {"value": "90", "unit": "UsageMinute"}}, "openings": {}}, manifest=foreign_fixture())
        changes = [lambda p: p.update(format="spl-ir/0.1"),
                   lambda p: p["dimension_admission"].update(unit_definitions=[]),
                   lambda p: p["dimension_admission"].update(factor="1/59"),
                   lambda p: p["dimension_admission"]["owners"].append(deepcopy(p["dimension_admission"]["owners"][0])),
                   lambda p: p["dimension_admission"]["signatures"].append(deepcopy(p["dimension_admission"]["signatures"][0])),
                   lambda p: p["dimension_admission"]["signatures"][0].update(label="unknown-owner"),
                   lambda p: p["dimension_admission"].update(signatures=None)]
        for change in changes:
            invalid = deepcopy(artifact)
            change(invalid)
            with self.assertRaisesRegex(DataError, "Invalid|Unexpected|Catalog|Malformed"):
                validate_ir_artifact(invalid)

    def test_ordinary_record_metadata_spellings_are_data_in_shape_preflight(self):
        text = source('emit "record"={uses:1,admission:"ordinary",owner_context:2,meta:{owner_context:3,uses:4}};', ())
        src, artifact = self.work / "Record.spl", self.work / "record-ir.json"
        src.write_text(text, encoding="utf-8")
        self.command([self.frontend, "ir", src, artifact])
        value = loads(artifact.read_bytes())
        self.assertEqual(value["format"], "spl-ir/0.1")
        self.assertEqual(validate_ir_artifact(value), {"status": "shape_checked", "stage": "ir_artifact_preflight", "execution": "not_executed"})
        OBSERVATIONS.append({"case": "ordinary-record-metadata-spellings", "stage": "artifact_shape_preflight",
                             "status": "shape_checked", "execution": "not_executed"})


if __name__ == "__main__":
    unittest.main()
