"""Measure authority/draw/cache overhead on the actual owned synthetic probe.

Read-only financial evidence; no new account, redraw, relaxed guard or OS cache
claim. Measurements coexist with the full backend regression.
"""
from pathlib import Path
import hashlib,json,os,sys,time
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path[:0]=[str(source),str(source/'tests')]
from backend.lab.service import Lab
from backend.lab.trade_twin_source import read_saved_source,_saved_state
from backend.lab.trade_twins import prepare_plan,draw_set
from backend.lab.research import require_current_source
from test_trade_twin_source import database_fingerprint
identifier='20261109T202726676713Z-trade-twins-uninstalled-actual-10000-paired-financial-sets-from-original-synthetic-account'
receipt=json.loads((root/'verification/receipts'/(identifier+'.json')).read_text());assert receipt['command']['exit_code']==0
folder=root/'verification/runs'/identifier
for a in receipt['artifacts']:
 p=root/a['path'];assert p.stat().st_size==a['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256']
summary=json.loads((folder/'prototype-financial-10000-summary.json').read_text());lab=Lab(root/'data/dev026/prototypes'/identifier);jid=summary['original_synthetic_job_id']
before=database_fingerprint(lab);authority=read_saved_source(lab,jid)
raw=json.loads((folder/'sealed-prototype-plan.json').read_text());plan=prepare_plan(raw['sources'],raw['moments'],raw['clocks'],raw['start'],raw['end'],raw['source_parent_identity']);assert plan.plan_hash==raw['plan_hash']
first=next((folder/'financial-bank').glob('*.json'));expected=hashlib.sha256(first.read_bytes()).hexdigest();original_files={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [folder/'sealed-prototype-plan.json',first]}
def measure(name,count,function):
 began=time.perf_counter()
 for index in range(count):function(index)
 seconds=time.perf_counter()-began
 return dict(name=name,calls=count,elapsed_seconds=seconds,seconds_per_call=seconds/count)
def source_read(_):assert read_saved_source(lab,jid)['authority_hash']==authority['authority_hash']
def registry_read(_):assert _saved_state(lab,jid,0)[2]==authority['authority']
def cache_read(_):
 value=first.read_bytes();assert hashlib.sha256(value).hexdigest()==expected;book=json.loads(value);assert book['inputs']['plan_hash']==plan.plan_hash
rows=[measure('fresh_complete_original_source_authority',50,source_read),measure('fresh_source_code_identity_guard',100,lambda _:require_current_source()),measure('original_registry_plan_trial_attempt_event_verification',50,registry_read),measure('one_complete_draw',1000,lambda i:draw_set(plan,42,i)),measure('saved_financial_book_byte_hash_and_decode',1000,cache_read)]
assert database_fingerprint(lab)==before
for p,digest in original_files.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==digest
value=dict(scope=__doc__,source_receipt=identifier,original_synthetic_job_id=jid,measurements=rows,original_database_unchanged=True,original_artifacts_unchanged=True,new_financial_jobs=0,guards_relaxed=False,production_optimization_applied=False,final_acceptance_certified=False)
(out/'authority-cost-profile.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
