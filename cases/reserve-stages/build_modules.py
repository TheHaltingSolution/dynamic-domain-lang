"""Reversible original/typed transport. Financial decisions execute in SPL.

The public runner validates complete original/typed correspondence before the
generic runner, whose prepared-binding boundary is explicitly trusted.
"""
from copy import deepcopy
from datetime import date
from fractions import Fraction
from importlib import import_module
import json
from math import gcd
from pathlib import Path
import re

from cases.r1.build_modules import _descriptor, _pin
from spl_compiler.codecs import canonical, exact, instant, money, number, read_json, write_json
from spl_compiler.modules import bind_module_package, resolve_module, run_module_package

s = import_module('cases.reserve-stages.source')
ROOT = Path(__file__).resolve().parents[2]
FOLDER = Path(__file__).resolve().parent
POLICY = 'SYNTHETIC-RESERVE-STAGES-01'
PURPOSE = 'synthetic_reserve_stage_history'
TRANSPORT = 'reserve-stages-original-json/1'
FRAME_KEYS = {'case_id','period','as_of','cutoff','receipts','elections','applications','authorities','population','evidence'}
CONTEXT_KEYS = {'schema_version','scope','policy','terms','registry_evidence'}

def raw(value): return json.dumps(value,ensure_ascii=True,separators=(',',':'))
def context_raw(value): return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'))
def loads(value):
    def pairs(items):
        result = {}
        for k,v in items:
            if k in result: raise ValueError('RS_DUPLICATE_JSON_KEY')
            result[k] = v
        return result
    def reject(value): raise ValueError('RS_JSON_NUMBER')
    return json.loads(value,object_pairs_hook=pairs,parse_float=reject,parse_constant=reject)
def record(value, keys):
    if type(value) is not dict or set(value) != set(keys): raise ValueError('RS_TRANSPORT_FIELDS')
def text(value):
    if type(value) is not str or not value or any(0xD800 <= ord(c) <= 0xDFFF for c in value): raise ValueError('RS_TEXT_TRANSPORT')
    return value
def identity(value): return text(value).encode('utf-8').hex()
def unidentity(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]+',value) or len(value)%2: raise ValueError('RS_IDENTITY_TRANSPORT')
    result = bytes.fromhex(value).decode('utf-8')
    if identity(result) != value: raise ValueError('RS_IDENTITY_TRANSPORT')
    return result
def q(value,derived=False):
    if derived:
        if type(value) is not str or not re.fullmatch(r'(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?',value) or str(Fraction(value)) != value: raise ValueError('RS_DERIVED_EXACT_TRANSPORT')
        return Fraction(value)
    if type(value) is str and re.fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]+)?',value): return Fraction(value)
    record(value,{'numerator','denominator'})
    n,d=value['numerator'],value['denominator']
    if type(n) is not str or type(d) is not str or not re.fullmatch(r'(?:0|[1-9][0-9]*)',n) or not re.fullmatch(r'[1-9][0-9]*',d) or gcd(int(n),int(d)) != 1: raise ValueError('RS_EXACT_TRANSPORT')
    return Fraction(int(n),int(d))
def day(value):
    if type(value) is not str or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value): raise ValueError('RS_DATE_TRANSPORT')
    return date.fromisoformat(value)
def stamp(value):
    # The selected original policy regards -00:00 as known UTC and unknown
    # local offset. Preserve the original spelling in raw originals/state.
    text(value)
    return instant(value[:-6]+'Z' if value.endswith('-00:00') else value).canonical
def unknown(value,path=''):
    found=[]
    if type(value) is dict:
        for k,v in value.items():
            location=path+'.'+k if path else k
            if k in ('observed_at','cutoff') and type(v) is str and v.endswith('-00:00'): found.append(location)
            found.extend(unknown(v,location))
    elif type(value) is list:
        for i,v in enumerate(value): found.extend(unknown(v,path+'.'+str(i)))
    return found

def encode(value,schema,*,derived=False):
    if isinstance(schema,dict):
        record(value,schema)
        return {k:encode(value[k],v,derived=derived) for k,v in schema.items()}
    if isinstance(schema,list):
        if type(value) is not list: raise ValueError('RS_ARRAY_TRANSPORT')
        return [encode(v,schema[0],derived=derived) for v in value]
    if isinstance(schema,tuple): return {'none':True} if value is None else {'some':encode(value,schema[0],derived=derived)}
    if schema == s.ID or schema.startswith('Id<'): return identity(value)
    if schema == s.RAW: return raw(value)
    if schema == s.M: return money(q(value,derived))
    if schema == s.R: return number(q(value,derived))
    if schema == 'Instant': return stamp(value)
    if schema == 'Date': return day(value).isoformat()
    if schema == 'Period':
        record(value,{'start','end'}); return {k:day(v).isoformat() for k,v in value.items()}
    if schema in ('Int','Nat'):
        if type(value) is not int: raise ValueError('RS_INT_TRANSPORT')
        if schema == 'Nat' and value < 0: raise ValueError('RS_NAT_TRANSPORT')
        return str(value)
    if schema == 'Bool':
        if type(value) is not bool: raise ValueError('RS_BOOL_TRANSPORT')
        return value
    return text(value)

def decode(value,schema):
    if isinstance(schema,dict):
        record(value,schema); return {k:decode(value[k],v) for k,v in schema.items()}
    if isinstance(schema,list): return [decode(v,schema[0]) for v in value]
    if isinstance(schema,tuple): return None if set(value)=={'none'} else decode(value['some'],schema[0])
    if schema == s.ID or schema.startswith('Id<'): return unidentity(value)
    if schema == s.RAW: return loads(value)
    if schema == s.M: return str(exact(value['value'] if isinstance(value,dict) and 'value' in value else value))
    if schema == s.R: return str(exact(value))
    if schema in ('Int','Nat'): return int(value)
    return deepcopy(value)

def terms(value):
    result=deepcopy(value); record(result,set(s.TERMS)-{'approved_utc'})
    result['approved_utc']=result['approved_date']+'T00:00:00Z'
    for rule in result['release_schedule']:
        record(rule,{'id','offset_months','kind'}|({'fraction'} if 'fraction' in rule else set()))
        if 'fraction' in rule: q(rule['fraction'])
        rule.setdefault('fraction',None)
    return encode(result,s.TERMS)
def frame(value,position):
    record(value,FRAME_KEYS)
    result=deepcopy(value); result['id']=result.pop('case_id')
    result.update(as_of_ordinal=day(value['as_of']).toordinal(),end_ordinal=day(value['period']['end']).toordinal(),end_utc=value['period']['end']+'T00:00:00Z',raw=deepcopy(value),unknown=unknown(value,'frames.'+str(position)))
    for kind in ('receipts','elections','applications','authorities'):
        for row,original in zip(result[kind],value[kind]):
            if kind in ('receipts','elections','applications'): row['raw']=deepcopy(original)
            if kind in ('receipts','elections','applications'): row['event_utc']=row['event_date']+'T00:00:00Z'
            if kind in ('elections','authorities'): row['approved_utc']=row['approved_date']+'T00:00:00Z'
    return encode(result,s.FRAME)

def state_transport(value,context):
    if value.get('origin')=='genesis':
        record(value,{'origin','boundary','source_case_id','history'})
        if value['history']: raise ValueError('RS_GENESIS_HISTORY')
        return {'transport_profile':TRANSPORT,'context':context_raw(context),'origin':'genesis','boundary':encode(value['boundary'],'Date'),'source_case_id':identity(value['source_case_id']),'detail':{'none':True}}
    keys={'schema_version','origin','boundary','source_case_id','scope','policy','terms','registry_evidence','history','vintages','cumulative','fee_consumption_keys','closing_reserve'}|{'consumed_'+k for k in s.SEEN}
    record(value,keys)
    if value['schema_version']!='reserve-stages-state/1': raise ValueError('RS_STATE_SCHEMA')
    state_context={'schema_version':'reserve-stages-neutral/1',**{k:deepcopy(value[k]) for k in ('scope','policy','terms','registry_evidence')}}
    book={k:deepcopy(value[k]) for k in ('vintages','cumulative','fee_consumption_keys','history')}
    book.update({k:deepcopy(value['consumed_'+k]) for k in s.SEEN})
    book['unknown']=unknown({'terms':value['terms'],'registry_evidence':value['registry_evidence'],'frames':[h['facts'] for h in value['history']]})
    physical=encode(book,s.BOOK,derived=True)
    # Closing balance is a projection of computed vintage availability; require
    # it through a separately retained field rather than solving it in Python.
    if value['closing_reserve'] != value['history'][-1]['result']['closing_reserve']: raise ValueError('RS_STATE_CLOSING_TRANSPORT')
    return {'transport_profile':TRANSPORT,'context':context_raw(state_context),'origin':value['origin'],'boundary':encode(value['boundary'],'Date'),'source_case_id':identity(value['source_case_id']),'detail':{'some':physical}}

def neutral_result(value): return decode(value,s.RESULT)
def neutral_state(value):
    record(value,s.STATE)
    if value['transport_profile']!=TRANSPORT: raise ValueError('RS_STATE_TRANSPORT')
    context=loads(value['context'])
    result={'origin':value['origin'],'boundary':value['boundary'],'source_case_id':unidentity(value['source_case_id']),'history':[]}
    if value['origin']!='genesis':
        book=decode(value['detail']['some'],s.BOOK)
        result.update(schema_version='reserve-stages-state/1',**{k:deepcopy(context[k]) for k in ('scope','policy','terms','registry_evidence')},**{k:book[k] for k in ('history','vintages','cumulative','fee_consumption_keys')},**{'consumed_'+k:book[k] for k in s.SEEN},closing_reserve=book['history'][-1]['result']['closing_reserve'])
    if state_transport(result,context)!=value: raise ValueError('RS_RESTORED_STATE_MISMATCH')
    return result

def register_reserve_stages():
    reference=_descriptor('reserve-stages','reserve-stages.spl','policy.md',{'policy':'parameter','cutoff':'parameter','comparison':'result','reconciliation':'reconciliation'},folder=FOLDER,capabilities=('spl.calendar-months/1',),state=[{'opening':'history','closing':'history','purpose':PURPOSE,'unit':'structured','key_fields':['agreement_id','participant_id','pool_id','asset_id','purpose'],'movement_kinds':['transition'],'history_required':False}])
    path=ROOT/reference['locator']; descriptor=read_json(path); descriptor['id']='synthetic:reserve-stages'; descriptor['policy'].update(id=POLICY,discriminating_cases=['35-vs36-once-fee','45-45-10-completed','cap32-vs33','V1-no-V2-borrow','actual-addition-original-quota'])
    for field in ('agreement_id','participant_id','pool_id'):
        descriptor['constraints'].append({'kind':'member_of' if field=='participant_id' else 'equals','path':'inputs.fact_scope.'+field,'fields':[],'target':'scope.participant_ids' if field=='participant_id' else 'scope.'+field,'value':''})
    descriptor['constraints'].append({'kind':'equals','path':'inputs.fact_scope.asset_id','fields':[],'target':'inputs.project','value':''})
    write_json(path,descriptor)
    return {'id':descriptor['id'],'revision':'1',**_pin(path)}

def reserve_stages_package(fixture,*,reference=None,state_cells=None,mode='final'):
    data=deepcopy(fixture); record(data,CONTEXT_KEYS|FRAME_KEYS|{'opening_state'}|({'prior_result'} if 'prior_result' in data else set()))
    if data['schema_version']!='reserve-stages-neutral/1': raise ValueError('RS_SCHEMA_TRANSPORT')
    context={k:deepcopy(data[k]) for k in CONTEXT_KEYS}; encode(data['scope'],s.SCOPE); encode(data['policy'],s.POLICY)
    reference=reference or register_reserve_stages()
    opening=state_transport(data['opening_state'],context)
    sources=[h['facts'] for h in data['opening_state']['history']]+[{k:data[k] for k in FRAME_KEYS}]
    work=encode(data['scope'],s.SCOPE); execution={k:work[k] for k in ('agreement_id','participant_id','pool_id','asset_id')}
    inputs={'scope':{k:execution[k] for k in ('agreement_id','participant_id','pool_id')}|{'period':deepcopy(data['period'])},'project':work['asset_id'],'fact_scope':work,'source_context':context_raw(context),'terms':terms(data['terms']),'registry_evidence':encode(data['registry_evidence'],s.lst(s.EVIDENCE)),'frames':[frame(f,i) for i,f in enumerate(sources)],'initial_unknown':unknown({'terms':data['terms'],'registry_evidence':data['registry_evidence']}),'supplied_opening':opening,'predecessor':{'none':True}}
    cell={'opening_port':'history','state_key':canonical({**execution,'purpose':PURPOSE}),'purpose':PURPOSE,'unit':'structured','scope':execution,'boundary':data['period']['start'],'quantity':deepcopy(opening),'provenance_ref':'original-synthetic-reserve-history','scenario_id':'SYNTHETIC-RESERVE-STAGES'}
    if 'prior_result' in data:
        prior=data['prior_result']; record(prior,{'source_case_id','period','result_ref','closing_state'})
        if type(prior['result_ref']) is not str or not re.fullmatch('result@sha256:[0-9a-f]{64}',prior['result_ref']): raise ValueError('RS_CANONICAL_PREDECESSOR_REQUIRED')
        inputs['predecessor']={'some':{'source_case_id':identity(prior['source_case_id']),'period':deepcopy(prior['period']),'result_ref':identity(prior['result_ref']),'closing_state':state_transport(prior['closing_state'],context)}}
        cell['prior_result_ref']=prior['result_ref']
    cells=deepcopy(state_cells) if state_cells is not None else [cell]
    if cells != [cell]: raise ValueError('RS_CANONICAL_CELL_MISMATCH')
    package={'profile':'spl-module/1','module_ref':reference,'manifest':{'run_id':'reserve-stages-run','scenario_id':'SYNTHETIC-RESERVE-STAGES','mode':mode,'period':deepcopy(data['period']),'cutoff':data['cutoff'],'compiler_build':'unbound','runtime_build':'unbound','module_closure':[],'resource_limits':{'max_input_rows':100000,'lean_timeout_seconds':180}},'scope':{'agreement_id':work['agreement_id'],'participant_ids':[work['participant_id']],'pool_id':work['pool_id'],'asset_ids':[work['asset_id']],'purpose':PURPOSE},'inputs':inputs,'parameters':{'policy':deepcopy(data['policy']),'cutoff':stamp(data['cutoff'])},'evidence':{},'state_cells':cells,'decisions':[{'decision_id':name,'policy_id':POLICY,'policy_revision':'1','status':'proposed','evidence_ref':'selected-synthetic-reserve-stage-policy'} for entry in resolve_module(reference,ROOT).closure for name in entry['descriptor']['policy']['decision_ids']]}
    # Manifest cutoff is the runtime's known-UTC transport; the complete raw
    # original spelling remains in frame.raw and source context.
    package['manifest']['cutoff']=stamp(data['cutoff'])
    return bind_module_package(package,ROOT)

def validate_prepared_package(package):
    context=loads(package['inputs']['source_context']); record(context,CONTEXT_KEYS)
    current=loads(package['inputs']['frames'][-1]['raw'])
    data={**context,**current,'opening_state':neutral_state(package['inputs']['supplied_opening'])}
    prior=package['inputs']['predecessor']
    if 'some' in prior:
        p=prior['some']; data['prior_result']={'source_case_id':unidentity(p['source_case_id']),'period':deepcopy(p['period']),'result_ref':unidentity(p['result_ref']),'closing_state':neutral_state(p['closing_state'])}
    expected=reserve_stages_package(data,reference=package['module_ref'],mode=package['manifest']['mode'])
    for k in ('profile','scope','inputs','parameters','evidence','state_cells','decisions'):
        if package[k]!=expected[k]: raise ValueError('RS_PREPARED_PACKAGE_MISMATCH')
    for k in ('period','cutoff','scenario_id','resource_limits'):
        if package['manifest'][k]!=expected['manifest'][k]: raise ValueError('RS_PREPARED_PACKAGE_MISMATCH')

def run_reserve_stages_package(package,registry_root=None,*,backend='compare',artifact_dir=None,audit_profile='array-v1'):
    from spl_compiler.artifacts import ArtifactPublication
    from spl_compiler.audited_artifacts import AuditedPublication, unavailable_trace
    from spl_compiler.compact_execution import require_profile
    def invalidate():
        if artifact_dir is not None: (AuditedPublication if audit_profile=='compact-v2' else ArtifactPublication)(artifact_dir)
    try: require_profile(audit_profile,backend,artifact_dir)
    except BaseException: invalidate(); raise
    snapshot=None
    try:
        snapshot=deepcopy(package); validate_prepared_package(snapshot)
    except (IndexError,KeyError,TypeError,ValueError):
        result={'status':'blocked','results':{},'statements':[],'detail':[],'closing_state':[],'trace':unavailable_trace() if audit_profile=='compact-v2' else [],'reconciliation':{},'policy_review':{},'manifest':snapshot.get('manifest',{}) if isinstance(snapshot,dict) else {},'issuance_status':'unissued','payment_evidence_status':'not_assessed','diagnostics':[{'code':'RS_PREPARED_PACKAGE_MISMATCH','message':'Bindings differ from complete retained original context, frames or state','pointer':'inputs.source_context'}]}
        if artifact_dir is not None:
            return (AuditedPublication if audit_profile=='compact-v2' else ArtifactPublication)(artifact_dir).finish(result,{'results.json':'results','statement.json':'statements','detail.json':'detail','trace.json':'trace','closing-state.json':'closing_state','reconciliation.json':'reconciliation','diagnostics.json':'diagnostics','policy-review.json':'policy_review'})
        return result
    except BaseException: invalidate(); raise
    return run_module_package(snapshot,registry_root or ROOT,backend=backend,artifact_dir=artifact_dir,audit_profile=audit_profile)

if __name__=='__main__':
    (FOLDER/'reserve-stages.spl').write_text(s.generate(),encoding='utf-8',newline='\n')
    ref=register_reserve_stages()
    pack=loads((FOLDER/'neutral.json').read_text(encoding='utf-8'))
    for name,case in pack['scenarios'].items():
        data={'schema_version':'reserve-stages-neutral/1',**case['context'],**case['frames'][0],'opening_state':{'origin':'genesis','boundary':case['frames'][0]['period']['start'],'source_case_id':'genesis','history':[]}}
        package=reserve_stages_package(data,reference=ref)
        package['manifest'].update(compiler_build='unbound',runtime_build='unbound',module_closure=[])
        write_json(FOLDER/(name.replace('_','-')+'-canonical-package.json'),package)
