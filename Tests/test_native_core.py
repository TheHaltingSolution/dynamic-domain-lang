"""Native source-to-target checks for scalar core and assertion barriers."""
from pathlib import Path
import tempfile
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, loads, write_json
from spl_compiler.evaluator import evaluate
from spl_compiler.lean_tools import ROOT, compile_schedule, lean
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target


HEADER = 'schedule NativeCore language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'


class NativeCoreTests(unittest.TestCase):
    def compare(self, body, inputs=None):
        source = HEADER + body + '}'
        checked = check_schedule(parse(source))
        inputs = inputs or {}
        reference = evaluate(checked, inputs, {}).to_dict()
        directory = ROOT / '.lake' / 'native-core-tests'
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            work = Path(temporary)
            schedule = work / 'source.spl'
            schedule.write_text(source, encoding='utf-8')
            write_json(work / 'bindings.json', {'inputs': inputs, 'openings': {}})
            target = compile_schedule(schedule, work / 'Settlement.lean')
            native = normalize_target(loads(lean(['--run', target, work / 'bindings.json'])))
            for field in ('status', 'emissions', 'closing'):
                self.assertEqual(canonical(reference[field]), canonical(native[field]), field)
            self.assertEqual([d['code'] for d in reference['diagnostics']], [d['code'] for d in native['diagnostics']])
        return native, reference

    def test_guard_precedes_unrelated_demanded_division(self):
        native, _ = self.compare('require false else "MISSING_POLICY"; define x = USD 1 / 0.0; emit "x" = x;')
        self.assertEqual(native['status'], 'blocked')
        self.assertEqual(native['diagnostics'][0]['code'], 'MISSING_POLICY')
        self.assertEqual(native['emissions'], {})
        self.assertEqual(native['closing'], {})

    def test_guard_demands_forward_definition_once(self):
        native, reference = self.compare('require rate > 0.0 else "RATE_REQUIRED"; define rate = 0.20; define x = USD 100 * rate; emit "x" = x;')
        self.assertEqual(native['emissions']['x'], '20')
        self.assertEqual([n['name'] for n in reference['trace'] if n['kind'] == 'definition'], ['rate', 'x'])

    def test_transitive_forward_dependencies_precede_guard_only(self):
        native, _ = self.compare('require rate < 0.0 else "RATE_BLOCK"; define rate = seed + 0.1; define seed = 0.1; define bad = USD 1 / 0.0; emit "bad" = bad;')
        self.assertEqual(native['diagnostics'][0]['code'], 'RATE_BLOCK')

    def test_local_guard_precedes_unrelated_division(self):
        native, _ = self.compare('define rows = for each item in [USD 1] { require false else "LOCAL_POLICY"; define bad = item / 0.0; yield bad; }; emit "rows" = rows;')
        self.assertEqual(native['diagnostics'][0]['code'], 'LOCAL_POLICY')

    def test_inactive_forward_conditional_branch_is_lazy(self):
        native, reference = self.compare('define selected = if true then USD 1 else future; require false else "POLICY"; define future = USD 1 / 0.0;')
        self.assertEqual(native['diagnostics'][0]['code'], 'POLICY')
        self.assertNotIn('future', [n.get('name') for n in reference['trace'] if n['kind'] == 'definition'])

    def test_inactive_forward_choose_arm_is_lazy(self):
        native, _ = self.compare('define selected = choose unique { when true => USD 1; when false => future; }; require false else "POLICY"; define future = USD 1 / 0.0;')
        self.assertEqual(native['diagnostics'][0]['code'], 'POLICY')

    def test_forward_short_circuit_is_lazy(self):
        native, _ = self.compare('define selected = false and future; require false else "POLICY"; define future = USD 1 / 0.0 > USD 0;')
        self.assertEqual(native['diagnostics'][0]['code'], 'POLICY')

    def test_empty_comprehension_does_not_demand_forward_binding(self):
        native, _ = self.compare('input xs: List<Money<USD>>; define selected = for each item in xs { define y = future; yield y; }; require false else "POLICY"; define future = USD 1 / 0.0;', {'xs': []})
        self.assertEqual(native['diagnostics'][0]['code'], 'POLICY')


if __name__ == '__main__':
    unittest.main()
