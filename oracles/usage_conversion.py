"""Independent exact controls for the selected finite usage-time extension.

This consumes original measurements and price quotes, never compiler-projected
bindings, emitted output, a user-supplied conversion factor or a solved answer.
It establishes no source admission, IR validation or state compatibility.
"""
from copy import deepcopy
from fractions import Fraction
import re


class UsageConversionError(ValueError):
    pass


def _fail(code):
    raise UsageConversionError(code)


def _keys(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail("unexpected_shape")


def _exact(value):
    if not isinstance(value, str) or not re.fullmatch(
            r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|[0-9]+/[0-9]+)", value):
        _fail("exact_number_required")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        _fail("exact_number_required")


def usage_conversion(data):
    """Convert an original quantity and optionally price the resulting quantity.

    These independent scale definitions come from the adopted specification:
    one UsageMinute measures one base minute; one UsageHour measures sixty.
    The algorithm compares exact base magnitudes, rather than accepting a
    caller's direction, factor or rounding certificate.
    """
    _keys(data, ("schema_version", "case_id", "feature", "relation_id",
                 "source_quantity", "target_unit", "price"))
    if data["schema_version"] != "spl-usage-conversion-neutral/1":
        _fail("unsupported_schema")
    if not isinstance(data["case_id"], str) or not data["case_id"]:
        _fail("missing_case_identity")
    if data["feature"] != "spl.usage-time/1":
        _fail("unsupported_feature")
    if data["relation_id"] != "spl.usage-time/1:minute-hour":
        _fail("unsupported_relation")
    original = data["source_quantity"]
    _keys(original, ("measurement_id", "evidence_ref", "value", "unit"))
    for key in ("measurement_id", "evidence_ref"):
        if not isinstance(original[key], str) or not original[key]:
            _fail("missing_measurement_evidence")
    scales = {"UsageMinute": Fraction(1), "UsageHour": Fraction(60)}
    source, target = original["unit"], data["target_unit"]
    if not isinstance(source, str) or source not in scales:
        _fail("unsupported_unit")
    if not isinstance(target, str) or target not in scales:
        _fail("unsupported_unit")
    if source == target:
        _fail("opposite_endpoint_required")
    original_value = _exact(original["value"])
    base_magnitude = original_value * scales[source]
    converted = base_magnitude / scales[target]
    price = data["price"]
    earned = None
    if price is not None:
        _keys(price, ("quote_id", "evidence_ref", "value", "per_unit", "currency"))
        if not all(isinstance(price[k], str) and price[k]
                   for k in ("quote_id", "evidence_ref")):
            _fail("missing_price_evidence")
        if price["currency"] != "USD":
            _fail("unsupported_currency")
        if price["per_unit"] != target:
            _fail("price_unit_mismatch")
        earned = converted * _exact(price["value"])
    return {
        "case_id": data["case_id"],
        "original_quantity": deepcopy(original),
        "original_price": deepcopy(price),
        "feature": data["feature"],
        "relation_id": data["relation_id"],
        "base_minutes": base_magnitude,
        "converted_quantity": {"value": converted, "unit": target},
        "earned": None if earned is None else {"value": earned, "currency": "USD"},
    }


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value.numerator) if value.denominator == 1 else str(value)
    if isinstance(value, list):
        return [exact_json(item) for item in value]
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    return value
