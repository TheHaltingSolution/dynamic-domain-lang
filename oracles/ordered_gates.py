"""Original-fact finite ordered work gates. No compiler or source projection imports."""
from copy import deepcopy
from datetime import date
from fractions import Fraction
import re

METHODS = {"split_reopen", "opening_gate", "closing_gate", "continuous_history",
           "split_latch", "full_cross_reopen", "next_row_reopen"}
FRAME = {"case_id", "period", "cutoff", "rows", "populations", "evidence",
         "ordering_authority", "aggregate_hurdle", "net_worksheet"}
COMMON = {"id", "scope", "original_ref", "source_ref", "evidence_ref", "observed_at"}
SCOPE = {"agreement_id", "participant_id", "pool_id", "asset_id", "purpose", "currency"}


class OrderedGateOracleError(ValueError):
    pass


def need(test, code):
    if not test: raise OrderedGateOracleError(code)


def fields(row, keys):
    need(type(row) is dict and row.keys() == keys, "GATE_RECORD_FIELDS")


def text(value):
    need(type(value) is str and bool(value) and all(not 0xD800 <= ord(c) <= 0xDFFF for c in value), "GATE_TEXT")
    return value


def line(value):
    text(value); a, mark, b = value.rpartition("#")
    need(a and mark and b, "GATE_ORIGINAL_LINE"); return value


def q(value):
    need(type(value) is str and re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?", value), "GATE_EXACT_NONNEGATIVE")
    return Fraction(value)


def day(value):
    need(type(value) is str and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value), "GATE_DATE")
    try: return date.fromisoformat(value)
    except ValueError: raise OrderedGateOracleError("GATE_DATE") from None


def tick(value):
    need(type(value) is str, "GATE_INSTANT")
    match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})", value)
    need(match is not None, "GATE_INSTANT")
    d, h, m, s, f, z = match.groups(); h, m, s = int(h), int(m), int(s)
    need(h < 24 and m < 60 and s < 60, "GATE_INSTANT")
    offset = 0
    if z.lower() != "z":
        zh, zm = int(z[1:3]), int(z[4:]); need(z != "-00:00" and zh < 24 and zm < 60, "GATE_INSTANT")
        offset = (zh * 60 + zm) * 60 * (1 if z[0] == "+" else -1)
    result = Fraction(day(d).toordinal()*86400+h*3600+m*60+s-offset)+Fraction(f or "0")
    need(86400 <= result < (date.max.toordinal()+1)*86400, "GATE_INSTANT")
    return result


def midnight(value):
    return Fraction(day(value).toordinal()*86400)


def index(rows):
    need(type(rows) is list and len(rows) <= 64, "GATE_FINITE_ROWS")
    result = {}
    for row in rows:
        identity = text(row["id"]); need(identity not in result, "GATE_DUPLICATE_ID"); result[identity] = row
    return result


def policy(method="split_reopen"):
    need(method in METHODS, "GATE_METHOD")
    return {"id":"SYNTHETIC-LG-ORDERED-GATE-01", "revision":"1", "method":method,
            "evidence_class":"research_assumption", "event_order":"exact_instant_then_authorized_unique_sequence",
            "continuous":"opening_and_every_current_prefix", "latch":"positive_receipt_reaches_equality_from_false_genesis",
            "rounding":"exact_no_rounding", "fee_offset":"0", "reserve_movements":"0",
            "net":"separately_evidenced_zero_worksheet", "amendments":"unsupported"}


def _frame(frame, scope, registry, selected, balances, seen):
    fields(frame, FRAME); text(frame["case_id"])
    fields(frame["period"], {"start","end"}); start, end = (midnight(frame["period"][k]) for k in ("start","end"))
    cutoff = tick(frame["cutoff"]); need(start < end < cutoff, "GATE_PERIOD_CUTOFF")
    evidence = index(frame["evidence"]); used = set()
    for ev in evidence.values():
        fields(ev, {"id","scope","kind","source_ref","observed_at","approved"})
        text(ev["source_ref"]); need(ev["approved"] is True, "GATE_EVIDENCE_APPROVAL")
        need(tick(ev["observed_at"]) < cutoff, "GATE_EVIDENCE_CUTOFF")
    def support(row, kind, expected_scope):
        need(row["scope"] == expected_scope, "GATE_SCOPE"); text(row["id"]); text(row["source_ref"]); line(row["original_ref"])
        observed = tick(row["observed_at"]); need(observed < cutoff, "GATE_OBSERVATION_CUTOFF")
        ev = evidence.get(row["evidence_ref"]); need(ev is not None, "GATE_MISSING_EVIDENCE")
        need(ev["scope"] == expected_scope and ev["kind"] == kind, "GATE_EVIDENCE_SCOPE_KIND")
        need(tick(ev["observed_at"]) <= observed, "GATE_EVIDENCE_NOT_KNOWN")
        used.add(row["evidence_ref"]); return observed
    terms = registry["terms"]; fields(terms, COMMON | {"effective_start","effective_end","gross_rate","video_proxy","net_rate"})
    support(terms,"terms",scope)
    need(midnight(terms["effective_start"]) <= start and end <= midnight(terms["effective_end"]), "GATE_TERMS_EFFECTIVE")
    need(tick(terms["observed_at"]) <= start, "GATE_TERMS_NOT_KNOWN_AT_OPENING")
    rate, proxy, net_rate = (q(terms[k]) for k in ("gross_rate","video_proxy","net_rate"))
    need(max(rate,proxy,net_rate) <= 1, "GATE_RATE_RANGE")
    work = registry["work"]; fields(work, COMMON | {"purchaser_produced","eligible"})
    support(work,"work_eligibility",scope)
    need(work["purchaser_produced"] is True and work["eligible"] is True, "GATE_WORK_INELIGIBLE")
    need(tick(work["observed_at"]) <= start, "GATE_WORK_NOT_KNOWN_AT_OPENING")
    aggregate_scope = {k:scope[k] for k in ("agreement_id","participant_id","currency")}
    hurdle = frame["aggregate_hurdle"]; fields(hurdle, COMMON | {"effective_date","attained"})
    support(hurdle,"aggregate_hurdle",aggregate_scope)
    need(hurdle["attained"] is True and midnight(hurdle["effective_date"]) < start, "GATE_OUTSIDE_HURDLE_STRICT_BEFORE")
    net_scope = {**aggregate_scope,"pool_id":registry["net_pool_id"]}
    net = frame["net_worksheet"]; fields(net, COMMON | {"period","member_asset_ids","amount"})
    support(net,"net_worksheet",net_scope)
    need(net["period"] == frame["period"] and net["member_asset_ids"] == [scope["asset_id"]], "GATE_NET_PERIOD_MEMBERS")
    need(q(net["amount"]) == 0, "GATE_ONLY_SUPPLIED_ZERO_NET_PROFILE")
    rows = index(frame["rows"]); need(len(rows) <= 32, "GATE_FINITE_EVENTS")
    derived = {}; raw_totals = {"receipt":Fraction(),"cost":Fraction()}; selected_totals = dict(raw_totals)
    for row in rows.values():
        kind = row["kind"]; need(kind in raw_totals,"GATE_ROW_KIND")
        extra = {"received_at","earned_at","nonrefundable","channel","amount"} if kind == "receipt" else {"incurred_at","actual_third_party","gross_amount","reductions"}
        fields(row, COMMON | {"kind","sequence","decision"} | extra)
        observed = support(row,kind,scope)
        need(type(row["sequence"]) is int and row["sequence"] > 0, "GATE_SEQUENCE")
        decision = row["decision"]
        fields(decision,COMMON | {"event_ref","eligible","reason","channel"})
        decision_observed = support(decision,"classification",scope)
        need(decision["event_ref"] == row["original_ref"] and type(decision["eligible"]) is bool, "GATE_CLASSIFICATION_TARGET")
        text(decision["reason"]); need(decision_observed <= observed,"GATE_CLASSIFICATION_NOT_KNOWN")
        need(decision["id"] not in seen["decision_ids"] and decision["original_ref"] not in seen["decision_refs"],"GATE_CLASSIFICATION_REPLAY_OR_ALIAS")
        seen["decision_ids"].add(decision["id"]);seen["decision_refs"].add(decision["original_ref"])
        for identity, collection in ((row["id"],"ids"),(row["original_ref"],"refs")):
            need(identity not in seen[collection],"GATE_EVENT_REPLAY_OR_ALIAS"); seen[collection].add(identity)
        if kind == "receipt":
            when = max(tick(row["received_at"]),tick(row["earned_at"]))
            need(type(row["nonrefundable"]) is bool and row["channel"] in {"ordinary","home_video"}, "GATE_RECEIPT_CLASSIFICATION")
            need(decision["channel"] == row["channel"],"GATE_CHANNEL_AUTHORITY")
            amount = q(row["amount"])
            need(not decision["eligible"] or row["nonrefundable"],"GATE_REFUNDABLE_RECEIPT_UNSUPPORTED")
        else:
            when = tick(row["incurred_at"]); gross = q(row["gross_amount"]); reductions = index(row["reductions"])
            reduction = Fraction()
            for item in reductions.values():
                fields(item,COMMON | {"category","amount"}); adjustment_observed = support(item,"cost_reduction",scope)
                need(item["category"] in {"discount","rebate","allowance","insurance","soft_money"},"GATE_REDUCTION_CATEGORY")
                need(adjustment_observed <= observed,"GATE_REDUCTION_NOT_KNOWN")
                need(item["original_ref"] not in seen["refs"] and item["id"] not in seen["ids"],"GATE_EVENT_REPLAY_OR_ALIAS")
                seen["refs"].add(item["original_ref"]);seen["ids"].add(item["id"]); reduction += q(item["amount"])
            need(reduction <= gross,"GATE_COST_REDUCTION_OVERAPPLY"); amount = gross-reduction
            need(type(row["actual_third_party"]) is bool and decision["channel"] == "not_applicable","GATE_COST_CLASSIFICATION")
            need(not decision["eligible"] or row["actual_third_party"],"GATE_COST_NOT_ACTUAL_THIRD_PARTY")
        need(start <= when < end and when <= observed,"GATE_EVENT_CHRONOLOGY")
        need(tick(terms["observed_at"]) <= observed and tick(work["observed_at"]) <= observed,"GATE_AUTHORITY_NOT_KNOWN")
        raw_totals[kind] += q(row["amount"] if kind == "receipt" else row["gross_amount"])
        included = amount if decision["eligible"] else Fraction(); selected_totals[kind] += included
        derived[row["id"]] = (when,row["sequence"],included)
    populations = index(frame["populations"]); need(len(populations) == 2,"GATE_COMPLETE_POPULATIONS_REQUIRED")
    covered = set()
    for pop in populations.values():
        fields(pop,COMMON | {"period","kind","complete","event_ids","raw_total"})
        observed = support(pop,"population",scope); kind=pop["kind"]
        need(kind in raw_totals and kind not in covered,"GATE_POPULATION_KIND"); covered.add(kind)
        expected_ids = {r["id"] for r in rows.values() if r["kind"] == kind}
        need(pop["complete"] is True and pop["period"] == frame["period"] and observed >= end,"GATE_POPULATION_COMPLETENESS")
        need(type(pop["event_ids"]) is list and len(set(pop["event_ids"])) == len(pop["event_ids"]) and set(pop["event_ids"]) == expected_ids,"GATE_POPULATION_IDENTITIES")
        need(q(pop["raw_total"]) == raw_totals[kind],"GATE_POPULATION_TOTAL")
        need(all(tick(row["observed_at"]) <= observed for row in rows.values() if row["kind"]==kind),"GATE_POPULATION_NOT_AS_KNOWN_COMPLETE")
    order = frame["ordering_authority"]; fields(order,COMMON | {"period","keys"})
    support(order,"event_order",scope); need(order["period"] == frame["period"],"GATE_ORDER_PERIOD")
    need(type(order["keys"]) is list and len(order["keys"]) == len(rows),"GATE_ORDER_POPULATION")
    authority_keys = {}; economic_keys = set()
    for key in order["keys"]:
        fields(key,{"event_id","occurred_at","sequence"}); identity=key["event_id"]
        need(identity in derived and identity not in authority_keys,"GATE_ORDER_IDENTITIES")
        actual=(tick(key["occurred_at"]),key["sequence"])
        need(type(key["sequence"]) is int and actual == derived[identity][:2],"GATE_ORDER_AUTHORITY_MISMATCH")
        need(actual not in economic_keys,"GATE_UNRESOLVED_EVENT_TIE")
        economic_keys.add(actual);authority_keys[identity]=actual
    need(used == set(evidence),"GATE_UNUSED_EVIDENCE")
    R,C,latch = balances; opening_R,opening_C,opening_latch=R,C,latch
    continuous = R >= C; path=[]; method=selected["method"]
    for identity in sorted(rows,key=lambda identity:derived[identity][:2]):
        row=rows[identity]; when,sequence,amount=derived[identity]; before=R-C; was_latched=latch
        if row["kind"] == "receipt":
            R+=amount
            if amount>0 and R>=C:latch=True
        else:C+=amount
        after=R-C;continuous=continuous and after>=0
        path.append({"original":deepcopy(row),"occurred_at_exact":when,"sequence":sequence,"selected_full_amount":amount,
                     "pre_receipts":R-amount if row["kind"]=="receipt" else R,"pre_costs":C if row["kind"]=="receipt" else C-amount,
                     "pre_surplus":before,"post_receipts":R,"post_costs":C,"post_surplus":after,"latch_before":was_latched,"latch_after":latch})
    base=Fraction(); any_applicable=False
    for item in path:
        row=item["original"]; admitted=Fraction(); applicable=False; why="cost_updates_gate_only"
        if row["kind"]=="receipt":
            before,after,amount=item["pre_surplus"],item["post_surplus"],item["selected_full_amount"]
            if not row["decision"]["eligible"]: why="explicitly_excluded_receipt"
            elif method in {"opening_gate","closing_gate","continuous_history"}:
                applicable = {"opening_gate":opening_R>=opening_C,"closing_gate":R>=C,"continuous_history":continuous}[method]
                admitted=amount if applicable else Fraction();why="period_gate_eligible" if applicable else "period_gate_inapplicable"
            else:
                if method=="split_latch":
                    applicable=item["latch_before"] or after>=0
                    admitted=amount if item["latch_before"] else max(Fraction(),after)-max(Fraction(),before)
                elif method=="full_cross_reopen":
                    applicable=after>=0;admitted=amount if after>0 else Fraction()
                elif method=="next_row_reopen":
                    applicable=before>=0;admitted=amount if applicable else Fraction()
                else:
                    applicable=after>=0;admitted=max(Fraction(),after)-max(Fraction(),before)
                why="eligible_zero_at_equality" if applicable and admitted==0 else "eligible_receipt" if applicable else "gate_below_receipt"
            proxy_factor=proxy if row["channel"]=="home_video" else Fraction(1)
            contribution=admitted*proxy_factor; base+=contribution;any_applicable|=applicable
        else:proxy_factor=Fraction();contribution=Fraction()
        item.update(gross_branch_applicable=applicable,reason=why,admitted_full_receipt=admitted,proxy_factor=proxy_factor,payout_base_contribution=contribution)
    if not rows or not any(r["kind"]=="receipt" and r["decision"]["eligible"] for r in rows.values()):
        any_applicable = {"opening_gate":opening_R>=opening_C,"closing_gate":R>=C,"continuous_history":continuous}.get(method,R>=C or (method=="split_latch" and latch))
    gross=base*rate;net_candidate=q(net["amount"])*net_rate
    result={"source_case_id":frame["case_id"],"period":deepcopy(frame["period"]),"status":"calculated",
            "opening_receipts":opening_R,"opening_costs":opening_C,"opening_latch":opening_latch,
            "current_full_receipts":selected_totals["receipt"],"current_eligible_costs":selected_totals["cost"],
            "closing_receipts":R,"closing_costs":C,"closing_latch":latch,"continuous_current_history":continuous,
            "payout_base":base,"gross_candidate":gross,"gross_status":"computed_positive" if gross else "computed_zero" if any_applicable else "inapplicable",
            "supplied_net_subtotal":q(net["amount"]),"net_candidate":net_candidate,"net_status":"computed_zero",
            "selected_branch":"gross" if gross>net_candidate else "net" if gross<net_candidate or not any_applicable else "tie",
            "calculated_unissued_entitlement":max(gross,net_candidate),"path":path,
            "aggregate_hurdle":deepcopy(hurdle),"net_worksheet":deepcopy(net),"population_records":deepcopy(frame["populations"]),
            "payment_evidence_status":"not_part_of_profile","bank_movement_created":False}
    return result,(R,C,latch)


def _calculate(data):
    fields(data,{"schema_version","scope","policy","research","registry","opening_state",*FRAME} | ({"prior_result"} if "prior_result" in data else set()))
    need(data["schema_version"]=="ordered-gates-neutral/1","GATE_SCHEMA");scope=data["scope"];fields(scope,SCOPE)
    for value in scope.values():text(value)
    need(scope["currency"]=="USD" and scope["purpose"]=="rolling_work_gate","GATE_SCOPE_CURRENCY_PURPOSE")
    selected=data["policy"];need(selected==policy(selected["method"]),"GATE_POLICY")
    registry=data["registry"];fields(registry,{"terms","work","net_pool_id","genesis_date"});text(registry["net_pool_id"])
    need(registry["net_pool_id"]!=scope["pool_id"],"GATE_NET_SCOPE_MUST_BE_DISTINCT");genesis=day(registry["genesis_date"])
    research=data["research"];fields(research,{"references","source_boundary","professional_approval"})
    need(type(research["references"]) is list and len(research["references"])>=3,"GATE_RESEARCH_PINS")
    for ref in research["references"]:
        fields(ref,{"path","sha256","locator"});text(ref["path"]);text(ref["locator"])
        need(type(ref["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}",ref["sha256"]),"GATE_RESEARCH_PINS")
    need(research["source_boundary"]=="source_economics_with_synthetic_history_and_operating_choices" and research["professional_approval"]=="not_established","GATE_RESEARCH_BOUNDARY")
    opening=data["opening_state"];need(type(opening) is dict,"GATE_OPENING")
    origin=opening.get("origin");need(origin in {"genesis","original_history","prior_result"},"GATE_OPENING")
    if origin=="genesis":
        fields(opening,{"origin","boundary"});history=[]
        need(opening["boundary"]==registry["genesis_date"]==data["period"]["start"] and "prior_result" not in data,"GATE_GENESIS")
    elif origin=="original_history":
        fields(opening,{"origin","boundary","frames"});history=[{"facts":f} for f in opening["frames"]]
        need("prior_result" not in data,"GATE_ORIGINAL_HISTORY_NOT_CANONICAL_RESULT")
    else:
        history=opening["history"]
        need(opening["scope"]==scope and opening["policy"]==selected and opening["registry"]==registry and opening["research"]==research,"GATE_PINNED_CONTEXT_CHANGED")
    need(type(history) is list and len(history)<=3 and (origin=="genesis" or bool(history)),"GATE_COMPLETE_PREHISTORY_REQUIRED")
    seen={"ids":set(),"refs":set(),"decision_ids":set(),"decision_refs":set()};balances=(Fraction(),Fraction(),False);replayed=[];previous_end=registry["genesis_date"];case_ids=set();expected=None;last_cutoff=None
    def state(frame):
        return exact_json({"schema_version":"ordered-gate-state/1","origin":"prior_result","scope":deepcopy(scope),"policy":deepcopy(selected),"registry":deepcopy(registry),"research":deepcopy(research),
             "source_case_id":frame["case_id"],"boundary":frame["period"]["end"],"receipts":balances[0],"costs":balances[1],"latched":balances[2],"history":deepcopy(replayed),
             "consumed_event_ids":sorted(seen["ids"]),"consumed_original_refs":sorted(seen["refs"]),
             "consumed_classification_ids":sorted(seen["decision_ids"]),"consumed_classification_refs":sorted(seen["decision_refs"]),
             "recognized_entitlement":sum((Fraction(r["result"]["calculated_unissued_entitlement"]) for r in replayed),Fraction())})
    for record in history:
        fields(record,{"facts","result"} if origin=="prior_result" else {"facts"});frame=record["facts"]
        need(frame["period"]["start"]==previous_end,"GATE_HISTORY_ADJACENCY")
        need(frame["case_id"] not in case_ids,"GATE_CASE_REPLAY");case_ids.add(frame["case_id"])
        if last_cutoff is not None:need(tick(frame["cutoff"])>last_cutoff,"GATE_HISTORY_CUTOFF_ORDER")
        result,balances=_frame(frame,scope,registry,selected,balances,seen)
        if origin=="prior_result":need(record["result"]==exact_json(result),"GATE_HISTORY_FINANCIAL_REPLAY")
        replayed.append({"facts":deepcopy(frame),"result":exact_json(result)});previous_end=frame["period"]["end"];last_cutoff=tick(frame["cutoff"]);expected=state(frame)
    need(previous_end==data["period"]["start"] and day(previous_end)>=genesis,"GATE_HISTORY_ADJACENCY")
    if origin=="original_history":need(opening["boundary"]==previous_end,"GATE_OPENING_BOUNDARY")
    if origin=="prior_result":
        need(opening==expected,"GATE_OPENING_RECONCILIATION");need("prior_result" in data,"GATE_PREDECESSOR_REQUIRED")
        prior=data["prior_result"]
        need(type(prior) is dict and {"source_case_id","period","closing_state"}<=prior.keys()<={"source_case_id","period","closing_state","result_ref"},"GATE_PREDECESSOR_FIELDS")
        need(prior["source_case_id"]==opening["source_case_id"] and prior["period"]==history[-1]["facts"]["period"] and prior["closing_state"]==opening,"GATE_PREDECESSOR_MISMATCH")
        if "result_ref" in prior:text(prior["result_ref"])
    frame={key:deepcopy(data[key]) for key in FRAME}
    need(frame["case_id"] not in case_ids,"GATE_CASE_REPLAY")
    if last_cutoff is not None:need(tick(frame["cutoff"])>last_cutoff,"GATE_HISTORY_CUTOFF_ORDER")
    result,balances=_frame(frame,scope,registry,selected,balances,seen)
    replayed.append({"facts":frame,"result":exact_json(result)})
    return {**result,"closing_state":state(frame)}


def ordered_gates(data):
    try:return _calculate(data)
    except (KeyError,TypeError,ValueError,ZeroDivisionError) as error:
        if isinstance(error,OrderedGateOracleError):raise
        raise OrderedGateOracleError("GATE_MALFORMED_INPUT") from error


def exact_json(value):
    if isinstance(value,Fraction):return str(value)
    if isinstance(value,dict):return {key:exact_json(child) for key,child in value.items()}
    if isinstance(value,(tuple,list)):return [exact_json(child) for child in value]
    return value
