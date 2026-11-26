import sys
sys.path.insert(0,'C:/spl-c09s/.lake')
import c9
from c9 import *
from oracles.reserve_stages import ReserveStageOracleError

def run_variant(name,case,checkpoints):
    previous=None; cells=None; reports=[]
    for position in range(checkpoints):
        data=view(case,position,previous)
        if previous is not None: data['prior_result']['result_ref']=cells[0]['prior_result_ref']
        package=m.reserve_stages_package(data,reference=REF,state_cells=cells)
        folder=WORK/'v'/name/str(position)
        result,report=completed(package,data,folder)
        reports.append(report)
        previous={**m.neutral_result(result['results']['comparison']),'closing_state':m.neutral_state(result['closing_state'][0]['quantity'])}
        cells=json.loads(json.dumps(result['closing_state']))
        for cell in cells: cell.pop('movement',None)
        print('VARIANT_PASS',name,position,flush=True)
    return reports

def invalid(name,package,*,wrapper=False):
    folder=WORK/'i'/name; folder.mkdir(parents=True,exist_ok=False)
    write_json(folder/'package.json',package)
    runner=m.run_reserve_stages_package if wrapper else lambda p,**kw:run_module_package(p,ROOT,**kw)
    result=runner(package,backend='compare',artifact_dir=folder,audit_profile='compact-v2')
    actual=load_completed_audited_result(folder)
    assert actual==result
    assert result['status']=='blocked' and not result['results'] and not result['closing_state'],result['diagnostics']
    code=result['diagnostics'][0]['code']
    reached='bindings' in result['trace']
    # source guard controls require native sidecars/pins, custody controls
    # deliberately fail in the public wrapper before native execution.
    if wrapper: assert code=='RS_PREPARED_PACKAGE_MISMATCH' and not reached
    else:
        assert code.startswith(('RS_','CALENDAR_')),result['diagnostics']
        assert reached,result
        native_work=folder/'.runs'/read_json(folder/'completion.json')['invocation_id']
        python_run(package,folder,native_work)
    report={'name':name,'code':code,'native_source_reached':reached,'wrapper':wrapper,'status':result['status'],'trace':result['trace']}
    print('INVALID_PASS',name,code,reached,flush=True)
    return report

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'valid'
    reports=[]
    if mode=='valid':
        for stage in ('basis_reserve','producer_holdback'):
            for cap in ('32','33'):
                case=fixture(stage+'_vintages'); case['context']['terms']['retained_cap']=cap
                gross='105' if stage=='basis_reserve' else '220'
                case['frames'][1]['receipts'][0]['gross']=gross; case['frames'][1]['population']['gross_total']=gross
                reports.extend(run_variant(('b' if stage=='basis_reserve' else 'h')+cap,case,2))
        case=fixture(); case['context']['terms']['retained_cap']='20'; reports.extend(run_variant('daycap',case,2))
        case=fixture('basis_reserve_tranches'); case['context']['terms']['retained_cap']='12'; case['frames'][0]['receipts'][0]['gross']='100'; case['frames'][0]['population']['gross_total']='100'; reports.extend(run_variant('actual',case,2))
        case=fixture('basis_reserve_tranches'); case['frames'][0]['applications'][0]['amount']='11'; case['frames'][0]['population']['application_total']='11'; remove_applications(case['frames'][1]); reports.extend(run_variant('unused',case,2))
        case=fixture('basis_reserve_tranches'); remove_applications(case['frames'][0]); remove_applications(case['frames'][1])
        case['frames'][0]['receipts'][0].update(event_date='2026-01-31',observed_at='2026-01-31T12:00:00Z'); case['frames'][0]['elections'][0].update(event_date='2026-01-31',approved_date='2026-01-31',observed_at='2026-01-31T12:00:00Z'); reports.extend(run_variant('month',case,2))
        for stage in ('basis_reserve','producer_holdback'):
            case=fixture(stage+'_stage'); case['context']['terms']['fixed_fee']='0.1'; gross={'numerator':'1','denominator':'3'}; case['frames'][0]['receipts'][0]['gross']=gross; case['frames'][0]['population']['gross_total']=deepcopy(gross); reports.extend(run_variant('fb' if stage=='basis_reserve' else 'fh',case,2))
        case=fixture('basis_reserve_stage')
        for row in (case['context']['terms'],*case['context']['registry_evidence'],case['frames'][0],case['frames'][0]['receipts'][0],case['frames'][0]['elections'][0]):
            key='cutoff' if 'cutoff' in row else 'observed_at'; row[key]=row[key][:-1]+'-00:00'
        reports.extend(run_variant('unknown',case,1))
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
        write_json(WORK/'variants.json',{'complete':True,'reports':reports,'checkpoints':len(reports)})
    else:
        base=read_json(WORK/'00/package.json')
        for name,change in ([] if mode=='rest' else [('fee',lambda d:d['terms'].__setitem__('fixed_fee','1000')),('election',lambda d:d['elections'][0].__setitem__('approved',False)),('evidence',lambda d:d['evidence'][0].__setitem__('approved',False)),('measure',lambda d:d['terms'].__setitem__('reserve_measure','producer_entitlement_USD')),('population',lambda d:d['population'].__setitem__('complete',False))]):
            data=view(fixture('basis_reserve_stage')); change(data)
            try: reserve_stages(data); raise AssertionError('Oracle admitted negative original control')
            except ReserveStageOracleError: pass
            p=m.reserve_stages_package(data,reference=REF); reports.append(invalid(name,p))
        # A genuine unused evidence row is still admitted by native source.
        if mode!='rest':
            data=view(fixture('basis_reserve_stage')); e=deepcopy(data['evidence'][0]); e.update(id='unused-bad',approved=False); data['evidence'].append(e); p=m.reserve_stages_package(data,reference=REF); reports.append(invalid('unused',p))
        # Current V1 overdraw is checked against its own balance, despite V2.
        entries=read_json(WORK/'verification.json')['mapping']
        number=next(k for k,v in entries.items() if v['scenario']=='basis_reserve_vintages' and v['position']==1 and v['mode']=='final')
        data=m.loads((WORK/f'{int(number):02d}'/'original.json').read_text()); data['applications'][0]['amount']='13'; data['population']['application_total']='13'; p=m.reserve_stages_package(data,reference=REF); reports.append(invalid('overdraw',p))
        # Equal-Date equal-sequence original receipts do not use physical order.
        data=view(fixture('basis_reserve_stage')); r=deepcopy(data['receipts'][0]); r.update(id='tie-receipt',original_ref='tie-original'); data['receipts'].append(r); e=deepcopy(data['elections'][0]); e.update(id='tie-election',receipt_id=r['id'],vintage_id='Vtie'); data['elections'].append(e); data['population']['receipt_ids'].append(r['id']); data['population']['election_ids'].append(e['id']); data['population']['gross_total']='200'; p=m.reserve_stages_package(data,reference=REF); reports.append(invalid('tie',p))
        # Calendar reject is a financial source operation on original Date.
        data=m.loads((WORK/'v/month/0/original.json').read_text()); data['terms']['calendar_mode']='reject_invalid_day'; p=m.reserve_stages_package(data,reference=REF); reports.append(invalid('month',p))
        # Bad original/typed custody is rejected by public wrapper separately.
        p=deepcopy(base); p['inputs']['terms']['fixed_fee']={'value':'9','currency':'USD'}; reports.append(invalid('custody',p,wrapper=True))
        write_json(WORK/'invalids.json',{'complete':True,'reports':reports})
