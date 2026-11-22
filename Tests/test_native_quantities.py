"""Four executable backends for quantities; no runtime dependency rebuilds.

SPL_QUANTITIES_REFERENCE_ONLY=1 checks fixtures without invoking Lean.
Ordinary runs compare Python reference, native IR, native emitted Lean, and
Python emitted Lean. Financial-policy controls are tested separately.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, loads, write_json
from spl_compiler.emitter import emit_module
from spl_compiler.evaluator import decode_value, evaluate
from spl_compiler.lean_tools import ROOT, compile_schedule, interpret_schedule, lean
from spl_compiler.linker import link_schedule
from spl_compiler.model import SPLException
from spl_compiler.parser import parse
from spl_compiler.run import normalize_target
from Tests.test_linking import importing, library

HEADER = 'schedule NativeQuantities language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {'
REFERENCE_ONLY = os.environ.get("SPL_QUANTITIES_REFERENCE_ONLY") == "1"


def quantity(value, unit="Download"):
    return {"value": value, "unit": unit}


def rate(value, unit="Download"):
    return {"value": value, "per_unit": unit, "currency": "USD"}


def source(body):
    return HEADER + body + "}"


def checked(body, links=None):
    ast = parse(source(body))
    return check_schedule(link_schedule(ast, links) if links else ast)


class NativeQuantityTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / ".lake" / "native-quantity-tests"
        directory.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)

    def compare(self, body, cases, links=None):
        """Compile once per source, then compare supplied binding sets."""
        program = checked(body, links)
        authored = self.work / "Source.spl"
        authored.write_text(source(body), encoding="utf-8")
        link_path = self.work / "links.json" if links else None
        if links:
            write_json(link_path, links)
        emitted = None if REFERENCE_ONLY else compile_schedule(authored, self.work / "Settlement.lean", link=link_path)
        results = []
        for index, (inputs, openings) in enumerate(cases):
            reference = normalize_target(evaluate(program, inputs, openings).to_dict())
            outcomes = {"reference": reference}
            if not REFERENCE_ONLY:
                bindings = self.work / f"bindings-{index}.json"
                write_json(bindings, {"inputs": inputs, "openings": openings})
                outcomes["native_ir"] = normalize_target(interpret_schedule(authored, bindings, link=link_path))
                outcomes["native_emitted"] = normalize_target(loads(lean(["--run", emitted, bindings])))
                decoded_inputs = {name: decode_value(value, program.types[name]) for name, value in inputs.items()}
                decoded_openings = {name: decode_value(value, program.types[name]) for name, value in openings.items()}
                mirror = self.work / f"Mirror-{index}.lean"
                mirror.write_text(emit_module(program, decoded_inputs, decoded_openings), encoding="utf-8")
                outcomes["python_emitted"] = normalize_target(loads(lean(["--run", mirror])))
                for backend, actual in outcomes.items():
                    with self.subTest(backend=backend, case=index):
                        for field in ("status", "emissions", "closing"):
                            self.assertEqual(canonical(actual[field]), canonical(reference[field]), field)
                        self.assertEqual([d["code"] for d in actual["diagnostics"]],
                                         [d["code"] for d in reference["diagnostics"]])
                seen = set()
                for node in outcomes["native_ir"]["trace"]:
                    self.assertTrue(set(node["dependencies"]) <= seen)
                    seen.add(node["node_id"])
            results.append(outcomes)
        return results

    def native_batch(self, expressions):
        """Batch pure native boundary checks in one Lean process."""
        if REFERENCE_ONLY:
            return None
        driver = self.work / "Boundary.lean"
        driver.write_text('import SPL\n\ndef main : IO Unit := do\n' +
                          '\n'.join('  IO.println (' + expression + ')' for expression in expressions) + '\n', encoding="utf-8")
        return lean(["--run", driver]).splitlines()

    def test_arithmetic_both_units_rates_rounding_and_typed_zero(self):
        declarations, bindings = [], {}
        profiles = [("download", "Quantity<Download>", quantity),
                    ("download_rate", "Rate<Download,USD>", rate),
                    ("minute", "Quantity<UsageMinute>", lambda v: quantity(v, "UsageMinute")),
                    ("minute_rate", "Rate<UsageMinute,USD>", lambda v: rate(v, "UsageMinute"))]
        for suffix, typ, make in profiles:
            value, step, empty = "v_" + suffix, "step_" + suffix, "empty_" + suffix
            declarations.append(f"input {value}:{typ}; input {step}:{typ}; input {empty}:List<{typ}>;")
            bindings.update({value: make("-1.05"), step: make("0.1"), empty: []})
            expressions = [("add", f"{value}+{value}"), ("subtract", f"{value}-{value}"),
                           ("negate", f"-{value}"), ("absolute", f"abs({value})"),
                           ("scale", f"{value}*0.5"), ("scale_left", f"0.5*{value}"),
                           ("divide", f"{value}/2"), ("cancel", f"{value}/{value}"),
                           ("minimum", f"min({value},{step})"), ("maximum", f"max({value},{step})"),
                           ("less", f"{value}<{step}"), ("equal", f"{value}=={value}"),
                           ("zero", f"sum({empty},item=>item)")]
            for name, expr in expressions:
                declarations.append(f'emit "{suffix}_{name}"={expr};')
            for mode in ["floor", "ceiling", "toward_zero", "half_even", "half_away_from_zero"]:
                declarations.append(f'emit "{suffix}_{mode}"=quantize({value},{step},"{mode}");')
        declarations += ['input downloads:Quantity<Download>; input price:Rate<Download,USD>;',
                         'emit "gross"=downloads*price; emit "reverse"=price*downloads;',
                         'emit "share"=(downloads*price)*0.5; emit "signed"=v_download*price;',
                         'emit "minutes"=v_minute*v_minute_rate;']
        bindings.update(downloads=quantity("100"), price=rate("1.5"))
        outcomes = self.compare("".join(declarations), [(bindings, {})])[0]
        self.assertEqual(outcomes["reference"]["status"], "calculated")
        actual = outcomes["reference"]["emissions"]
        self.assertEqual((actual["gross"], actual["share"], actual["signed"]), ("150", "75", "-1.575"))
        self.assertEqual(actual["minute_zero"], quantity("0", "UsageMinute"))
        self.assertEqual(actual["download_rate_half_even"], rate("-1"))
        self.assertEqual(actual["minute_rate_half_away_from_zero"], rate("-1.1", "UsageMinute"))
        if "native_ir" in outcomes:
            nodes = outcomes["native_ir"]["trace"]
            self.assertTrue(any(n["value_type"] == {"kind": "quantity", "unit": "UsageMinute"} for n in nodes))
            self.assertTrue(any(n["value_type"] == {"kind": "rate", "unit": "Download", "currency": "USD"} for n in nodes))
            self.assertTrue(any(n.get("outcome") == "calculated_zero" and n.get("result") == quantity("0") for n in nodes))

    def test_nested_containers_fold_tuple_sort_and_typed_imports(self):
        q_ast = {"name": "Quantity", "args": [{"name": "Download", "args": []}]}
        r_ast = {"name": "Rate", "args": [{"name": "Download", "args": []}, {"name": "USD", "args": []}]}
        halve = library("halve", "input amount:Quantity<Download>; define result=amount*0.5;",
                        parameters=[{"name": "amount", "type": q_ast}])
        halve["descriptor"]["interface"]["exports"][0]["result"] = q_ast
        gross = library("gross", "input amount:Quantity<Download>; input price:Rate<Download,USD>; define result=amount*price;",
                        result="Money", parameters=[{"name": "amount", "type": q_ast}, {"name": "price", "type": r_ast}])
        gross["descriptor"]["interface"]["exports"][0]["result"] = {"name": "Money", "args": [{"name": "USD", "args": []}]}
        links = {"modules": [halve, gross], "imports": [importing("halve", local="half_quantity"), importing("gross", local="price_quantity")]}
        body = '''input rows:List<{id:Int,amount:Quantity<Download>,price:Rate<Download,USD>}>;
          input nested:Option<Tuple<Quantity<Download>,List<Rate<Download,USD>>>>;
          input indexed:Map<Int,Quantity<UsageMinute>>;
          opening carry:Quantity<Download> from "carry";
          define sorted=sort_by(rows,row=>tuple(row.amount,row.price,row.id));
          define kept=filter(sorted,row=>row.amount>=carry);
          define quantities=map(kept,row=>half_quantity(row.amount));
          define total=fold quantities from carry with state,event {yield state+event;};
          closing carry=total;
          emit "nested"=nested; emit "indexed"=entries(indexed); emit "sorted"=sorted;
          emit "wrapped"=tuple(some({amount:total}),quantities);
          emit "function_total"=sum(kept,row=>price_quantity(row.amount,row.price));'''
        rows = [{"id": "3", "amount": quantity("2"), "price": rate("1")},
                {"id": "2", "amount": quantity("1"), "price": rate("2")},
                {"id": "1", "amount": quantity("1"), "price": rate("1")}]
        nested = {"some": [quantity({"numerator": "1", "denominator": "3"}), [rate("1.5")]]}
        indexed = [{"key": "1", "value": quantity("0.5", "UsageMinute")}]
        result = self.compare(body, [({"rows": rows, "nested": nested, "indexed": indexed}, {"carry": quantity("0.5")})], links)[0]["reference"]
        self.assertEqual(result["status"], "calculated")
        self.assertEqual(result["closing"], {"carry": quantity("2.5")})
        self.assertEqual([r["id"] for r in result["emissions"]["sorted"]], ["1", "2", "3"])
        self.assertEqual(result["emissions"]["function_total"], "5")
        self.assertEqual(result["emissions"]["nested"], nested)

    def test_atomic_failure_discards_provisional_outputs_and_closing(self):
        body = '''input divisor:Quantity<Download>; input quantum:Quantity<Download>; input divide:Bool;
          opening carry:Quantity<Download> from "carry";
          emit "provisional"=carry; closing carry=carry+carry;
          emit "late"=if divide then carry/divisor>0.0 else quantize(carry,quantum,"floor")>carry;'''
        cases = [({"divisor": quantity("0"), "quantum": quantity("1"), "divide": True}, {"carry": quantity("2")}),
                 ({"divisor": quantity("1"), "quantum": quantity("0"), "divide": False}, {"carry": quantity("2")}),
                 ({"divisor": quantity("1"), "quantum": quantity("0"), "divide": True}, {"carry": quantity("2")})]
        results = self.compare(body, cases)
        for outcomes, expected in zip(results, ["DIVISION_BY_ZERO", "INVALID_QUANTUM", None]):
            for actual in outcomes.values():
                self.assertEqual([d["code"] for d in actual["diagnostics"]], [expected] if expected else [])
                if expected:
                    self.assertEqual((actual["emissions"], actual["closing"]), ({}, {}))
            if expected and "native_ir" in outcomes:
                trace = outcomes["native_ir"]["trace"]
                self.assertTrue(any(n["kind"] == "emit" and n["status"] == "discarded" for n in trace))
                self.assertTrue(any(n["kind"] == "closing" and n["status"] == "discarded" for n in trace))

    def test_static_mismatches_and_key_dimensions_rejected(self):
        prefix = "input q:Quantity<Download>; input u:Quantity<UsageMinute>; input r:Rate<Download,USD>; input s:Rate<UsageMinute,USD>;"
        cases = [(prefix + f'emit "x"={expr};', "TYPE_MISMATCH") for expr in
                 ["q+u", "q<u", "q==u", "q+r", "r+s", "q*q", "r*r", "q*s", "s*q", "q/u", "r/s", "q/r", "USD 1/q", "q*USD 1", "q+1", "q==1", "1.0/q", 'quantize(q,r,"floor")']]
        cases += [("input q:Quantity<Unknown>;", "UNSUPPORTED_UNIT"),
                  ("input r:Rate<Download,EUR>;", "UNSUPPORTED_CURRENCY"),
                  ("input m:Map<Quantity<Download>,Int>;", "INVALID_MAP_KEY_TYPE"),
                  (prefix + 'emit "x"=make_map([1],k=>q,v=>v);', "INVALID_MAP_KEY_TYPE"),
                  ('input rows:List<Quantity<Download>>; input q:Quantity<Download>; define v=ordered_fold rows from q by k=>k identified by i=>i ties "reject" with state,event {yield state+event;};', "INVALID_EVENT_KEY_TYPE")]
        for body, code in cases:
            with self.subTest(body=body), self.assertRaises(SPLException) as raised:
                checked(body)
            self.assertEqual(raised.exception.code, code)
        expressions = []
        for body, _ in cases:
            literal = json.dumps(source(body), ensure_ascii=True)
            expressions.append(f'(match SPL.Parser.parse {literal} >>= SPL.Check.check with | .ok _ => "ACCEPTED" | .error d => d.code)')
        actual = self.native_batch(expressions)
        if actual is not None:
            self.assertEqual(actual, [code for _, code in cases])

    def test_strict_dimensional_binding_tags_and_eager_nested_decode(self):
        q_type = checked("input v:Quantity<Download>;").types["v"]
        r_type = checked("input v:Rate<Download,USD>;").types["v"]
        cases = [(None, q_type, '.quantity "Download"', "NULL_NOT_ALLOWED"),
                 ("1", q_type, '.quantity "Download"', "INVALID_QUANTITY"),
                 ({"value": "1"}, q_type, '.quantity "Download"', "INVALID_QUANTITY"),
                 (dict(quantity("1"), extra=True), q_type, '.quantity "Download"', "INVALID_QUANTITY"),
                 (quantity("1", "UsageMinute"), q_type, '.quantity "Download"', "UNIT_MISMATCH"),
                 (quantity("1", "unknown"), q_type, '.quantity "Download"', "UNSUPPORTED_UNIT"),
                 (quantity(True), q_type, '.quantity "Download"', "INVALID_EXACT_NUMBER"),
                 (quantity("1"), r_type, '.rate "Download" "USD"', "INVALID_RATE"),
                 (dict(rate("1"), currency="EUR"), r_type, '.rate "Download" "USD"', "CURRENCY_MISMATCH"),
                 (dict(rate("1"), per_unit=True), r_type, '.rate "Download" "USD"', "INVALID_RATE"),
                 (rate("1", "UsageMinute"), r_type, '.rate "Download" "USD"', "UNIT_MISMATCH")]
        expressions = []
        for value, typ, native_type, code in cases:
            with self.subTest(value=value), self.assertRaises(SPLException) as raised:
                decode_value(value, typ)
            self.assertEqual(raised.exception.code, code)
            literal = json.dumps(json.dumps(value, separators=(",", ":")), ensure_ascii=True)
            expressions.append(f'(match SPL.Bindings.parseStrict {literal} >>= SPL.Bindings.decode ({native_type}) with | .ok _ => "ACCEPTED" | .error code => code)')
        native_codes = [code for _, _, _, code in cases]
        # The raw native JSON profile rejects number tokens before typed decoding;
        # the Python decoder receives already-parsed objects and rejects the float.
        for value, typ, native_type in [(quantity(1.5), q_type, '.quantity "Download"'),
                                        (rate(1.5), r_type, '.rate "Download" "USD"')]:
            with self.assertRaises(SPLException) as raised:
                decode_value(value, typ)
            self.assertEqual(raised.exception.code, "INVALID_EXACT_NUMBER")
            literal = json.dumps(json.dumps(value, separators=(",", ":")), ensure_ascii=True)
            expressions.append(f'(match SPL.Bindings.parseStrict {literal} >>= SPL.Bindings.decode ({native_type}) with | .ok _ => "ACCEPTED" | .error code => code)')
            native_codes.append("JSON_NUMBER_NOT_ALLOWED")
        actual = self.native_batch(expressions)
        if actual is not None:
            self.assertEqual(actual, native_codes)
        body = 'input nested:Option<List<Quantity<Download>>>; emit "unrelated"=USD 1;'
        inputs = {"nested": {"some": [quantity("1", "UsageMinute")]}}
        reference = evaluate(checked(body), inputs, {}).to_dict()
        self.assertEqual(reference["diagnostics"][0]["code"], "UNIT_MISMATCH")
        self.assertEqual(reference["emissions"], {})
        if not REFERENCE_ONLY:
            authored = self.work / "Malformed.spl"
            authored.write_text(source(body), encoding="utf-8")
            bindings = self.work / "malformed.json"
            write_json(bindings, {"inputs": inputs, "openings": {}})
            emitted = compile_schedule(authored, self.work / "Malformed.lean")
            for actual in [interpret_schedule(authored, bindings), loads(lean(["--run", emitted, bindings]))]:
                self.assertEqual(actual["diagnostics"][0]["code"], "UNIT_MISMATCH")
                self.assertEqual((actual["emissions"], actual["closing"]), ({}, {}))


if __name__ == "__main__":
    unittest.main()
