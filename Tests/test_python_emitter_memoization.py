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

    def test_deferred_captures_keep_option_choose_and_short_circuit_lazy(self):
        expressions = [
            'get_or(some(7.0),future)',
            'choose unique { when true => 7.0; when false => future; }',
            'if false and future > 0.0 then 1.0 else 7.0',
            'if true or future > 0.0 then 7.0 else 1.0',
        ]
        for index, expression in enumerate(expressions):
            with self.subTest(expression=expression):
                self.compare('deferred-capture-' + str(index),
                    'define selected=' + expression + '; require false else "STOP"; '
                    'define future=1.0/0.0; emit "result"=selected;',
                    {'inputs': {}, 'openings': {}},
                    {'status': 'blocked', 'emissions': {}, 'closing': {}, 'diagnostics': ['STOP']})

    def test_nested_disjoint_and_callee_scopes_keep_captures_local(self):
        parameters = [{'name': 'n', 'type': {'name': 'Int', 'args': []}}]
        callee = library('scoped', 'input n:Int; define later=n*3; define result=later+n;', parameters=parameters)
        self.compare('scoped-captures', '''input n:Int; define original=n+n;
            define rows=for each outer in [2,5] {
              define later=outer*2;
              define nested=for each child in [1,3] { define twice=child+child; yield twice+later; };
              yield nested;
            };
            define total=fold [2,5] from n with s,event { define later=event*2; yield s+later; };
            emit "original"=original; emit "rows"=rows; emit "total"=total;
            emit "call"=compute(n); emit "other_call"=compute(3);''',
            {'inputs': {'n': '10'}, 'openings': {}},
            {'status': 'calculated', 'emissions': {'original': '20', 'rows': [['6', '10'], ['12', '16']],
             'total': '24', 'call': '40', 'other_call': '12'}, 'closing': {}, 'diagnostics': []},
            {'modules': [callee], 'imports': [importing('scoped', local='compute')]})

    def test_compiled_same_process_errors_are_not_cached_between_inputs(self):
        checked = self.checked(schedule('input divisor:Ratio; define quotient=10.0/divisor; '
                                        'define repeated=quotient+quotient; emit "result"=repeated;'))
        inputs = ['0', '2', '5', '0', '2']
        calls = '[' + ','.join('[("divisor",' + emitter.lean_value(decode_value(value, checked.types['divisor'])) + ')]'
                               for value in inputs) + ']'
        outcomes = {}
        for origin, module in [('new', emitter), *([('old', self.old)] if self.old else [])]:
            source = self.tools.work / (origin + '-error-freshness.lean')
            driver = '\ndef main : IO Unit := do\n  let cases : List SPL.Env := ' + calls
            driver += '\n  let results := cases.map (fun values => SPL.outcomeJson (GeneratedSPL.settle values []))'
            driver += '\n  IO.println (Lean.Json.arr results.toArray).compress\n'
            source.write_text(module.emit_module(checked) + driver, encoding='utf-8')
            executable = self.tools.native(source)
            actual = [financial_fixtures.financial(row) for row in loads(self.tools.command([executable]))]
            expected = [financial_fixtures.financial(evaluate(checked, {'divisor': value}, {}).to_dict()) for value in inputs]
            self.assertEqual(actual, expected)
            self.assertEqual([row['diagnostics'] for row in actual], [['DIVISION_BY_ZERO'], [], [], ['DIVISION_BY_ZERO'], []])
            self.assertEqual(actual[1], actual[4])
            outcomes[origin + '_compiled_same_process'] = actual
        self.record('compiled-error-freshness', outcomes)

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
