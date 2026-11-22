"""DYN-CAL-01 executable reference; no oracle imports or implicit date policy."""
import re
from fractions import Fraction

from .model import SPLException


def add_calendar_months(source, months, policy):
    def fail(code):
        raise SPLException(code, code)

    if not isinstance(source, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", source):
        fail("INVALID_DATE")
    year, month, day = map(int, source.split("-"))

    def length(y, m):
        if m == 2:
            return 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28
        return 30 if m in (4, 6, 9, 11) else 31

    if not (1 <= year <= 9999 and 1 <= month <= 12 and 1 <= day <= length(year, month)):
        fail("INVALID_DATE")
    if isinstance(months, bool) or not isinstance(months, (int, Fraction)) or months < 0 or Fraction(months).denominator != 1:
        fail("CALENDAR_INVALID_MONTHS")
    if policy not in ("clamp_day", "reject_invalid_day"):
        fail("CALENDAR_UNSUPPORTED_POLICY")
    index = (year - 1) * 12 + month - 1 + int(months)
    target_year, target_month = index // 12 + 1, index % 12 + 1
    if target_year > 9999:
        fail("CALENDAR_YEAR_RANGE")
    last = length(target_year, target_month)
    if day > last and policy == "reject_invalid_day":
        fail("CALENDAR_INVALID_TARGET_DAY")
    return f"{target_year:04d}-{target_month:02d}-{min(day, last):02d}"
