"""Independent payment-aware revision and separately authorized recovery controls."""
from datetime import date
from fractions import Fraction
import re


POLICY_ID = "SYNTHETIC-AUTHORIZED-OFFSETS-01"
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}
PERIOD_ARRAYS = ("reversals", "revision_authorities", "offset_authorities", "future_earnings", "cash_recoveries", "recovery_applications")


class AuthorizedOffsetOracleError(ValueError):
    def __init__(self, code, evidence_status=None):
        super().__init__(code)
        self.evidence_status = evidence_status


def _need(condition, code):
    if not condition:
        raise AuthorizedOffsetOracleError(code)


def _fields(value, required, optional=()):
    _need(type(value) is dict and required <= value.keys() and value.keys() <= required | set(optional), "OFFSET_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "OFFSET_IDENTITY_REQUIRED")
    return value


def _line(value):
    _text(value)
    before, marker, after = value.rpartition("#")
    _need(bool(before and marker and after), "OFFSET_ORIGINAL_LINE_REFERENCE")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "OFFSET_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _positive(value):
    result = _q(value)
    _need(result > 0, "OFFSET_POSITIVE_AMOUNT_REQUIRED")
    return result


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "OFFSET_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise AuthorizedOffsetOracleError("OFFSET_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    start, end = _day(value["start"]), _day(value["end"])
    _need(start < end, "OFFSET_PERIOD")
    return start, end


def _instant(value):
    _need(type(value) is str, "OFFSET_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "OFFSET_INSTANT")
    day, hour, minute, second, fraction, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "OFFSET_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "OFFSET_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "OFFSET_INSTANT")
    return result


def _index(rows):
    _need(type(rows) is list, "OFFSET_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row["id"])
        _need(identity not in result, "OFFSET_DUPLICATE_ID")
        result[identity] = row
    return result


def _unique_ids(values):
    _need(type(values) is list and all(type(value) is str and value for value in values)
          and len(set(values)) == len(values), "OFFSET_POPULATION_CONTROL")
    return set(values)


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "period", "as_of", "cutoff", "policy", "original_bundle", *PERIOD_ARRAYS,
                   "evidence", "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "authorized-offsets-neutral/1", "OFFSET_NEUTRAL_SCHEMA")
    case_id, scope, policy, bundle, opening = _text(data["case_id"]), data["scope"], data["policy"], data["original_bundle"], data["opening_state"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "OFFSET_CURRENCY")
    _fields(policy, {"id", "revision", "priority_recipe", "recognition", "recovery_order", "earning_order", "cash_date_basis", "unapplied_cash", "rounding", "evidence_class"})
    recipe = policy["priority_recipe"]
    _need(recipe in ("clawback_first", "other_claim_first"), "OFFSET_PRIORITY_RECIPE")
    _need({key: value for key, value in policy.items() if key != "priority_recipe"}
          == {"id": POLICY_ID, "revision": "1", "recognition": "revise_original_obligation_only", "recovery_order": "cash_then_earning_offsets",
              "earning_order": "date_then_unique_sequence", "cash_date_basis": "supplied_utc_date", "unapplied_cash": "reject",
              "rounding": "exact_no_rounding", "evidence_class": "research_assumption"}, "OFFSET_SELECTED_POLICY")
    start, end = _period(data["period"])
    cutoff = _instant(data["cutoff"])
    evidence = _index(data["evidence"])
    payment_control_fields = {"issued_id", "as_of", "payment_ids", "disbursement_ids", "application_ids", "paid_total"}
    recovery_control_fields = {"period", "cash_ids", "receipt_ids", "application_ids", "cash_total"}
    for row in evidence.values():
        extra = payment_control_fields if row["kind"] == "complete_original_payment_population" else recovery_control_fields if row["kind"] == "complete_cash_recovery_population" else set()
        _fields(row, {"id", "scope", "observed_at", "kind"} | extra)
        _need(row["scope"] == scope, "OFFSET_EVIDENCE_SCOPE")
        _text(row["kind"])
        _need(_instant(row["observed_at"]) < cutoff, "OFFSET_EVIDENCE_CUTOFF")
        if row["kind"] == "complete_original_payment_population":
            for field in ("payment_ids", "disbursement_ids", "application_ids"):
                _unique_ids(row[field])
            _q(row["paid_total"]); _instant(row["as_of"])
        elif row["kind"] == "complete_cash_recovery_population":
            for field in ("cash_ids", "receipt_ids", "application_ids"):
                _unique_ids(row[field])
            _q(row["cash_total"]); _period(row["period"])

    def support(row, category=None, before=None):
        _need(row["scope"] == scope, "OFFSET_FACT_SCOPE")
        _need(row["evidence_ref"] in evidence, "OFFSET_EVIDENCE_REQUIRED")
        _text(row["source_ref"])
        _need(_instant(row["observed_at"]) < (cutoff if before is None else before), "OFFSET_FACT_CUTOFF")
        if category:
            _need(evidence[row["evidence_ref"]]["kind"] == category, "OFFSET_ACTUAL_CASH_EVIDENCE")

    _fields(bundle, {"original", "issued", "payment_snapshot", "other_claims"})
    original, issued, snapshot = bundle["original"], bundle["issued"], bundle["payment_snapshot"]
    _fields(original, {"id", "scope", "basis", "rate", "measurement_date", "observed_at", "source_ref", "evidence_ref"})
    support(original)
    original_id, original_basis, original_rate = _text(original["id"]), _q(original["basis"]), _q(original["rate"])
    _need(original_rate <= 1, "OFFSET_ORIGINAL_RATE_DOMAIN")
    original_date = _day(original["measurement_date"])
    _need(original_date < start, "OFFSET_ORIGINAL_HISTORICAL_DATE")
    # The payment snapshot is frozen original history, not newly paid cash in
    # each recognition period. Its capture may be later than the transactions.
    first_start = min((_period(row["period"])[0] for row in opening["period_history"]), default=start)
    gross = original_basis * original_rate
    _fields(issued, {"id", "original_id", "scope", "amount", "issued_date", "observed_at", "source_ref", "evidence_ref"})
    support(issued)
    issued_id = _text(issued["id"])
    _need(issued["original_id"] == original_id and _q(issued["amount"]) == gross
          and original_date <= _day(issued["issued_date"]) < start, "OFFSET_ORIGINAL_ISSUE")
    _fields(snapshot, {"as_of", "payments", "applications", "evidence_ref"})
    payment_asof = _instant(snapshot["as_of"])
    _need(payment_asof <= cutoff, "OFFSET_PAYMENT_SNAPSHOT_ASOF")
    _need(all(payment_asof <= _instant(row["cutoff"]) for row in opening["period_history"]), "OFFSET_PAYMENT_SNAPSHOT_ASOF")
    population = evidence.get(snapshot["evidence_ref"])
    if population is None or population["kind"] != "complete_original_payment_population":
        raise AuthorizedOffsetOracleError("OFFSET_PAYMENT_POPULATION_REQUIRED", "no_event_supplied")
    _need(population["issued_id"] == issued_id and population["as_of"] == snapshot["as_of"]
          and _instant(population["observed_at"]) < payment_asof, "OFFSET_PAYMENT_POPULATION_SCOPE")
    payments, applications = _index(snapshot["payments"]), _index(snapshot["applications"])
    disbursements, payment_sources, paid, applied = set(), set(), Fraction(), {identity: Fraction() for identity in payments}
    for identity, row in payments.items():
        _fields(row, {"id", "issued_id", "scope", "amount", "paid_at", "observed_at", "disbursement_id", "source_ref", "evidence_ref"})
        support(row, "actual_original_payment", payment_asof)
        _need(row["issued_id"] == issued_id and _instant(issued["observed_at"]) <= _instant(row["observed_at"]), "OFFSET_PAYMENT_ISSUE")
        _need(_instant(row["paid_at"]) <= _instant(row["observed_at"]), "OFFSET_PAYMENT_DATE_ORDER")
        _need(_instant(row["paid_at"]) < first_start.toordinal() * 86400, "OFFSET_PAYMENT_NOT_HISTORICAL")
        bank_id = _text(row["disbursement_id"])
        _need(bank_id not in disbursements and row["source_ref"] not in payment_sources, "OFFSET_DUPLICATE_BANK_PAYMENT")
        disbursements.add(bank_id); payment_sources.add(row["source_ref"])
        paid += _positive(row["amount"])
    app_sources = set()
    for row in applications.values():
        _fields(row, {"id", "payment_id", "issued_id", "scope", "amount", "observed_at", "source_ref", "evidence_ref"})
        support(row, before=payment_asof)
        _need(row["payment_id"] in payments and row["issued_id"] == issued_id, "OFFSET_PAYMENT_APPLICATION_REFERENCE")
        _need(_instant(payments[row["payment_id"]]["observed_at"]) <= _instant(row["observed_at"]), "OFFSET_APPLICATION_DATE_ORDER")
        _need(row["source_ref"] not in app_sources, "OFFSET_DUPLICATE_SOURCE_VIEW")
        app_sources.add(row["source_ref"])
        applied[row["payment_id"]] += _positive(row["amount"])
    _need(all(applied[identity] == _q(row["amount"]) for identity, row in payments.items()) and paid <= gross, "OFFSET_ORIGINAL_PAYMENT_CONSERVATION")
    _need(set(population["payment_ids"]) == set(payments) and set(population["disbursement_ids"]) == disbursements
          and set(population["application_ids"]) == set(applications) and _q(population["paid_total"]) == paid, "OFFSET_PAYMENT_POPULATION_CONTROL")
    _need(all(_instant(row["observed_at"]) <= _instant(population["observed_at"])
              for row in (*payments.values(), *applications.values())), "OFFSET_POPULATION_OBSERVATION_ORDER")
    others = _index(bundle["other_claims"])
    other_refs = set()
    for row in others.values():
        _fields(row, {"id", "scope", "amount", "measurement_date", "observed_at", "origin_ref", "source_ref", "evidence_ref"})
        support(row)
        reference = _line(row["origin_ref"])
        _need(reference not in other_refs and _day(row["measurement_date"]) < start, "OFFSET_OTHER_CLAIM_SOURCE")
        other_refs.add(reference); _q(row["amount"])
    _fields(opening, {"scope", "purpose", "policy_id", "policy_revision", "priority_recipe", "original_bundle", "boundary", "origin", "source_case_id", "returned_basis", "claims", "period_history"})
    _need(opening["scope"] == scope and opening["purpose"] == "authorized_original_recovery", "OFFSET_OPENING_SCOPE")
    _need((opening["policy_id"], opening["policy_revision"], opening["priority_recipe"]) == (POLICY_ID, "1", recipe), "OFFSET_OPENING_POLICY")
    _need(opening["original_bundle"] == bundle, "OFFSET_ORIGINAL_SNAPSHOT_AMENDMENT")
    _need(opening["boundary"] == data["period"]["start"], "OFFSET_OPENING_BOUNDARY")
    history = opening["period_history"]
    _need(type(history) is list, "OFFSET_HISTORY_REQUIRED")
    if opening["origin"] == "genesis":
        _need(_q(opening["returned_basis"]) == 0 and opening["claims"] == [] and not history
              and opening["source_case_id"] == "genesis" and "prior_result" not in data, "OFFSET_GENESIS")
    else:
        _need(opening["origin"] == "prior_result" and "prior_result" in data, "OFFSET_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]
        _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
        if "result_ref" in prior:
            _text(prior["result_ref"])
        _, previous_end = _period(prior["period"])
        _need(previous_end == start, "OFFSET_PREDECESSOR_BOUNDARY")
        _need(prior["source_case_id"] == opening["source_case_id"] and prior["source_case_id"] != case_id
              and prior["closing_state"] == opening, "OFFSET_PREDECESSOR_MISMATCH")
    used = {key: set() for key in PERIOD_ARRAYS}
    used_sources, bank_receipts, earning_refs, authority_ids, claim_sequences = set(), set(), set(), set(), set()
    claims, returned, reversal_dates = {}, Fraction(), []

    def process(record):
        nonlocal returned
        period_start, period_end = _period(record["period"])
        as_of = _day(record["as_of"])
        period_cutoff = _instant(record["cutoff"])
        _need(period_cutoff <= cutoff, "OFFSET_HISTORY_CUTOFF")
        rows = {key: _index(record[key]) for key in PERIOD_ARRAYS}
        for key, indexed in rows.items():
            _need(not (set(indexed) & used[key]), "OFFSET_EVENT_ALREADY_RECOGNIZED")
            used[key].update(indexed)

        def current_fact(row, key):
            support(row, before=period_cutoff)
            _need(_instant(evidence[row["evidence_ref"]]["observed_at"]) < period_cutoff, "OFFSET_EVIDENCE_CUTOFF")
            source = (key, row["source_ref"])
            _need(source not in used_sources, "OFFSET_SOURCE_ALREADY_RECOGNIZED")
            used_sources.add(source)

        def authority(row):
            _need(row["id"] not in authority_ids, "OFFSET_AUTHORITY_ALREADY_RECOGNIZED")
            authority_ids.add(row["id"])
            current_fact(row, "authority")
            _need(row["effective"] == record["period"] and row["approved"] is True
                  and _day(row["approved_date"]) <= _day(row["recorded_date"]) <= as_of, "OFFSET_AUTHORITY_ASOF_SCOPE")

        revision = rows["revision_authorities"]
        for row in revision.values():
            _fields(row, {"id", "original_id", "issued_id", "scope", "effective", "approved", "approved_date", "recorded_date", "observed_at",
                          "permitted_reversal_ids", "maximum_returned_basis", "source_ref", "evidence_ref"})
            authority(row)
            _need(row["original_id"] == original_id and row["issued_id"] == issued_id, "OFFSET_REVISION_AUTHORITY_ORIGINAL")
            _unique_ids(row["permitted_reversal_ids"]); _q(row["maximum_returned_basis"])
        reversal_totals = {identity: Fraction() for identity in revision}
        current_reversal = Fraction()
        for row in rows["reversals"].values():
            _fields(row, {"id", "original_id", "revision_authority_id", "scope", "returned_basis", "return_date", "recognition_date", "observed_at", "source_ref", "evidence_ref"})
            current_fact(row, "reversal")
            identity = row["revision_authority_id"]
            _need(row["original_id"] == original_id and identity in revision and row["id"] in revision[identity]["permitted_reversal_ids"], "OFFSET_REVISION_AUTHORITY_REQUIRED")
            _need(period_start <= _day(row["recognition_date"]) < period_end
                  and original_date <= _day(row["return_date"]) <= _day(row["recognition_date"]), "OFFSET_REVERSAL_DATE")
            _need(_instant(original["observed_at"]) <= _instant(row["observed_at"])
                  and _instant(revision[identity]["observed_at"]) <= _instant(row["observed_at"]), "OFFSET_REVERSAL_OBSERVATION")
            amount = _q(row["returned_basis"])
            reversal_totals[identity] += amount
            current_reversal += amount
            reversal_dates.append((_day(row["recognition_date"]), amount))
        _need(all(amount <= _q(revision[identity]["maximum_returned_basis"]) for identity, amount in reversal_totals.items()), "OFFSET_REVISION_AUTHORITY_LIMIT")
        returned += current_reversal
        _need(returned <= original_basis, "OFFSET_ORIGINAL_OVERRETURN")
        revised = gross - returned * original_rate
        potential = max(paid - revised, Fraction())
        for row in sorted(rows["offset_authorities"].values(), key=lambda item: (item["eligible_from"], item["sequence"])):
            _fields(row, {"id", "claim_id", "kind", "origin_id", "scope", "amount", "priority", "sequence", "eligible_from", "effective",
                          "approved", "approved_date", "recorded_date", "observed_at", "source_ref", "evidence_ref"})
            authority(row)
            claim_id = _text(row["claim_id"])
            _need(claim_id not in claims, "OFFSET_CLAIM_ALREADY_REGISTERED")
            kind = row["kind"]
            _need(kind in ("original_overpayment", "other_supplied_claim"), "OFFSET_CLAIM_KIND")
            wanted = 0 if (kind == "original_overpayment") == (recipe == "clawback_first") else 1
            _need(type(row["priority"]) is int and row["priority"] == wanted, "OFFSET_EXPLICIT_PRIORITY")
            _need(type(row["sequence"]) is int and row["sequence"] >= 0 and row["sequence"] not in claim_sequences, "OFFSET_CLAIM_SEQUENCE")
            claim_sequences.add(row["sequence"])
            eligible = _day(row["eligible_from"])
            _need(period_start <= eligible < period_end and _day(row["recorded_date"]) <= eligible, "OFFSET_PROSPECTIVE_DATE")
            amount = _positive(row["amount"])
            origin = row["origin_id"]
            if kind == "original_overpayment":
                _need(origin == original_id, "OFFSET_CLAIM_ORIGINAL")
                authorized = sum((claim["authorized_amount"] for claim in claims.values() if claim["kind"] == kind), Fraction())
                recognized = sum((amount for day, amount in reversal_dates if day <= eligible), Fraction())
                prospective_capacity = max(paid - gross + recognized * original_rate, Fraction())
                _need(authorized + amount <= prospective_capacity, "OFFSET_OVERPAYMENT_AUTHORIZATION_CAPACITY")
            else:
                _need(origin in others, "OFFSET_OTHER_CLAIM_REQUIRED")
                authorized = sum((claim["authorized_amount"] for claim in claims.values() if claim["kind"] == kind and claim["origin_id"] == origin), Fraction())
                _need(authorized + amount <= _q(others[origin]["amount"]), "OFFSET_OTHER_AUTHORIZATION_CAPACITY")
            claims[claim_id] = {"id": claim_id, "kind": kind, "origin_id": origin, "authorized_amount": amount,
                                "priority": row["priority"], "sequence": row["sequence"], "eligible_from": row["eligible_from"],
                                "authority_id": row["id"], "authority_record": dict(row), "actual_cash_recovered": Fraction(),
                                "earning_offsets": Fraction(), "remaining": amount}
        cash, apps = rows["cash_recoveries"], rows["recovery_applications"]
        populations = [row for row in evidence.values() if row["kind"] == "complete_cash_recovery_population" and row["period"] == record["period"]]
        if not populations:
            raise AuthorizedOffsetOracleError("OFFSET_RECOVERY_POPULATION_REQUIRED", "no_event_supplied")
        _need(len(populations) == 1, "OFFSET_RECOVERY_POPULATION_AMBIGUOUS")
        _need(_instant(populations[0]["observed_at"]) < period_cutoff, "OFFSET_EVIDENCE_CUTOFF")
        receipts, current_cash = set(), Fraction()
        applied_cash = {identity: Fraction() for identity in cash}
        for row in cash.values():
            _fields(row, {"id", "receipt_id", "scope", "amount", "received_date", "received_at", "observed_at", "source_ref", "evidence_ref"})
            current_fact(row, "cash")
            _need(evidence[row["evidence_ref"]]["kind"] == "actual_cash_recovery", "OFFSET_ACTUAL_CASH_EVIDENCE")
            receipt = _text(row["receipt_id"])
            _need(receipt not in bank_receipts, "OFFSET_BANK_RECEIPT_ALREADY_RECOGNIZED")
            bank_receipts.add(receipt); receipts.add(receipt)
            received, observed, day = _instant(row["received_at"]), _instant(row["observed_at"]), _day(row["received_date"])
            _need(day.toordinal() * 86400 <= received < (day.toordinal() + 1) * 86400, "OFFSET_CASH_UTC_DATE")
            _need(period_start <= day < period_end and received <= observed, "OFFSET_CASH_DATE")
            current_cash += _positive(row["amount"])
        claim_cash = {identity: Fraction() for identity in claims}
        for row in apps.values():
            _fields(row, {"id", "cash_id", "claim_id", "scope", "amount", "observed_at", "source_ref", "evidence_ref"})
            current_fact(row, "cash_application")
            _need(row["cash_id"] in cash and row["claim_id"] in claims, "OFFSET_CASH_APPLICATION_REFERENCE")
            receipt, claim = cash[row["cash_id"]], claims[row["claim_id"]]
            _need(_day(receipt["received_date"]) >= _day(claim["eligible_from"]), "OFFSET_CASH_BEFORE_AUTHORITY")
            _need(_instant(receipt["observed_at"]) <= _instant(row["observed_at"])
                  and _instant(claim["authority_record"]["observed_at"]) <= _instant(row["observed_at"]), "OFFSET_APPLICATION_DATE_ORDER")
            amount = _positive(row["amount"])
            applied_cash[row["cash_id"]] += amount
            claim_cash[row["claim_id"]] += amount
        _need(all(applied_cash[identity] == _q(row["amount"]) for identity, row in cash.items()), "OFFSET_CASH_APPLICATION_CONSERVATION")
        population = populations[0]
        _need(set(population["cash_ids"]) == set(cash) and set(population["receipt_ids"]) == receipts
              and set(population["application_ids"]) == set(apps) and _q(population["cash_total"]) == current_cash, "OFFSET_RECOVERY_POPULATION_CONTROL")
        _need(all(_instant(row["observed_at"]) <= _instant(population["observed_at"])
                  for row in (*cash.values(), *apps.values())), "OFFSET_POPULATION_OBSERVATION_ORDER")
        for identity, claim in claims.items():
            amount = claim_cash[identity]
            _need(amount <= claim["remaining"], "OFFSET_CLAIM_CASH_OVERAPPLICATION")
            claim["actual_cash_recovered"] += amount
            claim["remaining"] -= amount
        earning_sequences, earning_lines, offset_lines = set(), [], []
        total_earnings, total_offsets, total_payable = Fraction(), Fraction(), Fraction()
        for row in sorted(rows["future_earnings"].values(), key=lambda item: (item["effective_date"], item["sequence"])):
            _fields(row, {"id", "scope", "amount", "effective_date", "sequence", "observed_at", "source_ref", "upstream_ref", "evidence_ref"})
            current_fact(row, "future_earning")
            day = _day(row["effective_date"])
            _need(period_start <= day < period_end, "OFFSET_EARNING_PERIOD")
            _need(type(row["sequence"]) is int and row["sequence"] >= 0 and row["sequence"] not in earning_sequences, "OFFSET_EARNING_SEQUENCE")
            earning_sequences.add(row["sequence"])
            reference = _line(row["upstream_ref"])
            _need(reference not in earning_refs, "OFFSET_EARNING_LINE_ALREADY_RECOGNIZED")
            earning_refs.add(reference)
            original_amount = capacity = _q(row["amount"])
            for claim in sorted(claims.values(), key=lambda item: (item["priority"], item["sequence"])):
                if day < _day(claim["eligible_from"]):
                    continue
                applied = min(capacity, claim["remaining"])
                if applied:
                    before_claim, before_capacity = claim["remaining"], capacity
                    claim["remaining"] -= applied
                    claim["earning_offsets"] += applied
                    capacity -= applied
                    offset_lines.append({"earning_id": row["id"], "claim_id": claim["id"], "priority": claim["priority"], "sequence": claim["sequence"],
                                         "capacity_before": before_capacity, "claim_before": before_claim, "amount": applied,
                                         "capacity_after": capacity, "claim_after": claim["remaining"]})
            total_earnings += original_amount
            total_offsets += original_amount - capacity
            total_payable += capacity
            earning_lines.append({"id": row["id"], "effective_date": row["effective_date"], "amount": original_amount,
                                  "earning_offset": original_amount - capacity, "payable_calculated": capacity, "upstream_ref": reference})
        _need(total_earnings == total_offsets + total_payable, "OFFSET_EARNING_RECONCILIATION")
        for claim in claims.values():
            _need(claim["authorized_amount"] == claim["actual_cash_recovered"] + claim["earning_offsets"] + claim["remaining"], "OFFSET_CLAIM_RECONCILIATION")
        total_authorized_original = sum((claim["authorized_amount"] for claim in claims.values() if claim["kind"] == "original_overpayment"), Fraction())
        return {"current_returned_basis": current_reversal, "current_signed_reversal": -current_reversal * original_rate,
                "returned_basis": returned, "cumulative_signed_reversal": -returned * original_rate,
                "revised_original_entitlement": revised, "original_outstanding": max(revised - paid, Fraction()),
                "potential_overpayment": potential, "total_authorized_original": total_authorized_original,
                "unallocated_overpayment_capacity": potential - total_authorized_original,
                "current_actual_cash_recovered": current_cash, "future_earnings": total_earnings,
                "current_earning_offsets": total_offsets, "payable_calculated": total_payable,
                "earning_lines": earning_lines, "offset_lines": offset_lines,
                "claims": [claims[key] for key in sorted(claims)]}

    previous_end, normalized, used_cases = None, [], {case_id}
    for row in sorted(history, key=lambda record: record["period"]["start"]):
        _fields(row, {"source_case_id", "period", "as_of", "cutoff", *PERIOD_ARRAYS})
        identity = _text(row["source_case_id"])
        _need(identity not in used_cases, "OFFSET_DUPLICATE_PERIOD_CASE")
        used_cases.add(identity)
        history_start, history_end = _period(row["period"])
        _need(history_end <= start and (previous_end is None or previous_end == history_start), "OFFSET_HISTORY_BOUNDARY")
        process(row)
        previous_end = history_end
        normalized.append({**row, **{key: sorted(row[key], key=lambda item: item["id"]) for key in PERIOD_ARRAYS}})
    _need(returned == _q(opening["returned_basis"]) and exact_json([claims[key] for key in sorted(claims)]) == opening["claims"]
          and (not history or (previous_end == start and normalized[-1]["source_case_id"] == opening["source_case_id"])), "OFFSET_OPENING_HISTORY_RECONCILIATION")
    current = {"source_case_id": case_id, "period": dict(data["period"]), "as_of": data["as_of"], "cutoff": data["cutoff"],
               **{key: sorted(data[key], key=lambda item: item["id"]) for key in PERIOD_ARRAYS}}
    result = process(current)
    closing = {"scope": dict(scope), "purpose": "authorized_original_recovery", "policy_id": POLICY_ID, "policy_revision": "1", "priority_recipe": recipe,
               "original_bundle": dict(bundle), "boundary": data["period"]["end"], "origin": "prior_result", "source_case_id": case_id,
               "returned_basis": returned, "claims": result["claims"], "period_history": normalized + [current]}
    return {"source_case_id": case_id, "period": dict(data["period"]), "original_gross": gross, "original_issued": _q(issued["amount"]),
            "original_actual_paid": paid, "original_paid_as_of": snapshot["as_of"], **result, "closing_state": closing,
            "original_payment_status": "complete_with_payments" if payments else "complete_no_events",
            "cash_recovery_status": "complete_with_recoveries" if data["cash_recoveries"] else "complete_no_events",
            "current_settlement_payment_status": "no_event_supplied",
            "status_meaning": "old obligation revision and separately authorized recovery; no new bank refund or settlement payment inferred"}


def authorized_offsets(data):
    """Return exact controls from original payment/reversal/authority populations."""
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, AuthorizedOffsetOracleError):
            raise
        raise AuthorizedOffsetOracleError("OFFSET_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(item) for item in value]
    return value
