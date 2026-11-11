"""Actual saved-envelope read scale, with zero signal/account computations."""
from pathlib import Path
import json,os,time,tracemalloc
import pytest
from backend.lab.service import Lab
from backend.lab.store import Store
from backend.lab.config import Strategy,identity,canonical
from backend.lab.spread import SpreadSettings
from backend.lab.spread_jobs import SpreadJournal,initial
from backend.lab.research import core_hash

def configuration(i):
 return Strategy(family='break_of_structure',timeframe='1m',level_age=2+i%999,
  swing_strength=[2,3,5,8][i//999%4],target=['1R','1.5R','2R','3R','4R','5R','swing'][i//3996%7],
  direction=['long','short','both'][i//27972%3],entry=['next_open','same_close','limit'][i//83916%3]).model_dump()

@pytest.mark.parametrize('count',[10,1000,100000])
def test_large_nonfinancial_original_selection_pages_remain_bounded(tmp_path,monkeypatch,count):
 lab=Lab(tmp_path);store=lab.store;settings=SpreadSettings(families=['break_of_structure'],timeframes=['1m'],per_family=count,batch_size=1,max_batches_per_family=count)
 context=dict(dataset_id='a'*24,dataset_manifest_hash='b'*64,primary_symbol='SPY',start='2026-11-02',end='2026-11-06')
 job=store.create_job('spread',dict(name='NONFINANCIAL saved-envelope fixture; declared40 counts are stubs; no actual qualification or financial accounts',settings=settings.model_dump(),context=context,core_hash=core_hash()))
 claimed=store.claim('nonfinancial-owner');SpreadJournal(store,claimed,'nonfinancial-owner');binding=identity(claimed['payload']);head=None;seen=set()
 with store.db() as db:
  db.execute('BEGIN IMMEDIATE')
  for i in range(count):
   cfg=configuration(i);cid=identity(cfg);assert cid not in seen;seen.add(cid)
   event=dict(kind='version_selected',family=cfg['family'],batch=i,ordinal=0,configuration=cfg,config_id=cid,signal_count=40,score=0)
   body=dict(sequence=i,previous=head,payload_sha256=binding,event=event,artifact_sha256=None,owner='nonfinancial-owner');head=identity(body)
   store.event('spread_protocol',job['id'],body|dict(event_sha256=head),db)
  last=db.execute('SELECT MAX(id) FROM events WHERE entity_id=?',(job['id'],)).fetchone()[0]
  # A deliberately unrelated huge body must not enter any page materialization.
  store.event('spread_protocol',job['id'],dict(event=dict(kind='nonfinancial_unrelated'),blob='x'*(8*1024*1024)),db)
  p=initial(settings);p.update(stage='qualified',selected_versions=count,family_counts={settings.families[0]:count},qualified_complete=True,selection_manifest_hash='f'*64)
  db.execute('UPDATE spread_state SET event_count=?,head_sha256=?,projection=?,projection_sha256=? WHERE job_id=?',(count,head,canonical(p),identity(p),job['id']))
  db.execute("UPDATE jobs SET status='completed',owner=NULL,lease_until=NULL WHERE id=?",(job['id'],));db.execute('COMMIT')
 original=json.loads;decoded=[]
 def observed(raw,*a,**k):decoded.append(len(raw.encode() if isinstance(raw,str) else raw));return original(raw,*a,**k)
 monkeypatch.setattr(json,'loads',observed)
 def forbidden(*a,**k):raise AssertionError('A saved-envelope page attempted numerical/account work')
 monkeypatch.setattr(lab,'spread_signal_probe',forbidden);monkeypatch.setattr(lab,'result',forbidden)
 tracemalloc.start();started=time.perf_counter();pages=[]
 for after in [0,max(0,last//2),max(0,last-100)]:
  page=lab.spread_selections(job['id'],after=after,limit=100);assert page['selected_count']==count
  assert len(page['versions'])<=100 and len(canonical(page).encode())<=2*1024*1024
  assert all(v['config_id']==identity(v['configuration']) for v in page['versions']);pages.append(page)
 elapsed=time.perf_counter()-started;_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
 assert len(pages[0]['versions'])==min(count,100) and peak<8*1024*1024
 assert max(decoded)<=65536 and sum(decoded)<=3*(2*1024*1024+65536)
 assert store.registry(job_id=job['id'])['totals']['computation_attempts']==0
 if os.environ.get('PA_EVIDENCE_RUN_DIR'):
  p=Path(os.environ['PA_EVIDENCE_RUN_DIR'])/('nonfinancial-selection-pages-'+str(count)+'.json')
  p.write_text(json.dumps(dict(scope=__doc__,saved_stub_selection_envelopes=count,unique_configurations=len(seen),actual_signal_computations=0,actual_financial_accounts=0,
   read_seconds=elapsed,python_tracemalloc_peak_bytes=peak,largest_decoded_json_bytes=max(decoded),total_decoded_json_bytes=sum(decoded),page_bytes=[len(canonical(page).encode()) for page in pages],
   limits=dict(page_bytes=2097152,page_rows=100,python_heap=8388608),full_prefix_validated=False,source_scale_executed=False),indent=2),encoding='utf-8')
