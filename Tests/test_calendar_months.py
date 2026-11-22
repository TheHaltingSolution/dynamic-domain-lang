"""Disclosed calendar extension: independent expectations and all execution paths."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import tempfile
import unittest

from cases.extensibility.build_modules import deadline_package, register_deadline
from oracles.calendar_months import add_calendar_months as oracle_months, derived_reserve
from spl_compiler.calendar_months import add_calendar_months
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import DataError, canonical, exact, loads, read_json, write_json
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
from spl_compiler.model import SPLException
from spl_compiler.modules import _check_capabilities, run_module_package
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target


HEADER = 'schedule CalendarMonths language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'


def schedule(body):
    return HEADER + body + '}'


class CalendarMonthsTests(unittest.TestCase):
    def test_independent_calendar_vectors_and_discriminators(self):
        cases = [
            ('2025-01-31', 1, '2025-02-28'), ('2024-01-31', 1, '2024-02-29'),
            ('2024-02-29', 12, '2025-02-28'), ('2000-01-31', 1, '2000-02-29'),
            ('1900-01-31', 1, '1900-02-28'), ('2100-01-31', 1, '2100-02-28'),
            ('2025-01-31', 0, '2025-01-31'), ('2025-02-28', 1, '2025-03-28'),
            ('2025-01-31', 2, '2025-03-31'), ('2024-12-31', 2, '2025-02-28'),
            ('0001-01-01', 119987, '9999-12-01'), ('9999-12-31', 0, '9999-12-31')]
        for source, months, expected in cases:
            with self.subTest(source=source, months=months):
                self.assertEqual(oracle_months(source, months, 'clamp_day'), expected)
                self.assertEqual(add_calendar_months(source, Fraction(months), 'clamp_day'), expected)
        self.assertEqual(oracle_months('2024-02-29', 48, 'reject_invalid_day'), '2028-02-29')
        first = oracle_months('2025-01-31', 1, 'clamp_day')
        self.assertEqual(oracle_months(first, 1, 'clamp_day'), '2025-03-28')
        self.assertNotEqual(oracle_months(first, 1, 'clamp_day'), oracle_months('2025-01-31', 2, 'clamp_day'))
        failures = [
            ('2025-01-31', 1, 'reject_invalid_day', 'CALENDAR_INVALID_TARGET_DAY'),
            ('9999-12-31', 1, 'clamp_day', 'CALENDAR_YEAR_RANGE'),
            ('0001-01-01', 120000, 'reject_invalid_day', 'CALENDAR_YEAR_RANGE'),
            ('2025-01-01', 0, 'unknown', 'CALENDAR_UNSUPPORTED_POLICY'),
            ('2025-02-29', 1, 'clamp_day', 'INVALID_DATE'),
            ('2025-01-01', -1, 'clamp_day', 'CALENDAR_INVALID_MONTHS')]
        for source, count, policy, code in failures:
            with self.assertRaisesRegex(ValueError, '^' + code + '$'):
                oracle_months(source, count, policy)
            with self.assertRaises(SPLException) as raised:
                add_calendar_months(source, count, policy)
            self.assertEqual(raised.exception.code, code)

    def test_checker_and_binding_boundaries(self):
        bad = [
            ('date "2025-01-01",1', 'BUILTIN_ARITY'),
            ('date "2025-02-29",1,"clamp_day"', 'INVALID_DATE'),
            ('date "2025-01-01",1.5,"clamp_day"', 'TYPE_MISMATCH'),
            ('date "2025-01-01",-1,"clamp_day"', 'TYPE_MISMATCH'),
            ('date "2025-01-01",1,"unknown"', 'CALENDAR_UNSUPPORTED_POLICY'),
            ('"2025-01-01",1,"clamp_day"', 'TYPE_MISMATCH')]
        directory = ROOT / '.lake' / 'calendar-tests'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            source = Path(temporary) / 'Invalid.spl'
            for args, code in bad:
                text = schedule('emit "x"=add_calendar_months(' + args + ');')
                with self.subTest(args=args), self.assertRaises(SPLException) as raised:
                    check_schedule(parse(text))
                self.assertEqual(raised.exception.code, code)
                source.write_text(text, encoding='utf-8', newline='\n')
                with self.assertRaises(DataError) as native:
                    lean(['--run', ROOT / 'SPL/Main.lean', 'check', source])
                self.assertEqual(native.exception.code, code)
        checked = check_schedule(parse(schedule('input d:Date; input n:Nat; emit "x"=add_calendar_months(d,n,"clamp_day");')))
        for d, n, code in [('2025-02-29', '1', 'INVALID_DATE'), ('2025-01-01', '-1', 'NEGATIVE_NAT'),
                           ('2025-01-01', '0.5', 'INVALID_INTEGER')]:
            outcome = evaluate(checked, {'d': d, 'n': n}, {}).to_dict()
            self.assertEqual(outcome['status'], 'blocked')
            self.assertEqual(outcome['diagnostics'][0]['code'], code)

    def test_four_backends_success_failure_strictness_and_lazy_bodies(self):
        declaration = 'input d:Date; input n:Nat; input p:Text; '
        ordinary = declaration + 'emit "x"=add_calendar_months(d,n,p);'
        rows = [
            (ordinary, {'d':'2025-01-31','n':'1','p':'clamp_day'}, '2025-02-28', None),
            (ordinary, {'d':'2024-02-29','n':'48','p':'reject_invalid_day'}, '2028-02-29', None),
            (ordinary, {'d':'2025-01-31','n':'1','p':'reject_invalid_day'}, None, 'CALENDAR_INVALID_TARGET_DAY'),
            (ordinary, {'d':'9999-12-31','n':'1','p':'clamp_day'}, None, 'CALENDAR_YEAR_RANGE'),
            (ordinary, {'d':'2025-01-01','n':'0','p':'unknown'}, None, 'CALENDAR_UNSUPPORTED_POLICY'),
            ('input xs:List<Nat>; emit "x"=map(xs,n => add_calendar_months(date "2025-01-31",n,"reject_invalid_day"));', {'xs':[]}, [], None),
            ('emit "x"=if true then date "2025-01-01" else add_calendar_months(date "2025-01-31",1,"reject_invalid_day");', {}, '2025-01-01', None),
            ('emit "x"=add_calendar_months(date "2025-01-01",0,if 1.0/0.0 == 0.0 then "clamp_day" else "reject_invalid_day");', {}, None, 'DIVISION_BY_ZERO'),
            (ordinary, {'d':'2025-02-29','n':'1','p':'clamp_day'}, None, 'INVALID_DATE'),
        ]
        directory = ROOT / '.lake' / 'calendar-tests'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            work = Path(temporary)
            for body, inputs, expected, code in rows:
                with self.subTest(body=body, inputs=inputs):
                    text = schedule(body)
                    checked = check_schedule(parse(text))
                    reference = evaluate(checked, inputs, {}).to_dict()
                    source, bindings = work/'Source.spl', work/'bindings.json'
                    source.write_text(text, encoding='utf-8', newline='\n')
                    write_json(bindings, {'inputs': inputs, 'openings': {}})
                    native_ir = normalize_target(interpret_schedule(source, bindings))
                    target = compile_schedule(source, work/'Settlement.lean')
                    native_target = normalize_target(loads(lean(['--run', target, bindings])))
                    backends = [reference, native_ir, native_target]
                    if code != 'INVALID_DATE':
                        decoded = {name:decode_value(value, checked.types[name]) for name,value in inputs.items()}
                        mirror = work/'Mirror.lean'
                        mirror.write_text(emit_module(checked, decoded, {}), encoding='utf-8', newline='\n')
                        backends.append(normalize_target(loads(lean(['--run',mirror]))))
                    for actual in backends:
                        self.assertEqual(actual['status'], 'blocked' if code else 'calculated')
                        self.assertEqual([d['code'] for d in actual['diagnostics']], [code] if code else [])
                        if code:
                            self.assertEqual(actual['emissions'], {})
                            self.assertEqual(actual['closing'], {})
                        else:
                            self.assertEqual(actual['emissions']['x'], expected)
                    for actual in backends[1:]:
                        self.assertEqual(canonical(actual['emissions']), canonical(reference['emissions']))
                    calendar_nodes = [n for n in native_ir['trace'] if n.get('detail', {}).get('builtin') == 'add_calendar_months']
                    if body.startswith('input xs') or body.startswith('emit "x"=if'):
                        self.assertEqual(calendar_nodes, [])

    def test_derived_canonical_module_against_independent_reserve_oracle(self):
        reference = register_deadline(derived=True)
        original = read_json(ROOT / 'cases/r1/supplied-due-reserve.json')
        for close in ['2025-02-27', '2025-02-28']:
            fixture = deepcopy(original)
            fixture.update(close_date=close, months=1, invalid_day_policy='clamp_day')
            expected = derived_reserve(fixture)
            package = deadline_package(fixture, derived=True, reference=reference)
            result = run_module_package(package, ROOT)
            self.assertEqual(result['diagnostics'], [], result)
            line = result['results']['reserve_ledger']
            self.assertEqual(line['deadline'], expected['deadline'])
            for field in ('released', 'closing_balance', 'available'):
                self.assertEqual(exact(line[field]), expected[field])
            self.assertEqual(exact(result['closing_state'][0]['quantity']), expected['closing_balance'])

    def test_capability_must_be_explicitly_declared(self):
        descriptor = {'imports': [], 'interface': {'exports': [], 'ports': [],
                                                  'schemas': [], 'dictionaries': {}},
                      'compatibility': {'capabilities': ['spl.core/1'], 'codecs': ['spl-exact/1']}}
        syntax = parse(schedule('emit "x"=add_calendar_months(date "2025-01-31",1,"clamp_day");'))
        with self.assertRaises(DataError) as raised:
            _check_capabilities(descriptor, syntax)
        self.assertEqual(raised.exception.code, 'MODULE_CAPABILITY_UNDECLARED')
        descriptor['compatibility']['capabilities'].append('spl.calendar-months/1')
        _check_capabilities(descriptor, syntax)


if __name__ == '__main__':
    unittest.main()
