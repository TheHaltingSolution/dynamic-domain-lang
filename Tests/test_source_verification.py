"""Exercise the independent source check against actual native elaboration."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from spl_compiler.certification import default_link
from spl_compiler.codecs import DataError, file_digest, read_json, write_json
from spl_compiler.lean_tools import ROOT, export_ir
from spl_compiler.modules import linking_manifest, resolve_module
from spl_compiler.source_verification import check_native_ir, check_source


class SourceVerificationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="spl-source-check-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)

    def ir(self, source, link=None):
        return read_json(export_ir(source, self.work / "native.json", link=link))

    def test_readable_stateful_and_multisettlement_source(self):
        for relative in ("cases/sv/rq07-readable.spl", "cases/readable-multi/two-participants-readable.spl"):
            with self.subTest(relative=relative):
                source = ROOT / relative
                checked = check_source(source)
                self.assertEqual(check_native_ir(checked, self.ir(source))["status"], "source_ir_matched")

    def test_altered_translation_and_fabricated_types_do_not_match(self):
        source = ROOT / "cases/certification/aggregate-readable.spl"
        link = self.work / "Link.json"
        write_json(link, default_link())
        checked = check_source(source, link=link)
        valid = self.ir(source, link)
        self.assertEqual(check_native_ir(checked, valid)["status"], "source_ir_matched")

        changed = self.work / "Changed.spl"
        changed.write_bytes(source.read_bytes().replace(b"50%", b"40%"))
        with self.assertRaises(DataError) as wrong_translation:
            check_native_ir(checked, self.ir(changed, link))
        self.assertEqual(wrong_translation.exception.code, "SOURCE_IR_MISMATCH")
        self.assertTrue(wrong_translation.exception.pointer.endswith("/value"))

        false_type = deepcopy(valid)
        input_decl = next(d for d in false_type["declarations"] if d["kind"] == "input")
        input_decl["meta"]["type"] = {"kind": "atom", "name": "Ratio"}
        with self.assertRaises(DataError) as wrong_type:
            check_native_ir(checked, false_type)
        self.assertEqual(wrong_type.exception.code, "SOURCE_IR_MISMATCH")
        self.assertTrue(wrong_type.exception.pointer.endswith("/meta/type"))

    def test_embedded_link_source_changes_and_repins_are_distinguished(self):
        source = ROOT / "cases/certification/aggregate-readable.spl"
        link = self.work / "Link.json"
        manifest = default_link()
        write_json(link, manifest)
        checked = check_source(source, link=link)
        module = manifest["modules"][0]
        module["source"] = module["source"].replace('quantize(value, quantum, "half_even")',
                                                      'quantize(value, quantum, "floor")')
        write_json(link, manifest)
        with self.assertRaises(DataError) as stale:
            check_source(source, link=link)
        self.assertEqual(stale.exception.code, "SOURCE_LINK_PIN_MISMATCH")
        self.assertEqual(stale.exception.diagnostic()["stage"], "link")
        self.assertEqual(stale.exception.pointer, str(link))

        module["descriptor"]["source"]["sha256"] = sha256(module["source"].encode("utf-8")).hexdigest()
        write_json(link, manifest)
        new_source = check_source(source, link=link)
        new_ir = self.ir(source, link)
        self.assertEqual(check_native_ir(new_source, new_ir)["status"], "source_ir_matched")
        with self.assertRaises(DataError) as changed_policy:
            check_native_ir(checked, new_ir)
        self.assertEqual(changed_policy.exception.code, "SOURCE_IR_MISMATCH")

    def test_owner_scoped_link_and_extended_types(self):
        root = ROOT / "cases/usage-conversion"
        descriptor = root / "inferred-import-module.json"
        registration = read_json(descriptor)
        reference = {key: registration[key] for key in ("id", "revision")}
        reference.update(locator=descriptor.relative_to(ROOT).as_posix(), sha256=file_digest(descriptor))
        resolved = resolve_module(reference, ROOT)
        source = resolved.source_path
        link = self.work / "Link.json"
        write_json(link, linking_manifest(resolved))
        checked = check_source(source, link=link)
        self.assertEqual(check_native_ir(checked, self.ir(source, link))["status"], "source_ir_matched")

    def test_ordered_fold_rule_priority_and_contextual_types_in_one_schedule(self):
        source = self.work / "Combination.spl"
        source.write_text('''schedule Combination language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {
  input receipts: List<{oid: Id<Receipt>, sequence: Int, gross: Money<USD>}>;
  opening balance: Money<USD> from "prior-balance";
  define unused: List<{oid: Id<Receipt>, sequence: Int, gross: Money<USD>}> = [];
  define rows = concat(receipts, unused);
  define receipts_by_id = make_map(rows, row_key => row_key.oid, row_val => row_val.gross);
  define accumulated = ordered_fold rows from balance by order_row => order_row.sequence
    identified by id_row => id_row.oid ties "reject" with total, row {
      define recorded: Option<Money<USD>> = lookup(receipts_by_id, row.oid);
      define gross = require_some(recorded, "UNKNOWN_RECEIPT");
      require gross >= USD 0 else "NEGATIVE_GROSS";
      yield total + gross;
    };
  define adjusted: Money<USD> = choose priority {
    rule "floor" priority 1 when accumulated < USD 0 => USD 0;
    rule "cap" priority 2 when accumulated > USD 100 => USD 100;
    otherwise "standard" => accumulated;
  };
  closing balance = adjusted;
  emit "balance" = adjusted;
}''', encoding="utf-8")
        checked = check_source(source)
        native = self.ir(source)
        self.assertEqual(check_native_ir(checked, native)["status"], "source_ir_matched")
        for name, mutation in (("accumulated", lambda n: n["order"].update(ties="unordered")),
                               ("adjusted", lambda n: n["arms"][0].update(priority=2))):
            with self.subTest(name=name):
                changed = deepcopy(native)
                declaration = next(d for d in changed["declarations"] if d.get("name") == name)
                mutation(declaration["body"])
                with self.assertRaises(DataError) as mismatch:
                    check_native_ir(checked, changed)
                self.assertEqual(mismatch.exception.code, "SOURCE_IR_MISMATCH")


if __name__ == "__main__":
    unittest.main()
