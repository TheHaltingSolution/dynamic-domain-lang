"""Independent finite cent allocation from original parents and approved terms."""
from datetime import date
from fractions import Fraction
import re


POLICY_ID = "SYNTHETIC-QUANTIZED-ALLOCATION-01"
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}
ARRAYS = ("parents", "authorities", "supplied_allocations")
LIMITS = {"recipients": 8, "parents_per_period": 4, "historical_periods": 8}


class QuantizedAllocationOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise QuantizedAllocationOracleError(code)


def _fields(row, keys, optional=()):
    _need(type(row) is dict and keys <= row.keys() <= keys | set(optional), "QA_RECORD_FIELDS")


def _id(value):
    _need(type(value) is str and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}", value), "QA_ASCII_ID")
    return value


def _text(value):
    _need(type(value) is str and bool(value), "QA_SOURCE_REQUIRED")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "QA_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "QA_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise QuantizedAllocationOracleError("QA_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "QA_PERIOD")
    return start, end


def _instant(value):
    _need(type(value) is str, "QA_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "QA_INSTANT")
    day, hour, minute, second, part, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "QA_INSTANT")
    offset = 0
    if zone != "Z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "QA_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(part or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "QA_INSTANT")
    return result


def _index(rows):
    _need(type(rows) is list, "QA_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _id(row["id"])
        _need(identity not in result, "QA_DUPLICATE_ID")
        result[identity] = row
    return result


def _ids(values):
    _need(type(values) is list, "QA_ID_LIST")
    result = [_id(value) for value in values]
    _need(len(set(result)) == len(result), "QA_DUPLICATE_RECIPIENT_OR_REFERENCE")
    return set(result)


def _half_even(value):
    lower = value.numerator // value.denominator
    remainder = value - lower
    return lower + (1 if remainder > Fraction(1, 2) or remainder == Fraction(1, 2) and lower % 2 else 0)


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "period", "as_of", "cutoff", "policy", "recipient_registry", *ARRAYS, "evidence", "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "quantized-allocation-neutral/1", "QA_SCHEMA")
    case_id, scope, policy, opening = _id(data["case_id"]), data["scope"], data["policy"], data["opening_state"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _id(value)
    _need(scope["currency"] == "USD", "QA_CURRENCY")
    _fields(policy, {"id", "revision", "method", "parent_rounding", "quota_basis", "residual_order", "evidence_class", "limits"})
    method = policy["method"]
    _need(method in ("exact_weights_largest_remainder", "authorized_supplied_cents"), "QA_METHOD")
    _need({key: value for key, value in policy.items() if key != "method"} == {
        "id": POLICY_ID, "revision": "1", "parent_rounding": "half_even_once_to_cent", "quota_basis": "rounded_parent_target",
        "residual_order": "descending_remainder_then_ascii_recipient_id", "evidence_class": "research_assumption", "limits": LIMITS}, "QA_POLICY")
    start, end = _period(data["period"])
    cutoff = _instant(data["cutoff"])
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _fields(row, {"id", "scope", "kind", "observed_at"})
        _need(row["scope"] == scope, "QA_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "QA_EVIDENCE_CUTOFF")

    def support(row, before):
        _need(row["scope"] == scope, "QA_FACT_SCOPE")
        _text(row["source_ref"])
        _need(row["evidence_ref"] in evidence, "QA_EVIDENCE_REQUIRED")
        _need(_instant(row["observed_at"]) < before, "QA_FACT_CUTOFF")
        _need(_instant(evidence[row["evidence_ref"]]["observed_at"]) < before, "QA_EVIDENCE_CUTOFF")

    recipients = _index(data["recipient_registry"])
    _need(1 <= len(recipients) <= LIMITS["recipients"], "QA_RECIPIENT_BOUND")
    for row in recipients.values():
        _fields(row, {"id", "scope", "observed_at", "source_ref", "evidence_ref"})
        support(row, cutoff)
    _fields(opening, {"scope", "purpose", "policy", "recipient_registry", "boundary", "origin", "source_case_id", "consumed_parent_ids", "consumed_upstream_refs", "history"})
    _need(opening["scope"] == scope and opening["purpose"] == "quantized_parent_allocation", "QA_OPENING_SCOPE")
    registry = [recipients[key] for key in sorted(recipients)]
    _need(opening["policy"] == policy and sorted(opening["recipient_registry"], key=lambda row: row["id"]) == registry, "QA_PINNED_TERMS")
    _need(opening["boundary"] == data["period"]["start"], "QA_OPENING_BOUNDARY")
    history = opening["history"]
    _need(type(history) is list and len(history) <= LIMITS["historical_periods"], "QA_HISTORY_BOUND")
    if opening["origin"] == "genesis":
        _need(not history and opening["consumed_parent_ids"] == [] and opening["consumed_upstream_refs"] == []
              and opening["source_case_id"] == "genesis" and "prior_result" not in data, "QA_GENESIS")
    else:
        _need(opening["origin"] == "prior_result" and "prior_result" in data, "QA_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if "result_ref" in prior:
            _text(prior["result_ref"])
        _need(_period(prior["period"])[1] == start, "QA_PREDECESSOR_BOUNDARY")
        _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id and prior["closing_state"] == opening, "QA_PREDECESSOR_MISMATCH")
    used = {key: set() for key in ARRAYS}
    upstream_refs, parent_sources = set(), set()

    def process(record):
        period_start, period_end = _period(record["period"])
        before, as_of = _instant(record["cutoff"]), _day(record["as_of"])
        _need(before <= cutoff, "QA_HISTORY_CUTOFF")
        for row in recipients.values():
            support(row, before)
        parents, authorities, supplied = (_index(record[key]) for key in ARRAYS)
        _need(len(parents) <= LIMITS["parents_per_period"], "QA_PARENT_BOUND")
        _need(len(authorities) == len(parents), "QA_AUTHORITY_CARDINALITY")
        _need(len(supplied) <= LIMITS["parents_per_period"] * LIMITS["recipients"], "QA_ALLOCATION_BOUND")
        for key, rows in zip(ARRAYS, (parents, authorities, supplied)):
            _need(not (set(rows) & used[key]), "QA_ALREADY_CONSUMED_ID")
            used[key].update(rows)
        referenced, referenced_supplied, output = set(), set(), []
        for row in supplied.values():
            _fields(row, {"id", "parent_id", "recipient_id", "scope", "amount", "observed_at", "source_ref", "evidence_ref"})
            support(row, before)
            _need(row["parent_id"] in parents and row["recipient_id"] in recipients, "QA_SUPPLIED_REFERENCE")
        for parent in sorted(parents.values(), key=lambda row: row["id"]):
            _fields(parent, {"id", "scope", "amount", "effective_date", "observed_at", "source_ref", "upstream_ref", "evidence_ref", "authority_id"})
            support(parent, before)
            _need(period_start <= _day(parent["effective_date"]) < period_end, "QA_PARENT_PERIOD")
            reference = _text(parent["upstream_ref"])
            prefix, marker, line = reference.rpartition("#")
            _need(bool(prefix and marker and line), "QA_ORIGINAL_PARENT_LINE")
            _need(reference not in upstream_refs and parent["source_ref"] not in parent_sources, "QA_PARENT_SOURCE_ALREADY_CONSUMED")
            upstream_refs.add(reference); parent_sources.add(parent["source_ref"])
            amount = _q(parent["amount"])
            target_cents = _half_even(amount * 100)
            target = Fraction(target_cents, 100)
            identity = parent["authority_id"]
            _need(identity in authorities and identity not in referenced, "QA_PARENT_AUTHORITY_REQUIRED")
            referenced.add(identity)
            authority = authorities[identity]
            _fields(authority, {"id", "parent_id", "parent_upstream_ref", "scope", "method", "effective", "approved", "approved_date", "recorded_date", "observed_at", "recipient_ids", "terms", "supplied_allocation_ids", "residual_order", "source_ref", "evidence_ref"})
            support(authority, before)
            _need(authority["parent_id"] == parent["id"] and authority["parent_upstream_ref"] == reference, "QA_AUTHORITY_PARENT_SCOPE")
            _need(authority["method"] == method and authority["residual_order"] == policy["residual_order"], "QA_AUTHORITY_METHOD")
            _need(authority["effective"] == record["period"] and authority["approved"] is True
                  and _day(authority["approved_date"]) <= _day(authority["recorded_date"]) <= as_of, "QA_AUTHORITY_ASOF")
            approved = _ids(authority["recipient_ids"])
            _need(approved == set(recipients), "QA_COMPLETE_RECIPIENTS")
            terms = _index(authority["terms"])
            _need(len(terms) == len(approved), "QA_COMPLETE_WEIGHT_TERMS")
            weights = {}
            for term in terms.values():
                _fields(term, {"id", "recipient_id", "scope", "weight", "observed_at", "source_ref", "evidence_ref"})
                support(term, before)
                recipient = term["recipient_id"]
                _need(recipient in approved and recipient not in weights, "QA_WEIGHT_RECIPIENT_REFERENCE")
                weights[recipient] = _q(term["weight"])
            _need(set(weights) == approved, "QA_COMPLETE_WEIGHT_TERMS")
            denominator = sum(weights.values(), Fraction())
            _need(denominator > 0, "QA_ZERO_WEIGHT_DENOMINATOR")
            quotas = {recipient: Fraction(target_cents) * weight / denominator for recipient, weight in weights.items()}
            bases = {recipient: quota.numerator // quota.denominator for recipient, quota in quotas.items()}
            remainders = {recipient: quota - bases[recipient] for recipient, quota in quotas.items()}
            residual = target_cents - sum(bases.values())
            _need(0 <= residual < len(weights), "QA_RESIDUAL_BOUND")
            order = sorted(weights, key=lambda recipient: (-remainders[recipient], recipient))
            ranks = {recipient: rank for rank, recipient in enumerate(order, 1)}
            weighted = {recipient: Fraction(bases[recipient] + (ranks[recipient] <= residual), 100) for recipient in weights}
            selected = weighted
            allocation_ids = _ids(authority["supplied_allocation_ids"])
            if method == "exact_weights_largest_remainder":
                _need(not allocation_ids, "QA_UNEXPECTED_SUPPLIED_ALLOCATIONS")
            else:
                _need(all(identity in supplied for identity in allocation_ids) and len(allocation_ids) == len(weights), "QA_COMPLETE_SUPPLIED_ALLOCATIONS")
                selected = {}
                for allocation_id in allocation_ids:
                    row = supplied[allocation_id]
                    _need(row["parent_id"] == parent["id"] and row["recipient_id"] not in selected, "QA_SUPPLIED_RECIPIENT_REFERENCE")
                    value = _q(row["amount"])
                    _need((value * 100).denominator == 1, "QA_SUPPLIED_MINOR_UNIT")
                    selected[row["recipient_id"]] = value
                _need(set(selected) == approved and sum(selected.values(), Fraction()) == target, "QA_SUPPLIED_TARGET_CONSERVATION")
                referenced_supplied.update(allocation_ids)
            children = [{"parent_id": parent["id"], "parent_upstream_ref": reference, "recipient_id": recipient,
                         "weight": weights[recipient], "weight_denominator": denominator,
                         "original_parent_exact_quota": amount * weights[recipient] / denominator,
                         "target_exact_share": quotas[recipient] / 100, "floor_base_cents": bases[recipient],
                         "fractional_cent_remainder": remainders[recipient], "rank": ranks[recipient],
                         "weighted_residual_cent": 1 if ranks[recipient] <= residual else 0,
                         "weighted_amount": weighted[recipient], "selected_amount": selected[recipient]}
                        for recipient in sorted(weights)]
            child_total = sum(selected.values(), Fraction())
            _need(child_total == target, "QA_CHILD_CONSERVATION")
            output.append({"parent_id": parent["id"], "parent_upstream_ref": reference, "authority_id": identity,
                           "original_parent_amount": amount, "target_cents": target_cents, "rounded_target": target,
                           "parent_rounding_delta": target - amount, "weight_denominator": denominator,
                           "base_cents_total": sum(bases.values()), "residual_cents": residual,
                           "ranked_recipient_ids": order, "children": children, "child_total": child_total})
        _need(referenced == set(authorities), "QA_UNUSED_AUTHORITY")
        _need(referenced_supplied == set(supplied), "QA_UNMATCHED_SUPPLIED_ALLOCATION")
        return output

    previous_end, normalized, used_cases = None, [], {case_id}
    for record in sorted(history, key=lambda row: row["period"]["start"]):
        _fields(record, {"source_case_id", "period", "as_of", "cutoff", *ARRAYS})
        identity = _id(record["source_case_id"])
        _need(identity not in used_cases, "QA_DUPLICATE_HISTORY_CASE")
        used_cases.add(identity)
        past_start, past_end = _period(record["period"])
        _need(past_end <= start and (previous_end is None or previous_end == past_start), "QA_HISTORY_BOUNDARY")
        process(record)
        previous_end = past_end
        normalized.append(record)
    _need(opening["consumed_parent_ids"] == sorted(used["parents"]) and opening["consumed_upstream_refs"] == sorted(upstream_refs)
          and (not history or previous_end == start and normalized[-1]["source_case_id"] == opening["source_case_id"]), "QA_OPENING_HISTORY_RECONCILIATION")
    current = {"source_case_id": case_id, "period": dict(data["period"]), "as_of": data["as_of"], "cutoff": data["cutoff"],
               **{key: sorted(data[key], key=lambda row: row["id"]) for key in ARRAYS}}
    current["authorities"] = [{**row, "recipient_ids": sorted(row["recipient_ids"]), "terms": sorted(row["terms"], key=lambda term: term["id"]),
                               "supplied_allocation_ids": sorted(row["supplied_allocation_ids"])} for row in current["authorities"]]
    output = process(current)
    closing = {"scope": dict(scope), "purpose": "quantized_parent_allocation", "policy": dict(policy), "recipient_registry": registry,
               "boundary": data["period"]["end"], "origin": "prior_result", "source_case_id": case_id,
               "consumed_parent_ids": sorted(used["parents"]), "consumed_upstream_refs": sorted(upstream_refs), "history": normalized + [current]}
    original_total = sum((row["original_parent_amount"] for row in output), Fraction())
    target_total = sum((row["rounded_target"] for row in output), Fraction())
    return {"source_case_id": case_id, "period": dict(data["period"]), "method": method, "allocations": output,
            "original_parent_total": original_total, "rounded_target_total": target_total,
            "child_allocation_total": sum((row["child_total"] for row in output), Fraction()),
            "parent_rounding_delta_total": target_total - original_total, "parent_count": len(output),
            "recognized_amount_space": "selected_children_only", "payment_status": "not_a_payment_measure", "closing_state": closing}


def quantized_allocation(data):
    """Calculate exact controls; original sources contain no solved ranks or shares."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, QuantizedAllocationOracleError):
            raise
        raise QuantizedAllocationOracleError("QA_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [exact_json(item) for item in value]
    return value
