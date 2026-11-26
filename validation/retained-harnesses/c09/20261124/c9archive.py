from pathlib import Path
import sys
ROOT=Path('C:/spl-c09s')
sys.path[:]=[str(ROOT)]+[p for p in sys.path if 'dynamic-domain-lang' not in p and not p.replace('\\','/').startswith('C:/spl-')]
import hashlib,json,shutil,subprocess,zipfile
from importlib import import_module
m=import_module('cases.reserve-stages.build_modules')
WORK=Path('C:/c9n_a')
OUT=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/reserve-stage-checks-20261124-a')
REF=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/c09-source-ref-a')
OUT.mkdir(parents=True,exist_ok=True)
def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v): Path(p).write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()
def git(*args): return subprocess.check_output(['git','-C',str(ROOT),*args],text=True,encoding='utf-8').strip()
assert not git('status','--porcelain')
assert 'Ran 42 tests' in (REF/'final-isolated-tests.txt').read_text(encoding='utf-8')
assert (REF/'final-isolated-tests.txt').read_text(encoding='utf-8').rstrip().endswith('OK')
source_pin=sha(m.FOLDER/'reserve-stages.spl'); builder_pin=sha(m.FOLDER/'build_modules.py')
assert source_pin=='4d65893714b4ecc0fd51c453be05b8bf64a5ac880b25f6064e3db852a28a6d56'
assert builder_pin=='ac0912afa60c5ca474cafcbedfacf23c15df11e6276eb624e5f929cf56858459'
frozen=['oracles/reserve_stages.py','cases/reserve-stages/neutral.json','cases/reserve-stages/policy.md','Tests/test_reserve_stage_oracle.py','docs/spl/reserve-stage-design.md']
frozen_pins={p:sha(ROOT/p) for p in frozen}
assert all(sha(Path('C:/TheHaltingSolution/dynamic-domain-lang')/p)==pin for p,pin in frozen_pins.items())
files=git('diff','--name-only','c80ac34','HEAD').splitlines()
assert all(p in frozen or p=='Tests/test_reserve_stage_modules.py' or p.startswith('cases/reserve-stages/') for p in files)
current_pins={p:sha(ROOT/p) for p in files}
for p in files:
    blob=subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+p])
    assert hashlib.sha256(blob).hexdigest()==sha(ROOT/p),('physical Git bytes differ',p)
valid=[x for name in ['verification.json','variants.json','unicode-fourth.json'] for x in load(WORK/name)['reports']]
assert len(valid)==50 and all(x['full_oracle_result_state_equal'] and x['python_native_equal'] for x in valid)
readers=load(WORK/'reader-verification.json')['readers'];assert len(readers)==63
invalid=[]
for p in sorted((WORK/'i').iterdir()):
    result=load(p/'result.json')
    assert result['status']=='blocked' and not result['results'] and not result['closing_state']
    reached='bindings' in result['trace']
    invalid.append({'path':p.relative_to(WORK).as_posix(),'code':result['diagnostics'][0]['code'],'native_source_reached':reached,'python_native_equal':(p/'python-comparison.json').is_file()})
assert len(invalid)==13 and sum(x['native_source_reached'] for x in invalid)==12
assert all(x['python_native_equal'] for x in invalid if x['native_source_reached'])
processes=[(p,load(p)) for p in WORK.rglob('process.json')]
assert all(p['status']=='passed' and not p['timed_out'] and not p['output_budget_exceeded'] and not p['working_set_budget_exceeded'] for _,p in processes)
assert all(p['working_set_budget_bytes']==(1073741824 if p['profile']=='compiler1g180' else 268435456) for _,p in processes)
assert all(p['output_limits_bytes']['stdout']==67108864 for _,p in processes)
worker_origins=[]
for p in WORK.rglob('stderr.bin'):
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.startswith('{'):
            event=json.loads(line)
            if event.get('format')=='spl-audit-worker-origin/1':
                assert Path(event['root'])==ROOT and Path(event['build_root'])==ROOT
                assert all(Path(item['path']).is_relative_to(ROOT) for item in event['modules'].values())
                worker_origins.append({'path':p.relative_to(WORK).as_posix(),'sha256':sha(p)})
assert len(worker_origins)>200
# Preserve the independently compiled native C/object and its exact cache pins.
for p in (ROOT/'.lake/compact-native').iterdir():
    if p.is_dir() and (p/'cache.json').exists() and load(p/'cache.json')['inputs']['source_sha256']==source_pin:
        target=WORK/'native-compiled'/p.name;target.mkdir(parents=True,exist_ok=True)
        for item in p.iterdir():
            if item.is_file():shutil.copyfile(item,target/item.name)
failures=[
 {'phase':'baseline review harness','error':'PUBLICATION_NOT_COMPLETED','cause':'v1 loader was intentionally/incorrectly selected for a completed v2 publication; corrected to the audited v2 loader; native baseline itself passed'},
 {'phase':'variant launcher harness','error':'ModuleNotFoundError: c9','cause':'embedded Python omits the script directory; corrected by explicitly inserting the own .lake helper path'},
 {'phase':'negative continuation harness','error':'NULL_NOT_ALLOWED','cause':'generic physical read_json was used on original neutral state containing legitimate computed null fractions; corrected to original JSON decoder; six prior native negatives retained'},
 {'phase':'retained reader launcher harness','error':'UnicodeDecodeError cp1252 byte0x81 position312','cause':'report metadata was opened without explicit UTF-8; corrected before any reader stage ran'},
 {'phase':'retained reader launcher harness','error':'NameError: _stage','cause':'import-star excludes private names; corrected with explicit helper import before any reader stage ran'},
 {'phase':'final42 non-isolated test attempt','error':'MODULE_DEPENDENCY_DIGEST (one failure, one error)','cause':'concurrent c9read.py import explicitly regenerated the unissued descriptor while two tests consumed it; this attempt had no closed descriptor freeze; isolated private registration fixes the harness; failed final-tests.txt retained'},
 {'phase':'pre-fix original null counterexample','error':'oracle RS_FIELDS versus old implementation calculated','cause':'explicit original final-rule fraction:null collapsed into omitted Option None; fixed in b2358bf by validating present exact values; pre-fix-null.json retains full original/result and actual old pins'}]
save(WORK/'failures.json',failures)
report={
 'complete':True,'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'base':'c80ac34bd7d529742a6223a06f56edd3118785b4',
 'commits':git('log','--format=%H %s','c80ac34..HEAD').splitlines(),
 'promotion_files':[p for p in files if p not in frozen],'frozen_five':frozen_pins,'frozen_five_match_main_bytes':True,'file_pins':current_pins,
 'financial_source_sha256':source_pin,'final_builder_sha256':builder_pin,'descriptor_sha256':sha(m.FOLDER/'reserve-stages-module.json'),
 'python_emitted_financial_library_plus_typed_transport_driver':load(WORK/'py/pins.json'),
 'scope':{'original_checkpoints':16,'original_actual_serialized_successors':10,'same_complete_checkpoint_previews':6,'additional_valid_checkpoints':28,'valid_publications':50,'native_source_blocked':12,'public_custody_blocked':1,'retained_bounded_reader_reloads':63,'distinct_modules_or_purposes':2,'native_fx_changed':False,'bank_movements':False,'source_clearance_inferred':False,'source_specific_genius_acceptance':False},
 'reference':{'independent_oracle_methods':37,'final_isolated_module_methods':42,'final_isolated_log_sha256':sha(REF/'final-isolated-tests.txt'),'old_frozen41_log_sha256':sha(REF/'frozen-tests.txt'),'post_null_focused_methods':4},
 'build_checks':{'fresh_lake_build':'passed103jobs','indexed':'passed22jobs','lake_exe_smoke':'passed','lake_exe_spl_smoke':'passed','toolchain':(ROOT/'lean-toolchain').read_text(encoding='utf-8').strip()},
 'budgets':load(WORK/'freeze.json')['budgets'],
 'metrics':{'valid_max_wire_bytes':max(x['trace']['wire_bytes'] for x in valid),'valid_max_logical_bytes':max(x['trace']['expanded_trace_bytes'] for x in valid),'valid_max_nodes':max(x['trace']['node_count'] for x in valid),'valid_max_result_bytes':max(x['result_bytes'] for x in valid),'compiler_peak_bytes':max(p.get('peak_working_set_bytes',0) for _,p in processes if p['profile']=='compiler1g180'),'runtime_reference_reader_peak_bytes':max(p.get('peak_working_set_bytes',0) for _,p in processes if p['profile']=='runtime256'),'retained_process_reports':len(processes),'asserted_worker_origin_reports':len(worker_origins)},
 'valid':[dict(x,archive_path='evidence/'+Path(x['path']).relative_to(WORK).as_posix()) for x in valid],
 'invalid':invalid,'reader_report':'evidence/reader-verification.json','lifecycle':load(WORK/'lifecycle.json'),'failures':failures,
 'environment':{'python':sys.executable,'python_sha256':sha(Path(sys.executable)),'python_version':sys.version,'python_path_after_explicit_own_root_prepend_and_other_root_removal':sys.path,'pth_pins':{str(p):sha(p) for p in Path(sys.executable).parent.glob('*._pth')}},
 'limits':'Finite controls and exact source pins only; no universal admitted-input capacity, quiet-host timing/SLA, source authenticity, external registration or compiler-correctness proof claim. Main integration remains separate.'}
save(OUT/'verification-inputs.json',report)
archive=OUT/'full-evidence.zip'
entries=[]
for p in sorted(WORK.rglob('*')):
    if p.is_file():entries.append((p,'evidence/'+p.relative_to(WORK).as_posix()))
for p in files: entries.append((ROOT/p,'source/'+p))
for p in sorted((ROOT/'.lake').glob('c9*.py')):entries.append((p,'harness/'+p.name))
for p in sorted(REF.glob('*.txt')):entries.append((p,'reference-tests/'+p.name))
entries.append((OUT/'verification-inputs.json','verification-inputs.json'))
manifest=[]
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
    for p,name in entries:
        manifest.append({'path':name,'bytes':p.stat().st_size,'sha256':sha(p)})
        z.write('\\\\?\\'+str(p.resolve()),arcname=name)
    z.writestr('archive-files.json',json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')))
save(OUT/'archive-files.json',manifest)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert len(z.infolist())==len(manifest)+1
report['archive']={'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'relative_entries':len(manifest)+1,'file_manifest_sha256':sha(OUT/'archive-files.json'),'long_path_strategy':'Windows extended source paths and explicit relative ZIP archive names'}
save(OUT/'verification.json',report)
print(json.dumps({'archive':report['archive'],'metrics':report['metrics'],'head':report['head']},indent=2),flush=True)
