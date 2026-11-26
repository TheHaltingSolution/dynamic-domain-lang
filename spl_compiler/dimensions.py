"""Finite dimensional vocabulary and exact reference arithmetic.

Money and Ratio retain their legacy shared Fraction representation. Static
checking is still required to distinguish these two scalar argument types.
"""
from fractions import Fraction
from dataclasses import dataclass
import hashlib
import json

from .model import QuantityValue, RateValue, SPLException, Type

UNIT_DICTIONARY = "spl.units/1"
UNITS = frozenset({"Download", "UsageMinute"})
USAGE_FEATURE = "spl.usage-time/1"
USAGE_RELATION = "spl.usage-time/1:minute-hour"


@dataclass(frozen=True)
class UnitDefinition:
    identifier: str
    name: str
    family: str
    base: str
    scale: Fraction

    @property
    def content(self):
        return {"id": self.identifier, "name": self.name, "family": self.family,
                "base": self.base, "scale_to_base": str(self.scale)}

    @property
    def pin(self):
        return hashlib.sha256(json.dumps(self.content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


UNIT_DEFINITIONS = (
    UnitDefinition("spl.units/1:Download", "Download", "download", "spl.units/1:Download", Fraction(1)),
    UnitDefinition("spl.units/1:UsageMinute", "UsageMinute", "usage-duration", "spl.units/1:UsageMinute", Fraction(1)),
    UnitDefinition("spl.units.usage-time/1:UsageHour", "UsageHour", "usage-duration", "spl.units/1:UsageMinute", Fraction(60)),
)


@dataclass(frozen=True)
class ConversionRelation:
    identifier: str
    left: str
    left_count: Fraction
    right: str
    right_count: Fraction

    @property
    def content(self):
        return {"id": self.identifier, "left": self.left, "left_count": str(self.left_count),
                "right": self.right, "right_count": str(self.right_count)}

    @property
    def pin(self):
        return hashlib.sha256(json.dumps(self.content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


CONVERSION_RELATIONS = (ConversionRelation(USAGE_RELATION, UNIT_DEFINITIONS[1].identifier, Fraction(60),
                                           UNIT_DEFINITIONS[2].identifier, Fraction(1)),)


@dataclass(frozen=True)
class FeatureDefinition:
    identifier: str
    units: tuple[str, ...]
    relations: tuple[str, ...]
    builtins: tuple[str, ...]
    unit_dictionary: str
    relation_dictionary: str


FEATURE_CATALOG = (FeatureDefinition(USAGE_FEATURE, (UNIT_DEFINITIONS[2].identifier,),
                                     (CONVERSION_RELATIONS[0].identifier,), ("convert_quantity",),
                                     "spl.units.usage-time/1", "spl.conversions.usage-time/1"),)


def _features(features):
    features = tuple(features)
    known = {entry.identifier for entry in FEATURE_CATALOG}
    if any(type(feature) is not str or feature not in known for feature in features):
        raise SPLException("UNSUPPORTED_FEATURE", "Unknown immutable dimension profile")
    if len(set(features)) != len(features):
        raise SPLException("DUPLICATE_FEATURE", "Repeated dimension profile")
    selected = tuple(entry for entry in FEATURE_CATALOG if entry.identifier in features)
    ids = {unit.identifier for unit in UNIT_DEFINITIONS if unit.name in UNITS}
    ids.update(identifier for feature in selected for identifier in feature.units)
    definitions = [entry for entry in UNIT_DEFINITIONS if entry.identifier in ids]
    if len(definitions) != len(ids) or len({entry.name for entry in definitions}) != len(definitions):
        raise SPLException("UNIT_OWNERSHIP_CONFLICT", "Unit names must have one immutable definition")
    if any(identifier not in {entry.identifier for entry in CONVERSION_RELATIONS}
           for feature in selected for identifier in feature.relations):
        raise SPLException("UNSUPPORTED_CONVERSION", "Feature contains an unknown relation")
    return features


@dataclass(frozen=True)
class DimensionAdmission:
    features: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "features", _features(self.features))


@dataclass(frozen=True)
class RuntimeMeanings:
    """Verified closure meanings; never used as source-spelling permission."""
    features: tuple[str, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "features", _features(self.features))


BASE_ADMISSION = DimensionAdmission()
BASE_MEANINGS = RuntimeMeanings()


def admission(features=()):
    return DimensionAdmission(tuple(features))


def meanings(owners=()):
    owners = tuple(owners)
    if any(not isinstance(owner, DimensionAdmission) for owner in owners):
        raise SPLException("INVALID_OWNER_CONTEXT", "Closure meanings require lexical owner admissions")
    return RuntimeMeanings(tuple(sorted({feature for owner in owners for feature in owner.features})))


def selected_features(context=None):
    if context is not None and not isinstance(context, (DimensionAdmission, RuntimeMeanings)):
        raise SPLException("INVALID_OWNER_CONTEXT", "Explicit immutable unit context required")
    features = context.features if isinstance(context, (DimensionAdmission, RuntimeMeanings)) else ()
    return tuple(entry for entry in FEATURE_CATALOG if entry.identifier in features)


def has_builtin(context, name):
    return isinstance(context, DimensionAdmission) and any(name in entry.builtins for entry in selected_features(context))


def unit_definition(unit, context=None):
    validate_unit(unit, context)
    return next(value for value in UNIT_DEFINITIONS if value.name == unit)


def used_unit_definitions(typ, context=BASE_MEANINGS):
    """Only actual Quantity/Rate occurrences, never Id kinds or enabled extras."""
    found = {}
    def visit(typ):
        if typ.name == "Id":
            return
        if typ.name in {"Quantity", "Rate"}:
            if len(typ.args) != (1 if typ.name == "Quantity" else 2):
                raise SPLException("TYPE_ARITY", "Invalid dimensional type")
            entry = unit_definition(typ.args[0].name, context)
            found[entry.identifier] = entry
            return
        for child in typ.args:
            visit(child)
        for _, child in typ.fields:
            visit(child)
    visit(typ)
    return tuple(found[key] for key in sorted(found))


def validate_relation(left, left_count, right, right_count):
    if any(not any(definition == endpoint for definition in UNIT_DEFINITIONS) for endpoint in (left, right)):
        raise SPLException("UNIT_DEFINITION_MISMATCH", "Endpoint definition differs from immutable catalog")
    if (not isinstance(left_count, Fraction) or not isinstance(right_count, Fraction)
            or left_count <= 0 or right_count <= 0 or left.family != right.family or left.base != right.base
            or left.scale <= 0 or right.scale <= 0
            or left_count * left.scale != right_count * right.scale):
        raise SPLException("CONVERSION_SCALE_MISMATCH", "Relation contradicts immutable endpoint meanings")


def conversion_factor(source, target, relation, context):
    entry = next((entry for entry in CONVERSION_RELATIONS if entry.identifier == relation), None)
    if entry is None:
        raise SPLException("UNSUPPORTED_CONVERSION", "Unknown immutable conversion relation")
    if not isinstance(context, (DimensionAdmission, RuntimeMeanings)) or not any(
            relation in entry.relations for entry in selected_features(context)):
        raise SPLException("FEATURE_REQUIRED", "Explicit conversion admission required")
    left, right = unit_definition(source, context), unit_definition(target, context)
    if {left.identifier, right.identifier} != {entry.left, entry.right} or left.identifier == right.identifier:
        raise SPLException("CONVERSION_ENDPOINT_MISMATCH", "Conversion requires opposite registered endpoints")
    registered_left = next(unit for unit in UNIT_DEFINITIONS if unit.identifier == entry.left)
    registered_right = next(unit for unit in UNIT_DEFINITIONS if unit.identifier == entry.right)
    validate_relation(registered_left, entry.left_count, registered_right, entry.right_count)
    return left.scale / right.scale
DIMENSIONAL_VALUES = (QuantityValue, RateValue)


def validate_unit(unit: str, context=None) -> None:
    extra_ids = {identifier for feature in selected_features(context) for identifier in feature.units}
    admitted_names = UNITS | {entry.name for entry in UNIT_DEFINITIONS if entry.identifier in extra_ids}
    if not isinstance(unit, str) or unit not in admitted_names:
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
        return QuantityValue(number, value.unit, value.context)
    if isinstance(value, RateValue):
        return RateValue(number, value.per_unit, value.currency, value.context)
    return number


def typed_zero(typ: Type, context=BASE_MEANINGS):
    if typ.name == "Quantity":
        return QuantityValue(Fraction(0), typ.args[0].name, context)
    if typ.name == "Rate":
        return RateValue(Fraction(0), typ.args[0].name, typ.args[1].name, context)
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
