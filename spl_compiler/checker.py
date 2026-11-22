"""Closed, first-order checker for the implemented SPL development slice."""
from __future__ import annotations

from datetime import date
from typing import Any

from .model import BOOL, DATE, INSTANT, INT, RATIO, TEXT, USD, CheckedSchedule, SPLException, Type
from .dimensions import validate_currency, validate_unit


def ident(kind: str) -> Type:
    return Type("Id", (Type(kind),))


PERIOD = Type("Period", fields=(("start", DATE), ("end", DATE)))
ASSET, AGREEMENT, PARTICIPANT, POOL = map(ident, ("Asset", "Agreement", "Participant", "Pool"))
SCHEMAS: dict[str, Type] = {
    "Period": PERIOD,
    "SVPicture": Type("SVPicture", fields=(("asset_id", ASSET), ("contribution_present", BOOL), ("funding_share", RATIO))),
    "SVReceipt": Type("SVReceipt", fields=(("fact_id", ident("Fact")), ("asset_id", ASSET), ("amount", USD), ("cash_received_date", DATE))),
    "SVCost": Type("SVCost", fields=(("fact_id", ident("Fact")), ("asset_id", ASSET), ("amount", USD), ("incurred_date", DATE), ("eligibility_decision_id", ident("Decision")))),
    "SVPostingCost": Type("SVPostingCost", fields=(("fact_id", ident("Fact")), ("asset_id", ASSET), ("amount", USD), ("recognition_date", DATE), ("recognition_policy_ref", ident("Policy")), ("eligibility_decision_id", ident("Decision")))),
    "SVPolicy": Type("SVPolicy", fields=(("agreement_id", AGREEMENT), ("participant_id", PARTICIPANT), ("pool_id", POOL), ("period", PERIOD))),
    "LGReceipt": Type("LGReceipt", fields=(("fact_id", ident("Fact")), ("asset_id", ASSET), ("amount", USD), ("cash_received_date", DATE), ("is_home_video", BOOL))),
    "LGCost": Type("LGCost", fields=(("fact_id", ident("Fact")), ("asset_id", ASSET), ("amount", USD), ("incurred_date", DATE))),
    "LGPolicy": Type("LGPolicy", fields=(("agreement_id", AGREEMENT), ("participant_id", PARTICIPANT), ("asset_id", ASSET), ("pool_id", POOL), ("period", PERIOD), ("video_proxy", RATIO), ("gross_rate", RATIO), ("net_rate", RATIO))),
    "LGHurdleAttestation": Type("LGHurdleAttestation", fields=(("agreement_id", AGREEMENT), ("attained", BOOL), ("effective_date", DATE))),
    "LGGateHistoryAttestation": Type("LGGateHistoryAttestation", fields=(("asset_id", ASSET), ("period", PERIOD), ("cleared_throughout", BOOL))),
}
MODES = {"floor", "ceiling", "toward_zero", "half_even", "half_away_from_zero"}

# Named synthetic mechanism inputs. These do not extend the canonical SV/LG
# run profiles or authorize a historical accounting policy.
_scope_fields = (("agreement_id", AGREEMENT), ("participant_id", PARTICIPANT), ("pool_id", POOL))
SCHEMAS.update({
    "SettlementScope": Type("SettlementScope", fields=_scope_fields + (("period", PERIOD),)),
    "AdvanceIssue": Type("AdvanceIssue", fields=(
        ("event_id", ident("Event")),
        ("issue_id", ident("AdvanceIssue")),
        ("disbursement_id", ident("Disbursement")),
        ("agreement_id", ident("Agreement")),
        ("participant_id", ident("Participant")),
        ("pool_id", ident("Pool")),
        ("source_title_id", ident("Asset")),
        ("currency", TEXT),
        ("balance_purpose", TEXT),
        ("amount", USD),
        ("funded_date", DATE),
        ("observed_at", INSTANT),
        ("approved", BOOL),
        ("authority_ref", ident("Decision")),
        ("evidence_ref", ident("AdvanceEvidence")),)),
    "AdvanceEvidence": Type("AdvanceEvidence", fields=(
        ("evidence_id", ident("AdvanceEvidence")),
        ("issue_id", ident("AdvanceIssue")),
        ("disbursement_id", ident("Disbursement")),
        ("agreement_id", ident("Agreement")),
        ("participant_id", ident("Participant")),
        ("pool_id", ident("Pool")),
        ("source_title_id", ident("Asset")),
        ("currency", TEXT),
        ("balance_purpose", TEXT),
        ("amount", USD),
        ("funded_date", DATE),
        ("observed_at", INSTANT),
        ("approved", BOOL),
        ("authority_ref", ident("Decision")),
        ("eligible", BOOL),)),
    "ReserveVintage": Type("ReserveVintage", fields=(
        ("vintage_id", ident("Vintage")),
        ("agreement_id", ident("Agreement")),
        ("participant_id", ident("Participant")),
        ("pool_id", ident("Pool")),
        ("purpose", TEXT),
        ("currency", TEXT),
        ("balance", USD),)),
    "ReserveMovement": Type("ReserveMovement", fields=(
        ("event_id", ident("Event")),
        ("agreement_id", ident("Agreement")),
        ("participant_id", ident("Participant")),
        ("pool_id", ident("Pool")),
        ("purpose", TEXT),
        ("currency", TEXT),
        ("vintage_id", ident("Vintage")),
        ("kind", TEXT),
        ("amount", USD),
        ("effective_date", DATE),
        ("observed_at", INSTANT),
        ("evidence_ref", ident("ReserveEvidence")),)),
    "ReserveEvidence": Type("ReserveEvidence", fields=(
        ("evidence_id", ident("ReserveEvidence")),
        ("agreement_id", ident("Agreement")),
        ("participant_id", ident("Participant")),
        ("pool_id", ident("Pool")),
        ("purpose", TEXT),
        ("currency", TEXT),
        ("vintage_id", ident("Vintage")),
        ("kind", TEXT),
        ("amount", USD),
        ("effective_date", DATE),
        ("observed_at", INSTANT),
        ("approved", BOOL),
        ("authority_ref", ident("Decision")),)),
    "PaymentApplication": Type("PaymentApplication", fields=(("event_id", ident("Event")),) + _scope_fields + (
        ("amount", USD), ("obligation_id", ident("Obligation")), ("paid_date", DATE), ("approved", BOOL), ("authority_ref", ident("Decision")))),
})


def fail(code: str, message: str, node: dict | None = None) -> None:
    raise SPLException(code, message, node.get("span") if node else None)


def type_from_ast(value: dict[str, Any]) -> Type:
    name = value["name"]
    args = value.get("args", [])
    if name == "Record":
        fields = value.get("fields", [])
        if len({n for n,_ in fields}) != len(fields):
            fail("DUPLICATE_FIELD", "Duplicate type field")
        return Type("Record", fields=tuple((n,type_from_ast(t)) for n,t in fields))
    if name == "Tuple":
        if len(args) < 2:
            fail("TYPE_ARITY", "Tuple requires at least two components")
        return Type("Tuple", tuple(map(type_from_ast,args)))
    if name == "Map" and len(args) == 2:
        key, val = map(type_from_ast,args)
        if not key_type(key):
            fail("INVALID_MAP_KEY_TYPE", "Map key is not admitted")
        return Type("Map", (key,val))
    if name in SCHEMAS:
        if args:
            fail("TYPE_ARITY", f"{name} does not take type arguments")
        return SCHEMAS[name]
    if name in {"Bool", "Int", "Nat", "Ratio", "Rational", "Text", "Date", "Instant"}:
        if args:
            fail("TYPE_ARITY", f"{name} does not take type arguments")
        return Type(name)
    if name == "Money":
        if len(args) != 1 or args[0]["name"] != "USD" or args[0].get("args"):
            fail("UNSUPPORTED_CURRENCY", "The implemented profile supports Money<USD> only")
        return USD
    if name in {"Quantity", "Rate"}:
        if len(args) != (1 if name == "Quantity" else 2):
            fail("TYPE_ARITY", f"{name} has invalid dimension argument count")
        if any(arg.get("args") or arg.get("fields") for arg in args):
            fail("UNSUPPORTED_TYPE", "Dimension arguments must be atomic")
        validate_unit(args[0]["name"])
        if name == "Rate":
            validate_currency(args[1]["name"])
        return Type(name, tuple(Type(arg["name"]) for arg in args))
    if name in {"List", "Option"} and len(args) == 1:
        return Type(name, (type_from_ast(args[0]),))
    if name == "Id" and len(args) == 1 and not args[0].get("args"):
        return ident(args[0]["name"])
    fail("UNSUPPORTED_TYPE", f"Unsupported type {name}")


def compatible(left: Type, right: Type) -> bool:
    if left == right:
        return True
    if left.name == right.name and left.name in {"List", "Option"}:
        return len(left.args) == len(right.args) == 1 and compatible(left.args[0], right.args[0])
    if left.fields and right.fields:
        return dict(left.fields) == dict(right.fields)
    return False


def key_type(typ: Type) -> bool:
    return typ.name in {"Bool", "Int", "Nat", "Date", "Id"} or (
        typ.name == "Tuple" and len(typ.args) >= 2 and all(map(key_type,typ.args)))


def scalar_type(typ: Type) -> bool:
    """Ordered scalar values, including tuples, distinct from admitted map keys."""
    return typ.numeric or typ.name in {"Date", "Instant", "Text", "Id"} or (
        typ.name == "Tuple" and all(map(scalar_type, typ.args)))


class Scope:
    def __init__(self, checker: "Checker", declarations: list[dict], parent: "Scope | None" = None,
                 bound: dict[str, Type] | None = None):
        self.checker, self.parent = checker, parent
        self.types = dict(bound or {})
        self.declarations = declarations
        self.definitions: dict[str, dict] = {}
        self.active: set[str] = set()
        self.order: list[str] = []
        visible = set(self.types)
        for declaration in declarations:
            if declaration["kind"] not in {"input", "opening", "define"}:
                continue
            name = declaration["name"]
            if name in visible or (parent and parent.has(name)):
                fail("DUPLICATE_NAME", f"Duplicate or shadowing binding {name}", declaration)
            visible.add(name)
            self.definitions[name] = declaration
            if declaration["kind"] in {"input", "opening"}:
                self.types[name] = type_from_ast(declaration["type"])

    def has(self, name: str) -> bool:
        return name in self.types or name in self.definitions or bool(self.parent and self.parent.has(name))

    def resolve(self, name: str, node: dict) -> Type:
        if name in self.types:
            return self.types[name]
        if name in self.active:
            fail("DEPENDENCY_CYCLE", f"Cyclic definition involving {name}", node)
        if name in self.definitions:
            self.active.add(name)
            declaration = self.definitions[name]
            expected = type_from_ast(declaration["type"]) if declaration.get("type") else None
            typ = self.checker.expr(declaration["expr"], self, expected)
            self.types[name] = typ
            self.active.remove(name)
            self.order.append(name)
            return typ
        if self.parent:
            return self.parent.resolve(name, node)
        fail("UNRESOLVED_NAME", f"Unresolved name {name}", node)

    def check(self) -> None:
        for name, declaration in self.definitions.items():
            self.resolve(name, declaration)
        seen_closing: set[str] = set()
        seen_emits: set[str] = set()
        openings = {d["name"] for d in self.declarations if d["kind"] == "opening"}
        for declaration in self.declarations:
            kind = declaration["kind"]
            if kind == "require":
                self.checker.expr(declaration["expr"], self, BOOL)
                if not declaration.get("code"):
                    fail("INVALID_DIAGNOSTIC", "Assertion requires a nonempty diagnostic code", declaration)
            elif kind == "closing":
                name = declaration["name"]
                if name not in openings or name in seen_closing:
                    fail("INVALID_CLOSING_PORT", f"Closing {name} must match exactly one opening", declaration)
                seen_closing.add(name)
                self.checker.expr(declaration["expr"], self, self.types[name])
            elif kind == "emit":
                name = declaration["name"]
                if name in seen_emits:
                    fail("DUPLICATE_OUTPUT", f"Duplicate emission {name}", declaration)
                seen_emits.add(name)
                typ = self.checker.expr(declaration["expr"], self)
                fields = dict(typ.fields)
                if "payable" in fields:
                    needed = {"agreement_id", "participant_id", "period"}
                    if not needed <= fields.keys() or not ({"pool_id", "asset_id"} & fields.keys()):
                        fail("UNRESOLVED_OUTPUT_SCOPE", "A payable output requires agreement, participant, title/pool and period", declaration)
            elif kind not in {"input", "opening", "define"}:
                fail("UNSUPPORTED_DECLARATION", f"Unsupported declaration {kind}", declaration)
        if openings != seen_closing:
            fail("MISSING_CLOSING_PORT", "Every opening binding requires exactly one closing port")


class Checker:
    def expr(self, node: dict, scope: Scope, expected: Type | None = None) -> Type:
        typ = self._expr(node, scope, expected)
        if expected is not None and not compatible(typ, expected):
            fail("TYPE_MISMATCH", f"Expected {expected}, found {typ}", node)
        node["_type"] = typ
        return typ

    def _expr(self, node: dict, scope: Scope, expected: Type | None) -> Type:
        kind = node["kind"]
        if kind == "number":
            if expected and expected.name in {"Int", "Nat", "Ratio", "Rational"}:
                if expected.name in {"Int", "Nat"} and "." in node["value"]:
                    fail("TYPE_MISMATCH", "Decimal literal cannot become an integer", node)
                return expected
            return RATIO if "." in node["value"] else INT
        if kind == "money":
            if node["currency"] != "USD":
                fail("UNSUPPORTED_CURRENCY", "Only USD is supported", node)
            return USD
        if kind in {"bool", "text", "date"}:
            if kind == "date":
                try:
                    if date.fromisoformat(node["value"]).isoformat() != node["value"]:
                        raise ValueError()
                except (ValueError, TypeError):
                    fail("INVALID_DATE", "Expected a valid Gregorian YYYY-MM-DD date", node)
            return {"bool": BOOL, "text": TEXT, "date": DATE}[kind]
        if kind == "name":
            return scope.resolve(node["name"], node)
        if kind == "field":
            record = self.expr(node["expr"], scope)
            fields = dict(record.fields)
            if node["name"] not in fields:
                fail("UNKNOWN_FIELD", f"{record} has no field {node['name']}", node)
            return fields[node["name"]]
        if kind == "unary":
            if node["op"] == "not":
                self.expr(node["expr"], scope, BOOL)
                return BOOL
            typ = self.expr(node["expr"], scope, expected)
            if not typ.numeric or typ.name == "Nat":
                fail("TYPE_MISMATCH", "Unary minus requires signed numeric type", node)
            return typ
        if kind == "binary":
            op = node["op"]
            if op in {"and", "or"}:
                self.expr(node["left"], scope, BOOL)
                self.expr(node["right"], scope, BOOL)
                return BOOL
            left_node, right_node = node["left"], node["right"]
            # Literal numeric inference follows the other operand's units when
            # dimensionless; money literals remain explicitly currency tagged.
            if left_node["kind"] == "number" and right_node["kind"] != "number":
                right = self.expr(right_node, scope)
                hint = right if right.name in {"Int", "Nat", "Ratio", "Rational"} else None
                if op == "*" and right.name in {"Money", "Quantity", "Rate"}:
                    hint = RATIO
                left = self.expr(left_node, scope, hint)
            else:
                left = self.expr(left_node, scope)
                hint = left if left.name in {"Int", "Nat", "Ratio", "Rational"} else None
                if op in {"*", "/"} and left.name in {"Money", "Quantity", "Rate"}:
                    hint = RATIO
                right = self.expr(right_node, scope, hint if right_node["kind"] == "number" else None)
            if op in {"==", "!=", "<", "<=", ">", ">="}:
                if not compatible(left, right):
                    fail("TYPE_MISMATCH", f"Cannot compare {left} with {right}", node)
                if op not in {"==", "!="} and not (scalar_type(left) or key_type(left)):
                    fail("TYPE_MISMATCH", f"No total comparison for {left}", node)
                return BOOL
            if not left.numeric or not right.numeric:
                fail("TYPE_MISMATCH", "Arithmetic requires numeric operands", node)
            if op == "-" and left.name == "Nat":
                fail("UNSUPPORTED_OPERATOR", "Nat subtraction is outside this emitted profile", node)
            if op in {"+", "-"} and compatible(left, right):
                return left
            if left.name in {"Quantity", "Rate"} or right.name in {"Quantity", "Rate"}:
                if op == "*":
                    if left.name in {"Quantity", "Rate"} and right == RATIO:
                        return left
                    if right.name in {"Quantity", "Rate"} and left == RATIO:
                        return right
                    quantity, rate = (left, right) if left.name == "Quantity" else (right, left)
                    if quantity.name == "Quantity" and rate.name == "Rate" and quantity.args[0] == rate.args[0]:
                        return USD
                if op == "/" and left.name in {"Quantity", "Rate"}:
                    if right == RATIO:
                        return left
                    if left == right:
                        return RATIO
                fail("TYPE_MISMATCH", f"Operator {op} is not defined for {left} and {right}", node)
            if op == "*":
                if left.name == "Money" and right == RATIO:
                    return left
                if left == RATIO and right.name == "Money":
                    return right
                if compatible(left, right) and left.name != "Money":
                    return left
            if op == "/":
                if left.name == "Money" and right == RATIO:
                    return left
                if left.name == "Money" and compatible(left, right):
                    return RATIO
                if left == right == RATIO or left == right == Type("Rational"):
                    return left
            fail("TYPE_MISMATCH", f"Operator {op} is not defined for {left} and {right}", node)
        if kind == "if":
            self.expr(node["condition"], scope, BOOL)
            if expected:
                self.expr(node["then"], scope, expected)
                self.expr(node["else"], scope, expected)
                return expected
            if node["then"]["kind"] == "number" and node["else"]["kind"] != "number":
                typ = self.expr(node["else"], scope)
                self.expr(node["then"], scope, typ)
            else:
                typ = self.expr(node["then"], scope)
                self.expr(node["else"], scope, typ)
            return typ
        if kind == "record":
            fields, names = [], set()
            expected_fields = dict(expected.fields) if expected else {}
            for name, expression in node["fields"]:
                if name in names:
                    fail("DUPLICATE_FIELD", f"Duplicate record field {name}", node)
                names.add(name)
                fields.append((name, self.expr(expression, scope, expected_fields.get(name))))
            return Type("Record", fields=tuple(sorted(fields)))
        if kind == "list":
            item_type = expected.args[0] if expected and expected.name == "List" else None
            for expression in node["items"]:
                item_type = self.expr(expression, scope, item_type)
            if item_type is None:
                fail("AMBIGUOUS_EMPTY_LIST", "Empty list needs an expected element type", node)
            return Type("List", (item_type,))
        if kind == "select_rules":
            fallback = node.get("otherwise")
            ids = [arm["rule_id"] for arm in node["arms"]] + ([fallback["rule_id"]] if fallback else [])
            if any(not isinstance(rule_id, str) or not rule_id for rule_id in ids):
                fail("INVALID_RULE_ID", "Rule IDs must be nonempty", node)
            if len(ids) != len(set(ids)):
                fail("DUPLICATE_RULE_ID", "Rule IDs must be unique", node)
            if not node["arms"] and (fallback is None or expected is None):
                fail("EMPTY_RULE_SET", "Empty registered rules require fallback and explicit result type", node)
            result_type = expected
            for arm in node["arms"]:
                if type(arm.get("priority")) is not int:
                    fail("MISSING_RULE_PRIORITY", "Registered priorities require an explicit integer", node)
                self.expr(arm["predicate"], scope, BOOL)
                result_type = self.expr(arm["body"], scope, result_type)
            if fallback is not None:
                result_type = self.expr(fallback["body"], scope, result_type)
            return result_type
        if kind == "choose":
            if not node["arms"]:
                fail("EMPTY_RULE_SET", "choose unique requires at least one arm", node)
            result_type = expected
            known_true = 0
            for predicate, expression in node["arms"]:
                self.expr(predicate, scope, BOOL)
                known_true += predicate["kind"] == "bool" and predicate["value"] is True
                result_type = self.expr(expression, scope, result_type)
            if known_true > 1:
                fail("AMBIGUOUS_RULE", "Multiple statically true choose unique arms", node)
            if node.get("otherwise") is not None:
                self.expr(node["otherwise"], scope, result_type)
            return result_type  # type: ignore[return-value]
        if kind == "apply":
            if len(node["parameters"]) != len(node["args"]):
                fail("FUNCTION_ARITY", "Function argument count differs", node)
            bound = {}
            for parameter, arg in zip(node["parameters"],node["args"]):
                name, typ = parameter["name"], type_from_ast(parameter["type"])
                if name in bound:
                    fail("DUPLICATE_NAME", "Duplicate function parameter", node)
                self.expr(arg,scope,typ)
                bound[name] = typ
            local = Scope(self,node["declarations"],bound=bound)
            local.check()
            result = type_from_ast(node["result"])
            self.expr(node["body"],local,result)
            node["_definition_order"] = local.order
            return result
        if kind == "fold":
            state_type = self.expr(node["initial"],scope,expected)
            source = self.expr(node["source"],scope)
            if source.name != "List":
                fail("TYPE_MISMATCH", "fold requires a finite list", node)
            order = node.get("order")
            if order:
                if order["ties"] != "reject":
                    fail("UNRESOLVED_EVENT_ORDER", "Only explicit reject tie policy is supported", node)
                for binder_key, expression_key in [("key_binder","key"),("id_binder","identity")]:
                    binder = order[binder_key]
                    if scope.has(binder):
                        fail("DUPLICATE_NAME", "Projection binder shadows a name", node)
                    ty = self.expr(order[expression_key],Scope(self,[],scope,{binder:source.args[0]}))
                    if not key_type(ty):
                        fail("INVALID_EVENT_KEY_TYPE", "Event key and identity need admitted total-order types", node)
            if node["state"] == node["event"] or scope.has(node["state"]) or scope.has(node["event"]):
                fail("DUPLICATE_NAME", "Fold binders must be distinct and cannot shadow", node)
            local = Scope(self,node["declarations"],scope,{node["state"]:state_type,node["event"]:source.args[0]})
            local.check()
            self.expr(node["body"],local,state_type)
            node["_definition_order"] = local.order
            return state_type
        if kind == "for":
            source = self.expr(node["source"], scope)
            if source.name != "List":
                fail("TYPE_MISMATCH", "for each requires a finite list", node)
            if scope.has(node["name"]):
                fail("DUPLICATE_NAME", f"Iterator shadows {node['name']}", node)
            local = Scope(self, node["declarations"], scope, {node["name"]: source.args[0]})
            if any(d["kind"] not in {"define", "require"} for d in node["declarations"]):
                fail("INVALID_LOCAL_DECLARATION", "A comprehension body permits only definitions and assertions", node)
            local.check()
            node["_definition_order"] = local.order
            node["_local_types"] = local.types
            hint = expected.args[0] if expected and expected.name == "List" else None
            return Type("List", (self.expr(node["yield"], local, hint),))
        if kind == "call":
            name, args = node["name"], node["args"]
            if name in {"append","concat"}:
                self.arity(node,2)
                source = self.expr(args[0],scope,expected)
                if source.name != "List":
                    fail("TYPE_MISMATCH", "append/concat require a list", node)
                self.expr(args[1],scope,source.args[0] if name == "append" else source)
                return source
            if name == "none":
                self.arity(node,0)
                if expected is None or expected.name != "Option":
                    fail("AMBIGUOUS_OPTION", "none requires expected Option type",node)
                return expected
            if name == "some":
                self.arity(node,1)
                return Type("Option",(self.expr(args[0],scope,expected.args[0] if expected and expected.name == "Option" else None),))
            if name in {"get_or","is_some"}:
                self.arity(node,2 if name == "get_or" else 1)
                option = self.expr(args[0],scope,Type("Option",(expected,)) if expected and name == "get_or" else None)
                if option.name != "Option":
                    fail("TYPE_MISMATCH","Expected Option",node)
                if name == "is_some":
                    return BOOL
                self.expr(args[1],scope,option.args[0])
                return option.args[0]
            if name == "tuple":
                if len(args) < 2:
                    fail("BUILTIN_ARITY","tuple requires at least two components",node)
                hints = expected.args if expected and expected.name == "Tuple" else (None,)*len(args)
                if len(hints) != len(args):
                    fail("TYPE_MISMATCH","Tuple arity differs",node)
                return Type("Tuple",tuple(self.expr(a,scope,h) for a,h in zip(args,hints)))
            if name == "tuple_get":
                self.arity(node,2)
                typ = self.expr(args[0],scope)
                index = args[1]
                if typ.name != "Tuple":
                    fail("TYPE_MISMATCH","tuple_get requires Tuple",node)
                if index["kind"] != "number" or not index["value"].isdigit() or int(index["value"]) >= len(typ.args):
                    fail("INVALID_TUPLE_INDEX","Expected in-bounds natural literal index",node)
                self.expr(index,scope,INT)
                return typ.args[int(index["value"])]
            if name in {"lookup","entries"}:
                self.arity(node,2 if name == "lookup" else 1)
                typ = self.expr(args[0],scope)
                if typ.name != "Map":
                    fail("TYPE_MISMATCH","Expected Map",node)
                k,v = typ.args
                if name == "entries":
                    return Type("List",(Type("Record",fields=(("key",k),("value",v))),))
                self.expr(args[1],scope,k)
                return Type("Option",(v,))
            if name in {"make_map","join","left_join"}:
                self.arity(node,3 if name == "make_map" else 4)
                lt = self.expr(args[0],scope)
                rt = lt if name == "make_map" else self.expr(args[1],scope)
                if lt.name != "List" or rt.name != "List":
                    fail("TYPE_MISMATCH","Indexed operators require lists",node)
                kl,vl = args[-2:]
                def projection(lam, item, hint=None):
                    if lam["kind"] != "lambda":
                        fail("TYPE_MISMATCH","Expected projection lambda",node)
                    if scope.has(lam["name"]):
                        fail("DUPLICATE_NAME","Projection shadows name",lam)
                    body = self.expr(lam["body"],Scope(self,[],scope,{lam["name"]:item}),hint)
                    lam["_type"] = Type("Lambda",(item,body))
                    return body
                kt = projection(kl,lt.args[0])
                if not key_type(kt):
                    fail("INVALID_MAP_KEY_TYPE","Key type is not admitted",node)
                vt = projection(vl,rt.args[0],expected.args[1] if name == "make_map" and expected and expected.name == "Map" else None)
                if name == "make_map":
                    return Type("Map",(kt,vt))
                if kt != vt:
                    fail("TYPE_MISMATCH","Join keys must have identical types",node)
                return Type("List",(Type("Record",fields=(("left",lt.args[0]),("right",Type("Option",(rt.args[0],)) if name == "left_join" else rt.args[0]))),))
            if name in {"filter", "map", "sum", "sort_by", "group_by"}:
                self.arity(node, 2)
                source = self.expr(args[0], scope)
                if source.name != "List" or args[1]["kind"] != "lambda":
                    fail("TYPE_MISMATCH", f"{name} requires a list and a one-variable lambda", node)
                lam = args[1]
                if scope.has(lam["name"]):
                    fail("DUPLICATE_NAME", f"Lambda shadows {lam['name']}", lam)
                local = Scope(self, [], scope, {lam["name"]: source.args[0]})
                hint = BOOL if name == "filter" else expected if name == "sum" else None
                body = self.expr(lam["body"], local, hint)
                lam["_type"] = Type("Lambda", (source.args[0], body))
                if name == "group_by":
                    if not key_type(body):
                        fail("INVALID_MAP_KEY_TYPE","Group key type is not admitted",node)
                    return Type("Map",(body,source))
                if name == "sum":
                    if not body.numeric:
                        fail("TYPE_MISMATCH", "sum requires numeric mapped values", node)
                    return body
                if name == "sort_by" and not (scalar_type(body) or key_type(body)):
                    fail("TYPE_MISMATCH", "sort_by requires a scalar total-order key", node)
                return source if name in {"filter", "sort_by"} else Type("List", (body,))
            if name == "instant":
                self.arity(node, 1)
                self.expr(args[0], scope, TEXT)
                if args[0]["kind"] == "text":
                    from .instant import parse_instant
                    parse_instant(args[0]["value"])
                return INSTANT
            if name in {"min", "max", "abs"}:
                self.arity(node, 1 if name == "abs" else 2)
                typ = self.expr(args[0], scope, expected)
                if name != "abs":
                    self.expr(args[1], scope, typ)
                if not typ.numeric:
                    fail("TYPE_MISMATCH", f"{name} requires numeric operands", node)
                return typ
            if name == "add_calendar_months":
                self.arity(node, 3)
                self.expr(args[0], scope, DATE)
                self.expr(args[1], scope, Type("Nat"))
                self.expr(args[2], scope, TEXT)
                if args[2]["kind"] == "text" and args[2]["value"] not in {"clamp_day", "reject_invalid_day"}:
                    fail("CALENDAR_UNSUPPORTED_POLICY", "Unsupported calendar invalid-day policy", node)
                return DATE
            if name == "in_period":
                self.arity(node, 2)
                self.expr(args[0], scope, DATE)
                self.expr(args[1], scope, PERIOD)
                return BOOL
            if name == "is_calendar_quarter":
                self.arity(node, 1)
                self.expr(args[0], scope, PERIOD)
                return BOOL
            if name == "quantize":
                self.arity(node, 3)
                typ = self.expr(args[0], scope, expected)
                if not typ.numeric:
                    fail("TYPE_MISMATCH", "quantize requires a number", node)
                self.expr(args[1], scope, typ)
                self.expr(args[2], scope, TEXT)
                if args[2]["kind"] != "text" or args[2]["value"] not in MODES:
                    fail("UNSUPPORTED_ROUNDING_MODE", "quantize mode must be a supported literal", node)
                return typ
            if name == "require_some":
                self.arity(node, 2)
                typ = self.expr(args[0], scope,Type("Option",(expected,)) if expected else None)
                self.expr(args[1], scope, TEXT)
                if typ.name != "Option" or args[1]["kind"] != "text":
                    fail("TYPE_MISMATCH", "require_some requires Option and literal diagnostic", node)
                return typ.args[0]
            fail("UNSUPPORTED_BUILTIN", f"Unsupported pure built-in {name}", node)
        fail("UNSUPPORTED_EXPRESSION", f"Unsupported expression kind {kind}", node)

    @staticmethod
    def arity(node: dict, count: int) -> None:
        if len(node["args"]) != count:
            fail("BUILTIN_ARITY", f"{node['name']} requires {count} arguments", node)


def check_schedule(schedule: dict[str, Any]) -> CheckedSchedule:
    for field, expected in (("language", "spl/0.1-draft"), ("core", "spl-core/0.1-draft"), ("schema", "spl-data/0.1-draft")):
        if schedule.get(field) != expected:
            fail("UNSUPPORTED_VERSION", f"Expected {field} {expected}", schedule)
    aliases = [d["alias"] for d in schedule["declarations"] if d["kind"] == "opening"]
    if len(aliases) != len(set(aliases)):
        fail("DUPLICATE_OPENING_ALIAS", "Opening aliases must be unique", schedule)
    checker = Checker()
    scope = Scope(checker, schedule["declarations"])
    scope.check()
    return CheckedSchedule(schedule, scope.types, scope.order)
