"""RULE-01 registered selection: independent Python and native/target agreement."""
from pathlib import Path
import tempfile
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.evaluator import evaluate
from spl_compiler.emitter import emit_module
from spl_compiler.model import SPLException
from spl_compiler.parser import parse


HEADER = 'schedule Priority language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'


def source(arms, fallback=None, mode="priority", annotation=""):
    otherwise = '' if fallback is None else f'otherwise "fallback" => {fallback};'
    return HEADER + f'define value{annotation} = choose {mode} {{ {arms} {otherwise} }}; emit "value" = value; }}'


def arm(identity, priority, predicate="true", body="USD 20"):
    return f'rule "{identity}" priority {priority} when {predicate} => {body};'


class PriorityTests(unittest.TestCase):
    def result(self, text):
        return evaluate(check_schedule(parse(text)), {}, {})

    def code(self, text, expected):
        result = self.result(text)
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(result.diagnostics[0]['code'], expected)
        self.assertEqual(result.emissions, {})
        self.assertEqual(result.closing, {})
        return result

    def test_greatest_priority_and_lower_tie(self):
        result = self.result(source(arm('z', 7, body='USD 40') + arm('b', 3) + arm('a', 3)))
        self.assertEqual(result.emissions['value'], 40)
        selection = next(n for n in result.trace if n['kind'] == 'selection')
        self.assertEqual(selection['selected_rule_id'], 'z')
        self.assertEqual([c['rule_id'] for c in selection['candidates']], ['a', 'b', 'z'])

    def test_selected_zero_is_not_fallback(self):
        result = self.result(source(arm('zero', -5, body='USD 0'), 'USD 10'))
        self.assertEqual(result.emissions['value'], 0)
        selection = next(n for n in result.trace if n['kind'] == 'selection')
        self.assertEqual(selection['selection_status'], 'calculated_zero')
        self.assertEqual(selection['selected_rule_id'], 'zero')

    def test_fallback_and_negative_ordinary_priority(self):
        self.assertEqual(self.result(source(arm('a', -5), 'USD 10')).emissions['value'], 20)
        result = self.result(source(arm('a', -5, 'false'), 'USD 10'))
        self.assertEqual(result.emissions['value'], 10)
        self.assertEqual(next(n for n in result.trace if n['kind'] == 'selection')['selected_rule_id'], 'fallback')
        self.code(source(arm('a', 0, 'false')), 'NO_APPLICABLE_RULE')

    def test_tied_highest_is_ambiguous_before_bodies(self):
        result = self.code(source(arm('a', 7, body='USD 1 / 0.0') + arm('b', 7)), 'AMBIGUOUS_RULE')
        self.assertEqual(next(n for n in result.trace if n['kind'] == 'selection')['bodies'], 'not_evaluated')

    def test_registered_unique_equal_bodies_are_ambiguous(self):
        self.code(source('rule "a" when true => USD 20; rule "b" when true => USD 20;', mode='registered unique'), 'AMBIGUOUS_RULE')

    def test_unselected_bodies_and_unused_fallback_are_lazy(self):
        result = self.result(source(arm('a', 0, 'false', 'USD 1 / 0.0') + arm('b', 3, body='USD 20'), 'USD 1 / 0.0'))
        self.assertEqual(result.emissions['value'], 20)

    def test_selected_body_failure_never_uses_fallback(self):
        result = self.code(source(arm('a', 0, body='USD 1 / 0.0'), 'USD 10'), 'DIVISION_BY_ZERO')
        selection = next(n for n in result.trace if n['kind'] == 'selection')
        self.assertEqual(selection['selected_rule_id'], 'a')
        self.assertEqual(selection['body_status'], 'failed')

    def test_lower_priority_predicate_is_demanded(self):
        text = source(arm('a', 7) + arm('b', -10, 'USD 1 / 0.0 > USD 0') + arm('z', 9))
        result = self.code(text, 'DIVISION_BY_ZERO')
        selection = next(n for n in result.trace if n['kind'] == 'selection')
        self.assertEqual(selection['failed_rule_id'], 'b')
        self.assertEqual(selection['candidates'][-1]['reason'], 'not_evaluated')
        self.assertEqual(selection['bodies'], 'not_evaluated')

    def test_rule_permutation_preserves_predicate_error_precedence(self):
        first = arm('b', 7, 'USD 1 / 0.0 > USD 0')
        second = arm('a', 1, 'true', 'USD 7')
        traces = []
        for arms in (first + second, second + first):
            result = self.code(source(arms), 'DIVISION_BY_ZERO')
            selection = next(n for n in result.trace if n['kind'] == 'selection')
            traces.append(selection['candidates'])
        self.assertEqual(traces[0], traces[1])

    def test_structure_precedes_false_predicates(self):
        for text, code in [
            (source(arm('a', 1, 'false') + arm('a', 2, 'false')), 'DUPLICATE_RULE_ID'),
            (source(arm('fallback', 0, 'false'), 'USD 0'), 'DUPLICATE_RULE_ID'),
            (source(arm('', 0)), 'INVALID_RULE_ID'),
            (source('', 'USD 0'), 'EMPTY_RULE_SET'),
            (source(''), 'EMPTY_RULE_SET'),
        ]:
            with self.subTest(code=code):
                with self.assertRaises(SPLException) as raised:
                    check_schedule(parse(text))
                self.assertEqual(raised.exception.code, code)

    def test_typed_empty_rule_set_and_type_errors(self):
        result = self.result(source('', 'USD 0', annotation=': Money<USD>'))
        self.assertEqual(result.emissions['value'], 0)
        for text in [source(arm('a', 0, 'USD 1')), source(arm('a', 0) + arm('b', 1, body='true'))]:
            with self.assertRaises(SPLException) as raised:
                check_schedule(parse(text))
            self.assertEqual(raised.exception.code, 'TYPE_MISMATCH')

    def test_priority_requires_explicit_integer(self):
        for priority in ['', 'priority 1.2', 'priority "3"']:
            with self.assertRaises(SPLException):
                parse(source(f'rule "a" {priority} when true => USD 1;'))

    def test_python_emitter_retains_lazy_predicate_and_body(self):
        generated = emit_module(check_schedule(parse(source(arm('a', -5), 'USD 0'))))
        self.assertIn('SPL.selectRules true', generated)
        self.assertIn('(-5 : Int)', generated)
        self.assertIn('(fun _ =>', generated)


class NativePriorityTests(unittest.TestCase):
    def test_all_backends_values_errors_and_trace(self):
        from spl_compiler.codecs import canonical, loads, write_json
        from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
        from spl_compiler.run import normalize_target

        witnesses = [
            (source(arm('low1', 3) + arm('winner', 7, body='USD 40') + arm('low2', 3)), '40', None),
            (source(arm('zero', -5, body='USD 0'), 'USD 10'), '0', None),
            (source(arm('a', 0, 'false'), 'USD 10'), '10', None),
            (source('', 'USD 0', annotation=': Money<USD>'), '0', None),
            (source(arm('a', 0, 'false')), None, 'NO_APPLICABLE_RULE'),
            (source(arm('a', 7, body='USD 1 / 0.0') + arm('b', 7)), None, 'AMBIGUOUS_RULE'),
            (source(arm('a', 7, body='USD 1 / 0.0'), 'USD 10'), None, 'DIVISION_BY_ZERO'),
            (source(arm('a', 7) + arm('b', -10, 'USD 1 / 0.0 > USD 0') + arm('z', 9)), None, 'DIVISION_BY_ZERO'),
            (source(arm('unselected', 0, 'false', 'USD 1 / 0.0') + arm('winner', 1), 'USD 1 / 0.0'), '20', None),
            (source('rule "a" when true => USD 20; rule "b" when true => USD 20;', mode='registered unique'), None, 'AMBIGUOUS_RULE'),
        ]
        directory = ROOT / '.lake' / 'priority-tests'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            work = Path(temporary)
            bindings = work / 'bindings.json'
            write_json(bindings, {'inputs': {}, 'openings': {}})
            for index, (text, amount, code) in enumerate(witnesses):
                with self.subTest(index=index):
                    authored = work / 'source.spl'
                    authored.write_text(text, encoding='utf-8')
                    checked = check_schedule(parse(text))
                    reference = evaluate(checked, {}, {}).to_dict()
                    interpreted = normalize_target(interpret_schedule(authored, bindings))
                    target = compile_schedule(authored, work / 'Settlement.lean')
                    emitted = normalize_target(loads(lean(['--run', target, bindings])))
                    mirror = work / 'Mirror.lean'
                    mirror.write_text(emit_module(checked, {}, {}), encoding='utf-8')
                    mirror_result = normalize_target(loads(lean(['--run', mirror])))
                    for actual in (interpreted, emitted, mirror_result):
                        for field in ('status', 'emissions', 'closing'):
                            self.assertEqual(canonical(reference[field]), canonical(actual[field]), field)
                        self.assertEqual([d['code'] for d in actual['diagnostics']], [code] if code else [])
                    if amount is not None:
                        self.assertEqual(emitted['emissions']['value'], amount)
                    selection = [n for n in interpreted['trace'] if n['kind'] == 'selection']
                    self.assertTrue(selection)
                    detail = selection[-1]['detail']
                    self.assertIn('candidates', detail)
                    seen = set()
                    def check_references(value):
                        if isinstance(value, dict):
                            for key, child in value.items():
                                if key in {'predicate_node', 'decision_node', 'skipped_node'}:
                                    self.assertIn(child, seen)
                                else:
                                    check_references(child)
                        elif isinstance(value, list):
                            for child in value:
                                check_references(child)
                    for node in interpreted['trace']:
                        self.assertTrue(set(node['dependencies']) <= seen)
                        check_references(node.get('detail', {}))
                        seen.add(node['node_id'])
                    if index == 1:
                        self.assertEqual(detail['selected_rule_id'], 'zero')
                        self.assertEqual(detail['selection_status'], 'calculated_zero')
                    if index == 7:
                        self.assertEqual(detail['failed_rule_id'], 'b')
                        self.assertEqual(detail['candidates'][-1]['reason'], 'not_evaluated')
                        self.assertFalse(any(n['kind'] == 'money' and n.get('outcome') == 'evaluated' for n in interpreted['trace']))


if __name__ == '__main__':
    unittest.main()
