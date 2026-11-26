import sys
sys.path.insert(0,'C:/spl-c09s/.lake')
from c9 import *
from unittest.mock import patch

folder=WORK/'life'
package=m.reserve_stages_package(view(fixture('basis_reserve_stage')),reference=REF)
reports=[]
for reason in ('null','cancel','profile'):
    result=m.run_reserve_stages_package(package,backend='compare',artifact_dir=folder,audit_profile='compact-v2')
    assert load_completed_audited_result(folder)==result
    expected=exact_json(reserve_stages(view(fixture('basis_reserve_stage'))))
    assert m.neutral_result(result['results']['comparison'])=={k:v for k,v in expected.items() if k!='closing_state'}
    assert m.neutral_state(result['closing_state'][0]['quantity'])==expected['closing_state']
    before=read_json(folder/'completion.json')
    write_json(folder/(reason+'-before-marker.json'),before)
    if reason=='null':
        bad=deepcopy(package); context=m.loads(bad['inputs']['source_context']); context['terms']['release_schedule'][0]['fraction']=None; bad['inputs']['source_context']=m.context_raw(context)
        failure=m.run_reserve_stages_package(bad,backend='compare',artifact_dir=folder,audit_profile='compact-v2')
        assert load_completed_audited_result(folder)==failure
        assert failure['status']=='blocked' and not failure['results'] and not failure['closing_state']
        assert failure['diagnostics'][0]['code']=='RS_PREPARED_PACKAGE_MISMATCH'
        report={'reason':reason,'source_reached':False,'status':'completed_blocked','diagnostics':failure['diagnostics']}
    elif reason=='cancel':
        with patch.object(m,'validate_prepared_package',side_effect=KeyboardInterrupt):
            try: m.run_reserve_stages_package(package,backend='compare',artifact_dir=folder,audit_profile='compact-v2'); raise AssertionError('Expected cancellation')
            except KeyboardInterrupt: pass
        try: load_completed_audited_result(folder); raise AssertionError('Stale success reused')
        except Exception as error: report={'reason':reason,'status':'invalidated','loader_error':str(error)}
    else:
        try: m.run_reserve_stages_package(package,backend='compare',artifact_dir=folder,audit_profile='bad-profile'); raise AssertionError('Expected profile rejection')
        except ValueError: pass
        try: load_completed_audited_result(folder); raise AssertionError('Stale success reused')
        except Exception as error: report={'reason':reason,'status':'invalidated','loader_error':str(error)}
    after=json.loads((folder/'completion.json').read_text())
    assert before['invocation_id']!=after['invocation_id']
    report.update(before=before['invocation_id'],after=after['invocation_id'],builder=file_digest(m.FOLDER/'build_modules.py'),source=file_digest(m.FOLDER/'reserve-stages.spl'))
    reports.append(report); print('LIFECYCLE_PASS',reason,flush=True)
write_json(WORK/'lifecycle.json',{'complete':True,'reports':reports})
