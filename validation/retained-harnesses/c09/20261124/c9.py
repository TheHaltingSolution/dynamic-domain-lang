from pathlib import Path
import sys
ROOT=Path('C:/spl-c09s')
sys.path[:]=[str(ROOT)]+[p for p in sys.path if 'dynamic-domain-lang' not in p and not p.replace('\\','/').startswith('C:/spl-')]
from importlib import import_module
import json
from copy import deepcopy
from spl_compiler.codecs import read_json,write_json,file_digest,canonical
from spl_compiler.modules import resolve_module,validate_module_package,run_module_package
from spl_compiler.compact_execution import _compiler_inputs,_verify_pins,_stage,metadata,checked_head
from spl_compiler.emitter import emit_module
from spl_compiler.audited_artifacts import load_completed_audited_result
from oracles.reserve_stages import reserve_stages,exact_json
from Tests.test_reserve_stage_oracle import fixture,view,add_application,remove_applications
m=import_module('cases.reserve-stages.build_modules')
assert m.ROOT==ROOT
for name,module in list(sys.modules.items()):
    if name.startswith(('spl_compiler','cases.','oracles.','Tests.')) and getattr(module,'__file__',None):
        assert Path(module.__file__).resolve().is_relative_to(ROOT), (name,module.__file__)
WORK=Path('C:/c9n_a')
PYWORK=WORK/'py'
REF=m.register_reserve_stages()
PINS={str(p):file_digest(p) for folder in ('cases/reserve-stages','spl_compiler','SPL') for p in (ROOT/folder).glob('*') if p.is_file()}
PINS.update({str(ROOT/p):file_digest(ROOT/p) for p in ('oracles/reserve_stages.py','Tests/test_reserve_stage_oracle.py','Tests/test_reserve_stage_modules.py','docs/spl/reserve-stage-design.md','lean-toolchain','lakefile.toml')})
write_json(WORK/'freeze.json',{'root':str(ROOT),'pins':PINS,'origins':{name:module.__file__ for name,module in sys.modules.items() if name.startswith(('spl_compiler','cases.','oracles.','Tests.')) and getattr(module,'__file__',None)},'budgets':{'compiler_bytes':1073741824,'compiler_seconds':180,'runtime_reference_reader_bytes':268435456,'runtime_reference_reader_seconds':60,'wire_result_bytes':67108864,'logical_bytes':1073741824,'nodes':100000}})

def verify():
    for path,pin in PINS.items(): assert file_digest(path)==pin,path

def literal_type(t):
    if t['name']=='Record': return '(.record ['+', '.join('('+json.dumps(k)+', '+literal_type(v)+')' for k,v in t['fields'])+'])'
    return '(.named '+json.dumps(t['name'])+' ['+', '.join(literal_type(a) for a in t.get('args',[]))+'])'

def python_build(package):
    if (PYWORK/'pins.json').exists(): return
    PYWORK.mkdir(exist_ok=True)
    checked,_,_=validate_module_package(package,resolve_module(package['module_ref'],ROOT))
    source=emit_module(checked)
    groups=[]
    for kind in ('input','opening'):
        groups.append('['+', '.join('('+json.dumps(d['name'])+', '+literal_type(d['type'])+')' for d in checked.schedule['declarations'] if d['kind']==kind)+']')
    source='import SPL.Bindings\n'+source+'\ndef main (args : List String) : IO UInt32 :=\n  SPL.Bindings.runMain '+groups[0]+' '+groups[1]+' GeneratedSPL.settle args\n'
    lean=PYWORK/'Candidate.lean'; c=PYWORK/'Candidate.c'; obj=PYWORK/'Candidate.o'; exe=PYWORK/'Candidate.exe'; rsp=PYWORK/'link.rsp'
    lean.write_text(source,encoding='utf-8',newline='\n')
    toolbin,flags,libraries,pins=_compiler_inputs()
    rsp.write_text('\n'.join(json.dumps(a) for a in [str(obj),*libraries]),encoding='utf-8',newline='\n')
    stages=[('cgen',[toolbin/'lean.exe','-DwarningAsError=true','-R',PYWORK,'-c',c,lean]),('obj',[toolbin/'clang.exe','-c','-o',obj,c,*flags]),('link',[toolbin/'clang.exe','-o',exe,'@'+str(rsp)])]
    for name,cmd in stages: _stage(cmd,PYWORK/name,compiler=True)
    _verify_pins(pins); verify()
    write_json(PYWORK/'pins.json',{'generator':'independent Python emit_module(checked), original typed transport driver','source':file_digest(lean),'c':file_digest(c),'object':file_digest(obj),'exe':file_digest(exe),'compiler':pins})
    print('PYTHON_TARGET_BUILT',flush=True)

def python_run(package,folder,native_work):
    checked,_,_=validate_module_package(package,resolve_module(package['module_ref'],ROOT))
    output=folder/'py-run'/'stdout.bin'
    if not (folder/'python-comparison.json').is_file(): output=_stage([PYWORK/'Candidate.exe',native_work/'bindings.json'],folder/'py-run')
    py=checked_head(metadata(output),checked)
    native=checked_head(metadata(native_work/'target-process/stdout.bin'),checked)
    assert canonical(py)==canonical(native), 'Python-native head mismatch'
    write_json(folder/'python-comparison.json',{'full_status_emissions_closing_diagnostics_equal':True,'source':file_digest(PYWORK/'Candidate.lean'),'exe':file_digest(PYWORK/'Candidate.exe'),'output':file_digest(output)})

def completed(package,data,folder,*,reuse=False):
    verify(); folder.mkdir(parents=True,exist_ok=True)
    write_json(folder/'package.json',package); write_json(folder/'original.json',data)
    if not reuse: m.run_reserve_stages_package(package,backend='compare',artifact_dir=folder,audit_profile='compact-v2')
    result=load_completed_audited_result(folder)
    assert result['status'] in ('calculated','provisional'),result['diagnostics']
    expected=exact_json(reserve_stages(data))
    actual=m.neutral_result(result['results']['comparison'])
    assert actual=={k:v for k,v in expected.items() if k!='closing_state'}
    if result['status']=='calculated': assert m.neutral_state(result['closing_state'][0]['quantity'])==expected['closing_state']
    else: assert not result['closing_state']
    write_json(folder/'oracle.json',expected); write_json(folder/'normalized.json',{'result':actual,'closing_state':None if not result['closing_state'] else m.neutral_state(result['closing_state'][0]['quantity'])})
    marker=read_json(folder/'completion.json'); native_work=folder/'.runs'/marker['invocation_id']
    python_build(package); python_run(package,folder,native_work)
    verify()
    return result,{'path':str(folder),'status':result['status'],'source_case_id':data['case_id'],'full_oracle_result_state_equal':True,'python_native_equal':True,'trace':result['trace'],'result_bytes':(native_work/'result.json').stat().st_size,'native_work':str(native_work)}

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'baseline'
    if mode=='baseline':
        data=view(fixture('basis_reserve_stage')); package=m.reserve_stages_package(data,reference=REF)
        _,report=completed(package,data,WORK/'00',reuse=True)
        write_json(WORK/'python-baseline.json',report)
        print('BASELINE_ALL_BACKENDS_PASS',flush=True)
    else:
        reports=[]; mapping={}; serial=0
        pack=m.loads((m.FOLDER/'neutral.json').read_text())
        for name,case in pack['scenarios'].items():
            previous=None; cells=None
            for position in range(len(case['frames'])):
                data=view(case,position,previous)
                if previous is not None: data['prior_result']['result_ref']=cells[0]['prior_result_ref']
                package=m.reserve_stages_package(data,reference=REF,state_cells=cells)
                folder=WORK/f'{serial:02d}'
                reuse=serial==0
                result,report=completed(package,data,folder,reuse=reuse)
                reports.append(report); mapping[str(serial)]={'scenario':name,'position':position,'mode':'final'}
                print('PASS',serial,name,position,report['trace']['node_count'],report['trace']['wire_bytes'],flush=True)
                serial+=1
                previous={**m.neutral_result(result['results']['comparison']),'closing_state':m.neutral_state(result['closing_state'][0]['quantity'])}
                cells=json.loads(json.dumps(result['closing_state']))
                for cell in cells: cell.pop('movement',None)
                write_json(WORK/'verification.json',{'reports':reports,'mapping':mapping,'complete':False})
            # Preview the same complete checkpoint using its original opening,
            # rather than consuming the just-returned final state again.
            package['manifest']['mode']='preview'
            # mode does not participate in compiler/runtime build binding.
            result,report=completed(package,data,WORK/f'{serial:02d}')
            reports.append(report); mapping[str(serial)]={'scenario':name,'position':position,'mode':'preview'}
            print('PREVIEW_PASS',serial,name,flush=True); serial+=1
        write_json(WORK/'control.json',mapping)
        write_json(WORK/'verification.json',{'reports':reports,'mapping':mapping,'complete':True,'native_checkpoints':16,'actual_successors':10,'previews':6,'frozen_pins':PINS})
        print('ALL_NATIVE_PYTHON_CHAINS_PASS',flush=True)
