"""Pure first-order module linking over already pin-verified source manifests.

The canonical registry verifies descriptor/source SHA-256 pins before constructing
this manifest. Linking never reads files, substitutes argument text, or evaluates
host code. Application nodes preserve strict arguments and lexical isolation.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .model import SPLException
from .parser import parse

BUILTINS = frozenset("filter map sum sort_by min max instant in_period is_calendar_quarter add_calendar_months quantize require_some tuple tuple_get make_map lookup entries group_by join left_join some none get_or is_some append concat".split())


def link_schedule(schedule: dict, manifest: dict) -> dict:
    """Return a capture-free AST; call ``check`` on the result before execution."""
    def fail(code, message):
        raise SPLException(code, message)

    def identity(reference):
        if not isinstance(reference, dict) or set(reference) != {"id", "revision", "locator", "sha256"}:
            fail("INVALID_MODULE_REFERENCE", "Require complete exact module reference")
        return json.dumps(reference, sort_keys=True, separators=(",", ":"))

    modules = {}
    for entry in manifest.get("modules", []):
        key = identity(entry["reference"])
        if key in modules:
            fail("DUPLICATE_MODULE", "Repeated exact module reference")
        descriptor = entry["descriptor"]
        if any(descriptor.get(field) != entry["reference"][field] for field in ("id", "revision")):
            fail("MODULE_IDENTITY_MISMATCH", "Descriptor and exact reference disagree")
        source = parse(entry["source"], "module:" + descriptor["id"])
        if any(source.get(k) != v for k, v in (("language", "spl/0.1-draft"), ("core", "spl-core/0.1-draft"), ("schema", "spl-data/0.1-draft"))):
            fail("UNSUPPORTED_VERSION", "Unsupported module source versions")
        if any(d["kind"] not in {"input", "define", "require"} for d in source["declarations"]):
            fail("INVALID_FUNCTION_MODULE", "Function modules permit inputs, definitions and assertions")
        exports = descriptor["interface"]["exports"]
        if len({e["name"] for e in exports}) != len(exports):
            fail("DUPLICATE_EXPORT", "Export names must be unique")
        modules[key] = (descriptor, source, exports)

    def namespace(imports, own=()):
        result, aliases = {}, set()
        for spec in imports:
            key = identity(spec["module_ref"])
            if key not in modules:
                fail("UNRESOLVED_MODULE", "Exact transitive module pin is absent")
            alias = spec["alias"]
            if alias in aliases:
                fail("AMBIGUOUS_IMPORT", "Import aliases must be unique")
            aliases.add(alias)
            for symbol in spec["symbols"]:
                name = symbol["local"]
                if name in result or name in own or name in BUILTINS:
                    fail("AMBIGUOUS_IMPORT", "Imported local name collides: " + name)
                if not any(e["name"] == symbol["export"] for e in modules[key][2]):
                    fail("UNRESOLVED_EXPORT", "Imported symbol is not exported")
                result[name] = (key, symbol["export"])
        return result

    namespaces = {}
    for key, (descriptor, source, exports) in modules.items():
        names = [e["name"] for e in exports]
        if any(name in BUILTINS for name in names):
            fail("AMBIGUOUS_EXPORT", "Function export collides with a published builtin")
        namespaces[key] = namespace(descriptor["imports"], names)
        bindings = {d.get("name") for d in source["declarations"] if d["kind"] in {"input", "define"}}
        if bindings & namespaces[key].keys():
            fail("AMBIGUOUS_IMPORT", "Imported function collides with a module binding")
        namespaces[key].update({name: (key, name) for name in names})
    root_names = namespace(manifest.get("imports", []))
    root_bindings = {d.get("name") for d in schedule["declarations"] if d["kind"] in {"input", "opening", "define"}}
    if root_bindings & root_names.keys():
        fail("AMBIGUOUS_IMPORT", "Imported function collides with a schedule binding")

    def visit_module(key, active, done):
        if key in active:
            fail("MODULE_IMPORT_CYCLE", "Module imports must be acyclic")
        if key in done:
            return
        for spec in modules[key][0]["imports"]:
            visit_module(identity(spec["module_ref"]), active | {key}, done)
        done.add(key)

    done = set()
    for key in modules:
        visit_module(key, set(), done)

    def function(target, active):
        if target in active:
            fail("FUNCTION_CALL_CYCLE", "Function calls must be nonrecursive")
        if len(active) >= 128:
            fail("RESOURCE_LIMIT", "Function expansion depth exceeds 128")
        key, name = target
        descriptor, source, exports = modules[key]
        export = next(e for e in exports if e["name"] == name)
        inputs = [{"name": d["name"], "type": d["type"]} for d in source["declarations"] if d["kind"] == "input"]
        if json.dumps(inputs, sort_keys=True) != json.dumps(export["parameters"], sort_keys=True):
            fail("FUNCTION_INTERFACE_MISMATCH", "Function parameters must exactly match source inputs")
        definition = next((d for d in source["declarations"] if d["kind"] == "define" and d["name"] == export["definition"]), None)
        if definition is None:
            fail("UNRESOLVED_EXPORT", "Export definition is absent")
        locals_ = [d for d in source["declarations"] if d["kind"] in {"define", "require"}]
        nested = active | {target}
        return {"parameters": deepcopy(inputs), "result": deepcopy(export["result"]),
                "declarations": transform(deepcopy(locals_), namespaces[key], nested),
                "body": {"kind": "name", "name": definition["name"], "span": definition["span"]},
                "function": descriptor["id"] + "@" + descriptor["revision"] + ":" + name}

    def transform(value, names, active):
        if isinstance(value, list):
            return [transform(v, names, active) for v in value]
        if isinstance(value, tuple):
            return tuple(transform(v, names, active) for v in value)
        if not isinstance(value, dict):
            return value
        if value.get("kind") == "call" and value["name"] in names:
            args = transform(value["args"], names, active)
            return {"kind": "apply", "span": value["span"], "args": args,
                    **function(names[value["name"]], active)}
        return {k: transform(v, names, active) for k, v in value.items() if not k.startswith("_")}

    # Validate every export, including unused definitions/cycles.
    from .checker import Checker, Scope, type_from_ast
    for key, (_, _, exports) in modules.items():
        for export in exports:
            compiled = function((key, export["name"]), set())
            checker = Checker()
            bound = {p["name"]: type_from_ast(p["type"]) for p in compiled["parameters"]}
            checker.expr({"kind": "apply", "span": {}, **compiled,
                          "args": [{"kind":"name", "name":p["name"], "span":{}}
                                   for p in compiled["parameters"]]}, Scope(checker, [], bound=bound))
    return transform(deepcopy(schedule), root_names, set())
