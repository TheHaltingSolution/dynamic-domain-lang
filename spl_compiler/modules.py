"""Pinned declarative interfaces and generic canonical execution.

The compiler remains the authority for economic expressions. JSON descriptors
contain ports, pins and a finite constraint vocabulary, never executable code.
Dependency resolution alone does not implement source function imports.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
import re

from .codecs import (DataError, amount, canonical, check_text, day, digest, exact,
                     fail, file_digest, instant, money, number, period, read_json,
                     write_json)
from .model import SPLException


SCHEMA_ROOT = Path(__file__).resolve().parent.parent / "schemas"
CAPABILITIES = {"spl.core/1", "spl.instant/1", "spl.priority/1", "spl.tuple-map/1",
                "spl.group-join/1", "spl.fold/1", "spl.modules/1", "spl.calendar-months/1", "spl.quantities/1"}
INPUT_ROLES = {"input": "inputs", "parameter": "parameters", "evidence": "evidence"}
OUTPUT_ROLES = {"result", "detail", "reconciliation"}


def _shape(value, schema, root=None, pointer=""):
    """The closed JSON Schema vocabulary used by the two published schemas."""
    root = root or schema
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].split("/")[1:]:
            target = target[part]
        return _shape(value, target, root, pointer)
    if "const" in schema and value != schema["const"]:
        fail("MODULE_SCHEMA_VERSION", f"Expected {schema['const']!r}", pointer)
    if "enum" in schema and value not in schema["enum"]:
        fail("MODULE_SCHEMA_ENUM", f"Unsupported value {value!r}", pointer)
    kind = schema.get("type")
    valid = {"object": isinstance(value, dict), "array": isinstance(value, list),
             "string": isinstance(value, str), "integer": type(value) is int,
             "boolean": type(value) is bool}.get(kind, True)
    if not valid:
        fail("MODULE_SCHEMA_TYPE", f"Expected {kind}", pointer)
    if kind == "object":
        properties = schema.get("properties", {})
        if set(schema.get("required", [])) - value.keys():
            fail("MODULE_MISSING_FIELD", "Missing required descriptor or binding field", pointer)
        unknown = value.keys() - properties.keys()
        additional = schema.get("additionalProperties", True)
        if unknown and additional is False:
            fail("MODULE_UNKNOWN_FIELD", "Unknown fields " + repr(sorted(unknown)), pointer)
        for key, item in value.items():
            child = properties.get(key, additional if isinstance(additional, dict) else {})
            _shape(item, child, root, pointer + "/" + key)
    elif kind == "array":
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            fail("MODULE_CARDINALITY", "Array cardinality outside the schema bounds", pointer)
        if schema.get("uniqueItems") and len({canonical(x) for x in value}) != len(value):
            fail("MODULE_DUPLICATE_VALUE", "Duplicate values", pointer)
        prefix = schema.get("prefixItems", [])
        for index, item in enumerate(value):
            child = prefix[index] if index < len(prefix) else schema.get("items", {})
            if child is False:
                fail("MODULE_CARDINALITY", "Extra array item", pointer)
            _shape(item, child, root, f"{pointer}/{index}")
    elif kind == "string":
        if len(value) < schema.get("minLength", 0) or ("pattern" in schema and not re.fullmatch(schema["pattern"], value)):
            fail("MODULE_SCHEMA_PATTERN", "Invalid string spelling", pointer)
    elif kind == "integer" and value < schema.get("minimum", value):
        fail("MODULE_SCHEMA_RANGE", "Value below minimum", pointer)


def _validate_document(value, schema_name):
    check_text(value)
    _shape(value, read_json(SCHEMA_ROOT / schema_name))


def _resource_guard(package):
    """Count top-level collection rows separately from nested transport volume."""
    if not isinstance(package, dict):
        fail("MODULE_SCHEMA_TYPE", "A module package must be an object")
    counts = {group: sum(len(value) for value in package.get(group, {}).values() if isinstance(value, list))
              if isinstance(package.get(group), dict) else 0 for group in ["inputs", "parameters", "evidence"]}
    cells = package.get("state_cells", [])
    counts["state_payloads"] = sum(len(cell["quantity"]) for cell in cells
                                   if isinstance(cell, dict) and isinstance(cell.get("quantity"), list)) if isinstance(cells, list) else 0
    counts["total"] = sum(counts.values())
    if counts["total"] > 100000:
        fail("RESOURCE_LIMIT", "Generic top-level input/evidence/parameter/state collection rows exceed 100000; no truncated calculation")
    stack = [(package.get(group, {}), 0) for group in ["inputs", "parameters", "evidence", "state_cells"]]
    items, scalars = 0, 0
    while stack:
        value, depth = stack.pop()
        if depth > 128:
            fail("RESOURCE_LIMIT", "Generic input nesting exceeds 128")
        if isinstance(value, list):
            items += len(value)
            if items > 1000000:
                fail("RESOURCE_LIMIT", "Generic nested transport exceeds 1000000 array elements")
            stack.extend((item, depth + 1) for item in value)
        elif isinstance(value, dict):
            stack.extend((item, depth + 1) for item in value.values())
        else:
            scalars += 1
            if scalars > 1000000:
                fail("RESOURCE_LIMIT", "Generic supplied values exceed 1000000 scalar fields")
    return counts


def _unique(rows, key, code):
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            fail(code, f"Duplicate {key}: {value}")
        result[value] = row
    return result


def _pinned_file(pin, registry_root):
    root = Path(registry_root).resolve()
    if "\x00" in pin["locator"]:
        fail("MODULE_DEPENDENCY_MISSING", "Invalid dependency locator")
    path = (root / pin["locator"]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        fail("MODULE_DEPENDENCY_MISSING", "Dependency must name a file within the registry: " + pin["locator"])
    if file_digest(path) != pin["sha256"]:
        fail("MODULE_DEPENDENCY_DIGEST", "Stale dependency: " + pin["locator"])
    return path


def _parse_source(path):
    from .parser import parse
    from .readable import is_readable, parse_readable
    source = path.read_text(encoding="utf-8")
    return parse_readable(source, path.name) if is_readable(source) else parse(source, path.name)


def _check_capabilities(descriptor, syntax):
    from .model import Type
    from .dimensions import UNIT_DICTIONARY, UNITS
    required = {"spl.core/1"}
    used_units = set()
    if descriptor["imports"] or descriptor["interface"]["exports"]:
        required.add("spl.modules/1")

    def scan(value):
        if isinstance(value, Type):
            if value.name == "Instant":
                required.add("spl.instant/1")
            if value.name in {"Tuple", "Map"}:
                required.add("spl.tuple-map/1")
            if value.name in {"Quantity", "Rate"}:
                required.add("spl.quantities/1")
                if value.args:
                    used_units.add(value.args[0].name)
            for child in value.args:
                scan(child)
            for _, child in value.fields:
                scan(child)
        elif isinstance(value, dict):
            if value.get("name") in {"Quantity", "Rate"} and "args" in value:
                required.add("spl.quantities/1")
                if value["args"]:
                    used_units.add(value["args"][0]["name"])
            if value.get("kind") == "select_rules":
                required.add("spl.priority/1")
            if value.get("kind") == "fold":
                required.add("spl.fold/1")
            if value.get("kind") == "apply":
                required.add("spl.modules/1")
            if value.get("kind") == "call":
                name = value["name"]
                if name == "instant":
                    required.add("spl.instant/1")
                if name == "add_calendar_months":
                    required.add("spl.calendar-months/1")
                if name in {"tuple", "tuple_get", "make_map", "lookup", "entries", "some", "none", "get_or", "is_some"}:
                    required.add("spl.tuple-map/1")
                if name in {"group_by", "join", "left_join"}:
                    required.update({"spl.group-join/1", "spl.tuple-map/1"})
                if name in {"append", "concat"}:
                    required.add("spl.fold/1")
            for key, child in value.items():
                if key != "span":
                    scan(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                scan(child)

    scan(syntax)
    for port in descriptor["interface"]["ports"]:
        scan(_port_type(port, descriptor))
    for schema in descriptor["interface"]["schemas"]:
        scan(schema["fields"])
    for export in descriptor["interface"]["exports"]:
        scan(export)
    missing = required - set(descriptor["compatibility"]["capabilities"])
    if missing:
        fail("MODULE_CAPABILITY_UNDECLARED", repr(sorted(missing)))
    codecs = set(descriptor["compatibility"]["codecs"])
    if "spl.quantities/1" in required and "spl-quantity/1" not in codecs:
        fail("MODULE_CODEC_VERSION", "Dimensional interfaces require spl-quantity/1")
    declared_units = set(descriptor["interface"]["dictionaries"].get(UNIT_DICTIONARY, []))
    if declared_units - UNITS or used_units - UNITS:
        fail("UNSUPPORTED_UNIT", repr(sorted((declared_units | used_units) - UNITS)))
    if used_units - declared_units:
        fail("MODULE_UNIT_UNDECLARED", repr(sorted(used_units - declared_units)))


@dataclass
class ResolvedModule:
    reference: dict
    descriptor: dict
    source_path: Path
    policy_path: Path
    closure: list[dict]
    registry_root: Path

    @property
    def references(self):
        return [entry["reference"] for entry in self.closure]


def resolve_module(reference, registry_root) -> ResolvedModule:
    """Resolve exact transitive pins in dependency order; never execute imports."""
    reference_schema = read_json(SCHEMA_ROOT / "spl-module-descriptor.schema.json")
    _shape(reference, reference_schema["$defs"]["module_ref"], reference_schema)
    seen, active, identities, closure = {}, set(), {}, []

    def visit(ref):
        identity = (ref["id"], ref["revision"])
        # Identity-cycle detection precedes digest checks, allowing a meaningful
        # diagnostic even though cryptographic cyclic file pins are unsatisfiable.
        if identity in active:
            fail("MODULE_IMPORT_CYCLE", "Cyclic module identity " + repr(identity))
        if identity in identities and identities[identity] != ref:
            fail("MODULE_IDENTITY_CONFLICT", "One revision has conflicting content pins")
        identities[identity] = ref
        if identity in seen:
            return seen[identity]
        descriptor_path = _pinned_file(ref, registry_root)
        descriptor = read_json(descriptor_path)
        _validate_document(descriptor, "spl-module-descriptor.schema.json")
        if (descriptor["id"], descriptor["revision"]) != identity:
            fail("MODULE_IDENTITY_MISMATCH", "Descriptor identity differs from registration")
        codecs = set(descriptor["compatibility"]["codecs"])
        if not {"spl-exact/1", "spl-instant/1"} <= codecs or codecs - {"spl-exact/1", "spl-instant/1", "spl-quantity/1"}:
            fail("MODULE_CODEC_VERSION", "The registered interface requires both exact codecs")
        unsupported = set(descriptor["compatibility"]["capabilities"]) - CAPABILITIES
        if unsupported:
            fail("MODULE_UNSUPPORTED_CAPABILITY", repr(sorted(unsupported)))
        source = _pinned_file(descriptor["source"], registry_root)
        policy = _pinned_file(descriptor["policy"]["readable"], registry_root)
        if not policy.read_text(encoding="utf-8").strip():
            fail("MODULE_POLICY_REQUIRED", "Readable economic policy is empty")
        _unique(descriptor["interface"]["ports"], "name", "MODULE_DUPLICATE_PORT")
        _unique(descriptor["interface"]["schemas"], "name", "MODULE_DUPLICATE_SCHEMA")
        _unique(descriptor["interface"]["exports"], "name", "MODULE_DUPLICATE_EXPORT")
        _unique(descriptor["imports"], "alias", "MODULE_IMPORT_COLLISION")
        # Every registered signature is admitted before linking, including
        # unused structural schemas and exports in imported descriptors.
        for schema in descriptor["interface"]["schemas"]:
            _port_type({"type": {"name": schema["name"], "args": []}}, descriptor)
        for export in descriptor["interface"]["exports"]:
            _port_type({"type": export["result"]}, descriptor)
            for parameter in export["parameters"]:
                _port_type(parameter, descriptor)
        _check_capabilities(descriptor, _parse_source(source))
        if identity != (reference["id"], reference["revision"]):
            if descriptor["constraints"] or descriptor["state"] or any(port["domain"] for port in descriptor["interface"]["ports"]):
                fail("MODULE_FUNCTION_CONSTRAINT_UNSUPPORTED", "Imported function preconditions must be explicit checked source assertions")
            if any(port["role"] not in {"input", "parameter"} for port in descriptor["interface"]["ports"]):
                fail("MODULE_FUNCTION_INTERFACE", "Function modules expose typed arguments through input/parameter ports")
            from .checker import compatible
            ports = {port["name"]: port for port in descriptor["interface"]["ports"]}
            for export in descriptor["interface"]["exports"]:
                parameters = _unique(export["parameters"], "name", "MODULE_DUPLICATE_PARAMETER")
                if parameters.keys() != ports.keys() or any(not compatible(_port_type(parameter, descriptor), _port_type(ports[name], descriptor))
                                                            for name, parameter in parameters.items()):
                    fail("MODULE_FUNCTION_INTERFACE", "Export signature differs from declared argument ports")
        active.add(identity)
        local_names = set()
        for imported in descriptor["imports"]:
            dependency = visit(imported["module_ref"])
            for symbol in imported["symbols"]:
                if symbol["export"] not in {export["name"] for export in dependency["descriptor"]["interface"]["exports"]}:
                    fail("MODULE_EXPORT_MISSING", symbol["export"])
                if symbol["local"] in local_names:
                    fail("MODULE_IMPORT_COLLISION", symbol["local"])
                local_names.add(symbol["local"])
        active.remove(identity)
        entry = {"reference": deepcopy(ref), "descriptor": descriptor,
                 "descriptor_path": descriptor_path, "source_path": source, "policy_path": policy}
        closure.append(entry)
        seen[identity] = entry
        return entry

    entry = visit(reference)
    return ResolvedModule(deepcopy(reference), entry["descriptor"], entry["source_path"],
                          entry["policy_path"], closure, Path(registry_root).resolve())


def _path(value, path):
    if not path:
        return value
    head, _, rest = path.partition(".")
    if head == "*":
        if not isinstance(value, list):
            fail("MODULE_CONSTRAINT_PATH", "Wildcard requires a list: " + path)
        return [_path(item, rest) for item in value]
    if not isinstance(value, dict) or head not in value:
        fail("MODULE_CONSTRAINT_PATH", "Missing declared path: " + path)
    return _path(value[head], rest)


def _rows(value):
    return value if isinstance(value, list) else [value]


def _quantity(value):
    return amount(value) if isinstance(value, dict) and "currency" in value else exact(value)


def _measure(value):
    """Preserve new dimensions while retaining legacy Money/scalar bounds."""
    from .codecs import dimensional_amount
    if isinstance(value, dict) and "per_unit" in value:
        decoded = dimensional_amount(value, value["per_unit"], currency=value.get("currency", "USD"))
        return ("Rate", decoded.per_unit, decoded.currency), decoded.value
    if isinstance(value, dict) and "unit" in value:
        decoded = dimensional_amount(value, value["unit"])
        return ("Quantity", decoded.unit), decoded.value
    return None, _quantity(value)


def _type_path(typ, parts):
    for part in parts:
        if part == "*" and typ.name == "List":
            typ = typ.args[0]
        elif part in dict(typ.fields):
            typ = dict(typ.fields)[part]
        else:
            return None
    return typ


def _constraint_row_type(descriptor, path, field):
    """Retain declared collection dimensions even when no rows are supplied."""
    parts = path.split(".")
    if len(parts) < 2:
        return None
    for port in descriptor["interface"]["ports"]:
        group = INPUT_ROLES.get(port["role"], "outputs" if port["role"] in OUTPUT_ROLES else "")
        if parts[:2] == [group, port["name"]]:
            typ = _type_path(_port_type(port, descriptor), parts[2:])
            if typ is None:
                return None
            if typ.name == "List":
                typ = typ.args[0]
            return _type_path(typ, field.split("."))
    return None


def _measure_type_dimension(typ):
    if typ.name == "Quantity":
        return ("Quantity", typ.args[0].name)
    if typ.name == "Rate":
        return ("Rate", typ.args[0].name, typ.args[1].name)
    return None


def _constraints(package, descriptor, outputs=None):
    context = {**package, "dictionaries": descriptor["interface"]["dictionaries"]}
    if outputs is not None:
        context["outputs"] = outputs
    decisions = {d["decision_id"] for d in package["decisions"]}
    for constraint in descriptor["constraints"]:
        kind, path, fields = constraint["kind"], constraint["path"], constraint["fields"]
        if "required" in constraint and kind != "evidence":
            fail("MODULE_CONSTRAINT_DEFINITION", "Only evidence constraints can declare required")
        if path.startswith("outputs.") and outputs is None:
            continue
        if not path.startswith("outputs.") and outputs is not None:
            continue
        rows = _rows(_path(context, path))
        values = [[_path(row, field) for field in fields] if fields else row for row in rows]
        if kind == "unique":
            if len({canonical(value) for value in values}) != len(values):
                fail("MODULE_DUPLICATE_KEY", path)
        elif kind in {"references", "member_of"}:
            allowed = _rows(_path(context, constraint["target"]))
            keys = {canonical(value) for value in allowed}
            selected = [value[0] if fields and len(fields) == 1 else value for value in values]
            if any(canonical(value) not in keys for value in selected):
                fail("MODULE_REFERENCE_SCOPE", path)
        elif kind == "equals":
            expected = _path(context, constraint["target"]) if constraint["target"] else constraint["value"]
            selected = [value[0] if fields and len(fields) == 1 else value for value in values]
            if any(canonical(value) != canonical(expected) for value in selected):
                fail("MODULE_SCOPE_MISMATCH", path)
        elif kind == "conservation":
            if len(fields) != 1:
                fail("MODULE_CONSTRAINT_DEFINITION", "Conservation requires one exact quantity field")
            target_dimension, target = _measure(_path(context, constraint["target"]))
            row_type = _constraint_row_type(descriptor, path, fields[0])
            if row_type is not None and _measure_type_dimension(row_type) != target_dimension:
                fail("MODULE_CONSERVATION_DIMENSION", "Conserved values require the target's explicit dimension")
            total = Fraction()
            for value in values:
                dimension, measured = _measure(value[0])
                if dimension != target_dimension:
                    fail("MODULE_CONSERVATION_DIMENSION", "Conserved values require the target's explicit dimension")
                total += measured
            if total != target:
                fail("MODULE_CONSERVATION", path)
        elif kind == "evidence":
            if not rows and constraint.get("required", True):
                fail("MODULE_EVIDENCE_REQUIRED", path)
            for row in rows:
                if not isinstance(row, dict) or not {"observed_at", "approval_ref", "evidence_ref", "kind"} <= row.keys():
                    fail("MODULE_EVIDENCE_REQUIRED", path)
                if (row["approval_ref"] not in decisions or not row["evidence_ref"] or
                        row["kind"] != constraint["value"]):
                    fail("MODULE_EVIDENCE_AUTHORITY", path)
                if instant(row["observed_at"]) >= instant(package["manifest"]["cutoff"]):
                    fail("EVIDENCE_AFTER_CUTOFF", path)


def _domain(value, port):
    domain = port["domain"]
    if "choices" in domain and canonical(value) not in {canonical(x) for x in domain["choices"]}:
        fail("MODULE_PARAMETER_DOMAIN", port["name"])
    for key, compare in [("minimum", lambda a, b: a < b), ("maximum", lambda a, b: a > b)]:
        if key in domain:
            dimension, measured = _measure(value)
            bound_dimension, bound = _measure(domain[key])
            if dimension != bound_dimension:
                fail("MODULE_PARAMETER_DIMENSION", "Bounds require the port's explicit dimension: " + port["name"])
            if compare(measured, bound):
                fail("MODULE_PARAMETER_DOMAIN", port["name"])
    for key, compare in [("min_items", lambda a, b: a < b), ("max_items", lambda a, b: a > b)]:
        if key in domain and (not isinstance(value, list) or compare(len(value), domain[key])):
            fail("MODULE_CARDINALITY", port["name"])


def _type_ast(value, descriptor, active=()):
    """Expand descriptor-local structural names without global schema mutation."""
    schemas = {schema["name"]: schema["fields"] for schema in descriptor["interface"]["schemas"]}
    name = value["name"]
    if name in schemas:
        if name in active or value.get("args"):
            fail("MODULE_SCHEMA_CYCLE", name)
        return {"name": "Record", "args": [], "fields": [
            [field, _type_ast(typ, descriptor, (*active, name))] for field, typ in schemas[name].items()]}
    result = {"name": name, "args": [_type_ast(arg, descriptor, active) for arg in value.get("args", [])]}
    if "fields" in value:
        if name != "Record" or len({field for field, _ in value["fields"]}) != len(value["fields"]):
            fail("MODULE_SCHEMA_FIELDS", name)
        result["fields"] = [[field, _type_ast(typ, descriptor, active)] for field, typ in value["fields"]]
    return result


def _port_type(port, descriptor):
    from .checker import type_from_ast
    return type_from_ast(_type_ast(port["type"], descriptor))


def dimensioned_state_unit(typ):
    """Stable state unit for a fully expanded type, including nested dimensions.

    AST input first passes through the compiler's type admission, expanding
    built-in structural schemas exactly as checked Type input does. The signature
    retains checked names, sorts record fields and includes an explicit fields
    list at every node. Argument order is significant.
    Accept either a checked Type or an expanded type AST; descriptor-local names
    must first be expanded with the owning descriptor.
    """
    if isinstance(typ, dict):
        from .checker import type_from_ast
        typ = type_from_ast(typ)

    def normalized(value):
        return {"name": value.name, "args": [normalized(arg) for arg in value.args],
                "fields": [[name, normalized(child)] for name, child in sorted(value.fields)]}
    return "dimensioned:" + digest(normalized(typ))


def _scope_value(value, typ, package):
    """Enforce intrinsic typed scope namespaces at every nested boundary."""
    if typ.name == "Id":
        if not value.isascii():
            fail("UNSUPPORTED_IDENTIFIER_PROFILE", "Canonical native IDs use the ASCII profile")
        kind, scope = typ.args[0].name, package["scope"]
        allowed = {"Agreement": [scope["agreement_id"]], "Pool": [scope["pool_id"]],
                   "Participant": scope["participant_ids"], "Asset": scope["asset_ids"]}.get(kind)
        if allowed is not None and value not in allowed:
            fail("MODULE_REFERENCE_SCOPE", "Out-of-scope Id<" + kind + ">")
    elif typ.name in {"List", "Tuple"}:
        for index, item in enumerate(value):
            _scope_value(item, typ.args[0] if typ.name == "List" else typ.args[index], package)
    elif typ.name == "Map":
        for row in value:
            _scope_value(row["key"], typ.args[0], package)
            _scope_value(row["value"], typ.args[1], package)
    elif typ.name == "Option" and isinstance(value, dict) and "some" in value:
        _scope_value(value["some"], typ.args[0], package)
    elif typ.fields:
        for name, field_type in typ.fields:
            _scope_value(value[name], field_type, package)


def linking_manifest(resolved):
    """Pure, pinned source bytes and descriptors for the native/Python linkers."""
    def normalized(descriptor):
        result = deepcopy(descriptor)
        for export in result["interface"]["exports"]:
            export["result"] = _type_ast(export["result"], descriptor)
            for parameter in export["parameters"]:
                parameter["type"] = _type_ast(parameter["type"], descriptor)
        return result

    return {"modules": [{"reference": entry["reference"],
                          "source": entry["source_path"].read_text(encoding="utf-8"),
                          "descriptor": normalized(entry["descriptor"])}
                         for entry in resolved.closure if entry["reference"] != resolved.reference],
            "imports": resolved.descriptor["imports"]}


def _checked_source(resolved):
    from .checker import check_schedule, compatible, type_from_ast
    descriptor = resolved.descriptor
    for schema in descriptor["interface"]["schemas"]:
        type_from_ast(_type_ast({"name": schema["name"], "args": []}, descriptor))
    for port in descriptor["interface"]["ports"]:
        _port_type(port, descriptor)
    syntax = _parse_source(resolved.source_path)
    if descriptor["imports"]:
        try:
            from .linker import link_schedule
        except ImportError:
            fail("MODULE_SOURCE_LINK_REQUIRED", "Resolved imports require native first-order source linking")
        syntax = link_schedule(syntax, linking_manifest(resolved))
    checked = check_schedule(syntax)
    declared = {d["name"]: d for d in syntax["declarations"] if d["kind"] in {"input", "opening"}}
    expected = {p["name"]: p for p in descriptor["interface"]["ports"] if p["role"] in {*INPUT_ROLES, "opening"}}
    if declared.keys() != expected.keys():
        fail("MODULE_PORT_MISMATCH", "Source input/opening ports differ from the registered interface")
    for name, port in expected.items():
        kind = "opening" if port["role"] == "opening" else "input"
        if declared[name]["kind"] != kind or not compatible(type_from_ast(declared[name]["type"]), _port_type(port, descriptor)):
            fail("MODULE_PORT_MISMATCH", name)
    names = {d["name"] for d in syntax["declarations"] if d["kind"] == "define"}
    if not {export["definition"] for export in descriptor["interface"]["exports"]} <= names:
        fail("MODULE_EXPORT_MISSING", "Registered export is absent from source definitions")
    return checked


def validate_module_package(package, resolved):
    """Validate declarative facts, authority and scoped openings before execution."""
    from .evaluator import decode_value
    _resource_guard(package)
    _validate_document(package, "spl-module-package.schema.json")
    if package["module_ref"] != resolved.reference:
        fail("MODULE_IDENTITY_MISMATCH", "Run registration differs from resolved module")
    descriptor = resolved.descriptor
    period(package["manifest"]["period"])
    instant(package["manifest"]["cutoff"], "/manifest/cutoff")
    decisions = _unique(package["decisions"], "decision_id", "MODULE_DUPLICATE_DECISION")
    required = {}
    for entry in resolved.closure:
        policy = entry["descriptor"]["policy"]
        for decision_id in policy["decision_ids"]:
            if decision_id in required and required[decision_id] != policy:
                fail("MODULE_POLICY_COLLISION", decision_id)
            required[decision_id] = policy
    if decisions.keys() != required.keys():
        fail("MODULE_POLICY_REQUIRED", "Run decisions must exactly cover the registered policy")
    for decision in decisions.values():
        policy = required[decision["decision_id"]]
        if (decision["policy_id"] != policy["id"] or
                decision["policy_revision"] != policy["revision"] or
                decision["status"] != policy["review_status"]):
            fail("MODULE_POLICY_MISMATCH", decision["decision_id"])
    checked = _checked_source(resolved)
    from .run import _citations
    if not _citations(checked.schedule) <= required.keys():
        fail("MODULE_POLICY_REQUIRED", "An executable source citation is outside the registered policy closure")
    ports = descriptor["interface"]["ports"]
    inputs = {}
    for role, group in INPUT_ROLES.items():
        declared = {port["name"]: port for port in ports if port["role"] == role}
        if package[group].keys() != declared.keys():
            fail("MODULE_BINDING_PORTS", "Undeclared or missing " + group)
        for name, port in declared.items():
            value = package[group][name]
            value_type = _port_type(port, descriptor)
            decode_value(value, value_type, group + "." + name)
            _scope_value(value, value_type, package)
            _domain(value, port)
            if role == "evidence" and not any(c["kind"] == "evidence" and c["path"] == "evidence." + name
                                              for c in descriptor["constraints"]):
                fail("MODULE_EVIDENCE_POLICY", "Evidence ports require an explicit observation and authority constraint")
            inputs[name] = value
    slots = _unique(descriptor["state"], "opening", "MODULE_DUPLICATE_STATE_WRITER")
    _unique(descriptor["state"], "closing", "MODULE_DUPLICATE_STATE_WRITER")
    cells = _unique(package["state_cells"], "opening_port", "MODULE_DUPLICATE_STATE_WRITER")
    _unique(package["state_cells"], "state_key", "MODULE_DUPLICATE_STATE_WRITER")
    opening_ports = {p["name"]: p for p in ports if p["role"] == "opening"}
    if cells.keys() != slots.keys() or slots.keys() != opening_ports.keys():
        fail("MODULE_STATE_PORTS", "Every opening port requires one explicit state slot and cell")
    openings = {}
    for name, slot in slots.items():
        cell, scope = cells[name], package["scope"]
        from .dimensions import contains_dimension
        state_type = _port_type(opening_ports[name], descriptor)
        dimensional = contains_dimension(state_type)
        if dimensional:
            expected_unit = dimensioned_state_unit(state_type)
            if slot["unit"] != expected_unit or cell["unit"] != expected_unit or cell["scope"].get("unit") != expected_unit:
                fail("MODULE_STATE_TYPE", "Dimensional state must retain its complete type in slot, cell and scope units")
            if "unit" not in slot["key_fields"]:
                fail("MODULE_STATE_KEY", "Dimensional state keys require unit")
        if cell["purpose"] != slot["purpose"] or cell["unit"] != slot["unit"]:
            fail("MODULE_STATE_PURPOSE", name)
        if (cell["scope"]["agreement_id"] != scope["agreement_id"] or cell["scope"]["pool_id"] != scope["pool_id"] or
                cell["scope"]["participant_id"] not in scope["participant_ids"] or
                ("asset_id" in cell["scope"] and cell["scope"]["asset_id"] not in scope["asset_ids"]) or
                cell["scenario_id"] != package["manifest"]["scenario_id"]):
            fail("MODULE_STATE_SCOPE", name)
        day(cell["boundary"])
        if cell["boundary"] != package["manifest"]["period"]["start"]:
            fail("MODULE_STATE_BOUNDARY", name)
        if slot["history_required"] and "prior_result_ref" not in cell:
            fail("MODULE_STATE_LINEAGE", name)
        key_record = {**cell["scope"], "purpose": cell["purpose"]}
        if not {"agreement_id", "participant_id", "pool_id", "purpose"} <= set(slot["key_fields"]):
            fail("MODULE_STATE_KEY", "State keys require agreement, participant, pool and purpose")
        if any((field in cell["scope"]) != (field in slot["key_fields"]) for field in ["asset_id", "vintage_id"]):
            fail("MODULE_STATE_KEY", "An asset/vintage state dimension must be retained in its key")
        if any(field not in key_record for field in slot["key_fields"]):
            fail("MODULE_STATE_KEY", "Missing key dimension for " + name)
        expected_key = canonical({field: key_record[field] for field in slot["key_fields"]})
        if cell["state_key"] != expected_key:
            fail("MODULE_STATE_KEY", name)
        is_money = state_type.name == "Money"
        if slot["movement_kinds"] != (["net_change"] if is_money else ["transition"]):
            fail("MODULE_STATE_MOVEMENT_UNSUPPORTED", "Declare net_change for money or transition for structured state")
        if is_money and slot["unit"] != state_type.args[0].name:
            fail("MODULE_STATE_TYPE", "State currency differs from its opening port")
        if not is_money and not dimensional and slot["unit"] != "structured":
            fail("MODULE_STATE_TYPE", "Non-money state must declare the structured unit")
        openings[name] = money(exact(cell["quantity"])) if is_money else cell["quantity"]
        decode_value(openings[name], state_type, "state." + name)
        _scope_value(openings[name], state_type, package)
    _constraints(package, descriptor)
    return checked, inputs, openings


def bind_module_package(package, registry_root):
    result = deepcopy(package)
    resolved = resolve_module(result["module_ref"], registry_root)
    compiler, runtime = module_identities()
    result["manifest"].update(compiler_build=compiler, runtime_build=runtime,
                              module_closure=deepcopy(resolved.references))
    return result


def module_identities():
    """Include machine-readable boundary schemas in this profile's build pin."""
    from .run import identities
    compiler, runtime = identities()
    schemas = {name: file_digest(SCHEMA_ROOT / name) for name in
               ["spl-module-descriptor.schema.json", "spl-module-package.schema.json"]}
    return digest({"compiler": compiler, "module_schemas": schemas}), runtime


def _module_policy_review(package, resolved):
    """Audit navigation from supplied terms and application labels to pinned text."""
    from .readable import is_readable, readable_policy_dependencies
    review = deepcopy(resolved.descriptor["policy"])
    review.update(format="spl-module-policy-review/1", actual_parameters=deepcopy(package["parameters"]),
                  parameters=[], modules=[], function_sources={},
                  limitation="Pins and source locations support review; they do not establish semantic equivalence or economic approval")
    for entry in resolved.closure:
        descriptor = entry["descriptor"]
        source = entry["source_path"].read_text(encoding="utf-8")
        syntax = _parse_source(entry["source_path"])
        declarations = {declaration["name"]: declaration for declaration in syntax["declarations"]
                        if declaration["kind"] in {"input", "opening", "define"}}

        def location(name):
            declaration = declarations[name]
            span = deepcopy(declaration["span"])
            return {"source": deepcopy(descriptor["source"]), "span": span,
                    "text": source[span["start"]:span["end"]]}

        module = {"module_ref": deepcopy(entry["reference"]), "source": deepcopy(descriptor["source"]),
                  "policy": deepcopy(descriptor["policy"]), "exports": [],
                  "declarations": [{"name": declaration.get("name", ""), "kind": declaration["kind"],
                                    "span": deepcopy(declaration["span"])} for declaration in syntax["declarations"]],
                  "readable_support": {}}
        if is_readable(source):
            module["readable_support"] = readable_policy_dependencies(source, entry["source_path"].name)
        for export in descriptor["interface"]["exports"]:
            label = descriptor["id"] + "@" + descriptor["revision"] + ":" + export["name"]
            exported = {**deepcopy(export), "function": label, "definition_location": location(export["definition"]),
                        "parameter_locations": {parameter["name"]: location(parameter["name"]) for parameter in export["parameters"]}}
            module["exports"].append(exported)
            review["function_sources"][label] = {"module_ref": deepcopy(entry["reference"]), "export": export["name"],
                                                 "definition": export["definition"], **location(export["definition"])}
        review["modules"].append(module)
        if entry["reference"] == resolved.reference:
            for port in descriptor["interface"]["ports"]:
                if port["role"] == "parameter":
                    review["parameters"].append({"name": port["name"], "value": deepcopy(package["parameters"][port["name"]]),
                        "type": deepcopy(port["type"]), "domain": deepcopy(port["domain"]),
                        "methodology": bool(port["domain"].get("methodology")), "declaration_location": location(port["name"])})
    return review


def _input_transport(value, typ):
    """Convert emitted values to typed input transport for successor state."""
    if typ.name == "Money":
        return value if isinstance(value, dict) and "currency" in value else money(exact(value), typ.args[0].name)
    if typ.name == "List":
        if not isinstance(value, list):
            fail("MODULE_OUTPUT_TYPE", "Expected a result list")
        return [_input_transport(item, typ.args[0]) for item in value]
    if typ.name == "Tuple":
        if not isinstance(value, list) or len(value) != len(typ.args):
            fail("MODULE_OUTPUT_TYPE", "Expected a result tuple of the declared arity")
        return [_input_transport(item, item_type) for item, item_type in zip(value, typ.args)]
    if typ.name == "Map":
        if not isinstance(value, list) or any(not isinstance(row, dict) or set(row) != {"key", "value"} for row in value):
            fail("MODULE_OUTPUT_TYPE", "Expected map entries")
        return [{"key": _input_transport(row["key"], typ.args[0]), "value": _input_transport(row["value"], typ.args[1])} for row in value]
    if typ.name == "Option" and isinstance(value, dict) and set(value) == {"some"}:
        return {"some": _input_transport(value["some"], typ.args[0])}
    if typ.fields:
        if not isinstance(value, dict) or value.keys() != dict(typ.fields).keys():
            fail("MODULE_OUTPUT_TYPE", "Result fields differ from the registered interface")
        return {name: _input_transport(value[name], field_type) for name, field_type in typ.fields}
    return value


def _decode_output(value, typ):
    from .evaluator import decode_value
    return decode_value(_input_transport(value, typ), typ, "result")


def run_module_package(package, registry_root, *, backend="compare", artifact_dir=None, blocked_evidence_labels=None):
    """Execute one registered connected scope with strict atomic finalization."""
    from .evaluator import evaluate
    from .lean_tools import compile_schedule, export_ir, interpret_schedule, lean
    from .run import normalize_target
    from .artifacts import ArtifactPublication
    unknown_fields = {"payment_evidence_status", "funding_evidence_status", "recovery_evidence_status"}
    if blocked_evidence_labels is not None and (type(blocked_evidence_labels) is not dict or
            any(type(code) is not str or type(labels) is not dict or not labels or
                any(field not in unknown_fields or type(label) is not str or label not in {"not_assessed", "no_event_supplied"}
                    for field, label in labels.items()) for code, labels in blocked_evidence_labels.items())):
        raise ValueError("INVALID_BLOCKED_EVIDENCE_LABELS")
    p = deepcopy(package)
    result = {"status": "blocked", "results": {}, "statements": [], "detail": [], "closing_state": [], "trace": [],
              "diagnostics": [], "reconciliation": {}, "policy_review": {}, "manifest": p.get("manifest", {}) if isinstance(p, dict) else {},
              "issuance_status": "unissued", "payment_evidence_status": "not_assessed"}
    publication = ArtifactPublication(artifact_dir) if artifact_dir else None

    def publish():
        if result["status"] == "blocked" and blocked_evidence_labels:
            selected = {}
            for diagnostic in result["diagnostics"]:
                for field, label in blocked_evidence_labels.get(diagnostic["code"], {}).items():
                    if field in selected and selected[field] != label:
                        raise ValueError("AMBIGUOUS_BLOCKED_EVIDENCE_LABELS")
                    selected[field] = label
            if selected:
                if result.get("result_digest") or result["results"] or result["closing_state"]:
                    raise ValueError("BLOCKED_RESULT_FINALIZED")
                result.update(selected)
        if publication:
            return publication.finish(result, {"results.json": "results", "statement.json": "statements",
                "detail.json": "detail", "trace.json": "trace", "closing-state.json": "closing_state",
                "reconciliation.json": "reconciliation", "diagnostics.json": "diagnostics", "policy-review.json": "policy_review"})
        return result

    try:
        if backend not in {"compare", "reference", "lean"}:
            fail("UNSUPPORTED_BACKEND", backend)
        result["input_statistics"] = _resource_guard(p)
        _validate_document(p, "spl-module-package.schema.json")
        resolved = resolve_module(p["module_ref"], registry_root)
        checked, inputs, openings = validate_module_package(p, resolved)
        compiler, runtime = module_identities()
        if (p["manifest"]["compiler_build"] != compiler or p["manifest"]["runtime_build"] != runtime or
                p["manifest"]["module_closure"] != resolved.references):
            fail("MANIFEST_DIGEST_MISMATCH", "Module closure or implementation has changed")
        logical_package = deepcopy(p)
        logical_package["manifest"].pop("run_id")
        semantic = digest({"package": logical_package, "closure": resolved.references})
        result["policy_review"] = _module_policy_review(p, resolved)
        work = publication.work if publication else Path(registry_root) / ".lake/module-runs" / semantic
        work.mkdir(parents=True, exist_ok=True)
        write_json(work / "canonical-package.json", p)
        write_json(work / "bindings.json", {"inputs": inputs, "openings": openings})
        write_json(work / "policy-review.json", result["policy_review"])
        link = None
        if resolved.descriptor["imports"]:
            link = work / "linking-manifest.json"
            write_json(link, linking_manifest(resolved))
        for entry in resolved.closure:
            for field, path in [("descriptor", entry["descriptor_path"]), ("source", entry["source_path"]), ("policy", entry["policy_path"])]:
                destination = work / "closure" / (entry["reference"]["sha256"] + "-" + field + path.suffix)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(path.read_bytes())
        observed = evaluate(checked, inputs, openings).to_dict()
        origin = "independent_reference_evaluator"
        if backend in {"compare", "lean"}:
            link_options = {"link": link} if link else {}
            export_ir(resolved.source_path, work / "typed-ir.json", **link_options)
            interpreted = normalize_target(interpret_schedule(resolved.source_path, work / "bindings.json", **link_options))
            if (interpreted["status"] == "blocked" and interpreted.get("diagnostics") and
                    interpreted["diagnostics"][0]["code"] == "RESOURCE_LIMIT"):
                result.update(trace=interpreted.get("trace", []), diagnostics=interpreted["diagnostics"],
                              trace_origin=interpreted.get("trace_origin", "native_ir_interpreter"),
                              trace_format=interpreted.get("trace_format", "spl-trace-dag/0.1"),
                              verification={"backend": backend, "required_audit_completed": False})
                return publish()
            target = compile_schedule(resolved.source_path, work / "Settlement.lean", **link_options)
            generated = normalize_target(read_native(lean(["--run", target, work / "bindings.json"])))
            for candidate in [observed, interpreted]:
                for field in ["status", "emissions", "closing"]:
                    if canonical(generated[field]) != canonical(candidate[field]):
                        fail("MODULE_DIFFERENTIAL_MISMATCH", field)
                if [d["code"] for d in generated["diagnostics"]] != [d["code"] for d in candidate["diagnostics"]]:
                    fail("MODULE_DIFFERENTIAL_MISMATCH", "diagnostics")
            observed = {**generated, "trace": interpreted["trace"]}
            origin = interpreted["trace_origin"]
        result["trace"] = observed["trace"]
        result["trace_origin"] = origin
        if observed["status"] == "blocked":
            result["diagnostics"] = observed["diagnostics"]
            return publish()
        output_ports = {port["name"]: port for port in resolved.descriptor["interface"]["ports"] if port["role"] in OUTPUT_ROLES}
        if not output_ports or not any(port["role"] == "result" for port in output_ports.values()):
            fail("MODULE_OUTPUT_REQUIRED", "A result port is required")
        if observed["emissions"].keys() != output_ports.keys():
            fail("MODULE_OUTPUT_PORTS", "Emitted output differs from registered result/detail/reconciliation ports")
        for name, port in output_ports.items():
            value_type = _port_type(port, resolved.descriptor)
            _decode_output(observed["emissions"][name], value_type)
            _scope_value(observed["emissions"][name], value_type, p)
            if port["role"] == "reconciliation" and port["type"]["name"] == "Bool" and not observed["emissions"][name]:
                fail("MODULE_RECONCILIATION_FAILED", name)
        _constraints(p, resolved.descriptor, observed["emissions"])
        slots = resolved.descriptor["state"]
        if observed["closing"].keys() != {slot["closing"] for slot in slots}:
            fail("MODULE_CLOSING_PORTS", "Missing or undeclared state writer")
        cells = {cell["opening_port"]: cell for cell in p["state_cells"]}
        closing = []
        opening_ports = {port["name"]: port for port in resolved.descriptor["interface"]["ports"] if port["role"] == "opening"}
        for slot in slots:
            cell = deepcopy(cells[slot["opening"]])
            state_type = _port_type(opening_ports[slot["opening"]], resolved.descriptor)
            emitted = observed["closing"][slot["closing"]]
            _decode_output(emitted, state_type)
            _scope_value(emitted, state_type, p)
            if state_type.name == "Money":
                initial, final = exact(cell["quantity"]), exact(emitted)
                quantity = number(final)
                movement = {"kind": "net_change", "opening": number(initial), "net_change": number(final - initial), "closing": quantity}
            else:
                quantity = _input_transport(emitted, state_type)
                movement = {"kind": "transition", "opening": cell["quantity"], "closing": quantity}
            cell.update(boundary=p["manifest"]["period"]["end"], quantity=quantity,
                        prior_result_ref="result@sha256:" + semantic, movement=movement)
            closing.append(cell)
        # Recheck every file pin after execution, before exposing consumable state.
        if resolve_module(p["module_ref"], registry_root).references != resolved.references or module_identities() != (compiler, runtime):
            fail("MODULE_DEPENDENCY_CHANGED", "Dependency changed during execution")
        grouped = {role: [observed["emissions"][name] for name, port in output_ports.items() if port["role"] == role]
                   for role in OUTPUT_ROLES}
        def flatten(values):
            return [item for value in values for item in (value if isinstance(value, list) else [value])]
        result.update(status="provisional" if p["manifest"]["mode"] == "preview" else "calculated",
                      results=deepcopy(observed["emissions"]),
                      statements=flatten(grouped["result"]), detail=flatten(grouped["detail"]),
                      reconciliation={"ports": {name: observed["emissions"][name] for name, port in output_ports.items() if port["role"] == "reconciliation"},
                                      "state": [cell["movement"] for cell in closing]},
                      closing_state=closing if p["manifest"]["mode"] == "final" else [],
                      module_closure=deepcopy(resolved.references), semantic_run_digest=semantic,
                      terms_digest=digest(p["parameters"]), method_digest=digest({"module": p["module_ref"],
                          "method_parameters": {port["name"]: p["parameters"][port["name"]]
                              for port in resolved.descriptor["interface"]["ports"]
                              if port["role"] == "parameter" and port["domain"].get("methodology")}}),
                      verification={"backend": backend, "reference_agrees": backend in {"compare", "lean"},
                                    "proof_scope": "No descriptor, policy, parser or orchestration correctness proof"})
        result["result_digest"] = digest({key: value for key, value in result.items() if key != "result_digest"})
        return publish()
    except DataError as error:
        result["diagnostics"] = [error.diagnostic()]
    except SPLException as error:
        result["diagnostics"] = [diagnostic.to_dict() for diagnostic in error.diagnostics]
    except OSError as error:
        result["diagnostics"] = [{"code": "IO_ERROR", "message": str(error)}]
    result.update(status="blocked", results={}, statements=[], detail=[], closing_state=[], reconciliation={})
    result.pop("result_digest", None)
    return publish()


def read_native(text):
    from .codecs import loads
    return loads(text)
