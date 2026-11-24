"""Python-generated Lean must cache definitions in their actual call scope.

The native fixture object is composed only for disposable C/link tooling. No
native test class is inherited or re-exported. An external evidence launcher
may supply the archived Python emitter for a real pre-change comparison.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest

from Tests import test_emitter_memoization as native_tools
from Tests import test_indexed_sv as financial_fixtures
from Tests.test_fold import schedule
from Tests.test_linking import library, importing
from scripts.spl_benchmark import receipt_probe
from spl_compiler import emitter
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import loads, write_json
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.linker import link_schedule
from spl_compiler.parser import parse


OLD_PYTHON_EMITTER = None
EVIDENCE_DIR = None
OBSERVATIONS = []


class PythonEmitterMemoizationTests(unittest.TestCase):
    def setUp(self):
        self.tools = native_tools.EmitterMemoizationTests()
        self.tools.setUp()
        self.addCleanup(self.tools.doCleanups)
        self.old = None
        if OLD_PYTHON_EMITTER:
            spec = importlib.util.spec_from_file_location(
                'spl_compiler._archived_python_emitter', OLD_PYTHON_EMITTER)
            self.old = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.old)

    def checked(self, source, manifest=None):
        syntax = parse(source)
        if manifest:
            syntax = link_schedule(syntax, manifest)
        return check_schedule(syntax)

    def generated(self, checked, values, module):
        inputs = {k: decode_value(v, checked.types[k]) for k, v in values['inputs'].items()}
        openings = {k: decode_value(v, checked.types[k]) for k, v in values['openings'].items()}
        return module.emit_module(checked, inputs, openings)

    def record(self, label, outcomes, extra=None):
        row = {'case': label, 'outcomes': outcomes,
               'archived_python_emitter_executed': self.old is not None, **(extra or {})}
        OBSERVATIONS.append(row)
        if EVIDENCE_DIR:
            destination = Path(EVIDENCE_DIR) / label
            destination.mkdir(parents=True, exist_ok=True)
            for path in self.tools.work.iterdir():
                if path.is_file():
                    (destination / path.name).write_bytes(path.read_bytes())
            write_json(destination / 'outcomes.json', row)

    def compare(self, label, body, values, expected, manifest=None):
        source = schedule(body)
        checked = self.checked(source, manifest)
        reference = financial_fixtures.financial(evaluate(
            checked, values['inputs'], values['openings']).to_dict())
        self.assertEqual(reference, expected)
        outcomes = {'reference': reference}
        for origin, module in [('new', emitter), *([('old', self.old)] if self.old else [])]:
            generated = self.tools.work / (origin + '.lean')
            generated.write_text(self.generated(checked, values, module), encoding='utf-8')
            # Exercise the same --run path used by the failed financial driver.
            result = loads(self.tools.command([self.tools.lean, '--run', generated]))
            outcomes[origin + '_python_emitted_lean'] = financial_fixtures.financial(result)
            self.assertEqual(outcomes[origin + '_python_emitted_lean'], expected)
        (self.tools.work / 'Source.spl').write_text(source, encoding='utf-8')
        write_json(self.tools.work / 'bindings.json', values)
        self.record(label, outcomes)

    def test_forward_references_and_repeated_definition(self):
        self.compare('forward', 'input x:Int; define twice=later+later; define later=x*2; emit "v"=twice;',
                     {'inputs': {'x': '7'}, 'openings': {}},
                     {'status': 'calculated', 'emissions': {'v': '28'}, 'closing': {}, 'diagnostics': []})

    def test_laziness_and_declaration_failure_order(self):
        for index, (body, code) in enumerate([
            ('require if true then true else bad == 0.0 else "BRANCH"; require false else "STOP"; define bad=1.0/0.0;', 'STOP'),
            ('require false else "EARLY"; define bad=1.0/0.0;', 'EARLY'),
            ('define bad=1.0/0.0; require false else "LATE";', 'DIVISION_BY_ZERO'),
            ('define first=later+1.0; require false else "MIDDLE"; define later=1.0/0.0;', 'DIVISION_BY_ZERO'),
        ]):
            with self.subTest(index=index):
                self.compare('failure-' + str(index), body + ' emit "v"=0;',
                             {'inputs': {}, 'openings': {}},
                             {'status': 'blocked', 'emissions': {}, 'closing': {}, 'diagnostics': [code]})

    def test_loop_and_fold_get_fresh_cells(self):
        self.compare('loop-fold', '''input xs:List<Int>;
          define rows=for each x in xs { define twice=x+x; define repeat=twice+twice; yield repeat; };
          define total=fold xs from 0 with s,x { define twice=x+x; define repeat=twice+twice; yield s+repeat; };
          emit "rows"=rows; emit "total"=total;''',
          {'inputs': {'xs': ['1', '3', '7']}, 'openings': {}},
          {'status': 'calculated', 'emissions': {'rows': ['4', '12', '28'], 'total': '44'},
           'closing': {}, 'diagnostics': []})

    def test_imported_function_cells_and_strict_arguments(self):
        parameter = [{'name': 'n', 'type': {'name': 'Int', 'args': []}}]
        inner = library('inner', 'input n:Int; define a=n*2; define result=a+a;', parameters=parameter)
        outer = library('outer', 'input n:Int; define a=twice(n); define result=a+a;', parameters=parameter,
                        imports=[importing('inner', local='twice')])
        self.compare('imports', 'define a=compute(2); define b=compute(5); emit "a"=a; emit "b"=b;',
                     {'inputs': {}, 'openings': {}},
                     {'status': 'calculated', 'emissions': {'a': '16', 'b': '40'}, 'closing': {}, 'diagnostics': []},
                     {'modules': [inner, outer], 'imports': [importing('outer', local='compute')]})
        strict = library('strict', 'input n:Ratio; define result=n+n;', result='Ratio',
                         parameters=[{'name': 'n', 'type': {'name': 'Ratio', 'args': []}}])
        self.compare('strict-argument', 'emit "v"=compute(1.0/0.0);',
                     {'inputs': {}, 'openings': {}},
                     {'status': 'blocked', 'emissions': {}, 'closing': {}, 'diagnostics': ['DIVISION_BY_ZERO']},
                     {'modules': [strict], 'imports': [importing('strict', local='compute')]})

    def test_same_process_settlements_have_fresh_input_and_opening(self):
        checked = self.checked(schedule('''input x:Int; opening balance:Int from "old";
          define twice=x*2; define repeated=twice+twice;
          emit "v"=repeated; closing balance=balance+repeated;'''))
        pairs = [(x, opening) for x in (-3, -1, 0, 1, 7, 13) for opening in (0, 17)]
        calls = '[' + ','.join('([("x",' + emitter.lean_value(x) + ')],[("balance",' +
                               emitter.lean_value(opening) + ')])' for x, opening in pairs) + ']'
        outcomes = {}
        for origin, module in [('new', emitter), *([('old', self.old)] if self.old else [])]:
            source = self.tools.work / (origin + '-repeated.lean')
            driver = '\ndef main : IO Unit := do\n  let cases : List (SPL.Env × SPL.Env) := ' + calls
            driver += '\n  let results := cases.map (fun pair => SPL.outcomeJson (GeneratedSPL.settle pair.1 pair.2))'
            driver += '\n  IO.println (Lean.Json.arr results.toArray).compress\n'
            source.write_text(module.emit_module(checked) + driver, encoding='utf-8')
            actual = loads(self.tools.command([self.tools.lean, '--run', source]))
            expected = [{'status': 'calculated', 'emissions': {'v': str(x * 4)},
                         'closing': {'balance': str(opening + x * 4)}, 'diagnostics': []} for x, opening in pairs]
            normalized = [financial_fixtures.financial(row) for row in actual]
            self.assertEqual(normalized, expected)
            outcomes[origin + '_same_process'] = normalized
        self.record('same-process', outcomes)

    def test_actual_group_build_count_and_full_values(self):
        source = self.tools.frontend.parents[3] / 'cases/sv/sv01-indexed.spl'
        checked = self.checked(source.read_text(encoding='utf-8'))
        values = receipt_probe(10, 8)
        expected = financial_fixtures.financial(evaluate(checked, values['inputs'], values['openings']).to_dict())
        counts, outcomes = {}, {}
        for origin, module in [('new', emitter), *([('old', self.old)] if self.old else [])]:
            generated = self.tools.work / (origin + '-counter.lean')
            generated.write_text(self.generated(checked, values, module), encoding='utf-8')
            executable = self.tools.native(generated, count_groups=True)
            process = subprocess.run([str(executable)], cwd=self.tools.work, env=self.tools.env,
                                     capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertTrue(all(row == b'MEMO_GROUP_BUILD' for row in process.stderr.splitlines()))
            counts[origin] = len(process.stderr.splitlines())
            outcomes[origin] = financial_fixtures.financial(loads(process.stdout))
            self.assertEqual(outcomes[origin], expected)
        self.assertEqual(counts['new'], 2)
        if self.old:
            self.assertGreater(counts['old'], counts['new'])
        self.record('group-builds', outcomes, {'observed_group_build_calls': counts})


if __name__ == '__main__':
    unittest.main()
