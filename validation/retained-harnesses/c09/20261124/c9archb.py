from pathlib import Path
import sys
ROOT=Path('C:/spl-c09s')
sys.path[:]=[str(ROOT)]+[p for p in sys.path if 'dynamic-domain-lang' not in p and not p.replace('\\','/').startswith('C:/spl-')]
import hashlib,json,shutil,subprocess,zipfile
WORK=Path('C:/c9n_b');OUT=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/reserve-stage-namespaces-20261124-b');OUT.mkdir(parents=True,exist_ok=True)
REF=Path('C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/c09-source-ref-a')
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8',newline='\n')
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while chunk:=f.read(1048576):h.update(chunk)
    return h.hexdigest()
def git(*a):return subprocess.check_output(['git','-C',str(ROOT),*a],text=True,encoding='utf-8').strip()
assert not git('status','--porcelain')
financial='4d65893714b4ecc0fd51c453be05b8bf64a5ac880b25f6064e3db852a28a6d56'
builder='94a5de9c4b473a703082621e0ae53f7849278521a96208ec1e24b84ae0ecf3c0'
assert sha(ROOT/'cases/reserve-stages/reserve-stages.spl')==financial
assert sha(ROOT/'cases/reserve-stages/build_modules.py')==builder
assert (REF/'namespace45-tests.txt').read_text(encoding='utf-8').rstrip().endswith('OK')
frozen=['oracles/reserve_stages.py','cases/reserve-stages/neutral.json','cases/reserve-stages/policy.md','Tests/test_reserve_stage_oracle.py','docs/spl/reserve-stage-design.md']
assert all(sha(ROOT/p)==sha(Path('C:/TheHaltingSolution/dynamic-domain-lang')/p) for p in frozen)
files=git('diff','--name-only','c80ac34','HEAD').splitlines()
assert all(p in frozen or p=='Tests/test_reserve_stage_modules.py' or p.startswith('cases/reserve-stages/') for p in files)
for p in files:assert hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT),'show','HEAD:'+p])).hexdigest()==sha(ROOT/p)
verification=load(WORK/'verification.json');ns=load(WORK/'namespace.json')
assert verification['complete'] and len(verification['reports'])==22 and ns['complete'] and len(ns['reports'])==9 and ns['different_keys_same_scope']
assert all(x['full_oracle_result_state_equal'] and x['python_native_equal'] for x in verification['reports'])
processes=[load(p) for p in WORK.rglob('process.json')]
assert all(p['status']=='passed' and not p['timed_out'] and not p['working_set_budget_exceeded'] and not p['output_budget_exceeded'] for p in processes)
assert all(p['working_set_budget_bytes']==(1073741824 if p['profile']=='compiler1g180' else 268435456) for p in processes)
assert len(list(WORK.rglob('retained-reader/process.json')))==31
origins=[]
for p in WORK.rglob('stderr.bin'):
    for line in p.read_text(encoding='utf-8').splitlines():
        if line.startswith('{'):
            event=json.loads(line)
            if event.get('format')=='spl-audit-worker-origin/1':
                assert Path(event['root'])==ROOT and Path(event['build_root'])==ROOT and all(Path(x['path']).is_relative_to(ROOT) for x in event['modules'].values())
                origins.append(p.relative_to(WORK).as_posix())
report={'complete':True,'head':git('rev-parse','HEAD'),'branch':git('branch','--show-current'),'base':'c80ac34bd7d529742a6223a06f56edd3118785b4','financial_source_sha256':financial,'builder_sha256':builder,
 'registration_references':ns['registration_references'],'canonical_purposes':{'basis_reserve':'synthetic_gross_basis_reserve','producer_holdback':'synthetic_producer_entitlement_holdback'},'registered_root_modules':2,'same_scope_distinct_state_keys':True,
 'original_checkpoints':16,'actual_serialized_successors':10,'complete_checkpoint_previews':6,'valid_publications':22,'public_or_generic_admission_blocks':9,'retained_bounded_readers':31,'final_isolated_reference_methods':45,
 'promotion_files':[p for p in files if p not in frozen],'file_pins':{p:sha(ROOT/p) for p in files},'frozen_five_match_main_bytes':True,'frozen_five':{p:sha(ROOT/p) for p in frozen},
 'budgets':load(WORK/'freeze.json')['budgets'],'metrics':{'max_wire_bytes':max(x['trace']['wire_bytes'] for x in verification['reports']),'max_logical_bytes':max(x['trace']['expanded_trace_bytes'] for x in verification['reports']),'max_nodes':max(x['trace']['node_count'] for x in verification['reports']),'max_result_bytes':max(x['result_bytes'] for x in verification['reports']),'compiler_peak_bytes':max(p.get('peak_working_set_bytes',0) for p in processes if p['profile']=='compiler1g180'),'runtime_reference_reader_peak_bytes':max(p.get('peak_working_set_bytes',0) for p in processes if p['profile']=='runtime256'),'retained_process_reports':len(processes),'asserted_worker_origins':len(origins)},
 'namespace':ns,'valid':verification['reports'],'python_emitted_financial_library_plus_typed_transport_driver':load(WORK/'py/pins.json'),
 'earlier_financial_evidence':{'verification':'C:/Projects/Film_TV_participation_dynamic_DSL/artifacts/spl/reserve-stage-checks-20261124-a/verification.json','head':'70010af956e55f763d7aca83885649560469f25c','archive_sha256':'efa94fcbf60a8f1f43aef92892f281444ed819cbc4414b1a5f04760dea360caa','valid_stage_discriminator_publications':50,'native_source_guard_blocks':12,'scope':'Earlier descriptor/adapter pins; credit for unchanged financial source stage/cap/calendar/history controls, not final canonical namespace qualification. The old shared technical history key collision is corrected by the two final registrations.'},
 'failed_attempts':[
 {'phase':'initial namespace descriptor development','error':'MODULE_SCHEMA_PATTERN','cause':'two-colon module ID spelling was rejected before any calculation; final static IDs use the admitted namespace/name spelling'},
 {'phase':'namespace focused test expectation','error':'expected MODULE_SCOPE_MISMATCH but got MODULE_STATE_PURPOSE','cause':'intrinsic state-purpose admission correctly ran first; final test records that rejection then retags metadata to separately reach defensive descriptor constraints'},
 {'phase':'namespace campaign launcher','error':'PowerShell/Python command quoting SyntaxError','cause':'launcher did not start; corrected source generation with native PowerShell file methods; no financial input or source changed'}],
 'scope_limits':'Finite selected original calculations, exact namespace/custody controls and complete publications; no native FX, Genius active-claim clearance/excess-return/after-liquidation interpretation, bank movement, source authenticity service, universal admitted-input capacity, quiet-host timing/SLA or compiler-correctness proof.',
 'fresh_checks':{'lake_build':'103jobs passed','indexed':'22jobs passed','smoke':'passed','spl_smoke':'passed','scope':'Fresh unchanged c80 compiler/toolchain build in own worktree before financial campaigns; later changes are case-only source/adapter/descriptors/tests/docs.'}}
save(OUT/'verification-inputs.json',report)
archive=OUT/'full-evidence.zip';entries=[]
for p in sorted(WORK.rglob('*')):
    if p.is_file():entries.append((p,'evidence/'+p.relative_to(WORK).as_posix()))
for p in files:entries.append((ROOT/p,'source/'+p))
for name in ('c9b.py','c9ns.py','c9archb.py'):entries.append((ROOT/'.lake'/name,'harness/'+name))
entries.append((REF/'namespace45-tests.txt','reference-tests/namespace45-tests.txt'))
entries.append((OUT/'verification-inputs.json','verification-inputs.json'))
manifest=[]
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
    for p,name in entries:
        manifest.append({'path':name,'bytes':p.stat().st_size,'sha256':sha(p)})
        z.write('\\\\?\\'+str(p.resolve()),arcname=name)
    z.writestr('archive-files.json',json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')))
save(OUT/'archive-files.json',manifest)
with zipfile.ZipFile(archive) as z:assert z.testzip() is None and len(z.infolist())==len(manifest)+1
report['archive']={'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'relative_entries':len(manifest)+1,'file_manifest_sha256':sha(OUT/'archive-files.json'),'long_path_strategy':'explicit Windows extended source paths and relative ZIP entries'}
save(OUT/'verification.json',report)
print(json.dumps({'head':report['head'],'archive':report['archive'],'metrics':report['metrics']},indent=2),flush=True)
