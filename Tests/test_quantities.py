"""Independent Python dimensional semantics and emitted-source witnesses.

These tests deliberately do not invoke the native runtime or either Lean build.
The native/canonical integration suites supply the backend comparisons.
"""
from dataclasses import FrozenInstanceError
from fractions import Fraction
import unittest

from spl_compiler.checker import check_schedule, type_from_ast
from spl_compiler.dimensions import UNIT_DICTIONARY, UNITS, contains_dimension
from spl_compiler.emitter import emit_module, lean_value
from spl_compiler.evaluator import decode_value, evaluate, quantize
from spl_compiler.model import QuantityValue, RateValue, SPLException, Type, encode_value
from spl_compiler.parser import parse

HEADER = 'schedule Quantities language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'


def quantity(value, unit="Download"):
    return {"value": value, "unit": unit}


def rate(value, unit="Download"):
    return {"value": value, "per_unit": unit, "currency": "USD"}


def checked(body):
    return check_schedule(parse(HEADER + body + "}"))


class QuantityReferenceTests(unittest.TestCase):
    def run_source(self, body, inputs=None, openings=None):
        return evaluate(checked(body), inputs or {}, openings or {})

    def test_finite_type_vocabulary_and_shape(self):
        self.assertEqual(UNIT_DICTIONARY, "spl.units/1")
        self.assertEqual(UNITS, {"Download", "UsageMinute"})
        for text, expected in [("Quantity<Download>", Type("Quantity", (Type("Download"),))),
                               ("Rate<UsageMinute,USD>", Type("Rate", (Type("UsageMinute"), Type("USD"))))]:
            self.assertEqual(checked(f"input x:{text};").types["x"], expected)
        for text, code in [("Quantity<download>", "UNSUPPORTED_UNIT"), ("Quantity<Minute>", "UNSUPPORTED_UNIT"),
                           ("Rate<Download,EUR>", "UNSUPPORTED_CURRENCY"), ("Quantity<Download,USD>", "TYPE_ARITY"),
                           ("Rate<Download>", "TYPE_ARITY"), ("Quantity<List<Download>>", "UNSUPPORTED_TYPE")]:
            with self.subTest(text=text), self.assertRaises(SPLException) as raised:
                checked(f"input x:{text};")
            self.assertEqual(raised.exception.code, code)

    def test_exact_tagged_values_are_immutable(self):
        q = QuantityValue(Fraction(1, 3), "Download")
        r = RateValue(Fraction("1.5"), "Download")
        self.assertEqual(encode_value(q), quantity({"numerator": "1", "denominator": "3"}))
        self.assertEqual(encode_value(r), rate("1.5"))
        with self.assertRaises(FrozenInstanceError):
            q.unit = "UsageMinute"
        for constructor in [lambda: QuantityValue(Fraction(1), "Unknown"),
                            lambda: RateValue(Fraction(1), "Download", "EUR"),
                            lambda: QuantityValue(1.5, "Download")]:
            with self.assertRaises(SPLException):
                constructor()

    def test_strict_transport(self):
        qt = checked("input x:Quantity<Download>;").types["x"]
        rt = checked("input x:Rate<Download,USD>;").types["x"]
        for value, typ, code in [("1", qt, "INVALID_QUANTITY"), ({"value": "1"}, qt, "INVALID_QUANTITY"),
                                  (dict(quantity("1"), extra=True), qt, "INVALID_QUANTITY"),
                                  (quantity("1", "UsageMinute"), qt, "UNIT_MISMATCH"),
                                  (quantity("1", "unknown"), qt, "UNSUPPORTED_UNIT"),
                                  (quantity("1", None), qt, "INVALID_QUANTITY"),
                                  (quantity("1", True), qt, "INVALID_QUANTITY"),
                                  (quantity("1", ["Download"]), qt, "INVALID_QUANTITY"),
                                  (quantity(True), qt, "INVALID_EXACT_NUMBER"), (quantity(1.5), qt, "INVALID_EXACT_NUMBER"),
                                  (quantity({"numerator": "2", "denominator": "4"}), qt, "INVALID_EXACT_NUMBER"),
                                  (quantity("1"), rt, "INVALID_RATE"),
                                  (dict(rate("1"), currency="EUR"), rt, "CURRENCY_MISMATCH"),
                                  (dict(rate("1"), currency=None), rt, "INVALID_RATE"),
                                  (dict(rate("bad"), currency=True), rt, "INVALID_RATE"),
                                  (rate("1", {"unit": "Download"}), rt, "INVALID_RATE"),
                                  (rate("1", "UsageMinute"), rt, "UNIT_MISMATCH")]:
            with self.subTest(value=value), self.assertRaises(SPLException) as raised:
                decode_value(value, typ)
            self.assertEqual(raised.exception.code, code)
        self.assertEqual(decode_value(quantity("-0.125"), qt), QuantityValue(Fraction(-1, 8), "Download"))

    def test_synthetic_usage_and_participation(self):
        body = '''input q:Quantity<Download>; input r:Rate<Download,USD>;
          define gross=q*r; define participation=gross*0.50;
          emit "gross"=gross; emit "participation"=participation; emit "q"=q; emit "r"=r;'''
        out = self.run_source(body, {"q": quantity("100"), "r": rate("1.50")})
        self.assertEqual(out.status, "calculated")
        self.assertEqual(out.to_dict()["emissions"], {"gross": "150", "participation": "75", "q": quantity("100"), "r": rate("1.5")})
        multiply = next(t for t in out.trace if t["kind"] == "binary")
        self.assertEqual(multiply["operands"], [quantity("100"), rate("1.5")])
        for amount, expected in [("0", "0"), ("0.5", "0.375"), ("-2", "-1.5")]:
            self.assertEqual(self.run_source(body, {"q": quantity(amount), "r": rate("1.50")}).to_dict()["emissions"]["participation"], expected)

    def test_quantity_and_rate_arithmetic_matrix(self):
        for typ, make in [("Quantity<Download>", quantity), ("Rate<Download,USD>", rate)]:
            out = self.run_source(f'''input a:{typ}; input b:{typ};
              emit "add"=a+b; emit "subtract"=a-b; emit "negative"=-a;
              emit "left"=a*0.25; emit "right"=0.25*a; emit "literal"=a*2;
              emit "divide"=a/2; emit "ratio"=a/b;
              emit "less"=a<b; emit "equal"=a==b; emit "absolute"=abs(-a);
              emit "minimum"=min(a,b); emit "maximum"=max(a,b);''', {"a": make("2.5"), "b": make("5")})
            self.assertEqual(out.status, "calculated", out.diagnostics)
            self.assertEqual(out.to_dict()["emissions"], {"add": make("7.5"), "subtract": make("-2.5"), "negative": make("-2.5"),
                "left": make("0.625"), "right": make("0.625"), "literal": make("5"), "divide": make("1.25"), "ratio": "0.5",
                "less": True, "equal": False, "absolute": make("2.5"), "minimum": make("2.5"), "maximum": make("5")})
        reverse = self.run_source('input q:Quantity<UsageMinute>; input r:Rate<UsageMinute,USD>; emit "v"=r*q;',
                                  {"q": quantity("0.5", "UsageMinute"), "r": rate("0.25", "UsageMinute")})
        self.assertEqual(reverse.to_dict()["emissions"]["v"], "0.125")

    def test_mixed_dimensions_and_scalar_substitution_fail_statically(self):
        prefix = "input q:Quantity<Download>; input u:Quantity<UsageMinute>; input r:Rate<Download,USD>; input s:Rate<UsageMinute,USD>;"
        for expression in ["q+u", "q< u", "q==u", "q+r", "r+s", "q*q", "r*r", "q*s", "s*q", "q/u", "r/s", "q/r",
                           "USD 1/q", "q*USD 1", "q+1", "q==1", "q*1.0 + USD 1", "1.0/q"]:
            with self.subTest(expression=expression), self.assertRaises(SPLException) as raised:
                checked(prefix + f'emit "x"={expression};')
            self.assertEqual(raised.exception.code, "TYPE_MISMATCH")

    def test_demanded_zero_division_and_lazy_bodies(self):
        for typ, make in [("Quantity<Download>", quantity), ("Rate<Download,USD>", rate)]:
            for denominator in ["zero", "0.0"]:
                out = self.run_source(f'input x:{typ}; input zero:{typ}; emit "x"=x/{denominator};', {"x": make("1"), "zero": make("0")})
                self.assertEqual(out.status, "blocked")
                self.assertEqual(out.diagnostics[0]["code"], "DIVISION_BY_ZERO")
                self.assertEqual(out.emissions, {})
            out = self.run_source(f'input x:{typ}; emit "v"=if true then x else x/0.0;', {"x": make("1")})
            self.assertEqual(out.to_dict()["emissions"]["v"], make("1"))

    def test_all_rounding_modes_keep_dimension(self):
        cases = [("floor", "-1.1"), ("ceiling", "-1"), ("toward_zero", "-1"),
                 ("half_even", "-1"), ("half_away_from_zero", "-1.1")]
        for typ, make in [("Quantity<Download>", quantity), ("Rate<Download,USD>", rate)]:
            for mode, expected in cases:
                out = self.run_source(f'input v:{typ}; input step:{typ}; emit "v"=quantize(v,step,"{mode}");',
                                      {"v": make("-1.05"), "step": make("0.1")})
                self.assertEqual(out.to_dict()["emissions"]["v"], make(expected))
            for quantum in ["0", "-0.1"]:
                out = self.run_source(f'input v:{typ}; input step:{typ}; emit "v"=quantize(v,step,"floor");',
                                      {"v": make("1"), "step": make(quantum)})
                self.assertEqual(out.diagnostics[0]["code"], "INVALID_QUANTUM")
        with self.assertRaises(SPLException) as raised:
            quantize(QuantityValue(Fraction(1), "Download"), QuantityValue(Fraction(1), "UsageMinute"), "floor")
        self.assertEqual(raised.exception.code, "TYPE_MISMATCH")

    def test_empty_and_nonempty_typed_sums(self):
        for typ, make in [("Quantity<Download>", quantity), ("Rate<Download,USD>", rate)]:
            body = f'input xs:List<{typ}>; define total=sum(xs,x=>x); emit "total"=total;'
            for rows, total in [([], "0"), ([make("0.125"), make("0.375")], "0.5")]:
                out = self.run_source(body, {"xs": rows})
                self.assertEqual(out.to_dict()["emissions"]["total"], make(total))
            zero = self.run_source(body, {"xs": []})
            self.assertTrue(any(t.get("outcome") == "calculated_zero" for t in zero.trace))

    def test_nested_containers_mapping_and_fold_carry(self):
        body = '''input xs:List<{amount:Quantity<Download>,price:Rate<Download,USD>}>;
          opening carry:Quantity<Download> from "meter";
          define kept=filter(xs,x=>x.amount>=carry);
          define quantities=map(kept,x=>x.amount);
          define total=fold quantities from carry with state,event { yield state+event; };
          closing carry=total;
          emit "nested"=tuple(some({amount:total}),quantities);
          emit "map"=entries(make_map([1],k=>k,v=>total));'''
        rows = [{"amount": quantity("1"), "price": rate("2")}, {"amount": quantity("0.25"), "price": rate("2")}]
        out = self.run_source(body, {"xs": rows}, {"meter": quantity("0.5")})
        self.assertEqual(out.status, "calculated", out.diagnostics)
        self.assertEqual(out.to_dict()["closing"], {"carry": quantity("1.5")})
        self.assertEqual(out.to_dict()["emissions"]["nested"], [{"some": {"amount": quantity("1.5")}}, [quantity("1")]])
        self.assertEqual(out.to_dict()["emissions"]["map"], [{"key": "1", "value": quantity("1.5")}])
        self.assertTrue(contains_dimension(type_from_ast({"name": "List", "args": [{"name": "Quantity", "args": [{"name": "Download"}]}]})))

    def test_key_and_expected_type_guards(self):
        for body, code in [
            ('input xs:Map<Quantity<Download>,Int>;', "INVALID_MAP_KEY_TYPE"),
            ('input q:Quantity<Download>; emit "v"=make_map([1],k=>q,v=>v);', "INVALID_MAP_KEY_TYPE"),
            ('input q:Rate<Download,USD>; emit "v"=group_by([1],k=>q);', "INVALID_MAP_KEY_TYPE"),
            ('input q:Quantity<Download>; emit "v"=make_map([1],k=>tuple(q,k),v=>v);', "INVALID_MAP_KEY_TYPE"),
            ('input q:Rate<Download,USD>; emit "v"=group_by([1],k=>tuple(q,k));', "INVALID_MAP_KEY_TYPE"),
            ('input xs:List<Quantity<Download>>; input z:Quantity<Download>; define v=ordered_fold xs from z by k=>k identified by i=>i ties "reject" with s,e {yield s+e;};', "INVALID_EVENT_KEY_TYPE"),
            ('input xs:List<Quantity<Download>>; input z:Quantity<Download>; define v=ordered_fold xs from z by k=>tuple(k,1) identified by i=>1 ties "reject" with s,e {yield s+e;};', "INVALID_EVENT_KEY_TYPE"),
            ('input q:Quantity<Download>; define r:Ratio=q;', "TYPE_MISMATCH"),
            ('input q:Quantity<Download>; input r:Rate<Download,USD>; emit "v"=quantize(q,r,"floor");', "TYPE_MISMATCH"),
        ]:
            with self.subTest(body=body), self.assertRaises(SPLException) as raised:
                checked(body)
            self.assertEqual(raised.exception.code, code)

    def test_nested_transport_is_strict_before_demand(self):
        body = '''input nested:Option<Tuple<Quantity<Download>,List<Rate<Download,USD>>>>;
          input indexed:Map<Int,Quantity<UsageMinute>>;
          emit "nested"=nested; emit "indexed"=entries(indexed);'''
        nested = {"some": [quantity("0.5"), [rate({"numerator": "1", "denominator": "3"})]]}
        indexed = [{"key": "1", "value": quantity("2", "UsageMinute")}]
        out = self.run_source(body, {"nested": nested, "indexed": indexed})
        self.assertEqual(out.to_dict()["emissions"], {"nested": nested, "indexed": indexed})
        bad = {"some": [quantity("0.5"), [rate("1", "UsageMinute")]]}
        out = self.run_source(body, {"nested": bad, "indexed": indexed})
        self.assertEqual(out.diagnostics[0]["code"], "UNIT_MISMATCH")
        self.assertEqual(out.emissions, {})

    def test_sorting_and_typed_function_imports(self):
        from spl_compiler.linker import link_schedule
        from Tests.test_linking import importing, library
        qast = {"name": "Quantity", "args": [{"name": "Download", "args": []}]}
        rast = {"name": "Rate", "args": [{"name": "Download", "args": []}, {"name": "USD", "args": []}]}
        module = library("arithmetic", "input q:Quantity<Download>; input r:Rate<Download,USD>; define result=q*r;",
                         parameters=[{"name": "q", "type": qast}, {"name": "r", "type": rast}])
        module["descriptor"]["interface"]["exports"][0]["result"] = {"name": "Money", "args": [{"name": "USD", "args": []}]}
        syntax = parse(HEADER + 'input q:Quantity<Download>; input r:Rate<Download,USD>; emit "v"=compute(q,r);}')
        linked = link_schedule(syntax, {"modules": [module], "imports": [importing("arithmetic")]})
        out = evaluate(check_schedule(linked), {"q": quantity("100"), "r": rate("1.5")}, {})
        self.assertEqual(out.to_dict()["emissions"]["v"], "150")
        sorted_out = self.run_source('input xs:List<Quantity<Download>>; emit "v"=sort_by(xs,x=>x);',
                                     {"xs": [quantity("2"), quantity("-0.5"), quantity("0")]})
        self.assertEqual(sorted_out.to_dict()["emissions"]["v"], [quantity("-0.5"), quantity("0"), quantity("2")])

    def test_recursive_scalar_tuple_sort_and_comparison(self):
        body = '''input xs:List<{identity:Int,q:Quantity<Download>,r:Rate<Download,USD>}>;
          define ordered=sort_by(xs,x=>tuple(x.q,tuple(x.r,x.identity)));
          emit "identities"=map(ordered,x=>x.identity);
          input q:Quantity<Download>; input r:Rate<Download,USD>;
          emit "less"=tuple(q,tuple(r,1))<tuple(q,tuple(r,2));
          emit "equal_bound"=tuple(q,r)<=tuple(q,r);
          emit "greater"=tuple(q,tuple(r,3))>tuple(q,tuple(r,2));
          emit "greater_equal"=tuple(q,r)>=tuple(q,r);'''
        rows = [{"identity": "3", "q": quantity("2"), "r": rate("1")},
                {"identity": "2", "q": quantity("1"), "r": rate("1.5")},
                {"identity": "1", "q": quantity("1"), "r": rate("0.5")},
                {"identity": "0", "q": quantity("-1"), "r": rate("5")}]
        out = self.run_source(body, {"xs": rows, "q": quantity("1"), "r": rate("0.5")})
        self.assertEqual(out.status, "calculated", out.diagnostics)
        self.assertEqual(out.to_dict()["emissions"], {"identities": ["0", "1", "2", "3"],
            "less": True, "equal_bound": True, "greater": True, "greater_equal": True})
        with self.assertRaises(SPLException) as raised:
            checked('input xs:List<Quantity<Download>>; emit "v"=sort_by(xs,x=>tuple(x,true));')
        self.assertEqual(raised.exception.code, "TYPE_MISMATCH")

    def test_emitter_preserves_tags_and_typed_empty_sum(self):
        q = QuantityValue(Fraction(1, 3), "Download")
        r = RateValue(Fraction("1.5"), "Download")
        self.assertEqual(lean_value(q), '(.quantity "Download" (mkRat (1) 3))')
        self.assertEqual(lean_value(r), '(.rate "Download" "USD" (mkRat (3) 2))')
        for typ, zero in [("Quantity<Download>", '(.quantity "Download" (mkRat (0) 1))'),
                          ("Rate<Download,USD>", '(.rate "Download" "USD" (mkRat (0) 1))')]:
            module = emit_module(checked(f'input xs:List<{typ}>; emit "v"=sum(xs,x=>abs(x));'), {"xs": []}, {})
            self.assertIn("SPL.sumValuesFrom " + zero, module)
            self.assertIn("SPL.absolute", module)
        self.assertEqual(lean_value(quantity("0.5")), '(.quantity "Download" (mkRat (1) 2))')
        with self.assertRaises(SPLException):
            lean_value(quantity(0.5))


class QuantityGeneratedTests(unittest.TestCase):
    def test_actual_python_emitted_dimensional_execution(self):
        from spl_compiler.emitter import run_generated
        from spl_compiler.run import normalize_target
        body = '''input q:Quantity<Download>; input r:Rate<Download,USD>;
          input quantum:Quantity<Download>; input empty:List<Quantity<Download>>;
          emit "product"=q*r; emit "sum"=q+q; emit "negative"=-q;
          emit "empty"=sum(empty,x=>x);
          emit "rounded"=quantize(q,quantum,"half_even");
          emit "tuple_less"=tuple(q/2,r)<tuple(q,r);
          emit "ordered"=sort_by([tuple(q,r),tuple(q/2,r)],x=>x);'''
        program = checked(body)
        bindings = {"q": quantity("2.5"), "r": rate("1.5"), "quantum": quantity("1"), "empty": []}
        actual = normalize_target(run_generated(program, bindings, {}))
        self.assertEqual(actual["status"], "calculated", actual)
        self.assertEqual(actual["emissions"], {"product": "3.75", "sum": quantity("5"),
            "negative": quantity("-2.5"), "empty": quantity("0"), "rounded": quantity("2"),
            "tuple_less": True, "ordered": [[quantity("1.25"), rate("1.5")], [quantity("2.5"), rate("1.5")]]})
        self.assertEqual(actual["emissions"], evaluate(program, bindings, {}).to_dict()["emissions"])


if __name__ == "__main__":
    unittest.main()
