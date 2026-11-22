"""MAP-01 / REL-01 independent reference, IR and generated execution witnesses."""
from pathlib import Path
import tempfile
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.evaluator import evaluate, decode_value
from spl_compiler.emitter import emit_module
from spl_compiler.model import SPLException
from spl_compiler.parser import parse

HEADER = 'schedule Collections language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'


def source(body):
    return HEADER + body + '}'


WITNESSES = [
    ('define m = make_map([2,1], x => tuple(x,false), y => USD 10 * 0.0); emit "entries" = entries(m); emit "zero" = lookup(m,tuple(1,false)); emit "missing" = lookup(m,tuple(3,false));', {}, None),
    ('define m = make_map([1,1], x => x, y => USD 1 / 0.0); emit "v" = entries(m);', {}, 'DUPLICATE_MAP_KEY'),
    ('define g = group_by([2,1,2,1], x => x); emit "v" = entries(g); emit "empty" = get_or(lookup(g,3),[]);', {}, None),
    ('emit "v" = join([1,1],[1,1,1], l => l, r => r);', {}, None),
    ('emit "v" = left_join([2,1],[1,1], l => l, r => r);', {}, None),
    ('input empty: List<Int>; emit "v" = join(empty,[1], l => l, r => if USD 1 / 0.0 > USD 0 then r else r);', {'empty':[]}, 'DIVISION_BY_ZERO'),
    ('input rows: List<{event_id:Id<Event>, key:Tuple<Id<Asset>,Int>, amount:Money<USD>}>; emit "v" = entries(make_map(rows,x => x.key,y => y.amount));', {'rows':[{'event_id':'e1','key':['A','0'],'amount':{'value':'0','currency':'USD'}}]}, None),
    ('emit "v" = get_or(some(USD 0),USD 1 / 0.0); emit "has" = is_some(some(0)); define n:Option<Int> = none(); emit "none" = n; define nested:Option<Option<Int>> = some(none()); emit "nested" = nested;', {}, None),
    ('define m:Map<Int,Money<USD>> = make_map([2,1],x => x,y => if y == 1 then require_some(none(),"FIRST_KEY") else require_some(none(),"SECOND_KEY")); emit "v" = entries(m);', {}, 'FIRST_KEY'),
    ('input m:Map<Tuple<Id<Asset>,Int>,Money<USD>>; emit "v" = entries(m);', {'m':[{'key':['B','1'],'value':{'value':'10','currency':'USD'}},{'key':['A','0'],'value':{'value':'0','currency':'USD'}}]}, None),
    ('input empty:List<Int>; emit "v"=entries(group_by(empty,x=>x)); emit "j"=join([1],empty,l=>l,r=>r);', {'empty':[]}, None),
    ('define m=make_map([1,1,3],x=>if USD 1 / (if x == 3 then 0.0 else 1.0) > USD 0 then x else x,y=>USD 1 / 0.0); emit "v"=entries(m);', {}, 'DIVISION_BY_ZERO'),
]


class CollectionTests(unittest.TestCase):
    def test_reference_witnesses(self):
        for body,inputs,code in WITNESSES:
            with self.subTest(body=body):
                result = evaluate(check_schedule(parse(source(body))),inputs,{})
                self.assertEqual([d['code'] for d in result.diagnostics],[code] if code else [])
        grouped = evaluate(check_schedule(parse(source(WITNESSES[2][0]))),{},{}).to_dict()['emissions']['v']
        self.assertEqual(grouped,[{'key':'1','value':['1','1']},{'key':'2','value':['2','2']}])

    def test_key_type_and_namespace_guards(self):
        for body in [
            'define m = make_map([1],x => "text",y => y);',
            'define m = group_by([1],x => USD 1);',
            'input a:Id<Agreement>; input b:Id<Asset>; define m = make_map([1],x => tuple(a,b),y => y); emit "v" = lookup(m,tuple(b,a));',
            'define x = tuple_get(tuple(1,2),2);',
            'input x:Map<Text,Int>;',
            'input x:{a:Int,a:Int};',
        ]:
            with self.subTest(body=body), self.assertRaises(SPLException):
                check_schedule(parse(source(body)))

    def test_duplicate_smallest_key_lineage(self):
        result = evaluate(check_schedule(parse(source('define m=make_map([2,2,1,1],x=>x,y=>USD 1 / 0.0); emit "v"=entries(m);'))),{},{})
        node = next(n for n in result.trace if n['kind'] == 'make_map')
        self.assertEqual(node['source_occurrences'],[2,3])
        self.assertEqual(node['values'],'not_evaluated')


class NativeCollectionTests(unittest.TestCase):
    def test_ir_and_both_emitters(self):
        from spl_compiler.codecs import canonical, loads, write_json
        from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
        from spl_compiler.run import normalize_target
        directory = ROOT / '.lake' / 'collection-tests'
        directory.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            work = Path(temporary)
            for body,inputs,code in WITNESSES:
                with self.subTest(body=body):
                    text = source(body)
                    authored = work/'source.spl'
                    authored.write_text(text,encoding='utf-8')
                    bindings = work/'bindings.json'
                    write_json(bindings,{'inputs':inputs,'openings':{}})
                    checked = check_schedule(parse(text))
                    reference = evaluate(checked,inputs,{}).to_dict()
                    interpreted = normalize_target(interpret_schedule(authored,bindings))
                    emitted = normalize_target(loads(lean(['--run',compile_schedule(authored,work/'Target.lean'),bindings])))
                    mirror = work/'Mirror.lean'
                    decoded = {k:decode_value(v,checked.types[k]) for k,v in inputs.items()}
                    mirror.write_text(emit_module(checked,decoded,{}),encoding='utf-8')
                    mirrored = normalize_target(loads(lean(['--run',mirror])))
                    for actual in [interpreted,emitted,mirrored]:
                        for field in ['status','emissions','closing']:
                            self.assertEqual(canonical(reference[field]),canonical(actual[field]),field)
                        self.assertEqual([d['code'] for d in actual['diagnostics']],[code] if code else [])
                    seen = set()
                    for node in interpreted['trace']:
                        self.assertTrue(set(node['dependencies']) <= seen)
                        seen.add(node['node_id'])


if __name__ == '__main__':
    unittest.main()
