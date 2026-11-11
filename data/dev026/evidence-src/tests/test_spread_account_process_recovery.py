"""Actual owned child-account interpreter deaths; no running-app PID is touched."""
from pathlib import Path
import json,os,subprocess,sys
import pytest
from backend.lab.worker import Worker
from test_spread_probe import owned
from test_spread_account_handoff import qualified

@pytest.mark.parametrize('boundary',['attempt_started','part_committed'])
def test_actual_financial_worker_death_retains_attempts_and_exact_part_bytes(owned,tmp_path,monkeypatch,boundary):
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id']);driver=tmp_path/'owned-account-crash.py'
 driver.write_text('''from pathlib import Path
import os,sys
from backend.lab.service import Lab
from backend.lab.worker import Worker
trial=Worker._trial
progress=Worker._progress
def crash_trial(self,job,part,window,calculate):
 if job['kind']=='spread_accounts' and sys.argv[2]=='attempt_started':
  self.lab.store.start_trial(job['id'],part,window,self.owner);os._exit(19)
 return trial(self,job,part,window,calculate)
def crash_progress(self,job,fraction,note,checkpoint=None):
 if job['kind']=='spread_accounts' and sys.argv[2]=='part_committed' and checkpoint==1:os._exit(19)
 return progress(self,job,fraction,note,checkpoint)
Worker._trial=crash_trial
Worker._progress=crash_progress
Worker(Lab(Path(sys.argv[1]))).run_once()
raise AssertionError('Owned account crash boundary was not reached')
''',encoding='utf-8')
 process=subprocess.run([sys.executable,str(driver),str(lab.root),boundary],capture_output=True,timeout=120)
 assert process.returncode==19,process.stderr.decode('utf-8',errors='replace')
 assert lab.store.job(child['id'])['status']=='running'
 part=lab.output_path(child['id']).parent/'parts/000000.json.gz';committed=part.read_bytes() if part.exists() else None
 if boundary=='part_committed':
  assert committed is not None
  def forbidden(*a,**k):raise AssertionError('Actual process recovery recomputed a committed account')
  monkeypatch.setattr('backend.lab.service.simulate',forbidden)
 with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(child['id'],))
 assert Worker(lab).run_once();assert lab.store.job(child['id'])['status']=='completed',lab.store.job(child['id'])['error']
 registry=lab.store.registry(job_id=child['id']);assert registry['totals']['computation_attempts']==(2 if boundary=='attempt_started' else 1)
 if committed is not None:assert part.read_bytes()==committed and registry['rows'][0]['reuses']>=1
 assert len([e for e in lab.store.events(parent['id']) if e['kind']=='spread_accounts_frozen'])==1
 if os.environ.get('PA_EVIDENCE_RUN_DIR'):
  p=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/('actual-account-process-'+boundary+'.json')
  p.write_text(json.dumps(dict(scope=__doc__,boundary=boundary,child_exit_code=19,job_id=child['id'],original_parent_id=parent['id'],registry=registry,committed_part_reused=committed is not None),indent=2),encoding='utf-8')
