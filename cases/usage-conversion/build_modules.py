"""Author pinned unit interfaces; transport original measurements, never answers."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re

from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, file_digest, number, read_json, write_json
from spl_compiler.dimensions import FEATURE_CATALOG, USAGE_FEATURE, USAGE_RELATION
from spl_compiler.linker import link_schedule
from spl_compiler.modules import bind_module_package, dimensioned_state_unit, linking_manifest, resolve_module
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
HEADER = 'schedule Usage language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft"'
EXTENDED = HEADER + ' uses "spl.usage-time/1"'
RELATION = '"spl.usage-time/1:minute-hour"'


def original_number(value):
    if type(value) is not str or not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|[0-9]+/[1-9][0-9]*)", value):
        raise ValueError("USAGE_EXACT_ORIGINAL_NUMBER")
    return Fraction(value)


def record(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise ValueError("USAGE_ORIGINAL_RECORD_FIELDS")


SOURCES = {
    "base-minute-meter": HEADER + ''' {
  input original: Quantity<UsageMinute>;
  input price: Rate<UsageMinute,USD>;
  opening meter: Quantity<UsageMinute> from "usage-meter";
  emit "quantity" = original;
  emit "earned" = original * price;
  closing meter = meter + original;
}
''',
    "base-download-meter": HEADER + ''' {
  input original: Quantity<Download>;
  input price: Rate<Download,USD>;
  opening meter: Quantity<Download> from "usage-meter";
  emit "quantity" = original;
  emit "earned" = original * price;
  closing meter = meter + original;
}
''',
    "minute-meter": EXTENDED + ''' {
  input original: Quantity<UsageMinute>;
  input price: Rate<UsageHour,USD>;
  opening meter: Quantity<UsageMinute> from "usage-meter";
  define converted = convert_quantity(original, "UsageHour", ''' + RELATION + ''');
  emit "quantity" = converted;
  emit "earned" = converted * price;
  closing meter = meter + original;
}
''',
    "hour-meter": EXTENDED + ''' {
  input original: Quantity<UsageMinute>;
  input price: Rate<UsageHour,USD>;
  opening meter: Quantity<UsageHour> from "usage-meter";
  define converted = convert_quantity(original, "UsageHour", ''' + RELATION + ''');
  emit "quantity" = converted;
  emit "earned" = converted * price;
  closing meter = meter + converted;
}
''',
    "convert-library": EXTENDED + ''' {
  input original: Quantity<UsageMinute>;
  define converted = convert_quantity(original, "UsageHour", ''' + RELATION + ''');
}
''',
    "usd-library": EXTENDED + ''' {
  input original: Money<USD>;
  define unchanged = original * 1.0;
}
''',
    "inferred-import": HEADER + ''' {
  input original: Quantity<UsageMinute>;
  define h = to_hour(original);
  emit "quantity" = h + h;
}
''',
    "unused-extended": HEADER + ''' {
  emit "earned" = USD 1;
}
''',
    "base-library": HEADER + ''' {
  input original: Ratio;
  define unchanged = original * 0.5;
}
''',
    "base-custom-import": HEADER + ''' {
  input original: Ratio;
  emit "earned" = convert_quantity(original);
}
''',
    "extended-base-import": EXTENDED + ''' {
  input original: Ratio;
  emit "earned" = legacy_convert(original);
}
''',
}


def ast_type(typ):
    result = {"name": typ.name, "args": [ast_type(arg) for arg in typ.args]}
    if typ.fields:
        result = {"name": "Record", "args": [], "fields": [[name, ast_type(child)] for name, child in typ.fields]}
    return result


def pin(path, root=ROOT):
    return {"locator": path.resolve().relative_to(Path(root).resolve()).as_posix(), "sha256": file_digest(path)}


def register(name, root=ROOT, *, imports=(), exports=()):
    root = Path(root)
    folder = root / "cases/usage-conversion"
    folder.mkdir(parents=True, exist_ok=True)
    source = folder / (name + ".spl")
    source.write_bytes(SOURCES[name].encode("utf-8"))
    policy = folder / "policy.md"
    if not policy.exists():
        policy.write_bytes((FOLDER / "policy.md").read_bytes())
    syntax = parse(source.read_text(encoding="utf-8"), source.name)
    own_features = tuple(syntax.get("features", ()))
    entries, seen = [], set()
    for spec in imports:
        for entry in resolve_module(spec["module_ref"], root).closure:
            if entry["reference"]["sha256"] not in seen:
                entries.append(entry); seen.add(entry["reference"]["sha256"])
    if imports:
        # Canonical alias normalization is preserved for descriptor signatures.
        from spl_compiler.modules import ResolvedModule
        temporary = ResolvedModule({}, {"imports": list(imports)}, source, policy, entries, root)
        syntax = link_schedule(syntax, linking_manifest(temporary))
    checked = check_schedule(syntax)
    context = checked.meanings
    ports, state, units = [], [], set()
    from spl_compiler.dimensions import used_unit_definitions
    for node in syntax["declarations"]:
        if node["kind"] in {"input", "opening"}:
            typ = checked.types[node["name"]]
            ports.append({"name": node["name"], "role": node["kind"], "type": node["type"], "dimensions": [], "domain": {}})
            if node["kind"] == "opening":
                state.append({"opening": node["name"], "closing": node["name"], "purpose": "synthetic-usage-meter",
                              "unit": dimensioned_state_unit(typ, context),
                              "key_fields": ["agreement_id", "participant_id", "pool_id", "asset_id", "purpose", "unit"],
                              "movement_kinds": ["transition"], "history_required": False})
        elif node["kind"] == "emit":
            typ = node["expr"]["_type"]
            ports.append({"name": node["name"], "role": "result", "type": ast_type(typ), "dimensions": [], "domain": {}})
        else:
            continue
        units.update(unit.name for unit in used_unit_definitions(typ, context))
    for exported in exports:
        units.update(unit.name for unit in used_unit_definitions(checked.types[exported["definition"]], context))
    dictionaries = {}
    from spl_compiler.dimensions import UNITS, UNIT_DICTIONARY, UNIT_DEFINITIONS
    if units & UNITS:
        dictionaries[UNIT_DICTIONARY] = sorted(units & UNITS)
    for feature in FEATURE_CATALOG:
        names = {unit.name for unit in UNIT_DEFINITIONS if unit.identifier in feature.units}
        if units & names:
            dictionaries[feature.unit_dictionary] = sorted(units & names)
        if feature.identifier in own_features and "convert_quantity(" in SOURCES[name]:
            dictionaries[feature.relation_dictionary] = list(feature.relations)
    capabilities = ["spl.core/1", "spl.modules/1"]
    if units:
        capabilities.append("spl.quantities/1")
    capabilities.extend(context.features)
    descriptor = {"schema_version": "spl-module-descriptor/1", "id": "synthetic:usage-" + name, "revision": "1",
        "compatibility": {"surface": "spl/0.1-draft", "core": "spl-core/0.1-draft", "ir": "spl-ir/0.2" if context.features else "spl-ir/0.1",
                          "package": "spl-module/1", "toolchain": "leanprover/lean4:v4.35.0",
                          "codecs": ["spl-exact/1", "spl-instant/1", "spl-quantity/1"], "capabilities": capabilities},
        "source": pin(source, root), "imports": list(imports),
        "interface": {"ports": ports, "schemas": [], "dictionaries": dictionaries, "exports": list(exports)},
        "policy": {"id": "synthetic:usage-conversion", "revision": "1", "readable": pin(policy, root),
                   "decision_ids": ["USAGE_CONVERSION_SELECTED"], "evidence_class": "synthetic", "review_status": "proposed",
                   "discriminating_cases": ["ninety-original-usage-minutes", "legacy-base-carry", "new-hour-carry"]},
        "constraints": [], "state": state}
    path = folder / (name + "-module.json")
    write_json(path, descriptor)
    return {"id": descriptor["id"], "revision": descriptor["revision"], **pin(path, root)}


def register_all(root=ROOT):
    qminute = {"name": "Quantity", "args": [{"name": "UsageMinute", "args": []}]}
    qhour = {"name": "Quantity", "args": [{"name": "UsageHour", "args": []}]}
    usd = {"name": "Money", "args": [{"name": "USD", "args": []}]}
    ratio = {"name": "Ratio", "args": []}
    refs = {name: register(name, root) for name in ("base-minute-meter", "base-download-meter", "minute-meter", "hour-meter")}
    for name, exported, arg, result, definition in [("convert-library", "to_hour", qminute, qhour, "converted"),
            ("usd-library", "identity", usd, usd, "unchanged"), ("base-library", "convert_quantity", ratio, ratio, "unchanged")]:
        refs[name] = register(name, root, exports=[{"name": exported, "parameters": [{"name": "original", "type": arg}], "result": result, "definition": definition}])
    for name, dependency, symbol, local in [("inferred-import", "convert-library", "to_hour", "to_hour"),
            ("unused-extended", "usd-library", None, None), ("base-custom-import", "base-library", "convert_quantity", "convert_quantity"),
            ("extended-base-import", "base-library", "convert_quantity", "legacy_convert")]:
        refs[name] = register(name, root, imports=[{"module_ref": refs[dependency], "alias": "library",
                        "symbols": [] if symbol is None else [{"export": symbol, "local": local}]}])
    return refs


def usage_package(name="minute-meter", neutral=None, *, root=ROOT, reference=None, opening=None, bind=True):
    root = Path(root)
    data = deepcopy(read_json(FOLDER / "neutral.json") if neutral is None else neutral)
    record(data, {"schema_version", "case_id", "feature", "relation_id", "source_quantity", "target_unit", "price"})
    if data["schema_version"] != "spl-usage-conversion-neutral/1" or data["feature"] != USAGE_FEATURE or data["relation_id"] != USAGE_RELATION:
        raise ValueError("USAGE_ORIGINAL_PROFILE")
    if name in {"minute-meter", "hour-meter", "inferred-import"} and data["target_unit"] != "UsageHour":
        raise ValueError("USAGE_SELECTED_TARGET")
    if not all(type(data["source_quantity"].get(key)) is str and data["source_quantity"][key]
               for key in ("measurement_id", "evidence_ref")):
        raise ValueError("USAGE_ORIGINAL_MEASUREMENT_REFERENCE")
    # Only exact original magnitudes and quoted tags cross this boundary.
    original = data["source_quantity"]
    record(original, {"measurement_id", "evidence_ref", "value", "unit"})
    quantity = {"value": number(original_number(original["value"])), "unit": original["unit"]}
    price = data["price"]
    if price is not None:
        record(price, {"quote_id", "evidence_ref", "value", "per_unit", "currency"})
        if not all(type(price.get(key)) is str and price[key] for key in ("quote_id", "evidence_ref")):
            raise ValueError("USAGE_ORIGINAL_QUOTE_REFERENCE")
    quoted = {"value": number(original_number(price["value"])), "per_unit": price["per_unit"], "currency": price["currency"]} if price else None
    reference = reference or register_all(root)[name]
    descriptor = read_json(root / reference["locator"])
    inputs = {"original": quantity}
    if name in {"minute-meter", "hour-meter", "base-minute-meter", "base-download-meter"}:
        inputs["price"] = quoted
    if name == "unused-extended": inputs = {}
    if name in {"base-custom-import", "extended-base-import"}: inputs = {"original": number(original_number(original["value"]))}
    scope = {"agreement_id": "synthetic-usage-agreement", "participant_ids": ["synthetic-recipient"], "pool_id": "synthetic-usage-pool",
             "asset_ids": ["synthetic-usage-asset"], "purpose": "synthetic-usage-conversion"}
    cells = []
    if descriptor["state"]:
        slot = descriptor["state"][0]
        opening_type = next(port["type"] for port in descriptor["interface"]["ports"] if port["role"] == "opening")
        initial_unit = opening_type["args"][0]["name"]
        cell_scope = {"agreement_id": scope["agreement_id"], "participant_id": scope["participant_ids"][0], "pool_id": scope["pool_id"],
                      "asset_id": scope["asset_ids"][0], "unit": slot["unit"]}
        cells = [{"state_key": canonical({**cell_scope, "purpose": slot["purpose"]}), "opening_port": "meter", "purpose": slot["purpose"],
                  "unit": slot["unit"], "scope": cell_scope, "boundary": "2026-01-01", "quantity": {"value": "0", "unit": initial_unit},
                  "provenance_ref": "explicit-synthetic-zero-genesis", "scenario_id": "synthetic-usage-conversion"}]
        if opening is not None: cells = [deepcopy(opening)]
    package = {"profile": "spl-module/1", "module_ref": reference,
        "manifest": {"run_id": data["case_id"], "scenario_id": "synthetic-usage-conversion", "mode": "final",
                     "period": {"start": "2026-01-01", "end": "2026-04-01"}, "cutoff": "2026-04-03T00:00:00Z",
                     "compiler_build": "unbound", "runtime_build": "unbound", "module_closure": [],
                     "resource_limits": {"max_input_rows": 100000, "lean_timeout_seconds": 180}},
        "scope": scope, "inputs": inputs, "parameters": {}, "evidence": {}, "state_cells": cells,
        "decisions": [{"decision_id": "USAGE_CONVERSION_SELECTED", "policy_id": "synthetic:usage-conversion", "policy_revision": "1",
                       "status": "proposed", "evidence_ref": "independent-original-measurement-and-quote"}]}
    # Retain full originals alongside the package in the authored artifact; the
    # executable bindings contain exactly original tagged quantities/quotes.
    return bind_module_package(package, root) if bind else package


if __name__ == "__main__":
    refs = register_all()
    for name in ("minute-meter", "hour-meter", "inferred-import", "unused-extended"):
        write_json(FOLDER / (name + "-package.unbound.json"), usage_package(name, reference=refs[name], bind=False))
