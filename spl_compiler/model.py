"""Shared SPL syntax, checked types, diagnostics and exact transport helpers.

Syntax is a closed dict tree so parsed source and emitted code share no executable
Python objects. The static checker attaches immutable ``_type`` annotations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any


@dataclass(frozen=True)
class Type:
    name: str
    args: tuple["Type", ...] = ()
    fields: tuple[tuple[str, "Type"], ...] = ()

    def __str__(self) -> str:
        if self.fields:
            return "{" + ", ".join(f"{k}: {v}" for k, v in self.fields) + "}"
        return self.name + ("<" + ",".join(map(str, self.args)) + ">" if self.args else "")

    @property
    def numeric(self) -> bool:
        return self.name in {"Int", "Nat", "Ratio", "Rational", "Money", "Quantity", "Rate"}


BOOL = Type("Bool")
INT = Type("Int")
RATIO = Type("Ratio")
TEXT = Type("Text")
DATE = Type("Date")
INSTANT = Type("Instant")
USD = Type("Money", (Type("USD"),))


@dataclass(frozen=True)
class QuantityValue:
    value: Fraction
    unit: str

    def __post_init__(self) -> None:
        from .dimensions import validate_unit
        validate_unit(self.unit)
        if not isinstance(self.value, Fraction):
            raise SPLException("INVALID_EXACT_NUMBER", "Quantity requires an exact Fraction")


@dataclass(frozen=True)
class RateValue:
    value: Fraction
    per_unit: str
    currency: str = "USD"

    def __post_init__(self) -> None:
        from .dimensions import validate_currency, validate_unit
        validate_unit(self.per_unit)
        validate_currency(self.currency)
        if not isinstance(self.value, Fraction):
            raise SPLException("INVALID_EXACT_NUMBER", "Rate requires an exact Fraction")


@dataclass(frozen=True, order=True)
class InstantValue:
    """Normalized exact UTC seconds, kept distinct from financial numbers."""
    seconds: Fraction
    canonical: str = field(compare=False)


@dataclass(frozen=True)
class MapValue:
    entries: tuple[tuple[Any, Any], ...]


@dataclass(frozen=True)
class OptionValue:
    present: bool
    value: Any = None


@dataclass(frozen=True)
class Diagnostic:
    code: str
    message: str
    span: dict[str, Any] | None = None
    scope: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.span is not None:
            value["span"] = self.span
        if self.scope is not None:
            value["scope"] = self.scope
        return value


class SPLException(Exception):
    def __init__(self, code: str, message: str, span: dict | None = None):
        super().__init__(f"{code}: {message}")
        self.code, self.message, self.span = code, message, span
        self.diagnostics = [Diagnostic(code, message, span)]

    def to_dict(self) -> dict[str, Any]:
        return self.diagnostics[0].to_dict()


@dataclass
class CheckedSchedule:
    schedule: dict[str, Any]
    types: dict[str, Type]
    definition_order: list[str]


@dataclass
class Outcome:
    status: str
    emissions: dict[str, Any] = field(default_factory=dict)
    closing: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "emissions": encode_value(self.emissions),
                "closing": encode_value(self.closing), "trace": encode_value(self.trace),
                "diagnostics": self.diagnostics}


def encode_fraction(value: Fraction) -> str | dict[str, str]:
    """Canonical exact decimal when finite; normalized fraction otherwise."""
    denominator = value.denominator
    twos = fives = 0
    while denominator % 2 == 0:
        twos += 1
        denominator //= 2
    while denominator % 5 == 0:
        fives += 1
        denominator //= 5
    if denominator != 1:
        return {"numerator": str(value.numerator), "denominator": str(value.denominator)}
    scale = max(twos, fives)
    if scale == 0:
        return str(value.numerator)
    integer = abs(value.numerator) * (10 ** scale // value.denominator)
    digits = str(integer).rjust(scale + 1, "0")
    result = digits[:-scale] + "." + digits[-scale:]
    result = result.rstrip("0").rstrip(".")
    return ("-" if value < 0 else "") + result


def encode_value(value: Any) -> Any:
    if isinstance(value, QuantityValue):
        return {"value": encode_fraction(value.value), "unit": value.unit}
    if isinstance(value, RateValue):
        return {"value": encode_fraction(value.value), "per_unit": value.per_unit, "currency": value.currency}
    if isinstance(value, OptionValue):
        return {"some":encode_value(value.value)} if value.present else {"none":True}
    if isinstance(value, MapValue):
        return [{"key": encode_value(k), "value": encode_value(v)} for k,v in value.entries]
    if isinstance(value, InstantValue):
        return value.canonical
    if isinstance(value, Fraction):
        return encode_fraction(value)
    if isinstance(value, Type):
        return str(value)
    if isinstance(value, dict):
        return {key: encode_value(item) for key, item in value.items() if key != "_type"}
    if isinstance(value, (list, tuple)):
        return [encode_value(item) for item in value]
    return value
