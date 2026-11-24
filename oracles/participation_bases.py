"""Independent original-fact controls for the selected finite C02 base policies.

This module uses exact rational arithmetic and calendar dates only. It imports
no SPL implementation, adapter, registration, financial helper or test module.
The selected policy does not admit signed original measures or net losses.
"""
from copy import deepcopy
from datetime import date
from fractions import Fraction
import re


class ParticipationBaseError(ValueError):
    pass


def require(value, code):
    if not value:
        raise ParticipationBaseError(code)


def fields(value, names):
    require(type(value) is dict and set(value) == set(names), "BASE_FIELDS")


def text(value):
    require(type(value) is str and bool(value) and all(not 0xD800 <= ord(c) <= 0xDFFF for c in value), "BASE_TEXT")
    return value


def exact(value):
    require(type(value) is str and re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+|[0-9]+/[1-9][0-9]*)", value) is not None,
            "BASE_EXACT")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError):
        raise ParticipationBaseError("BASE_EXACT") from None


def day(value):
    require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is not None, "BASE_DATE")
    try:
        result = date.fromisoformat(value)
    except ValueError:
        raise ParticipationBaseError("BASE_DATE") from None
    return result


def instant(value):
    require(type(value) is str, "BASE_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})", value)
    require(match is not None, "BASE_INSTANT")
    try:
        calendar = day(match[1])
    except ParticipationBaseError:
        raise ParticipationBaseError("BASE_INSTANT") from None
    hour, minute, second = (int(match[i]) for i in (2,3,4))
    require(hour < 24 and minute < 60 and second < 60, "BASE_INSTANT")
    offset = 0
    if match[6] != "Z":
        oh, om = int(match[6][1:3]), int(match[6][4:6])
        require(oh < 24 and om < 60, "BASE_INSTANT")
        offset = (oh * 3600 + om * 60) * (1 if match[6][0] == "+" else -1)
    fraction = Fraction(match[5]) if match[5] else Fraction()
    return Fraction(calendar.toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + fraction


def participation_bases(data):
    fields(data, {"case_id", "method", "scope", "period", "cutoff", "terms", "receipts", "deductions", "usage", "populations"})
    text(data["case_id"])
    require(type(data["method"]) is str and data["method"] in {"gross_percent", "net_percent", "unit_rate", "unit_rate_then_participation"}, "BASE_METHOD")
    scope = data["scope"]
    fields(scope, {"agreement_id", "participant_id", "asset_id", "pool_id", "currency"})
    for value in scope.values():
        text(value)
    require(scope["currency"] == "USD", "BASE_CURRENCY")
    fields(data["period"], {"start", "end"})
    start, end = day(data["period"]["start"]), day(data["period"]["end"])
    require(start < end, "BASE_PERIOD")
    cutoff = instant(data["cutoff"])
    require(cutoff >= end.toordinal() * 86400, "BASE_COMPLETE_PERIOD")
    terms = data["terms"]
    fields(terms, {"id", "source_ref", "scope", "approved", "effective", "observed_at", "percentage", "unit_rate", "unit", "participation_share"})
    text(terms["id"]); text(terms["source_ref"])
    require(terms["scope"] == scope and terms["approved"] is True, "BASE_TERMS_AUTHORITY")
    fields(terms["effective"], {"start", "end"})
    require(day(terms["effective"]["start"]) <= start < end <= day(terms["effective"]["end"]), "BASE_TERMS_PERIOD")
    require(instant(terms["observed_at"]) < cutoff, "BASE_TERMS_CUTOFF")
    percentage, rate, share = (exact(terms[name]) for name in ("percentage", "unit_rate", "participation_share"))
    require(0 <= percentage <= 1 and rate >= 0 and 0 <= share <= 1, "BASE_RATE_RANGE")
    require(terms["unit"] == "Download", "BASE_UNIT")
    require(type(data["populations"]) is list and len(data["populations"]) == 3, "BASE_POPULATIONS")
    populations = {}
    for population in data["populations"]:
        fields(population, {"id", "source_ref", "scope", "kind", "period", "complete", "row_ids", "reported_total", "observed_at"})
        text(population["id"]); text(population["source_ref"])
        kind = population["kind"]
        require(type(kind) is str and kind in {"receipts", "deductions", "usage"} and kind not in populations, "BASE_POPULATIONS")
        require(population["scope"] == scope and population["period"] == data["period"] and population["complete"] is True,
                "BASE_POPULATION_AUTHORITY")
        observed = instant(population["observed_at"])
        require(end.toordinal() * 86400 <= observed < cutoff, "BASE_POPULATION_CUTOFF")
        require(type(population["row_ids"]) is list, "BASE_POPULATION_ROWS")
        for value in population["row_ids"]:
            text(value)
        require(len(set(population["row_ids"])) == len(population["row_ids"]), "BASE_POPULATION_ROWS")
        populations[kind] = (population, observed)
    totals = {}
    all_ids, all_refs = set(), set()
    for kind in ("receipts", "deductions", "usage"):
        rows = data[kind]
        require(type(rows) is list and len(rows) <= 32, "BASE_ROW_BOUND")
        population, population_observed = populations[kind]
        total, ids = Fraction(), []
        for row in rows:
            fields(row, {"id", "original_ref", "source_ref", "scope", "effective_date", "observed_at", "amount"})
            identity, original = text(row["id"]), text(row["original_ref"])
            text(row["source_ref"])
            require(identity not in all_ids and original not in all_refs, "BASE_ORIGINAL_REUSE")
            all_ids.add(identity); all_refs.add(original); ids.append(identity)
            require(row["scope"] == scope, "BASE_ROW_SCOPE")
            effective, observed = day(row["effective_date"]), instant(row["observed_at"])
            require(start <= effective < end, "BASE_ROW_PERIOD")
            require(effective.toordinal() * 86400 <= observed <= population_observed and observed < cutoff,
                    "BASE_ROW_OBSERVATION")
            require(instant(terms["observed_at"]) <= observed, "BASE_TERMS_NOT_KNOWN")
            amount = exact(row["amount"])
            require(amount >= 0, "BASE_NONNEGATIVE")
            total += amount
        require(sorted(ids) == sorted(population["row_ids"]) and total == exact(population["reported_total"]), "BASE_POPULATION_RECONCILIATION")
        totals[kind] = total
    gross, deductions, quantity = (totals[k] for k in ("receipts", "deductions", "usage"))
    require(deductions <= gross, "BASE_NET_LOSS_VARIANT_REQUIRED")
    net = gross - deductions
    method = data["method"]
    basis = net if method == "net_percent" else gross if method == "gross_percent" else quantity
    selected_rate = percentage if method in {"gross_percent", "net_percent"} else rate
    pre_participation = basis * selected_rate
    selected_share = share if method == "unit_rate_then_participation" else Fraction(1)
    return {"case_id": data["case_id"], "method": method, "scope": deepcopy(scope), "period": deepcopy(data["period"]),
            "gross": gross, "deductions": deductions, "net": net, "quantity": quantity,
            "basis_measure": "USD" if method in {"gross_percent", "net_percent"} else "Download",
            "selected_basis": basis, "selected_rate": selected_rate,
            "rate_measure": "Ratio" if method in {"gross_percent", "net_percent"} else "USD/Download",
            "pre_participation": pre_participation, "applied_participation": selected_share,
            "earned": pre_participation * selected_share, "issuance_status": "unissued"}


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, list):
        return [exact_json(x) for x in value]
    if isinstance(value, dict):
        return {k: exact_json(x) for k, x in value.items()}
    return value
