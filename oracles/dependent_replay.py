"""Independent finite authorized replay and prospective-attribution controls.

This module reads no SPL, compiler, adapter, prior implementation or golden.
Original issue controls and bank payments are checked against original facts.
"""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import re

POLICY_ID = 'SYNTHETIC-DEPENDENT-REPLAY-01'
SCOPE = {'agreement_id','pool_id','asset_id','participant_id','currency','purpose'}
COMMON = {'id','scope','observed_at','source_ref','evidence_ref'}
FRAME = {'case_id','period_id','period','as_of','cutoff','predecessor_period_id','predecessor_result_ref','receipts','population','cash_population','replacements','authorities','requests','correction_population','evidence'}

class DependentReplayOracleError(ValueError):
    pass

def require(value, code):
    if not value:raise DependentReplayOracleError(code)

def fields(value, keys):
    require(type(value)is dict and value.keys()==set(keys),'REPLAY_RECORD_FIELDS')

def text(value):
    require(type(value)is str and value and all(not 0xD800<=ord(c)<=0xDFFF for c in value),'REPLAY_TEXT');return value

def q(value):
    require(type(value)is str and re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?',value),'REPLAY_EXACT_NONNEGATIVE');return Fraction(value)

def day(value):
    require(type(value)is str and re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value),'REPLAY_DATE')
    try:return date.fromisoformat(value)
    except ValueError:raise DependentReplayOracleError('REPLAY_DATE')from None

def midnight(value):return Fraction(day(value).toordinal()*86400)

def tick(value):
    require(type(value)is str,'REPLAY_INSTANT')
    m=re.fullmatch(r'([0-9]{4}-[0-9]{2}-[0-9]{2})[Tt]([0-9]{2}):([0-9]{2}):([0-9]{2})(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})',value);require(m is not None,'REPLAY_INSTANT')
    d,h,minute,second,part,zone=m.groups();h,minute,second=int(h),int(minute),int(second);require(h<24 and minute<60 and second<60,'REPLAY_INSTANT');offset=0
    if zone.lower()!='z':
        zh,zm=int(zone[1:3]),int(zone[4:]);require(zone!='-00:00'and zh<24 and zm<60,'REPLAY_INSTANT');offset=(zh*60+zm)*60*(1 if zone[0]=='+'else-1)
    result=midnight(d)+h*3600+minute*60+second-offset+Fraction(part or'0');require(86400<=result<(date.max.toordinal()+1)*86400,'REPLAY_INSTANT');return result

def period(value):
    fields(value,{'start','end'});a,b=day(value['start']),day(value['end']);require(a<b,'REPLAY_PERIOD');return a,b

def ids(value):
    require(type(value)is list and len(value)<=8,'REPLAY_ID_LIST');require(all(type(x)is str and x and all(not 0xD800<=ord(c)<=0xDFFF for c in x)for x in value)and len(set(value))==len(value),'REPLAY_ID_LIST');return set(value)

def index(value, bound=8):
    require(type(value)is list and len(value)<=bound,'REPLAY_FINITE_ROWS');result={}
    for row in value:
        key=text(row['id']);require(key not in result,'REPLAY_DUPLICATE_ID');result[key]=row
    return result

def line(value):
    a,s,b=text(value).rpartition('#');require(a and s and b,'REPLAY_ORIGINAL_LINE');return value

def policy(route='restatement'):
    require(route in {'restatement','prospective'},'REPLAY_ROUTE')
    return {'id':POLICY_ID,'revision':'1','route':route,'economics':'original_opening_exact_cumulative_basis','attribution':'revised_historical_lines'if route=='restatement'else'original_lines_plus_current_signed_credit','cash':'complete_empty_current_only','replacements':'one_authorized_replacement_per_original_receipt','balance_scope':'nonnegative_account_and_no_original_overpayment','rounding':'exact_no_rounding','evidence_class':'research_assumption'}

def normalized(registry):
    result=deepcopy(registry)
    for k,v in result.items():
        if isinstance(v,list):result[k]=sorted(v,key=lambda x:x['id'])if v and isinstance(v[0],dict)else sorted(v)
    return result

def evidence(rows, scope, cutoff):
    result=index(rows,32)
    for row in result.values():
        fields(row,{'id','scope','kind','approved','observed_at','source_ref'});require(row['scope']==scope and row['approved']is True and tick(row['observed_at'])<cutoff,'REPLAY_EVIDENCE_SCOPE_APPROVAL_CUTOFF');text(row['kind']);text(row['source_ref'])
    return result

def support(row,kind,ev,scope,cutoff):
    require(row['scope']==scope,'REPLAY_FACT_SCOPE');text(row['source_ref']);require(row['evidence_ref']in ev,'REPLAY_EVIDENCE_REQUIRED');e=ev[row['evidence_ref']]
    require(e['kind']==kind and tick(e['observed_at'])<=tick(row['observed_at'])<cutoff,'REPLAY_SOURCE_OBSERVATION')

def receipt(row,ev,scope,cutoff):
    fields(row,COMMON|{'period_id','term_id','base_amount','effective_date','sequence','original_ref','entitlement_ref'})
    support(row,'original_receipt_basis',ev,scope,cutoff);q(row['base_amount']);line(row['original_ref']);line(row['entitlement_ref']);text(row['period_id']);text(row['term_id'])
    require(type(row['sequence'])is int and row['sequence']>=0 and midnight(row['effective_date'])<=tick(row['observed_at']),'REPLAY_RECEIPT_CHRONOLOGY')

def compute(periods, receipts, terms, replacements):
    """Derive every original/revised earning and dependency meter from basis."""
    cumulative=Fraction();result=[];by_receipt={}
    for p in periods:
        opening=cumulative;earnings=Fraction();details=[]
        rows=sorted([r for r in receipts if r['period_id']==p['id']],key=lambda r:(r['effective_date'],r['sequence']))
        require(len({(r['effective_date'],r['sequence'])for r in rows})==len(rows),'REPLAY_UNRESOLVED_RECEIPT_ORDER')
        for r in rows:
            term=terms.get(r['term_id']);require(term is not None and term['effective']==p['period'],'REPLAY_TERM_REFERENCE')
            require(day(term['approved_date'])<=day(r['effective_date']) and tick(term['observed_at'])<=tick(r['observed_at']),'REPLAY_TERM_NOT_KNOWN_OR_EFFECTIVE')
            base=q(replacements[r['id']]['base_amount'])if r['id']in replacements else q(r['base_amount']);before=cumulative
            if term['kind']=='flat_ratio':lower=base;upper=Fraction();earned=base*q(term['flat_rate'])
            else:
                lower=min(base,max(q(term['threshold'])-before,Fraction()));upper=base-lower;earned=lower*q(term['lower_rate'])+upper*q(term['upper_rate'])
            cumulative+=base;earnings+=earned;by_receipt[r['id']]=earned
            details.append({'receipt_id':r['id'],'original_basis':q(r['base_amount']),'selected_basis':base,'replacement_id':replacements[r['id']]['id']if r['id']in replacements else None,'term_id':term['id'],'opening_cumulative_basis':before,'lower_basis':lower,'upper_basis':upper,'earned':earned,'closing_cumulative_basis':cumulative})
        result.append({'period_id':p['id'],'period':deepcopy(p['period']),'opening_cumulative_basis':opening,'gross_basis':cumulative-opening,'earned':earnings,'closing_cumulative_basis':cumulative,'receipt_details':details})
    return result,by_receipt

def registry(raw,scope,cutoff):
    fields(raw,{'party_ids','payer_id','origin','periods','terms','receipts','issued_artifacts','payments','applications','payment_population','evidence'})
    parties=ids(raw['party_ids']);require(raw['payer_id']in parties and scope['participant_id']in parties and raw['payer_id']!=scope['participant_id'],'REPLAY_PARTY_ROLES')
    fields(raw['origin'],{'boundary','cumulative_basis','recognized_entitlement','actual_paid'});require(all(q(raw['origin'][k])==0 for k in ['cumulative_basis','recognized_entitlement','actual_paid']),'REPLAY_ORIGINAL_OPENING')
    ev=evidence(raw['evidence'],scope,cutoff);tables={k:index(raw[k],4 if k in {'periods','issued_artifacts'}else 8)for k in ['periods','terms','receipts','issued_artifacts','payments','applications']}
    periods=sorted(tables['periods'].values(),key=lambda r:r['period']['start']);require(periods and raw['origin']['boundary']==periods[0]['period']['start'],'REPLAY_ORIGINAL_OPENING');previous=None
    for p in periods:
        fields(p,COMMON|{'period','as_of','cutoff','predecessor_period_id'});support(p,'issued_period',ev,scope,cutoff);a,b=period(p['period']);require(day(p['as_of'])==b-timedelta(days=1)and tick(p['cutoff'])>=b.toordinal()*86400,'REPLAY_COMPLETE_ORIGINAL_PERIOD')
        require((previous is None and p['predecessor_period_id']is None)or(previous is not None and p['predecessor_period_id']==previous['id']and p['period']['start']==previous['period']['end']),'REPLAY_BROKEN_DEPENDENCY');previous=p
    for t in tables['terms'].values():
        fields(t,COMMON|{'kind','effective','approved','approved_date','original_ref','flat_rate','lower_rate','upper_rate','threshold'});support(t,'earning_terms',ev,scope,cutoff);period(t['effective']);line(t['original_ref'])
        require(t['approved']is True and midnight(t['approved_date'])<=tick(t['observed_at'])and t['kind']in {'flat_ratio','cumulative_marginal'},'REPLAY_TERM_AUTHORITY')
        require(all(q(t[k])<=1 for k in ['flat_rate','lower_rate','upper_rate'])and q(t['lower_rate'])<=q(t['upper_rate']),'REPLAY_TERM_RATE');q(t['threshold'])
    refs=set();entitlements=set()
    for r in tables['receipts'].values():
        receipt(r,ev,scope,cutoff);require(r['period_id']in tables['periods'],'REPLAY_RECEIPT_PERIOD');p=tables['periods'][r['period_id']];a,b=period(p['period']);require(a<=day(r['effective_date'])<b and tick(r['observed_at'])<tick(p['cutoff']),'REPLAY_ORIGINAL_KNOWN_VIEW')
        require(r['original_ref']not in refs and r['entitlement_ref']not in entitlements,'REPLAY_RECEIPT_LINE_ALIAS');refs.add(r['original_ref']);entitlements.add(r['entitlement_ref'])
    original,by_receipt=compute(periods,list(tables['receipts'].values()),tables['terms'],{});issue_by_period={}
    for issue in tables['issued_artifacts'].values():
        fields(issue,COMMON|{'period_id','receipt_ids','complete','issued_at','original_ref','result_ref','predecessor_issue_id','basis_total','earned','opening_cumulative_basis','closing_cumulative_basis'})
        support(issue,'original_issued_artifact',ev,scope,cutoff);require(issue['period_id']in tables['periods']and issue['period_id']not in issue_by_period,'REPLAY_ISSUE_PERIOD');p=tables['periods'][issue['period_id']]
        require(midnight(p['period']['end'])<=tick(issue['issued_at'])<=tick(issue['observed_at'])<tick(p['cutoff']),'REPLAY_ISSUE_KNOWN_VIEW');line(issue['original_ref']);text(issue['result_ref'])
        expected=next(x for x in original if x['period_id']==p['id']);rs=[r for r in tables['receipts'].values()if r['period_id']==p['id']]
        require(issue['complete']is True and ids(issue['receipt_ids'])=={r['id']for r in rs} and all(tick(r['observed_at'])<=tick(issue['observed_at'])for r in rs),'REPLAY_COMPLETE_ORIGINAL_ISSUE')
        require(q(issue['basis_total'])==expected['gross_basis']and q(issue['earned'])==expected['earned']and q(issue['opening_cumulative_basis'])==expected['opening_cumulative_basis']and q(issue['closing_cumulative_basis'])==expected['closing_cumulative_basis'],'REPLAY_ORIGINAL_ISSUE_RECONCILIATION');issue_by_period[p['id']]=issue
    require(issue_by_period.keys()==tables['periods'].keys(),'REPLAY_COMPLETE_ISSUED_CHAIN')
    for i,p in enumerate(periods):require(issue_by_period[p['id']]['predecessor_issue_id']==(None if i==0 else issue_by_period[periods[i-1]['id']]['id']),'REPLAY_BROKEN_ISSUE_PREDECESSOR')
    require(len({x['original_ref']for x in issue_by_period.values()})==len(issue_by_period)and len({x['result_ref']for x in issue_by_period.values()})==len(issue_by_period),'REPLAY_ISSUE_ALIAS')
    applied_payment={k:Fraction()for k in tables['payments']};paid_receipt={k:Fraction()for k in tables['receipts']};bank_refs=set()
    for r in tables['payments'].values():
        fields(r,COMMON|{'receipt_id','payer_id','recipient_id','purpose','amount','paid_at','original_ref'});support(r,'actual_participation_payment',ev,scope,cutoff);require(r['receipt_id']in tables['receipts']and r['payer_id']==raw['payer_id']and r['recipient_id']==scope['participant_id']and r['purpose']=='participation_payment','REPLAY_PAYMENT_ROLES')
        require(midnight(tables['receipts'][r['receipt_id']]['effective_date'])<=tick(r['paid_at'])<=tick(r['observed_at'])and tick(r['paid_at'])<midnight(periods[-1]['period']['end']),'REPLAY_PAYMENT_CHRONOLOGY');ref=line(r['original_ref']);require(ref not in bank_refs,'REPLAY_BANK_LINE_ALIAS');bank_refs.add(ref);q(r['amount'])
    for r in tables['applications'].values():
        fields(r,COMMON|{'payment_id','receipt_id','original_entitlement_ref','amount','approved'});support(r,'actual_payment_application',ev,scope,cutoff);require(r['payment_id']in tables['payments']and r['receipt_id']in tables['receipts'],'REPLAY_PAYMENT_APPLICATION_REFERENCE');pay=tables['payments'][r['payment_id']];rec=tables['receipts'][r['receipt_id']]
        require(r['approved']is True and pay['receipt_id']==rec['id']and r['original_entitlement_ref']==rec['entitlement_ref']and tick(pay['observed_at'])<=tick(r['observed_at']),'REPLAY_PAYMENT_APPLICATION_AUTHORITY');applied_payment[pay['id']]+=q(r['amount']);paid_receipt[rec['id']]+=q(r['amount'])
    require(all(applied_payment[k]==q(p['amount'])for k,p in tables['payments'].items()),'REPLAY_PAYMENT_CONSERVATION');require(all(v<=by_receipt[k]for k,v in paid_receipt.items()),'REPLAY_ORIGINAL_PAYMENT_CEILING')
    pop=raw['payment_population'];fields(pop,COMMON|{'complete','through_period_id','payment_ids','application_ids','paid_total'});support(pop,'complete_historical_payment_population',ev,scope,cutoff)
    require(pop['complete']is True and pop['through_period_id']==periods[-1]['id']and ids(pop['payment_ids'])==tables['payments'].keys()and ids(pop['application_ids'])==tables['applications'].keys()and q(pop['paid_total'])==sum(paid_receipt.values(),Fraction()),'REPLAY_COMPLETE_PAID_POPULATION')
    require(tick(pop['observed_at'])>=midnight(periods[-1]['period']['end'])and all(tick(r['observed_at'])<=tick(pop['observed_at'])for k in ['payments','applications']for r in tables[k].values()),'REPLAY_PAYMENT_POPULATION_OBSERVATION')
    return periods,tables,original,issue_by_period,paid_receipt,refs|bank_refs


def _run(data):
    fields(data,{'schema_version','scope','policy','research','registry','opening_state',*FRAME}|({'prior_result'}if'prior_result'in data else set()));require(data['schema_version']=='dependent-replay-neutral/1','REPLAY_SCHEMA');scope=data['scope'];fields(scope,SCOPE)
    for v in scope.values():text(v)
    require(scope['currency']=='USD'and scope['purpose']=='authorized_dependent_replay','REPLAY_SCOPE');selected=data['policy'];require(selected==policy(selected['route']),'REPLAY_POLICY')
    fields(data['research'],{'catalog_sha256','backlog_sha256','scope_note'});require(all(type(data['research'][k])is str and re.fullmatch('[0-9a-f]{64}',data['research'][k])for k in ['catalog_sha256','backlog_sha256']),'REPLAY_RESEARCH_PIN');require(data['research']['scope_note']=='C13.DEPENDENT_PERIOD_REPLAY+C13.PROSPECTIVE_PERIOD_ADJUSTMENT;synthetic-positive-balance-only','REPLAY_RESEARCH_SCOPE')
    opening=data['opening_state'];require(type(opening)is dict and opening.get('origin')in {'genesis','prior_result'},'REPLAY_OPENING');history=opening.get('history',[]);require(type(history)is list and len(history)<=3,'REPLAY_HISTORY_BOUND')
    raw=normalized(data['registry']);current={k:deepcopy(data[k])for k in FRAME};frames=[deepcopy(x['facts'])for x in history]+[current];minimum=min(tick(f['cutoff'])for f in frames)
    originals,tables,initial,issues,paid_by_receipt,static_refs=registry(data['registry'],scope,minimum);require(len(originals)+len(frames)<=4,'REPLAY_TOTAL_PERIOD_BOUND')
    if opening['origin']=='genesis':require(opening=={'origin':'genesis','boundary':current['period']['start'],'source_case_id':'genesis','history':[]}and'prior_result'not in data,'REPLAY_GENESIS')
    else:
        require(opening.get('scope')==scope and opening.get('policy')==selected and opening.get('research')==data['research']and opening.get('registry')==raw,'REPLAY_PINNED_ORIGINALS_OR_ROUTE')
        require('prior_result'in data,'REPLAY_PREDECESSOR_REQUIRED');p=data['prior_result'];fields(p,{'source_case_id','period','closing_state','result_ref'});text(p['result_ref']);require(p['source_case_id']==opening['source_case_id']and p['closing_state']==opening and p['period']['end']==current['period']['start'],'REPLAY_PREDECESSOR_MISMATCH')
    closed=deepcopy(originals);all_receipts=deepcopy(list(tables['receipts'].values()));active={};consumed_ids=set();consumed_originals=set();authority_lines=set();replacement_lines=set();seen_case=set();replayed=[];recognized={r['period_id']:r['earned']for r in initial};paid=sum(paid_by_receipt.values(),Fraction());expected=None;latest=None;cumulative_credit=Fraction()
    for f in frames:
        fields(f,FRAME);text(f['case_id']);text(f['period_id']);require(f['case_id']not in seen_case,'REPLAY_DUPLICATE_CASE');seen_case.add(f['case_id']);start,end=period(f['period']);cutoff=tick(f['cutoff']);as_of=day(f['as_of'])
        require(as_of==end-timedelta(days=1)and cutoff>=end.toordinal()*86400,'REPLAY_COMPLETE_PERIOD');require(f['period']['start']==closed[-1]['period']['end']and f['predecessor_period_id']==closed[-1]['id']and f['period_id']not in {p['id']for p in closed},'REPLAY_BROKEN_DEPENDENCY');text(f['predecessor_result_ref'])
        if not replayed:require(f['predecessor_result_ref']==issues[closed[-1]['id']]['result_ref'],'REPLAY_ORIGINAL_PREDECESSOR_REFERENCE')
        if f is frames[-1] and opening['origin']=='prior_result':require(expected==opening and f['predecessor_result_ref']==data['prior_result']['result_ref'],'REPLAY_OPENING_RECONCILIATION')
        ev=evidence(f['evidence'],scope,cutoff);rs=index(f['receipts']);known_ids={r['id']for r in all_receipts};known_refs={r['original_ref']for r in all_receipts};known_entitlements={r['entitlement_ref']for r in all_receipts}
        for r in rs.values():
            receipt(r,ev,scope,cutoff);require(r['period_id']==f['period_id']and start<=day(r['effective_date'])<end,'REPLAY_CURRENT_RECEIPT_PERIOD');require(r['id']not in known_ids and r['original_ref']not in known_refs and r['original_ref']not in replacement_lines|static_refs,'REPLAY_RECEIPT_REUSE');known_ids.add(r['id']);known_refs.add(r['original_ref']);require(r['entitlement_ref']not in known_entitlements,'REPLAY_ENTITLEMENT_LINE_ALIAS');known_entitlements.add(r['entitlement_ref'])
        pop=f['population'];fields(pop,COMMON|{'period','complete','receipt_ids','gross_basis_total'});support(pop,'complete_current_receipt_population',ev,scope,cutoff);require(pop['complete']is True and pop['period']==f['period']and ids(pop['receipt_ids'])==rs.keys()and q(pop['gross_basis_total'])==sum((q(r['base_amount'])for r in rs.values()),Fraction()),'REPLAY_COMPLETE_CURRENT_POPULATION');require(tick(pop['observed_at'])>=midnight(f['period']['end'])and all(tick(r['observed_at'])<=tick(pop['observed_at'])for r in rs.values()),'REPLAY_POPULATION_OBSERVATION')
        cash=f['cash_population'];fields(cash,COMMON|{'period','complete','event_ids','total'});support(cash,'complete_current_cash_population',ev,scope,cutoff);require(cash['complete']is True and cash['period']==f['period'],'REPLAY_CURRENT_CASH_UNKNOWN');require(tick(cash['observed_at'])>=midnight(f['period']['end']),'REPLAY_POPULATION_OBSERVATION');require(cash['event_ids']==[]and q(cash['total'])==0,'REPLAY_NONEMPTY_CURRENT_CASH_VARIANT_REQUIRED')
        replacements=index(f['replacements']);authorities=index(f['authorities']);requests=index(f['requests']);cp=f['correction_population'];fields(cp,COMMON|{'period','complete','request_ids','replacement_ids','authority_ids'});support(cp,'complete_correction_population',ev,scope,cutoff)
        require(cp['complete']is True and cp['period']==f['period']and ids(cp['request_ids'])==requests.keys()and ids(cp['replacement_ids'])==replacements.keys()and ids(cp['authority_ids'])==authorities.keys(),'REPLAY_COMPLETE_CORRECTION_POPULATION')
        require(tick(cp['observed_at'])>=midnight(f['period']['end']),'REPLAY_POPULATION_OBSERVATION')
        for r in replacements.values():
            fields(r,COMMON|{'original_receipt_id','base_amount','effective_date','original_basis_ref','original_ref'});support(r,'replacement_measurement',ev,scope,cutoff);q(r['base_amount']);line(r['original_ref']);require(r['original_receipt_id']in tables['receipts'],'REPLAY_REPLACEMENT_ORIGINAL_REQUIRED');old=tables['receipts'][r['original_receipt_id']];require(r['effective_date']==old['effective_date']and r['original_basis_ref']==old['original_ref'],'REPLAY_REPLACEMENT_LINK');require(midnight(r['effective_date'])<=tick(r['observed_at'])and tick(old['observed_at'])<=tick(r['observed_at']),'REPLAY_REPLACEMENT_CHRONOLOGY')
        for a in authorities.values():
            fields(a,COMMON|{'replacement_id','original_receipt_id','original_issue_id','route','dependent_period_ids','predecessor_result_ref','approved','approved_date','recorded_date','apply_revised_basis_to_future','original_ref'});support(a,'correction_authority',ev,scope,cutoff);line(a['original_ref']);require(a['approved']is True and a['apply_revised_basis_to_future']is True and a['route']==selected['route']and day(a['approved_date'])<=day(a['recorded_date'])<=as_of and midnight(a['recorded_date'])<=tick(a['observed_at']),'REPLAY_CORRECTION_AUTHORITY')
        orders=set();changes=[];adjustments=[];restatements=[]
        require({r['replacement_id']for r in requests.values()}==replacements.keys()and{r['authority_id']for r in requests.values()}==authorities.keys()and len(requests)==len(replacements)==len(authorities),'REPLAY_CORRECTION_REFERENCE_POPULATION')
        for request in requests.values():
            fields(request,COMMON|{'replacement_id','authority_id','sequence'});support(request,'correction_request',ev,scope,cutoff);require(type(request['sequence'])is int and request['sequence']>=0,'REPLAY_CORRECTION_SEQUENCE');require(request['authority_id']in authorities and request['replacement_id']in replacements,'REPLAY_CORRECTION_REFERENCE')
        ordered=sorted(requests.values(),key=lambda r:(authorities[r['authority_id']]['recorded_date'],r['sequence']))
        for request in ordered:
            repl=replacements[request['replacement_id']];a=authorities[request['authority_id']];old=tables['receipts'][repl['original_receipt_id']];order=(a['recorded_date'],request['sequence']);require(order not in orders,'REPLAY_UNRESOLVED_CORRECTION_ORDER');orders.add(order)
            require(request['id']not in consumed_ids and old['id']not in consumed_originals,'REPLAY_CORRECTION_ALREADY_CONSUMED');require(a['replacement_id']==repl['id']and a['original_receipt_id']==old['id']and a['original_issue_id']==issues[old['period_id']]['id']and a['predecessor_result_ref']==f['predecessor_result_ref'],'REPLAY_CORRECTION_LINK')
            old_issue=issues[old['period_id']]
            require(tick(old_issue['issued_at'])<=tick(a['observed_at'])and tick(old_issue['issued_at'])//86400<=day(a['recorded_date']).toordinal(),'REPLAY_AUTHORITY_PRECEDES_ISSUE')
            start_index=next(i for i,p in enumerate(closed)if p['id']==old['period_id']);require(a['dependent_period_ids']==[p['id']for p in closed[start_index:]],'REPLAY_COMPLETE_DEPENDENT_CHAIN')
            require(tick(repl['observed_at'])<=tick(a['observed_at'])<=tick(request['observed_at'])<=tick(cp['observed_at']),'REPLAY_CORRECTION_OBSERVATION_ORDER');require(repl['original_ref']not in replacement_lines|known_refs|static_refs and a['original_ref']not in authority_lines,'REPLAY_CORRECTION_LINE_ALIAS')
            before,_=compute(closed,all_receipts,tables['terms'],active);active[old['id']]=deepcopy(repl);after,per_receipt=compute(closed,all_receipts,tables['terms'],active)
            require(all(v<=per_receipt[k]for k,v in paid_by_receipt.items()),'REPLAY_OVERPAYMENT_RECOVERY_VARIANT_REQUIRED')
            for previous,revised in zip(before[start_index:],after[start_index:]):
                delta=revised['earned']-previous['earned'];entry={'key':[f['case_id'],a['original_ref'],revised['period_id']],'request_id':request['id'],'replacement_id':repl['id'],'authority_id':a['id'],'affected_period_id':revised['period_id'],'previous_earned':previous['earned'],'revised_earned':revised['earned'],'delta':delta,'original_issued_result_ref':issues[revised['period_id']]['result_ref']if revised['period_id']in issues else None}
                (restatements if selected['route']=='restatement'else adjustments).append(entry)
            changes.append({'request_id':request['id'],'original_receipt_id':old['id'],'original_basis':q(old['base_amount']),'replacement_basis':q(repl['base_amount']),'basis_delta':q(repl['base_amount'])-q(old['base_amount']),'dependent_period_ids':deepcopy(a['dependent_period_ids'])});consumed_ids.add(request['id']);consumed_originals.add(old['id']);replacement_lines.add(repl['original_ref']);authority_lines.add(a['original_ref'])
        closed_before,_=compute(closed,all_receipts,tables['terms'],active)
        current_period={'id':f['period_id'],'period':deepcopy(f['period'])};new_periods=closed+[current_period];new_receipts=all_receipts+list(rs.values());economic,per_receipt=compute(new_periods,new_receipts,tables['terms'],active);new_earning=economic[-1]['earned'];posted=sum((r['delta']for r in adjustments),Fraction());current_recognized=new_earning+posted
        if selected['route']=='restatement':recognized={r['period_id']:r['earned']for r in economic}
        else:recognized[f['period_id']]=current_recognized
        total=sum(recognized.values(),Fraction());economic_total=sum((r['earned']for r in economic),Fraction());require(total==economic_total,'REPLAY_ATTRIBUTION_RECONCILIATION');require(total>=paid,'REPLAY_POSITIVE_BALANCE_SCOPE')
        original_issued_total=sum((q(i['earned'])for i in issues.values()),Fraction())
        unissued_earnings=sum((Fraction(h['result']['current_economic_earned'])for h in replayed),Fraction())+new_earning
        cumulative_credit+=sum((r['delta']for r in restatements+adjustments),Fraction())
        require(original_issued_total-paid+unissued_earnings+cumulative_credit==total-paid,'REPLAY_ISSUED_UNISSUED_BRIDGE')
        revised_original_total=sum((r['earned']for r in economic if r['period_id']in issues),Fraction())
        lines=[{'period_id':r['period_id'],'period':deepcopy(r['period']),'original_issued_entitlement':q(issues[r['period_id']]['earned'])if r['period_id']in issues else None,'original_issued_result_ref':issues[r['period_id']]['result_ref']if r['period_id']in issues else None,'economic_earned':r['earned'],'recognized_entitlement':recognized[r['period_id']],'opening_cumulative_basis':r['opening_cumulative_basis'],'closing_cumulative_basis':r['closing_cumulative_basis']}for r in economic]
        latest={'source_case_id':f['case_id'],'period':deepcopy(f['period']),'route':selected['route'],'status':'calculated','current_gross_basis':economic[-1]['gross_basis'],'current_economic_earned':new_earning,'current_posted_adjustment':posted,'current_recognized':current_recognized,'cumulative_economic_entitlement':economic_total,'cumulative_recognized_entitlement':total,'actual_original_paid':paid,'original_issued_total':original_issued_total,'original_issued_unpaid':original_issued_total-paid,'revised_original_issued_economic_total':revised_original_total,'revised_original_issued_economic_unpaid':revised_original_total-paid,'calculated_unissued_earnings':unissued_earnings,'authorized_correction_credit':cumulative_credit,'signed_net_unissued_recognition':total-original_issued_total,'calculated_restatement_credit':cumulative_credit if selected['route']=='restatement'else Fraction(),'calculated_prospective_credit':cumulative_credit if selected['route']=='prospective'else Fraction(),'outstanding':total-paid,'closing_cumulative_basis':economic[-1]['closing_cumulative_basis'],'original_period_controls':deepcopy(initial),'replayed_period_controls':economic,'period_lines':lines,'source_changes':changes,'restatement_records':restatements,'prospective_adjustments':adjustments,'consumed_correction_ids':sorted(consumed_ids),'original_issued_artifacts':deepcopy(sorted(tables['issued_artifacts'].values(),key=lambda r:tables['periods'][r['period_id']]['period']['start'])),'actual_current_cash':Fraction(),'bank_movement_created':False,'adjustment_issued_or_paid':False,'issuance_status':'unissued_calculation','outstanding_measure':'revised_economic_entitlement_less_actual_paid','bridge_measure':'immutable_issued_unpaid_plus_calculated_unissued_credit_and_earnings','measure':'recognized_entitlement_balance_not_new_total_disbursement'}
        if f is not frames[-1]:
            record=history[len(replayed)];fields(record,{'facts','result'});require(exact_json(latest)==record['result'],'REPLAY_HISTORY_FINANCIAL_REPLAY')
        replayed.append({'facts':deepcopy(f),'result':exact_json(latest)});closed=new_periods;all_receipts=new_receipts
        expected=exact_json({'schema_version':'dependent-replay-state/1','scope':deepcopy(scope),'policy':deepcopy(selected),'research':deepcopy(data['research']),'registry':deepcopy(raw),'boundary':f['period']['end'],'origin':'prior_result','source_case_id':f['case_id'],'history':deepcopy(replayed),'active_replacements':deepcopy(sorted(active.values(),key=lambda r:r['id'])),'consumed_correction_ids':sorted(consumed_ids),'consumed_original_receipt_ids':sorted(consumed_originals),'recognized_period_lines':deepcopy(lines),'cumulative_basis':economic[-1]['closing_cumulative_basis'],'recognized_entitlement':total,'actual_paid':paid,'authorized_correction_credit':cumulative_credit,'outstanding':total-paid})
    return {**latest,'closing_state':expected}


def dependent_replay(data):
    try:return _run(data)
    except (KeyError,TypeError,ValueError,StopIteration,ZeroDivisionError)as error:
        if isinstance(error,DependentReplayOracleError):raise
        raise DependentReplayOracleError('REPLAY_MALFORMED_INPUT')from error

def exact_json(value):
    if isinstance(value,Fraction):return str(value)
    if isinstance(value,dict):return {k:exact_json(v)for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [exact_json(v)for v in value]
    return value
