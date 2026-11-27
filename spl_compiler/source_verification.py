"""Independent source and typed-IR correspondence for the native SPL compiler.

The Python frontend is the source specification for this check. A match is a
structural witness over one authored program and the links supplied to it. The
source/frontend specification itself, source spans and Lean lowering have their
own proof obligations.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from .checker import check_schedule, type_from_ast
from .codecs import DataError, digest, fail, read_json
from .dimensions import admission
from .ir_artifacts import validate_ir_artifact
from .lean_tools import FrontendDiagnostic
from .linker import link_schedule
from .model import BOOL, CheckedSchedule, SPLException, Type
from .parser import parse
from .readable import is_readable, parse_readable


def _check_links(schedule, link):
    try:
        manifest = read_json(link)
        if not isinstance(manifest, dict) or not all(isinstance(manifest.get(key), list)
                                                    for key in ("modules", "imports")):
            fail("SOURCE_LINK_INVALID", "Expected a module and import list")
        for entry in manifest["modules"]:
            descriptor = entry["descriptor"]
            if "source" in descriptor:
                expected = descriptor["source"]["sha256"]
                actual = sha256(entry["source"].encode("utf-8")).hexdigest()
                if expected != actual:
                    fail("SOURCE_LINK_PIN_MISMATCH", f"Changed linked source for {descriptor['id']}")
        return link_schedule(schedule, manifest)
    except (DataError, SPLException) as error:
        message = error.message if isinstance(error, SPLException) else str(error)
        raise FrontendDiagnostic(error.code, message, source=str(link), span=error.span, stage="link") from error
    except (TypeError, KeyError, AttributeError) as error:
        raise FrontendDiagnostic("SOURCE_LINK_INVALID", str(error), source=str(link), span=None, stage="link") from error
    except (UnicodeError, OSError) as error:
        raise FrontendDiagnostic("SOURCE_READ_FAILED", str(error), source=str(link), span=None, stage="link") from error


def check_source(source: Path, *, link: Path | None = None) -> CheckedSchedule:
    """Parse, resolve and type-check exact source independently of native SPL.

    The manifest binds its embedded source content. Registry authentication of
    descriptor file bytes and external policy approval take place upstream.
    """
    source = Path(source)
    try:
        authored = source.read_bytes().decode("utf-8")
        schedule = (parse_readable if is_readable(authored) else parse)(authored, str(source))
        if link is not None:
            schedule = _check_links(schedule, link)
        return check_schedule(schedule)
    except SPLException as error:
        raise DataError(error.code, error.message, str(source), error.span) from error
    except (UnicodeError, OSError) as error:
        raise DataError("SOURCE_READ_FAILED", str(error), str(source)) from error


def _type(typ: Type) -> dict:
    name, args = typ.name, typ.args
    if name == "Id":
        return {"kind": "atom", "name": "Id:" + args[0].name}
    if name == "Money":
        return {"kind": "money", "currency": args[0].name}
    if name == "Quantity":
        return {"kind": "quantity", "unit": args[0].name}
    if name == "Rate":
        return {"kind": "rate", "unit": args[0].name, "currency": args[1].name}
    if name in {"List", "Option"}:
        return {"kind": name.lower(), "item": _type(args[0])}
    if name == "Tuple":
        return {"kind": "tuple", "items": [_type(item) for item in args]}
    if name == "Map":
        return {"kind": "map", "key": _type(args[0]), "value": _type(args[1])}
    if typ.fields or name == "Record":
        return {"kind": "record", "name": "literal" if name == "Record" else name,
                "fields": [{"name": field, "type": _type(t)} for field, t in sorted(typ.fields)]}
    return {"kind": "atom", "name": name}


def _owner(label):
    if not label.startswith("@module:"):
        return label
    # The linkers serialize the same exact reference as an object or an array.
    ref = json.loads(label.removeprefix("@module:"))
    if isinstance(ref, dict):
        ref = [ref[field] for field in ("id", "revision", "locator", "sha256")]
    return "@module:" + json.dumps(ref, ensure_ascii=False, separators=(",", ":"))


class _SourceProjection:
    def __init__(self, checked):
        self.checked = checked
        self.owners = dict(checked.schedule.get("dimension_owners", ()))
        self.extended_owners = any(self.owners.values())
        self.extended = bool(checked.admission.features or self.extended_owners)

    def declaration(self, decl, ctx, inherited=None):
        kind = decl["kind"]
        if kind in {"input", "opening"}:
            result = {"kind": kind, "name": decl["name"], "meta": {"type": _type(self.checked.types[decl["name"]])}}
            if kind == "opening":
                result["alias"] = decl["alias"]
            return result
        expr = decl["expr"]
        citation = decl.get("citation")
        if citation is None:
            citation = inherited
        ftype = expr["_type"]
        if kind == "require":
            ftype = BOOL
        elif kind == "closing":
            ftype = self.checked.types[decl["name"]]
        meta = self.meta(ftype, citation)
        if kind == "define" and (ctx.features or self.extended_owners) and decl.get("type") is not None:
            meta["source_annotation"] = _type(type_from_ast(decl["type"], ctx))
        if kind == "require":
            return {"kind": kind, "meta": meta, "condition": self.expression(expr, citation), "code": decl["code"]}
        return {"kind": kind, "meta": meta, "name": decl["name"], "body": self.expression(expr, citation)}

    @staticmethod
    def meta(typ, citation):
        return {"type": _type(typ)} if citation is None else {"type": _type(typ), "citation": citation}

    def expression(self, expr, citation):
        def nested(body):
            return self.expression(body, citation)

        kind = expr["kind"]
        meta = self.meta(expr["_type"], citation)
        result = {"kind": kind, "meta": meta}
        if kind in {"number", "money", "bool", "text", "date"}:
            if kind == "bool":
                result["kind"] = "boolean"
            if kind == "money":
                result["currency"] = expr["currency"]
            result["value"] = expr["value"]
        elif kind == "name":
            result["name"] = expr["name"]
        elif kind == "unary":
            result.update(op=expr["op"], body=nested(expr["expr"]))
        elif kind == "binary":
            result.update(op=expr["op"], left=nested(expr["left"]), right=nested(expr["right"]))
        elif kind == "field":
            result.update(base=nested(expr["expr"]), name=expr["name"])
        elif kind == "if":
            result.update({field: nested(expr[field]) for field in ("condition", "then", "else")})
        elif kind == "record":
            result["fields"] = [{"name": name, "value": nested(value)} for name, value in expr["fields"]]
        elif kind == "list":
            result["items"] = [nested(item) for item in expr["items"]]
        elif kind == "choose":
            result.update(kind="choose_unique", arms=[{"predicate": nested(p), "body": nested(b)} for p, b in expr["arms"]])
            if expr.get("otherwise") is not None:
                result["otherwise"] = nested(expr["otherwise"])
        elif kind == "select_rules":
            result.update(priority_mode=expr["priority_mode"], arms=[
                {**arm, "predicate": nested(arm["predicate"]), "body": nested(arm["body"])} for arm in expr["arms"]])
            if expr.get("otherwise") is not None:
                fallback = expr["otherwise"]
                result["otherwise"] = {**fallback, "body": nested(fallback["body"])}
        elif kind == "call":
            result.update(self.call(expr, nested))
        elif kind in {"for", "fold"}:
            src = expr["source"]
            item_type = _type(src["_type"].args[0])
            result.update(source=nested(src), declarations=[self.declaration(d, expr["_admission"], citation)
                                                             for d in expr["declarations"]])
            if kind == "for":
                result.update(kind="for_each", binder=expr["name"], binder_type=item_type, **{"yield": nested(expr["yield"])})
            else:
                result.update(initial=nested(expr["initial"]), state_binder=expr["state"], event_binder=expr["event"],
                              event_type=item_type, **{"yield": nested(expr["body"])})
                if expr.get("order") is not None:
                    order = expr["order"]
                    result["order"] = {**order, "key": nested(order["key"]), "identity": nested(order["identity"])}
        elif kind == "apply":
            owner = admission(self.owners.get(expr["function"], ()))
            result.update(function=expr["function"], parameters=self.parameters(expr, owner),
                          arguments=[nested(arg) for arg in expr["args"]], body=nested(expr["body"]),
                          declarations=[self.declaration(d, owner, citation) for d in expr["declarations"]])
        else:
            fail("SOURCE_PROJECTION_UNSUPPORTED", f"Cannot project source expression {kind}")
        return result

    @staticmethod
    def call(expr, nested):
        name, args = expr["name"], expr["args"]
        if name in {"filter", "map", "sum", "sort_by", "group_by"}:
            source, lam = args
            return {"kind": "collection", "op": name, "source": nested(source), "binder": lam["name"],
                    "binder_type": _type(lam["_type"].args[0]), "body": nested(lam["body"])}
        if name in {"make_map", "join", "left_join"}:
            key, value = args[-2:]
            result = {"kind": "indexed", "op": name, "source": nested(args[0]), "key_binder": key["name"],
                      "key_binder_type": _type(key["_type"].args[0]), "key": nested(key["body"]),
                      "value_binder": value["name"], "value_binder_type": _type(value["_type"].args[0]),
                      "value": nested(value["body"])}
            if name != "make_map":
                result["right"] = nested(args[1])
            return result
        return {"name": name, "arguments": [nested(arg) for arg in args]}

    @staticmethod
    def parameters(node, ctx):
        return [{"name": p["name"], "type": _type(type_from_ast(p["type"], ctx))} for p in node["parameters"]]

    def program(self):
        schedule = self.checked.schedule
        result = {field: schedule[field] for field in ("name", "language", "core", "schema")}
        result.update(format="spl-ir/0.2" if self.extended else "spl-ir/0.1",
                      declarations=[self.declaration(d, self.checked.admission) for d in schedule["declarations"]])
        if self.extended:
            signatures = []
            for entry in schedule.get("dimension_signatures", ()):
                owner = admission(self.owners[entry["label"]])
                signatures.append({"label": entry["label"], "parameters": self.parameters(entry, owner),
                                   "result": _type(type_from_ast(entry["result"], owner))})
            result["dimension_admission"] = {
                "features": list(schedule.get("features", ())),
                "owners": [{"label": _owner(label), "features": list(features)} for label, features in self.owners.items()],
                "signatures": signatures,
            }
        return result


def _native_projection(value):
    if isinstance(value, list):
        return [_native_projection(child) for child in value]
    if not isinstance(value, dict):
        return value
    result = {key: _native_projection(child) for key, child in value.items()}
    if "meta" in result:
        del result["meta"]["id"]
        del result["meta"]["span"]
    if result.get("kind") == "record" and "meta" not in result:
        result["fields"].sort(key=lambda field: field["name"])
    return result


def _difference(expected, actual, path=""):
    if type(expected) is not type(actual):
        return path, "different value types"
    if isinstance(expected, dict):
        if expected.keys() != actual.keys():
            return path, "different fields"
        items = ((f"{path}/{key}", left, actual[key]) for key, left in expected.items())
    elif isinstance(expected, list):
        if len(expected) != len(actual):
            return path, "different sequence lengths"
        items = ((f"{path}/{i}", left, right) for i, (left, right) in enumerate(zip(expected, actual)))
    else:
        return (path, "different values") if expected != actual else None
    for pointer, left, right in items:
        difference = _difference(left, right, pointer)
        if difference:
            return difference
    return None


def check_native_ir(checked: CheckedSchedule, ir: dict) -> dict:
    """Require the complete semantic projection of native IR to match source.

    Source spans and compiler-assigned trace IDs are omitted. The independent
    v2 preflight checks the contents of the versioned dimension catalog.
    """
    validate_ir_artifact(ir)
    try:
        expected = _SourceProjection(checked).program()
        actual = _native_projection(ir)
        del actual["span"]
        if "dimension_admission" in actual:
            snapshot = actual["dimension_admission"]
            del snapshot["unit_definitions"]
            del snapshot["relations"]
            for owner in snapshot["owners"]:
                owner["label"] = _owner(owner["label"])
    except (TypeError, KeyError, AttributeError, json.JSONDecodeError) as error:
        raise DataError("SOURCE_IR_MALFORMED", str(error)) from error
    difference = _difference(expected, actual)
    if difference:
        pointer, reason = difference
        fail("SOURCE_IR_MISMATCH", f"Native IR and independently checked source have {reason}", pointer)
    return {"status": "source_ir_matched", "projection_sha256": digest(expected)}
