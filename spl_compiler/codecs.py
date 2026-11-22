"""Strict transport codecs and content identities; no financial floats."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import unicodedata
from datetime import date
from fractions import Fraction
from pathlib import Path

from .instant import parse_instant
from .model import InstantValue, SPLException


class DataError(ValueError):
    def __init__(self, code, message, pointer="", span=None):
        self.code, self.pointer, self.span = code, pointer, span
        super().__init__(message)

    def diagnostic(self):
        value = {"code": self.code, "message": str(self), "pointer": self.pointer}
        if self.span is not None:
            value["span"] = self.span
        return value


def fail(code, message, pointer=""):
    raise DataError(code, message, pointer)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("DUPLICATE_JSON_KEY", f"Duplicate JSON key {key!r}")
        result[key] = value
    return result


def loads(data):
    try:
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        if data.startswith("\ufeff"):
            fail("INVALID_UTF8", "UTF-8 BOM is not supported")
        value = json.loads(data, object_pairs_hook=_pairs,
                           parse_float=lambda _: fail("JSON_FLOAT", "Use exact decimal strings"),
                           parse_constant=lambda _: fail("INVALID_JSON", "Nonfinite JSON number"))
        check_text(value)
        return value
    except (UnicodeError, json.JSONDecodeError) as exc:
        fail("INVALID_JSON", str(exc))


def read_json(path):
    return loads(Path(path).read_bytes())


def check_text(value, pointer=""):
    if value is None:
        fail("NULL_NOT_ALLOWED", "Omit optional fields rather than using null", pointer)
    if isinstance(value, float):
        fail("JSON_FLOAT", "Binary floats are unsupported", pointer)
    if isinstance(value, str) and unicodedata.normalize("NFC", value) != value:
        fail("NON_NFC_TEXT", "Text must already be NFC", pointer)
    if isinstance(value, str) and any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        fail("INVALID_UNICODE", "Unpaired Unicode surrogate", pointer)
    if isinstance(value, dict):
        for key, item in value.items():
            check_text(key, pointer)
            check_text(item, pointer + "/" + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            check_text(item, pointer + "/" + str(i))


DECIMAL = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?\Z")
INTEGER = re.compile(r"-?(0|[1-9][0-9]*)\Z")


def exact(value, pointer=""):
    if isinstance(value, Fraction):
        return value
    if isinstance(value, str) and DECIMAL.fullmatch(value):
        return Fraction(value)
    if isinstance(value, dict) and set(value) == {"numerator", "denominator"}:
        n, d = value["numerator"], value["denominator"]
        if (not isinstance(n, str) or not INTEGER.fullmatch(n) or
                not isinstance(d, str) or not re.fullmatch(r"[1-9][0-9]*", d)):
            fail("INVALID_RATIONAL", "Expected integer strings and a positive denominator", pointer)
        q = Fraction(int(n), int(d))
        if str(q.numerator) != n or str(q.denominator) != d:
            fail("NONCANONICAL_RATIONAL", "Rational must be reduced; zero is 0/1", pointer)
        return q
    fail("INVALID_EXACT_NUMBER", f"Expected exact decimal string or normalized rational: {value!r}", pointer)


def number(value):
    """Canonical exact output: terminating decimal, otherwise reduced fraction."""
    q = Fraction(value)
    d, twos, fives = q.denominator, 0, 0
    while d % 2 == 0:
        d //= 2
        twos += 1
    while d % 5 == 0:
        d //= 5
        fives += 1
    if d != 1:
        return {"numerator": str(q.numerator), "denominator": str(q.denominator)}
    places = max(twos, fives)
    scaled = abs(q.numerator) * 2 ** (places - twos) * 5 ** (places - fives)
    if not places:
        return str(q.numerator)
    digits = str(scaled).zfill(places + 1)
    out = (digits[:-places] + "." + digits[-places:]).rstrip("0").rstrip(".")
    return ("-" if q < 0 else "") + out


def money(value, currency="USD"):
    return {"value": number(value), "currency": currency}


def quantity(value, unit):
    """Encode an exact quantity without erasing its admitted unit."""
    from .dimensions import UNITS
    if unit not in UNITS:
        fail("UNSUPPORTED_UNIT", str(unit))
    return {"value": number(value), "unit": unit}


def rate(value, per_unit, currency="USD"):
    """Encode an exact monetary rate with its denominator unit."""
    from .dimensions import UNITS
    if per_unit not in UNITS:
        fail("UNSUPPORTED_UNIT", str(per_unit))
    if currency != "USD":
        fail("UNSUPPORTED_CURRENCY", str(currency))
    return {"value": number(value), "per_unit": per_unit, "currency": currency}


def dimensional_amount(value, unit, *, currency=None, pointer=""):
    """Strictly decode quantity/rate transport to immutable tagged values."""
    from .evaluator import decode_value
    from .model import Type
    typ = Type("Quantity", (Type(unit),)) if currency is None else Type("Rate", (Type(unit), Type(currency)))
    return decode_value(value, typ, pointer)


def amount(value, pointer=""):
    if not isinstance(value, dict) or set(value) != {"value", "currency"}:
        fail("INVALID_MONEY", "Expected value and currency", pointer)
    if value["currency"] != "USD":
        fail("UNSUPPORTED_CURRENCY", "This implementation supports USD only", pointer)
    return exact(value["value"], pointer + "/value")


def day(value, pointer=""):
    try:
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Expected YYYY-MM-DD")
        return date.fromisoformat(value)
    except ValueError as exc:
        fail("INVALID_DATE", str(exc), pointer)


def instant(value, pointer=""):
    """Exact UTC chronology using the same bounded RFC3339 profile as SPL.

    The result is an InstantValue, not a host datetime: decimal fractions retain
    every digit, and equivalent explicit offsets compare equal.
    """
    try:
        return parse_instant(value)
    except SPLException as exc:
        fail(exc.code, exc.message, pointer)


def instant_utc_day(value, pointer=""):
    """Explicit UTC calendar-day projection for date-precision source policies.

    This is intentionally a date boundary, never an Instant comparison.
    """
    return date.fromisoformat(instant(value, pointer).canonical[:10])


def period(value):
    if not isinstance(value, dict) or set(value) != {"start", "end"}:
        fail("INVALID_PERIOD", "Expected start and end")
    if day(value["start"]) >= day(value["end"]):
        fail("INVALID_PERIOD", "Period must have start < end")
    return value


def encode(value):
    from .model import QuantityValue, RateValue
    if isinstance(value, QuantityValue):
        return quantity(value.value, value.unit)
    if isinstance(value, RateValue):
        return rate(value.value, value.per_unit, value.currency)
    if isinstance(value, InstantValue):
        return value.canonical
    if isinstance(value, Fraction):
        return number(value)
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(x) for x in value]
    return value


def canonical(value):
    return json.dumps(encode(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(encode(value), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def read_csv(path, headers):
    try:
        raw = Path(path).read_bytes().decode("utf-8")
        if raw.startswith("\ufeff"):
            fail("INVALID_CSV", "UTF-8 BOM unsupported")
        state = "start"
        for char in raw:
            if state == "quoted":
                if char == '"':
                    state = "closed"
            elif state == "closed":
                if char == '"':
                    state = "quoted"
                elif char in ",\r\n":
                    state = "start"
                else:
                    fail("INVALID_CSV", "Unexpected character after closing quote")
            elif state == "start":
                if char == '"':
                    state = "quoted"
                elif char not in ",\r\n":
                    state = "unquoted"
            elif state == "unquoted":
                if char == '"':
                    fail("INVALID_CSV", "Quote inside unquoted field")
                if char in ",\r\n":
                    state = "start"
        if state == "quoted":
            fail("INVALID_CSV", "Unterminated quoted field")
        reader = csv.reader(io.StringIO(raw, newline=""), strict=True)
        header = next(reader)
        if len(set(header)) != len(header) or set(header) != set(headers):
            fail("INVALID_CSV_HEADER", f"Expected exactly {headers}", str(path))
        rows = []
        for i, row in enumerate(reader, 1):
            if len(row) != len(header):
                fail("RAGGED_CSV", f"Invalid record {i}", str(path))
            record = dict(zip(header, row))
            check_text(record)
            rows.append(record)
        return rows
    except (UnicodeError, csv.Error, StopIteration) as exc:
        fail("INVALID_CSV", str(exc), str(path))


def write_csv(path, rows, headers):
    check_text(rows)
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=headers, lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    writer.writerows(rows)
    Path(path).write_bytes(out.getvalue().encode("utf-8"))
