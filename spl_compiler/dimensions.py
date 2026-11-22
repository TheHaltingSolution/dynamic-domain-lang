"""Finite dimensional vocabulary and exact reference arithmetic.

Money and Ratio retain their legacy shared Fraction representation. Static
checking is still required to distinguish these two scalar argument types.
"""
from fractions import Fraction

from .model import QuantityValue, RateValue, SPLException, Type

UNIT_DICTIONARY = "spl.units/1"
UNITS = frozenset({"Download", "UsageMinute"})
DIMENSIONAL_VALUES = (QuantityValue, RateValue)


def validate_unit(unit: str) -> None:
    if not isinstance(unit, str) or unit not in UNITS:
        raise SPLException("UNSUPPORTED_UNIT", "Only Download and UsageMinute are admitted by spl.units/1")


def validate_currency(currency: str) -> None:
    if currency != "USD":
        raise SPLException("UNSUPPORTED_CURRENCY", "The implemented rate profile supports USD only")


def contains_dimension(typ: Type) -> bool:
    return typ.name in {"Quantity", "Rate"} or any(map(contains_dimension, typ.args)) or any(
        contains_dimension(field) for _, field in typ.fields)


def dimension_key(value):
    if isinstance(value, QuantityValue):
        return ("quantity", value.unit)
    if isinstance(value, RateValue):
        return ("rate", value.per_unit, value.currency)
    return None


def with_number(value, number: Fraction):
    if isinstance(value, QuantityValue):
        return QuantityValue(number, value.unit)
    if isinstance(value, RateValue):
        return RateValue(number, value.per_unit, value.currency)
    return number


def typed_zero(typ: Type):
    if typ.name == "Quantity":
        return QuantityValue(Fraction(0), typ.args[0].name)
    if typ.name == "Rate":
        return RateValue(Fraction(0), typ.args[0].name, typ.args[1].name)
    return Fraction(0)


def is_zero(value) -> bool:
    return value.value == 0 if isinstance(value, DIMENSIONAL_VALUES) else value == 0


def dimensional_binary(op: str, left, right):
    """Evaluate an operation with at least one tagged dimensional operand."""
    lk, rk = dimension_key(left), dimension_key(right)
    matching = lk is not None and lk == rk
    if matching:
        a, b = left.value, right.value
        if op in {"+", "-"}:
            return with_number(left, a + b if op == "+" else a - b)
        if op in {"==", "!=", "<", "<=", ">", ">="}:
            return {"==": lambda: a == b, "!=": lambda: a != b,
                    "<": lambda: a < b, "<=": lambda: a <= b,
                    ">": lambda: a > b, ">=": lambda: a >= b}[op]()
        if op == "/":
            if b == 0:
                raise SPLException("DIVISION_BY_ZERO", "Demanded exact division by zero")
            return a / b
    if op == "*":
        if lk is not None and isinstance(right, Fraction):
            return with_number(left, left.value * right)
        if rk is not None and isinstance(left, Fraction):
            return with_number(right, left * right.value)
        quantity, rate = (left, right) if isinstance(left, QuantityValue) else (right, left)
        if isinstance(quantity, QuantityValue) and isinstance(rate, RateValue) and quantity.unit == rate.per_unit:
            return quantity.value * rate.value
    if op == "/" and lk is not None and isinstance(right, Fraction):
        if right == 0:
            raise SPLException("DIVISION_BY_ZERO", "Demanded exact division by zero")
        return with_number(left, left.value / right)
    raise SPLException("TYPE_MISMATCH", f"Operator {op} requires compatible dimensions")
