"""Original parent authority after valid byte rehashes and internal handoff boundaries."""
import gzip,hashlib,json
import pytest
from backend.lab.config import canonical,identity
from backend.lab.store import StateError
from backend.lab.worker import Worker
from backend.lab import spread_accounts
from test_spread_probe import owned
from test_spread_account_handoff import qualified

@pytest.mark.parametrize('field',['spread_selection','selection_manifest','context','numerical_source','selection_manifest_hash'])
def test_rehashed_parent_root_cannot_change_original_qualification_facts(owned,field):
 lab,parent,result=qualified(owned);p=lab.output_path(parent['id']);value=json.loads(gzip.decompress(p.read_bytes()))
 if field=='spread_selection':value[field]['scope']='invented completed scope'
 elif field=='selection_manifest':value[field]['minimum_signals']=41
 elif field=='context':value[field]['primary_symbol']='QQQ'
 elif field=='selection_manifest_hash':value[field]='f'*64
 else:value['core_hash']='a'*64
 raw=gzip.compress(canonical(value).encode(),mtime=0);p.write_bytes(raw);lab.store.event('result_saved',parent['id'],dict(sha256=hashlib.sha256(raw).hexdigest()))
 with pytest.raises(StateError):lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==0

def test_missing_original_signal_fails_without_requalification(owned,monkeypatch):
 lab,parent,result=qualified(owned);next((lab.output_path(parent['id']).parent/'spread-signals').glob('*.gz')).unlink()
 def forbidden(*a,**k):raise AssertionError('Missing original signal triggered requalification')
 monkeypatch.setattr(lab,'spread_signal_probe',forbidden)
 with pytest.raises(StateError):lab.create_spread_accounts(parent['id'])

def test_cancellation_while_reading_original_parent_does_not_create_an_account_job(owned):
 lab,parent,result=qualified(owned)
 with pytest.raises(InterruptedError):spread_accounts.parent(lab,parent['id'],lambda:True)
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==0

def test_continuation_never_accepts_a_new_event_or_probe_from_the_replay_interface(owned,monkeypatch):
 lab,parent,result=qualified(owned)
 def changed(plan,context,probe,record,**kwargs):record(dict(kind='new_uncommitted_event'))
 monkeypatch.setattr(spread_accounts,'select',changed)
 with pytest.raises(StateError,match='no new qualification'):lab.create_spread_accounts(parent['id'])

@pytest.mark.parametrize('fault',['changed_payload','deleted_link','changed_event'])
def test_worker_handoff_boundary_rejects_changed_child_inputs_or_link(owned,monkeypatch,fault):
 lab,parent,result=qualified(owned);child=lab.create_spread_accounts(parent['id'])
 if fault=='changed_payload':
  changed=child|dict(payload=child['payload']|dict(costs=child['payload']['costs']|dict(borrow_annual=0)))
  with pytest.raises(StateError):spread_accounts.verify_child(lab,changed)
  return
 with lab.store.db() as db:
  if fault=='deleted_link':db.execute('DELETE FROM spread_account_links WHERE parent_id=?',(parent['id'],))
  else:db.execute("UPDATE events SET details='{}' WHERE entity_id=? AND kind='spread_accounts_frozen'",(parent['id'],))
 with pytest.raises(StateError,match='original atomic continuation link'):spread_accounts.verify_child(lab,child)
 def forbidden(*a,**k):raise AssertionError('Changed original link reached P&L')
 monkeypatch.setattr('backend.lab.service.simulate',forbidden);assert Worker(lab).run_once()
 assert lab.store.job(child['id'])['status']=='failed' and lab.store.registry(job_id=child['id'])['totals']['computation_attempts']==0

def test_explicit_news_parent_is_inherited_and_unavailable_calendar_blocks_accounts(owned):
 from backend.lab.news import NewsCalendar
 lab,m,context,cfg=owned;calendar=lab.news.save(NewsCalendar(name='Synthetic account lineage news',start='2026-10-05',end='2026-10-30',mode='synthetic',complete=True,events=[]))
 lab,parent,result=qualified(owned,news_calendar_id=calendar['id'],settings=dict(families=['break_of_structure'],timeframes=['1m'],per_family=1,batch_size=40,max_batches_per_family=4,include_news=True))
 assert result['spread_selection']['complete'];child=lab.create_spread_accounts(parent['id'])
 assert child['payload']['news_calendar_id']==calendar['id'] and child['payload']['news_calendar']==calendar
 lab.news.calendar_path(calendar['id']).unlink();assert Worker(lab).run_once()
 assert lab.store.job(child['id'])['status']=='failed' and lab.store.registry(job_id=child['id'])['totals']['computation_attempts']==0

def test_valid_manifest_identity_with_changed_source_fingerprint_blocks_continuation(owned):
 lab,parent,result=qualified(owned);p=lab.datasets_root/parent['payload']['dataset_id']/'manifest.json';value=json.loads(p.read_text());value['parquet_sha256']='f'*64;p.write_text(canonical(value))
 with pytest.raises(StateError,match='source manifest changed'):lab.create_spread_accounts(parent['id'])

def test_decoded_signal_content_is_checked_against_original_byte_and_context_binding(owned,monkeypatch):
 lab,parent,result=qualified(owned);decompress=gzip.decompress
 def mismatched(raw):
  decoded=decompress(raw);value=json.loads(decoded)
  if isinstance(value,dict) and 'signal_count' in value:value['context']=value['context']|dict(primary_symbol='QQQ');return canonical(value).encode()
  return decoded
 monkeypatch.setattr(gzip,'decompress',mismatched)
 with pytest.raises(StateError,match='primary signal evidence changed'):lab.create_spread_accounts(parent['id'])

def test_parent_root_changed_during_replay_is_rechecked_before_child_freeze(owned,monkeypatch):
 lab,parent,result=qualified(owned);select=spread_accounts.select
 def changed(*a,**k):
  replayed=select(*a,**k);p=lab.output_path(parent['id']);value=json.loads(gzip.decompress(p.read_bytes()));value['scope']='changed during verification'
  raw=gzip.compress(canonical(value).encode(),mtime=0);p.write_bytes(raw);lab.store.event('result_saved',parent['id'],dict(sha256=hashlib.sha256(raw).hexdigest()));return replayed
 monkeypatch.setattr(spread_accounts,'select',changed)
 with pytest.raises(StateError,match='changed during continuation'):lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==0

def test_calendar_date_validation_cannot_replace_the_original_news_identity_check(owned,monkeypatch):
 from backend.lab.news import NewsCalendar
 lab,m,context,cfg=owned;calendar=lab.news.save(NewsCalendar(name='Synthetic frozen-calendar identity boundary',start='2026-10-05',end='2026-10-30',mode='synthetic',complete=True,events=[]))
 lab,parent,result=qualified(owned,news_calendar_id=calendar['id'],settings=dict(families=['break_of_structure'],timeframes=['1m'],per_family=1,batch_size=40,max_batches_per_family=4,include_news=True))
 assert result['spread_selection']['complete']
 # Isolate independent identity verification from the calendar coverage adapter:
 # even an adapter accepting the dates cannot authorize different calendar facts.
 monkeypatch.setattr(lab,'news_input',lambda *a,**k:(None,calendar))
 monkeypatch.setattr(lab.news,'load',lambda *a,**k:calendar|dict(invented_fact=True))
 with pytest.raises(StateError,match='news calendar changed'):lab.create_spread_accounts(parent['id'])
 with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='spread_accounts'").fetchone()[0]==0
