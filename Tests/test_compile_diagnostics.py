"""Located, staged diagnostics through the authoritative SPL frontend."""
from pathlib import Path
import tempfile
import unittest

from spl_compiler.certification import default_link
from spl_compiler.codecs import write_json
from spl_compiler.lean_tools import ROOT, FrontendDiagnostic, compile_schedule, export_ir, preflight_schedule


HEADER = 'schedule Diagnostic language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'


class CompileDiagnosticsTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="spl-compile-diagnostics-")
        self.addCleanup(directory.cleanup)
        self.work = Path(directory.name)

    def write_source(self, *lines):
        path = self.work / "Schedule.spl"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        return path

    def assert_failure(self, action, code, stage, path, *, line=None, contains=None):
        with self.assertRaises(FrontendDiagnostic) as caught:
            action()
        result = caught.exception.diagnostic()
        self.assertEqual(result["code"], code, result)
        self.assertEqual(result["stage"], stage, result)
        self.assertEqual(result["pointer"], str(path), result)
        if line is not None:
            self.assertEqual(result["span"]["line"], line, result)
        if contains is not None:
            self.assertIn(contains, result["message"], result)

    def test_core_parse_failure_reports_real_line_and_emits_no_artifact(self):
        source = self.write_source(HEADER, "", "  input p: Money<USD;", "}")
        output = self.work / "Settlement.lean"
        self.assert_failure(lambda: compile_schedule(source, output), "SYNTAX_ERROR", "source", source, line=3)
        self.assertFalse(output.exists())

    def test_readable_metadata_failure_points_to_using_footer(self):
        authored = (ROOT / "cases/certification/aggregate-readable.spl").read_text(encoding="utf-8")
        lines = authored.replace('Using language "', 'Using language 9 "', 1).splitlines()
        line = next(index for index, text in enumerate(lines, 1) if text.strip().startswith("Using "))
        source = self.write_source(*lines)
        self.assert_failure(lambda: preflight_schedule(source), "SYNTAX_ERROR", "source", source, line=line)

    def test_type_arity_and_unresolved_names_report_the_offending_declaration(self):
        source = self.write_source(HEADER, "", "  input receipt: List<Money<USD>,Text>;", "}")
        self.assert_failure(lambda: preflight_schedule(source), "TYPE_ARITY", "type", source, line=3, contains="List")
        source = self.write_source(HEADER, "  define value: Wallet = USD 0;", "}")
        self.assert_failure(lambda: preflight_schedule(source), "UNSUPPORTED_TYPE", "unsupported", source,
                            line=2, contains="Wallet")
        source = self.write_source(HEADER, "  define value = missing_price;", "}")
        self.assert_failure(lambda: preflight_schedule(source), "UNRESOLVED_NAME_OR_CYCLE", "type", source,
                            line=2, contains="missing_price")

    def test_conversion_requires_feature_admission_of_the_calling_owner(self):
        source = self.write_source(HEADER, "  input duration: Quantity<UsageMinute>;",
                                   '  define hours = convert_quantity(duration, "UsageHour", "spl.usage-time/1:minute-hour");', "}")
        output = self.work / "ir.json"
        self.assert_failure(lambda: export_ir(source, output), "UNSUPPORTED_BUILTIN", "unsupported", source,
                            line=3, contains='uses "spl.usage-time/1"')
        self.assertFalse(output.exists())

    def test_link_reports_unresolved_exact_reference_or_export(self):
        source = ROOT / "cases/certification/aggregate-readable.spl"
        link = self.work / "Link.json"
        manifest = default_link()
        imported = manifest["imports"][0]
        reference = imported["module_ref"]
        label = reference["id"] + "@" + reference["revision"]
        write_json(link, {**manifest, "modules": []})
        self.assert_failure(lambda: preflight_schedule(source, link=link), "UNRESOLVED_MODULE", "link", link,
                            contains=label)
        imported["symbols"][0]["export"] = "unpublished_rounding"
        write_json(link, manifest)
        self.assert_failure(lambda: export_ir(source, self.work / "ir.json", link=link), "UNRESOLVED_EXPORT", "link", link,
                            contains="unpublished_rounding")


if __name__ == "__main__":
    unittest.main()
