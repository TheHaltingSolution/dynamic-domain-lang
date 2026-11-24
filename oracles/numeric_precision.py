"""Independent exact controls for supplied ratio precision and money placement.

Only original basis/expressions and explicit policy are consumed. No compiler,
runtime, adapter, prior financial oracle, filesystem or clock is consulted.
"""
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
import json
import re

MODES = ("floor", "ceiling", "toward_zero", "half_even", "half_away_from_zero")
SCOPE = {"agreement_id", "participant_id", "pool_id", "asset_id", "currency"}
POLICY_FIELDS = {"id", "revision", "evidence_class", "ratio_expression_id", "ratio_expression_unit", "ratio_expressed_decimal_places", "ratio_quantum", "ratio_mode", "ratio_point", "money_quantum", "money_mode", "money_point", "bridge", "arithmetic"}


class NumericPrecisionOracleError(ValueError):
    pass


def require(condition, code):
    if not condition: raise NumericPrecisionOracleError(code)


def fields(value, names):
    require(type(value) is dict and value.keys() == set(names), "PRECISION_FIELDS")


def text(value):
    require(type(value) is str and bool(value) and all(not 0xD800 <= ord(char) <= 0xDFFF for char in value), "PRECISION_TEXT")
    return value


def numeric(value):
    if type(value) is str:
        require(re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is not None, "PRECISION_EXACT_NUMBER")
        return Fraction(value)
    fields(value, {"numerator", "denominator"})
    numerator, denominator = value["numerator"], value["denominator"]
    require(type(numerator) is str and re.fullmatch(r"-?(?:0|[1-9][0-9]*)", numerator) is not None and type(denominator) is str and re.fullmatch(r"[1-9][0-9]*", denominator) is not None, "PRECISION_EXACT_NUMBER")
    result = Fraction(int(numerator), int(denominator))
    require(str(result.numerator) == numerator and str(result.denominator) == denominator, "PRECISION_NORMALIZED_FRACTION")
    return result


def monetary(value, code):
    require(type(value) is dict and value.get("dimension") == "Money", code)
    fields(value, {"dimension", "currency", "value"})
    require(value["currency"] == "USD", "PRECISION_CURRENCY")
    return numeric(value["value"])


def registration(policy):
    """Content correspondence only; no external registry/version-history claim."""
    require(type(policy) is dict, "PRECISION_POLICY")
    text(policy["id"]); text(policy["revision"])
    payload = json.dumps(policy, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return {"id": policy["id"], "revision": policy["revision"], "sha256": sha256(payload).hexdigest()}


def _round_units(value, quantum, mode):
    """Choose an integer number of quanta using exact magnitude/remainder."""
    magnitude = abs(value) / quantum
    whole, remainder = divmod(magnitude.numerator, magnitude.denominator)
    negative = value < 0
    if mode == "floor": units = -(whole + bool(remainder)) if negative else whole
    elif mode == "ceiling": units = -whole if negative else whole + bool(remainder)
    elif mode == "toward_zero": units = -whole if negative else whole
    else:
        twice = remainder * 2
        increment = twice > magnitude.denominator or (twice == magnitude.denominator and (mode == "half_away_from_zero" or whole % 2 == 1))
        units = (whole + increment) * (-1 if negative else 1)
    return units * quantum


def _run(data):
    fields(data, {"schema_version", "case_id", "scope", "policy", "policy_ref", "ratio_expression", "lines", "population"})
    require(data["schema_version"] == "numeric-precision-neutral/1", "PRECISION_SCHEMA")
    text(data["case_id"])
    scope = data["scope"]; fields(scope, SCOPE)
    for item in scope.values(): text(item)
    require(scope["currency"] == "USD", "PRECISION_CURRENCY")
    selected = data["policy"]; fields(selected, POLICY_FIELDS)
    text(selected["id"]); text(selected["revision"]); text(selected["ratio_expression_id"])
    require(selected["evidence_class"] == "research_assumption" and selected["arithmetic"] == "exact_rational_no_implicit_rounding", "PRECISION_POLICY")
    require(selected["ratio_point"] == "before_monetary_application" and selected["money_point"] in {"row", "aggregate"} and selected["bridge"] == "selected_total_minus_sum_rounded_detail", "PRECISION_POINT")
    require(type(selected["ratio_mode"]) is str and selected["ratio_mode"] in MODES and type(selected["money_mode"]) is str and selected["money_mode"] in MODES, "PRECISION_MODE")
    places = selected["ratio_expressed_decimal_places"]
    require(type(places) is int and 0 <= places <= 6 and selected["ratio_expression_unit"] in {"fraction", "percentage"}, "PRECISION_EXPRESSION_PRECISION")
    ratio_quantum = selected["ratio_quantum"]
    require(type(ratio_quantum) is dict and ratio_quantum.get("dimension") == "Ratio", "PRECISION_RATIO_QUANTUM_DIMENSION")
    fields(ratio_quantum, {"dimension", "value"})
    rq = numeric(ratio_quantum["value"])
    mq = monetary(selected["money_quantum"], "PRECISION_MONEY_QUANTUM_DIMENSION")
    require(rq > 0 and mq > 0, "PRECISION_POSITIVE_QUANTUM")
    expected_quantum = Fraction(1, 10 ** places) / (100 if selected["ratio_expression_unit"] == "percentage" else 1)
    require(rq == expected_quantum, "PRECISION_RATIO_QUANTUM_PRECISION")
    reference = data["policy_ref"]; fields(reference, {"id", "revision", "sha256"})
    require(type(reference["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", reference["sha256"]) is not None and reference == registration(selected), "PRECISION_POLICY_PIN")
    expression = data["ratio_expression"]
    fields(expression, {"id", "scope", "original_ref", "source_ref", "expressed_unit", "expressed_value"})
    text(expression["id"]); text(expression["original_ref"]); text(expression["source_ref"])
    require(expression["scope"] == scope and expression["id"] == selected["ratio_expression_id"] and expression["expressed_unit"] == selected["ratio_expression_unit"], "PRECISION_EXPRESSION_AUTHORITY")
    expressed = numeric(expression["expressed_value"])
    exact_ratio = expressed / (100 if expression["expressed_unit"] == "percentage" else 1)
    rows = data["lines"]
    require(type(rows) is list and len(rows) <= 8, "PRECISION_ROW_BOUND")
    row_ids, originals, parsed = set(), set(), []
    for row in rows:
        fields(row, {"id", "scope", "original_ref", "source_ref", "basis", "ratio_expression_id"})
        identity, original = text(row["id"]), text(row["original_ref"]); text(row["source_ref"])
        require(identity not in row_ids and original not in originals, "PRECISION_ORIGINAL_REUSE")
        row_ids.add(identity); originals.add(original)
        require(row["scope"] == scope and row["ratio_expression_id"] == expression["id"], "PRECISION_ROW_AUTHORITY")
        parsed.append((row, monetary(row["basis"], "PRECISION_BASIS_DIMENSION")))
    population = data["population"]
    fields(population, {"id", "scope", "source_ref", "complete", "row_ids", "basis_total"})
    text(population["id"]); text(population["source_ref"])
    require(population["scope"] == scope and population["complete"] is True, "PRECISION_COMPLETE_POPULATION")
    require(type(population["row_ids"]) is list and len(population["row_ids"]) <= 8, "PRECISION_POPULATION_IDS")
    for identity in population["row_ids"]: text(identity)
    require(len(set(population["row_ids"])) == len(population["row_ids"]) and set(population["row_ids"]) == row_ids, "PRECISION_POPULATION_IDS")
    total_basis = sum((basis for _, basis in parsed), Fraction())
    require(monetary(population["basis_total"], "PRECISION_BASIS_DIMENSION") == total_basis, "PRECISION_POPULATION_TOTAL")

    rounded_ratio = _round_units(exact_ratio, rq, selected["ratio_mode"])
    details = []
    for row, basis in parsed:
        before, after = basis * exact_ratio, basis * rounded_ratio
        displayed = _round_units(after, mq, selected["money_mode"])
        details.append({"id": row["id"], "original": deepcopy(row), "basis": basis, "exact_original_ratio": exact_ratio, "selected_ratio": rounded_ratio,
            "exact_before_ratio_rounding": before, "exact_after_ratio_rounding": after, "ratio_rounding_effect": after - before,
            "displayed_rounded": displayed, "money_rounding_delta": displayed - after})
    before_total = sum((row["exact_before_ratio_rounding"] for row in details), Fraction())
    after_total = sum((row["exact_after_ratio_rounding"] for row in details), Fraction())
    displayed_total = sum((row["displayed_rounded"] for row in details), Fraction())
    aggregate = _round_units(after_total, mq, selected["money_mode"])
    statement_total = displayed_total if selected["money_point"] == "row" else aggregate
    bridge = statement_total - displayed_total
    require(displayed_total + bridge == statement_total and before_total + (after_total - before_total) + (statement_total - after_total) == statement_total, "PRECISION_INTERNAL_BRIDGE")
    return {"case_id": data["case_id"], "scope": deepcopy(scope), "policy_ref": deepcopy(reference), "policy": deepcopy(selected),
        "ratio_precision": {"original": deepcopy(expression), "measure": "Ratio", "expressed_exact": expressed, "expression_unit": expression["expressed_unit"], "declared_decimal_places": places,
            "exact_ratio": exact_ratio, "ratio_quantum": rq, "mode": selected["ratio_mode"], "point": selected["ratio_point"], "rounded_ratio": rounded_ratio, "ratio_rounding_delta": rounded_ratio - exact_ratio},
        "line_details": details, "population": deepcopy(population),
        "statement": {"money_measure": "USD", "source_row_ids": sorted(row_ids), "original_basis_total": total_basis, "exact_before_ratio_rounding": before_total, "exact_after_ratio_rounding": after_total,
            "ratio_rounding_effect_total": after_total - before_total, "sum_rounded_detail": displayed_total, "aggregate_rounded_control": aggregate,
            "money_quantum": mq, "mode": selected["money_mode"], "selected_point": selected["money_point"], "selected_total": statement_total, "money_rounding_delta": statement_total - after_total,
            "total_adjustment": statement_total - before_total, "rounding_bridge": bridge, "bridge_equation": "sum_rounded_detail_plus_rounding_bridge_equals_statement_total"},
        "issuance_status": "unissued_calculation", "payment_evidence_status": "not_part_of_profile", "bank_movement_created": False}


def numeric_precision(data):
    try: return _run(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as error:
        if isinstance(error, NumericPrecisionOracleError): raise
        raise NumericPrecisionOracleError("PRECISION_MALFORMED_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction): return str(value)
    if isinstance(value, list): return [exact_json(item) for item in value]
    if isinstance(value, dict): return {key: exact_json(item) for key, item in value.items()}
    return value
