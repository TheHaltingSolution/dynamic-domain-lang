"""Independent synthetic reserve-stage/cap/tranche original-history controls.

No existing reserve implementation/oracle, compiler, adapter, filesystem or
clock is consulted. Generic unconditional releases are not sourced clearance.
"""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import calendar
import re

SCOPE = {"agreement_id", "participant_id", "pool_id", "asset_id", "currency", "purpose"}
COMMON = {"id", "scope", "observed_at", "source_ref", "evidence_ref"}
FRAME = {"case_id", "period", "as_of", "cutoff", "receipts", "elections", "applications", "authorities", "population", "evidence"}
PURPOSES = {"basis_reserve": "synthetic_gross_basis_reserve", "producer_holdback": "synthetic_producer_entitlement_holdback"}
MEASURES = {"basis_reserve": "gross_basis_USD", "producer_holdback": "producer_entitlement_USD"}


class ReserveStageOracleError(ValueError):
    pass


def require(condition, code):
    if not condition: raise ReserveStageOracleError(code)


def fields(value, names):
    require(type(value) is dict and value.keys() == set(names), "RS_FIELDS")


def text(value):
    require(type(value) is str and value and all(not 0xD800 <= ord(char) <= 0xDFFF for char in value), "RS_TEXT")
    return value


def amount(value):
    if type(value) is str:
        require(re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", value) is not None, "RS_EXACT_NONNEGATIVE")
        return Fraction(value)
    fields(value, {"numerator", "denominator"})
    n, d = value["numerator"], value["denominator"]
    require(type(n) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)", n) is not None and type(d) is str and re.fullmatch(r"[1-9][0-9]*", d) is not None, "RS_EXACT_NONNEGATIVE")
    result = Fraction(int(n), int(d))
    require(str(result.numerator) == n and str(result.denominator) == d, "RS_NORMALIZED_FRACTION")
    return result


def day(value):
    require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is not None, "RS_DATE")
    try: return date.fromisoformat(value)
    except ValueError: raise ReserveStageOracleError("RS_DATE") from None


def tick(value):
    require(type(value) is str, "RS_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    require(match is not None, "RS_INSTANT")
    d, h, m, s, part, zone = match.groups(); h, m, s = int(h), int(m), int(s)
    require(h < 24 and m < 60 and s < 60, "RS_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:]); require(zh < 24 and zm < 60, "RS_INSTANT")
        offset = (zh * 60 + zm) * 60 * (1 if zone[0] == "+" else -1)
    # Numeric -00:00 retains known UTC and unknown local offset. No local
    # calendar interpretation is made; original lexemes remain in history.
    result = Fraction(day(d).toordinal() * 86400 + h * 3600 + m * 60 + s - offset) + Fraction(part or "0")
    require(86400 <= result < (date.max.toordinal() + 1) * 86400, "RS_INSTANT")
    return result


def midnight(value): return Fraction(day(value).toordinal() * 86400)


def span(value):
    fields(value, {"start", "end"}); a, b = day(value["start"]), day(value["end"])
    require(a < b, "RS_PERIOD"); return a, b


def due_date(original, months, mode):
    start = day(original); ordinal = start.year * 12 + start.month - 1 + months
    year, month = divmod(ordinal, 12); month += 1
    require(1 <= year <= 9999, "RS_RELEASE_DATE_RANGE")
    maximum = calendar.monthrange(year, month)[1]
    require(start.day <= maximum or mode == "clamp_day", "RS_RELEASE_INVALID_DAY")
    return date(year, month, min(start.day, maximum)).isoformat()


def index(rows, limit=8):
    require(type(rows) is list and len(rows) <= limit, "RS_ROW_BOUND")
    result = {}
    for row in rows:
        require(type(row) is dict, "RS_FIELDS"); identity = text(row["id"])
        require(identity not in result, "RS_DUPLICATE_ID"); result[identity] = row
    return result


def identities(value):
    require(type(value) is list and len(value) <= 8, "RS_POPULATION_IDS")
    for identity in value: text(identity)
    require(len(set(value)) == len(value), "RS_POPULATION_IDS")
    return set(value)


def evidence(rows, scope, cutoff):
    result = index(rows, 32)
    for row in result.values():
        fields(row, {"id", "scope", "kind", "approved", "observed_at", "source_ref"})
        require(row["scope"] == scope and row["approved"] is True and tick(row["observed_at"]) < cutoff, "RS_EVIDENCE_SCOPE_APPROVAL_CUTOFF")
        text(row["kind"]); text(row["source_ref"])
    return result


def support(row, kind, ev, scope, cutoff):
    require(row["scope"] == scope, "RS_FACT_SCOPE"); text(row["id"]); text(row["source_ref"])
    require(row["evidence_ref"] in ev, "RS_EVIDENCE_REQUIRED")
    selected = ev[row["evidence_ref"]]
    require(selected["kind"] == kind and tick(selected["observed_at"]) <= tick(row["observed_at"]) < cutoff, "RS_SOURCE_OBSERVATION")


def unknown_local_offsets(value, path=""):
    result = []
    if isinstance(value, dict):
        for key, item in value.items():
            location = path + "." + key if path else key
            if key in {"observed_at", "cutoff"} and isinstance(item, str) and item.endswith("-00:00"): result.append(location)
            result.extend(unknown_local_offsets(item, location))
    elif isinstance(value, list):
        for position, item in enumerate(value): result.extend(unknown_local_offsets(item, path + "." + str(position)))
    return result


def policy(stage="basis_reserve"):
    require(stage in PURPOSES, "RS_STAGE")
    return {"id": "SYNTHETIC-RESERVE-STAGES-01", "revision": "1", "stage": stage, "reserve_measure": MEASURES[stage], "fee": "fixed_once_per_original_receipt", "cap": "limit_addition_with_unretained_current",
        "order": "daily_receipts_then_ordered_applications_then_due_tranches", "release": "unconditional_under_supplied_generic_terms", "rounding": "exact_no_rounding", "evidence_class": "research_assumption"}


def validate_terms(terms, registry_evidence, scope, cutoff):
    fields(terms, COMMON | {"version", "approved", "approved_date", "effective", "reserve_rate", "participation_share", "fixed_fee", "retained_cap", "reserve_measure", "calendar_mode", "release_schedule"})
    support(terms, "generic_reserve_terms", registry_evidence, scope, cutoff)
    text(terms["version"]); require(terms["approved"] is True and midnight(terms["approved_date"]) <= tick(terms["observed_at"]), "RS_TERMS_AUTHORITY")
    span(terms["effective"])
    require(amount(terms["reserve_rate"]) <= 1 and amount(terms["participation_share"]) <= 1, "RS_RATIO_RANGE")
    amount(terms["fixed_fee"]); amount(terms["retained_cap"])
    require(terms["calendar_mode"] in {"clamp_day", "reject_invalid_day"}, "RS_CALENDAR_MODE")
    rules = terms["release_schedule"]
    require(type(rules) is list and 1 <= len(rules) <= 2, "RS_RELEASE_SCHEDULE")
    previous, seen = 0, set()
    for position, row in enumerate(rules):
        final = position == len(rules) - 1
        fields(row, {"id", "offset_months", "kind"} | ({"fraction"} if not final else set()))
        identity = text(row["id"]); require(identity not in seen, "RS_RELEASE_SCHEDULE"); seen.add(identity)
        months = row["offset_months"]
        require(type(months) is int and previous < months <= 24, "RS_RELEASE_SCHEDULE"); previous = months
        require(row["kind"] == ("all_remaining" if final else "fraction_of_original_addition"), "RS_RELEASE_SCHEDULE")
        if not final: require(amount(row["fraction"]) <= 1, "RS_RELEASE_SCHEDULE")


def _run(data):
    fields(data, {"schema_version", "scope", "policy", "terms", "registry_evidence", "opening_state", *FRAME} | ({"prior_result"} if "prior_result" in data else set()))
    require(data["schema_version"] == "reserve-stages-neutral/1", "RS_SCHEMA")
    scope = data["scope"]; fields(scope, SCOPE)
    for value in scope.values(): text(value)
    selected = data["policy"]; require(type(selected) is dict and selected == policy(selected["stage"]), "RS_POLICY")
    stage = selected["stage"]
    require(scope["currency"] == "USD" and scope["purpose"] == PURPOSES[stage], "RS_SCOPE_STAGE_UNIT")
    terms = data["terms"]; opening = data["opening_state"]
    require(type(opening) is dict and opening.get("origin") in {"genesis", "prior_result"}, "RS_OPENING")
    history = opening.get("history", []); require(type(history) is list and len(history) <= 3, "RS_HISTORY_BOUND")
    frames = [deepcopy(row["facts"]) for row in history] + [{key: deepcopy(data[key]) for key in FRAME}]
    minimum = min(tick(row["cutoff"]) for row in frames)
    registry_ev = evidence(data["registry_evidence"], scope, minimum)
    validate_terms(terms, registry_ev, scope, minimum)
    require(terms["reserve_measure"] == MEASURES[stage], "RS_SCOPE_STAGE_UNIT")
    if opening["origin"] == "genesis":
        require(opening == {"origin": "genesis", "boundary": frames[0]["period"]["start"], "source_case_id": "genesis", "history": []} and "prior_result" not in data, "RS_GENESIS")
    else:
        require(opening.get("scope") == scope and opening.get("policy") == selected and opening.get("terms") == terms and opening.get("registry_evidence") == data["registry_evidence"], "RS_PINNED_CONTEXT")
        require("prior_result" in data, "RS_PREDECESSOR_REQUIRED")
        prior = data["prior_result"]; fields(prior, {"source_case_id", "period", "result_ref", "closing_state"}); text(prior["result_ref"])
        require(bool(history) and prior["source_case_id"] == opening["source_case_id"] and prior["closing_state"] == opening and prior["period"] == history[-1]["facts"]["period"] and prior["period"]["end"] == data["period"]["start"], "RS_PREDECESSOR_MISMATCH")
    vintages = {}; seen_receipts = set(); receipt_refs = set(); seen_elections = set(); seen_apps = set(); app_refs = set(); seen_authorities = set(); fee_keys = set(); cases = set(); replayed = []; expected = None
    cumulative = {key: Fraction() for key in ("gross", "fee", "producer", "nonparticipant", "applications", "additions", "releases")}
    boundary = frames[0]["period"]["start"]
    for frame in frames:
        fields(frame, FRAME); text(frame["case_id"])
        require(frame["case_id"] not in cases, "RS_DUPLICATE_CASE"); cases.add(frame["case_id"])
        start, end = span(frame["period"]); cutoff = tick(frame["cutoff"])
        require(frame["period"]["start"] == boundary and day(frame["as_of"]) == end - timedelta(days=1) and cutoff >= midnight(frame["period"]["end"]), "RS_COMPLETE_ADJACENT_PERIOD")
        if frame is frames[-1] and opening["origin"] == "prior_result": require(expected == opening, "RS_OPENING_RECONCILIATION")
        ev = evidence(frame["evidence"], scope, cutoff)
        tables = {key: index(frame[key]) for key in ("receipts", "elections", "applications", "authorities")}
        for key, kind in (("receipts", "original_gross_basis"), ("elections", "reserve_election"), ("applications", "reserve_application"), ("authorities", "reserve_application_authority")):
            for row in tables[key].values():
                extras = {"original_ref", "event_date", "sequence", "gross"} if key == "receipts" else {"receipt_id", "vintage_id", "elected", "approved", "approved_date", "event_date"} if key == "elections" else {"original_ref", "vintage_id", "amount", "event_date", "sequence", "authority_id", "reserve_measure"} if key == "applications" else {"application_id", "vintage_id", "approved", "approved_date", "reserve_measure"}
                fields(row, COMMON | extras); support(row, kind, ev, scope, cutoff)
                if key in {"receipts", "applications"}:
                    require(type(row["sequence"]) is int and row["sequence"] >= 0 and start <= day(row["event_date"]) < end and midnight(row["event_date"]) <= tick(row["observed_at"]), "RS_EVENT_ORDER_PERIOD")
                    text(row["original_ref"]); amount(row["gross"] if key == "receipts" else row["amount"])
        require({row["receipt_id"] for row in tables["elections"].values()} == tables["receipts"].keys() and len(tables["elections"]) == len(tables["receipts"]), "RS_COMPLETE_ELECTIONS")
        require({row["application_id"] for row in tables["authorities"].values()} == tables["applications"].keys() and len(tables["authorities"]) == len(tables["applications"]), "RS_COMPLETE_AUTHORITIES")
        for election in tables["elections"].values():
            text(election["vintage_id"]); receipt = tables["receipts"][election["receipt_id"]]
            require(type(election["elected"]) is bool and election["approved"] is True and election["event_date"] == receipt["event_date"] and day(election["approved_date"]) <= day(receipt["event_date"]) and tick(receipt["observed_at"]) <= tick(election["observed_at"]), "RS_ELECTION_AUTHORITY")
        for authority in tables["authorities"].values():
            application = tables["applications"][authority["application_id"]]
            require(authority["id"] not in seen_authorities, "RS_AUTHORITY_REUSE")
            require(authority["approved"] is True and authority["vintage_id"] == application["vintage_id"] and application["authority_id"] == authority["id"] and authority["reserve_measure"] == application["reserve_measure"] == MEASURES[stage] and day(authority["approved_date"]) <= day(application["event_date"]) and midnight(authority["approved_date"]) <= tick(authority["observed_at"]) <= tick(application["observed_at"]), "RS_APPLICATION_AUTHORITY")
        pop = frame["population"]
        fields(pop, COMMON | {"period", "complete", "receipt_ids", "election_ids", "application_ids", "authority_ids", "gross_total", "application_total"}); support(pop, "complete_current_population", ev, scope, cutoff)
        require(pop["complete"] is True and pop["period"] == frame["period"] and all(identities(pop[key + "_ids"]) == tables[table].keys() for key, table in (("receipt", "receipts"), ("election", "elections"), ("application", "applications"), ("authority", "authorities"))), "RS_COMPLETE_POPULATION")
        require(amount(pop["gross_total"]) == sum((amount(row["gross"]) for row in tables["receipts"].values()), Fraction()) and amount(pop["application_total"]) == sum((amount(row["amount"]) for row in tables["applications"].values()), Fraction()), "RS_POPULATION_TOTAL")
        require(tick(pop["observed_at"]) >= midnight(frame["period"]["end"]) and all(tick(row["observed_at"]) <= tick(pop["observed_at"]) for table in tables.values() for row in table.values()), "RS_POPULATION_OBSERVATION")
        receipt_keys = [(row["event_date"], row["sequence"]) for row in tables["receipts"].values()]; application_keys = [(row["event_date"], row["sequence"]) for row in tables["applications"].values()]
        require(len(set(receipt_keys)) == len(receipt_keys) and len(set(application_keys)) == len(application_keys), "RS_UNRESOLVED_STAGE_ORDER")
        opening_balance = sum((row["available"] for row in vintages.values()), Fraction())
        current = {key: Fraction() for key in cumulative}; receipt_details = []; application_details = []; releases = []
        pending = {day(row["event_date"]) for key in ("receipts", "applications") for row in tables[key].values()}
        for vintage in vintages.values():
            for tranche in vintage["tranches"]:
                if not tranche["processed"] and start <= day(tranche["due_date"]) < end: pending.add(day(tranche["due_date"]))
        # New receipts can introduce release dates inside the same supplied
        # interval. A finite sorted worklist preserves daily stage priority.
        while pending:
            today = min(pending); pending.remove(today)
            for receipt in sorted((row for row in tables["receipts"].values() if day(row["event_date"]) == today), key=lambda row: row["sequence"]):
                election = next(row for row in tables["elections"].values() if row["receipt_id"] == receipt["id"])
                require(receipt["id"] not in seen_receipts and receipt["original_ref"] not in receipt_refs and election["id"] not in seen_elections and election["vintage_id"] not in vintages, "RS_ORIGINAL_REUSE")
                require(len(vintages) < 4, "RS_VINTAGE_BOUND")
                a, z = span(terms["effective"])
                require(a <= today < z and day(terms["approved_date"]) <= today and tick(terms["observed_at"]) <= tick(receipt["observed_at"]), "RS_TERMS_NOT_KNOWN_EFFECTIVE")
                gross, fee, share, rate = amount(receipt["gross"]), amount(terms["fixed_fee"]), amount(terms["participation_share"]), amount(terms["reserve_rate"])
                retained = sum((row["available"] for row in vintages.values()), Fraction()); room = max(amount(terms["retained_cap"]) - retained, Fraction())
                require(gross >= fee, "RS_FIXED_FEE_FUNDING_VARIANT_REQUIRED")
                earnings = (gross - fee) * share
                raw_addition = (gross if stage == "basis_reserve" else earnings) * rate if election["elected"] else Fraction()
                addition = min(raw_addition, room)
                require(stage != "basis_reserve" or gross - addition >= fee, "RS_FIXED_FEE_FUNDING_VARIANT_REQUIRED")
                producer = (gross - addition - fee) * share if stage == "basis_reserve" else earnings - addition
                nonparticipant = (gross - addition - fee) * (1 - share) if stage == "basis_reserve" else (gross - fee) * (1 - share)
                fee_key = (terms["id"], receipt["original_ref"]); require(fee_key not in fee_keys, "RS_FEE_ALREADY_CONSUMED"); fee_keys.add(fee_key)
                tranches = [{"id": rule["id"], "kind": rule["kind"], "fraction": amount(rule["fraction"]) if "fraction" in rule else None, "due_date": due_date(receipt["event_date"], rule["offset_months"], terms["calendar_mode"]), "processed": False} for rule in terms["release_schedule"]]
                vintage = {"id": election["vintage_id"], "scope": deepcopy(scope), "reserve_measure": MEASURES[stage], "original_receipt": deepcopy(receipt), "original_election": deepcopy(election), "established_date": receipt["event_date"], "original_addition": addition, "raw_addition": raw_addition, "available": addition, "applied": Fraction(), "released": Fraction(), "fee_assessed_once": fee, "fee_key": list(fee_key), "liquidated": False, "tranches": tranches}
                vintages[vintage["id"]] = vintage; seen_receipts.add(receipt["id"]); receipt_refs.add(receipt["original_ref"]); seen_elections.add(election["id"])
                for tranche in tranches:
                    if start <= day(tranche["due_date"]) < end: pending.add(day(tranche["due_date"]))
                current["gross"] += gross; current["fee"] += fee; current["producer"] += producer; current["nonparticipant"] += nonparticipant; current["additions"] += addition
                receipt_details.append({"receipt_id": receipt["id"], "vintage_id": vintage["id"], "gross": gross, "fee_consumed": fee, "fee_key": list(fee_key), "raw_addition": raw_addition, "retained_before": retained, "cap_room_before": room, "addition": addition, "unretained_current": raw_addition - addition, "producer": producer, "nonparticipant": nonparticipant, "closing_retained_after_addition": retained + addition})
            for application in sorted((row for row in tables["applications"].values() if day(row["event_date"]) == today), key=lambda row: row["sequence"]):
                require(application["id"] not in seen_apps and application["original_ref"] not in app_refs, "RS_APPLICATION_REUSE")
                require(application["vintage_id"] in vintages, "RS_UNKNOWN_VINTAGE")
                vintage = vintages[application["vintage_id"]]
                require(not vintage["liquidated"], "RS_AFTER_TERM_APPLICATION_VARIANT_REQUIRED")
                require(day(vintage["established_date"]) <= today and tick(vintage["original_election"]["observed_at"]) <= tick(application["observed_at"]), "RS_APPLICATION_CHRONOLOGY")
                value = amount(application["amount"]); require(value <= vintage["available"], "RS_VINTAGE_APPLICATION_EXCEEDS_AVAILABLE")
                before = vintage["available"]; vintage["available"] -= value; vintage["applied"] += value; current["applications"] += value
                seen_apps.add(application["id"]); app_refs.add(application["original_ref"]); seen_authorities.add(application["authority_id"])
                application_details.append({"original": deepcopy(application), "opening_available": before, "applied": value, "closing_available": vintage["available"]})
            for vintage in sorted(vintages.values(), key=lambda row: row["id"]):
                for tranche in vintage["tranches"]:
                    if tranche["processed"] or day(tranche["due_date"]) != today: continue
                    before = vintage["available"]
                    quota = vintage["original_addition"] * tranche["fraction"] if tranche["kind"] == "fraction_of_original_addition" else before
                    value = min(before, quota); vintage["available"] -= value; vintage["released"] += value; tranche["processed"] = True
                    if tranche["kind"] == "all_remaining": vintage["liquidated"] = True
                    producer = value * amount(terms["participation_share"]) if stage == "basis_reserve" else value
                    nonparticipant = value - producer
                    current["releases"] += value; current["producer"] += producer; current["nonparticipant"] += nonparticipant
                    releases.append({"key": [vintage["id"], terms["id"], terms["version"], tranche["id"]], "vintage_id": vintage["id"], "tranche_id": tranche["id"], "due_date": tranche["due_date"], "basis": tranche["kind"], "original_addition": vintage["original_addition"], "opening_available": before, "quota": quota, "released": value, "closing_available": vintage["available"], "producer": producer, "nonparticipant": nonparticipant, "fee": Fraction()})
        for vintage in vintages.values():
            require(vintage["original_addition"] == vintage["applied"] + vintage["released"] + vintage["available"], "RS_VINTAGE_BRIDGE")
            require(all(tranche["processed"] or day(tranche["due_date"]) >= end for tranche in vintage["tranches"]), "RS_OVERDUE_RELEASE")
        closing = sum((row["available"] for row in vintages.values()), Fraction())
        require(current["gross"] + opening_balance == current["fee"] + current["producer"] + current["nonparticipant"] + current["applications"] + closing, "RS_PERIOD_BRIDGE")
        for key in cumulative: cumulative[key] += current[key]
        require(cumulative["gross"] == cumulative["fee"] + cumulative["producer"] + cumulative["nonparticipant"] + cumulative["applications"] + closing, "RS_CUMULATIVE_BRIDGE")
        latest = {"source_case_id": frame["case_id"], "period": deepcopy(frame["period"]), "stage": stage, "reserve_measure": MEASURES[stage], "status": "calculated", "opening_reserve": opening_balance, "current": current, "closing_reserve": closing,
            "receipt_details": receipt_details, "application_details": application_details, "release_details": releases, "vintages": deepcopy(sorted(vintages.values(), key=lambda row: row["id"])), "cumulative": deepcopy(cumulative), "fee_consumption_keys": [list(key) for key in sorted(fee_keys)],
            "issuance_status": "unissued_calculation", "payment_evidence_status": "not_part_of_profile", "bank_movement_created": False, "source_clearance_inferred": False, "release_policy": selected["release"],
            "observation_basis": "exact_UTC_no_local_date_inference", "unknown_local_offset_paths": unknown_local_offsets({"terms": terms, "registry_evidence": data["registry_evidence"], "frames": frames[:len(replayed) + 1]})}
        if frame is not frames[-1]:
            old = history[len(replayed)]; fields(old, {"facts", "result"}); require(exact_json(latest) == old["result"], "RS_HISTORY_FINANCIAL_REPLAY")
        replayed.append({"facts": deepcopy(frame), "result": exact_json(latest)}); boundary = frame["period"]["end"]
        expected = exact_json({"schema_version": "reserve-stages-state/1", "origin": "prior_result", "boundary": boundary, "source_case_id": frame["case_id"], "scope": deepcopy(scope), "policy": deepcopy(selected), "terms": deepcopy(terms), "registry_evidence": deepcopy(data["registry_evidence"]), "history": deepcopy(replayed),
            "vintages": deepcopy(sorted(vintages.values(), key=lambda row: row["id"])), "cumulative": deepcopy(cumulative), "fee_consumption_keys": [list(key) for key in sorted(fee_keys)], "consumed_receipt_ids": sorted(seen_receipts), "consumed_receipt_refs": sorted(receipt_refs), "consumed_election_ids": sorted(seen_elections), "consumed_application_ids": sorted(seen_apps), "consumed_application_refs": sorted(app_refs), "consumed_authority_ids": sorted(seen_authorities), "closing_reserve": closing})
    return {**latest, "closing_state": expected}


def reserve_stages(data):
    try: return _run(data)
    except (KeyError, TypeError, ValueError, StopIteration, ZeroDivisionError, OverflowError) as error:
        if isinstance(error, ReserveStageOracleError): raise
        raise ReserveStageOracleError("RS_MALFORMED_INPUT") from error


def exact_json(value):
    if isinstance(value, Fraction): return str(value)
    if isinstance(value, list): return [exact_json(item) for item in value]
    if isinstance(value, dict): return {key: exact_json(item) for key, item in value.items()}
    return value
