"""Exact explicit-zone RFC3339 transport shared by the reference checker/evaluator."""
from datetime import date, timedelta
from fractions import Fraction
import re

from .model import InstantValue, SPLException

RFC3339 = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.([0-9]+))?([Zz]|[+-][0-9]{2}:[0-9]{2})\Z")


def parse_instant(text: str) -> InstantValue:
    try:
        match = RFC3339.fullmatch(text) if isinstance(text, str) else None
        if match is None:
            raise ValueError()
        year, month, day, hour, minute, second = map(int, match.groups()[:6])
        fraction, zone = match.groups()[6:]
        local = date(year, month, day)
        if hour >= 24 or minute >= 60 or second >= 60 or zone == "-00:00":
            raise ValueError()
        offset = 0
        if zone.upper() != "Z":
            hours, minutes = map(int, zone[1:].split(":"))
            if hours >= 24 or minutes >= 60:
                raise ValueError()
            offset = (hours * 3600 + minutes * 60) * (-1 if zone[0] == "-" else 1)
        whole = (local.toordinal() - 1) * 86400 + hour * 3600 + minute * 60 + second - offset
        days, time = divmod(whole, 86400)
        utc = date(1, 1, 1) + timedelta(days=days)
        seconds = Fraction(whole) + (Fraction(int(fraction), 10 ** len(fraction)) if fraction else 0)
        fraction = (fraction or "").rstrip("0")
        canonical = (f"{utc.year:04d}-{utc.month:02d}-{utc.day:02d}T{time // 3600:02d}:"
                     f"{time // 60 % 60:02d}:{time % 60:02d}" + ("." + fraction if fraction else "") + "Z")
        return InstantValue(seconds, canonical)
    except (ValueError, TypeError, OverflowError):
        raise SPLException("INVALID_INSTANT", "Expected RFC3339 timestamp with known explicit offset; leap seconds excluded") from None
