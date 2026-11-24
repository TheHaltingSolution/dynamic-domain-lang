"""Independent original-receipt cross-contract entitlement subtraction controls."""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import re

POLICY_ID = "SYNTHETIC-CONTRACT-BURDENS-01"
SCOPE = {"agreement_id", "participant_id", "pool_id", "asset_id", "currency"}
ARRAYS = ("accounts", "terms", "receipts", "authorizations", "requests", "payments", "applications", "receipt_populations", "payment_populations", "evidence")
FRAME_FIELDS = {"case_id", "period", "as_of", "cutoff", *ARRAYS}
STATIC = ("accounts", "terms", "authorizations")
KINDS = ("receipt_ids", "receipt_refs", "entitlement_refs", "payment_ids", "payment_refs", "application_ids", "request_ids", "request_refs", "semantic_keys")


class ContractBurdenOracleError(ValueError):
    pass


def need(value, code):
    if not value: raise ContractBurdenOracleError(code)


def fields(row, required, optional=()):
    need(type(row) is dict and required <= row.keys() <= required | set(optional), "BURDEN_RECORD_FIELDS")


def text(value):
    need(type(value) is str and bool(value) and all(not 0xD800 <= ord(char) <= 0xDFFF for char in value), "BURDEN_TEXT_IDENTITY")
    return value


def q(value):
    need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "BURDEN_EXACT_NONNEGATIVE")
    return Fraction(value)


def day(value):
    need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "BURDEN_DATE")
    try: return date.fromisoformat(value)
    except ValueError: raise ContractBurdenOracleError("BURDEN_DATE") from None


def period(value):
    fields(value, {"start", "end"}); start, end = day(value["start"]), day(value["end"])
    need(start < end, "BURDEN_PERIOD"); return start, end


def instant(value):
    need(type(value) is str, "BURDEN_INSTANT")
    m = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    need(m is not None, "BURDEN_INSTANT")
    d, h, minute, second, fraction, zone = m.groups(); h, minute, second = int(h), int(minute), int(second)
    need(h < 24 and minute < 60 and second < 60, "BURDEN_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:]); need(zone != "-00:00" and zh < 24 and zm < 60, "BURDEN_INSTANT")
        offset = (zh * 60 + zm) * 60 * (1 if zone[0] == "+" else -1)
    result = Fraction(day(d).toordinal() * 86400 + h * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    need(86400 <= result < (date.max.toordinal() + 1) * 86400, "BURDEN_INSTANT")
    return result


def line(value):
    text(value); before, marker, after = value.rpartition("#")
    need(before and marker and after, "BURDEN_ORIGINAL_LINE_REFERENCE"); return value


def index(rows):
    need(type(rows) is list and len(rows) <= 64, "BURDEN_FINITE_RECORDS")
    result = {}
    for row in rows:
        identity = text(row["id"]); need(identity not in result, "BURDEN_DUPLICATE_ID"); result[identity] = row
    return result


def ids(values):
    need(type(values) is list and all(type(x) is str and x for x in values) and len(values) == len(set(values)), "BURDEN_POPULATION_IDS")
    return set(values)


def policy(method="accrued_basis_current_period"):
    need(method in {"accrued_basis_current_period", "paid_basis_current_period"}, "BURDEN_METHOD")
    return {"id": POLICY_ID, "revision": "1", "method": method, "measurement": "original_pre_burden_current_participation",
            "cap": "cumulative_original_authority", "cap_excess": "consume_no_carry", "shortfall": "atomic_reject_after_cap",
            "threshold": "basis_at_least_minimum", "request_limit": "one_canonical_authority_source_period_measurement",
            "order": "unique_authorized_sequence", "rounding": "exact_no_rounding", "observation_date_basis": "UTC",
            "late_payment_reopening": "unsupported", "evidence_class": "research_assumption"}


def _run(frame, coordinator, selected, seen, caps, registry):
    fields(frame, FRAME_FIELDS)
    text(frame["case_id"])
    start, end = period(frame["period"]); as_of, cutoff = day(frame["as_of"]), instant(frame["cutoff"])
    need(as_of == end - timedelta(days=1) and cutoff >= end.toordinal() * 86400, "BURDEN_COMPLETE_PERIOD_VIEW")
    rows = {key: index(frame[key]) for key in ARRAYS}
    accounts = rows["accounts"]; need(1 <= len(accounts) <= 4 and len(rows["authorizations"]) <= 8 and len(rows["requests"]) <= 8, "BURDEN_FINITE_PROFILE")
    scopes = set()
    for row in accounts.values():
        fields(row, {"id", "scope", "observed_at", "source_ref", "evidence_ref"}); fields(row["scope"], SCOPE)
        for value in row["scope"].values(): text(value)
        need(row["scope"]["currency"] == "USD", "BURDEN_CURRENCY")
        key = tuple(row["scope"][name] for name in sorted(SCOPE)); need(key not in scopes, "BURDEN_ACCOUNT_ALIAS"); scopes.add(key)
    for row in rows["evidence"].values():
        fields(row, {"id", "coordinator_id", "account_ids", "kind", "approved", "observed_at", "source_ref"})
        need(row["coordinator_id"] == coordinator["id"] and ids(row["account_ids"]) <= accounts.keys(), "BURDEN_EVIDENCE_SCOPE")
        need(row["approved"] is True and instant(row["observed_at"]) < cutoff, "BURDEN_EVIDENCE_APPROVAL_CUTOFF"); text(row["source_ref"])
        text(row["kind"])

    def support(row, endpoints, kind):
        text(row["source_ref"])
        need(row["evidence_ref"] in rows["evidence"], "BURDEN_EVIDENCE_REQUIRED")
        ev = rows["evidence"][row["evidence_ref"]]
        need(set(endpoints) <= set(ev["account_ids"]) and ev["kind"] == kind, "BURDEN_EVIDENCE_AUTHORITY")
        need(instant(row["observed_at"]) < cutoff and instant(ev["observed_at"]) <= instant(row["observed_at"]), "BURDEN_SOURCE_OBSERVATION")

    def scoped(row, account):
        need(account in accounts and row["scope"] == accounts[account]["scope"], "BURDEN_FACT_SCOPE")

    def consume(kind, value):
        need(value not in seen[kind], "BURDEN_REPLAY_" + kind.upper()); seen[kind].add(value)

    for row in accounts.values(): support(row, [row["id"]], "account_scope")
    term_refs = set()
    for row in rows["terms"].values():
        fields(row, {"id", "account_id", "scope", "share", "effective", "approved", "approved_date", "observed_at", "original_ref", "source_ref", "evidence_ref"})
        scoped(row, row["account_id"]); support(row, [row["account_id"]], "participation_terms")
        need(row["approved"] is True and day(row["approved_date"]) <= as_of and q(row["share"]) <= 1, "BURDEN_TERM_APPROVAL_RATE")
        need(day(row["approved_date"]).toordinal() * 86400 <= instant(row["observed_at"]), "BURDEN_TERM_OBSERVATION")
        period(row["effective"]); ref = line(row["original_ref"]); need(ref not in term_refs, "BURDEN_TERM_ALIAS"); term_refs.add(ref)
    auth_refs, sequences, graph = set(), set(), {account: set() for account in accounts}
    for row in rows["authorizations"].values():
        fields(row, {"id", "claimant_account", "burdened_account", "claimant_scope", "burdened_scope", "purpose", "basis_kind", "burden_rate", "minimum_basis", "cap", "sequence", "effective", "approved", "approved_date", "recorded_date", "observed_at", "original_ref", "source_ref", "evidence_ref"})
        source, target = row["claimant_account"], row["burdened_account"]
        need(source in accounts and target in accounts and source != target, "BURDEN_ENDPOINTS")
        need(row["claimant_scope"] == accounts[source]["scope"] and row["burdened_scope"] == accounts[target]["scope"], "BURDEN_AUTHORITY_SCOPE")
        need(row["claimant_scope"]["agreement_id"] != row["burdened_scope"]["agreement_id"], "BURDEN_CROSS_AGREEMENT_REQUIRED")
        need(row["purpose"] == coordinator["purpose"] and row["basis_kind"] == selected["method"], "BURDEN_AUTHORITY_PURPOSE_BASIS")
        support(row, [source, target], "cross_contract_authority")
        need(row["approved"] is True and day(row["approved_date"]) <= day(row["recorded_date"]) <= as_of, "BURDEN_AUTHORITY_APPROVAL")
        need(day(row["recorded_date"]).toordinal() * 86400 <= instant(row["observed_at"]), "BURDEN_AUTHORITY_OBSERVATION")
        need(q(row["burden_rate"]) <= 1, "BURDEN_AUTHORITY_RATE"); q(row["minimum_basis"]); q(row["cap"]); period(row["effective"])
        need(type(row["sequence"]) is int and row["sequence"] >= 0 and row["sequence"] not in sequences, "BURDEN_AUTHORIZED_SEQUENCE"); sequences.add(row["sequence"])
        ref = line(row["original_ref"]); need(ref not in auth_refs, "BURDEN_AUTHORITY_ALIAS"); auth_refs.add(ref)
        graph[source].add(target); caps.setdefault(row["id"], Fraction())
    remaining = set(accounts); order = []
    while remaining:
        ready = sorted(a for a in remaining if not any(a in graph[b] for b in remaining))
        need(ready, "BURDEN_CYCLIC_DEPENDENCY"); node = ready[0]; order.append(node); remaining.remove(node)
    current_registry = {key: sorted(deepcopy(frame[key]), key=lambda row: row["id"]) for key in STATIC}
    static_evidence = {row["evidence_ref"] for key in STATIC for row in frame[key]}
    current_registry["static_evidence"] = [deepcopy(rows["evidence"][key]) for key in sorted(static_evidence)]
    if registry is not None: need(current_registry == registry, "BURDEN_REGISTRY_AMENDMENT_OR_RESET")
    registry = current_registry
    accrued = {account: Fraction() for account in accounts}; gross = dict(accrued); receipt_earned = {}; receipt_details = []
    for row in rows["receipts"].values():
        fields(row, {"id", "account_id", "scope", "amount", "term_id", "effective_date", "observed_at", "original_ref", "entitlement_line_ref", "source_ref", "evidence_ref"})
        account = row["account_id"]; scoped(row, account); support(row, [account], "original_receipt_basis")
        need(row["term_id"] in rows["terms"], "BURDEN_UNKNOWN_TERM"); term = rows["terms"][row["term_id"]]
        when = day(row["effective_date"]); ts, te = period(term["effective"])
        need(term["account_id"] == account and start <= when < end and ts <= when < te and day(term["approved_date"]) <= when, "BURDEN_RECEIPT_TERM_PERIOD")
        need(when.toordinal() * 86400 <= instant(row["observed_at"]), "BURDEN_RECEIPT_OBSERVATION")
        consume("receipt_ids", row["id"]); consume("receipt_refs", line(row["original_ref"])); consume("entitlement_refs", line(row["entitlement_line_ref"]))
        amount = q(row["amount"]); earned = amount * q(term["share"]); gross[account] += amount; accrued[account] += earned; receipt_earned[row["id"]] = earned
        receipt_details.append({"receipt": deepcopy(row), "original_share": term["share"], "derived_participation_entitlement": earned})
    for account in accounts:
        pops = [row for row in rows["receipt_populations"].values() if row["account_id"] == account]
        need(len(pops) == 1 and pops[0]["complete"] is True, "BURDEN_COMPLETE_RECEIPT_POPULATION_REQUIRED")
        pop = pops[0]; fields(pop, {"id", "account_id", "scope", "period", "complete", "receipt_ids", "gross_total", "observed_at", "source_ref", "evidence_ref"})
        scoped(pop, account); support(pop, [account], "complete_receipt_population")
        selected_ids = {row["id"] for row in rows["receipts"].values() if row["account_id"] == account}
        need(pop["period"] == frame["period"] and ids(pop["receipt_ids"]) == selected_ids and q(pop["gross_total"]) == gross[account], "BURDEN_RECEIPT_POPULATION_CONTROL")
        need(all(instant(rows["receipts"][key]["observed_at"]) <= instant(pop["observed_at"]) for key in selected_ids), "BURDEN_POPULATION_OBSERVATION")
    need(all(row["account_id"] in accounts for row in rows["receipt_populations"].values()), "BURDEN_UNKNOWN_ACCOUNT")
    paid, payment_details = {account: None for account in accounts}, []
    payment_apps = {key: Fraction() for key in rows["payments"]}; receipt_apps = {key: Fraction() for key in rows["receipts"]}
    for row in rows["payments"].values():
        fields(row, {"id", "account_id", "scope", "amount", "purpose", "paid_at", "observed_at", "original_ref", "source_ref", "evidence_ref"})
        scoped(row, row["account_id"]); support(row, [row["account_id"]], "actual_participation_payment")
        tick = instant(row["paid_at"]); paid_day = date.fromordinal(tick.numerator // tick.denominator // 86400)
        need(start <= paid_day < end and tick <= instant(row["observed_at"]), "BURDEN_PAYMENT_PERIOD_OBSERVATION")
        need(row["purpose"] == "participation_entitlement_settlement", "BURDEN_PAYMENT_PURPOSE")
        consume("payment_ids", row["id"]); consume("payment_refs", line(row["original_ref"])); q(row["amount"])
    for row in rows["applications"].values():
        fields(row, {"id", "account_id", "scope", "payment_id", "receipt_id", "entitlement_line_ref", "amount", "approved", "application_date", "observed_at", "source_ref", "evidence_ref"})
        scoped(row, row["account_id"]); support(row, [row["account_id"]], "approved_participation_application")
        need(row["payment_id"] in rows["payments"] and row["receipt_id"] in rows["receipts"], "BURDEN_CURRENT_PARTICIPATION_REFERENCE")
        payment, receipt = rows["payments"][row["payment_id"]], rows["receipts"][row["receipt_id"]]
        need(row["approved"] is True and row["account_id"] == payment["account_id"] == receipt["account_id"]
             and row["entitlement_line_ref"] == receipt["entitlement_line_ref"], "BURDEN_APPLICATION_SCOPE_LINEAGE")
        need(start <= day(row["application_date"]) < end and instant(payment["paid_at"]) <= instant(row["observed_at"]), "BURDEN_APPLICATION_PERIOD")
        need(day(receipt["effective_date"]) <= day(row["application_date"]) and
             instant(payment["paid_at"]) // 86400 <= day(row["application_date"]).toordinal()
             and day(row["application_date"]).toordinal() * 86400 <= instant(row["observed_at"])
             and instant(payment["observed_at"]) <= instant(row["observed_at"]), "BURDEN_APPLICATION_CHRONOLOGY")
        consume("application_ids", row["id"]); amount = q(row["amount"]); payment_apps[row["payment_id"]] += amount; receipt_apps[row["receipt_id"]] += amount
        payment_details.append({"application": deepcopy(row), "derived_participation_limit": receipt_earned[row["receipt_id"]], "applied": amount})
    need(all(payment_apps[key] == q(row["amount"]) for key, row in rows["payments"].items()), "BURDEN_PAYMENT_APPLICATION_CONSERVATION")
    need(all(amount <= receipt_earned[key] for key, amount in receipt_apps.items()), "BURDEN_PAID_EXCEEDS_PARTICIPATION_ENTITLEMENT")
    for account in accounts:
        pops = [row for row in rows["payment_populations"].values() if row["account_id"] == account]
        payments = {key for key, row in rows["payments"].items() if row["account_id"] == account}
        applications = {key for key, row in rows["applications"].items() if row["account_id"] == account}
        need(len(pops) <= 1, "BURDEN_PAYMENT_POPULATION_DUPLICATE")
        if not pops:
            need(not payments and not applications, "BURDEN_COMPLETE_PAYMENT_POPULATION_REQUIRED"); continue
        pop = pops[0]; fields(pop, {"id", "account_id", "scope", "period", "complete", "payment_ids", "application_ids", "paid_total", "observed_at", "source_ref", "evidence_ref"})
        scoped(pop, account); support(pop, [account], "complete_payment_population")
        need(pop["complete"] is True and pop["period"] == frame["period"], "BURDEN_COMPLETE_PAYMENT_POPULATION_REQUIRED")
        total = sum((payment_apps[key] for key in payments), Fraction())
        need(ids(pop["payment_ids"]) == payments and ids(pop["application_ids"]) == applications and q(pop["paid_total"]) == total, "BURDEN_PAYMENT_POPULATION_CONTROL")
        need(all(instant(rows["payments"][key]["observed_at"]) <= instant(pop["observed_at"]) for key in payments)
             and all(instant(rows["applications"][key]["observed_at"]) <= instant(pop["observed_at"]) for key in applications), "BURDEN_POPULATION_OBSERVATION")
        paid[account] = total
    need(all(row["account_id"] in accounts for row in rows["payment_populations"].values()), "BURDEN_UNKNOWN_ACCOUNT")
    adjusted = dict(accrued); applied_total = Fraction(); details = []
    requests = []
    for row in rows["requests"].values():
        fields(row, {"id", "authorization_id", "claimant_account", "burdened_account", "claimant_scope", "burdened_scope", "measurement_id", "basis_receipt_ids", "recognition_date", "observed_at", "original_ref", "source_ref", "evidence_ref"})
        need(row["authorization_id"] in rows["authorizations"], "BURDEN_UNKNOWN_AUTHORITY")
        auth = rows["authorizations"][row["authorization_id"]]; source, target = auth["claimant_account"], auth["burdened_account"]
        need((row["claimant_account"], row["burdened_account"], row["claimant_scope"], row["burdened_scope"]) == (source, target, auth["claimant_scope"], auth["burdened_scope"]), "BURDEN_REQUEST_AUTHORITY_SCOPE")
        support(row, [source, target], "original_burden_request"); text(row["measurement_id"])
        when = day(row["recognition_date"]); first, last = period(auth["effective"])
        need(when == as_of and first <= when < last and day(auth["approved_date"]) <= when and instant(auth["observed_at"]) <= instant(row["observed_at"]), "BURDEN_AUTHORITY_EFFECTIVE_OBSERVATION")
        need(when.toordinal() * 86400 <= instant(row["observed_at"]), "BURDEN_REQUEST_OBSERVATION")
        original_ids = {key for key, receipt in rows["receipts"].items() if receipt["account_id"] == source}
        need(ids(row["basis_receipt_ids"]) == original_ids, "BURDEN_ORIGINAL_MEASUREMENT_POPULATION")
        measurements = [receipt for receipt in rows["receipts"].values() if receipt["account_id"] == source]
        measurements += [pop for pop in rows["receipt_populations"].values() if pop["account_id"] == source]
        if selected["method"] == "paid_basis_current_period":
            measurements += [fact for key in ("payments", "applications", "payment_populations") for fact in rows[key].values() if fact["account_id"] == source]
        need(all(instant(fact["observed_at"]) <= instant(row["observed_at"]) for fact in measurements), "BURDEN_MEASUREMENT_NOT_KNOWN")
        semantic = (auth["original_ref"], tuple(auth["claimant_scope"][key] for key in sorted(SCOPE)), frame["period"]["start"], frame["period"]["end"], selected["method"])
        consume("semantic_keys", semantic); consume("request_ids", row["id"]); consume("request_refs", line(row["original_ref"]))
        requests.append((auth["sequence"], row, auth))
    for _, row, auth in sorted(requests, key=lambda item: item[0]):
        source, target = auth["claimant_account"], auth["burdened_account"]
        basis = accrued[source] if selected["method"] == "accrued_basis_current_period" else paid[source]
        need(basis is not None, "BURDEN_PAID_BASIS_UNKNOWN")
        eligible = basis >= q(auth["minimum_basis"]); requested = basis * q(auth["burden_rate"]) if eligible else Fraction()
        opening_cap, limit = caps[auth["id"]], q(auth["cap"]); need(opening_cap <= limit, "BURDEN_CAP_HISTORY")
        permitted = min(requested, limit - opening_cap); before = adjusted[target]
        need(permitted <= before, "BURDEN_TARGET_SHORTFALL_ATOMIC")
        adjusted[target] -= permitted; caps[auth["id"]] += permitted; applied_total += permitted
        details.append({"request": deepcopy(row), "authorization_id": auth["id"], "source_original_accrued": accrued[source], "source_actual_paid": paid[source],
                        "basis_kind": selected["method"], "basis": basis, "minimum_basis": q(auth["minimum_basis"]), "eligible": eligible,
                        "burden_rate": q(auth["burden_rate"]), "requested": requested, "cap_limit": limit, "cap_opening_consumed": opening_cap,
                        "cap_remaining_before": limit - opening_cap, "applied": permitted, "cap_excess_not_carried": requested - permitted,
                        "cap_consumed_after": caps[auth["id"]], "cap_remaining_after": limit - caps[auth["id"]],
                        "target_before": before, "target_after": adjusted[target], "claimant_credit_added": Fraction()})
    original_total = sum(accrued.values(), Fraction()); final_total = sum(adjusted.values(), Fraction())
    need(final_total == original_total - applied_total, "BURDEN_ENTITLEMENT_DEBIT_RECONCILIATION")
    account_results = [{"id": key, "scope": deepcopy(accounts[key]["scope"]), "original_gross_basis": gross[key], "original_accrued": accrued[key],
                        "actual_paid": paid[key], "payment_evidence_status": "complete_original_payment_population" if paid[key] is not None else "no_event_supplied",
                        "burden_applied": accrued[key] - adjusted[key], "adjusted_entitlement": adjusted[key], "claimant_credit_added": Fraction()} for key in sorted(accounts)]
    return {"source_case_id": frame["case_id"], "period": deepcopy(frame["period"]), "status": "calculated", "account_results": account_results,
            "receipt_details": sorted(receipt_details, key=lambda row: row["receipt"]["id"]),
            "payment_application_details": sorted(payment_details, key=lambda row: row["application"]["id"]), "burden_details": details, "dependency_order": order,
            "original_entitlement_total": original_total, "applied_burden_total": applied_total, "adjusted_entitlement_total": final_total,
            "reconciliation": "adjusted_total_equals_original_total_minus_burdens", "bank_movement_created": False}, registry


def _calculate(data):
    fields(data, {"schema_version", "coordinator", "policy", "research", "opening_state", *FRAME_FIELDS}, {"prior_result"})
    need(data["schema_version"] == "entitlement-burdens-neutral/1", "BURDEN_SCHEMA")
    coordinator, selected, opening = data["coordinator"], data["policy"], data["opening_state"]
    fields(coordinator, {"id", "currency", "purpose"}); text(coordinator["id"])
    need(coordinator["currency"] == "USD" and coordinator["purpose"] == "cross_contract_entitlement_burden", "BURDEN_COORDINATOR_METADATA")
    need(selected == policy(selected["method"]), "BURDEN_SELECTED_POLICY")
    fields(data["research"], {"ld03_sha256", "rr04_sha256", "review_locator"})
    for key in ("ld03_sha256", "rr04_sha256"): need(type(data["research"][key]) is str and re.fullmatch(r"[0-9a-f]{64}", data["research"][key]), "BURDEN_REVIEW_PIN")
    need(data["research"]["review_locator"] == "LD03:390-399;B-C10-BURDEN;RR04:no-C10-specific-rule", "BURDEN_REVIEW_SCOPE")
    need(type(opening) is dict and opening.get("origin") in {"genesis", "prior_result"}, "BURDEN_OPENING_REQUIRED")
    history = opening.get("history", []); need(type(history) is list and len(history) <= 3, "BURDEN_HISTORY_BOUND")
    seen, caps, registry = {key: set() for key in KINDS}, {}, None
    replayed, previous_end, expected_opening = [], None, None

    def state(frame):
        authorities = {row["id"]: row for row in registry["authorizations"]}
        return exact_json({"schema_version": "entitlement-burden-state/1", "coordinator": deepcopy(coordinator), "policy": deepcopy(selected), "research": deepcopy(data["research"]),
                          "registry": deepcopy(registry), "boundary": frame["period"]["end"], "origin": "prior_result", "source_case_id": frame["case_id"],
                          "history": deepcopy(replayed), "cap_usage": [{"authorization_id": key, "cap_limit": q(authorities[key]["cap"]),
                                                                         "consumed": caps[key], "remaining": q(authorities[key]["cap"]) - caps[key]} for key in sorted(caps)],
                          "consumed": {key: sorted(values) for key, values in seen.items()}})
    for record in history:
        fields(record, {"facts", "result"}); frame = record["facts"]
        if previous_end is not None: need(frame["period"]["start"] == previous_end, "BURDEN_HISTORY_ADJACENCY")
        result, registry = _run(frame, coordinator, selected, seen, caps, registry)
        need(exact_json(result) == record["result"], "BURDEN_HISTORY_FINANCIAL_REPLAY")
        replayed.append(deepcopy(record)); previous_end = frame["period"]["end"]; expected_opening = state(frame)
    if opening["origin"] == "genesis":
        need(opening == {"origin": "genesis", "boundary": data["period"]["start"], "source_case_id": "genesis", "history": []} and "prior_result" not in data, "BURDEN_GENESIS")
        need(all(day(data["period"]["start"]) <= day(auth["effective"]["start"]) for auth in data["authorizations"]), "BURDEN_GENESIS_CAP_BOUNDARY")
    else:
        need(history and opening == expected_opening and previous_end == data["period"]["start"], "BURDEN_OPENING_RECONCILIATION")
        need("prior_result" in data, "BURDEN_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]; fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        need(prior["source_case_id"] == opening["source_case_id"] and prior["closing_state"] == opening and period(prior["period"])[1] == day(data["period"]["start"]), "BURDEN_PREDECESSOR_MISMATCH")
        if "result_ref" in prior: text(prior["result_ref"])
    frame = {key: deepcopy(data[key]) for key in FRAME_FIELDS}
    need(all(record["facts"]["case_id"] != frame["case_id"] for record in history), "BURDEN_CASE_ID_REPLAY")
    result, registry = _run(frame, coordinator, selected, seen, caps, registry)
    replayed.append({"facts": deepcopy(frame), "result": exact_json(result)})
    return {**result, "closing_state": state(frame)}


def contract_burdens(data):
    try: return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, ContractBurdenOracleError): raise
        raise ContractBurdenOracleError("BURDEN_MALFORMED_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction): return str(value)
    if isinstance(value, dict): return {key: exact_json(child) for key, child in value.items()}
    if isinstance(value, (tuple, list)): return [exact_json(child) for child in value]
    return value
