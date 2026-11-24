"""Independent original-fact controls for the disclosed SV incurred profile.

No executable SPL, compiler evaluator, schema helper or projected bindings are
consulted. Financial facts are the supplied snapshot, not observed-at records.
"""
from datetime import date
from fractions import Fraction
import re


class SkourasOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise SkourasOracleError(code)


def _text(value):
    _need(type(value) is str and bool(value), "SV_IDENTITY_REQUIRED")
    return value


def _q(value):
    if type(value) is str:
        _need(re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value), "SV_EXACT_VALUE_REQUIRED")
        return Fraction(value)
    _need(type(value) is dict and set(value) == {"numerator", "denominator"}, "SV_EXACT_VALUE_REQUIRED")
    numerator, denominator = value["numerator"], value["denominator"]
    _need(type(numerator) is str and re.fullmatch(r"-?(?:0|[1-9][0-9]*)", numerator)
          and type(denominator) is str and re.fullmatch(r"[1-9][0-9]*", denominator), "SV_EXACT_VALUE_REQUIRED")
    result = Fraction(int(numerator), int(denominator))
    _need(result.numerator == int(numerator) and result.denominator == int(denominator), "SV_REDUCED_FRACTION_REQUIRED")
    return result


def _money(value):
    _need(type(value) is dict and set(value) == {"value", "currency"} and value["currency"] == "USD", "SV_MONEY_DIMENSION")
    result = _q(value["value"])
    _need(result >= 0, "SV_NONNEGATIVE_AMOUNT")
    return result


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "SV_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise SkourasOracleError("SV_DATE") from None


def _period(value):
    _need(type(value) is dict and set(value) == {"start", "end"}, "SV_PERIOD")
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "SV_PERIOD")
    return start, end


def _covers(interval, start, end):
    lower, upper = _period(interval)
    return lower <= start and end <= upper


def _instant(value):
    _need(type(value) is str, "SV_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "SV_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "SV_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "SV_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "SV_INSTANT")
    return result


def _index(rows, field):
    _need(type(rows) is list, "SV_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row[field])
        _need(identity not in result, "SV_DUPLICATE_ID")
        result[identity] = row
    return result


def _calculate(data):
    _need(type(data) is dict and set(data) == {"schema_version", "policy_ref", "source_profile", "allocation_authorities", "package"}, "SV_NEUTRAL_FIELDS")
    _need((data["schema_version"], data["policy_ref"], data["source_profile"])
          == ("sv-neutral/1", "sv-incurred@1", "sv-incurred-v1"), "SV_SELECTED_PROFILE")
    package = data["package"]
    _need(package["profile"] == "sv-incurred-v1", "SV_SELECTED_PROFILE")
    manifest, parameters = package["manifest"], package["parameters"]
    _need(manifest["input_mode"] == "full_snapshot" and manifest["mode"] == "final" and manifest["output_currency"] == "USD", "SV_SELECTED_RUN_MODE")
    policy = parameters["policy"]
    _need(policy["period"] == manifest["period"] and parameters["cost_date_basis"] == "incurred_date", "SV_INCURRED_POLICY_REQUIRED")
    start, end = _period(policy["period"])
    next_start = date(start.year + (start.month == 10), 1 if start.month == 10 else start.month + 3, 1) if start.month in (1, 4, 7, 10) else None
    _need(start.day == 1 and next_start == end, "SV_CALENDAR_QUARTER_REQUIRED")
    cutoff = _instant(manifest["cutoff"])
    agreement_id, participant_id, pool_id = (_text(policy[key]) for key in ("agreement_id", "participant_id", "pool_id"))
    scenario = _text(manifest["scenario_id"])
    references = _index(package["references"], "reference_id")
    agreements = _index(package["agreements"], "agreement_id")
    _need(len(agreements) == 1 and agreement_id in agreements, "SV_AGREEMENT_SCOPE")
    agreement = agreements[agreement_id]
    _need(_covers(agreement["effective"], start, end), "SV_AGREEMENT_PERIOD")
    asset_records = _index(package["assets"], "asset_id")
    assets = agreement["asset_ids"]
    _need(type(assets) is list and assets and len(set(assets)) == len(assets), "SV_ASSET_UNIVERSE")
    _need(all(asset in asset_records and asset_records[asset]["kind"] == "picture" for asset in assets), "SV_ASSET_UNIVERSE")
    parties = _index(package["parties"], "party_id")
    roles = _index(package["roles"], "role_id")
    _need(len(set(agreement["role_ids"])) == len(agreement["role_ids"]), "SV_ROLE_SCOPE")
    selected_roles = [roles[identity] for identity in agreement["role_ids"]]
    _need(all(row["agreement_id"] == agreement_id and row["party_id"] in parties
              and _covers(row["effective"], start, end) for row in selected_roles), "SV_ROLE_SCOPE")
    participants = [row["party_id"] for row in selected_roles if row["role"] == "participant"]
    distributors = [row["party_id"] for row in selected_roles if row["role"] == "distributor"]
    _need(participants == [participant_id] and len(distributors) == 1 and distributors[0] != participant_id, "SV_ROLE_SCOPE")
    distributor_id = distributors[0]
    interpretations = _index(package["interpretations"], "interpretation_id")
    _need(len(interpretations) == 1, "SV_INTERPRETATION_SCOPE")
    interpretation = next(iter(interpretations.values()))
    _need(agreement["interpretation_ref"] == interpretation["interpretation_id"] + "@" + interpretation["version"], "SV_INTERPRETATION_SCOPE")
    decisions = _index(interpretation["decisions"], "decision_id")

    def authority(identity):
        _need(identity in decisions, "SV_AUTHORITY_REQUIRED")
        row = decisions[identity]
        _need(row["scope"] == {"agreement_id": agreement_id, "pool_id": pool_id}
              and _covers(row["effective"], start, end)
              and row["review_status"] in ("proposed", "approved")
              and row["evidence_label"] in ("research_assumption", "explicit_clause"), "SV_AUTHORITY_SCOPE")
        _text(row["adopted_policy"])
        _need(row["document_ref"] in references, "SV_AUTHORITY_DOCUMENT")

    for identity in ("SV-8-CASH", "SV-8-COST-SCHEDULE", "SV-8-FEE", "SV-8-BASIS", "SV-8-SHARE", "SV-7-POOL-RECOVERY"):
        authority(identity)
    _index(package["mappings"], "mapping_id")
    membership = {}
    for row in package["mappings"]:
        if row["kind"] == "pool_membership" and row.get("pool_id") == pool_id and row.get("purpose") == "participation_prepayment":
            asset = row["target_ref"]
            _need(asset in assets and asset not in membership and _covers(row["effective"], start, end), "SV_POOL_MEMBERSHIP")
            authority(row["authority_ref"])
            membership[asset] = row["mapping_id"]
    _need(set(membership) == set(assets), "SV_POOL_MEMBERSHIP")
    snapshot = parameters["funding_snapshot"]
    _need(snapshot["complete"] is True and snapshot["as_of"] == policy["period"]["start"]
          and set(snapshot["covered_assets"]) == set(assets) and len(snapshot["covered_assets"]) == len(assets)
          and set(snapshot["covered_parties"]) == {participant_id, distributor_id} and len(snapshot["covered_parties"]) == 2
          and snapshot["evidence_ref"] in references, "SV_COMPLETE_FUNDING_SNAPSHOT_REQUIRED")
    funding = {asset: {participant_id: Fraction(), distributor_id: Fraction()} for asset in assets}
    funding_ids = {asset: [] for asset in assets}
    funding_excluded = []
    evidence = _index(package["evidence_events"], "event_id")
    for row in evidence.values():
        _need(row["kind"] == "funding", "SV_UNSUPPORTED_EVIDENCE_KIND")
        asset, party = row["asset_id"], row["party_id"]
        _need(asset in funding and row["subject_ref"] == asset and party in funding[asset], "SV_FUNDING_SCOPE")
        _need(row["evidence_ref"] in references, "SV_FUNDING_EVIDENCE")
        authority(row["approval_ref"])
        _need(row["approval_ref"] == "SV-8-SHARE", "SV_FUNDING_AUTHORITY")
        amount, effective = _money(row["amount"]), _day(row["effective_date"])
        observed = _instant(row["observed_at"])
        _need(observed < cutoff and effective.toordinal() * 86400 <= observed, "SV_FUNDING_CUTOFF")
        if effective <= start:
            funding[asset][party] += amount
            funding_ids[asset].append(row["event_id"])
        else:
            funding_excluded.append({"event_id": row["event_id"], "reason": "after_opening_valuation", "amount": amount})
    branches = {asset: "funded" if funding[asset][participant_id] > 0 else "unfunded" for asset in assets}

    batches = {}
    for row in package["source_batches"]:
        key = tuple(_text(row[name]) for name in ("source_system", "batch_id", "version"))
        _need(key not in batches, "SV_DUPLICATE_ID")
        _instant(row["ingested_at"])
        _need(type(row["row_count"]) is int and row["row_count"] >= 0, "SV_SOURCE_BATCH_COUNT")
        batches[key] = row
    facts = _index(package["financial_facts"], "fact_id")
    batch_rows = {key: [] for key in batches}
    source_rows, cash_events = set(), set()
    for row in facts.values():
        _need(row["event_kind"] in ("cash_receipt", "incurred_cost", "invoice"), "SV_UNSUPPORTED_FACT_KIND")
        _money(row["amount"])
        _need(row["asset_id"] in asset_records, "SV_FACT_ASSET")
        key = tuple(row["batch_ref"][name] for name in ("source_system", "batch_id", "version"))
        _need(key in batches, "SV_SOURCE_BATCH_REFERENCE")
        batch_rows[key].append(row)
        locator = (key, _text(row["source_row"]), row["event_kind"])
        _need(locator not in source_rows, "SV_DUPLICATE_SOURCE_VIEW")
        source_rows.add(locator)
        for value in row["dates"].values():
            _day(value)
        temporal = row["temporal_basis"]
        _day(temporal["date"])
        _need(temporal["kind"] in ("cash_received_date", "incurred_date", "posting_date", "invoice_date"), "SV_TEMPORAL_BASIS")
        if temporal["kind"] in row["dates"]:
            _need(row["dates"][temporal["kind"]] == temporal["date"], "SV_TEMPORAL_BASIS")
        if row["event_kind"] == "cash_receipt" and "external_event_ref" in row:
            _need(row["external_event_ref"] not in cash_events, "SV_DUPLICATE_CASH_EVENT")
            cash_events.add(row["external_event_ref"])
        visited, current = {row["fact_id"]}, row
        while "parent_fact_id" in current:
            parent = current["parent_fact_id"]
            _need(parent in facts and parent not in visited, "SV_PARENT_REFERENCE_OR_CYCLE")
            visited.add(parent)
            _need(not (current["event_kind"] == "cash_receipt" and facts[parent]["event_kind"] == "cash_receipt"), "SV_OVERLAPPING_CASH_VIEWS")
            current = facts[parent]
    for key, row in batches.items():
        _need(len(batch_rows[key]) == row["row_count"], "SV_SOURCE_BATCH_COUNT")
        for control in row["control_totals"]:
            _need(control["currency"] == "USD" and control["amount_kind"] in ("cash_receipt", "incurred_cost", "invoice"), "SV_CONTROL_AMOUNT_SPACE")
            total = sum((_money(fact["amount"]) for fact in batch_rows[key] if fact["event_kind"] == control["amount_kind"]), Fraction())
            _need(total == _q(control["signed_total"]) == _q(control["absolute_total"]), "SV_SOURCE_CONTROL_TOTAL")

    allocation_rows = _index(package["allocations"], "allocation_id")
    authorities = _index(data["allocation_authorities"], "source_fact_id")
    by_source = {}
    for row in allocation_rows.values():
        _need(row["source_fact_id"] in facts and facts[row["source_fact_id"]]["event_kind"] == "cash_receipt", "SV_ALLOCATION_SOURCE")
        by_source.setdefault(row["source_fact_id"], []).append(row)
    _need(set(by_source) == set(authorities), "SV_ALLOCATION_AUTHORITY_REQUIRED")
    receipt_lines, allocation_controls, dispositions = [], [], []
    for identity, row in sorted(facts.items()):
        if row["event_kind"] != "cash_receipt":
            continue
        _need("cash_received_date" in row["dates"], "SV_CASH_DATE_REQUIRED")
        cash_day = _day(row["dates"]["cash_received_date"])
        included = start <= cash_day < end
        amount = _money(row["amount"])
        if identity in by_source:
            selected = by_source[identity]
            auth = authorities[identity]
            authority(auth["authority_ref"])
            _need(_covers(auth["effective"], start, end) and auth["scenario_id"] == scenario
                  and auth["method"] == "exact_weight" and auth["method_version"] == "1", "SV_ALLOCATION_AUTHORITY_SCOPE")
            approved = _index(auth["weights"], "asset_id")
            _need(set(approved) <= set(assets) and approved, "SV_ALLOCATION_TARGET")
            expected = {asset: _q(record["weight"]) for asset, record in approved.items()}
            _need(all(weight >= 0 for weight in expected.values()) and sum(expected.values(), Fraction()) == 1, "SV_ALLOCATION_AUTHORITY_CONSERVATION")
            targets, actual = set(), {}
            for allocation in selected:
                for field in ("allocation_group_id", "method", "method_version", "authority_ref", "policy_ref", "scenario_id", "effective"):
                    _need(allocation[field] == auth[field], "SV_ALLOCATION_UNAUTHORIZED_VARIANT")
                target = allocation["target_scope"]
                _need(target.get("agreement_id") == agreement_id and set(target) <= {"agreement_id", "asset_ids", "pool_id", "participant_id"}
                      and target.get("pool_id", pool_id) == pool_id and target.get("participant_id", participant_id) == participant_id
                      and len(target.get("asset_ids", [])) == 1, "SV_ALLOCATION_TARGET")
                asset = target["asset_ids"][0]
                _need(asset in expected and asset not in targets, "SV_ALLOCATION_TARGET")
                targets.add(asset)
                weight = _q(allocation["weight"])
                _need(weight == expected[asset], "SV_ALLOCATION_UNAUTHORIZED_WEIGHT")
                actual[asset] = amount * weight
                receipt_lines.append({"contribution_id": "allocation:" + allocation["allocation_id"], "source_fact_id": identity,
                                      "parent_fact_id": row.get("parent_fact_id", ""), "allocation_id": allocation["allocation_id"],
                                      "allocation_group_id": allocation["allocation_group_id"], "asset_id": asset,
                                      "cash_received_date": row["dates"]["cash_received_date"], "amount": amount * weight,
                                      "included": included, "source_row": row["source_row"]})
            _need(targets == set(expected) and sum(actual.values(), Fraction()) == amount, "SV_ALLOCATION_CONSERVATION")
            allocation_controls.append({"source_fact_id": identity, "source_amount": amount, "allocated_amount": sum(actual.values(), Fraction()), "targets": actual})
        else:
            _need(row["asset_id"] in assets, "SV_CASH_ALLOCATION_REQUIRED")
            receipt_lines.append({"contribution_id": "direct:" + identity, "source_fact_id": identity,
                                  "parent_fact_id": row.get("parent_fact_id", ""), "allocation_id": "", "allocation_group_id": "",
                                  "asset_id": row["asset_id"], "cash_received_date": row["dates"]["cash_received_date"],
                                  "amount": amount, "included": included, "source_row": row["source_row"]})
        if not included:
            dispositions.append({"fact_id": identity, "reason": "cash_outside_period", "amount": amount})
    cost_decisions = _index(parameters["cost_decisions"], "fact_id")
    costs = {identity: row for identity, row in facts.items() if row["event_kind"] == "incurred_cost"}
    _need(set(cost_decisions) == set(costs), "SV_COST_DECISION_COVERAGE")
    allowed = {asset: Fraction() for asset in assets}
    cost_lines = []
    for identity, row in sorted(costs.items()):
        _need(row["asset_id"] in assets, "SV_COST_SCOPE")
        _need("incurred_date" in row["dates"], "SV_INCURRED_DATE_REQUIRED")
        incurred = _day(row["dates"]["incurred_date"])
        choice = cost_decisions[identity]
        authority(choice["decision_id"])
        _need(choice["decision_id"] == "SV-8-COST-SCHEDULE" and choice["branch"] == branches[row["asset_id"]]
              and type(choice["eligible"]) is bool and type(choice["reason"]) is str and choice["reason"], "SV_COST_BRANCH_AUTHORITY")
        amount = _money(row["amount"])
        included = choice["eligible"] and start <= incurred < end
        if included:
            allowed[row["asset_id"]] += amount
        cost_lines.append({"fact_id": identity, "asset_id": row["asset_id"], "amount": amount,
                           "incurred_date": row["dates"]["incurred_date"], "branch": choice["branch"],
                           "included": included, "reason": choice["reason"] if not choice["eligible"] else "included" if included else "incurred_outside_period",
                           "decision_id": choice["decision_id"], "source_row": row["source_row"]})
    aliases = _index(package["opening_aliases"], "alias")
    _need("sv/participant-prepayment/main-pool" in aliases, "SV_OPENING_ALIAS")
    states = _index(package["state_cells"], "state_key")
    state_key = aliases["sv/participant-prepayment/main-pool"]["state_key"]
    _need(state_key in states, "SV_OPENING_REQUIRED")
    opening = states[state_key]
    _need(opening["agreement_id"] == agreement_id and opening["participant_id"] == participant_id
          and opening["pool_id"] == pool_id and opening["scope"] == {"agreement_id": agreement_id, "pool_id": pool_id}
          and opening["unit"] == "USD" and opening["balance_kind"] == "participation_prepayment"
          and opening["scenario_id"] == scenario and opening["boundary"] == policy["period"]["start"], "SV_OPENING_SCOPE")
    _need(opening["provenance_ref"] in references and "SV-7-POOL-RECOVERY" in opening["policy_lineage"], "SV_OPENING_AUTHORITY")
    advance = _q(opening["quantity"])
    _need(advance >= 0, "SV_NONNEGATIVE_OPENING")
    title_lines = []
    for asset in sorted(assets):
        participant_funding, distributor_funding = funding[asset][participant_id], funding[asset][distributor_id]
        total_funding = participant_funding + distributor_funding
        funded = participant_funding > 0
        _need(not funded or total_funding > 0, "SV_FUNDING_DENOMINATOR")
        fee_rate = Fraction(3, 40) if funded else Fraction(1, 4)
        share = participant_funding / total_funding if funded else Fraction(1, 5)
        cash = sum((line["amount"] for line in receipt_lines if line["asset_id"] == asset and line["included"]), Fraction())
        fee = cash * fee_rate
        basis = cash - fee - allowed[asset]
        earned = basis * share
        _need(earned >= 0, "SV_NEGATIVE_EARNINGS_OUTSIDE_PROFILE")
        title_lines.append({"asset_id": asset, "branch": branches[asset], "participant_funding": participant_funding,
                            "distributor_funding": distributor_funding, "total_funding": total_funding,
                            "funding_event_ids": sorted(funding_ids[asset]), "cash": cash, "fee_rate": fee_rate,
                            "fee": fee, "allowed_cost": allowed[asset], "basis": basis, "share": share, "earned": earned,
                            "receipt_contribution_ids": sorted(line["contribution_id"] for line in receipt_lines if line["asset_id"] == asset and line["included"]),
                            "cost_fact_ids": sorted(line["fact_id"] for line in cost_lines if line["asset_id"] == asset and line["included"])})
    earned = sum((line["earned"] for line in title_lines), Fraction())
    recovered = min(earned, advance)
    closing = advance - recovered
    return {"titles": title_lines, "pool": {"agreement_id": agreement_id, "participant_id": participant_id, "pool_id": pool_id,
                                             "period": dict(policy["period"]), "opening_prepayment": advance, "earned": earned,
                                             "recovered": recovered, "payable": earned - recovered, "closing_prepayment": closing},
            "receipt_contributions": sorted(receipt_lines, key=lambda row: row["contribution_id"]), "cost_dispositions": cost_lines,
            "excluded_funding": sorted(funding_excluded, key=lambda row: row["event_id"]),
            "allocation_controls": allocation_controls, "excluded_receipts": dispositions,
            "closing_state": {**opening, "boundary": policy["period"]["end"], "quantity": closing},
            "payment_evidence_status": "no_event_supplied", "issuance_status": "unissued",
            "limits": ["Supplied remaining opening advance, not reconstructed historical funding.",
                       "Financial fact observed_at is absent; supplied snapshot availability is an assumption.",
                       "Compiler/schema/content-pin/publication validation is outside this oracle."]}


def skouras(data):
    """Return exact independent original-fact controls, or fail atomically."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, SkourasOracleError):
            raise
        raise SkourasOracleError("SV_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
