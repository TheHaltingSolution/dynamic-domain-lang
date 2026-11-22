"""Independent DYN-CAL-01 expectation using the standard civil calendar library.

This disclosed synthetic oracle imports no compiler implementation. Agreement
with finite examples is regression evidence, not a general correctness proof.
"""
from calendar import monthrange
from copy import deepcopy
from datetime import date

from .r1 import supplied_due_reserve


def add_calendar_months(source, months, policy):
    try:
        origin = date.fromisoformat(source)
        if origin.isoformat() != source:
            raise ValueError
    except (TypeError, ValueError):
        raise ValueError("INVALID_DATE") from None
    if type(months) is not int or months < 0:
        raise ValueError("CALENDAR_INVALID_MONTHS")
    if policy not in {"clamp_day", "reject_invalid_day"}:
        raise ValueError("CALENDAR_UNSUPPORTED_POLICY")
    years, remainder = divmod(origin.month - 1 + months, 12)
    target_year, target_month = origin.year + years, remainder + 1
    if target_year > 9999:
        raise ValueError("CALENDAR_YEAR_RANGE")
    final_day = monthrange(target_year, target_month)[1]
    if origin.day > final_day and policy == "reject_invalid_day":
        raise ValueError("CALENDAR_INVALID_TARGET_DAY")
    return date(target_year, target_month, min(origin.day, final_day)).isoformat()


def derived_reserve(fixture):
    """Derive once from vintage creation, then apply the independent release rule."""
    supplied = deepcopy(fixture)
    supplied["vintage"]["supplied_due_date"] = add_calendar_months(
        fixture["vintage"]["creation_date"], fixture["months"], fixture["invalid_day_policy"])
    result = supplied_due_reserve(supplied)
    return {**result, "deadline": supplied["vintage"]["supplied_due_date"]}
