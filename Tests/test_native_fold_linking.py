"""Four-backend agreement for finite folds and source-pinned function linking."""
from pathlib import Path
import tempfile
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, loads, write_json
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import evaluate, decode_value
from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
from spl_compiler.linker import link_schedule
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target
from Tests.test_fold import schedule
from Tests.test_linking import library, importing


class NativeFoldLinkingTests(unittest.TestCase):
    def test_typed_record_state_with_empty_history_and_append(self):
        text=schedule('define x:{total:Int,history:List<Int>}=fold [2,3] from {total:0,history:[]} with s,e { yield {total:s.total+e,history:append(s.history,s.total+e)}; }; emit "x"=x;')
        directory=ROOT/".lake"/"fold-link-tests"
        directory.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            work=Path(temporary)
            source=work/"Source.spl"
            source.write_text(text,encoding="utf-8")
            bindings=work/"bindings.json"
            write_json(bindings,{"inputs":{},"openings":{}})
            interpreted=normalize_target(interpret_schedule(source,bindings))
            target=compile_schedule(source,work/"Settlement.lean")
            emitted=normalize_target(loads(lean(["--run",target,bindings])))
            for actual in (interpreted,emitted):
                self.assertEqual(actual["status"],"calculated")
                self.assertEqual(actual["emissions"]["x"],{"total":"5","history":["2","5"]})

    def test_four_backend_values_failures_and_trace(self):
        module = library("arithmetic",'input a:Ratio; input b:Ratio; require a >= 0.0 else "NEGATIVE"; define hidden=2.0; define result=a+a+hidden;',
                         result="Ratio",parameters=[{"name":n,"type":{"name":"Ratio","args":[]}} for n in ["a","b"]])
        manifest = {"modules":[module],"imports":[importing("arithmetic")]}
        inner=library("inner",'input n:Int; define result=n*2;',parameters=[{"name":"n","type":{"name":"Int","args":[]}}])
        outer=library("outer",'input n:Int; define result=twice(n)+1;',parameters=[{"name":"n","type":{"name":"Int","args":[]}}],imports=[importing("inner",local="twice")])
        transitive={"modules":[inner,outer],"imports":[importing("outer",local="calculate")]}
        prefix = 'input xs:List<{id:Id<Event>,day:Date,amount:Int}>; define x = ordered_fold xs from 0 by k => k.day identified by i => i.id ties "reject" with s,e { yield s*10+e.amount; }; emit "x"=x;'
        row_a = {"id":"a","day":"2026-01-01","amount":"1"}
        row_b = {"id":"b","day":"2026-01-02","amount":"2"}
        cases = [
            ('define x=fold [1,2,3] from 0 with s,e { yield s*10+e; }; emit "x"=x;',{},None,"123",None),
            ('input xs:List<Int>; define x=fold xs from 9 with s,e { yield s+e; }; emit "x"=x;',{"xs":[]},None,"9",None),
            ('define x=fold [1,2,3] from 0 with s,e { require e!=2 else "STOP"; yield s+e; }; emit "x"=x;',{},None,None,"STOP"),
            (prefix,{"xs":[row_b,row_a]},None,"12",None),
            (prefix,{"xs":[row_a,{**row_b,"day":"2026-01-01"}]},None,None,"UNRESOLVED_EVENT_ORDER"),
            (prefix,{"xs":[row_a,{**row_b,"id":"a"}]},None,None,"DUPLICATE_EVENT_ID"),
            ('define hidden=100.0; emit "x"=compute(1.0+2.0,4.0);',{},manifest,"8",None),
            ('emit "x"=compute(1.0,1.0/0.0);',{},manifest,None,"DIVISION_BY_ZERO"),
            ('emit "x"=compute(-1.0,4.0);',{},manifest,None,"NEGATIVE"),
            ('emit "x"=compute(quantize(1.0,0.0,"floor"),1.0/0.0);',{},manifest,None,"INVALID_QUANTUM"),
            ('emit "x"=calculate(3);',{},transitive,"7",None),
        ]
        directory=ROOT/".lake"/"fold-link-tests"
        directory.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            work=Path(temporary)
            for index,(body,inputs,links,amount,code) in enumerate(cases):
                with self.subTest(index=index):
                    text=schedule(body)
                    authored=work/"Source.spl"
                    authored.write_text(text,encoding="utf-8")
                    bindings=work/"bindings.json"
                    write_json(bindings,{"inputs":inputs,"openings":{}})
                    linkpath=None
                    ast=parse(text)
                    if links:
                        linkpath=work/"link.json"
                        write_json(linkpath,links)
                        ast=link_schedule(ast,links)
                    checked=check_schedule(ast)
                    reference=evaluate(checked,inputs,{}).to_dict()
                    interpreted=normalize_target(interpret_schedule(authored,bindings,link=linkpath))
                    emitted=compile_schedule(authored,work/"Settlement.lean",link=linkpath)
                    target=normalize_target(loads(lean(["--run",emitted,bindings])))
                    mirror=work/"Mirror.lean"
                    decoded={name:decode_value(value,checked.types[name]) for name,value in inputs.items()}
                    mirror.write_text(emit_module(checked,decoded,{}),encoding="utf-8")
                    mirror_result=normalize_target(loads(lean(["--run",mirror])))
                    for actual in (interpreted,target,mirror_result):
                        for field in ("status","emissions","closing"):
                            self.assertEqual(canonical(actual[field]),canonical(reference[field]),field)
                        self.assertEqual([d["code"] for d in actual["diagnostics"]],[code] if code else [])
                    if amount is not None:
                        self.assertEqual(target["emissions"]["x"],amount)
                    steps=[n for n in interpreted["trace"] if n["kind"]=="fold_step"]
                    if index==2:
                        self.assertEqual(len(steps),2)
                        self.assertTrue(any(s["detail"].get("code")=="STOP" for s in steps))
                    if index in (4,5):
                        self.assertEqual(steps,[])
                    seen=set()
                    for node in interpreted["trace"]:
                        self.assertTrue(set(node["dependencies"])<=seen)
                        seen.add(node["node_id"])

    def test_native_link_rejects_cycles_missing_pins_and_collisions(self):
        from spl_compiler.codecs import DataError
        module=library("arithmetic",'define result=1;')
        witnesses=[
            ({"modules":[],"imports":[importing("arithmetic")]},"UNRESOLVED_MODULE"),
            ({"modules":[module],"imports":[importing("arithmetic"),importing("arithmetic")]},"AMBIGUOUS_IMPORT"),
            ({"modules":[library("arithmetic",'define result=calculate();')],"imports":[importing("arithmetic")]},"FUNCTION_CALL_CYCLE"),
            ({"modules":[library("arithmetic",'define result=1;',imports=[importing("arithmetic",local="self")])],"imports":[importing("arithmetic")]},"MODULE_IMPORT_CYCLE"),
        ]
        directory=ROOT/".lake"/"fold-link-tests"
        directory.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            work=Path(temporary)
            source=work/"Source.spl"
            source.write_text(schedule('emit "x"=compute();'),encoding="utf-8")
            for manifest,code in witnesses:
                write_json(work/"link.json",manifest)
                with self.subTest(code=code),self.assertRaises(DataError) as raised:
                    lean(["--run",ROOT/"SPL/Main.lean","check",source,"--link",work/"link.json"])
                self.assertEqual(raised.exception.code,code)


if __name__=="__main__":
    unittest.main()
