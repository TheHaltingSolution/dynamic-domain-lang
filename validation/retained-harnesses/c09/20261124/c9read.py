import sys
sys.path.insert(0,'C:/spl-c09s/.lake')
from c9 import *
from spl_compiler.compact_execution import WORKER, _stage

paths=[Path(report['path']) for name in ('verification.json','variants.json','unicode-fourth.json') for report in json.loads((WORK/name).read_text(encoding='utf-8'))['reports']]
paths.extend(sorted((WORK/'i').iterdir()))
reports=[]
for i,path in enumerate(paths):
    output=_stage([sys.executable,WORKER,'load',path],path/'retained-reader')
    result=metadata(output)
    if path.parent.name!='i': assert result['status'] in ('calculated','provisional')
    else: assert result['status']=='blocked' and not result['results'] and not result['closing_state']
    report=read_json(path/'retained-reader/process.json')
    reports.append({'path':str(path),'status':result['status'],'reader':report})
    print('READER_PASS',i,path.name,flush=True)
write_json(WORK/'reader-verification.json',{'complete':True,'readers':reports})
