"""Independent original-measurement return and explicitly selected loss controls."""
from datetime import date
from fractions import Fraction
import re


POLICY_ID = "SYNTHETIC-RETURNS-LOSSES-01"
METHODS = {"signed_pool", "per_title_floor", "pooled_loss_carry"}
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "currency"}
ORIGINAL_FIELDS = {"id", "asset_id", "scope", "basis", "rate", "measurement_date", "observed_at", "source_ref", "evidence_ref"}


class ReturnsOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise ReturnsOracleError(code)


def _fields(value, required, optional=()):
    _need(type(value) is dict and required <= value.keys() and value.keys() <= required | set(optional), "RETURNS_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "RETURNS_IDENTITY_REQUIRED")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "RETURNS_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _rate(value):
    result = _q(value)
    _need(result <= 1, "RETURNS_RATE_DOMAIN")
    return result


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "RETURNS_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ReturnsOracleError("RETURNS_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "RETURNS_PERIOD")
    return start, end


def _instant(value):
    _need(type(value) is str, "RETURNS_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "RETURNS_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "RETURNS_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "RETURNS_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "RETURNS_INSTANT")
    return result


def _index(rows, field="id"):
    _need(type(rows) is list, "RETURNS_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row[field])
        _need(identity not in result, "RETURNS_DUPLICATE_ID")
        result[identity] = row
    return result


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "asset_ids", "period", "cutoff", "policy", "current_rates",
                   "originals", "sales", "returns", "evidence", "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "returns-neutral/1", "RETURNS_NEUTRAL_SCHEMA")
    case_id, scope, policy, opening = _text(data["case_id"]), data["scope"], data["policy"], data["opening_state"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "RETURNS_CURRENCY")
    assets = data["asset_ids"]
    _need(type(assets) is list and assets and all(type(value) is str and value for value in assets)
          and len(set(assets)) == len(assets), "RETURNS_ASSET_UNIVERSE")
    start, end = _period(data["period"])
    cutoff = _instant(data["cutoff"])
    _fields(policy, {"id", "revision", "method", "recognition", "measurement", "rounding", "evidence_class"})
    method = policy["method"]
    _need(method in METHODS, "RETURNS_METHOD_REQUIRED")
    _need((policy["id"], policy["revision"], policy["recognition"], policy["measurement"], policy["rounding"], policy["evidence_class"])
          == (POLICY_ID, "1", "supplied_current_period", "original_basis_original_rate", "exact_no_rounding", "research_assumption"), "RETURNS_SELECTED_POLICY")
    state_fields = {"scope", "asset_ids", "purpose", "policy_id", "policy_revision", "method", "boundary", "origin", "source_case_id",
                    "loss_carry", "original_registry", "recognized_ids"}
    _fields(opening, state_fields)
    _need(opening["scope"] == scope and opening["purpose"] == "returns_and_loss"
          and type(opening["asset_ids"]) is list and set(opening["asset_ids"]) == set(assets)
          and len(opening["asset_ids"]) == len(assets), "RETURNS_OPENING_SCOPE")
    _need((opening["policy_id"], opening["policy_revision"], opening["method"]) == (POLICY_ID, "1", method), "RETURNS_OPENING_METHOD")
    _need(opening["boundary"] == data["period"]["start"], "RETURNS_OPENING_BOUNDARY")
    loss = _q(opening["loss_carry"])
    _need(method == "pooled_loss_carry" or loss == 0, "RETURNS_LOSS_OUTSIDE_METHOD")
    recognized = opening["recognized_ids"]
    _need(type(recognized) is list and all(type(value) is str and re.fullmatch(r"(?:originals|sales|returns):.+", value) for value in recognized)
          and len(set(recognized)) == len(recognized), "RETURNS_RECOGNIZED_HISTORY")
    if opening["origin"] == "genesis":
        _need(loss == 0 and opening["original_registry"] == [] and not recognized and opening["source_case_id"] == "genesis"
              and "prior_result" not in data, "RETURNS_GENESIS")
    else:
        _need(opening["origin"] == "prior_result" and "prior_result" in data, "RETURNS_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if "result_ref" in prior:
            _text(prior["result_ref"])
        _, previous_end = _period(prior["period"])
        _need(previous_end == start, "RETURNS_PREDECESSOR_BOUNDARY")
        _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id
              and prior["closing_state"] == opening, "RETURNS_PREDECESSOR_MISMATCH")
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _fields(row, {"id", "scope", "observed_at", "kind"})
        _need(row["scope"] == scope, "RETURNS_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "RETURNS_EVIDENCE_CUTOFF")

    def fact(row):
        _need(row["scope"] == scope and row["asset_id"] in assets, "RETURNS_FACT_SCOPE")
        _need(row["evidence_ref"] in evidence, "RETURNS_FACT_EVIDENCE")
        _text(row["source_ref"])
        _need(_instant(row["observed_at"]) < cutoff, "RETURNS_FACT_CUTOFF")

    rates = _index(data["current_rates"], "asset_id")
    _need(set(rates) == set(assets), "RETURNS_CURRENT_RATE_COVERAGE")
    for row in rates.values():
        _fields(row, {"asset_id", "rate", "scope", "effective", "observed_at", "source_ref", "evidence_ref"})
        fact(row)
        rate_start, rate_end = _period(row["effective"])
        _need(rate_start <= start and end <= rate_end, "RETURNS_CURRENT_RATE_PERIOD")
        _rate(row["rate"])

    registry = {}
    for identity, row in _index(opening["original_registry"]).items():
        _fields(row, ORIGINAL_FIELDS | {"returned_basis", "origin_kind", "registered_case_id"})
        fact(row)
        basis, returned = _q(row["basis"]), _q(row["returned_basis"])
        _rate(row["rate"])
        _need(_day(row["measurement_date"]) < start, "RETURNS_CARRIED_ORIGINAL_DATE")
        _need(returned <= basis, "RETURNS_ORIGINAL_METER")
        _text(row["registered_case_id"])
        _need(row["origin_kind"] in ("historical_import", "current_sale"), "RETURNS_ORIGINAL_PROVENANCE")
        token = ("originals:" if row["origin_kind"] == "historical_import" else "sales:") + identity
        _need(token in recognized, "RETURNS_ORIGINAL_PROVENANCE")
        registry[identity] = {**row, "basis": basis, "rate": _rate(row["rate"]), "returned_basis": returned}
    originals, sales, returns = (_index(data[key]) for key in ("originals", "sales", "returns"))
    _need(not (set(originals) & set(sales)) and not ((set(originals) | set(sales)) & set(registry)), "RETURNS_ORIGINAL_ALREADY_REGISTERED")
    new_tokens = {"originals:" + key for key in originals} | {"sales:" + key for key in sales} | {"returns:" + key for key in returns}
    _need(not (new_tokens & set(recognized)), "RETURNS_ALREADY_RECOGNIZED")
    for identity, row in originals.items():
        _fields(row, ORIGINAL_FIELDS)
        fact(row)
        _need(_day(row["measurement_date"]) < start, "RETURNS_HISTORICAL_ORIGINAL_DATE")
        registry[identity] = {**row, "basis": _q(row["basis"]), "rate": _rate(row["rate"]),
                              "returned_basis": Fraction(), "origin_kind": "historical_import", "registered_case_id": case_id}
    current_earned = {asset: Fraction() for asset in assets}
    current_basis = {asset: Fraction() for asset in assets}
    sale_lines = []
    for identity, row in sorted(sales.items()):
        _fields(row, {"id", "asset_id", "scope", "basis", "effective_date", "observed_at", "source_ref", "evidence_ref"})
        fact(row)
        _need(start <= _day(row["effective_date"]) < end, "RETURNS_SALE_PERIOD")
        basis, rate = _q(row["basis"]), _rate(rates[row["asset_id"]]["rate"])
        earned = basis * rate
        current_basis[row["asset_id"]] += basis
        current_earned[row["asset_id"]] += earned
        registry[identity] = {key: value for key, value in row.items() if key != "effective_date"}
        registry[identity].update(measurement_date=row["effective_date"], basis=basis, rate=rate, returned_basis=Fraction(),
                                  origin_kind="current_sale", registered_case_id=case_id)
        sale_lines.append({"id": identity, "asset_id": row["asset_id"], "basis": basis, "current_rate": rate, "earned": earned,
                           "source_ref": row["source_ref"], "evidence_ref": row["evidence_ref"]})
    reversed_earned = {asset: Fraction() for asset in assets}
    returned_basis = {asset: Fraction() for asset in assets}
    by_original = {identity: Fraction() for identity in registry}
    return_lines = []
    for identity, row in sorted(returns.items()):
        _fields(row, {"id", "original_id", "asset_id", "scope", "returned_basis", "return_date", "recognition_date", "observed_at", "source_ref", "evidence_ref"})
        fact(row)
        _need(row["original_id"] in registry, "RETURNS_ORIGINAL_REQUIRED")
        original = registry[row["original_id"]]
        _need(row["asset_id"] == original["asset_id"] and row["scope"] == original["scope"], "RETURNS_ORIGINAL_SCOPE")
        recognition = _day(row["recognition_date"])
        _need(start <= recognition < end, "RETURNS_RECOGNITION_PERIOD")
        _need(_day(original["measurement_date"]) <= _day(row["return_date"]) <= recognition, "RETURNS_DATE_ORDER")
        _need(_instant(original["observed_at"]) <= _instant(row["observed_at"]), "RETURNS_OBSERVATION_ORDER")
        magnitude = _q(row["returned_basis"])
        by_original[row["original_id"]] += magnitude
        effect_magnitude = magnitude * original["rate"]
        returned_basis[row["asset_id"]] += magnitude
        reversed_earned[row["asset_id"]] += effect_magnitude
        return_lines.append({"id": identity, "original_id": row["original_id"], "asset_id": row["asset_id"],
                             "original_basis": original["basis"], "original_rate": original["rate"], "returned_basis": magnitude,
                             "original_measurement_date": original["measurement_date"], "recognition_date": row["recognition_date"],
                             "reversed_earned": effect_magnitude, "signed_effect": -effect_magnitude,
                             "original_source_ref": original["source_ref"], "original_evidence_ref": original["evidence_ref"],
                             "source_ref": row["source_ref"], "evidence_ref": row["evidence_ref"]})
    original_lines = []
    for identity, original in sorted(registry.items()):
        prior_returned, current_returned = original["returned_basis"], by_original[identity]
        cumulative = prior_returned + current_returned
        _need(cumulative <= original["basis"], "RETURNS_ORIGINAL_OVERRETURN")
        original_lines.append({"original_id": identity, "original_basis": original["basis"], "original_rate": original["rate"],
                               "opening_returned_basis": prior_returned, "current_returned_basis": current_returned,
                               "closing_returned_basis": cumulative, "remaining_basis": original["basis"] - cumulative,
                               "source_ref": original["source_ref"], "evidence_ref": original["evidence_ref"]})
        original["returned_basis"] = cumulative
    titles = [{"asset_id": asset, "current_rate": _rate(rates[asset]["rate"]), "current_basis": current_basis[asset],
               "current_earned": current_earned[asset], "returned_basis": returned_basis[asset], "reversed_earned": reversed_earned[asset],
               "signed_earned": current_earned[asset] - reversed_earned[asset],
               "floored_earned": max(current_earned[asset] - reversed_earned[asset], Fraction())} for asset in sorted(assets)]
    signed = sum((row["signed_earned"] for row in titles), Fraction())
    if method == "signed_pool":
        entitlement, closing_loss = signed, Fraction()
    elif method == "per_title_floor":
        entitlement, closing_loss = sum((row["floored_earned"] for row in titles), Fraction()), Fraction()
    else:
        entitlement, closing_loss = max(signed - loss, Fraction()), max(loss - signed, Fraction())
        _need(signed + closing_loss == entitlement + loss, "RETURNS_LOSS_RECONCILIATION")
    closing = {"scope": dict(scope), "asset_ids": sorted(assets), "purpose": "returns_and_loss", "policy_id": POLICY_ID,
               "policy_revision": "1", "method": method, "boundary": data["period"]["end"], "origin": "prior_result", "source_case_id": case_id,
               "loss_carry": closing_loss, "original_registry": [registry[key] for key in sorted(registry)],
               "recognized_ids": sorted(set(recognized) | new_tokens)}
    return {"source_case_id": case_id, "period": dict(data["period"]), "method": method, "titles": titles,
            "sales": sale_lines, "returns": return_lines, "originals": original_lines,
            "current_earned": sum(current_earned.values(), Fraction()), "reversed_earned": sum(reversed_earned.values(), Fraction()),
            "pool_signed_earned": signed, "recognized_entitlement": entitlement, "opening_loss": loss,
            "loss_applied": min(loss, max(signed, Fraction())) if method == "pooled_loss_carry" else Fraction(),
            "new_loss": max(-signed, Fraction()) if method == "pooled_loss_carry" else Fraction(),
            "closing_loss": closing_loss, "closing_state": closing,
            "status_meaning": "calculated_delta_or_earning_credit; no issuance, bank refund or actual payment inferred"}


def returns_losses(data):
    """Return exact linked-return/loss controls or reject without successor state."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, ReturnsOracleError):
            raise
        raise ReturnsOracleError("RETURNS_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
