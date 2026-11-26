"""Independent bounded Genius-style basis reserve; no compiler calculation imports."""
from calendar import monthrange
from datetime import date, timedelta
from fractions import Fraction
import re


POLICY_ID = "RR04-GENIUS-BASIS-RESERVE-01"
SCOPE_FIELDS = {"contract_id", "participant_id", "pool_id", "asset_id", "currency"}
ARRAYS = ("checkpoints", "receipts", "elections", "returns", "return_authorities", "populations", "clearances", "evidence")


class BasisReserveOracleError(ValueError):
    pass


def _need(condition, code):
    if not condition:
        raise BasisReserveOracleError(code)


def _fields(row, fields, optional=()):
    _need(type(row) is dict and fields <= row.keys() <= fields | set(optional), "BR_RECORD_FIELDS")


def _text(value):
    _need(type(value) is str and bool(value), "BR_IDENTITY_REQUIRED")
    return value


def _q(value):
    _need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "BR_EXACT_NONNEGATIVE_VALUE")
    return Fraction(value)


def _day(value):
    _need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "BR_DATE")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise BasisReserveOracleError("BR_DATE") from None


def _period(value):
    _fields(value, {"start", "end"})
    first, last = _day(value["start"]), _day(value["end"])
    _need(first < last, "BR_PERIOD")
    return first, last


def _instant(value):
    _need(type(value) is str, "BR_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?(Z|[+-][0-9]{2}:[0-9]{2})", value)
    _need(match is not None, "BR_INSTANT")
    day, hour, minute, second, part, zone = match.groups()
    hour, minute, second = int(hour), int(minute), int(second)
    _need(hour < 24 and minute < 60 and second < 60, "BR_INSTANT")
    offset = 0
    if zone != "Z":
        zh, zm = int(zone[1:3]), int(zone[4:])
        _need(zone != "-00:00" and zh < 24 and zm < 60, "BR_INSTANT")
        offset = (zh * 3600 + zm * 60) * (1 if zone[0] == "+" else -1)
    result = Fraction(_day(day).toordinal() * 86400 + hour * 3600 + minute * 60 + second - offset) + Fraction(part or "0")
    _need(86400 <= result < (date.max.toordinal() + 1) * 86400, "BR_INSTANT")
    return result


def _add_six_months(day):
    """Selected anniversary + clamp-day convention, not month-end preservation."""
    months = (day.year - 1) * 12 + day.month - 1 + 6
    year, month0 = divmod(months, 12)
    year, month = year + 1, month0 + 1
    _need(year <= 9999, "BR_DATE_RANGE")
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def _index(rows):
    _need(type(rows) is list, "BR_RECORD_LIST")
    result = {}
    for row in rows:
        identity = _text(row["id"])
        _need(identity not in result, "BR_DUPLICATE_ID")
        result[identity] = row
    return result


def _ids(values):
    _need(type(values) is list and all(type(value) is str and value for value in values), "BR_POPULATION_IDS")
    _need(len(values) == len(set(values)), "BR_DUPLICATE_POPULATION_ID")
    return set(values)


def _line(value):
    _text(value)
    prefix, marker, suffix = value.rpartition("#")
    _need(bool(prefix and marker and suffix), "BR_ORIGINAL_LINE_REFERENCE")
    return value


def _calculate(data):
    _fields(data, {"schema_version", "case_id", "scope", "policy", "research", "authority", "run_checkpoint_id", *ARRAYS, "opening_state"}, {"prior_result"})
    _need(data["schema_version"] == "basis-reserves-neutral/1", "BR_SCHEMA")
    scope, policy, authority = data["scope"], data["policy"], data["authority"]
    _fields(scope, SCOPE_FIELDS)
    for value in scope.values():
        _text(value)
    _need(scope["currency"] == "USD", "BR_CURRENCY")
    _need(policy == {"id": POLICY_ID, "revision": "1", "method": "elected_basis_reserve_within_vintage_only", "excess_returns": "reject_pending_signed_policy",
                     "fee_stage": "after_basis_reserve", "liquidation": "full_unused_on_due_date", "months": "6", "invalid_day": "clamp_day",
                     "same_day_order": "receipt_election_then_return_then_due_release", "date_basis": "supplied_utc_date", "rounding": "exact_no_rounding",
                     "evidence_class": "research_assumption", "professional_review": "proposed"}, "BR_SELECTED_POLICY")
    _fields(data["research"], {"rr04_sha256", "ld03_sha256", "primary_url", "assignment_url", "clauses"})
    _need(data["research"]["primary_url"] == "https://www.sec.gov/Archives/edgar/data/1098016/000119312506200074/dex101.htm"
          and data["research"]["assignment_url"] == "https://www.sec.gov/Archives/edgar/data/1098016/000101968706002845/genius_10q-093006.htm"
          and data["research"]["clauses"] == "1-4;9(c);10-11;20;24(d)", "BR_RESEARCH_SOURCE")
    for field in ("rr04_sha256", "ld03_sha256"):
        _need(re.fullmatch(r"[0-9a-f]{64}", data["research"][field]) is not None, "BR_RESEARCH_PIN")
    rows = {key: _index(data[key]) for key in ARRAYS}
    checkpoints = sorted(rows["checkpoints"].values(), key=lambda row: row["period"]["start"])
    _need(1 <= len(checkpoints) <= 12 and len(rows["receipts"]) <= 24 and len(rows["returns"]) <= 48, "BR_FINITE_BOUND")
    _need(all(len(group) <= 256 for group in rows.values()), "BR_FINITE_BOUND")
    _need(checkpoints[-1]["id"] == data["run_checkpoint_id"] and checkpoints[-1]["source_case_id"] == data["case_id"], "BR_CURRENT_CHECKPOINT")
    cutoff = _instant(checkpoints[-1]["cutoff"])
    for row in rows["evidence"].values():
        _fields(row, {"id", "scope", "kind", "approved", "observed_at", "source_ref"})
        _need(row["scope"] == scope, "BR_EVIDENCE_SCOPE")
        _need(row["approved"] is True, "BR_EVIDENCE_APPROVAL")
        _text(row["kind"]); _text(row["source_ref"])
        _need(_instant(row["observed_at"]) < cutoff, "BR_EVIDENCE_AFTER_CUTOFF")

    def support(row, before=cutoff, kind=None):
        _need(row["scope"] == scope, "BR_FACT_SCOPE")
        _text(row["source_ref"])
        _need(row["evidence_ref"] in rows["evidence"], "BR_EVIDENCE_REQUIRED")
        evidence = rows["evidence"][row["evidence_ref"]]
        _need(_instant(row["observed_at"]) < before and _instant(evidence["observed_at"]) < before, "BR_SOURCE_AFTER_CUTOFF")
        if kind:
            _need(evidence["kind"] == kind, "BR_EVIDENCE_KIND")

    _fields(authority, {"id", "version", "scope", "effective", "sales_period_id", "reserve_rate", "fee_rate", "fee_substitute", "source_fee_redacted",
                        "original_distributor", "successor_id", "successor_authorized", "covered_program", "approved", "observed_at", "source_ref", "evidence_ref"})
    support(authority, kind="approved_successor_and_selected_sales_period_terms")
    _text(authority["id"]); _text(authority["version"])
    _need(authority["approved"] is True and authority["successor_authorized"] is True and authority["covered_program"] is True
          and bool(authority["successor_id"]) and authority["original_distributor"] == "Genius Products Inc.", "BR_SUCCESSOR_SCOPE_AUTHORITY")
    _need(authority["sales_period_id"] == "SalesPeriod3" and authority["effective"] == {"start": "2009-01-01", "end": "2010-01-01"}
          and _q(authority["reserve_rate"]) == Fraction(1, 5) and _q(authority["fee_rate"]) == Fraction(1, 10)
          and authority["fee_substitute"] == "synthetic_flat_10_percent" and authority["source_fee_redacted"] is True, "BR_SELECTED_TERMS")
    sale_start, sale_end = _period(authority["effective"])
    used_cases, previous_end, previous_cutoff = set(), None, None
    for row in checkpoints:
        _fields(row, {"id", "source_case_id", "scope", "period", "as_of", "cutoff", "approved", "observed_at", "source_ref", "evidence_ref"})
        support(row)
        first, last = _period(row["period"])
        _need(sale_start <= first < last <= sale_end and _day(row["as_of"]) == last - timedelta(days=1), "BR_SALES_PERIOD_SCOPE")
        _need((previous_end is None and first == sale_start) or previous_end == first, "BR_CHECKPOINT_ADJACENCY")
        _need(row["approved"] is True and row["source_case_id"] not in used_cases and row["source_case_id"] != "", "BR_CHECKPOINT_AUTHORITY_ID")
        _need(_instant(row["cutoff"]) >= last.toordinal() * 86400 and (previous_cutoff is None or previous_cutoff < _instant(row["cutoff"])), "BR_CHECKPOINT_CUTOFF")
        _need(_instant(row["observed_at"]) < _instant(row["cutoff"]), "BR_CHECKPOINT_OBSERVATION")
        used_cases.add(row["source_case_id"]); previous_end, previous_cutoff = last, _instant(row["cutoff"])

    election_receipts, vintage_ids, cash_refs = set(), set(), set()
    elections = rows["elections"]
    _need(len(elections) == len(rows["receipts"]), "BR_ELECTION_REQUIRED")
    for row in elections.values():
        _fields(row, {"id", "receipt_id", "vintage_id", "purpose", "scope", "elected", "election_date", "approved_date", "approved", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="original_reserve_election")
        _need(row["receipt_id"] in rows["receipts"] and row["receipt_id"] not in election_receipts, "BR_ELECTION_RECEIPT_REFERENCE")
        _need(row["vintage_id"] not in vintage_ids and row["purpose"] == "basis_stage_videogram_returns", "BR_VINTAGE_IDENTITY_PURPOSE")
        _need(row["approved"] is True and type(row["elected"]) is bool and _day(row["approved_date"]) <= _day(row["election_date"]), "BR_ELECTION_AUTHORITY")
        election_receipts.add(row["receipt_id"]); vintage_ids.add(_text(row["vintage_id"]))
    for row in rows["receipts"].values():
        _fields(row, {"id", "scope", "amount", "receipt_date", "sequence", "cash_received_country", "territory", "medium", "election_id", "cash_line_ref", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="actual_qualifying_gross_cash_receipt")
        _need(row["cash_received_country"] == "US" and row["territory"] == "US" and row["medium"] == "physical_videogram", "BR_US_PHYSICAL_PROFILE")
        _need(row["election_id"] in elections and elections[row["election_id"]]["receipt_id"] == row["id"], "BR_ELECTION_REQUIRED")
        _need(elections[row["election_id"]]["election_date"] == row["receipt_date"], "BR_SAME_DAY_ESTABLISHMENT")
        reference = _line(row["cash_line_ref"])
        _need(reference not in cash_refs, "BR_CASH_PARENT_ALIAS")
        cash_refs.add(reference); _q(row["amount"])

    returned_ids, claim_ids, return_refs = set(), set(), set()
    for row in rows["return_authorities"].values():
        _fields(row, {"id", "return_id", "receipt_id", "vintage_id", "scope", "purpose", "approved", "approved_date", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="approved_original_return_application")
        _need(row["return_id"] in rows["returns"] and row["return_id"] not in returned_ids, "BR_UNUSED_RETURN_AUTHORITY")
        _need(row["approved"] is True and row["purpose"] == "basis_stage_videogram_returns", "BR_RETURN_AUTHORITY")
        returned_ids.add(row["return_id"])
    _need(returned_ids == set(rows["returns"]), "BR_RETURN_AUTHORITY_REQUIRED")
    for row in rows["returns"].values():
        _fields(row, {"id", "scope", "receipt_id", "vintage_id", "claim_id", "amount", "return_date", "sequence", "authority_id", "return_line_ref", "observed_at", "source_ref", "evidence_ref"})
        support(row, kind="actual_customer_return")
        _need(row["receipt_id"] in rows["receipts"] and row["authority_id"] in rows["return_authorities"], "BR_RETURN_REFERENCE")
        linked = rows["return_authorities"][row["authority_id"]]
        receipt = rows["receipts"][row["receipt_id"]]
        election = elections[receipt["election_id"]]
        _need((linked["return_id"], linked["receipt_id"], linked["vintage_id"]) == (row["id"], row["receipt_id"], row["vintage_id"])
              and row["vintage_id"] == election["vintage_id"], "BR_RETURN_VINTAGE_LINEAGE")
        _need(_day(receipt["receipt_date"]) <= _day(row["return_date"]) and _day(linked["approved_date"]) <= _day(row["return_date"]), "BR_RETURN_DATE_AUTHORITY")
        _need(_instant(linked["observed_at"]) <= _instant(row["observed_at"]), "BR_RETURN_OBSERVATION_ORDER")
        reference = _line(row["return_line_ref"])
        _need(row["claim_id"] not in claim_ids and reference not in return_refs, "BR_RETURN_CLAIM_ALIAS")
        claim_ids.add(_text(row["claim_id"])); return_refs.add(reference); _q(row["amount"])
    for key, day_field in (("receipts", "receipt_date"), ("returns", "return_date")):
        sequences, sources = set(), set()
        for row in rows[key].values():
            day = _day(row[day_field])
            _need(type(row["sequence"]) is int and row["sequence"] >= 0 and (day, row["sequence"]) not in sequences, "BR_EXPLICIT_EVENT_SEQUENCE")
            sequences.add((day, row["sequence"]))
            _need(row["source_ref"] not in sources, "BR_SOURCE_ALIAS")
            sources.add(row["source_ref"])
            containing = [cp for cp in checkpoints if _period(cp["period"])[0] <= day < _period(cp["period"])[1]]
            _need(len(containing) == 1, "BR_EVENT_WINDOW")
            support(row, _instant(containing[0]["cutoff"]))
            _need(day.toordinal() * 86400 <= _instant(row["observed_at"]), "BR_EVENT_OBSERVATION_ORDER")
    for key in ("populations", "clearances"):
        for row in rows[key].values():
            support(row)
            _need(row["checkpoint_id"] in rows["checkpoints"], "BR_CONTROL_CHECKPOINT_REFERENCE")

    vintages, movements, snapshots, states = {}, [], [], []
    cumulative = {key: Fraction() for key in ("gross", "added", "applied_returns", "released", "net_receipts", "fee", "allocation")}
    for index, checkpoint in enumerate(checkpoints):
        first, last = _period(checkpoint["period"])
        as_of, before = _day(checkpoint["as_of"]), _instant(checkpoint["cutoff"])
        support(authority, before); support(checkpoint, before)
        population = [row for row in rows["populations"].values() if row["checkpoint_id"] == checkpoint["id"]]
        _need(len(population) == 1 and population[0]["complete"] is True, "BR_COMPLETE_POPULATION_REQUIRED")
        control = population[0]
        _fields(control, {"id", "checkpoint_id", "scope", "complete", "receipt_ids", "receipt_total", "election_ids", "return_ids", "return_total", "authority_ids", "other_adjustment_ids", "other_adjustment_total", "observed_at", "source_ref", "evidence_ref"})
        support(control, before, "complete_original_reserve_population")
        visible_receipts = {identity: row for identity, row in rows["receipts"].items() if _day(row["receipt_date"]) <= as_of}
        visible_returns = {identity: row for identity, row in rows["returns"].items() if _day(row["return_date"]) <= as_of}
        visible_elections = {row["election_id"] for row in visible_receipts.values()}
        visible_authorities = {row["authority_id"] for row in visible_returns.values()}
        _need(_ids(control["receipt_ids"]) == set(visible_receipts) and _q(control["receipt_total"]) == sum((_q(row["amount"]) for row in visible_receipts.values()), Fraction())
              and _ids(control["return_ids"]) == set(visible_returns) and _q(control["return_total"]) == sum((_q(row["amount"]) for row in visible_returns.values()), Fraction())
              and _ids(control["election_ids"]) == visible_elections and _ids(control["authority_ids"]) == visible_authorities, "BR_ORIGINAL_POPULATION_CONTROL")
        _need(_ids(control["other_adjustment_ids"]) == set() and _q(control["other_adjustment_total"]) == 0, "BR_OTHER_ADJUSTMENT_VARIANT_REQUIRED")
        for row in [*visible_receipts.values(), *visible_returns.values(), *(elections[key] for key in visible_elections), *(rows["return_authorities"][key] for key in visible_authorities)]:
            support(row, before)
            _need(_instant(row["observed_at"]) <= _instant(control["observed_at"]), "BR_POPULATION_OBSERVATION_ORDER")
        clearance = [row for row in rows["clearances"].values() if row["checkpoint_id"] == checkpoint["id"]]
        _need(len(clearance) == 1, "BR_CLAIM_CLEARANCE_REQUIRED")
        clearance = clearance[0]
        _fields(clearance, {"id", "checkpoint_id", "scope", "complete", "approved", "minimum_guarantee_remaining", "expense_remaining", "unresolved_claim_ids", "observed_at", "source_ref", "evidence_ref"})
        support(clearance, before, "complete_cleared_recoupment_claims")
        _need(clearance["complete"] is True and clearance["approved"] is True and _q(clearance["minimum_guarantee_remaining"]) == 0
              and _q(clearance["expense_remaining"]) == 0 and _ids(clearance["unresolved_claim_ids"]) == set(), "BR_CLAIMS_NOT_CLEARED")
        current_receipts = [row for row in visible_receipts.values() if first <= _day(row["receipt_date"]) < last]
        current_returns = [row for row in visible_returns.values() if first <= _day(row["return_date"]) < last]
        days = {_day(row["receipt_date"]) for row in current_receipts} | {_day(row["return_date"]) for row in current_returns}
        days |= {_day(row["due_date"]) for row in vintages.values() if first <= _day(row["due_date"]) < last}
        days |= {_add_six_months(_day(row["receipt_date"])) for row in current_receipts if first <= _add_six_months(_day(row["receipt_date"])) < last}
        start_movement = len(movements)
        totals = {key: Fraction() for key in cumulative}
        for day in sorted(days):
            for receipt in sorted((row for row in current_receipts if _day(row["receipt_date"]) == day), key=lambda row: row["sequence"]):
                election = elections[receipt["election_id"]]
                gross = _q(receipt["amount"])
                addition = gross * _q(authority["reserve_rate"]) if election["elected"] else Fraction()
                vintage = {"id": election["vintage_id"], "scope": dict(scope), "purpose": election["purpose"], "receipt_id": receipt["id"],
                           "cash_line_ref": receipt["cash_line_ref"], "election_id": election["id"], "election_record": dict(election),
                           "reserve_elected": election["elected"], "origin_date": receipt["receipt_date"], "due_date": _add_six_months(day).isoformat(),
                           "added": addition, "applied_returns": Fraction(), "released": Fraction(), "available": addition,
                           "return_ids": [], "claim_ids": [], "release_ids": []}
                _need(vintage["id"] not in vintages, "BR_VINTAGE_ALREADY_ESTABLISHED")
                vintages[vintage["id"]] = vintage
                totals["gross"] += gross; totals["added"] += addition
                net = gross - addition
                fee = net * _q(authority["fee_rate"])
                movements.append({"id": "addition:" + receipt["id"], "kind": "receipt_and_election", "date": day.isoformat(), "receipt_id": receipt["id"],
                                  "vintage_id": vintage["id"], "election_id": election["id"], "source_ref": receipt["source_ref"], "gross": gross,
                                  "reserve_addition": addition, "return_applied": Fraction(), "release": Fraction(), "net_receipts": net, "fee": fee, "allocation": net - fee})
            for returned in sorted((row for row in current_returns if _day(row["return_date"]) == day), key=lambda row: row["sequence"]):
                _need(returned["vintage_id"] in vintages, "BR_ORIGINAL_VINTAGE_REQUIRED")
                vintage = vintages[returned["vintage_id"]]
                amount = _q(returned["amount"])
                _need(day <= _day(vintage["due_date"]), "BR_RETURN_AFTER_LIQUIDATION_VARIANT_REQUIRED")
                _need(amount <= vintage["available"], "BR_EXCESS_RETURN_VARIANT_REQUIRED")
                vintage["available"] -= amount; vintage["applied_returns"] += amount
                vintage["return_ids"].append(returned["id"]); vintage["claim_ids"].append(returned["claim_id"])
                totals["applied_returns"] += amount
                movements.append({"id": "return:" + returned["id"], "kind": "matched_actual_return", "date": day.isoformat(), "receipt_id": returned["receipt_id"],
                                  "vintage_id": vintage["id"], "claim_id": returned["claim_id"], "authority_id": returned["authority_id"], "source_ref": returned["source_ref"],
                                  "gross": Fraction(), "reserve_addition": Fraction(), "return_applied": amount, "release": Fraction(), "net_receipts": Fraction(), "fee": Fraction(), "allocation": Fraction()})
            for vintage in sorted(vintages.values(), key=lambda row: row["id"]):
                if _day(vintage["due_date"]) == day and vintage["available"] > 0:
                    amount = vintage["available"]
                    identity = "due-release:" + vintage["id"]
                    _need(not vintage["release_ids"], "BR_VINTAGE_ALREADY_RELEASED")
                    vintage["available"] = Fraction(); vintage["released"] += amount; vintage["release_ids"].append(identity)
                    totals["released"] += amount
                    fee = amount * _q(authority["fee_rate"])
                    movements.append({"id": identity, "kind": "calculated_due_unused_release", "date": day.isoformat(), "receipt_id": vintage["receipt_id"],
                                      "vintage_id": vintage["id"], "election_id": vintage["election_id"], "gross": Fraction(), "reserve_addition": Fraction(),
                                      "return_applied": Fraction(), "release": amount, "net_receipts": amount, "fee": fee, "allocation": amount - fee})
        current_lines = movements[start_movement:]
        totals["net_receipts"] = totals["gross"] - totals["added"] + totals["released"]
        totals["fee"] = totals["net_receipts"] * _q(authority["fee_rate"])
        totals["allocation"] = totals["net_receipts"] - totals["fee"]
        for key in cumulative:
            cumulative[key] += totals[key]
        balance = sum((row["available"] for row in vintages.values()), Fraction())
        _need(all(row["added"] == row["applied_returns"] + row["released"] + row["available"] for row in vintages.values()), "BR_VINTAGE_CONSERVATION")
        _need(all(row["available"] == 0 or _day(row["due_date"]) > as_of for row in vintages.values()), "BR_OVERDUE_UNRELEASED")
        _need(cumulative["gross"] - cumulative["applied_returns"] == cumulative["net_receipts"] + balance
              and cumulative["fee"] + cumulative["allocation"] == cumulative["net_receipts"], "BR_LEDGER_CONSERVATION")
        snapshots.append({"checkpoint_id": checkpoint["id"], "source_case_id": checkpoint["source_case_id"], "period": dict(checkpoint["period"]),
                          "as_of": checkpoint["as_of"], "cutoff": checkpoint["cutoff"], **totals, "closing_reserve": balance,
                          "movements": list(current_lines), "vintages": [deep_record(vintages[key]) for key in sorted(vintages)]})
        processed = {row["id"] for row in checkpoints[:index + 1]}
        source = {}
        for key in ARRAYS:
            values = []
            for row in rows[key].values():
                visible = _instant(row["observed_at"]) < before
                if key == "checkpoints":
                    visible = visible and row["id"] in processed
                elif key in ("populations", "clearances"):
                    visible = visible and row["checkpoint_id"] in processed
                elif key == "receipts":
                    visible = visible and row["id"] in visible_receipts
                elif key == "elections":
                    visible = visible and row["id"] in visible_elections
                elif key == "returns":
                    visible = visible and row["id"] in visible_returns
                elif key == "return_authorities":
                    visible = visible and row["id"] in visible_authorities
                if visible:
                    values.append(row)
            source[key] = sorted(values, key=lambda row: row["id"])
        states.append({"scope": dict(scope), "purpose": "basis_stage_videogram_returns", "policy": dict(policy), "research": dict(data["research"]),
                       "authority": dict(authority), "boundary": checkpoint["period"]["end"], "origin": "prior_result", "source_case_id": checkpoint["source_case_id"],
                       "last_checkpoint_id": checkpoint["id"], "vintages": [deep_record(vintages[key]) for key in sorted(vintages)],
                       "cumulative": dict(cumulative), "movements": list(movements), "sources": source})
    opening = data["opening_state"]
    if len(checkpoints) == 1:
        _need(opening == {"scope": scope, "purpose": "basis_stage_videogram_returns", "policy": policy, "boundary": authority["effective"]["start"],
                          "origin": "genesis", "source_case_id": "genesis"} and "prior_result" not in data, "BR_GENESIS")
    else:
        _need(type(opening) is dict and opening.get("origin") in ("supplied_history", "prior_result"), "BR_OPENING_REQUIRED")
        _need(all(_q(row["available"]) == 0 or _day(row["due_date"]) >= _day(opening["boundary"]) for row in opening["vintages"]), "BR_OPENING_OVERDUE")
        expected = exact_json(states[-2]); expected["origin"] = opening["origin"]
        _need(opening == expected, "BR_OPENING_RECONCILIATION")
        if opening["origin"] == "prior_result":
            _need("prior_result" in data, "BR_PREDECESSOR_REQUIRED")
            prior = data["prior_result"]
            _fields(prior, {"source_case_id", "period", "closing_state"}, {"result_ref"})
            _need(prior["closing_state"] == opening and prior["source_case_id"] == opening["source_case_id"]
                  and _period(prior["period"])[1] == _period(checkpoints[-1]["period"])[0], "BR_PREDECESSOR_MISMATCH")
            if "result_ref" in prior:
                _text(prior["result_ref"])
        else:
            _need("prior_result" not in data, "BR_SUPPLIED_HISTORY_NOT_CANONICAL")
    return {"source_case_id": data["case_id"], "period": dict(checkpoints[-1]["period"]), "status": "calculated", **snapshots[-1],
            "checkpoint_results": snapshots, "cumulative": dict(cumulative), "closing_state": states[-1],
            "payment_status": "not_assessed_no_bank_payment_measure", "source_support": "partial_within_vintage_returns_only",
            "remaining_source_acceptance": "excess actual returns require separate signed Net Receipts/fee/allocation policy"}


def deep_record(value):
    """Copy calculation records without making historical snapshots alias mutation."""
    if isinstance(value, dict):
        return {key: deep_record(child) for key, child in value.items()}
    if isinstance(value, list):
        return [deep_record(child) for child in value]
    return value


def basis_reserves(data):
    try:
        return _calculate(data)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as error:
        if isinstance(error, BasisReserveOracleError):
            raise
        raise BasisReserveOracleError("BR_MALFORMED_NEUTRAL_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, dict):
        return {key: exact_json(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [exact_json(child) for child in value]
    return value
