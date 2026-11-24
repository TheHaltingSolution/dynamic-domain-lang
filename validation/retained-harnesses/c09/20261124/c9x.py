import sys
sys.path.insert(0,'C:/spl-c09s/.lake')
from c9v import *

reports=[]
case=fixture('basis_reserve_vintages')
identity_fields={'id','agreement_id','participant_id','pool_id','asset_id','case_id','receipt_id','vintage_id','authority_id','application_id','original_ref','source_ref','evidence_ref','version'}
identity_arrays={'receipt_ids','election_ids','application_ids','authority_ids'}
def unicode_original(value,path='',field=''):
    if path=='context.policy': return deepcopy(value)
    if isinstance(value,dict): return {k:unicode_original(v,path+'.'+k if path else k,k) for k,v in value.items()}
    if isinstance(value,list): return [unicode_original(v,path+'.'+str(i),field) for i,v in enumerate(value)]
    return '雪|e\u0301#\x00|'+value if field in identity_fields|identity_arrays else value
case=unicode_original(case)
case['context']['terms'].update(fixed_fee='10.0000',reserve_rate='0.200000',participation_share='0.500000')
case['frames'][0]['receipts'][0]['gross']='60.000000'; case['frames'][0]['population']['gross_total']='60.000000'
for row in (case['frames'][0]['receipts'][0],case['frames'][0]['elections'][0]): row['observed_at']='2026-01-01t13:00:00.000000000001+01:00'
reports.extend(run_variant('unicode',case,3))
case=fixture('basis_reserve_tranches'); fourth=deepcopy(case['frames'][-1]); fourth.update(case_id='fourth-empty',period={'start':'2026-07-01','end':'2026-10-01'},as_of='2026-09-30',cutoff='2026-10-03T00:00:00Z')
fourth['population'].update(id='population-fourth',period=deepcopy(fourth['period']),observed_at='2026-10-02T12:00:00Z',source_ref='source-fourth',evidence_ref='evidence-fourth')
fourth['evidence'][0].update(id='evidence-fourth',observed_at='2026-10-02T12:00:00Z',source_ref='evidence-source-fourth')
case['frames'].append(fourth); reports.extend(run_variant('fourth',case,4))
write_json(WORK/'unicode-fourth.json',{'complete':True,'reports':reports,'checkpoints':len(reports)})
print('UNICODE_AND_FOURTH_PASS',flush=True)
