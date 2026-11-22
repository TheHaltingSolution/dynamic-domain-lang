"""First-order linking, strict argument demand and hygienic module scopes."""
import unittest

from spl_compiler.checker import check_schedule as check
from spl_compiler.evaluator import evaluate
from spl_compiler.linker import link_schedule
from spl_compiler.model import SPLException
from spl_compiler.parser import parse
from Tests.test_fold import schedule


def ref(name):
    return dict(id="test:"+name, revision="1", locator=name+".json", sha256="a"*64)


def library(name, source, *, parameters=None, result="Int", definition="result", imports=None, export="calculate"):
    return {"reference":ref(name), "source":schedule(source), "descriptor":{
        "id":"test:"+name,"revision":"1","imports":imports or [],"interface":{"exports":[{
            "name":export,"parameters":parameters or [],"result":{"name":result,"args":[]},"definition":definition}]}}}


def importing(name, export="calculate", local="compute"):
    return {"module_ref":ref(name),"alias":name,"symbols":[{"export":export,"local":local}]}


class LinkingTests(unittest.TestCase):
    def run_link(self, body, module):
        linked = link_schedule(parse(schedule(body)), {"modules":[module],"imports":[importing("arithmetic")]})
        return evaluate(check(linked), {}, {})

    def test_function_assertions_and_capture_isolation(self):
        module = library("arithmetic", 'input a:Int; define hidden=5; require a >= 0 else "POSITIVE"; define result=a+hidden;',
                         parameters=[{"name":"a","type":{"name":"Int","args":[]}}])
        out = self.run_link('define hidden=100; define a=999; emit "x"=compute(3);', module)
        self.assertEqual(out.to_dict()["emissions"]["x"], "8")
        self.assertEqual(self.run_link('emit "x"=compute(-1);', module).diagnostics[0]["code"], "POSITIVE")

    def test_unused_argument_strict_once_and_left_to_right(self):
        module = library("arithmetic", 'input a:Ratio; input b:Ratio; define result=a+a;', result="Ratio",
            parameters=[{"name":n,"type":{"name":"Ratio","args":[]}} for n in ["a","b"]])
        out = self.run_link('emit "x"=compute(1.0+2.0,4.0);', module)
        self.assertEqual(out.to_dict()["emissions"]["x"], "6")
        self.assertEqual(len([t for t in out.trace if t["kind"]=="binary" and t.get("operands")==["1","2"]]), 1)
        self.assertEqual(self.run_link('emit "x"=compute(1.0,1.0/0.0);', module).diagnostics[0]["code"], "DIVISION_BY_ZERO")
        self.assertEqual(self.run_link('emit "x"=compute(quantize(1.0,0.0,"floor"),1.0/0.0);', module).diagnostics[0]["code"], "INVALID_QUANTUM")

    def test_transitive_function_calls(self):
        inner = library("inner", 'input n:Int; define result=n*2;', parameters=[{"name":"n","type":{"name":"Int","args":[]}}])
        outer = library("outer", 'input n:Int; define result=twice(n)+1;', parameters=[{"name":"n","type":{"name":"Int","args":[]}}],
                        imports=[importing("inner", local="twice")])
        linked = link_schedule(parse(schedule('emit "x"=calculate(3);')), {"modules":[inner,outer],"imports":[importing("outer",local="calculate")]})
        self.assertEqual(evaluate(check(linked),{},{}).to_dict()["emissions"]["x"], "7")

    def test_missing_pin_collision_and_cycles(self):
        module = library("arithmetic", 'define result=1;')
        bad = [
            {"modules":[],"imports":[importing("arithmetic")]},
            {"modules":[module],"imports":[importing("arithmetic"),importing("arithmetic")]},
            {"modules":[library("arithmetic",'define result=calculate();')],"imports":[importing("arithmetic")]},
            {"modules":[library("arithmetic",'define result=1;',imports=[importing("arithmetic",local="self")])],"imports":[importing("arithmetic")]},
        ]
        for manifest in bad:
            with self.assertRaises(SPLException):
                link_schedule(parse(schedule('emit "x"=compute();')),manifest)

    def test_export_type_and_argument_type_checked(self):
        module = library("arithmetic",'input a:Int; define result=a;',parameters=[{"name":"a","type":{"name":"Int","args":[]}}])
        with self.assertRaises(SPLException):
            self.run_link('emit "x"=compute(true);',module)
        module["descriptor"]["interface"]["exports"][0]["result"]={"name":"Bool","args":[]}
        with self.assertRaises(SPLException):
            self.run_link('emit "x"=compute(1);',module)


if __name__ == "__main__":
    unittest.main()

