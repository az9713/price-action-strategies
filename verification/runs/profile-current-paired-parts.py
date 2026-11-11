"""Measure actual two-part original-authority overhead before optimizing reuse."""
from pathlib import Path
import hashlib,json,os,sys,time
root=Path.cwd();source=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path[:0]=[str(source),str(source/'tests'),str(root)]
from verification.record_check import source_paths
before={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(source)}
from conftest import minute_frame
from backend.lab import service
from backend.lab.service import Lab
from backend.lab.data import save_dataset,normalize,prepare as prepare_data
from backend.lab.models import Experiment
from backend.lab.worker import Worker
from backend.lab.trade_twin_jobs import create
from backend.lab.trade_twin_preparation import prepare
from backend.lab.trade_twin_parts import FinancialParts
from test_reference_execution import CFG,ZERO,ACCOUNT,sig
folder=root/'data/dev026/part-profiles'/out.name.split('-')[0];lab=Lab(folder)
frame=minute_frame('2026-11-04');manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='paired authority profile',corporate_actions_complete=True))
signal=sig(prepare_data(normalize(frame)[0]),at=20);service.generate_signals=lambda *a,**k:[signal]
parent=lab.create_experiment(Experiment(dataset_id=manifest['id'],start='2026-11-04',end='2026-11-04',strategy=CFG,costs=ZERO,portfolio=ACCOUNT))
assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
child=create(lab,parent['id']);owner='paired-profile';job=lab.store.claim(owner)
prepared=prepare(lab,job,owner);journal=FinancialParts(lab,job,owner,prepared)
load=journal._load;timings=[]
def measured(*args,**kwargs):
 started=time.perf_counter()
 try:return load(*args,**kwargs)
 finally:timings.append(time.perf_counter()-started)
journal._load=measured;parts=[]
for ordinal in range(2):
 begin=len(timings);started=time.perf_counter();value=journal.execute(ordinal);elapsed=time.perf_counter()-started
 parts.append(dict(part=ordinal,seconds=elapsed,original_load_calls=len(timings)-begin,original_load_seconds=sum(timings[begin:]),new_books=len(value['books']),financial_occurrences=len(value['sets'])))
lab.store.release(job['id'],owner)
after={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(source)}
assert before==after
value=dict(scope=__doc__,parts=parts,original_parent=parent['id'],child=child['id'],source_files=before,source_unchanged=True,configured_sets_per_policy=10000,executed_sets_per_policy=200,full_comparison_completed=False,main_app_source_not_replaced=True)
(out/'paired-authority-profile.json').write_text(json.dumps(value,indent=2))
print(json.dumps({k:v for k,v in value.items() if k!='source_files'},indent=2))
