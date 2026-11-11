"""Owned synthetic worker exit/recovery audit: cache and read connections close without changing durable authority."""
from pathlib import Path
from threading import Event
import hashlib,json,os,sqlite3,sys,tempfile
import pandas as pd
import pytest
root=Path.cwd();sys.path[:0]=[str(root),str(root/'tests')]
from backend.lab.service import Lab
from backend.lab.worker import Worker
from backend.lab.models import Experiment,Search
from backend.lab.data import save_dataset,DataError
from backend.lab.evaluation_cache import current_cache
from backend.lab import store as store_module
from conftest import minute_frame
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);records=[]
def closed(cache,connection):
 assert cache is not None and cache.cache_bytes==0 and cache.current_frame is None
 try:connection.execute('SELECT 1')
 except sqlite3.ProgrammingError:return
 raise AssertionError('Owned control connection survived its worker job scope')
with tempfile.TemporaryDirectory(prefix='owned-cache-exits-',dir=root/'data') as directory:
 owned=Path(directory).resolve();assert owned.is_relative_to((root/'data').resolve())
 for mode in ['completed','failed','canceled','shutdown_release','lost_owner','part_recovery']:
  lab=Lab(owned/mode);frame=pd.concat([minute_frame('2026-11-02'),minute_frame('2026-11-03')]);manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',source='Owned software exit-contract prices'),start='2026-11-02',end='2026-11-03')
  request=Search(dataset_id=manifest['id'],count=2,families=['break_of_structure'],timeframes=['1m'],start='2026-11-02',end='2026-11-03') if mode=='part_recovery' else Experiment(dataset_id=manifest['id'],start='2026-11-02',end='2026-11-03')
  job=lab.create_experiment(request);jid=job['id'];shutdown=Event();worker=Worker(lab,shutdown);captured=[];original=lab.evaluate
  def evaluate(*args,**kwargs):
   cache=current_cache(lab.root);reader=store_module._control_reader.get();assert cache is not None and reader is not None
   captured.append((cache,reader[-1]));value=original(*args,**kwargs)
   if mode=='failed':raise DataError('Owned post-evaluation fault')
   if mode=='canceled':lab.store.cancel(jid)
   if mode=='shutdown_release':shutdown.set()
   if mode=='lost_owner':
    with lab.store.db() as db:db.execute('UPDATE jobs SET owner=? WHERE id=?',('different-owned-worker',jid))
   return value
  with pytest.MonkeyPatch.context() as patch:
   patch.setattr(lab,'evaluate',evaluate)
   if mode=='part_recovery':
    progress=worker._progress
    def checkpoint(*args,**kwargs):
     value=progress(*args,**kwargs)
     if kwargs.get('checkpoint')==1 or len(args)>3 and args[3]==1:shutdown.set()
     return value
    patch.setattr(worker,'_progress',checkpoint)
   assert worker.run_once()
  assert captured
  for cache,connection in captured:closed(cache,connection)
  assert current_cache(lab.root) is None and store_module._control_reader.get() is None
  state=lab.store.job_status(jid);expected=dict(completed='completed',failed='failed',canceled='canceled',shutdown_release='queued',lost_owner='running',part_recovery='queued')[mode];assert state['status']==expected,(mode,state['status'])
  recovered=False;first_part_unchanged=None
  if mode in ['shutdown_release','part_recovery']:
   part=lab.root/'data/jobs'/jid/'parts/000000.json.gz';before=hashlib.sha256(part.read_bytes()).hexdigest() if part.exists() else None
   original_evaluate=lab.evaluate;recovered_scopes=[]
   def resumed(*args,**kwargs):
    cache=current_cache(lab.root);reader=store_module._control_reader.get();recovered_scopes.append((cache,reader[-1]));assert all(cache is not old[0] for old in captured)
    return original_evaluate(*args,**kwargs)
   with pytest.MonkeyPatch.context() as patch:patch.setattr(lab,'evaluate',resumed);assert Worker(lab).run_once()
   assert lab.store.job_status(jid)['status']=='completed';assert recovered_scopes
   for cache,connection in recovered_scopes:closed(cache,connection)
   recovered=True
   if before is not None:
    assert hashlib.sha256(part.read_bytes()).hexdigest()==before;first_part_unchanged=True
    with lab.store.db() as db:
     rows=db.execute('SELECT part,state,attempts,reuses FROM trial_plans WHERE job_id=? ORDER BY part',(jid,)).fetchall()
    assert len(rows)==2 and all(r['state']=='completed' and r['attempts']==1 for r in rows) and rows[0]['reuses']==1 and rows[1]['reuses']==0
  if mode=='lost_owner':assert not (lab.root/'data/jobs'/jid/'result.json.gz').exists()
  records.append(dict(mode=mode,initial_status=state['status'],cache_cleared=True,control_connection_closed=True,resumed=recovered,first_part_unchanged=first_part_unchanged,financial_edge_certified=False))
value=dict(scope=__doc__,cases=records,synthetic_software_evidence=True);(out/'evaluation-cache-worker-exits.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(worker_exit_cases=len(records),recovery_cases=sum(r['resumed'] for r in records),all_caches_cleared=True,all_control_connections_closed=True,scope=__doc__)))
