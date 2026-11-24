"""Mechanical original transport for mixed claims; all economic decisions are SPL."""
from copy import deepcopy
from datetime import date, timedelta
from fractions import Fraction
import json
from pathlib import Path
import re
from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.checker import check_schedule
from spl_compiler.codecs import canonical, exact, instant, instant_utc_day, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package
from spl_compiler.parser import parse

ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = 'SYNTHETIC-MIXED-CLAIMS-01'
PURPOSE = 'mixed_claim_recovery'
TRANSPORT = 'mixed-claims-original-json/3'
IDENTITY_CODEC = 'unicode-utf8-hex/1'
MONEY = {'amount','base_amount','total','gross_basis_total','original_basis','return_basis','paid_total','authorized_principal','source_capacity','unallocated_source_capacity','recoupment_credit','earning_offset','remaining','original_base','derived_fee','original_entitlement','reversal','revised_entitlement','actual_original_paid','original_outstanding','potential_overpayment','capital_actual_funding','advance_actual_funding','capacity','recoupment_credits','earning_offsets','residual_entitlement','unissued_allocations_added','derived_capacity','eligible_opening_balance','recovery_pool','residual','opening_remaining','available_before','applied','closing_remaining','available_after','actual_current_claim_cash_settlement'}
RATIO = {'rate','original_rate','share','weight'}
DATE = {'approved_date','recorded_date','eligible_from','effective_date','original_date','return_date','as_of'}
INSTANT = {'observed_at','paid_at','funded_at','cutoff'}
IDENTITY = {'id','agreement_id','pool_id','asset_id','participant_group','participant_id','payer_id','funder_id','recipient_group','creditor_id','debtor_group','beneficiary','evidence_ref','source_ref','original_ref','original_entitlement_ref','return_ref','correction_source_id','payment_id','claim_id','earning_id','source_case_id','case_id'}
IDLIST = {'participant_ids','member_ids','source_ids','funding_ids','payment_ids','application_ids','earning_ids','event_ids','consumed_earning_ids','consumed_earning_refs'}
FRAME = {'case_id','period','as_of','cutoff','earnings','earning_population','cash_settlement_population','evidence'}

def _fields(v, fields, optional=()):
    if type(v) is not dict or not set(fields) <= v.keys() <= set(fields)|set(optional): raise ValueError('MIXED_RECORD_FIELDS')

def encode_identity(v):
    if type(v) is not str or not v or any(0xD800<=ord(c)<=0xDFFF for c in v): raise ValueError('MIXED_TEXT_IDENTITY')
    return v.encode('utf-8').hex()

def decode_identity(v):
    if type(v) is not str or not v or len(v)%2 or not re.fullmatch('[0-9a-f]+',v): raise ValueError('MIXED_IDENTITY_TRANSPORT')
    try: result=bytes.fromhex(v).decode('utf-8',errors='strict')
    except (UnicodeError,ValueError): raise ValueError('MIXED_IDENTITY_TRANSPORT') from None
    if encode_identity(result)!=v: raise ValueError('MIXED_IDENTITY_TRANSPORT')
    return result

def _q(v):
    if type(v) is not str or not re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+|/[1-9][0-9]*)?',v): raise ValueError('MIXED_EXACT_NONNEGATIVE')
    return Fraction(v)

def _raw(v):
    s=json.dumps(v,ensure_ascii=True,sort_keys=True,separators=(',',':'))
    if json.loads(s)!=v: raise ValueError('MIXED_ORIGINAL_JSON_TRANSPORT')
    return s

def _unraw(v):
    if type(v) is not str:raise ValueError('MIXED_ORIGINAL_JSON_TRANSPORT')
    def reject(x):raise ValueError('MIXED_ORIGINAL_JSON_TRANSPORT')
    try:original=json.loads(v,parse_constant=reject)
    except (ValueError,TypeError):raise ValueError('MIXED_ORIGINAL_JSON_TRANSPORT') from None
    if _raw(original)!=v:raise ValueError('MIXED_ORIGINAL_JSON_TRANSPORT')
    return original

def _normalized(v):
    r=deepcopy(v)
    for k, rows in r.items():
        if isinstance(rows,list): r[k]=sorted(rows,key=lambda x:x.get('id',x.get('participant_id',''))) if rows and isinstance(rows[0],dict) else sorted(rows)
    return r

def _encode(v,k=''):
    if k in IDLIST:
        if type(v) is not list: raise ValueError('MIXED_ID_LIST')
        return [encode_identity(x) for x in v]
    if isinstance(v,list):
        if len(v)>32: raise ValueError('MIXED_FINITE_ROWS')
        return [_encode(x) for x in v]
    if isinstance(v,dict):
        out={key:_encode(x,key) for key,x in v.items()}
        for key,x in v.items():
            if key=='funded_at':out['funded_utc_date']=instant_utc_day(x).isoformat()
            if key=='share':out['share_source']=x
            if key in DATE: out[key+'_utc']=x+'T00:00:00Z'
        return out
    if k in IDENTITY:return encode_identity(v)
    if k in MONEY:return money(_q(v))
    if k in RATIO:return number(_q(v))
    if k in DATE or k in {'start','end','boundary'}: date.fromisoformat(v)
    if k in INSTANT: instant(v)
    if k in {'sequence','priority'}:
        if type(v) is not int: raise ValueError('MIXED_INTEGER')
        return number(v)
    if k.endswith('original_ref') or k in {'return_ref'}:
        a,sep,b=v.rpartition('#')
        if not(a and sep and b): raise ValueError('MIXED_ORIGINAL_LINE_REFERENCE')
    return deepcopy(v)

def _decode(v,k=''):
    if k in IDLIST:return [decode_identity(x) for x in v]
    if isinstance(v,list):return [_decode(x) for x in v]
    if isinstance(v,dict):
        if set(v)=={'value','currency'}:
            if v['currency']!='USD':raise ValueError('MIXED_CURRENCY')
            return str(exact(v['value']))
        if set(v)=={'numerator','denominator'}:return int(exact(v)) if k in {'sequence','priority'} else str(exact(v))
        return {key:_decode(x,key) for key,x in v.items() if not key.endswith('_utc') and key not in {'share_source','funded_utc_date'}}
    if k in MONEY|RATIO:return str(Fraction(v))
    if k in IDENTITY:return decode_identity(v)
    if k in {'sequence','priority'}:return int(exact(v))
    return v

def _fact(v, exemplar):
    _fields(v,exemplar)
    for key in ['original_ref','original_entitlement_ref','return_ref']:
        if key in v:
            a,sep,b=v[key].rpartition('#')
            if not (a and sep and b):raise ValueError('MIXED_ORIGINAL_LINE_REFERENCE')
    if 'scope'in v:_fields(v['scope'],{'agreement_id','pool_id','asset_id','participant_group','purpose','currency'})
    for key in ['period','effective']:
        if key in v:_fields(v[key],{'start','end'})
    row=_encode(v)
    # Every original is validated before any projection; raw source preserves lexemes.
    decoded=_decode(row)
    def same(a,b,key=''):
        if isinstance(b,dict):return set(a)==set(b) and all(same(a[x],b[x],x) for x in b)
        if isinstance(b,list):return len(a)==len(b) and all(same(x,y,key) for x,y in zip(a,b))
        if key in MONEY|RATIO:return Fraction(a)==Fraction(b)
        if key in INSTANT:return instant(a)==instant(b)
        return a==b
    if not same(decoded,v):raise ValueError('MIXED_TYPED_ORIGINAL_TRANSPORT')
    return row

def _frame(v):
    _fields(v,FRAME)
    ex=read_json(FOLDER/'neutral.json')
    row={k:_encode(v[k],k) for k in ['case_id','period','as_of','cutoff']}
    row['as_of_next']=(date.fromisoformat(v['as_of'])+timedelta(days=1)).isoformat()
    for k in ['earnings','evidence']:row[k]=[_fact(x,ex[k][0]) for x in v[k]]
    for k in ['earning_population','cash_settlement_population']:row[k]=_fact(v[k],ex[k])
    row['as_of_next_utc']=row['as_of_next']+'T00:00:00Z'
    row['period_end_utc']=v['period']['end']+'T00:00:00Z'
    row['period_start_utc']=v['period']['start']+'T00:00:00Z'
    return row

def _registry(v):
    ex=read_json(FOLDER/'neutral.json')['registry'];_fields(v,ex)
    row={}
    for k,x in v.items():
        if k in IDLIST or k=='payer_id':row[k]=_encode(x,k)
        elif isinstance(x,list):row[k]=[_fact(a,ex[k][0]) for a in x]
        else:row[k]=_fact(x,ex[k])
    return row

def _result(v, registry, frame):
    row=deepcopy(v)
    authorities={x['id']:x for x in registry['claim_authorities']}
    earnings={x['id']:x for x in frame['earnings']}
    for claim in row['claim_ledger']:
        if claim.pop('authority')!=authorities.get(claim['id']):raise ValueError('MIXED_ORIGINAL_AUTHORITY_TRANSPORT')
    for event in row['event_details']:
        original=event.pop('earning')
        if original!=earnings.get(original['id']):raise ValueError('MIXED_ORIGINAL_EARNING_TRANSPORT')
        event['earning_id']=original['id']
    for key in ['current_unissued_allocations','current_offset_records']:
        for item in row[key]:
            item['key']= [encode_identity(x) for x in item['key']]
            item['claim_id']={'some':encode_identity(item['claim_id'])} if 'claim_id' in item else {'none':True}
    return _encode_result(row)

def _encode_result(v,k=''):
    if k in {'key','claim_id'} and (isinstance(v,list) or isinstance(v,dict)):return deepcopy(v)
    if k=='original_share':return v
    if isinstance(v,list):return [_encode_result(x) for x in v]
    if isinstance(v,dict):return {a:_encode_result(b,a) for a,b in v.items()}
    return _encode(v,k)

def _original_frame(v):
    return {'id':encode_identity(v['case_id']),'original':_raw(v),'earning_ids':[encode_identity(x['id']) for x in v['earnings']],'evidence_ids':[encode_identity(x['id']) for x in v['evidence']],'earning_population_id':encode_identity(v['earning_population']['id']),'cash_population_id':encode_identity(v['cash_settlement_population']['id'])}

def _registry_ids(v):
    rows=[]
    for key,value in v.items():
        if key=='payer_id':continue
        if key=='participant_ids':ids=[encode_identity(x) for x in value]
        elif isinstance(value,list):ids=[encode_identity(x['participant_id'] if key=='residual_weights' else x['id']) for x in value]
        else:ids=[encode_identity(value['id'])]
        rows.append({'category':key,'ids':sorted(ids)})
    return rows

def _state(v):
    genesis={'origin','boundary','source_case_id','history'}
    if v.get('origin')=='genesis':
        _fields(v,genesis)
        if v['history']!=[]:raise ValueError('MIXED_GENESIS')
        return {'boundary':v['boundary'],'origin':'genesis','source_case_id':encode_identity(v['source_case_id']),'detail':{'none':True},'transport_profile':TRANSPORT,'identity_codec':IDENTITY_CODEC}
    _fields(v,{'schema_version','scope','policy','research','registry','boundary','origin','source_case_id','history','claim_ledger','unissued_allocation_ledger','earning_offset_ledger','consumed_earning_ids','consumed_earning_refs'})
    if v['schema_version']!='mixed-claim-state/1':raise ValueError('MIXED_STATE_SCHEMA')
    for record in v['history']:_fields(record,{'facts','result'})
    detail={k:deepcopy(v[k]) for k in ['scope','policy','research']}
    detail['registry']=_registry(v['registry'])
    detail['registry_original']=_raw(_normalized(v['registry']))
    detail['original_frames']=[_original_frame(x['facts']) for x in v['history']]
    detail['history']=[{'id':encode_identity(x['facts']['case_id']),'facts':_frame(x['facts']),'result':_result(x['result'],v['registry'],x['facts'])} for x in v['history']]
    for k in ['claim_ledger','unissued_allocation_ledger','earning_offset_ledger','consumed_earning_ids','consumed_earning_refs']:
        if k=='claim_ledger':
            rows=deepcopy(v[k]);authorities={x['id']:x for x in v['registry']['claim_authorities']}
            for x in rows:
                if x.pop('authority')!=authorities.get(x['id']):raise ValueError('MIXED_ORIGINAL_AUTHORITY_TRANSPORT')
            detail[k]=_encode(rows)
        elif k.endswith('_ledger'):
            rows=deepcopy(v[k])
            for x in rows:
                x['key']=[encode_identity(a) for a in x['key']]
                x['claim_id']={'some':encode_identity(x['claim_id'])} if 'claim_id'in x else {'none':True}
            detail[k]=_encode_result(rows)
        else:detail[k]=_encode(v[k],k)
    detail['scope']=_encode(v['scope'])
    return {'boundary':v['boundary'],'origin':v['origin'],'source_case_id':encode_identity(v['source_case_id']),'detail':{'some':detail},'transport_profile':TRANSPORT,'identity_codec':IDENTITY_CODEC}

def _restore_result(v,registry,frame):
    row=_decode(v)
    authorities={x['id']:x for x in registry['claim_authorities']}
    for claim in row['claim_ledger']:claim['authority']=deepcopy(authorities[claim['id']])
    earnings={x['id']:x for x in frame['earnings']}
    for event in row['event_details']:event['earning']=deepcopy(earnings[event.pop('earning_id')])
    for key in ['current_unissued_allocations','current_offset_records']:
        for x in row[key]:
            x['key']=[decode_identity(a) for a in x['key']]
            option=x.pop('claim_id')
            if 'some' in option:x['claim_id']=decode_identity(option['some'])
    return row

def _wire_equal(actual, expected, key=''):
    if isinstance(expected,dict) and set(expected)=={'numerator','denominator'}:
        return exact(actual)==exact(expected)
    if isinstance(expected,dict):
        return isinstance(actual,dict) and set(actual)==set(expected) and all(_wire_equal(actual[k],v,k) for k,v in expected.items())
    if isinstance(expected,list):
        return isinstance(actual,list) and len(actual)==len(expected) and all(_wire_equal(a,b,key) for a,b in zip(actual,expected))
    if key in INSTANT or key.endswith('_utc'):return instant(actual)==instant(expected)
    if key in RATIO|{'sequence','priority'}:return exact(actual)==exact(expected)
    return actual==expected

def neutral_state(v):
    if v['transport_profile']!=TRANSPORT or v['identity_codec']!=IDENTITY_CODEC:raise ValueError('MIXED_TRANSPORT_PROFILE')
    if v['origin']=='genesis':return {'origin':'genesis','boundary':v['boundary'],'source_case_id':decode_identity(v['source_case_id']),'history':[]}
    d=v['detail']['some'];registry=_unraw(d['registry_original'])
    if not _wire_equal(d['registry'],_registry(registry)):raise ValueError('MIXED_TYPED_REGISTRY_TRANSPORT')
    originals={x['id']:_unraw(x['original']) for x in d['original_frames']}
    if len(originals)!=len(d['original_frames']) or [x['id'] for x in d['original_frames']]!=[x['id'] for x in d['history']]:raise ValueError('MIXED_ORIGINAL_FRAME_POPULATION')
    for original in d['original_frames']:
        if _original_frame(originals[original['id']])!=original:raise ValueError('MIXED_ORIGINAL_FRAME_POPULATION')
    for item in d['history']:
        if not _wire_equal(item['facts'],_frame(originals[item['id']])):raise ValueError('MIXED_TYPED_FRAME_TRANSPORT')
    history=[{'facts':originals[x['id']],'result':_restore_result(x['result'],registry,originals[x['id']])} for x in d['history']]
    ledger=_decode(d['claim_ledger']);authorities={x['id']:x for x in registry['claim_authorities']}
    for c in ledger:c['authority']=deepcopy(authorities[c['id']])
    result={'schema_version':'mixed-claim-state/1','scope':_decode(d['scope']),'policy':d['policy'],'research':d['research'],'registry':registry,'boundary':v['boundary'],'origin':v['origin'],'source_case_id':decode_identity(v['source_case_id']),'history':history,'claim_ledger':ledger}
    for key in ['unissued_allocation_ledger','earning_offset_ledger']:
        rows=_decode(d[key])
        for x in rows:
            x['key']=[decode_identity(a) for a in x['key']];o=x.pop('claim_id')
            if 'some'in o:x['claim_id']=decode_identity(o['some'])
        result[key]=rows
    for k in ['consumed_earning_ids','consumed_earning_refs']:result[k]=_decode(d[k],k)
    return result

def neutral_result(v,data):return _restore_result(v,data['registry'],{k:data[k] for k in FRAME})

def _export_type(v):
    r={'name':v.name,'args':[_export_type(x) for x in v.args]}
    if v.name=='Record':r['fields']=[[k,_export_type(t)]for k,t in v.fields]
    return r

def _registered_descriptor(name, *args, **kwargs):
    reference=_descriptor(name,*args,**kwargs)
    path=ROOT/reference['locator'];descriptor=read_json(path)
    descriptor['id']='synthetic:'+name
    descriptor['policy'].update(id=POLICY,evidence_class='synthetic',review_status='proposed',discriminating_cases=['four-original-claim-kinds','fee-correction-priority','exact-eligible-balance-pro-rata','original-paid-not-rewritten','actual-adjacent-carry'])
    write_json(path,descriptor)
    return {'id':descriptor['id'],'revision':'1',**_pin(path)}

def register_mixed_claims():
    refs=[]
    for name,definition in [('claim-registry','registered'),('claim-period','calculated')]:
        syntax=parse((FOLDER/(name+'.spl')).read_text(encoding='utf-8'));check_schedule(syntax)
        params=[{'name':d['name'],'type':d['type']}for d in syntax['declarations']if d['kind']=='input']
        result=_export_type(next(d for d in syntax['declarations']if d.get('name')==definition)['expr']['_type'])
        ref=_registered_descriptor(name,name+'.spl','policy.md',{},folder=FOLDER,exports=[{'name':'calculate','definition':definition,'parameters':params,'result':result}]);refs.append(ref)
    reference=_registered_descriptor('mixed-claims','mixed-claims.spl','policy.md',{'cutoff':'parameter','policy':'parameter','evidence':'evidence','comparison':'result','reconciliation':'reconciliation'},folder=FOLDER,
        imports=[{'module_ref':r,'alias':alias,'symbols':[{'export':'calculate','local':local}]}for r,alias,local in zip(refs,['registry','period'],['register_claims','calculate_period'])],
        state=[{'opening':'history','closing':'history','purpose':PURPOSE,'unit':'structured','key_fields':['agreement_id','participant_id','pool_id','asset_id','purpose'],'movement_kinds':['transition'],'history_required':False}])
    return reference

def mixed_claim_package(fixture=None,*,reference=None,state_cells=None,mode='final'):
    data=deepcopy(read_json(FOLDER/'neutral.json')if fixture is None else fixture)
    _fields(data,{'schema_version','scope','policy','research','registry','opening_state',*FRAME},{'prior_result'})
    if data['schema_version']!='mixed-claims-neutral/1' or mode not in {'final','preview'}:raise ValueError('MIXED_SCHEMA')
    _fields(data['scope'],{'agreement_id','pool_id','asset_id','participant_group','purpose','currency'})
    _fields(data['policy'],read_json(FOLDER/'neutral.json')['policy'])
    _fields(data['research'],{'atomic_catalog_sha256','waterfall_policy_sha256','offset_policy_sha256','scope_note'})
    for key in ['atomic_catalog_sha256','waterfall_policy_sha256','offset_policy_sha256']:
        if type(data['research'][key]) is not str or not re.fullmatch('[0-9a-f]{64}',data['research'][key]):raise ValueError('MIXED_REVIEW_PIN')
    registry=_registry(data['registry']);frame=_frame({k:data[k]for k in FRAME});scope=_encode(data['scope'])
    reference=reference or register_mixed_claims();opening=_state(data['opening_state'])
    outer={'agreement_id':scope['agreement_id'],'participant_id':scope['participant_group'],'pool_id':scope['pool_id'],'asset_id':scope['asset_id']}
    inputs={'scope':{k:v for k,v in outer.items()if k!='asset_id'}|{'period':data['period']},'project':scope['asset_id'],'fact_scope':scope,'research':data['research'],'registry':registry,'registry_original':_raw(_normalized(data['registry'])),'original_registry_ids':_registry_ids(data['registry']),'original_frames':[_original_frame(x['facts']) for x in data['opening_state'].get('history',[])]+[_original_frame({k:data[k] for k in FRAME})],'frame':frame,'supplied_opening':opening,'predecessor':{'none':True}}
    cell={'opening_port':'history','state_key':canonical({**outer,'purpose':PURPOSE}),'purpose':PURPOSE,'unit':'structured','scope':outer,'boundary':data['period']['start'],'quantity':opening,'provenance_ref':'supplied-original-mixed-claim-history','scenario_id':'SYNTHETIC-MIXED-CLAIMS'}
    if 'prior_result'in data:
        prior=data['prior_result'];_fields(prior,{'source_case_id','period','closing_state'},{'result_ref'})
        if type(prior.get('result_ref'))is not str or not prior['result_ref'].startswith('result@sha256:'):raise ValueError('MIXED_CANONICAL_PREDECESSOR_REQUIRED')
        inputs['predecessor']={'some':{'source_case_id':encode_identity(prior['source_case_id']),'period':prior['period'],'closing_state':_state(prior['closing_state'])}}
        cell['prior_result_ref']=prior['result_ref']
    cells=deepcopy(state_cells)if state_cells is not None else [cell]
    if 'prior_result'in data and any(c.get('prior_result_ref')!=cell['prior_result_ref']for c in cells):raise ValueError('MIXED_CANONICAL_PREDECESSOR_MISMATCH')
    evidence=[{'id':r['id'],'kind':'selected_synthetic_record','observed_at':r['observed_at'],'approval_ref':'MIXED_CLAIMS_SELECTED','evidence_ref':r['id']}for r in frame['evidence']]
    package={'profile':'spl-module/1','module_ref':reference,'manifest':{'run_id':encode_identity(data['case_id'])+'-run','scenario_id':'SYNTHETIC-MIXED-CLAIMS','mode':mode,'period':data['period'],'cutoff':data['cutoff'],'compiler_build':'unbound','runtime_build':'unbound','module_closure':[],'resource_limits':{'max_input_rows':100000,'lean_timeout_seconds':180}},'scope':{'agreement_id':outer['agreement_id'],'participant_ids':[outer['participant_id']],'pool_id':outer['pool_id'],'asset_ids':[outer['asset_id']],'purpose':PURPOSE},'inputs':inputs,'parameters':{'cutoff':data['cutoff'],'policy':data['policy']},'evidence':{'evidence':evidence},'state_cells':cells,'decisions':[{'decision_id':n,'policy_id':r['descriptor']['policy']['id'],'policy_revision':'1','status':'proposed','evidence_ref':'synthetic-selected-mixed-claims-policy'}for r in resolve_module(reference,ROOT).closure for n in r['descriptor']['policy']['decision_ids']]}
    return bind_module_package(package,ROOT)

def run_mixed_claim_package(package,registry_root=None,*,backend='compare',artifact_dir=None):return run_module_package(package,registry_root or ROOT,backend=backend,artifact_dir=artifact_dir)

if __name__=='__main__':
    reference=register_mixed_claims()
    for mode,name in [('final','canonical-package.json'),('preview','preview-canonical-package.json')]:
        p=mixed_claim_package(reference=reference,mode=mode);p['manifest'].update(compiler_build='unbound',runtime_build='unbound',module_closure=[]);write_json(FOLDER/name,p)








