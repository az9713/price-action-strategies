"""Actual interpreter exits bypass finally; all processes/stores are test-owned."""
from pathlib import Path
import json,os,subprocess,sys
import pytest
from test_spread_probe import owned
from test_spread_worker import request,state
from backend.lab.worker import Worker
from backend.lab.spread_jobs import SpreadJournal

@pytest.mark.parametrize('event,boundary',[('preparation_batch','before'),('preparation_batch','after'),('probe_started','after')])
def test_actual_interpreter_death_recovers_only_owned_lease_and_original_checkpoints(owned,tmp_path,event,boundary):
    lab,m,context,cfg=owned;job=lab.create_spread(request(m));driver=tmp_path/'owned-worker-crash.py'
    driver.write_text('''from pathlib import Path
import os,sys
from backend.lab.service import Lab
from backend.lab.worker import Worker
from backend.lab.spread_jobs import SpreadJournal
original=SpreadJournal.append
def crash(self,event,*args,**kwargs):
 if event['kind']==sys.argv[2] and sys.argv[3]=='before':os._exit(17)
 value=original(self,event,*args,**kwargs)
 if event['kind']==sys.argv[2]:os._exit(17)
 return value
SpreadJournal.append=crash
Worker(Lab(Path(sys.argv[1]))).run_once()
raise AssertionError('Owned crash boundary was not reached')
''',encoding='utf-8')
    process=subprocess.run([sys.executable,str(driver),str(lab.root),event,boundary],capture_output=True,timeout=120)
    assert process.returncode==17,process.stderr.decode('utf-8',errors='replace')
    abandoned=lab.store.job(job['id']);assert abandoned['status']=='running'
    before=SpreadJournal(lab.store,abandoned,None);prefix=before.load();batches=[e['record'] for e in prefix if e['kind']=='preparation_batch']
    original_files={r['relative_path']:(lab.root/'data/jobs'/job['id']/'spread-preparation'/r['relative_path']).read_bytes() for r in batches}
    # Expire exactly this owned fixture's lease; do not sleep or touch live app jobs.
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
    assert Worker(lab).run_once();finished=lab.store.job(job['id']);assert finished['status']=='completed',finished.get('error')
    for name,raw in original_files.items():assert (lab.root/'data/jobs'/job['id']/'spread-preparation'/name).read_bytes()==raw
    assert state(lab,job)['stage']=='qualified'
    registry=lab.store.registry(job_id=job['id']);assert registry['totals']['computation_attempts']==(10 if event=='probe_started' else 9)
    assert len([e for e in lab.store.events(job['id']) if e['kind']=='trial_plan_frozen'])==1
    if boundary=='before':assert list((lab.root/'data/jobs'/job['id']/'preparation-orphans').glob('*.gz'))
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        p=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/('actual-process-'+event+'-'+boundary+'.json')
        p.write_text(json.dumps(dict(scope='Actual test-owned interpreter exit17 and durable original checkpoint recovery; synthetic inputs, no live app process terminated',job_id=job['id'],crashed_on=event,boundary=boundary,child_exit_code=17,committed_batches_before=len(batches),registry=registry,final_status=state(lab,job)),indent=2),encoding='utf-8')
