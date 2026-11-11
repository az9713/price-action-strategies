"""Bind current downloaded research books to the independently audited constant-cost account."""
from pathlib import Path
import hashlib,json,os,struct,sys
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.service import Lab
from backend.lab.research import core_hash
lab=Lab(root);browser=root/sys.argv[1];reference=json.loads((root/sys.argv[2]).read_text(encoding='utf-8'));rows=[]
assert reference['core_hash']==core_hash()
for observation in sorted((browser/'artifacts').glob('*/observations.json')):
    folder=observation.parent;observed=json.loads(observation.read_text(encoding='utf-8'));report=lab.report(observed['job_id'])
    assert report['core_hash']==reference['core_hash'] and report['config']==reference['config'] and report['costs']==reference['costs'] and report['portfolio']==reference['portfolio']
    assert report['signals']==reference['signals']
    for key in ['trades','ledger','equity','rejected']:assert report[key]==reference['actual'][key],key
    assert json.loads((folder/'downloaded-report.json').read_text(encoding='utf-8'))==report
    assert observed['consoleErrors']==[]
    images=[]
    for name in ['data','strategies','experiment','results','trade-inspector','validation','reports','trade-chart']:
        p=folder/(name+'.png');raw=p.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
        w,h=struct.unpack('>II',raw[16:24]);assert w>200 and h>300
        images.append(dict(path=p.relative_to(root).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),width=w,height=h))
    rows.append(dict(profile=folder.name,job_id=observed['job_id'],signals=len(report['signals']),trades=len(report['trades']),ledger_events=len(report['ledger']),marks=len(report['equity']),screenshots=images))
assert len(rows)==2
(Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'basic-research-reconciliation.json').write_text(json.dumps(dict(scope=__doc__,reference_path=sys.argv[2],profiles=rows),indent=2),encoding='utf-8')
print(json.dumps(dict(profiles=len(rows),independently_audited_accounts_matched=2,screenshots=sum(len(r['screenshots']) for r in rows))))
