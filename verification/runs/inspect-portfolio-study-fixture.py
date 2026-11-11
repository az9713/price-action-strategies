from pathlib import Path
import json,sys,os
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from test_portfolio_studies import study_data,request
from backend.lab.worker import Worker
folder=root/'data/portfolio-study-fixture-probe';assert not folder.exists();folder.mkdir()
lab,m,frame=study_data.__wrapped__(folder);study=lab.register_study(request(m));job=lab.screen(study['id']);Worker(lab).run_once()
result=lab.result(job['id']);reports={w:lab.report(job['id'],0,w) for w in ['discovery','validation']}
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'authored-study-fixture-diagnostics.json').write_text(json.dumps(dict(study=lab.guard.study(study['id']),reports=reports),indent=2),encoding='utf-8')
print(json.dumps({w:dict(metrics=r['metrics'],trades=r['trades'],signals=len(r['signals'])) for w,r in reports.items()},indent=2))
