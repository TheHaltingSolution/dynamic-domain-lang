import sys
sys.path.insert(0,'C:/spl-c09s/.lake')
from c9b import *
from spl_compiler.modules import bind_module_package
from spl_compiler.compact_execution import WORKER, _stage

roots=[WORK/'00',WORK/'11']
results=[load_completed_audited_result(path) for path in roots]
cells=[json.loads(json.dumps(result['closing_state'])) for result in results]
for group in cells:
    for cell in group:cell.pop('movement',None)
assert cells[0][0]['scope']==cells[1][0]['scope']
assert cells[0][0]['state_key']!=cells[1][0]['state_key']
assert {x[0]['purpose'] for x in cells}==set(m.PURPOSES.values())
for i,group in enumerate(cells):write_json(WORK/'namespace'/('cells-'+str(i)+'.json'),group)
packages=[read_json(WORK/'01/package.json'),read_json(WORK/'12/package.json')]
reports=[]
def blocked(name,package,expected,*,generic=False):
    folder=WORK/'namespace'/name
    runner=(lambda p,**kw:run_module_package(p,ROOT,**kw)) if generic else m.run_reserve_stages_package
    result=runner(package,backend='compare',artifact_dir=folder,audit_profile='compact-v2')
    assert load_completed_audited_result(folder)==result
    assert result['status']=='blocked' and not result['results'] and not result['closing_state']
    assert result['diagnostics'][0]['code']==expected,result['diagnostics']
    assert result['trace']['status']=='unavailable'
    output=_stage([sys.executable,WORKER,'load',folder],folder/'retained-reader')
    assert metadata(output)['status']=='blocked'
    reports.append({'name':name,'code':expected,'boundary':'generic intrinsic/descriptor admission' if generic else 'public prepared custody','native_source_reached':False,'path':str(folder)})
    print('NAMESPACE_BLOCK_PASS',name,expected,flush=True)
for i in (0,1):
    own,other=packages[i],packages[1-i]
    swapped=deepcopy(own);swapped['state_cells']=deepcopy(cells[1-i]);blocked('cells-'+str(i),swapped,'RS_PREPARED_PACKAGE_MISMATCH')
    swapped=deepcopy(own);swapped['module_ref']=deepcopy(other['module_ref']);blocked('public-ref-'+str(i),swapped,'RS_PREPARED_PACKAGE_MISMATCH')
    swapped['decisions']=deepcopy(other['decisions']);swapped=bind_module_package(swapped,ROOT)
    blocked('generic-state-'+str(i),swapped,'MODULE_STATE_PURPOSE',generic=True)
    swapped['state_cells'][0]['purpose']=other['state_cells'][0]['purpose'];swapped['state_cells'][0]['state_key']=other['state_cells'][0]['state_key']
    blocked('descriptor-'+str(i),swapped,'MODULE_SCOPE_MISMATCH',generic=True)
bad=deepcopy(packages[0]);context=m.loads(bad['inputs']['source_context']);context['terms']['release_schedule'][0]['fraction']=None;bad['inputs']['source_context']=m.context_raw(context)
blocked('null-original',bad,'RS_PREPARED_PACKAGE_MISMATCH')
# Explicitly retain bounded reader reports for every newly qualified valid run.
for report in json.loads((WORK/'verification.json').read_text(encoding='utf-8'))['reports']:
    path=Path(report['path']);output=_stage([sys.executable,WORKER,'load',path],path/'retained-reader');result=metadata(output)
    assert result['status'] in ('calculated','provisional')
verify()
write_json(WORK/'namespace.json',{'complete':True,'different_keys_same_scope':True,'actual_serialized_cells':cells,'registration_references':REF,'reports':reports,'valid_readers':22,'blocked_readers':len(reports),'source_unchanged':file_digest(m.FOLDER/'reserve-stages.spl')})
print('ALL_NAMESPACE_CONTROLS_PASS',flush=True)
