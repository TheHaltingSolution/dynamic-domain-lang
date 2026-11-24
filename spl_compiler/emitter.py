"""Hygienic Lean emission for checked SPL and a disposable execution driver.

The emitted settlement is pure and parameterized. A driver may embed an already
validated input snapshot for reproducible `lean --run` comparisons; this does
not specialize the settlement or compute answers in Python.
"""

from __future__ import annotations

from datetime import date, datetime
from fractions import Fraction
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from .model import InstantValue, MapValue, OptionValue, QuantityValue, RateValue
from .dimensions import typed_zero


def _string(value: str) -> str:
    # Lean strings support these JSON escapes; escape non-ASCII directly rather
    # than introducing JSON-only \u surrogate escapes.
    return json.dumps(value, ensure_ascii=False).replace("\\b", "\\x08").replace("\\f", "\\x0c")


def _list(items) -> str:
    return "[" + ", ".join(items) + "]"


def _pair(key: str, value: str) -> str:
    return f"({_string(key)}, {value})"


def _do(lines: list[str], result: str) -> str:
    return "(do\n" + "\n".join("  " + line.replace("\n", "\n  ") for line in lines) + (
        "\n" if lines else ""
    ) + "  " + result.replace("\n", "\n  ") + ")"


def _fraction(value) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, dict):
        if "currency" in value and "value" in value:
            return _fraction(value["value"])
        if set(value) == {"numerator", "denominator"}:
            return Fraction(int(value["numerator"]), int(value["denominator"]))
    return Fraction(value)


def lean_value(value) -> str:
    """Render validated Python values without ever passing through float."""
    if isinstance(value, bool):
        return f"(.flag {'true' if value else 'false'})"
    if isinstance(value, QuantityValue):
        number = value.value
        return f"(.quantity {_string(value.unit)} (mkRat ({number.numerator}) {number.denominator}))"
    if isinstance(value, RateValue):
        number = value.value
        return f"(.rate {_string(value.per_unit)} {_string(value.currency)} (mkRat ({number.numerator}) {number.denominator}))"
    if isinstance(value, InstantValue):
        number = value.seconds
        return f"(.instant (mkRat ({number.numerator}) {number.denominator}) {_string(value.canonical)})"
    if isinstance(value, (Fraction, int)):
        number = _fraction(value)
        return f"(.num (mkRat ({number.numerator}) {number.denominator}))"
    if isinstance(value, (date, datetime)):
        return f"(.text {_string(value.isoformat())})"
    if isinstance(value, str):
        return f"(.text {_string(value)})"
    if value is None:
        return ".absent"
    if isinstance(value, OptionValue):
        return "(.present " + lean_value(value.value) + ")" if value.present else ".absent"
    if isinstance(value, MapValue):
        return "(.map " + _list(lean_value({"key":k,"value":v}) for k,v in value.entries) + ")"
    if isinstance(value, tuple):
        return "(.tuple " + _list(lean_value(item) for item in value) + ")"
    if isinstance(value, list):
        return "(.seq " + _list(lean_value(item) for item in value) + ")"
    if isinstance(value, dict):
        if set(value) == {"value", "unit"}:
            from .evaluator import parse_exact
            return lean_value(QuantityValue(parse_exact(value["value"]), value["unit"]))
        if set(value) == {"value", "per_unit", "currency"}:
            from .evaluator import parse_exact
            return lean_value(RateValue(parse_exact(value["value"]), value["per_unit"], value["currency"]))
        if (set(value) == {"numerator", "denominator"}) or (
            set(value) == {"value", "currency"}
        ):
            return lean_value(_fraction(value))
        return "(.obj " + _list(_pair(key, lean_value(item)) for key, item in value.items()) + ")"
    raise TypeError(f"Cannot embed unchecked Lean target value: {type(value).__name__}")


def _ordered_references(expr, bound=frozenset()):
    """Free names in left-to-right syntax order, retaining first use order."""
    if not isinstance(expr, dict):
        return []
    kind = expr.get("kind")
    if kind == "name":
        return [] if expr["name"] in bound else [expr["name"]]
    if kind in {"unary", "field"}:
        return _ordered_references(expr["expr"], bound)
    if kind == "binary":
        return _ordered_references(expr["left"], bound) + _ordered_references(expr["right"], bound)
    if kind == "if":
        return sum((_ordered_references(expr[key], bound) for key in ("condition", "then", "else")), [])
    if kind == "call":
        return sum((_ordered_references(arg, bound) for arg in expr["args"]), [])
    if kind == "apply":
        return sum((_ordered_references(arg,bound) for arg in expr["args"]),[])
    if kind == "fold":
        local = bound | {expr["state"],expr["event"]} | {d["name"] for d in expr["declarations"] if d["kind"] == "define"}
        result = _ordered_references(expr["initial"],bound)+_ordered_references(expr["source"],bound)
        if expr.get("order"):
            order = expr["order"]
            result += _ordered_references(order["key"],bound | {order["key_binder"]})
            result += _ordered_references(order["identity"],bound | {order["id_binder"]})
        return result+sum((_ordered_references(d.get("expr"),local) for d in expr["declarations"]),[])+_ordered_references(expr["body"],local)
    if kind == "lambda":
        return _ordered_references(expr["body"], bound | {expr["name"]})
    if kind == "record":
        return sum((_ordered_references(value, bound) for _, value in expr["fields"]), [])
    if kind == "list":
        return sum((_ordered_references(value, bound) for value in expr["items"]), [])
    if kind == "select_rules":
        result = sum((_ordered_references(arm["predicate"], bound) + _ordered_references(arm["body"], bound)
                      for arm in expr["arms"]), [])
        fallback = expr.get("otherwise")
        return result + _ordered_references(fallback["body"] if fallback else None, bound)
    if kind == "choose":
        result = sum((_ordered_references(predicate, bound) + _ordered_references(body, bound)
                      for predicate, body in expr["arms"]), [])
        return result + _ordered_references(expr.get("otherwise"), bound)
    if kind == "for":
        local = bound | {expr["name"]} | {d["name"] for d in expr["declarations"] if d["kind"] == "define"}
        return (_ordered_references(expr["source"], bound)
                + sum((_ordered_references(d.get("expr"), local) for d in expr["declarations"]), [])
                + _ordered_references(expr["yield"], local))
    return []


class _Emitter:
    def __init__(self):
        self.counter = 0

    def fresh(self):
        value = f"_spl_v{self.counter}"
        self.counter += 1
        return value

    def expression(self, expr, env):
        kind = expr["kind"]
        if kind in {"number", "money"}:
            return "(pure " + lean_value(Fraction(expr["value"])) + ")"
        if kind in {"bool", "text", "date"}:
            return "(pure " + lean_value(expr["value"]) + ")"
        if kind == "name":
            return env[expr["name"]]
        if kind == "field":
            return _do([], f"SPL.field (← {self.expression(expr['expr'], env)}) {_string(expr['name'])}")
        if kind == "unary":
            dimensional = expr["expr"]["_type"].name in {"Quantity", "Rate"}
            target = "SPL.Core.numericUnary" if expr["op"] == "-" and not dimensional else f"SPL.unary {_string(expr['op'])}"
            return _do([], f"{target} (← {self.expression(expr['expr'], env)})")
        if kind == "binary":
            left = self.expression(expr["left"], env)
            right = self.expression(expr["right"], env)
            if expr["op"] in {"and", "or"}:
                function = "conjunction" if expr["op"] == "and" else "disjunction"
                return f"(SPL.{function} {left} (fun _ => {right}))"
            arithmetic = {"+": "add", "-": "subtract", "*": "multiply", "/": "divide"}.get(expr["op"])
            dimensional = any(expr[key]["_type"].name in {"Quantity", "Rate"} for key in ("left", "right"))
            target = f"SPL.Core.numericBinary .{arithmetic}" if arithmetic and not dimensional else f"SPL.binary {_string(expr['op'])}"
            return _do([], f"{target} (← {left}) (← {right})")
        if kind == "if":
            return "(SPL.conditional " + self.expression(expr["condition"], env) + (
                " (fun _ => " + self.expression(expr["then"], env) + ") (fun _ => "
                + self.expression(expr["else"], env) + "))"
            )
        if kind == "record":
            return "(SPL.recordValues " + _list(
                _pair(name, self.expression(value, env)) for name, value in expr["fields"]
            ) + ")"
        if kind == "list":
            return "(SPL.listValues " + _list(self.expression(item, env) for item in expr["items"]) + ")"
        if kind == "select_rules":
            arms = _list(
                f'({_string(arm["rule_id"])}, ({arm["priority"]} : Int), '
                f'(fun _ => {self.expression(arm["predicate"], env)}), '
                f'(fun _ => {self.expression(arm["body"], env)}))'
                for arm in expr["arms"])
            fallback = expr.get("otherwise")
            otherwise = "none" if fallback is None else (
                f'(some ({_string(fallback["rule_id"])}, (fun _ => {self.expression(fallback["body"], env)})))')
            return f'(SPL.selectRules {str(expr["priority_mode"]).lower()} {arms} {otherwise})'
        if kind == "choose":
            arms = _list(
                f"({self.expression(predicate, env)}, (fun _ => {self.expression(body, env)}))"
                for predicate, body in expr["arms"]
            )
            fallback = "none" if expr.get("otherwise") is None else (
                "(some (fun _ => " + self.expression(expr["otherwise"], env) + "))"
            )
            return f"(SPL.choose {arms} {fallback})"
        if kind == "apply":
            lines, nested = [], {}
            for parameter,arg in zip(expr["parameters"],expr["args"]):
                variable = self.fresh()
                lines.append(f"let {variable} : SPL.Value ← {self.expression(arg,env)}")
                nested[parameter["name"]] = f"(pure {variable})"
            local_lines,nested = self.scope(expr["declarations"],nested)
            return _do(lines+local_lines,self.expression(expr["body"],nested))
        if kind == "fold":
            initial,source,state,event = self.fresh(),self.fresh(),self.fresh(),self.fresh()
            lines = [f"let {initial} ← {self.expression(expr['initial'],env)}",f"let {source} ← {self.expression(expr['source'],env)}"]
            nested = dict(env,**{expr["state"]:f"(pure {state})",expr["event"]:f"(pure {event})"})
            local_lines,nested = self.scope(expr["declarations"],nested)
            step = f"(fun {state} {event} => {_do(local_lines,self.expression(expr['body'],nested))})"
            order = expr.get("order")
            if order:
                kv,iv = self.fresh(),self.fresh()
                key = self.expression(order["key"],dict(env,**{order["key_binder"]:f"(pure {kv})"}))
                identity = self.expression(order["identity"],dict(env,**{order["id_binder"]:f"(pure {iv})"}))
                return _do(lines,f"SPL.orderedFoldValues {initial} {source} (fun {kv} => {key}) (fun {iv} => {identity}) {_string(order['ties'])} {step}")
            return _do(lines,f"SPL.foldValues {initial} {source} {step}")
        if kind == "for":
            variable = self.fresh()
            nested = dict(env, **{expr["name"]: f"(pure {variable})"})
            lines, nested = self.scope(expr["declarations"], nested)
            body = _do(lines, self.expression(expr["yield"], nested))
            return _do([], f"SPL.mapValues (← {self.expression(expr['source'], env)}) (fun {variable} => {body})")
        if kind == "call":
            name, args = expr["name"], expr["args"]
            if name in {"make_map","join","left_join"}:
                k,v = self.fresh(),self.fresh()
                kl,vl = args[-2:]
                key = self.expression(kl["body"],dict(env,**{kl["name"]:f"(pure {k})"}))
                value = self.expression(vl["body"],dict(env,**{vl["name"]:f"(pure {v})"}))
                projections = f" (fun {k} => {key}) (fun {v} => {value})"
                source = f"(← {self.expression(args[0],env)})"
                if name == "make_map":
                    return _do([],"SPL.makeMap " + source + projections)
                return _do([],f"SPL.joinValues {str(name == 'left_join').lower()} " + source +
                           f" (← {self.expression(args[1],env)})" + projections)
            if name in {"filter", "sum", "map", "sort_by", "group_by"}:
                variable = self.fresh()
                function = {"filter": "filterValues", "sum": "sumValues", "map": "mapValues", "sort_by": "sortValues", "group_by":"groupValues"}[name]
                lam = args[1]
                nested = dict(env, **{lam["name"]: f"(pure {variable})"})
                body = self.expression(lam["body"], nested)
                if name == "sum" and expr["_type"].name in {"Quantity", "Rate"}:
                    zero = lean_value(typed_zero(expr["_type"]))
                    return _do([], f"SPL.sumValuesFrom {zero} (← {self.expression(args[0], env)}) (fun {variable} => {body})")
                return _do([], f"SPL.{function} (← {self.expression(args[0], env)}) (fun {variable} => {body})")
            if name == "tuple":
                return "(SPL.tupleValues " + _list(self.expression(a,env) for a in args) + ")"
            if name == "none":
                return "(pure .absent)"
            if name == "some":
                return _do([],f"pure (.present (← {self.expression(args[0],env)}))")
            if name == "get_or":
                return _do([],f"SPL.getOr (← {self.expression(args[0],env)}) (fun _ => {self.expression(args[1],env)})")
            values = [f"(← {self.expression(arg, env)})" for arg in args]
            if name in {"append","concat"}:
                return _do([],"SPL."+{"append":"appendValue","concat":"concatValues"}[name]+" "+" ".join(values))
            if name in {"tuple_get","lookup","entries","is_some"}:
                function = {"tuple_get":"tupleGet","lookup":"mapLookup","entries":"mapEntries","is_some":"isSome"}[name]
                return _do([],"SPL."+function+" "+" ".join(values))
            if name in {"min", "max"}:
                return _do([], f"SPL.extrema {'true' if name == 'max' else 'false'} " + " ".join(values))
            if name == "abs":
                return _do([], "SPL.absolute " + " ".join(values))
            if name == "in_period":
                return _do([], "SPL.inPeriod " + " ".join(values))
            if name == "add_calendar_months":
                return _do([], "SPL.addCalendarMonths " + " ".join(values))
            if name == "instant":
                return _do([], "SPL.instant " + " ".join(values))
            if name == "is_calendar_quarter":
                return _do([], "SPL.isCalendarQuarter " + " ".join(values))
            if name == "quantize":
                return _do([], "SPL.quantize " + " ".join(values))
            if name == "require_some":
                return _do([], "SPL.requireSome " + " ".join(values))
            raise ValueError(f"Unsupported checked target builtin: {name}")
        raise ValueError(f"Unsupported checked target expression: {kind}")

    def scope(self, declarations, outer):
        env = dict(outer)
        functions = {}
        for decl in declarations:
            if decl["kind"] == "define":
                function = self.fresh()
                functions[decl["name"]] = function
                env[decl["name"]] = f"({function}.get)"
        lines = []
        definitions = {decl["name"]: decl for decl in declarations if decl["kind"] == "define"}
        emitted, active = set(), set()

        def emit_definition(name):
            if name not in definitions or name in emitted:
                return
            if name in active:
                raise ValueError("Unchecked cyclic core cannot be emitted")
            active.add(name)
            decl = definitions[name]
            # Hoist fresh memo cells, not evaluated values. Each invocation keeps
            # its own cache and the existing declaration demand/failure order.
            for reference in _ordered_references(decl["expr"]):
                emit_definition(reference)
            lines.append(f"let {functions[name]} : Thunk (SPL.Eval SPL.Value) := Thunk.mk (fun _ => {self.expression(decl['expr'], env)})")
            active.remove(name)
            emitted.add(name)

        for name in definitions:
            emit_definition(name)

        for decl in declarations:
            if decl["kind"] == "define":
                value = self.fresh()
                lines.append(f"let {value} ← {env[decl['name']]}")
                env[decl["name"]] = f"(pure {value})"
            elif decl["kind"] == "require":
                lines.append(f"SPL.assertValue (← {self.expression(decl['expr'], env)}) {_string(decl['code'])}")
        return lines, env


def emit_module(checked, inputs=None, openings=None) -> str:
    """Emit pure parameterized Lean; optionally include a replay driver.

    `checked` is the checker-owned CheckedSchedule, not an arbitrary syntax tree.
    The driver accepts decoded exact values, as does the reference evaluator.
    """
    schedule = checked.schedule
    emitter, env, lines = _Emitter(), {}, []
    for decl in schedule["declarations"]:
        if decl["kind"] in {"input", "opening"}:
            variable = emitter.fresh()
            env[decl["name"]] = f"(pure {variable})"
            source = "_inputs" if decl["kind"] == "input" else "_openings"
            lines.append(f"let {variable} ← SPL.lookup {source} {_string(decl['name'])}")
    body, env = emitter.scope(schedule["declarations"], env)
    lines += body
    emissions, closing = [], []
    for decl in schedule["declarations"]:
        if decl["kind"] in {"emit", "closing"}:
            variable = emitter.fresh()
            lines.append(f"let {variable} ← {emitter.expression(decl['expr'], env)}")
            (emissions if decl["kind"] == "emit" else closing).append(_pair(decl["name"], variable))
    result = "pure { emissions := " + _list(emissions) + ", closing := " + _list(closing) + " }"
    rules = _list(
        _pair(str(decl.get("name", decl.get("code", "require"))), _string(decl.get("citation") or ""))
        for decl in schedule["declarations"]
    )
    module = "import SPL.Fold\nimport SPL.Core\n\nset_option maxRecDepth 4096\nset_option maxHeartbeats 0\n\nnamespace GeneratedSPL\n\n"
    module += f"def scheduleName : String := {_string(schedule['name'])}\n"
    module += f"def sourceRules : List (String × String) := {rules}\n\n"
    module += "def settle (_inputs _openings : SPL.Env) : SPL.Eval SPL.Settlement := " + _do(lines, result) + "\n\nend GeneratedSPL\n"
    if inputs is not None:
        if openings is None:
            openings = {}
        normalized_openings = dict(openings)
        for decl in schedule["declarations"]:
            if decl["kind"] == "opening" and decl["name"] not in normalized_openings and decl.get("alias") in openings:
                normalized_openings[decl["name"]] = openings[decl["alias"]]
        input_values = _list(_pair(name, lean_value(value)) for name, value in inputs.items())
        opening_values = _list(_pair(name, lean_value(value)) for name, value in normalized_openings.items())
        module += "\ndef main : IO Unit := do\n  let result := GeneratedSPL.settle " + input_values + " " + opening_values
        module += "\n  IO.println (SPL.outcomeJson result).compress\n"
    return module


def _lean_executable():
    configured = os.environ.get("SPL_LEAN")
    if configured:
        return configured
    elan_home = os.environ.get("ELAN_HOME")
    roots = [Path(elan_home)] if elan_home else []
    roots += [Path("C:/Projects/Film_TV_participation_dynamic_DSL/environment/elan"), Path.home() / ".elan"]
    version = Path(__file__).resolve().parents[1].joinpath("lean-toolchain").read_text().strip().replace("/", "--").replace(":", "---")
    for root in roots:
        candidate = root / "toolchains" / version / "bin" / ("lean.exe" if os.name == "nt" else "lean")
        if candidate.exists():
            return str(candidate)
    found = shutil.which("lean")
    if not found:
        raise RuntimeError("Pinned Lean toolchain unavailable; set SPL_LEAN or ELAN_HOME")
    return found


def run_generated(checked, inputs, openings, output_path=None, timeout=180):
    """Build runtime if necessary, run emitted Lean, parse its exact JSON result."""
    root = Path(__file__).resolve().parents[1]
    build = root / ".lake" / "build" / "lib" / "lean"
    (build / "SPL").mkdir(parents=True, exist_ok=True)
    lean = _lean_executable()
    environment = dict(os.environ)
    environment["LEAN_PATH"] = str(build) + (os.pathsep + environment["LEAN_PATH"] if environment.get("LEAN_PATH") else "")
    dependencies = {"Instant": (), "Calendar": (), "Dimensions": (),
                    "Runtime": ("Instant", "Calendar", "Dimensions"), "Fold": ("Runtime",), "Core": ("Runtime",)}
    for name, imported in dependencies.items():
        source = root / "SPL" / (name + ".lean")
        target = build / "SPL" / (name + ".olean")
        required_time = max([source.stat().st_mtime] + [
            (build / "SPL" / (dependency + ".olean")).stat().st_mtime for dependency in imported])
        if not target.exists() or target.stat().st_mtime < required_time:
            process = subprocess.run([lean, "-o", str(target), str(source)], cwd=root, env=environment, text=True, encoding="utf-8", capture_output=True, timeout=timeout)
            if process.returncode:
                raise RuntimeError(f"Lean {name} compilation failed:\n" + process.stdout + process.stderr)
    driver_dir = root / ".lake" / "spl"
    driver_dir.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        descriptor, filename = tempfile.mkstemp(prefix="Run_", suffix=".lean", dir=driver_dir)
        os.close(descriptor)
        output_path = Path(filename)
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(emit_module(checked, inputs, openings), encoding="utf-8", newline="\n")
    process = subprocess.run([lean, "--run", str(output_path)], cwd=root, env=environment, text=True, encoding="utf-8", capture_output=True, timeout=timeout)
    if process.returncode:
        raise RuntimeError("Generated Lean execution failed:\n" + process.stdout + process.stderr)
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("Generated Lean did not return a JSON outcome:\n" + process.stdout) from error
