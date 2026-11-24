"""Independent original-fact controls for the selected lg-cleared@1 policy.

Only standard-library code is used. The crossed-net amount and continuous gate
history are explicit supplied evidence, never reconstructed from payout facts.
This module does not read SPL, projected bindings, compiler codecs or evaluators.
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date
from fractions import Fraction
import re


POLICY = "lg-cleared@1"
PROFILE = "lg-cleared-v1"
REQUIRED_DECISIONS = {"LG-OUTSIDE-HURDLE", "LG-GATE-HISTORY", "LG-TRUE-CASH",
                      "LG-TRUE-CASH-COST", "LG-GROSS-VIDEO-PROXY", "LG-GROSS-BRANCH",
                      "LG-NET-BRANCH", "LG-GREATER-OF", "SYNTHETIC-PAYMENT-HOLDBACK"}


class LionsgateOracleError(ValueError):
    """A rejection has no payable, actual-paid number or consumable state."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _need(condition, code):
    if not condition:
        raise LionsgateOracleError(code)


def _fields(value, required, optional=()):
    _need(type(value) is dict and set(required) <= value.keys()
          and value.keys() <= set(required) | set(optional), "LG_ORACLE_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "LG_ORACLE_IDENTITY_REQUIRED")
    return value


def _q(value):
    if type(value) is str and re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value):
        return Fraction(value)
    if type(value) is dict and set(value) == {"numerator", "denominator"}:
        n, d = value["numerator"], value["denominator"]
        _need(type(n) is str and type(d) is str
              and re.fullmatch(r"-?(?:0|[1-9][0-9]*)", n)
              and re.fullmatch(r"[1-9][0-9]*", d), "LG_ORACLE_EXACT_NUMBER")
        result = Fraction(int(n), int(d))
        _need(str(result.numerator) == n and str(result.denominator) == d, "LG_ORACLE_REDUCED_RATIONAL")
        return result
    raise LionsgateOracleError("LG_ORACLE_EXACT_NUMBER")


def _nonnegative(value):
    result = _q(value)
    _need(result >= 0, "LG_ORACLE_NEGATIVE_AMOUNT")
    return result


def _money(value):
    _fields(value, {"value", "currency"})
    _need(value["currency"] == "USD", "LG_ORACLE_CURRENCY")
    return _nonnegative(value["value"])


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "LG_ORACLE_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise LionsgateOracleError("LG_ORACLE_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "LG_ORACLE_PERIOD")
    return start, end


def _covers(value, start, end):
    a, b = _period(value)
    return a <= start and b >= end


def _instant(value):
    _need(type(value) is str, "LG_ORACLE_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "LG_ORACLE_INSTANT")
    civil, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "LG_ORACLE_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "LG_ORACLE_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(civil).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset)
    result += Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "LG_ORACLE_INSTANT")
    return result


def _index(rows, field):
    _need(type(rows) is list, "LG_ORACLE_RECORD_LIST")
    result = {}
    for row in rows:
        _need(type(row) is dict, "LG_ORACLE_RECORD_FIELDS")
        key = _text(row[field])
        _need(key not in result, "LG_ORACLE_DUPLICATE_ID")
        result[key] = row
    return result


def _weights(rows):
    _need(type(rows) is list and bool(rows), "LG_ORACLE_ALLOCATION_AUTHORITY")
    result = {}
    for row in rows:
        _fields(row, {"asset_id", "weight"})
        target, weight = _text(row["asset_id"]), _nonnegative(row["weight"])
        _need(target not in result, "LG_ORACLE_DUPLICATE_ALLOCATION_TARGET")
        result[target] = weight
    _need(sum(result.values(), Fraction()) == 1, "LG_ORACLE_ALLOCATION_CONSERVATION")
    return result


def _calculate(data):
    _fields(data, {"schema_version", "policy_ref", "source_profile", "allocation_authorities", "package"})
    _need((data["schema_version"], data["policy_ref"], data["source_profile"])
          == ("lg-neutral/1", POLICY, PROFILE), "LG_ORACLE_PROFILE")
    p = data["package"]
    _fields(p, {"adapter", "agreements", "allocations", "assets", "evidence_events", "financial_facts",
                "incorporated_policies", "interpretations", "manifest", "mappings", "opening_aliases",
                "parameters", "parties", "profile", "references", "roles", "source_batches", "state_cells"})
    _need(p["profile"] == PROFILE, "LG_ORACLE_PROFILE")
    manifest, parameters = p["manifest"], p["parameters"]
    _fields(parameters, {"policy", "cost_date_basis", "cost_decisions", "producer_fee_offset",
                         "payment_holdback_addition", "payment_holdback_release"})
    policy = parameters["policy"]
    _fields(policy, {"agreement_id", "participant_id", "asset_id", "pool_id", "period", "video_proxy", "gross_rate", "net_rate"})
    agreement, participant, work, pool = (_text(policy[k]) for k in
                                         ["agreement_id", "participant_id", "asset_id", "pool_id"])
    start, end = _period(policy["period"])
    next_quarter = date(start.year + (start.month == 10), 1 if start.month == 10 else start.month + 3, 1) if start.month in {1, 4, 7, 10} else None
    _need(start.day == 1 and next_quarter == end, "LG_ORACLE_CALENDAR_QUARTER")
    _need(manifest["period"] == policy["period"] and manifest["output_currency"] == "USD"
          and manifest["input_mode"] == "full_snapshot", "LG_ORACLE_MANIFEST_SCOPE")
    cutoff, scenario = _instant(manifest["cutoff"]), _text(manifest["scenario_id"])
    _need(parameters["cost_date_basis"] == "incurred_date", "LG_ORACLE_COST_DATE_POLICY")
    proxy, gross_rate, net_rate = (_nonnegative(policy[k]) for k in ["video_proxy", "gross_rate", "net_rate"])
    producer_offset = _money(parameters["producer_fee_offset"])
    addition, release = (_money(parameters[k]) for k in ["payment_holdback_addition", "payment_holdback_release"])

    assets, parties = _index(p["assets"], "asset_id"), _index(p["parties"], "party_id")
    agreements = _index(p["agreements"], "agreement_id")
    _need(len(agreements) == 1 and agreement in agreements and work in assets and participant in parties
          and assets[work]["kind"] == "picture", "LG_ORACLE_AGREEMENT_SCOPE")
    agreement_row = agreements[agreement]
    _need(work in agreement_row["asset_ids"] and _covers(agreement_row["effective"], start, end), "LG_ORACLE_AGREEMENT_SCOPE")
    roles = _index(p["roles"], "role_id")
    selected_roles = [roles[identifier] for identifier in agreement_row["role_ids"]]
    _need(len({r["role_id"] for r in selected_roles}) == len(selected_roles)
          and all(r["agreement_id"] == agreement and r["party_id"] in parties
                  and _covers(r["effective"], start, end) for r in selected_roles), "LG_ORACLE_ROLE_SCOPE")
    _need(sum(r["role"] == "participant" and r["party_id"] == participant for r in selected_roles) == 1
          and sum(r["role"] == "distributor" for r in selected_roles) == 1, "LG_ORACLE_ROLE_SCOPE")
    references = _index(p["references"], "reference_id")
    _need(agreement_row["calendar_ref"] in references
          and references[agreement_row["calendar_ref"]]["kind"] == "calendar", "LG_ORACLE_CALENDAR_REFERENCE")
    decisions = {}
    interpretations = _index(p["interpretations"], "interpretation_id")
    selected_interpretations = [row for row in interpretations.values()
                               if row["interpretation_id"] + "@" + row["version"] == agreement_row["interpretation_ref"]]
    _need(len(selected_interpretations) == 1, "LG_ORACLE_INTERPRETATION_REFERENCE")
    for interpretation in selected_interpretations:
        for key, decision in _index(interpretation["decisions"], "decision_id").items():
            _need(key not in decisions, "LG_ORACLE_DUPLICATE_ID")
            decisions[key] = decision
    _need(REQUIRED_DECISIONS <= decisions.keys(), "LG_ORACLE_POLICY_REQUIRED")

    used_decisions = set()

    def authority(identifier):
        _need(identifier in decisions, "LG_ORACLE_POLICY_REQUIRED")
        row = decisions[identifier]
        scope = row["scope"]
        _need(scope["agreement_id"] == agreement and scope.get("pool_id", pool) == pool
              and scope.get("participant_id", participant) == participant
              and ("asset_ids" not in scope or set(scope["asset_ids"]) == {work})
              and _covers(row["effective"], start, end), "LG_ORACLE_POLICY_SCOPE")
        _need(row["evidence_label"] in {"research_assumption", "explicit_clause"}
              and row["review_status"] in {"proposed", "reviewed", "approved"}, "LG_ORACLE_UNRESOLVED_POLICY")
        _need(row["document_ref"] in agreement_row["document_refs"], "LG_ORACLE_POLICY_DOCUMENT")
        used_decisions.add(identifier)
        return row

    for identifier in REQUIRED_DECISIONS:
        authority(identifier)
    mappings = _index(p["mappings"], "mapping_id")
    members = []
    for row in mappings.values():
        if row["kind"] == "pool_membership" and row.get("pool_id") == pool and row.get("purpose") == "participation_prepayment":
            authority(row["authority_ref"])
            _need(row["source_code"] == row["target_ref"] and _covers(row["effective"], start, end), "LG_ORACLE_MEMBERSHIP")
            members.append(row["target_ref"])
    _need(members == [work], "LG_ORACLE_MEMBERSHIP")

    evidence = _index(p["evidence_events"], "event_id")
    by_kind = defaultdict(list)
    for row in evidence.values():
        _need(row["agreement_id"] == agreement and row["evidence_ref"] in references, "LG_ORACLE_EVIDENCE_SCOPE")
        _need(_instant(row["observed_at"]) < cutoff, "LG_ORACLE_EVIDENCE_CUTOFF")
        _day(row["effective_date"])
        authority(row["approval_ref"])
        by_kind[row["kind"]].append(row)
    for kind in ["hurdle_attestation", "gate_history", "crossed_net_worksheet"]:
        _need(len(by_kind[kind]) == 1, "LG_ORACLE_REQUIRED_EVIDENCE")
    hurdle, history, worksheet = (by_kind[k][0] for k in ["hurdle_attestation", "gate_history", "crossed_net_worksheet"])
    _need(hurdle["subject_ref"] == agreement and hurdle["approval_ref"] == "LG-OUTSIDE-HURDLE", "LG_ORACLE_HURDLE_SCOPE")
    _need(hurdle["satisfied"] is True, "LG_OUTSIDE_HURDLE_NOT_ATTAINED")
    _need(_day(hurdle["effective_date"]) < start, "LG_HURDLE_TIMING_POLICY_REQUIRED")
    _need(history["asset_id"] == work and history["subject_ref"] == work
          and history["approval_ref"] == "LG-GATE-HISTORY", "LG_ORACLE_HISTORY_SCOPE")
    _need(history["period"] == policy["period"], "LG_ORACLE_HISTORY_PERIOD")
    _need(history["satisfied"] is True, "LG_GATE_HISTORY_POLICY_REQUIRED")
    _need(worksheet["pool_id"] == pool and worksheet["subject_ref"] == pool
          and worksheet["period"] == policy["period"] and set(worksheet["member_ids"]) == {work}
          and len(worksheet["member_ids"]) == 1 and worksheet["approval_ref"] == "LG-NET-BRANCH", "LG_ORACLE_WORKSHEET_SCOPE")
    net_subtotal = _money(worksheet["amount"])

    cells = _index(p["state_cells"], "state_key")
    aliases = _index(p["opening_aliases"], "alias")
    state = {}
    for label, alias, balance_kind in [
            ("gate_gross", f"{agreement}/{work}/true-cash/cumulative-gross", "cumulative_gross"),
            ("gate_cost", f"{agreement}/{work}/true-cash/cumulative-cost", "cumulative_cost"),
            ("payment_holdback", f"synthetic/{work}/payment-holdback", "synthetic_payment_holdback")]:
        _need(alias in aliases and aliases[alias]["state_key"] in cells, "LG_ORACLE_OPENING_REQUIRED")
        row = cells[aliases[alias]["state_key"]]
        _need(row["agreement_id"] == agreement and row["participant_id"] == participant and row["pool_id"] == pool
              and row["unit"] == "USD" and row["balance_kind"] == balance_kind
              and row["boundary"] == policy["period"]["start"] and row["scenario_id"] == scenario
              and row["scope"] == {"agreement_id": agreement, "pool_id": pool, "asset_ids": [work]}, "LG_ORACLE_STATE_SCOPE")
        _need(row["provenance_ref"] in references and "SYNTHETIC-PAYMENT-HOLDBACK" in row["policy_lineage"], "LG_ORACLE_STATE_PROVENANCE")
        state[label] = _nonnegative(row["quantity"])
    _need(len(cells) == 3 and len(aliases) == 3
          and len({a["state_key"] for a in aliases.values()}) == 3, "LG_ORACLE_STATE_SCOPE")
    _need(state["gate_gross"] >= state["gate_cost"], "LG_CROSSING_POLICY_REQUIRED")

    facts = _index(p["financial_facts"], "fact_id")
    batches = {}
    for row in p["source_batches"]:
        key = tuple(_text(row[k]) for k in ["source_system", "batch_id", "version"])
        _need(key not in batches, "LG_ORACLE_DUPLICATE_ID")
        batches[key] = row
    batch_facts = defaultdict(list)
    seen_events = set()
    for identifier, row in facts.items():
        _fields(row, {"fact_id", "batch_ref", "source_row", "event_kind", "amount", "temporal_basis", "asset_id", "dates"},
                {"channel", "territory", "category", "counterparty_id", "external_event_ref", "parent_fact_id"})
        _text(row["source_row"])
        _need(row["event_kind"] in {"cash_receipt", "invoice", "incurred_cost"}, "LG_ORACLE_FACT_KIND")
        _need(row["asset_id"] in assets, "LG_ORACLE_FACT_SCOPE")
        _money(row["amount"])
        batch_key = tuple(row["batch_ref"][k] for k in ["source_system", "batch_id", "version"])
        _need(batch_key in batches, "LG_ORACLE_BATCH_REFERENCE")
        batch_facts[batch_key].append(row)
        basis = row["temporal_basis"]
        _fields(basis, {"kind", "date"})
        _day(basis["date"])
        _need(basis["kind"] in {"cash_received_date", "incurred_date", "posting_date", "invoice_date"}, "LG_ORACLE_DATE_BASIS")
        _fields(row["dates"], set(), {"cash_received_date", "incurred_date", "posting_date", "invoice_date", "license_date", "paid_date"})
        for value in row["dates"].values():
            _day(value)
        _need(basis["kind"] not in row["dates"] or basis["date"] == row["dates"][basis["kind"]], "LG_ORACLE_DATE_CONFLICT")
        if row["event_kind"] == "cash_receipt":
            _need("channel" in row, "LG_ORACLE_CHANNEL_REQUIRED")
            _need(row["channel"] in {"home_video", "other"}, "LG_ORACLE_CHANNEL")
            _need("cash_received_date" in row["dates"], "LG_ORACLE_CASH_DATE_REQUIRED")
        if row["event_kind"] == "incurred_cost":
            _need("incurred_date" in row["dates"], "LG_ORACLE_INCURRED_DATE_REQUIRED")
        if "external_event_ref" in row and row["event_kind"] != "invoice":
            identity = (row["event_kind"], _text(row["external_event_ref"]))
            _need(identity not in seen_events, "LG_ORACLE_DUPLICATE_ECONOMIC_EVENT")
            seen_events.add(identity)
        chain, current = set(), identifier
        while "parent_fact_id" in facts[current]:
            parent = facts[current]["parent_fact_id"]
            _need(parent in facts and parent not in chain and parent != identifier, "LG_ORACLE_PARENT_GRAPH")
            _need(not (row["event_kind"] == "cash_receipt" and facts[parent]["event_kind"] == "cash_receipt"), "LG_ORACLE_PARENT_CHILD_CASH")
            chain.add(parent)
            current = parent
    for key, batch in batches.items():
        _need(type(batch["row_count"]) is int and batch["row_count"] == len(batch_facts[key]), "LG_ORACLE_BATCH_COUNT")
        for control in batch["control_totals"]:
            _fields(control, {"amount_kind", "currency", "signed_total", "absolute_total"})
            _need(control["currency"] == "USD" and control["amount_kind"] in {"cash_receipt", "invoice", "incurred_cost"}, "LG_ORACLE_BATCH_CONTROL")
            amount = sum((_money(row["amount"]) for row in batch_facts[key] if row["event_kind"] == control["amount_kind"]), Fraction())
            _need(_q(control["signed_total"]) == amount and _q(control["absolute_total"]) == amount, "LG_ORACLE_BATCH_CONTROL")

    allocations = _index(p["allocations"], "allocation_id")
    authorities = {}
    for row in data["allocation_authorities"]:
        _fields(row, {"source_fact_id", "allocation_group_id", "method", "method_version", "authority_ref", "policy_ref", "scenario_id", "effective", "weights"})
        key = row["source_fact_id"]
        _need(key not in authorities, "LG_ORACLE_ALLOCATION_AUTHORITY")
        authorities[key] = row
    grouped = defaultdict(list)
    for allocation in allocations.values():
        _fields(allocation, {"allocation_id", "allocation_group_id", "source_fact_id", "target_scope", "method", "method_version", "authority_ref", "policy_ref", "scenario_id", "effective", "weight"})
        grouped[allocation["source_fact_id"]].append(allocation)
    _need(set(grouped) == set(authorities), "LG_ORACLE_ALLOCATION_AUTHORITY")
    expanded = {}
    for identifier, rows in grouped.items():
        _need(identifier in facts and facts[identifier]["event_kind"] == "cash_receipt", "LG_ORACLE_ALLOCATION_SOURCE")
        expected = authorities[identifier]
        for field in ["source_fact_id", "allocation_group_id", "method", "method_version", "authority_ref", "policy_ref", "scenario_id"]:
            _text(expected[field])
        expected_weights = _weights(expected["weights"])
        _need(set(expected_weights) == {work} and expected["scenario_id"] == scenario
              and _covers(expected["effective"], start, end), "LG_ORACLE_ALLOCATION_AUTHORITY")
        # The physical allocation policy_ref names an interpretation decision;
        # the neutral envelope's lg-cleared@1 is a different registry namespace.
        policy_decision = authority(expected["policy_ref"])
        _need(_weights(policy_decision.get("allocation_terms", [])) == expected_weights, "LG_ORACLE_ALLOCATION_AUTHORITY")
        decision = authority(expected["authority_ref"])
        _need(_weights(decision.get("allocation_terms", [])) == expected_weights, "LG_ORACLE_ALLOCATION_AUTHORITY")
        weights, children = {}, []
        for row in rows:
            _need(all(row[k] == expected[k] for k in ["allocation_group_id", "method", "method_version", "authority_ref", "policy_ref", "scenario_id", "effective"]), "LG_ORACLE_ALLOCATION_AUTHORITY")
            scope = row["target_scope"]
            _need(scope["agreement_id"] == agreement and scope.get("participant_id", participant) == participant
                  and scope.get("pool_id", pool) == pool and scope["asset_ids"] == [work], "LG_ORACLE_ALLOCATION_SCOPE")
            _need(work not in weights, "LG_ORACLE_DUPLICATE_ALLOCATION_TARGET")
            weights[work] = _nonnegative(row["weight"])
            children.append((work, weights[work], row["allocation_id"]))
        _need(weights == expected_weights, "LG_ORACLE_ALLOCATION_AUTHORITY")
        expanded[identifier] = children

    cost_choices = _index(parameters["cost_decisions"], "fact_id")
    _need(set(cost_choices) == {key for key, row in facts.items() if row["event_kind"] == "incurred_cost"}, "LG_ORACLE_COST_DECISION")
    contributions, dispositions = [], []
    cash = video = ordinary = costs = Fraction()
    for identifier, row in sorted(facts.items()):
        if row["event_kind"] == "invoice":
            dispositions.append({"fact_id": identifier, "disposition": "excluded", "reason": "invoice_is_not_cash"})
            continue
        selector = "cash_received_date" if row["event_kind"] == "cash_receipt" else "incurred_date"
        selected_date = _day(row["dates"][selector])
        eligible = True
        if row["event_kind"] == "incurred_cost":
            choice = cost_choices[identifier]
            _fields(choice, {"fact_id", "decision_id", "eligible", "branch", "reason"})
            _need(choice["branch"] == "lg" and type(choice["eligible"]) is bool, "LG_ORACLE_COST_DECISION")
            _text(choice["reason"])
            terms = authority(choice["decision_id"]).get("cost_terms", [])
            _need(sum(term == {"fact_id": identifier, "branch": "lg", "eligible": choice["eligible"]} for term in terms) == 1, "LG_ORACLE_COST_AUTHORITY")
            eligible = choice["eligible"]
        if not start <= selected_date < end:
            dispositions.append({"fact_id": identifier, "disposition": "excluded", "reason": "outside_period", "selected_date_kind": selector})
            continue
        if not eligible:
            dispositions.append({"fact_id": identifier, "disposition": "excluded", "reason": "explicit_cost_exclusion", "decision_id": cost_choices[identifier]["decision_id"]})
            continue
        targets = expanded.get(identifier, [(row["asset_id"], Fraction(1), None)])
        included = False
        for target, weight, allocation_id in targets:
            if target != work:
                continue
            included = True
            amount = _money(row["amount"]) * weight
            contribution = {"fact_id": identifier, "asset_id": target, "amount": amount,
                            "kind": row["event_kind"], "selected_date_kind": selector,
                            "selected_date": row["dates"][selector], "source_row": row["source_row"],
                            "batch_ref": deepcopy(row["batch_ref"]), "allocation_id": allocation_id}
            if row["event_kind"] == "cash_receipt":
                is_video = row.get("channel", "other") == "home_video"
                contribution["channel"] = "home_video" if is_video else "other"
                cash += amount
                if is_video:
                    video += amount
                else:
                    ordinary += amount
            else:
                costs += amount
                contribution["decision_id"] = cost_choices[identifier]["decision_id"]
            contributions.append(contribution)
        dispositions.append({"fact_id": identifier, "disposition": "included" if included else "excluded",
                             "reason": "allocated_parent_consumed_once" if identifier in expanded else "selected_work" if included else "other_work"})

    closing_gross, closing_cost = state["gate_gross"] + cash, state["gate_cost"] + costs
    _need(closing_gross >= closing_cost, "LG_RECROSSING_POLICY_REQUIRED")
    payout_base = ordinary + video * proxy
    before_offset = payout_base * gross_rate
    gross_candidate, net_candidate = max(Fraction(), before_offset - producer_offset), net_subtotal * net_rate
    earned = max(gross_candidate, net_candidate)
    label = "tie" if gross_candidate == net_candidate else "gross" if gross_candidate > net_candidate else "net"
    _need(release <= state["payment_holdback"], "SYNTHETIC_HOLDBACK_RELEASE_EXCEEDS_OPENING")
    _need(addition <= earned + release, "SYNTHETIC_HOLDBACK_ADDITION_EXCEEDS_AVAILABLE")
    return {"agreement_id": agreement, "participant_id": participant, "asset_id": work, "pool_id": pool,
            "period": deepcopy(policy["period"]), "opening_gate_gross": state["gate_gross"],
            "opening_gate_cost": state["gate_cost"], "cash_measure": cash, "actual_cost_measure": costs,
            "non_video_receipts": ordinary, "home_video_receipts": video,
            "closing_gate_gross": closing_gross, "closing_gate_cost": closing_cost,
            "gate_surplus": closing_gross - closing_cost, "payout_base": payout_base,
            "gross_before_offset": before_offset, "producer_fee_offset": producer_offset,
            "gross_candidate": gross_candidate, "crossed_net_subtotal": net_subtotal,
            "net_candidate": net_candidate, "selected_label": label, "earned": earned,
            "opening_payment_holdback": state["payment_holdback"], "holdback_addition": addition,
            "holdback_release": release, "payable": earned + release - addition,
            "closing_payment_holdback": state["payment_holdback"] + addition - release,
            "closing_state": {"gate_gross": closing_gross, "gate_cost": closing_cost,
                              "payment_holdback": state["payment_holdback"] + addition - release},
            "outside_hurdle": deepcopy(hurdle), "work_gate_history": deepcopy(history),
            "crossed_net_worksheet": deepcopy(worksheet), "contributions": contributions,
            "dispositions": dispositions,
            "review_records": [deepcopy(decisions[key]) for key in sorted(used_decisions)],
            "payment_evidence_status": "no_event_supplied", "issuance_status": "unissued",
            "professional_approval": "not_established", "gate_history_basis": "supplied_attestation",
            "net_ledger_basis": "supplied_worksheet", "fact_observation_basis": "supplied_snapshot_without_fact_observation_fields"}


def lionsgate(data):
    """Return exact bounded controls or a rejection with no financial results."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError, OverflowError) as error:
        if isinstance(error, LionsgateOracleError):
            raise
        raise LionsgateOracleError("LG_ORACLE_MALFORMED_INPUT") from error


def exact_json(value):
    """Neutral reporting only; no compiler financial codec is imported."""
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
