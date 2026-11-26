import sys
sys.path.insert(0,'C:/spl-c09s/.lake')
from c9v import *

reports=[]
mapping=read_json(WORK/'verification.json')['mapping']
def original_at(name,position):
    number=next(k for k,v in mapping.items() if v['scenario']==name and v['position']==position and v['mode']=='final')
    return m.loads((WORK/f'{int(number):02d}'/'original.json').read_text())

case=fixture(); add_application(case,1,'second-V1-application','V1','8','2026-04-01','15',1)
data=original_at('basis_reserve_vintages',1); data.update(deepcopy(case['frames'][1]))
try: reserve_stages(data); raise AssertionError('Expected no-borrow rejection')
except ReserveStageOracleError as error: oracle_code=str(error)
reports.append({**invalid('second8',m.reserve_stages_package(data,reference=REF)),'oracle_code':oracle_code})

case=fixture(); add_application(case,2,'after-liquidation','V1','1','2026-07-01','1',0)
data=original_at('basis_reserve_vintages',2); data.update(deepcopy(case['frames'][2]))
try: reserve_stages(data); raise AssertionError('Expected unsupported after-liquidation rejection')
except ReserveStageOracleError as error: oracle_code=str(error)
reports.append({**invalid('after',m.reserve_stages_package(data,reference=REF)),'oracle_code':oracle_code})

previous=load_completed_audited_result(WORK/'v/fourth/3')
state=m.neutral_state(previous['closing_state'][0]['quantity'])
frame=m.loads((WORK/'v/fourth/3/original.json').read_text())
frame.update(case_id='fifth-outside-profile',period={'start':'2026-10-01','end':'2027-01-01'},as_of='2026-12-31',cutoff='2027-01-03T00:00:00Z')
frame['population'].update(id='population-fifth',period=deepcopy(frame['period']),observed_at='2027-01-02T12:00:00Z',source_ref='source-fifth',evidence_ref='evidence-fifth')
frame['evidence'][0].update(id='evidence-fifth',observed_at='2027-01-02T12:00:00Z',source_ref='evidence-source-fifth')
frame['opening_state']=state
frame['prior_result']={'source_case_id':m.unidentity(previous['closing_state'][0]['quantity']['source_case_id']),'period':previous['results']['comparison']['period'],'result_ref':previous['closing_state'][0]['prior_result_ref'],'closing_state':deepcopy(state)}
try: reserve_stages(frame); raise AssertionError('Expected finite bound rejection')
except ReserveStageOracleError as error: oracle_code=str(error)
reports.append({**invalid('fifth',m.reserve_stages_package(frame,reference=REF)),'oracle_code':oracle_code})
write_json(WORK/'more-negatives.json',{'complete':True,'reports':reports})
