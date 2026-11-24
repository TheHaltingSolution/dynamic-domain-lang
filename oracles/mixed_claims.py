"""Independent mixed recoupment credits/earning offsets over original facts."""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import re

POLICY_ID = "SYNTHETIC-MIXED-CLAIMS-01"
SCOPE_FIELDS = {"agreement_id", "pool_id", "asset_id", "participant_group", "purpose", "currency"}
KINDS = {"capital", "advance", "fee", "approved_correction"}
METHODS = {"priority_fee_first", "priority_correction_first", "pro_rata_eligible_balances"}
FRAME_FIELDS = {"case_id", "period", "as_of", "cutoff", "earnings", "earning_population", "cash_settlement_population", "evidence"}


class MixedClaimOracleError(ValueError):
    pass


def require(value, code):
    if not value: raise MixedClaimOracleError(code)


def fields(row, required):
    require(type(row) is dict and row.keys() == required, "MIXED_RECORD_FIELDS")


def text(value):
    require(type(value) is str and bool(value) and all(not 0xD800 <= ord(c) <= 0xDFFF for c in value), "MIXED_TEXT_IDENTITY")
    return value


def q(value):
    require(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "MIXED_EXACT_NONNEGATIVE")
    return Fraction(value)


def day(value):
    require(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "MIXED_DATE")
    try: return date.fromisoformat(value)
    except ValueError: raise MixedClaimOracleError("MIXED_DATE") from None


def period(value):
    fields(value, {"start", "end"}); a, b = day(value["start"]), day(value["end"])
    require(a < b, "MIXED_PERIOD"); return a, b


def tick(value):
    require(type(value) is str, "MIXED_INSTANT")
    m = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    require(m is not None, "MIXED_INSTANT")
    d, h, minute, second, fraction, zone = m.groups(); h, minute, second = int(h), int(minute), int(second)
    require(h < 24 and minute < 60 and second < 60, "MIXED_INSTANT")
    offset = 0
    if zone.lower() != "z":
        zh, zm = int(zone[1:3]), int(zone[4:]); require(zone != "-00:00" and zh < 24 and zm < 60, "MIXED_INSTANT")
        offset = (zh * 60 + zm) * 60 * (1 if zone[0] == "+" else -1)
    result = Fraction(day(d).toordinal() * 86400 + h * 3600 + minute * 60 + second - offset) + Fraction(fraction or "0")
    require(86400 <= result < (date.max.toordinal() + 1) * 86400, "MIXED_INSTANT")
    return result


def line(value):
    text(value); a, marker, b = value.rpartition("#"); require(a and marker and b, "MIXED_ORIGINAL_LINE_REFERENCE"); return value


def index(rows):
    require(type(rows) is list and len(rows) <= 32, "MIXED_FINITE_ROWS")
    result = {}
    for row in rows:
        identity = text(row["id"]); require(identity not in result, "MIXED_DUPLICATE_ID"); result[identity] = row
    return result


def ids(values):
    require(type(values) is list and all(type(x) is str and x for x in values) and len(set(values)) == len(values), "MIXED_ID_LIST")
    return set(values)


def policy(method="priority_fee_first"):
    require(method in METHODS, "MIXED_METHOD")
    return {"id": POLICY_ID, "revision": "1", "method": method, "fund": "original_current_group_earning_capacity",
            "fee_treatment": "claim_only_not_pre_deduction", "correction_treatment": "prospective_offset_not_second_reversal",
            "event_order": "date_then_unique_sequence", "claim_order": "kind_priority_then_eligible_date_then_sequence",
            "residual": "complete_original_roster_positive_weight_sum", "current_cash_settlement": "complete_empty_only",
            "new_claims": "genesis_registry_only", "rounding": "exact_no_rounding", "evidence_class": "research_assumption"}


def _normalized_registry(raw):
    result = deepcopy(raw)
    for key,value in result.items():
        if isinstance(value,list):
            result[key] = sorted(value,key=lambda row: row.get("id",row.get("participant_id",""))) if value and isinstance(value[0],dict) else sorted(value)
    return result


def _support(scope, evidence, cutoff):
    def support(row, kind):
        require(row["scope"] == scope, "MIXED_FACT_SCOPE"); text(row["source_ref"])
        require(row["evidence_ref"] in evidence, "MIXED_EVIDENCE_REQUIRED")
        ev = evidence[row["evidence_ref"]]
        require(ev["kind"] == kind and tick(ev["observed_at"]) <= tick(row["observed_at"]) < cutoff, "MIXED_SOURCE_OBSERVATION_AUTHORITY")
    return support


def _evidence(rows, scope, cutoff):
    result = index(rows)
    for row in result.values():
        fields(row, {"id", "scope", "kind", "approved", "observed_at", "source_ref"})
        require(row["scope"] == scope and row["approved"] is True and tick(row["observed_at"]) < cutoff, "MIXED_EVIDENCE_SCOPE_APPROVAL_CUTOFF")
        text(row["kind"]); text(row["source_ref"])
    return result


def _registry(raw, scope, selected, first_start, as_of, cutoff):
    fields(raw, {"participant_ids", "payer_id", "earning_terms", "roster_authority", "residual_weights", "capital_fundings", "advance_fundings", "funding_populations",
                 "fee_bases", "correction_sources", "historical_payments", "historical_applications", "historical_payment_populations", "claim_authorities", "evidence"})
    participants = ids(raw["participant_ids"]); require(scope["participant_group"] in participants and raw["payer_id"] in participants
                    and raw["payer_id"] != scope["participant_group"], "MIXED_PARTY_ROLES")
    require(len(participants)<=12,"MIXED_PARTICIPANT_BOUND")
    for participant in participants:text(participant)
    evidence = _evidence(raw["evidence"], scope, cutoff); support = _support(scope, evidence, cutoff)
    tables = {key: index(raw[key]) for key in ("capital_fundings", "advance_fundings", "funding_populations", "fee_bases", "correction_sources", "historical_payments", "historical_applications", "historical_payment_populations", "claim_authorities")}
    require(len(tables["claim_authorities"]) <= 8, "MIXED_CLAIM_BOUND")
    terms = raw["earning_terms"]
    fields(terms, {"id", "scope", "payer_id", "share", "effective", "approved", "approved_date", "observed_at", "original_ref", "source_ref", "evidence_ref"})
    support(terms, "earning_terms"); period(terms["effective"])
    require(terms["payer_id"] == raw["payer_id"] and terms["approved"] is True and day(terms["approved_date"]) <= as_of and q(terms["share"]) <= 1, "MIXED_EARNING_TERMS")
    require(day(terms["approved_date"]).toordinal()*86400 <= tick(terms["observed_at"]),"MIXED_SOURCE_CHRONOLOGY")
    line(terms["original_ref"])
    roster = raw["roster_authority"]
    fields(roster, {"id", "scope", "complete", "member_ids", "approved", "observed_at", "original_ref", "source_ref", "evidence_ref"})
    support(roster, "residual_roster")
    members = ids(roster["member_ids"])
    line(roster["original_ref"])
    require(roster["complete"] is True and roster["approved"] is True and members and members <= participants and scope["participant_group"] not in members, "MIXED_COMPLETE_RESIDUAL_ROSTER")
    require(len(members)<=8 and type(raw["residual_weights"]) is list and len(raw["residual_weights"])<=8,"MIXED_ROSTER_BOUND")
    weights = {}
    for row in raw["residual_weights"]:
        fields(row, {"participant_id", "weight"}); key = text(row["participant_id"])
        require(key not in weights, "MIXED_DUPLICATE_RESIDUAL_MEMBER"); weights[key] = q(row["weight"])
    require(weights.keys() == members and sum(weights.values(), Fraction()) > 0, "MIXED_RESIDUAL_WEIGHT_POPULATION")
    bank_refs, source_refs = set(), set()
    funding = {}; capacities = {}
    def unique(reference, pool, code):
        ref = line(reference); require(ref not in pool, code); pool.add(ref); return ref
    for kind in ("capital", "advance"):
        group = tables[kind + "_fundings"]
        for row in group.values():
            fields(row, {"id", "scope", "funder_id", "recipient_group", "amount", "funded_at", "observed_at", "original_ref", "source_ref", "evidence_ref"})
            support(row, "actual_" + kind + "_funding")
            require(row["funder_id"] in participants and row["funder_id"] != scope["participant_group"] and row["recipient_group"] == scope["participant_group"], "MIXED_FUNDING_PARTIES")
            funded = tick(row["funded_at"])
            require(first_start.toordinal() * 86400 <= funded <= tick(row["observed_at"])
                    and funded // 86400 <= as_of.toordinal(), "MIXED_FUNDING_CHRONOLOGY")
            unique(row["original_ref"], bank_refs, "MIXED_BANK_LINE_ALIAS"); funding[(kind, row["id"])] = q(row["amount"])
        pops = [row for row in tables["funding_populations"].values() if row["kind"] == kind]
        require(len(pops) == 1 and pops[0]["complete"] is True, "MIXED_COMPLETE_FUNDING_POPULATION_REQUIRED")
        pop = pops[0]; fields(pop, {"id", "scope", "kind", "complete", "funding_ids", "total", "observed_at", "source_ref", "evidence_ref"})
        support(pop, "complete_funding_population")
        require(ids(pop["funding_ids"]) == group.keys() and q(pop["total"]) == sum((q(row["amount"]) for row in group.values()), Fraction()), "MIXED_FUNDING_POPULATION_CONTROL")
        require(all(tick(row["observed_at"]) <= tick(pop["observed_at"]) for row in group.values()), "MIXED_POPULATION_OBSERVATION")
    require(all(row["kind"] in {"capital", "advance"} for row in tables["funding_populations"].values()), "MIXED_FUNDING_KIND")
    fees = {}
    for row in tables["fee_bases"].values():
        fields(row, {"id", "scope", "creditor_id", "debtor_group", "base_amount", "rate", "effective_date", "observed_at", "original_ref", "source_ref", "evidence_ref"})
        support(row, "original_fee_basis")
        require(row["creditor_id"] == raw["payer_id"] and row["debtor_group"] == scope["participant_group"] and q(row["rate"]) <= 1
                and first_start <= day(row["effective_date"]) <= as_of, "MIXED_FEE_SOURCE_AUTHORITY")
        require(day(row["effective_date"]).toordinal()*86400 <= tick(row["observed_at"]),"MIXED_SOURCE_CHRONOLOGY")
        unique(row["original_ref"], source_refs, "MIXED_FEE_CORRECTION_LINE_ALIAS"); fees[row["id"]] = q(row["base_amount"]) * q(row["rate"])
    corrections = {}; original_controls = []
    apps_by_payment = {key: Fraction() for key in tables["historical_payments"]}
    apps_by_source = {key: Fraction() for key in tables["correction_sources"]}
    for row in tables["correction_sources"].values():
        fields(row, {"id", "scope", "payer_id", "recipient_group", "original_basis", "original_rate", "original_date", "original_entitlement_ref", "return_basis", "return_date", "return_ref", "observed_at", "original_ref", "source_ref", "evidence_ref"})
        support(row, "original_correction_measurements")
        require(row["payer_id"] == raw["payer_id"] and row["recipient_group"] == scope["participant_group"] and q(row["original_rate"]) <= 1
                and q(row["return_basis"]) <= q(row["original_basis"]) and day(row["original_date"]) <= day(row["return_date"])
                and first_start <= day(row["return_date"]) <= as_of, "MIXED_CORRECTION_SOURCE")
        require(day(row["return_date"]).toordinal()*86400 <= tick(row["observed_at"]),"MIXED_SOURCE_CHRONOLOGY")
        for key in ("original_ref", "original_entitlement_ref", "return_ref"): unique(row[key], source_refs, "MIXED_FEE_CORRECTION_LINE_ALIAS")
    for row in tables["historical_payments"].values():
        fields(row, {"id", "scope", "correction_source_id", "payer_id", "recipient_group", "amount", "paid_at", "observed_at", "original_ref", "source_ref", "evidence_ref"})
        support(row, "actual_historical_participation_payment")
        require(row["correction_source_id"] in tables["correction_sources"] and row["payer_id"] == raw["payer_id"] and row["recipient_group"] == scope["participant_group"]
                and tick(row["paid_at"]) < first_start.toordinal() * 86400 and tick(row["paid_at"]) <= tick(row["observed_at"]), "MIXED_ORIGINAL_PAYMENT_SCOPE_CHRONOLOGY")
        require(day(tables["correction_sources"][row["correction_source_id"]]["original_date"]).toordinal()*86400 <= tick(row["paid_at"]),"MIXED_ORIGINAL_PAYMENT_SCOPE_CHRONOLOGY")
        unique(row["original_ref"], bank_refs, "MIXED_BANK_LINE_ALIAS"); q(row["amount"])
    for row in tables["historical_applications"].values():
        fields(row, {"id", "scope", "payment_id", "correction_source_id", "original_entitlement_ref", "amount", "approved", "observed_at", "source_ref", "evidence_ref"})
        support(row, "historical_participation_application")
        require(row["payment_id"] in tables["historical_payments"] and row["correction_source_id"] in tables["correction_sources"], "MIXED_ORIGINAL_APPLICATION_REFERENCE")
        payment = tables["historical_payments"][row["payment_id"]]; original = tables["correction_sources"][row["correction_source_id"]]
        require(row["approved"] is True and payment["correction_source_id"] == row["correction_source_id"]
                and row["original_entitlement_ref"] == original["original_entitlement_ref"] and tick(payment["observed_at"]) <= tick(row["observed_at"]), "MIXED_ORIGINAL_APPLICATION_AUTHORITY")
        apps_by_payment[row["payment_id"]] += q(row["amount"]); apps_by_source[row["correction_source_id"]] += q(row["amount"])
    require(all(apps_by_payment[key] == q(row["amount"]) for key,row in tables["historical_payments"].items()), "MIXED_ORIGINAL_PAYMENT_CONSERVATION")
    for key,row in tables["correction_sources"].items():
        pops = [pop for pop in tables["historical_payment_populations"].values() if pop["correction_source_id"] == key]
        require(len(pops) == 1 and pops[0]["complete"] is True, "MIXED_COMPLETE_ORIGINAL_PAYMENT_POPULATION_REQUIRED")
        pop = pops[0]; fields(pop, {"id", "scope", "correction_source_id", "complete", "payment_ids", "application_ids", "paid_total", "observed_at", "source_ref", "evidence_ref"})
        support(pop, "complete_original_payment_population")
        payment_ids = {p["id"] for p in tables["historical_payments"].values() if p["correction_source_id"] == key}
        application_ids = {a["id"] for a in tables["historical_applications"].values() if a["correction_source_id"] == key}
        require(ids(pop["payment_ids"]) == payment_ids and ids(pop["application_ids"]) == application_ids and q(pop["paid_total"]) == apps_by_source[key], "MIXED_ORIGINAL_PAYMENT_POPULATION_CONTROL")
        require(all(tick(tables["historical_payments"][p]["observed_at"]) <= tick(pop["observed_at"]) for p in payment_ids)
                and all(tick(tables["historical_applications"][a]["observed_at"]) <= tick(pop["observed_at"]) for a in application_ids), "MIXED_POPULATION_OBSERVATION")
        original = q(row["original_basis"]) * q(row["original_rate"]); reversal = q(row["return_basis"]) * q(row["original_rate"]); revised = original - reversal; paid = apps_by_source[key]
        require(paid <= original, "MIXED_ORIGINAL_PAID_CEILING")
        potential = max(paid - revised, Fraction()); corrections[key] = potential
        original_controls.append({"id": key, "original_entitlement": original, "reversal": reversal, "revised_entitlement": revised,
                                  "actual_original_paid": paid, "original_outstanding": max(revised-paid, Fraction()), "potential_overpayment": potential})
    require(all(pop["correction_source_id"] in tables["correction_sources"] for pop in tables["historical_payment_populations"].values()), "MIXED_ORIGINAL_POPULATION_REFERENCE")
    priorities = {"fee":0,"approved_correction":1,"capital":2,"advance":3}
    if selected["method"] == "priority_correction_first": priorities.update(approved_correction=0, fee=1)
    claims, orders, authority_refs, backing_used = {}, set(), set(), set()
    for row in tables["claim_authorities"].values():
        fields(row, {"id", "scope", "kind", "beneficiary", "source_ids", "authorized_principal", "priority", "sequence", "eligible_from", "approved", "approved_date", "recorded_date", "observed_at", "original_ref", "source_ref", "evidence_ref"})
        support(row, "claim_authority"); kind = row["kind"]
        require(kind in KINDS and row["beneficiary"] in participants and row["beneficiary"] != scope["participant_group"], "MIXED_CLAIM_KIND_BENEFICIARY")
        require(row["approved"] is True and first_start <= day(row["eligible_from"]) and day(row["approved_date"]) <= day(row["recorded_date"]) <= day(row["eligible_from"])
                and day(row["recorded_date"]) <= as_of, "MIXED_PROSPECTIVE_AUTHORITY")
        require(day(row["recorded_date"]).toordinal()*86400 <= tick(row["observed_at"]),"MIXED_SOURCE_CHRONOLOGY")
        require(type(row["priority"]) is int and row["priority"] == priorities[kind] and type(row["sequence"]) is int and row["sequence"] >= 0, "MIXED_PRIORITY_RECIPE")
        order = (row["priority"], row["eligible_from"], row["sequence"]); require(order not in orders, "MIXED_UNRESOLVED_CLAIM_ORDER"); orders.add(order)
        unique(row["original_ref"], authority_refs, "MIXED_AUTHORITY_LINE_ALIAS")
        source_ids = ids(row["source_ids"]); capacity = Fraction()
        for source_id in source_ids:
            token = (kind, source_id); require(token not in backing_used, "MIXED_CLAIM_SOURCE_REUSE"); backing_used.add(token)
            if kind in {"capital", "advance"}:
                require(token in funding and tables[kind + "_fundings"][source_id]["funder_id"] == row["beneficiary"], "MIXED_CLAIM_FUNDING_AUTHORITY")
                capacity += funding[token]
                require(tick(tables[kind + "_fundings"][source_id]["funded_at"]) // 86400 <= day(row["eligible_from"]).toordinal(), "MIXED_SOURCE_ELIGIBILITY")
            else:
                require(row["beneficiary"] == raw["payer_id"], "MIXED_RECIPROCAL_OFFSET_AUTHORITY")
                source_table = fees if kind == "fee" else corrections
                require(source_id in source_table, "MIXED_CLAIM_SOURCE_REFERENCE"); capacity += source_table[source_id]
                source_row = tables["fee_bases" if kind == "fee" else "correction_sources"][source_id]
                require(day(source_row["effective_date" if kind == "fee" else "return_date"]) <= day(row["eligible_from"]), "MIXED_SOURCE_ELIGIBILITY")
        principal = q(row["authorized_principal"]); require(principal <= capacity, "MIXED_AUTHORIZED_PRINCIPAL_EXCEEDS_SOURCE")
        claims[row["id"]] = {"id": row["id"], "kind": kind, "beneficiary": row["beneficiary"], "source_capacity": capacity,
                             "authorized_principal": principal, "unallocated_source_capacity": capacity-principal, "recoupment_credit": Fraction(),
                             "earning_offset": Fraction(), "remaining": principal, "authority": deepcopy(row)}
    source_controls = {"capital_actual_funding": sum((q(r["amount"]) for r in tables["capital_fundings"].values()),Fraction()),
                       "advance_actual_funding": sum((q(r["amount"]) for r in tables["advance_fundings"].values()),Fraction()),
                       "fee_sources": [{"id":r["id"],"original_base":q(r["base_amount"]),"original_rate":q(r["rate"]),"derived_fee":fees[r["id"]]} for r in sorted(tables["fee_bases"].values(),key=lambda r:r["id"])],
                       "correction_sources": sorted(original_controls,key=lambda row:row["id"])}
    return claims, weights, source_controls, source_refs | bank_refs, _normalized_registry(raw)


def _period(frame, scope, selected, raw_registry, first_start, ledger, allocation_ledger, offset_ledger, seen):
    fields(frame, FRAME_FIELDS); text(frame["case_id"])
    start,end = period(frame["period"]); as_of,cutoff = day(frame["as_of"]),tick(frame["cutoff"])
    require(as_of == end-timedelta(days=1) and cutoff >= end.toordinal()*86400, "MIXED_COMPLETE_PERIOD")
    principals, weights, source_controls, static_refs, normalized = _registry(raw_registry,scope,selected,first_start,as_of,cutoff)
    if ledger is None: ledger = principals
    evidence = _evidence(frame["evidence"],scope,cutoff); support = _support(scope,evidence,cutoff)
    cash = frame["cash_settlement_population"]
    fields(cash,{"id","scope","period","complete","event_ids","total","observed_at","source_ref","evidence_ref"})
    support(cash,"complete_current_claim_cash_settlement_population")
    require(cash["complete"] is True and cash["period"] == frame["period"],"MIXED_CURRENT_CASH_SETTLEMENT_UNKNOWN")
    require(tick(cash["observed_at"])>=end.toordinal()*86400,"MIXED_FINAL_POPULATION_OBSERVATION")
    require(cash["event_ids"] == [] and q(cash["total"]) == 0,"MIXED_NONEMPTY_CASH_SETTLEMENT_VARIANT_REQUIRED")
    earnings = index(frame["earnings"]); orders = set()
    for row in earnings.values():
        fields(row,{"id","scope","base_amount","effective_date","sequence","original_ref","observed_at","source_ref","evidence_ref"})
        support(row,"current_group_earning_basis"); when=day(row["effective_date"])
        require(start<=when<end and when.toordinal()*86400<=tick(row["observed_at"]),"MIXED_EARNING_PERIOD_OBSERVATION")
        require(type(row["sequence"]) is int and row["sequence"]>=0 and (when,row["sequence"]) not in orders,"MIXED_UNRESOLVED_EARNING_ORDER");orders.add((when,row["sequence"]))
        ref=line(row["original_ref"]);require(ref not in static_refs,"MIXED_FUND_SOURCE_AMOUNT_SPACE_OVERLAP")
        require(row["id"] not in seen["earning_ids"] and ref not in seen["earning_refs"],"MIXED_EARNING_REPLAY_ALIAS")
        seen["earning_ids"].add(row["id"]);seen["earning_refs"].add(ref);q(row["base_amount"])
    pop=frame["earning_population"]
    fields(pop,{"id","scope","period","complete","earning_ids","gross_basis_total","observed_at","source_ref","evidence_ref"})
    support(pop,"complete_earning_population")
    require(pop["complete"] is True and pop["period"]==frame["period"] and ids(pop["earning_ids"])==earnings.keys()
            and q(pop["gross_basis_total"])==sum((q(r["base_amount"]) for r in earnings.values()),Fraction()),"MIXED_COMPLETE_EARNING_POPULATION")
    require(tick(pop["observed_at"])>=end.toordinal()*86400,"MIXED_FINAL_POPULATION_OBSERVATION")
    require(all(tick(r["observed_at"])<=tick(pop["observed_at"]) for r in earnings.values()),"MIXED_POPULATION_OBSERVATION")
    terms=raw_registry["earning_terms"]; ts,te=period(terms["effective"])
    current_allocations,current_offsets,movements,residuals,events=[],[],[],[],[]
    total_capacity=total_credit=total_offset=total_residual=Fraction()
    for earning in sorted(earnings.values(),key=lambda row:(row["effective_date"],row["sequence"])):
        when=day(earning["effective_date"])
        require(ts<=when<te and day(terms["approved_date"])<=when,"MIXED_EARNING_TERMS_EFFECTIVE")
        capacity=q(earning["base_amount"])*q(terms["share"]);funds=capacity;total_capacity+=capacity
        eligible=[c for c in ledger.values() if day(c["authority"]["eligible_from"])<=when]
        eligible.sort(key=lambda c:(c["authority"]["priority"],c["authority"]["eligible_from"],c["authority"]["sequence"]))
        total_balance=sum((c["remaining"] for c in eligible),Fraction());pool=min(capacity,total_balance)
        for claim in eligible:
            require(tick(claim["authority"]["observed_at"])<=tick(earning["observed_at"]),"MIXED_AUTHORITY_NOT_KNOWN_AT_EARNING")
            before=claim["remaining"];applied=min(funds,before) if selected["method"]!="pro_rata_eligible_balances" else (pool*before/total_balance if total_balance else Fraction())
            require(0<=applied<=before and applied<=funds,"MIXED_CLAIM_OVERAPPLICATION")
            offset=claim["kind"] in {"fee","approved_correction"}
            classification="earning_offset" if offset else "recoupment_credit"
            claim[classification]+=applied;claim["remaining"]-=applied
            movements.append({"earning_id":earning["id"],"claim_id":claim["id"],"kind":claim["kind"],"application_kind":classification,
                              "opening_remaining":before,"available_before":funds,"applied":applied,"closing_remaining":claim["remaining"],"available_after":funds-applied})
            funds-=applied
            record={"key":[frame["case_id"],earning["original_ref"],classification,claim["authority"]["original_ref"]],"source_case_id":frame["case_id"],
                    "earning_id":earning["id"],"claim_id":claim["id"],"kind":claim["kind"],"beneficiary":claim["beneficiary"],"amount":applied,
                    "measure":"calculated_setoff_not_cash" if offset else "unissued_recoupment_allocation_not_bank_repayment"}
            if applied:
                (current_offsets if offset else current_allocations).append(record)
            if offset:total_offset+=applied
            else:total_credit+=applied
        for beneficiary,weight in sorted(weights.items()):
            amount=funds*weight/sum(weights.values(),Fraction())
            residuals.append({"earning_id":earning["id"],"participant_id":beneficiary,"weight":weight,"residual_entitlement":amount})
            if amount:current_allocations.append({"key":[frame["case_id"],earning["original_ref"],"residual",beneficiary],"source_case_id":frame["case_id"],
                "earning_id":earning["id"],"kind":"residual","beneficiary":beneficiary,"amount":amount,"measure":"unissued_residual_entitlement_not_cash"})
        total_residual+=funds;events.append({"earning":deepcopy(earning),"original_share":terms["share"],"derived_capacity":capacity,"eligible_opening_balance":total_balance,"recovery_pool":pool,"residual":funds})
    allocation_ledger.extend(current_allocations);offset_ledger.extend(current_offsets)
    require(total_capacity==total_credit+total_offset+total_residual,"MIXED_CAPACITY_RECONCILIATION")
    require(all(c["authorized_principal"]==c["recoupment_credit"]+c["earning_offset"]+c["remaining"] for c in ledger.values()),"MIXED_CLAIM_RECONCILIATION")
    result={"source_case_id":frame["case_id"],"period":deepcopy(frame["period"]),"status":"calculated","capacity":total_capacity,"recoupment_credits":total_credit,
            "earning_offsets":total_offset,"residual_entitlement":total_residual,"unissued_allocations_added":total_credit+total_residual,
            "event_details":events,"claim_movements":movements,"residual_lines":residuals,"claim_ledger":[deepcopy(ledger[key]) for key in sorted(ledger)],
            "current_unissued_allocations":current_allocations,"current_offset_records":current_offsets,
            "original_correction_controls":source_controls["correction_sources"],"original_source_controls":source_controls,
            "actual_current_claim_cash_settlement":Fraction(),"cash_evidence_status":"complete_original_empty_population","bank_movement_created":False}
    return result,ledger,normalized


def _calculate(data):
    fields(data,{"schema_version","scope","policy","research","registry","opening_state",*FRAME_FIELDS}|({"prior_result"} if "prior_result" in data else set()))
    require(data["schema_version"]=="mixed-claims-neutral/1","MIXED_SCHEMA")
    scope,selected=data["scope"],data["policy"];fields(scope,SCOPE_FIELDS)
    for value in scope.values():text(value)
    require(scope["currency"]=="USD" and scope["purpose"]=="mixed_claim_recovery","MIXED_SCOPE_PURPOSE_CURRENCY")
    require(selected==policy(selected["method"]),"MIXED_SELECTED_POLICY")
    fields(data["research"],{"atomic_catalog_sha256","waterfall_policy_sha256","offset_policy_sha256","scope_note"})
    for key in ("atomic_catalog_sha256","waterfall_policy_sha256","offset_policy_sha256"):
        require(type(data["research"][key]) is str and re.fullmatch(r"[0-9a-f]{64}",data["research"][key]),"MIXED_REVIEW_PIN")
    require(data["research"]["scope_note"]=="C07.MIXED_CLAIM_KINDS;capital/advance/correction plus fee-priority composition","MIXED_REVIEW_SCOPE")
    opening=data["opening_state"];require(type(opening) is dict and opening.get("origin") in {"genesis","prior_result"},"MIXED_OPENING")
    history=opening.get("history",[]);require(type(history) is list and len(history)<=3,"MIXED_HISTORY_BOUND")
    if opening["origin"]=="prior_result":
        require(opening.get("scope")==scope and opening.get("policy")==selected and opening.get("research")==data["research"]
                and opening.get("registry")==_normalized_registry(data["registry"]),"MIXED_REGISTRY_AMENDMENT_OR_NEW_CLAIM")
    first_start=day(history[0]["facts"]["period"]["start"]) if history else day(data["period"]["start"])
    ledger,normalized=None,None;allocations,offsets,replayed=[],[],[];seen={"earning_ids":set(),"earning_refs":set()};previous_end=None;expected=None
    def state(frame):
        return exact_json({"schema_version":"mixed-claim-state/1","scope":deepcopy(scope),"policy":deepcopy(selected),"research":deepcopy(data["research"]),
            "registry":deepcopy(normalized),"boundary":frame["period"]["end"],"origin":"prior_result","source_case_id":frame["case_id"],"history":deepcopy(replayed),
            "claim_ledger":[deepcopy(ledger[key]) for key in sorted(ledger)],"unissued_allocation_ledger":deepcopy(allocations),"earning_offset_ledger":deepcopy(offsets),
            "consumed_earning_ids":sorted(seen["earning_ids"]),"consumed_earning_refs":sorted(seen["earning_refs"])})
    for record in history:
        fields(record,{"facts","result"});frame=record["facts"]
        if previous_end is not None:require(frame["period"]["start"]==previous_end,"MIXED_HISTORY_ADJACENCY")
        result,ledger,normalized=_period(frame,scope,selected,data["registry"],first_start,ledger,allocations,offsets,seen)
        require(exact_json(result)==record["result"],"MIXED_HISTORY_FINANCIAL_REPLAY")
        replayed.append(deepcopy(record));previous_end=frame["period"]["end"];expected=state(frame)
    if opening["origin"]=="genesis":
        require(opening=={"origin":"genesis","boundary":data["period"]["start"],"source_case_id":"genesis","history":[]} and "prior_result" not in data,"MIXED_GENESIS")
    else:
        require(history and opening==expected and previous_end==data["period"]["start"],"MIXED_OPENING_RECONCILIATION")
        require("prior_result" in data,"MIXED_PREDECESSOR_REQUIRED");prior=data["prior_result"]
        require(type(prior) is dict and {"source_case_id","period","closing_state"}<=prior.keys()<= {"source_case_id","period","closing_state","result_ref"},"MIXED_PREDECESSOR_FIELDS")
        require(prior["source_case_id"]==opening["source_case_id"] and prior["closing_state"]==opening and period(prior["period"])[1]==day(data["period"]["start"]),"MIXED_PREDECESSOR_MISMATCH")
        if "result_ref" in prior:text(prior["result_ref"])
    frame={key:deepcopy(data[key]) for key in FRAME_FIELDS}
    require(all(record["facts"]["case_id"]!=frame["case_id"] for record in history),"MIXED_CASE_REPLAY")
    result,ledger,normalized=_period(frame,scope,selected,data["registry"],first_start,ledger,allocations,offsets,seen)
    if history:require(normalized==opening["registry"],"MIXED_REGISTRY_AMENDMENT_OR_NEW_CLAIM")
    replayed.append({"facts":frame,"result":exact_json(result)})
    return {**result,"closing_state":state(frame)}


def mixed_claims(data):
    try:return _calculate(data)
    except (KeyError,TypeError,ValueError,ZeroDivisionError) as error:
        if isinstance(error,MixedClaimOracleError):raise
        raise MixedClaimOracleError("MIXED_MALFORMED_INPUT") from error


def exact_json(value):
    if isinstance(value,Fraction):return str(value)
    if isinstance(value,dict):return {key:exact_json(child) for key,child in value.items()}
    if isinstance(value,(tuple,list)):return [exact_json(child) for child in value]
    return value
