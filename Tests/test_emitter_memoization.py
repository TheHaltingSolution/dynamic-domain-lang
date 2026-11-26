"""Compiled emitted definitions: demand order and fresh, per-call memo cells.

Temporary C/native targets use the pinned toolchain and existing runtime objects;
no repository build outputs or historical generated financial targets are changed.
An external evidence launcher may supply OLD_FRONTEND for a dated comparison.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import loads, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT, lean_environment
from spl_compiler.linker import link_schedule
from spl_compiler.model import SPLException
from spl_compiler.parser import parse
from Tests.test_fold import schedule
from Tests.test_indexed_sv import financial, original_cases, project_original, raw_cases
from Tests.test_linking import library, importing
from scripts.spl_benchmark import receipt_probe
from spl_compiler.readable import is_readable, parse_readable


OLD_FRONTEND = None
HISTORICAL_TARGET_DIR = None
EVIDENCE_DIR = None
OBSERVATIONS = []
PROMOTED = [
    ("cases/sv/sv01.spl", "Demos/SV.lean", "compile", "spl_sv", "cases/sv/bindings.json"),
    ("cases/lg/lg01.spl", "Demos/LG.lean", "compile", "spl_lg", "cases/lg/bindings.json"),
    ("cases/sv/rq07.spl", "Demos/RQ07.lean", "compile", "spl_rq07", "cases/rq07/bindings.json"),
    ("cases/sv/sv01-readable.spl", "Demos/SVReadable.lean", "compile", "spl_sv_readable", "cases/sv/readable/bindings.json"),
    ("cases/lg/lg01-readable.spl", "Demos/LGReadable.lean", "compile", "spl_lg_readable", "cases/lg/readable/bindings.json"),
    ("cases/sv/rq07-readable.spl", "Demos/RQ07Readable.lean", "compile", "spl_rq07_readable", "cases/rq07/readable/bindings.json"),
    ("cases/sv/sv01.spl", "Demos/SVBenchmarkLibrary.lean", "compile-library", None, None),
    ("cases/sv/sv01-indexed.spl", "Demos/SVIndexed.lean", "compile", "spl_sv_indexed", None),
]


class EmitterMemoizationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.lean, self.env = lean_environment()
        self.env["LEAN_PATH"] = str(self.work) + os.pathsep + self.env["LEAN_PATH"]
        self.frontend = ROOT / ".lake/build/bin" / ("spl.exe" if os.name == "nt" else "spl")
        self.assertTrue(self.frontend.is_file())
        self.sequence = 0

    def command(self, args, *, timeout=90):
        process = subprocess.run(list(map(str, args)), cwd=self.work, env=self.env,
                                 capture_output=True, timeout=timeout)
        self.assertEqual(process.returncode, 0, (process.stdout + process.stderr).decode("utf-8", "replace"))
        self.assertEqual(process.stderr, b"")
        return process.stdout

    def native(self, source, *, extra_objects=(), module=False, count_groups=False, link_template="spl_sv"):
        """Compile only temporary sources; reuse Lake's exact runtime link closure."""
        c = source.with_suffix(".c")
        args = [self.lean, "-R", self.work, "-c", c]
        if module:
            args += ["-o", source.with_suffix(".olean")]
        self.command([*args, source])
        if count_groups:
            # Counter exists only in this disposable generated C, never finance
            # source, emitted production Lean, or the shared runtime object.
            text = c.read_text(encoding="utf-8")
            symbols = set(re.findall(r"\b(\w*SPL_groupValues)\(", text))
            self.assertEqual(len(symbols), 1)
            symbol = symbols.pop()
            c.with_suffix(".original.c").write_bytes(c.read_bytes())
            text = re.sub(r"\b" + re.escape(symbol) + r"\(", "memo_counted_group(", text)
            write_call = "_write" if os.name == "nt" else "write"
            text += ('\nextern int ' + write_call + '(int, const void*, unsigned int);\nextern lean_object* ' + symbol + '(lean_object*, lean_object*);\n'
                     'lean_object* memo_counted_group(lean_object* a, lean_object* b) {\n'
                     '  const char marker[] = "MEMO_GROUP_BUILD\\n";\n'
                     '  (void)' + write_call + '(2, marker, sizeof(marker)-1);\n'
                     '  return ' + symbol + '(a, b);\n}\n')
            c.write_text(text, encoding="utf-8")
        leanc = Path(self.lean).with_name("leanc.exe" if os.name == "nt" else "leanc")
        obj = source.with_suffix(".o")
        self.command([leanc, "-O3", "-c", "-o", obj, c])
        if module:
            return obj
        executable = source.with_suffix(".exe" if os.name == "nt" else "")
        suffix = ".exe" if os.name == "nt" else ""
        template = ROOT / ".lake/build/bin" / (link_template + suffix + ".rsp")
        self.assertTrue(template.is_file(), "Build historical spl_sv link closure first")
        arguments = [json.loads(line) for line in template.read_text().splitlines() if line.strip()]
        arguments = [str(obj), *map(str, extra_objects), *arguments[1:]]
        response = source.with_suffix(".rsp")
        response.write_text("\n".join(json.dumps(arg) for arg in arguments), encoding="utf-8")
        clang = Path(self.lean).with_name("clang.exe" if os.name == "nt" else "clang")
        self.command([clang, "-o", executable, "@" + str(response)])
        return executable

    def compare(self, label, body, values, expected, *, manifest=None):
        source = self.work / "Case.spl"
        source.write_text(schedule(body), encoding="utf-8")
        binding = self.work / "bindings.json"
        write_json(binding, values)
        link_args = []
        checked = parse(source.read_text())
        if manifest is not None:
            link = self.work / "link.json"
            write_json(link, manifest)
            link_args = ["--link", link]
            checked = link_schedule(checked, manifest)
        reference = evaluate(check_schedule(checked), values["inputs"], values["openings"]).to_dict()
        self.assertEqual(financial(reference), expected)
        outcomes = {"reference": reference}
        for origin, frontend in [("new", self.frontend), *([("old", Path(OLD_FRONTEND))] if OLD_FRONTEND else [])]:
            generated = self.work / (origin.title() + ".lean")
            self.command([frontend, "compile", source, generated, *link_args])
            text = generated.read_text(encoding="utf-8")
            if origin == "new" and "define " in body:
                self.assertIn("Thunk.mk", text)
                self.assertIn(".get", text)
                self.assertNotIn("Thunk.pure", text)
            executable = self.native(generated)
            outcomes[origin + "_compiled"] = loads(self.command([executable, binding]))
        outcomes["native_ir"] = loads(self.command([self.frontend, "interpret", source, binding, *link_args]))
        for origin, outcome in outcomes.items():
            self.assertEqual(financial(outcome), expected, origin)
        self.record(label, source, values, outcomes)

    def record(self, label, source, values, outcomes):
        observation = {"case": label, "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                       "backends": list(outcomes), "financial": {k: financial(v) for k, v in outcomes.items()},
                       "old_emitter_comparison": "executed" if OLD_FRONTEND else "not_executed_unavailable",
                       "legacy_target_role": "historical_pre_memo_archive" if HISTORICAL_TARGET_DIR else "current_legacy_source_target"}
        OBSERVATIONS.append(observation)
        if EVIDENCE_DIR:
            destination = Path(EVIDENCE_DIR) / label
            destination.mkdir(parents=True, exist_ok=True)
            for path in self.work.iterdir():
                if path.suffix in {".lean", ".spl", ".c", ".rsp", ".exe", ".json"}:
                    (destination / path.name).write_bytes(path.read_bytes())
            write_json(destination / "values.json", values)
            write_json(destination / "outcomes.json", outcomes)

    def test_forward_dependency_and_repeated_references(self):
        self.compare("forward-repeated", 'input x:Int; define twice=later+later; define later=x*2; emit "result"=twice;',
                     {"inputs": {"x": "7"}, "openings": {}},
                     {"status": "calculated", "emissions": {"result": "28"}, "closing": {}, "diagnostics": []})

    def test_lazy_branches_and_declaration_first_failure(self):
        cases = [
            ('require if true then true else bad == 0.0 else "BRANCH"; require false else "STOP"; define bad=1.0/0.0;', "STOP"),
            ('require false else "EARLY"; define bad=1.0/0.0;', "EARLY"),
            ('define bad=1.0/0.0; require false else "LATE";', "DIVISION_BY_ZERO"),
            ('define first=later+1.0; require false else "MIDDLE"; define later=1.0/0.0;', "DIVISION_BY_ZERO"),
        ]
        for index, (body, code) in enumerate(cases):
            with self.subTest(code=code, index=index):
                self.compare("first-failure-" + str(index), body + ' emit "result"=0;',
                             {"inputs": {}, "openings": {}},
                             {"status": "blocked", "emissions": {}, "closing": {}, "diagnostics": [code]})

    def test_loop_and_fold_scopes_get_fresh_input_dependent_caches(self):
        self.compare("loop-fold", '''input xs:List<Int>;
            define rows=for each x in xs { define twice=x+x; define repeated=twice+twice; yield repeated; };
            define total=fold xs from 0 with s,x { define twice=x+x; define repeated=twice+twice; yield s+repeated; };
            emit "rows"=rows; emit "total"=total;''', {"inputs": {"xs": ["1", "3", "7"]}, "openings": {}},
            {"status": "calculated", "emissions": {"rows": ["4", "12", "28"], "total": "44"}, "closing": {}, "diagnostics": []})

    def test_deferred_captures_preserve_option_choose_and_short_circuit_demand(self):
        expressions = [
            'get_or(some(7.0),future)',
            'choose unique { when true => 7.0; when false => future; }',
            'if false and future > 0.0 then 1.0 else 7.0',
            'if true or future > 0.0 then 7.0 else 1.0',
        ]
        for index, expression in enumerate(expressions):
            with self.subTest(expression=expression):
                self.compare("deferred-capture-" + str(index),
                             'define selected=' + expression + '; require false else "STOP"; '
                             'define future=1.0/0.0; emit "result"=selected;',
                             {"inputs": {}, "openings": {}},
                             {"status": "blocked", "emissions": {}, "closing": {}, "diagnostics": ["STOP"]})

    def test_nested_disjoint_and_callee_scopes_keep_capture_values_local(self):
        parameters = [{"name": "n", "type": {"name": "Int", "args": []}}]
        callee = library("scoped", 'input n:Int; define later=n*3; define result=later+n;', parameters=parameters)
        manifest = {"modules": [callee], "imports": [importing("scoped", local="compute")]}
        self.compare("scoped-captures", '''input n:Int;
            define original=n+n;
            define rows=for each outer in [2,5] {
              define later=outer*2;
              define nested=for each child in [1,3] { define twice=child+child; yield twice+later; };
              yield nested;
            };
            define total=fold [2,5] from n with s,event { define later=event*2; yield s+later; };
            emit "original"=original; emit "rows"=rows; emit "total"=total;
            emit "call"=compute(n); emit "other_call"=compute(3);''',
            {"inputs": {"n": "10"}, "openings": {}},
            {"status": "calculated", "emissions": {"original": "20", "rows": [["6", "10"], ["12", "16"]],
             "total": "24", "call": "40", "other_call": "12"}, "closing": {}, "diagnostics": []}, manifest=manifest)
        # Iterator/input and fold/input name reuse is outside the language's
        # admitted lexical scopes. Both frontends must reject it before emission.
        for index, body in enumerate([
            'input n:Int; define rows=for each n in [1] { yield n; }; emit "x"=rows;',
            'input n:Int; define total=fold [1] from 0 with s,n { yield s+n; }; emit "x"=total;',
        ]):
            with self.subTest(forbidden_scope=index):
                with self.assertRaises(SPLException) as error:
                    check_schedule(parse(schedule(body)))
                self.assertEqual(error.exception.code, "DUPLICATE_NAME")
                source = self.work / "ForbiddenScope.spl"
                source.write_text(schedule(body), encoding="utf-8")
                process = subprocess.run([str(self.frontend), "check", str(source)], cwd=self.work,
                                         env=self.env, capture_output=True, timeout=90)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(process.stderr, b"")
                self.assertEqual(loads(process.stdout)["diagnostics"][0]["code"], "DUPLICATE_NAME")

    def test_native_library_error_cache_is_fresh_between_independent_inputs(self):
        source = self.work / "FreshError.spl"
        source.write_text(schedule('input divisor:Ratio; define quotient=10.0/divisor; '
                                   'define repeated=quotient+quotient; emit "result"=repeated;'), encoding="utf-8")
        library_path = self.work / "FreshErrorLibrary.lean"
        standalone = self.work / "FreshErrorStandalone.lean"
        self.command([self.frontend, "compile-library", source, library_path])
        self.command([self.frontend, "compile", source, standalone])
        main = re.search(r"  (SPL\.Bindings\.runMain .+) args\n", standalone.read_text(encoding="utf-8")).group(1)
        driver = self.work / "FreshErrorDriver.lean"
        driver.write_text('import FreshErrorLibrary\ndef main (args : List String) : IO UInt32 := do\n'
                          '  for path in args do\n    let _ ← ' + main + ' [path]\n  return 0\n', encoding="utf-8")
        obj = self.native(library_path, module=True)
        executable = self.native(driver, extra_objects=[obj])
        values = [{"inputs": {"divisor": divisor}, "openings": {}} for divisor in ("0", "2", "5", "0", "2")]
        paths = [self.write_binding("fresh-error-" + str(index), value) for index, value in enumerate(values)]
        outcomes = [loads(line) for line in self.command([executable, *paths]).splitlines()]
        self.assertEqual(len(outcomes), len(values))
        checked = check_schedule(parse(source.read_text(encoding="utf-8")))
        for index, (value, outcome) in enumerate(zip(values, outcomes)):
            reference = evaluate(checked, value["inputs"], {}).to_dict()
            self.assertEqual(financial(outcome), financial(reference), index)
        self.assertEqual([financial(outcome)["diagnostics"] for outcome in outcomes],
                         [["DIVISION_BY_ZERO"], [], [], ["DIVISION_BY_ZERO"], []])
        self.assertEqual(outcomes[1]["emissions"], outcomes[4]["emissions"])

    def test_imported_pure_function_caches_are_fresh_per_call_and_keep_argument_errors(self):
        parameter = [{"name": "n", "type": {"name": "Int", "args": []}}]
        inner = library("inner", 'input n:Int; define a=n*2; define result=a+a;', parameters=parameter)
        outer = library("outer", 'input n:Int; define a=twice(n); define result=a+a;', parameters=parameter,
                        imports=[importing("inner", local="twice")])
        manifest = {"modules": [inner, outer], "imports": [importing("outer", local="compute")]}
        self.compare("imported-fresh", 'define a=compute(2); define b=compute(5); emit "a"=a; emit "b"=b;',
                     {"inputs": {}, "openings": {}},
                     {"status": "calculated", "emissions": {"a": "16", "b": "40"}, "closing": {}, "diagnostics": []}, manifest=manifest)
        strict = library("strict", 'input n:Ratio; define result=n+n;', result="Ratio",
                         parameters=[{"name": "n", "type": {"name": "Ratio", "args": []}}])
        self.compare("imported-argument-error", 'emit "x"=compute(1.0/0.0);',
                     {"inputs": {}, "openings": {}},
                     {"status": "blocked", "emissions": {}, "closing": {}, "diagnostics": ["DIVISION_BY_ZERO"]},
                     manifest={"modules": [strict], "imports": [importing("strict", local="compute")]})

    def test_isolated_native_group_build_counter(self):
        source = ROOT / "cases/sv/sv01-indexed.spl"
        values = receipt_probe(10, 8)
        binding = self.write_binding("counter-bindings", values)
        outcomes = {}
        counts = {}
        for origin, frontend in [("new", self.frontend), *([("old", Path(OLD_FRONTEND))] if OLD_FRONTEND else [])]:
            generated = self.work / (origin.title() + "Counter.lean")
            self.command([frontend, "compile", source, generated])
            executable = self.native(generated, count_groups=True)
            process = subprocess.run([str(executable), str(binding)], cwd=self.work, env=self.env,
                                     capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 0)
            markers = process.stderr.splitlines()
            self.assertTrue(all(line == b"MEMO_GROUP_BUILD" for line in markers))
            counts[origin] = len(markers)
            outcomes[origin + "_instrumented_compiled"] = loads(process.stdout)
        self.assertEqual(counts["new"], 2, "One receipt and one cost grouping per settlement")
        if "old" in counts:
            self.assertGreater(counts["old"], counts["new"])
            self.assertEqual(financial(outcomes["old_instrumented_compiled"]), financial(outcomes["new_instrumented_compiled"]))
        self.record("isolated-group-build-counter", source, values, outcomes)
        OBSERVATIONS[-1]["observed_group_build_calls"] = counts
        OBSERVATIONS[-1]["instrumentation_scope"] = "Disposable generated-C external group-call wrapper; no production counter or timing claim"

    def test_native_library_repeated_financial_calls_with_varied_inputs_and_openings(self):
        """Library remains verbatim native output, imported by a separate driver."""
        source = ROOT / "cases/sv/sv01.spl"
        library_path = self.work / "MemoLibrary.lean"
        standalone = self.work / "Standalone.lean"
        self.command([self.frontend, "compile-library", source, library_path])
        self.command([self.frontend, "compile", source, standalone])
        self.assertNotIn("\ndef main", library_path.read_text(encoding="utf-8"))
        main = re.search(r"  (SPL\.Bindings\.runMain .+) args\n", standalone.read_text(encoding="utf-8")).group(1)
        driver = self.work / "Driver.lean"
        driver.write_text('import MemoLibrary\ndef main (args : List String) : IO UInt32 := do\n'
                          '  for path in args do\n    let _ ← ' + main + ' [path]\n  return 0\n', encoding="utf-8")
        obj = self.native(library_path, module=True)
        executable = self.native(driver, extra_objects=[obj])
        cases = []
        for label, data in original_cases():
            values, expected, _ = project_original(data)
            cases.append((label, values, expected))
        original = next(original_cases())[1]
        for index, opening in enumerate(("0", "1000", "3", "0")):
            data = deepcopy(original)
            data["package"]["state_cells"][0]["quantity"] = opening
            values, expected, _ = project_original(data)
            cases.append(("varied-opening-" + str(index) + "-" + opening, values, expected))
        for label, values in list(raw_cases()):
            cases.append((label, values, None))
        paths = [self.write_binding("call-" + str(index), values) for index, (_, values, _) in enumerate(cases)]
        observations = [loads(line) for line in self.command([executable, *paths]).splitlines()]
        self.assertEqual(len(observations), len(cases))
        from scripts.spl_mixed_benchmark import check_target
        for (label, values, expected), path, outcome in zip(cases, paths, observations):
            old = loads(self.command([self.comparison_target("spl_sv"), path]))
            self.assertEqual(financial(outcome), financial(old), label)
            if expected is not None:
                check_target(outcome, expected)
            role = "historical_compiled" if HISTORICAL_TARGET_DIR else "current_legacy_source_compiled"
            self.record("library-" + label, source, values, {"new_compiled_library": outcome, role: old})

    def comparison_target(self, name):
        directory = Path(HISTORICAL_TARGET_DIR) if HISTORICAL_TARGET_DIR else self.frontend.parent
        target = directory / (name + (".exe" if os.name == "nt" else ""))
        self.assertTrue(target.is_file())
        return target

    def test_promoted_modules_equal_fresh_authoritative_native_emission(self):
        for source, destination, mode, _, _ in PROMOTED:
            with self.subTest(destination=destination):
                fresh = self.work / "Fresh.lean"
                self.command([self.frontend, mode, ROOT / source, fresh])
                self.assertEqual(fresh.read_bytes(), (ROOT / destination).read_bytes())
                OBSERVATIONS.append({"case": "fresh-" + destination, "status": "passed", "mode": mode,
                                     "source_sha256": hashlib.sha256((ROOT / source).read_bytes()).hexdigest(),
                                     "generated_sha256": hashlib.sha256(fresh.read_bytes()).hexdigest()})

    def test_promoted_financial_targets_match_full_reference_ir_and_dated_baseline(self):
        for source, _, _, target, bindings in PROMOTED[:6]:
            with self.subTest(target=target):
                values = loads((ROOT / bindings).read_bytes())
                source_path = ROOT / source
                text = source_path.read_text(encoding="utf-8")
                parsed = parse_readable(text) if is_readable(text) else parse(text)
                reference = evaluate(check_schedule(parsed), values["inputs"], values["openings"]).to_dict()
                outcomes = {"reference": reference,
                            "current_compiled": loads(self.command([self.frontend.with_name(target + (".exe" if os.name == "nt" else "")), ROOT / bindings])),
                            "native_ir": loads(self.command([self.frontend, "interpret", source_path, ROOT / bindings]))}
                if HISTORICAL_TARGET_DIR:
                    outcomes["historical_compiled"] = loads(self.command([self.comparison_target(target), ROOT / bindings]))
                for outcome in outcomes.values():
                    self.assertEqual(financial(outcome), financial(reference))
                normalized = financial(reference)
                self.assertEqual(normalized["status"], "calculated")
                if target.startswith("spl_lg"):
                    self.assertEqual(normalized["emissions"]["settlement"]["payable"], "35")
                else:
                    self.assertEqual(normalized["emissions"]["pool"]["earned"], "33000")
                    self.assertEqual(normalized["emissions"]["pool"]["payable"], "18000")
                    self.assertEqual(normalized["closing"], {"prepayment": "0"})
                self.record("promoted-" + target, source_path, values, outcomes)

    def write_binding(self, name, values):
        path = self.work / (name + ".json")
        write_json(path, values)
        return path


if __name__ == "__main__":
    unittest.main()
