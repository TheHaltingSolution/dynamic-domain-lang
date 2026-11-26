"""Native linked signatures preserve opaque kinds named Record.

The manifest fixtures exercise the pure linking boundary, not registry trust.
Build this checkout with pinned Lake before running the native checks.
"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import DataError, loads, write_json
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
from spl_compiler.linker import link_schedule
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target
from Tests.test_fold import schedule
from Tests.test_linking import importing, library


def named(name, *args):
    return {"name": name, "args": list(args)}


IDENTITY = named("Id", named("Record"))


def fixture(annotation="Id<Record>", typ=IDENTITY, extended=False):
    module = library("opaque", "input n:" + annotation + "; define result=n;",
                     parameters=[{"name": "n", "type": deepcopy(typ)}])
    module["descriptor"]["interface"]["exports"][0]["result"] = deepcopy(typ)
    if extended:
        module["source"] = module["source"].replace(
            'schema "spl-data/0.1-draft" {',
            'schema "spl-data/0.1-draft" uses "spl.usage-time/1" {')
    return schedule("input n:" + annotation + '; emit "v"=compute(n);'), {
        "modules": [module], "imports": [importing("opaque")]}


class LinkedIdKindTests(unittest.TestCase):
    def test_native_linked_opaque_kind_values_and_extended_signature(self):
        record = {"name": "Record", "args": [], "fields": [
            ["id", IDENTITY], ["note", named("Text")]]}
        cases = [
            ("Id<Record>", IDENTITY, "original-1", False),
            ("List<Id<Record>>", named("List", IDENTITY), ["a", "b"], False),
            ("{id:Id<Record>,note:Text}", record, {"id": "a", "note": "kept"}, False),
            ("Id<Record>", IDENTITY, "original-1", True),
        ]
        parent = ROOT / ".lake/linked-id"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temporary:
            work = Path(temporary)
            for index, (annotation, typ, original, extended) in enumerate(cases):
                with self.subTest(annotation=annotation, extended=extended):
                    source, manifest = fixture(annotation, typ, extended)
                    checked = check_schedule(link_schedule(parse(source), manifest))
                    inputs = {"n": decode_value(original, checked.types["n"])}
                    expected = normalize_target(evaluate(checked, inputs, {}).to_dict())
                    source_path = work / (str(index) + ".spl")
                    source_path.write_text(source, encoding="utf-8")
                    link_path = work / "manifest.json"
                    bindings = work / "bindings.json"
                    write_json(link_path, manifest)
                    write_json(bindings, {"inputs": {"n": original}, "openings": {}})
                    native_ir = normalize_target(interpret_schedule(source_path, bindings, link=link_path))
                    target = compile_schedule(source_path, work / "Native.lean", link=link_path)
                    native = normalize_target(loads(lean(["--run", target, bindings])))
                    secondary = work / "Secondary.lean"
                    secondary.write_text(emit_module(checked, inputs, {}), encoding="utf-8")
                    python_emitted = normalize_target(loads(lean(["--run", secondary])))
                    for actual in (expected, native_ir, native, python_emitted):
                        self.assertEqual(actual["status"], "calculated", actual)
                        self.assertEqual(actual["emissions"], {"v": original})
                        self.assertEqual(actual["closing"], {})
                        self.assertEqual(actual["diagnostics"], [])

    def test_native_bad_structural_record_and_nonatomic_kind_still_reject(self):
        parent = ROOT / ".lake/linked-id"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temporary:
            work = Path(temporary)
            source, original = fixture()
            source_path = work / "Source.spl"
            source_path.write_text(source, encoding="utf-8")
            malformed = [
                (named("Record"), "FUNCTION_INTERFACE_MISMATCH"),
                ({"name": "Record", "args": [], "fields": "malformed"}, "INVALID_LINK_MANIFEST"),
                (named("Id", named("Record", named("Int"))), "FUNCTION_INTERFACE_MISMATCH"),
                (named("Id", {"name": "Record", "args": [], "fields": []}), "FUNCTION_INTERFACE_MISMATCH"),
                (named("Id", named("Other")), "FUNCTION_INTERFACE_MISMATCH"),
            ]
            for typ, code in malformed:
                with self.subTest(typ=typ):
                    manifest = deepcopy(original)
                    export = manifest["modules"][0]["descriptor"]["interface"]["exports"][0]
                    export["parameters"][0]["type"] = typ
                    export["result"] = typ
                    link_path = work / "manifest.json"
                    write_json(link_path, manifest)
                    # The frontend must reject before any interpreter bindings
                    # or emitted target is evaluated.
                    with self.assertRaises(DataError) as raised:
                        compile_schedule(source_path, work / "Rejected.lean", link=link_path)
                    self.assertEqual(raised.exception.code, code)


if __name__ == "__main__":
    unittest.main()
