"""Independent exact Python semantics for the bounded SPL core.

This evaluator never calls generated Lean code. It is a differential reference,
not a substitute for an independently authored contract-methodology oracle.
"""
from __future__ import annotations

from datetime import date
from fractions import Fraction
from math import gcd
import re
import unicodedata
from typing import Any, Callable

from .model import CheckedSchedule, Diagnostic, MapValue, OptionValue, Outcome, SPLException, Type, encode_value
from .instant import parse_instant
from .calendar_months import add_calendar_months

DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")
POSITIVE_INTEGER = re.compile(r"[1-9][0-9]*\Z")


def parse_exact(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, str) and DECIMAL.fullmatch(value):
        return Fraction(value)
    if isinstance(value, dict) and set(value) == {"numerator", "denominator"}:
        n, d = value["numerator"], value["denominator"]
        if isinstance(n, str) and isinstance(d, str) and INTEGER.fullmatch(n) and POSITIVE_INTEGER.fullmatch(d):
            numerator, denominator = int(n), int(d)
            if gcd(numerator, denominator) == 1 and (numerator != 0 or denominator == 1) and n != "-0":
                return Fraction(numerator, denominator)
    raise SPLException("INVALID_EXACT_NUMBER", "Expected exact decimal string or reduced rational with positive denominator")


def decode_value(value: Any, typ: Type, pointer: str = "input") -> Any:
    def error(code: str, message: str) -> None:
        raise SPLException(code, f"{pointer}: {message}")

    if isinstance(value,list) and len(value) > 100000:
        error("RESOURCE_LIMIT", "Collection exceeds fixed 100000 item envelope")
    if value is None:
        error("NULL_NOT_ALLOWED", "Explicit null is not a value")
    if typ.name == "Money":
        if not isinstance(value, dict) or set(value) != {"value", "currency"}:
            error("INVALID_MONEY", "Expected exactly value and currency fields")
        if value["currency"] != typ.args[0].name:
            error("CURRENCY_MISMATCH", f"Expected {typ.args[0].name}")
        return parse_exact(value["value"])
    if typ.name in {"Ratio", "Rational", "Int", "Nat"}:
        number = parse_exact(value)
        if typ.name in {"Int", "Nat"} and number.denominator != 1:
            error("INVALID_INTEGER", "Fractional integer supplied")
        if typ.name == "Nat" and number < 0:
            error("NEGATIVE_NAT", "Natural number cannot be negative")
        return number
    if typ.name == "Bool":
        if type(value) is not bool:
            error("INVALID_BOOL", "Expected true or false")
        return value
    if typ.name == "Instant":
        return parse_instant(value)
    if typ.name in {"Text", "Id", "Date"}:
        if not isinstance(value, str):
            error("INVALID_TEXT", "Expected a string")
        if typ.name == "Id" and (not value or unicodedata.normalize("NFC", value) != value):
            error("INVALID_ID", "Expected nonempty NFC identifier")
        if typ.name == "Id" and not value.isascii():
            error("UNSUPPORTED_IDENTIFIER_PROFILE", "Only ASCII opaque identifiers are admitted")
        if typ.name == "Date":
            try:
                if date.fromisoformat(value).isoformat() != value:
                    raise ValueError()
            except ValueError:
                error("INVALID_DATE", "Expected Gregorian YYYY-MM-DD")
        return value
    if typ.name == "List":
        if not isinstance(value, list):
            error("INVALID_LIST", "Expected a finite JSON array")
        decoded = [decode_value(item, typ.args[0], f"{pointer}[{i}]") for i, item in enumerate(value)]
        if typ.args[0].name in {"AdvanceIssue", "ReserveMovement", "PaymentApplication"}:
            identities = [item["event_id"] for item in decoded]
            if len(set(identities)) != len(identities):
                error("DUPLICATE_EVENT_ID", "A supplied mechanism event can be applied only once")
        keys = ({"AdvanceIssue": [("issue_id", "DUPLICATE_ISSUE_ID"), ("disbursement_id", "DUPLICATE_DISBURSEMENT_ID")],
                 "AdvanceEvidence": [("evidence_id", "DUPLICATE_EVIDENCE_ID")],
                 "ReserveEvidence": [("evidence_id", "DUPLICATE_EVIDENCE_ID")],
                 "ReserveVintage": [("vintage_id", "DUPLICATE_VINTAGE_ID")]}.get(typ.args[0].name, []))
        for key, code in keys:
            ids = [item[key] for item in decoded]
            if len(set(ids)) != len(ids):
                error(code, "A supplied mechanism identity can be applied only once")
        return decoded
    if typ.name == "Tuple":
        if not isinstance(value,list) or len(value) != len(typ.args):
            error("TUPLE_ARITY","Expected fixed-arity tuple array")
        return tuple(decode_value(v,t,f"{pointer}[{i}]") for i,(v,t) in enumerate(zip(value,typ.args)))
    if typ.name == "Map":
        if not isinstance(value,list) or any(not isinstance(e,dict) or set(e) != {"key","value"} for e in value):
            error("EXPECTED_MAP","Expected key/value entry array")
        keyed = [(decode_value(e["key"],typ.args[0],f"{pointer}[{i}].key"),e["value"]) for i,e in enumerate(value)]
        if len({k for k,_ in keyed}) != len(keyed):
            error("DUPLICATE_MAP_KEY","Duplicate supplied map key")
        return MapValue(tuple((k,decode_value(v,typ.args[1],pointer+".value")) for k,v in sorted(keyed,key=lambda p:p[0])))
    if typ.name == "Option":
        if value == {"none": True}:
            return OptionValue(False)
        if isinstance(value, dict) and set(value) == {"some"}:
            return OptionValue(True,decode_value(value["some"], typ.args[0], pointer + ".some"))
        error("INVALID_OPTION", "Expected {none:true} or {some:value}")
    if typ.fields:
        fields = dict(typ.fields)
        if not isinstance(value, dict):
            error("INVALID_RECORD", f"Expected {typ.name} object")
        missing, extra = fields.keys() - value.keys(), value.keys() - fields.keys()
        if missing:
            error("MISSING_FIELD", f"Missing {', '.join(sorted(missing))}")
        if extra:
            error("UNKNOWN_FIELD", f"Unknown fields {', '.join(sorted(extra))}")
        result = {name: decode_value(value[name], field_type, pointer + "." + name) for name, field_type in typ.fields}
        if typ.name == "Period" and result["start"] >= result["end"]:
            error("INVALID_PERIOD", "Half-open period requires start < end")
        return result
    error("UNSUPPORTED_TYPE", f"Cannot decode {typ}")


def quantize(value: Fraction, quantum: Fraction, mode: str) -> Fraction:
    if quantum <= 0:
        raise SPLException("INVALID_QUANTUM", "Rounding quantum must be strictly positive")
    scaled = value / quantum
    low = scaled.numerator // scaled.denominator
    fraction = scaled - low
    if mode == "floor":
        rounded = low
    elif mode == "ceiling":
        rounded = low + (fraction != 0)
    elif mode == "toward_zero":
        rounded = low + (value < 0 and fraction != 0)
    elif mode in {"half_even", "half_away_from_zero"}:
        rounded = low + (fraction > Fraction(1, 2))
        if fraction == Fraction(1, 2):
            rounded = low + (low % 2 != 0 if mode == "half_even" else value >= 0)
    else:
        raise SPLException("UNSUPPORTED_ROUNDING_MODE", f"Unsupported mode {mode}")
    return rounded * quantum


class Environment:
    def __init__(self, values: dict[str, Any], parent: "Environment | None" = None):
        self.values, self.parent = values, parent
        self.deferred: dict[str, Callable[[], Any]] = {}
        self.active: set[str] = set()

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if name in self.deferred:
            if name in self.active:
                raise SPLException("DEPENDENCY_CYCLE", name)
            self.active.add(name)
            try:
                value = self.deferred[name]()
                self.values[name] = value
                return value
            finally:
                self.active.remove(name)
        if self.parent:
            return self.parent.get(name)
        raise SPLException("UNRESOLVED_NAME", name)


class Evaluator:
    def __init__(self):
        self.trace: list[dict[str, Any]] = []
        self.instances: list[str] = []

    def observe(self, node: dict, kind: str, **fields: Any) -> None:
        if len(self.trace) >= 100000:
            raise SPLException("RESOURCE_LIMIT","Trace exceeds fixed 100000 observation envelope",node.get("span"))
        span = node.get("span", {})
        identity = f"{kind}:{node.get('_node_id', 'unassigned')}:{span.get('start', span.get('line', 0))}:{span.get('end', 0)}"
        if self.instances:
            identity += ":" + "/".join(self.instances)
        self.trace.append({"node_id": identity, "kind": kind, "source_span": span, **encode_value(fields)})

    def expr(self, node: dict, env: Environment) -> Any:
        kind = node["kind"]
        if kind in {"number", "money"}:
            return Fraction(node["value"])
        if kind in {"bool", "text", "date"}:
            return node["value"]
        if kind == "name":
            return env.get(node["name"])
        if kind == "field":
            return self.expr(node["expr"], env)[node["name"]]
        if kind == "record":
            return {name: self.expr(expression, env) for name, expression in node["fields"]}
        if kind == "list":
            if len(node["items"]) > 100000:
                raise SPLException("RESOURCE_LIMIT","Collection exceeds fixed 100000 item envelope",node.get("span"))
            return [self.expr(expression, env) for expression in node["items"]]
        if kind == "unary":
            value = self.expr(node["expr"], env)
            return not value if node["op"] == "not" else -value
        if kind == "binary":
            left = self.expr(node["left"], env)
            op = node["op"]
            if op == "and" and not left or op == "or" and left:
                self.observe(node, "short_circuit", operator=op, left=left, right="not_evaluated", result=left)
                return left
            right = self.expr(node["right"], env)
            if op == "/" and right == 0:
                raise SPLException("DIVISION_BY_ZERO", "Demanded exact division by zero", node.get("span"))
            operations = {"+": lambda: left + right, "-": lambda: left - right, "*": lambda: left * right,
                          "/": lambda: left / right, "==": lambda: left == right, "!=": lambda: left != right,
                          "<": lambda: left < right, "<=": lambda: left <= right, ">": lambda: left > right,
                          ">=": lambda: left >= right, "and": lambda: bool(left and right), "or": lambda: bool(left or right)}
            result = operations[op]()
            if node.get("_type", Type("Unknown")).name == "Nat" and result < 0:
                raise SPLException("NAT_UNDERFLOW", "Natural subtraction would be negative", node.get("span"))
            self.observe(node, "binary", operator=op, operands=[left, right], result=result)
            return result
        if kind == "if":
            condition = self.expr(node["condition"], env)
            selected = "then" if condition else "else"
            result = self.expr(node[selected], env)
            self.observe(node, "branch", predicate=condition, selected=selected, unselected="not_evaluated", result=result)
            return result
        if kind == "select_rules":
            fallback = node.get("otherwise")
            ids = [arm["rule_id"] for arm in node["arms"]] + ([fallback["rule_id"]] if fallback else [])
            if len(ids) != len(set(ids)):
                raise SPLException("DUPLICATE_RULE_ID", "Rule IDs must be unique", node.get("span"))
            ordered = sorted(node["arms"], key=lambda arm: arm["rule_id"])
            matches, candidates = [], []
            for index, arm in enumerate(ordered):
                try:
                    matched = self.expr(arm["predicate"], env)
                except SPLException as error:
                    candidates.append(dict(rule_id=arm["rule_id"], priority=arm["priority"],
                                           reason="predicate_failed", code=error.code))
                    candidates.extend(dict(rule_id=later["rule_id"], priority=later["priority"],
                                           reason="not_evaluated") for later in ordered[index + 1:])
                    self.observe(node, "selection", candidates=candidates, failed_rule_id=arm["rule_id"],
                                 reason="predicate_failed", bodies="not_evaluated", code=error.code)
                    raise
                candidates.append(dict(rule_id=arm["rule_id"], priority=arm["priority"], applicable=matched,
                                       reason="predicate_true" if matched else "predicate_false"))
                if matched:
                    matches.append(arm)
            winners = matches
            if node["priority_mode"] and matches:
                highest = max(arm["priority"] for arm in matches)
                winners = [arm for arm in matches if arm["priority"] == highest]
            selected = winners[0] if len(winners) == 1 else fallback if not winners else None
            reason = ("ambiguous_applicable_rules" if len(winners) > 1 else
                      "fallback_no_applicable_rule" if not matches and fallback else
                      "no_applicable_rule" if not matches else
                      "greatest_priority_rule" if node["priority_mode"] else "unique_applicable_rule")
            details = dict(candidates=candidates, reason=reason, tie=len(winners) > 1,
                           priority_mode=node["priority_mode"], unselected="not_evaluated")
            if selected is None:
                code = "AMBIGUOUS_RULE" if matches else "NO_APPLICABLE_RULE"
                self.observe(node, "selection", **details, code=code, bodies="not_evaluated")
                raise SPLException(code, reason, node.get("span"))
            details["selected_rule_id"] = selected["rule_id"]
            try:
                result = self.expr(selected["body"], env)
            except SPLException as error:
                self.observe(node, "selection", **details, body_status="failed", code=error.code)
                raise
            self.observe(node, "selection", **details, result=result,
                         selection_status="calculated_zero" if result == 0 else "calculated")
            return result
        if kind == "choose":
            matches = []
            predicates = []
            for index, (predicate, _) in enumerate(node["arms"]):
                matched = self.expr(predicate, env)
                predicates.append(matched)
                if matched:
                    matches.append(index)
            if len(matches) > 1:
                raise SPLException("AMBIGUOUS_RULE", "More than one choose unique predicate matched", node.get("span"))
            if matches:
                selected: int | str = matches[0]
                result = self.expr(node["arms"][matches[0]][1], env)
            elif node.get("otherwise") is not None:
                selected = "otherwise"
                result = self.expr(node["otherwise"], env)
            else:
                raise SPLException("NO_APPLICABLE_RULE", "No choose unique predicate matched", node.get("span"))
            self.observe(node, "selection", predicates=predicates, selected=selected, unselected="not_evaluated", result=result)
            return result
        if kind == "apply":
            values = [self.expr(arg,env) for arg in node["args"]]
            local = Environment({p["name"]:v for p,v in zip(node["parameters"],values)})
            self.instances.append("call:"+str(node.get("_node_id"))+":"+node["function"])
            try:
                self.declarations(node["declarations"],node["_definition_order"],local)
                result = self.expr(node["body"],local)
                self.observe(node,"application",function=node["function"],arguments=values,result=result)
                return result
            finally:
                self.instances.pop()
        if kind == "fold":
            state = self.expr(node["initial"],env)
            events = self.expr(node["source"],env)
            order = node.get("order")
            if order:
                identities = [self.expr(order["identity"],Environment({order["id_binder"]:e},env)) for e in events]
                keys = [self.expr(order["key"],Environment({order["key_binder"]:e},env)) for e in events]
                if len(set(identities)) != len(identities):
                    self.observe(node,"fold_order",status="failed",code="DUPLICATE_EVENT_ID",identities=identities,keys=keys)
                    raise SPLException("DUPLICATE_EVENT_ID","Declared event identities repeat",node.get("span"))
                if len(set(keys)) != len(keys):
                    self.observe(node,"fold_order",status="failed",code="UNRESOLVED_EVENT_ORDER",identities=identities,keys=keys)
                    raise SPLException("UNRESOLVED_EVENT_ORDER","Complete semantic keys tie",node.get("span"))
                entries = sorted(zip(keys,identities,events),key=lambda entry:entry[0])
                self.observe(node,"fold_order",status="validated",tie_policy=order["ties"],identities=[i for _,i,_ in entries],keys=[k for k,_,_ in entries])
            else:
                entries = [(index,index,event) for index,event in enumerate(events)]
            for index,(key,identity,event) in enumerate(entries):
                before = state
                self.instances.append("fold:"+str(node.get("_node_id"))+":"+str(identity)+":"+str(index))
                try:
                    local = Environment({node["state"]:state,node["event"]:event},env)
                    self.declarations(node["declarations"],node["_definition_order"],local)
                    state = self.expr(node["body"],local)
                    self.observe(node,"fold_step",event_identity=identity,semantic_key=key,
                                 tie_policy=order["ties"] if order else "supplied_list_order",
                                 state_before=before,state_after=state,status="calculated")
                except SPLException as error:
                    self.observe(node,"fold_step",event_identity=identity,semantic_key=key,
                                 state_before=before,status="failed",code=error.code)
                    raise
                finally:
                    self.instances.pop()
            self.observe(node,"fold",count=len(events),result=state)
            return state
        if kind == "for":
            source = self.expr(node["source"], env)
            results = []
            for index, item in enumerate(source):
                instance = item.get("asset_id", item.get("fact_id", str(index))) if isinstance(item, dict) else str(index)
                self.instances.append(str(instance))
                local = Environment({node["name"]: item}, env)
                self.declarations(node["declarations"], node["_definition_order"], local)
                results.append(self.expr(node["yield"], local))
                self.instances.pop()
            self.observe(node, "map", count=len(source), result=results)
            return results
        if kind == "call":
            name, args = node["name"], node["args"]
            if name == "get_or":
                option = self.expr(args[0],env)
                result = self.expr(args[1],env) if not option.present else option.value
                self.observe(node,name,result=result,fallback="evaluated" if not option.present else "not_evaluated")
                return result
            if name in {"make_map","group_by","join","left_join"}:
                left = self.expr(args[0],env)
                def project(lam,rows,phase):
                    out = []
                    for i,row in enumerate(rows):
                        self.instances.append(f"{phase}:{i}")
                        try:
                            out.append(self.expr(lam["body"],Environment({lam["name"]:row},env)))
                        finally:
                            self.instances.pop()
                    return out
                kl = args[1] if name == "group_by" else args[-2]
                keys = project(kl,left,"left_key")
                lineage = [{"row":i,"key":k} for i,k in enumerate(keys)]
                if name == "make_map":
                    repeated = sorted(k for k in set(keys) if keys.count(k) > 1)
                    if repeated:
                        k = repeated[0]
                        identities = [{"position":i,"identity":left[i].get("fact_id",left[i].get("event_id",str(i))) if isinstance(left[i],dict) else str(i)} for i,x in enumerate(keys) if x == k]
                        self.observe(node,name,key=k,source_occurrences=[i for i,x in enumerate(keys) if x == k],source_identities=identities,values="not_evaluated")
                        raise SPLException("DUPLICATE_MAP_KEY","Repeated map key",node.get("span"))
                    ordered = sorted(range(len(left)),key=keys.__getitem__)
                    values = project(args[2],[left[i] for i in ordered],"map_value")
                    result = MapValue(tuple((keys[i],v) for i,v in zip(ordered,values)))
                elif name == "group_by":
                    result = MapValue(tuple((k,[row for row,rk in zip(left,keys) if rk == k]) for k in sorted(set(keys))))
                else:
                    right = self.expr(args[1],env)
                    rkeys = project(args[3],right,"right_key")
                    result, lineage = [], []
                    for i,(l,k) in enumerate(zip(left,keys)):
                        matches = [(j,r) for j,(r,rk) in enumerate(zip(right,rkeys)) if rk == k]
                        if not matches and name == "left_join":
                            if len(result) >= 100000:
                                raise SPLException("RESOURCE_LIMIT","Join exceeds fixed 100000 pair envelope",node.get("span"))
                            result.append({"left":l,"right":OptionValue(False)})
                            lineage.append({"left_occurrence":i,"right_absent":True})
                        for j,r in matches:
                            if len(result) >= 100000:
                                raise SPLException("RESOURCE_LIMIT","Join exceeds fixed 100000 pair envelope",node.get("span"))
                            result.append({"left":l,"right":OptionValue(True,r) if name == "left_join" else r})
                            lineage.append({"left_occurrence":i,"right_occurrence":j})
                self.observe(node,name,result=result,occurrences=lineage)
                return result
            if name in {"filter", "map", "sum", "sort_by"}:
                source, lam = self.expr(args[0], env), args[1]
                mapped = []
                for index, item in enumerate(source):
                    key = item.get("fact_id", item.get("asset_id", str(index))) if isinstance(item, dict) else str(index)
                    self.instances.append(str(key))
                    mapped.append(self.expr(lam["body"], Environment({lam["name"]: item}, env)))
                    self.instances.pop()
                if name == "filter":
                    result = [item for item, include in zip(source, mapped) if include]
                elif name == "map":
                    result = mapped
                elif name == "sum":
                    result = sum(mapped, Fraction(0))
                else:
                    result = [item for _, item in sorted(zip(mapped, source), key=lambda pair: pair[0])]
                self.observe(node, name, operands=mapped, result=result)
                return result
            values = [self.expr(arg, env) for arg in args]
            if name == "append":
                if len(values[0]) >= 100000:
                    raise SPLException("RESOURCE_LIMIT","Collection exceeds fixed 100000 item envelope",node.get("span"))
                result = values[0] + [values[1]]
            elif name == "concat":
                if len(values[0])+len(values[1]) > 100000:
                    raise SPLException("RESOURCE_LIMIT","Collection exceeds fixed 100000 item envelope",node.get("span"))
                result = values[0] + values[1]
            elif name == "tuple":
                result = tuple(values)
            elif name == "tuple_get":
                result = values[0][int(values[1])]
            elif name == "none":
                result = OptionValue(False)
            elif name == "some":
                result = OptionValue(True,values[0])
            elif name == "is_some":
                result = values[0].present
            elif name == "entries":
                result = [{"key":k,"value":v} for k,v in values[0].entries]
            elif name == "lookup":
                result = next((OptionValue(True,v) for k,v in values[0].entries if k == values[1]),OptionValue(False))
            elif name == "min":
                result = min(values)
            elif name == "instant":
                result = parse_instant(values[0])
            elif name == "max":
                result = max(values)
            elif name == "add_calendar_months":
                result = add_calendar_months(*values)
            elif name == "in_period":
                result = values[1]["start"] <= values[0] < values[1]["end"]
            elif name == "is_calendar_quarter":
                start, end = (date.fromisoformat(values[0][k]) for k in ["start", "end"])
                result = (start.day == end.day == 1 and start.month in {1, 4, 7, 10} and
                          end.month == (1 if start.month == 10 else start.month + 3) and
                          end.year == start.year + (start.month == 10))
            elif name == "quantize":
                result = quantize(*values)
            elif name == "require_some":
                if not values[0].present:
                    raise SPLException(values[1], "Required option is absent", node.get("span"))
                result = values[0].value
            else:
                raise SPLException("UNSUPPORTED_BUILTIN", name, node.get("span"))
            self.observe(node, name, operands=values, result=result,
                         **({"selection_reason": "tie" if values[0] == values[1] else "left" if result == values[0] else "right"} if name in {"min", "max"} else {}))
            return result
        raise SPLException("UNSUPPORTED_EXPRESSION", kind, node.get("span"))

    def declarations(self, declarations: list[dict], _order: list[str], env: Environment) -> None:
        definitions = {d["name"]: d for d in declarations if d["kind"] == "define"}
        declaration_scope = list(self.instances)

        def calculate(name: str) -> Any:
            declaration = definitions[name]
            demand_scope = self.instances
            self.instances = list(declaration_scope)
            try:
                value = self.expr(declaration["expr"], env)
                self.observe(declaration, "definition", name=name, rule_id=declaration.get("citation") or name,
                             result=value, outcome="calculated_zero" if isinstance(value, Fraction) and value == 0 else "calculated")
                return value
            finally:
                self.instances = demand_scope

        # Register closures without evaluating them. A forward reference in an
        # unselected branch, short circuit or empty map body is not demanded.
        for name in definitions:
            env.deferred[name] = lambda name=name: calculate(name)

        for declaration in declarations:
            if declaration["kind"] == "define":
                env.get(declaration["name"])
            elif declaration["kind"] == "require":
                passed = self.expr(declaration["expr"], env)
                self.observe(declaration, "assertion", code=declaration["code"], passed=passed)
                if not passed:
                    raise SPLException(declaration["code"], "Required case precondition failed", declaration.get("span"))


def evaluate(checked: CheckedSchedule, inputs: dict[str, Any], openings: dict[str, Any]) -> Outcome:
    evaluator = Evaluator()
    try:
        # Readable expansion maps every subexpression back to its authored
        # statement span. A preorder AST identity distinguishes nested operators
        # with that same span without relying on dynamic evaluation order.
        counter = 0
        def identify(value):
            nonlocal counter
            if isinstance(value, dict):
                if "kind" in value:
                    value["_node_id"] = counter
                    counter += 1
                for key, child in value.items():
                    if not key.startswith("_"):
                        identify(child)
            elif isinstance(value, (list, tuple)):
                for child in value:
                    identify(child)
        identify(checked.schedule)
        declarations = checked.schedule["declarations"]
        input_decls = {d["name"]: d for d in declarations if d["kind"] == "input"}
        opening_decls = {d["name"]: d for d in declarations if d["kind"] == "opening"}
        if inputs.keys() != input_decls.keys():
            raise SPLException("INPUT_BINDING_MISMATCH", f"Input names must be exactly {', '.join(input_decls)}")
        expected_openings = set(opening_decls)
        alias_map = {d["alias"]: name for name, d in opening_decls.items()}
        normalized_openings = {}
        for name, value in openings.items():
            binding = name if name in expected_openings else alias_map.get(name)
            if binding is None or binding in normalized_openings:
                raise SPLException("OPENING_BINDING_MISMATCH", f"Unknown or duplicate opening {name}")
            normalized_openings[binding] = value
        if normalized_openings.keys() != expected_openings:
            raise SPLException("OPENING_BINDING_MISMATCH", "Missing opening binding")
        values = {name: decode_value(value, checked.types[name], name) for name, value in inputs.items()}
        values.update({name: decode_value(value, checked.types[name], name) for name, value in normalized_openings.items()})
        env = Environment(values)
        evaluator.declarations(declarations, checked.definition_order, env)
        emissions, closing = {}, {}
        for declaration in declarations:
            if declaration["kind"] in {"closing", "emit"}:
                result = evaluator.expr(declaration["expr"], env)
                target = closing if declaration["kind"] == "closing" else emissions
                target[declaration["name"]] = result
                evaluator.observe(declaration, declaration["kind"], name=declaration["name"], result=result)
        return Outcome("calculated", emissions, closing, evaluator.trace, [])
    except SPLException as error:
        return Outcome("blocked", {}, {}, evaluator.trace, [d.to_dict() for d in error.diagnostics])
