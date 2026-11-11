"""Actual worker evidence publication, orphan retention and guarded restart failures."""
from pathlib import Path
import gzip,hashlib,json
import pytest
from backend.lab.config import canonical,identity
from backend.lab.store import StateError
from backend.lab.spread_jobs import SpreadJournal
from backend.lab.spread_worker import execute_spread
from backend.lab.worker import Worker
from test_spread_probe import owned
from test_spread_worker import job_and_worker

def claimed(owned,**updates):
 lab,job,worker=job_and_worker(owned,**updates);job=lab.store.claim(worker.owner);return lab,job,worker

@pytest.mark.parametrize('fault',['context','configuration','count','warmup','symbol','malformed_gzip'])
def test_new_signal_artifact_is_verified_before_it_becomes_committed(owned,monkeypatch,fault):
 lab,job,worker=claimed(owned);original=lab.spread_signal_probe
 def changed(*a,**k):
  report=original(*a,**k)
  if fault=='context':report['context']=report['context']|{'primary_symbol':'QQQ'}
  elif fault=='configuration':report['config_id']='a'*64
  elif fault=='count':report['signal_count']+=1
  elif fault=='warmup':report['excluded_warmup_signals']+=1
  elif fault=='symbol':
   if not report['signals']:report['signals']=[dict(symbol='QQQ',available_at='2026-10-20T15:00:00Z')];report['signal_count']=1
   else:report['signals'][0]['symbol']='QQQ'
  return report
 monkeypatch.setattr(lab,'spread_signal_probe',changed)
 if fault=='malformed_gzip':
  compress=gzip.compress
  def bad(raw,*a,**k):
   value=compress(raw,*a,**k)
   return b'malformed compressed signal' if b'"signal_count"' in raw else value
  monkeypatch.setattr(gzip,'compress',bad)
 with pytest.raises(StateError):execute_spread(worker,job,lambda:False)
 assert not lab.output_path(job['id']).exists()
 assert not any(e['kind']=='spread_protocol' and e['details']['event']['kind']=='probe_completed' for e in lab.store.events(job['id']))

@pytest.mark.parametrize('fault',['wrong_existing','same_existing','temporary','already_preserved'])
def test_uncommitted_signal_orphans_are_preserved_before_atomic_publication(owned,monkeypatch,fault):
 lab,job,worker=claimed(owned);original=lab.spread_signal_probe;injected=[]
 folder=lab.output_path(job['id']).parent;wrong=b'original uncommitted wrong bytes'
 def seeded(*a,**k):
  report=original(*a,**k)
  if not injected:
   injected.append(True);raw=canonical(report).encode();p=folder/'spread-signals'/(hashlib.sha256(raw).hexdigest()+'.json.gz');p.parent.mkdir(exist_ok=True)
   if fault=='temporary':p=p.with_name(p.name+'.uncommitted')
   p.write_bytes(gzip.compress(raw,mtime=0) if fault=='same_existing' else wrong)
   if fault=='already_preserved':
    q=folder/'spread-orphans'/(hashlib.sha256(wrong).hexdigest()+'.gz');q.parent.mkdir(exist_ok=True);q.write_bytes(wrong)
  return report
 monkeypatch.setattr(lab,'spread_signal_probe',seeded);execute_spread(worker,job,lambda:False)
 assert lab.output_path(job['id']).exists()
 if fault!='same_existing':assert any(p.read_bytes()==wrong for p in (folder/'spread-orphans').iterdir())
 assert not list((folder/'spread-signals').glob('*.uncommitted'))

@pytest.mark.parametrize('fault',['unchanged','bytes','context','uncommitted'])
def test_saved_root_recovery_preserves_the_original_result_authority(owned,monkeypatch,fault):
 from backend.lab.service import compressed_read,compressed_write
 lab,job,worker=job_and_worker(owned);progress=worker._progress
 def stop_at_saved(job,fraction,*a,**k):
  if fraction==1 and any(e['kind']=='result_saved' for e in lab.store.events(job['id'])):raise InterruptedError('Owned crash after result_saved before job finish')
  return progress(job,fraction,*a,**k)
 monkeypatch.setattr(worker,'_progress',stop_at_saved);assert worker.run_once();assert lab.store.job(job['id'])['status']=='canceled'
 path=lab.output_path(job['id']);original=path.read_bytes()
 if fault=='bytes':path.write_bytes(b'X'+original[1:])
 elif fault=='context':
  value=compressed_read(path);value['context']=value['context']|{'primary_symbol':'QQQ'};compressed_write(path,value)
  # Even a matching root-byte event cannot change its frozen scientific context.
  lab.store.event('result_saved',job['id'],dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 elif fault=='uncommitted':
  with lab.store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_saved'",(job['id'],))
 lab.store.resume(job['id']);assert Worker(lab).run_once();saved=lab.store.job(job['id'])
 assert saved['status']==('failed' if fault in {'bytes','context'} else 'completed'),saved.get('error')
 if fault in {'unchanged','uncommitted'}:assert path.read_bytes()==original
 if fault=='uncommitted':assert any(p.read_bytes()==original for p in (path.parent/'spread-orphans').glob('*.gz'))

def test_changed_primary_source_bytes_prevent_committed_signal_reuse(owned,monkeypatch):
 lab,job,worker=job_and_worker(owned);append=SpreadJournal.append;once=[]
 def stop(self,event,*a,**k):
  value=append(self,event,*a,**k)
  if event['kind']=='probe_completed' and not once:once.append(True);raise InterruptedError('Owned committed probe checkpoint')
  return value
 monkeypatch.setattr(SpreadJournal,'append',stop);assert worker.run_once();assert once
 p=lab.datasets_root/job['payload']['dataset_id']/'minutes.parquet';raw=p.read_bytes();p.write_bytes(raw[:-1]+bytes([raw[-1]^1]))
 monkeypatch.setattr(SpreadJournal,'append',append);lab.store.resume(job['id']);assert Worker(lab).run_once()
 assert lab.store.job(job['id'])['status']=='failed' and not lab.output_path(job['id']).exists()

@pytest.mark.parametrize('changed',[False,True])
def test_explicit_news_parent_is_rechecked_through_qualification(owned,monkeypatch,changed):
 from backend.lab.news import NewsCalendar
 lab,m,context,cfg=owned;calendar=lab.news.save(NewsCalendar(name='Owned synthetic worker news',start='2026-10-05',end='2026-10-30',mode='synthetic',complete=True,events=[]))
 lab,job,worker=claimed(owned,news_calendar_id=calendar['id'],settings=dict(families=['break_of_structure'],timeframes=['1m'],per_family=1,batch_size=2,max_batches_per_family=1,include_news=True))
 original=lab.news.load;append=SpreadJournal.append;sealed=[]
 def track(self,event,*a,**k):
  value=append(self,event,*a,**k)
  if event['kind']=='preparation_sealed':sealed.append(True)
  return value
 def load(*a,**k):
  value=original(*a,**k)
  return value|dict(changed=True) if changed and sealed else value
 monkeypatch.setattr(SpreadJournal,'append',track);monkeypatch.setattr(lab.news,'load',load)
 if changed:
  with pytest.raises(StateError):execute_spread(worker,job,lambda:False)
  assert not lab.output_path(job['id']).exists()
 else:
  execute_spread(worker,job,lambda:False);assert lab.output_path(job['id']).exists()

def test_cancel_after_preparation_cannot_start_a_new_signal_probe(owned,monkeypatch):
 lab,job,worker=claimed(owned);sealed=[];append=SpreadJournal.append
 def track(self,event,*a,**k):
  value=append(self,event,*a,**k)
  if event['kind']=='preparation_sealed':sealed.append(True)
  return value
 monkeypatch.setattr(SpreadJournal,'append',track)
 with pytest.raises(InterruptedError):execute_spread(worker,job,lambda:bool(sealed))
 assert lab.store.registry(job_id=job['id'])['totals']['computation_attempts']==0

def test_initial_cancel_rejects_before_preparation_or_signal_prices(owned):
 lab,job,worker=claimed(owned)
 with pytest.raises(InterruptedError):execute_spread(worker,job,lambda:True)
 assert not (lab.output_path(job['id']).parent/'spread-preparation').exists()
 assert lab.store.registry(job_id=job['id'])['totals']['computation_attempts']==0

def test_self_consistent_journal_cannot_substitute_a_different_preparation_contract(owned):
 lab,job,worker=claimed(owned);journal=SpreadJournal(lab.store,job,worker.owner)
 journal.append(dict(kind='preparation_started',contract_hash='a'*64))
 with pytest.raises(StateError,match='preparation contract changed'):execute_spread(worker,job,lambda:False)
 assert lab.store.registry(job_id=job['id'])['totals']['computation_attempts']==0

def test_manifest_changed_after_preparation_cannot_authorize_first_signal(owned,monkeypatch):
 lab,job,worker=claimed(owned);append=SpreadJournal.append
 def changed(self,event,*a,**k):
  value=append(self,event,*a,**k)
  if event['kind']=='preparation_sealed':
   p=lab.datasets_root/job['payload']['dataset_id']/'manifest.json';value=json.loads(p.read_text());value['parquet_sha256']='f'*64;p.write_text(canonical(value))
  return value
 monkeypatch.setattr(SpreadJournal,'append',changed)
 with pytest.raises(StateError,match='dataset manifest changed'):execute_spread(worker,job,lambda:False)
 assert not lab.output_path(job['id']).exists()
 assert lab.store.registry(job_id=job['id'])['totals']['computation_attempts']==0
