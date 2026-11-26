"""Independent finite cross-contract current-entitlement transfer controls."""
from datetime import date
from fractions import Fraction
import re


POLICY_ID = "SYNTHETIC-CONTRACT-TRANSFERS-01"
SCOPE_FIELDS = {"agreement_id", "participant_id", "pool_id", "currency"}
MAX_ACCOUNTS = 16
MAX_EDGES = 64
MAX_ENTITLEMENTS = 256


class TransferOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise TransferOracleError(code)


def _fields(value, required, optional=()):
    _need(type(value) is dict and required <= value.keys() and value.keys() <= required | set(optional), "TRANSFER_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "TRANSFER_IDENTITY_REQUIRED")
    return value


def _upstream(value):
    _text(value)
    artifact, separator, line = value.rpartition("#")
    _need(bool(separator and artifact and line), "TRANSFER_UPSTREAM_LINE_REFERENCE")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "TRANSFER_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "TRANSFER_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise TransferOracleError("TRANSFER_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "TRANSFER_PERIOD")
    return start, end


def _instant(value):
    _need(type(value) is str, "TRANSFER_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "TRANSFER_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "TRANSFER_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "TRANSFER_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "TRANSFER_INSTANT")
    return result


def _index(rows, field="id"):
    _need(type(rows) is list, "TRANSFER_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row[field])
        _need(identity not in result, "TRANSFER_DUPLICATE_ID")
        result[identity] = row
    return result


def _scope(value):
    _fields(value, SCOPE_FIELDS)
    for item in value.values():
        _text(item)
    _need(value["currency"] == "USD", "TRANSFER_CURRENCY")


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "coordinator", "period", "as_of", "cutoff", "policy", "accounts",
                   "entitlements", "authorizations", "transfers", "evidence", "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "transfers-neutral/1", "TRANSFER_NEUTRAL_SCHEMA")
    case_id = _text(data["case_id"])
    coordinator, opening = data["coordinator"], data["opening_state"]
    _fields(coordinator, {"id", "currency", "purpose"})
    _text(coordinator["id"])
    _need(coordinator["currency"] == "USD", "TRANSFER_CURRENCY")
    _need(coordinator["purpose"] == "current_entitlement_transfers", "TRANSFER_COORDINATOR_PURPOSE")
    _need(data["policy"] == {"id": POLICY_ID, "revision": "1", "measure": "current_period_entitlement",
                            "execution": "topological_then_authorized_sequence", "edge_limit": "one_transaction_per_authorization",
                            "rounding": "exact_no_rounding", "evidence_class": "research_assumption"}, "TRANSFER_SELECTED_POLICY")
    start, end = _period(data["period"])
    as_of, cutoff = _day(data["as_of"]), _instant(data["cutoff"])
    accounts = _index(data["accounts"])
    authorizations, transfers, entitlements = (_index(data[key]) for key in ("authorizations", "transfers", "entitlements"))
    _need(1 <= len(accounts) <= MAX_ACCOUNTS and len(authorizations) <= MAX_EDGES
          and len(transfers) <= MAX_EDGES and len(entitlements) <= MAX_ENTITLEMENTS, "TRANSFER_RESOURCE_BOUND")
    economic_scopes = set()
    for row in accounts.values():
        _fields(row, {"id", "scope", "source_ref", "evidence_ref"})
        _scope(row["scope"])
        key = tuple(row["scope"][name] for name in sorted(SCOPE_FIELDS))
        _need(key not in economic_scopes, "TRANSFER_DUPLICATE_ECONOMIC_ACCOUNT")
        economic_scopes.add(key)
        _text(row["source_ref"])
    account_scopes = [{"id": key, "scope": dict(accounts[key]["scope"])} for key in sorted(accounts)]
    _fields(opening, {"coordinator_id", "account_scopes", "purpose", "policy_id", "policy_revision", "boundary", "origin", "source_case_id",
                      "consumed_transfer_ids", "consumed_entitlement_ids", "consumed_authorization_ids", "consumed_upstream_refs", "last_period"})
    _need(opening["coordinator_id"] == coordinator["id"] and opening["purpose"] == coordinator["purpose"]
          and sorted(opening["account_scopes"], key=lambda row: row["id"]) == account_scopes, "TRANSFER_OPENING_SCOPE")
    _need((opening["policy_id"], opening["policy_revision"]) == (POLICY_ID, "1"), "TRANSFER_OPENING_POLICY")
    _need(opening["boundary"] == data["period"]["start"], "TRANSFER_OPENING_BOUNDARY")
    consumed = {}
    for key in ("consumed_transfer_ids", "consumed_entitlement_ids", "consumed_authorization_ids", "consumed_upstream_refs"):
        values = opening[key]
        _need(type(values) is list and all(type(value) is str and value for value in values)
              and len(set(values)) == len(values), "TRANSFER_CONSUMED_HISTORY")
        consumed[key] = set(values)
    for reference in consumed["consumed_upstream_refs"]:
        _upstream(reference)
    if opening["origin"] == "genesis":
        _need(not any(consumed.values()) and opening["last_period"] == [] and opening["source_case_id"] == "genesis"
              and "prior_result" not in data, "TRANSFER_GENESIS")
    else:
        _need(opening["origin"] == "prior_result" and "prior_result" in data, "TRANSFER_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if "result_ref" in prior:
            _text(prior["result_ref"])
        _, previous_end = _period(prior["period"])
        _need(previous_end == start, "TRANSFER_PREDECESSOR_BOUNDARY")
        _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id
              and prior["closing_state"] == opening, "TRANSFER_PREDECESSOR_MISMATCH")
        _need(type(opening["last_period"]) is list and len(opening["last_period"]) == 1, "TRANSFER_PRIOR_AUDIT")
        last = opening["last_period"][0]
        _fields(last, {"source_case_id", "period", "accounts", "entitlement_facts", "applied_transfers"})
        _need(last["source_case_id"] == prior["source_case_id"] and last["period"] == prior["period"], "TRANSFER_PRIOR_AUDIT")
        old_accounts = _index(last["accounts"], "account_id")
        _need(set(old_accounts) == set(accounts), "TRANSFER_PRIOR_AUDIT")
        old_original, old_final = Fraction(), Fraction()
        for identity, row in old_accounts.items():
            _need(row["scope"] == accounts[identity]["scope"], "TRANSFER_PRIOR_AUDIT")
            original, incoming, outgoing, final = (_q(row[name]) for name in ("original_entitlement", "received_credit", "transferred_out", "final_entitlement"))
            _need(final == original + incoming - outgoing, "TRANSFER_PRIOR_AUDIT")
            old_original += original
            old_final += final
        _need(old_original == old_final, "TRANSFER_PRIOR_AUDIT")
        _need(all(row["id"] in consumed["consumed_transfer_ids"] for row in last["applied_transfers"])
              and all(row["id"] in consumed["consumed_entitlement_ids"] and row["upstream_result_ref"] in consumed["consumed_upstream_refs"]
                      for row in last["entitlement_facts"]), "TRANSFER_PRIOR_AUDIT")
    _need(not (set(transfers) & consumed["consumed_transfer_ids"]), "TRANSFER_ALREADY_CONSUMED")
    _need(not (set(entitlements) & consumed["consumed_entitlement_ids"]), "TRANSFER_ENTITLEMENT_ALREADY_CONSUMED")
    _need(not (set(authorizations) & consumed["consumed_authorization_ids"]), "TRANSFER_AUTHORIZATION_ALREADY_CONSUMED")
    evidence = _index(data["evidence"])
    for row in evidence.values():
        _fields(row, {"id", "coordinator_id", "account_ids", "observed_at", "kind"})
        _need(row["coordinator_id"] == coordinator["id"] and type(row["account_ids"]) is list
              and set(row["account_ids"]) <= set(accounts) and len(set(row["account_ids"])) == len(row["account_ids"]), "TRANSFER_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "TRANSFER_EVIDENCE_CUTOFF")

    def supported(reference, covered):
        _need(reference in evidence and set(covered) <= set(evidence[reference]["account_ids"]), "TRANSFER_EVIDENCE_REQUIRED")

    for identity, row in accounts.items():
        supported(row["evidence_ref"], [identity])

    def observed(row, covered):
        _text(row["source_ref"])
        _need(_instant(row["observed_at"]) < cutoff, "TRANSFER_FACT_CUTOFF")
        supported(row["evidence_ref"], covered)

    original = {identity: Fraction() for identity in accounts}
    upstream_refs, source_views = set(), set()
    for row in entitlements.values():
        _fields(row, {"id", "account_id", "scope", "amount", "effective_date", "observed_at", "source_ref", "upstream_result_ref", "evidence_ref"})
        account = row["account_id"]
        _need(account in accounts and row["scope"] == accounts[account]["scope"], "TRANSFER_ENTITLEMENT_SCOPE")
        observed(row, [account])
        _need(start <= _day(row["effective_date"]) < end, "TRANSFER_ENTITLEMENT_PERIOD")
        reference = _upstream(row["upstream_result_ref"])
        _need(reference not in upstream_refs and reference not in consumed["consumed_upstream_refs"], "TRANSFER_UPSTREAM_ALREADY_CONSUMED")
        upstream_refs.add(reference)
        view = (account, row["source_ref"])
        _need(view not in source_views, "TRANSFER_DUPLICATE_SOURCE_VIEW")
        source_views.add(view)
        original[account] += _q(row["amount"])

    def endpoints(row):
        source, target = row["source_account"], row["target_account"]
        _need(source in accounts and target in accounts, "TRANSFER_UNKNOWN_ACCOUNT")
        _need(source != target, "TRANSFER_SELF_EDGE")
        _need(row["source_scope"] == accounts[source]["scope"] and row["target_scope"] == accounts[target]["scope"], "TRANSFER_ENDPOINT_SCOPE")
        _need(row["source_scope"]["currency"] == row["target_scope"]["currency"] == "USD", "TRANSFER_CURRENCY")
        _need(row["source_scope"]["agreement_id"] != row["target_scope"]["agreement_id"], "TRANSFER_CROSS_AGREEMENT_REQUIRED")
        return source, target

    sequences, graph = set(), {identity: set() for identity in accounts}
    for row in authorizations.values():
        _fields(row, {"id", "source_account", "target_account", "source_scope", "target_scope", "effective", "approved", "approved_date",
                      "recorded_date", "observed_at", "sequence", "maximum_amount", "source_ref", "evidence_ref"})
        source, target = endpoints(row)
        observed(row, [source, target])
        _need(row["effective"] == data["period"], "TRANSFER_AUTHORIZATION_PERIOD")
        _need(row["approved"] is True and _day(row["approved_date"]) <= _day(row["recorded_date"]) <= as_of, "TRANSFER_AUTHORIZATION_ASOF")
        _q(row["maximum_amount"])
        sequence = row["sequence"]
        _need(type(sequence) is int and sequence >= 0 and sequence not in sequences, "TRANSFER_AUTHORIZED_SEQUENCE")
        sequences.add(sequence)
        graph[source].add(target)
    incoming_nodes = {identity: sum(identity in targets for targets in graph.values()) for identity in accounts}
    remaining, topology = set(accounts), []
    while remaining:
        choices = sorted(identity for identity in remaining if incoming_nodes[identity] == 0)
        _need(bool(choices), "TRANSFER_GRAPH_CYCLE")
        selected = choices[0]
        remaining.remove(selected)
        topology.append(selected)
        for target in graph[selected]:
            incoming_nodes[target] -= 1
    by_source, used_authorizations = {identity: [] for identity in accounts}, set()
    for row in transfers.values():
        _fields(row, {"id", "authorization_id", "source_account", "target_account", "source_scope", "target_scope", "amount",
                      "recognition_date", "observed_at", "source_ref", "evidence_ref"})
        source, target = endpoints(row)
        observed(row, [source, target])
        identity = row["authorization_id"]
        _need(identity in authorizations and identity not in used_authorizations, "TRANSFER_AUTHORIZATION_REFERENCE_OR_REUSE")
        used_authorizations.add(identity)
        auth = authorizations[identity]
        _need(all(row[key] == auth[key] for key in ("source_account", "target_account", "source_scope", "target_scope")), "TRANSFER_AUTHORIZATION_ENDPOINTS")
        _need(start <= _day(row["recognition_date"]) < end, "TRANSFER_RECOGNITION_PERIOD")
        _need(_instant(auth["observed_at"]) <= _instant(row["observed_at"]), "TRANSFER_OBSERVATION_ORDER")
        amount = _q(row["amount"])
        _need(amount > 0 and amount <= _q(auth["maximum_amount"]), "TRANSFER_AUTHORIZED_AMOUNT")
        by_source[source].append(row)
    available = dict(original)
    received, outgoing = dict.fromkeys(accounts, Fraction()), dict.fromkeys(accounts, Fraction())
    applied = []
    for source in topology:
        for row in sorted(by_source[source], key=lambda transfer: authorizations[transfer["authorization_id"]]["sequence"]):
            target, amount = row["target_account"], _q(row["amount"])
            auth = authorizations[row["authorization_id"]]
            before_source, before_target = available[source], available[target]
            _need(amount <= before_source, "TRANSFER_SOURCE_OVERDRAW")
            available[source] -= amount
            available[target] += amount
            outgoing[source] += amount
            received[target] += amount
            applied.append({**row, "amount": amount, "sequence": auth["sequence"], "source_before": before_source,
                            "source_after": available[source], "target_before": before_target, "target_after": available[target],
                            "authorization_source_ref": auth["source_ref"]})
    results = []
    for identity in sorted(accounts):
        _need(available[identity] == original[identity] + received[identity] - outgoing[identity] and available[identity] >= 0, "TRANSFER_ACCOUNT_CONSERVATION")
        results.append({"account_id": identity, "scope": dict(accounts[identity]["scope"]), "original_entitlement": original[identity],
                        "received_credit": received[identity], "transferred_out": outgoing[identity], "final_entitlement": available[identity],
                        "source_ref": accounts[identity]["source_ref"], "evidence_ref": accounts[identity]["evidence_ref"]})
    total_original, total_final = sum(original.values(), Fraction()), sum(available.values(), Fraction())
    _need(total_original == total_final and sum(received.values(), Fraction()) == sum(outgoing.values(), Fraction()), "TRANSFER_GLOBAL_CONSERVATION")
    closing = {"coordinator_id": coordinator["id"], "account_scopes": account_scopes, "purpose": coordinator["purpose"],
               "policy_id": POLICY_ID, "policy_revision": "1", "boundary": data["period"]["end"], "origin": "prior_result", "source_case_id": case_id,
               "consumed_transfer_ids": sorted(consumed["consumed_transfer_ids"] | set(transfers)),
               "consumed_entitlement_ids": sorted(consumed["consumed_entitlement_ids"] | set(entitlements)),
               "consumed_authorization_ids": sorted(consumed["consumed_authorization_ids"] | set(authorizations)),
               "consumed_upstream_refs": sorted(consumed["consumed_upstream_refs"] | upstream_refs),
               "last_period": [{"source_case_id": case_id, "period": dict(data["period"]), "accounts": results,
                                "entitlement_facts": [dict(entitlements[key]) for key in sorted(entitlements)], "applied_transfers": applied}]}
    return {"source_case_id": case_id, "period": dict(data["period"]), "coordinator_id": coordinator["id"], "topological_accounts": topology,
            "accounts": results, "transfers": applied, "original_entitlement_total": total_original, "final_entitlement_total": total_final,
            "transferred_total": sum(outgoing.values(), Fraction()), "external_cash_added": Fraction(), "closing_state": closing,
            "status_meaning": "calculated cross-contract entitlement redistribution; no bank or issuance evidence inferred"}


def contract_transfers(data):
    """Return exact coordinated controls, or fail with no partial successor state."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, TransferOracleError):
            raise
        raise TransferOracleError("TRANSFER_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
