"""Structural declarations and reproducible authored SPL source assembly.

No fixture values or financial answers are read by this generator.
"""
from pathlib import Path

def rec(**fields): return fields
def lst(item): return [item]
def opt(item): return (item,)
ID = "Identity"
RAW = "OriginalJSON"
M = "Money<USD>"
R = "Ratio"
SCOPE = rec(agreement_id='Id<Agreement>', participant_id='Id<Participant>', pool_id='Id<Pool>', asset_id='Id<Asset>', currency="Text", purpose="Text")
POLICY = rec(**{k:"Text" for k in ("id","revision","stage","reserve_measure","fee","cap","order","release","rounding","evidence_class")})
COMMON = rec(id=ID, scope=SCOPE, observed_at="Instant", source_ref=ID, evidence_ref=ID)
EVIDENCE = rec(id=ID, scope=SCOPE, observed_at="Instant", source_ref=ID, kind="Text", approved="Bool")
RULE = rec(id=ID, offset_months="Nat", kind="Text", fraction=opt(R))
TERMS = rec(**COMMON, version=ID, approved="Bool", approved_date="Date", approved_utc="Instant", effective="Period", reserve_rate=R, participation_share=R, fixed_fee=M, retained_cap=M, reserve_measure="Text", calendar_mode="Text", release_schedule=lst(RULE))
RECEIPT = rec(**COMMON, original_ref=ID, gross=M, event_date="Date", event_utc="Instant", sequence="Int", raw=RAW)
ELECTION = rec(**COMMON, receipt_id=ID, vintage_id=ID, elected="Bool", approved="Bool", approved_date="Date", approved_utc="Instant", event_date="Date", event_utc="Instant", raw=RAW)
APPLICATION = rec(**COMMON, original_ref=ID, vintage_id=ID, amount=M, event_date="Date", event_utc="Instant", sequence="Int", authority_id=ID, reserve_measure="Text", raw=RAW)
AUTHORITY = rec(**COMMON, application_id=ID, vintage_id=ID, approved="Bool", approved_date="Date", approved_utc="Instant", reserve_measure="Text")
POP = rec(**COMMON, period="Period", complete="Bool", receipt_ids=lst(ID), election_ids=lst(ID), application_ids=lst(ID), authority_ids=lst(ID), gross_total=M, application_total=M)
FRAME = rec(id=ID, period="Period", as_of="Date", as_of_ordinal="Int", end_ordinal="Int", end_utc="Instant", cutoff="Instant", receipts=lst(RECEIPT), elections=lst(ELECTION), applications=lst(APPLICATION), authorities=lst(AUTHORITY), population=POP, evidence=lst(EVIDENCE), raw=RAW, unknown=lst("Text"))
TRANCHE = rec(id=ID, kind="Text", fraction=opt(R), due_date="Date", processed="Bool")
VINTAGE = rec(id=ID, scope=SCOPE, reserve_measure="Text", original_receipt=RAW, original_election=RAW, established_date="Date", original_addition=M, raw_addition=M, available=M, applied=M, released=M, fee_assessed_once=M, fee_key=lst(ID), liquidated="Bool", tranches=lst(TRANCHE))
METERS = rec(**{k:M for k in ("gross","fee","producer","nonparticipant","applications","additions","releases")})
RECEIPT_DETAIL = rec(receipt_id=ID,vintage_id=ID,gross=M,fee_consumed=M,fee_key=lst(ID),raw_addition=M,retained_before=M,cap_room_before=M,addition=M,unretained_current=M,producer=M,nonparticipant=M,closing_retained_after_addition=M)
APP_DETAIL = rec(original=RAW,opening_available=M,applied=M,closing_available=M)
RELEASE_DETAIL = rec(key=lst(ID),vintage_id=ID,tranche_id=ID,due_date="Date",basis="Text",original_addition=M,opening_available=M,quota=M,released=M,closing_available=M,producer=M,nonparticipant=M,fee=M)
RESULT = rec(source_case_id=ID,period="Period",stage="Text",reserve_measure="Text",status="Text",opening_reserve=M,current=METERS,closing_reserve=M,receipt_details=lst(RECEIPT_DETAIL),application_details=lst(APP_DETAIL),release_details=lst(RELEASE_DETAIL),vintages=lst(VINTAGE),cumulative=METERS,fee_consumption_keys=lst(lst(ID)),issuance_status="Text",payment_evidence_status="Text",bank_movement_created="Bool",source_clearance_inferred="Bool",release_policy="Text",observation_basis="Text",unknown_local_offset_paths=lst("Text"))
SEEN = ("receipt_ids","receipt_refs","election_ids","application_ids","application_refs","authority_ids")
BOOK = rec(vintages=lst(VINTAGE),cumulative=METERS,fee_consumption_keys=lst(lst(ID)),**{k:lst(ID) for k in SEEN}, history=lst(rec(facts=RAW,result=RESULT)),unknown=lst("Text"))
STATE = rec(transport_profile="Text",context=RAW,origin="Text",boundary="Date",source_case_id=ID,detail=opt(BOOK))
PREVIOUS = rec(source_case_id=ID,period="Period",result_ref=ID,closing_state=STATE)

def typ(schema):
    if isinstance(schema,dict): return "{"+", ".join(k+": "+typ(schema[k]) for k in sorted(schema))+"}"
    if isinstance(schema,list): return "List<"+typ(schema[0])+">"
    if isinstance(schema,tuple): return "Option<"+typ(schema[0])+">"
    return "Text" if schema in (ID,RAW) else schema

def fields(old, schema, **replace):
    return "{"+", ".join(k+": "+replace.get(k,old+"."+k) for k in schema)+"}"

def generate():
    out = ["// Synthetic supplied stage, cap and schedule policy. All finance executes below.", 'schedule ReserveStages language "spl/0.1-draft" core "spl-core/0.1-draft" schema "spl-data/0.1-draft" {']
    def line(s): out.append("  "+s)
    for name,schema in dict(scope=rec(agreement_id="Id<Agreement>",participant_id="Id<Participant>",pool_id="Id<Pool>",period="Period"),project="Id<Asset>",fact_scope=SCOPE,source_context=RAW,terms=TERMS,registry_evidence=lst(EVIDENCE),frames=lst(FRAME),initial_unknown=lst("Text"),supplied_opening=STATE,predecessor=opt(PREVIOUS)).items(): line(f"input {name}: {typ(schema)};")
    line(f"input policy: {typ(POLICY)};")
    line("input cutoff: Instant;")
    line('define zero_nat: Nat = 0;')
    line(f'opening history: {typ(STATE)} from "reserve-stages/full-original-history";')
    for name,schema in dict(empty_vintages=lst(VINTAGE),empty_history=lst(rec(facts=RAW,result=RESULT)),empty_receipt_details=lst(RECEIPT_DETAIL),empty_application_details=lst(APP_DETAIL),empty_release_details=lst(RELEASE_DETAIL),empty_ids=lst(ID),empty_fee_keys=lst(lst(ID)),empty_dates=lst('Date'),empty_tranches=lst(TRANCHE)).items(): line(f"define {name}: {typ(schema)} = [];")
    line("define zero = {"+", ".join(k+": USD 0" for k in METERS)+"};")
    line('require history == supplied_opening and history.context == source_context and history.transport_profile == "reserve-stages-original-json/1" and history.boundary == scope.period.start else "RS_OPENING_CONTEXT";')
    line('require fact_scope.agreement_id == scope.agreement_id and fact_scope.participant_id == scope.participant_id and fact_scope.pool_id == scope.pool_id and fact_scope.asset_id == project and fact_scope.currency == "USD" else "RS_SCOPE";')
    line('require policy.id == "SYNTHETIC-RESERVE-STAGES-01" and policy.revision == "1" and policy.fee == "fixed_once_per_original_receipt" and policy.cap == "limit_addition_with_unretained_current" and policy.order == "daily_receipts_then_ordered_applications_then_due_tranches" and policy.release == "unconditional_under_supplied_generic_terms" and policy.rounding == "exact_no_rounding" and policy.evidence_class == "research_assumption" else "RS_POLICY";')
    line('define basis = policy.stage == "basis_reserve";')
    line('require (basis and policy.reserve_measure == "gross_basis_USD" and fact_scope.purpose == "synthetic_gross_basis_reserve") or (policy.stage == "producer_holdback" and policy.reserve_measure == "producer_entitlement_USD" and fact_scope.purpose == "synthetic_producer_entitlement_holdback") else "RS_STAGE_MEASURE_PURPOSE";')
    line('require sum(frames, f => 1) >= 1 and sum(frames, f => 1) <= 4 else "RS_FRAME_BOUND";')
    line('define minimum_cutoff = fold frames from cutoff with a, f { yield if a < f.cutoff then a else f.cutoff; };')
    line('define registry_checked = for each e in registry_evidence { require e.id != "" and e.source_ref != "" and e.kind != "" and e.approved and e.scope == fact_scope and e.observed_at < minimum_cutoff and sum(filter(registry_evidence, x => x.id == e.id), x => 1) == 1 else "RS_REGISTRY_EVIDENCE"; yield e; };')
    line('require sum(registry_checked, e => 1) <= 32 and terms.scope == fact_scope and terms.id != "" and terms.version != "" and terms.source_ref != "" and terms.approved and terms.approved_utc <= terms.observed_at and terms.observed_at < minimum_cutoff else "RS_TERMS";')
    line('require sum(filter(registry_checked, e => e.id == terms.evidence_ref and e.kind == "generic_reserve_terms" and e.observed_at <= terms.observed_at), e => 1) == 1 else "RS_TERMS_SUPPORT";')
    line('require terms.reserve_measure == policy.reserve_measure and terms.fixed_fee >= USD 0 and terms.retained_cap >= USD 0 and terms.reserve_rate >= 0.0 and terms.reserve_rate <= 1.0 and terms.participation_share >= 0.0 and terms.participation_share <= 1.0 and (terms.calendar_mode == "clamp_day" or terms.calendar_mode == "reject_invalid_day") else "RS_TERMS_VALUES";')
    line('define schedule_check = fold terms.release_schedule from {count: 0, offset: 0, final: false} with a, r { require r.id != "" and sum(filter(terms.release_schedule, x => x.id == r.id), x => 1) == 1 and r.offset_months > a.offset and r.offset_months <= 24 and not a.final else "RS_SCHEDULE_ORDER"; require (r.kind == "all_remaining" and not is_some(r.fraction)) or (a.count == 0 and r.kind == "fraction_of_original_addition" and is_some(r.fraction) and require_some(r.fraction, "RS_FRACTION") > 0.0 and require_some(r.fraction, "RS_FRACTION") <= 1.0) else "RS_SCHEDULE_RULE"; yield {count: a.count + 1, offset: r.offset_months, final: r.kind == "all_remaining"}; };')
    line('require schedule_check.count >= 1 and schedule_check.count <= 2 and schedule_check.final else "RS_SCHEDULE_FINAL";')
    genesis = '{vintages: empty_vintages, cumulative: zero, fee_consumption_keys: empty_fee_keys, '+', '.join(k+': empty_ids' for k in SEEN)+', history: empty_history, unknown: initial_unknown}'
    line(f'define genesis: {typ(BOOK)} = {genesis};')
    line(f'define first_slot: Option<{typ(FRAME)}> = fold frames from none() with a, f {{ yield if is_some(a) then a else some(f); }};')
    line('define first = require_some(first_slot, "RS_FRAME_REQUIRED");')
    line('define replay = fold frames from {book: genesis, boundary: first.period.start, last_case: "67656e65736973", count: 0} with prior, frame {')
    line('  require frame.id != "" and sum(filter(frames, f => f.id == frame.id), f => 1) == 1 and frame.period.start == prior.boundary and frame.period.start < frame.period.end and frame.as_of_ordinal + 1 == frame.end_ordinal and frame.end_utc <= frame.cutoff and terms.effective.start <= frame.period.start and frame.period.end <= terms.effective.end else "RS_PERIOD";')
    line('  define current_frame = frame.period == scope.period;')
    line('  require not current_frame or frame.cutoff == cutoff else "RS_CURRENT_CUTOFF";')
    line('  require not current_frame or (if prior.count == 0 then history.origin == "genesis" and history.source_case_id == "67656e65736973" and not is_some(history.detail) and not is_some(predecessor) else history.origin == "prior_result" and history.source_case_id == prior.last_case and require_some(history.detail, "RS_OPENING_REQUIRED") == prior.book and is_some(predecessor) and require_some(predecessor, "RS_PREDECESSOR_REQUIRED").closing_state == history and require_some(predecessor, "RS_PREDECESSOR_REQUIRED").source_case_id == history.source_case_id and require_some(predecessor, "RS_PREDECESSOR_REQUIRED").period == require_some(fold prior.book.history from none() with a, h { yield some(h.result.period); }, "RS_PRIOR_PERIOD")) else "RS_REPLAY_OPENING";')
    # All supplied rows, even unused rows, have independent admission checks.
    line('  define checked_evidence = for each e in frame.evidence { require e.id != "" and e.source_ref != "" and e.kind != "" and e.scope == fact_scope and e.approved and e.observed_at < frame.cutoff and sum(filter(frame.evidence, x => x.id == e.id), x => 1) == 1 else "RS_EVIDENCE"; yield e; };')
    line('  require sum(checked_evidence, e => 1) <= 32 else "RS_EVIDENCE_BOUND";')
    for table,kind in [('receipts','original_gross_basis'),('elections','reserve_election'),('applications','reserve_application'),('authorities','reserve_application_authority')]:
        line(f'  define checked_{table} = for each r in frame.{table} {{ require r.id != "" and r.source_ref != "" and r.scope == fact_scope and r.observed_at < frame.cutoff and sum(filter(frame.{table}, x => x.id == r.id), x => 1) == 1 and sum(filter(checked_evidence, e => e.id == r.evidence_ref and e.kind == "{kind}" and e.observed_at <= r.observed_at), e => 1) == 1 else "RS_ROW_ADMISSION"; yield r; }};')
        line(f'  require sum(checked_{table}, r => 1) <= 8 else "RS_ROW_BOUND";')
    line('  define p = frame.population;')
    line('  require p.id != "" and p.source_ref != "" and p.scope == fact_scope and p.complete and p.period == frame.period and p.observed_at >= frame.end_utc and p.observed_at < frame.cutoff and sum(filter(checked_evidence, e => e.id == p.evidence_ref and e.kind == "complete_current_population" and e.observed_at <= p.observed_at), e => 1) == 1 else "RS_POPULATION";')
    for table,key in [('receipts','receipt_ids'),('elections','election_ids'),('applications','application_ids'),('authorities','authority_ids')]:
        line(f'  require sort_by(p.{key}, x => x) == sort_by(map(checked_{table}, x => x.id), x => x) and sum(filter(checked_{table}, r => r.observed_at > p.observed_at), r => 1) == 0 else "RS_COMPLETE_POPULATION";')
    line('  require sum(checked_receipts, r => r.gross) == p.gross_total and sum(checked_applications, r => r.amount) == p.application_total else "RS_POPULATION_TOTAL";')
    line('  define receipts = for each r in checked_receipts { require r.gross >= USD 0 and r.original_ref != "" and in_period(r.event_date, frame.period) and sum(filter(checked_receipts, x => x.event_date == r.event_date and x.sequence == r.sequence), x => 1) == 1 and sum(filter(checked_elections, e => e.receipt_id == r.id), e => 1) == 1 else "RS_RECEIPT"; yield r; };')
    line('  define elections = for each e in checked_elections { require e.approved and e.approved_date <= e.event_date and e.approved_utc <= e.observed_at and e.vintage_id != "" and sum(filter(receipts, r => r.id == e.receipt_id and r.event_date == e.event_date and e.observed_at <= r.observed_at), r => 1) == 1 else "RS_ELECTION"; yield e; };')
    line('  define applications = for each a in checked_applications { require a.amount >= USD 0 and a.original_ref != "" and a.reserve_measure == policy.reserve_measure and in_period(a.event_date, frame.period) and sum(filter(checked_applications, x => x.event_date == a.event_date and x.sequence == a.sequence), x => 1) == 1 and sum(filter(checked_authorities, x => x.id == a.authority_id and x.application_id == a.id and x.vintage_id == a.vintage_id and x.reserve_measure == a.reserve_measure and x.approved and x.approved_date <= a.event_date and x.approved_utc <= x.observed_at and x.observed_at <= a.observed_at), x => 1) == 1 else "RS_APPLICATION_AUTHORITY"; yield a; };')
    line('  define authority_check = for each a in checked_authorities { require sum(filter(applications, x => x.authority_id == a.id), x => 1) == 1 else "RS_UNUSED_AUTHORITY"; yield a; };')
    # Original IDs/references are checked across the complete prefix.
    for table,key,field in [('receipts','receipt_ids','id'),('receipts','receipt_refs','original_ref'),('elections','election_ids','id'),('applications','application_ids','id'),('applications','application_refs','original_ref'),('authority_check','authority_ids','id')]:
        line(f'  define next_{key} = concat(prior.book.{key}, map({table}, r => r.{field}));')
        line(f'  require sum(filter(next_{key}, id => sum(filter(next_{key}, x => x == id), x => 1) != 1), id => 1) == 0 else "RS_ORIGINAL_REUSE";')
    line('  define new_deadlines = fold receipts from [] with ds, r { yield concat(ds, map(terms.release_schedule, rule => add_calendar_months(r.event_date, rule.offset_months, terms.calendar_mode))); };')
    line('  define old_deadlines = fold prior.book.vintages from [] with ds, v { yield concat(ds, map(filter(v.tranches, t => not t.processed), t => t.due_date)); };')
    line('  define all_dates = concat(concat(map(receipts, r => r.event_date), map(applications, a => a.event_date)), concat(new_deadlines, old_deadlines));')
    line('  define dates = map(entries(group_by(filter(all_dates, d => in_period(d, frame.period)), d => d)), row => row.key);')
    line('  define moved = fold sort_by(dates, d => d) from {vintages: prior.book.vintages, receipts: empty_receipt_details, apps: empty_application_details, releases: empty_release_details} with daybook, d {')
    line('    define added = fold sort_by(filter(receipts, r => r.event_date == d), r => r.sequence) from {vintages: daybook.vintages, details: daybook.receipts} with a, r {')
    line('      define e = require_some(fold filter(elections, e => e.receipt_id == r.id) from none() with slot, e { yield some(e); }, "RS_ELECTION");')
    line('      require sum(a.vintages, v => 1) < 4 and sum(filter(a.vintages, v => v.id == e.vintage_id), v => 1) == 0 else "RS_VINTAGE_ID_BOUND";')
    line('      require r.gross >= terms.fixed_fee else "RS_FIXED_FEE_FUNDING_VARIANT_REQUIRED";')
    line('      define earned = (r.gross - terms.fixed_fee) * terms.participation_share;')
    line('      define candidate = if e.elected then (if basis then r.gross else earned) * terms.reserve_rate else USD 0;')
    line('      define retained = sum(a.vintages, v => v.available);')
    line('      define room = max(terms.retained_cap - retained, USD 0);')
    line('      define addition = min(candidate, room);')
    line('      require not basis or r.gross - addition >= terms.fixed_fee else "RS_FIXED_FEE_FUNDING_VARIANT_REQUIRED";')
    line('      define producer = if basis then (r.gross - addition - terms.fixed_fee) * terms.participation_share else earned - addition;')
    line('      define nonparticipant = (r.gross - terms.fixed_fee - (if basis then addition else USD 0)) * (1.0 - terms.participation_share);')
    line('      define tranches = map(terms.release_schedule, rule => {id: rule.id, kind: rule.kind, fraction: rule.fraction, due_date: add_calendar_months(r.event_date, rule.offset_months, terms.calendar_mode), processed: false});')
    line('      define vintage = {id: e.vintage_id, scope: fact_scope, reserve_measure: policy.reserve_measure, original_receipt: r.raw, original_election: e.raw, established_date: r.event_date, original_addition: addition, raw_addition: candidate, available: addition, applied: USD 0, released: USD 0, fee_assessed_once: terms.fixed_fee, fee_key: [terms.id, r.original_ref], liquidated: false, tranches: tranches};')
    line('      define detail = {receipt_id: r.id, vintage_id: e.vintage_id, gross: r.gross, fee_consumed: terms.fixed_fee, fee_key: [terms.id, r.original_ref], raw_addition: candidate, retained_before: retained, cap_room_before: room, addition: addition, unretained_current: candidate - addition, producer: producer, nonparticipant: nonparticipant, closing_retained_after_addition: retained + addition};')
    line('      yield {vintages: append(a.vintages, vintage), details: append(a.details, detail)}; };')
    line('    define applied = fold sort_by(filter(applications, app => app.event_date == d), app => app.sequence) from {vintages: added.vintages, details: daybook.apps} with a, app {')
    line('      define v = require_some(fold filter(a.vintages, v => v.id == app.vintage_id) from none() with s, v { yield some(v); }, "RS_UNKNOWN_VINTAGE");')
    line('      require not v.liquidated and app.amount <= v.available and sum(filter(elections, e => e.vintage_id == v.id and e.observed_at <= app.observed_at), e => 1) + sum(filter(prior.book.vintages, old => old.id == v.id), old => 1) == 1 else "RS_VINTAGE_OVERDRAW_OR_LIQUIDATED";')
    line('      define updated = '+fields('v',VINTAGE,available='v.available - app.amount',applied='v.applied + app.amount')+';')
    line('      yield {vintages: map(a.vintages, old => if old.id == v.id then updated else old), details: append(a.details, {original: app.raw, opening_available: v.available, applied: app.amount, closing_available: v.available - app.amount})}; };')
    line('    define released = fold sort_by(applied.vintages, v => v.id) from {vintages: empty_vintages, details: daybook.releases} with a, v {')
    line('      define tr = fold v.tranches from {available: v.available, released: v.released, liquidated: v.liquidated, tranches: [], details: a.details} with b, t {')
    line('        define due = not t.processed and t.due_date == d;')
    line('        define quota = if t.kind == "all_remaining" then b.available else v.original_addition * require_some(t.fraction, "RS_FRACTION");')
    line('        define amount = if due then min(quota, b.available) else USD 0;')
    line('        define producer = if basis then amount * terms.participation_share else amount;')
    line('        define detail = {key: [v.id, terms.id, terms.version, t.id], vintage_id: v.id, tranche_id: t.id, due_date: t.due_date, basis: t.kind, original_addition: v.original_addition, opening_available: b.available, quota: quota, released: amount, closing_available: b.available - amount, producer: producer, nonparticipant: amount - producer, fee: USD 0};')
    line('        yield {available: b.available - amount, released: b.released + amount, liquidated: b.liquidated or (due and t.kind == "all_remaining"), tranches: append(b.tranches, '+fields('t',TRANCHE,processed='t.processed or due')+'), details: if due then append(b.details, detail) else b.details}; };')
    line('      yield {vintages: append(a.vintages, '+fields('v',VINTAGE,available='tr.available',released='tr.released',liquidated='tr.liquidated',tranches='tr.tranches')+'), details: tr.details}; };')
    line('    yield {vintages: released.vintages, receipts: added.details, apps: applied.details, releases: released.details}; };')
    line('  define vintage_check = for each v in moved.vintages { require v.original_addition == v.available + v.applied + v.released and sum(filter(v.tranches, t => not t.processed and t.due_date < frame.period.end), t => 1) == 0 else "RS_VINTAGE_CONSERVATION_OR_OVERDUE"; yield v; };')
    line('  define current = {gross: sum(moved.receipts, r => r.gross), fee: sum(moved.receipts, r => r.fee_consumed), producer: sum(moved.receipts, r => r.producer) + sum(moved.releases, r => r.producer), nonparticipant: sum(moved.receipts, r => r.nonparticipant) + sum(moved.releases, r => r.nonparticipant), applications: sum(moved.apps, r => r.applied), additions: sum(moved.receipts, r => r.addition), releases: sum(moved.releases, r => r.released)};')
    line('  define cumulative = {'+', '.join(k+': prior.book.cumulative.'+k+' + current.'+k for k in METERS)+'};')
    line('  define opening = sum(prior.book.vintages, v => v.available);')
    line('  define closing = sum(vintage_check, v => v.available);')
    line('  require current.gross + opening == current.fee + current.producer + current.nonparticipant + current.applications + closing and cumulative.gross == cumulative.fee + cumulative.producer + cumulative.nonparticipant + cumulative.applications + closing else "RS_BRIDGE";')
    line('  define keys = sort_by(concat(prior.book.fee_consumption_keys, map(moved.receipts, r => r.fee_key)), k => require_some(fold k from none() with a, x { yield some(x); }, "RS_KEY"));')
    line('  define unknown = concat(prior.book.unknown, frame.unknown);')
    line('  define result = {source_case_id: frame.id, period: frame.period, stage: policy.stage, reserve_measure: policy.reserve_measure, status: "calculated", opening_reserve: opening, current: current, closing_reserve: closing, receipt_details: moved.receipts, application_details: moved.apps, release_details: moved.releases, vintages: sort_by(vintage_check, v => v.id), cumulative: cumulative, fee_consumption_keys: keys, issuance_status: "unissued_calculation", payment_evidence_status: "not_part_of_profile", bank_movement_created: false, source_clearance_inferred: false, release_policy: policy.release, observation_basis: "exact_UTC_no_local_date_inference", unknown_local_offset_paths: unknown};')
    line('  define book = {vintages: result.vintages, cumulative: cumulative, fee_consumption_keys: keys, '+', '.join(k+': sort_by(next_'+k+', id => id)' for k in SEEN)+', history: append(prior.book.history, {facts: frame.raw, result: result}), unknown: unknown};')
    line('  yield {book: book, boundary: frame.period.end, last_case: frame.id, count: prior.count + 1}; };')
    line('require replay.boundary == scope.period.end else "RS_CURRENT_LAST";')
    line('define current = require_some(fold replay.book.history from none() with a, h { yield some(h.result); }, "RS_RESULT");')
    line('closing history = {transport_profile: "reserve-stages-original-json/1", context: source_context, origin: "prior_result", boundary: replay.boundary, source_case_id: replay.last_case, detail: some(replay.book)};')
    line('emit "comparison" = current;')
    line('emit "reconciliation" = true;')
    out.append('}')
    import re
    source = '\n'.join(out)+'\n'
    source = source.replace('in_period(r.event_date, frame.period) and', 'in_period(r.event_date, frame.period) and r.event_utc <= r.observed_at and')
    source = source.replace('e.approved and e.approved_date', 'e.event_utc <= e.observed_at and e.approved and e.approved_date')
    source = source.replace('in_period(a.event_date, frame.period) and', 'in_period(a.event_date, frame.period) and a.event_utc <= a.observed_at and')
    source = source.replace('sum(filter(elections, e => e.vintage_id == v.id and e.observed_at <= app.observed_at), e => 1) + sum(filter(prior.book.vintages, old => old.id == v.id), old => 1) == 1', 'sum(frames, known => sum(filter(known.elections, election => election.raw == v.original_election and election.observed_at <= app.observed_at), election => 1)) == 1')
    source = source.replace('offset: 0, final:', 'offset: zero_nat, final:')
    source = source.replace('require_some(fold prior.book.history from none() with a, h { yield some(h.result.period); }, "RS_PRIOR_PERIOD")', '(fold prior.book.history from {start: prior.boundary, end: prior.boundary} with a, h { yield h.result.period; })')
    source = source.replace('fold receipts from []', 'fold receipts from empty_dates').replace('fold prior.book.vintages from []','fold prior.book.vintages from empty_dates').replace('tranches: [], details:', 'tranches: empty_tranches, details:')
    source = source.replace('define e = require_some(fold filter(elections, e => e.receipt_id == r.id) from none() with slot, e { yield some(e); }, "RS_ELECTION");', f'define election_slot: Option<{typ(ELECTION)}> = fold filter(elections, e => e.receipt_id == r.id) from none() with slot, e {{ yield some(e); }}; define e = require_some(election_slot, "RS_ELECTION");')
    source = source.replace('define v = require_some(fold filter(a.vintages, v => v.id == app.vintage_id) from none() with s, v { yield some(v); }, "RS_UNKNOWN_VINTAGE");', f'define vintage_slot: Option<{typ(VINTAGE)}> = fold filter(a.vintages, v => v.id == app.vintage_id) from none() with s, v {{ yield some(v); }}; define v = require_some(vintage_slot, "RS_UNKNOWN_VINTAGE");')
    source = source.replace('require_some(fold k from none() with a, x { yield some(x); }, "RS_KEY")','fold k from "" with a, x { yield x; }')
    source = source.replace('define current = require_some(fold replay.book.history from none() with a, h { yield some(h.result); }, "RS_RESULT");', f'define current_slot: Option<{typ(RESULT)}> = fold replay.book.history from none() with a, h {{ yield some(h.result); }}; define current = require_some(current_slot, "RS_RESULT");')
    source = source.replace('define current = require_some(current_slot, "RS_RESULT");','define final_result = require_some(current_slot, "RS_RESULT");').replace('emit "comparison" = current;', 'emit "comparison" = final_result;')
    start=source.index('define election_slot:')
    end=source.index('define applied =',start)
    block=source[start:end].replace('define e =','define elected_row =')
    block=re.sub(r'\be\.', 'elected_row.', block)
    block=block.replace('e => elected_row.receipt_id','e => e.receipt_id').replace('yield some(e);','yield some(e);')
    source=source[:start]+block+source[end:]
    start=source.index('define vintage_slot:')
    end=source.index('define released =',start)
    block=source[start:end].replace('define v =','define designated =')
    block=re.sub(r'\bv\.', 'designated.', block)
    block=block.replace('v => designated.id','v => v.id')
    source=source[:start]+block+source[end:]
    source = re.sub(r'\bopening\b', 'opening_amount', source)
    source = re.sub(r'\bclosing\b', 'closing_amount', source)
    source = source.replace('opening_amount history:', 'opening history:').replace('closing_amount history =', 'closing history =')
    return source

if __name__ == '__main__': Path(__file__).with_name('reserve-stages.spl').write_text(generate(),encoding='utf-8')
