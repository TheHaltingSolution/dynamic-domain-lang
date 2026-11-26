"""Version/admission shape preflight, not execution of serialized JSON IR.

The native typed-Program validator additionally re-infers expressions. This
gate prevents artifact consumers from silently dropping extension metadata.
"""
from .codecs import fail, DataError
from .dimensions import (admission, meanings, UNIT_DEFINITIONS, CONVERSION_RELATIONS,
                         selected_features, validate_unit)
from .model import SPLException


def validate_ir_artifact(value):
    try:
        return _validate_ir_artifact(value)
    except DataError:
        raise
    except (TypeError, KeyError, AttributeError, ValueError):
        fail("INVALID_IR", "Malformed artifact metadata")


def _validate_ir_artifact(value):
    def reject(message):
        fail("INVALID_IR", message)

    keys = {"format", "name", "language", "core", "schema", "span", "declarations"}
    if not isinstance(value, dict) or value.get("format") not in {"spl-ir/0.1", "spl-ir/0.2"}:
        reject("Unknown artifact version")
    extended = value["format"] == "spl-ir/0.2"
    if set(value) != keys | ({"dimension_admission"} if extended else set()):
        reject("Unexpected artifact metadata")
    context = meanings()
    if extended:
        snapshot = value["dimension_admission"]
        if not isinstance(snapshot, dict) or set(snapshot) != {"features", "owners", "unit_definitions", "relations", "signatures"}:
            reject("Invalid admission snapshot")
        try:
            if not isinstance(snapshot["features"], list) or not isinstance(snapshot["owners"], list):
                reject("Invalid feature/owner declarations")
            root = admission(snapshot["features"])
            owners = []
            labels = set()
            for owner in snapshot["owners"]:
                if (not isinstance(owner, dict) or set(owner) != {"label", "features"}
                        or not isinstance(owner["label"], str) or not owner["label"]
                        or owner["label"] in labels or not isinstance(owner["features"], list)):
                    reject("Invalid application owner")
                labels.add(owner["label"])
                owners.append(admission(owner["features"]))
            context = meanings([root, *owners])
        except SPLException as error:
            reject(error.code)
        if not context.features:
            reject("V2 lacks extension closure")
        unit_ids = {identifier for row in selected_features(context) for identifier in row.units}
        from .dimensions import UNITS
        expected_units = [{"id": row.identifier, "sha256": row.pin} for row in UNIT_DEFINITIONS
                          if row.name in UNITS or row.identifier in unit_ids]
        relation_ids = {identifier for row in selected_features(context) for identifier in row.relations}
        expected_relations = [{"id": row.identifier, "sha256": row.pin} for row in CONVERSION_RELATIONS
                              if row.identifier in relation_ids]
        if snapshot["unit_definitions"] != expected_units or snapshot["relations"] != expected_relations:
            reject("Catalog definitions/pins differ")
        signatures = {}
        if not isinstance(snapshot["signatures"], list):
            reject("Invalid linked signature table")
        for signature in snapshot["signatures"]:
            if (not isinstance(signature, dict) or set(signature) != {"label", "parameters", "result"}
                    or signature["label"] in signatures or signature["label"] not in labels):
                reject("Invalid linked signature")
            owner = next(entry for entry in snapshot["owners"] if entry["label"] == signature["label"])
            own_context = meanings([admission(owner["features"])])
            if not isinstance(signature["parameters"], list) or any(
                    not isinstance(parameter, dict) or set(parameter) != {"name", "type"}
                    or not isinstance(parameter["name"], str) for parameter in signature["parameters"]):
                reject("Invalid linked parameters")
            if len({parameter["name"] for parameter in signature["parameters"]}) != len(signature["parameters"]):
                reject("Duplicate linked parameter")
            signatures[signature["label"]] = signature
            # Type dictionaries are validated at their owner, never root union.
            def signature_units(typ):
                if isinstance(typ, list):
                    for child in typ:
                        signature_units(child)
                elif isinstance(typ, dict):
                    if typ.get("kind") in {"quantity", "rate"}:
                        try:
                            validate_unit(typ.get("unit"), own_context)
                        except SPLException:
                            reject("Signature unit lacks owner admission")
                    for child in typ.values():
                        signature_units(child)
            signature_units(signature)
    else:
        signatures = {}

    def walk(node):
        if isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, dict):
            if "meta" in node:
                meta = node["meta"]
                allowed = {"id", "span", "type", "citation"} | ({"source_annotation"} if extended else set())
                if not isinstance(meta, dict) or not set(meta) <= allowed or not {"id", "span", "type"} <= set(meta):
                    reject("Unexpected expression metadata")
                if node.get("kind") == "apply" and set(node) != {
                        "kind", "meta", "function", "parameters", "arguments", "declarations", "body"}:
                    reject("Unexpected application metadata")
                if extended and node.get("kind") == "apply":
                    signature = signatures.get(node["function"])
                    if (signature is None or node["parameters"] != signature["parameters"]
                            or node["meta"]["type"] != signature["result"]):
                        reject("Application differs from linked signature")
            if node.get("kind") in {"quantity", "rate"}:
                try:
                    validate_unit(node.get("unit"), context)
                except SPLException as error:
                    reject(error.code)
                if node["kind"] == "rate" and node.get("currency") != "USD":
                    reject("Unsupported rate currency")
            for child in node.values():
                walk(child)
    walk(value["declarations"])
    return {"status": "shape_checked", "stage": "ir_artifact_preflight", "execution": "not_executed"}
