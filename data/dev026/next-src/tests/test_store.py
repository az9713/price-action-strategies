from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
import pytest
from backend.lab.store import Store,StateError

def test_transactional_claim_not_shared_between_workers(tmp_path):
    store=Store(tmp_path)
    job=store.create_job('experiment',{'seed':12})
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims=list(pool.map(store.claim,['one','two']))
    assert sum(c is not None for c in claims)==1
    assert next(c for c in claims if c)['id']==job['id']
    assert len([e for e in store.events(job['id']) if e['kind']=='job_claimed'])==1

def test_dead_worker_lease_recovery_preserves_checkpoint(tmp_path):
    store=Store(tmp_path);job=store.create_job('search',{'seed':42})
    store.claim('dead',lease_seconds=-1)
    with store.db() as db: db.execute('UPDATE jobs SET checkpoint=7 WHERE id=?',(job['id'],))
    recovered=store.claim('replacement')
    assert recovered['checkpoint']==7 and recovered['owner']=='replacement'
    with pytest.raises(StateError): store.finish(job['id'],'dead','completed')

def test_cancel_resume_and_stale_complete_prevented(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',{})
    store.claim('worker');store.cancel(job['id'])
    assert store.heartbeat(job['id'],'worker',progress=.5,checkpoint=2)
    assert store.finish(job['id'],'worker','completed')['status']=='canceled'
    assert store.resume(job['id'])['checkpoint']==2
    claim=store.claim('new')
    assert store.finish(job['id'],'new','completed')['status']=='completed'
    with pytest.raises(StateError): store.resume(job['id'])

def test_queued_cancel_and_reopened_store(tmp_path):
    store=Store(tmp_path);job=store.create_job('download',{})
    store.cancel(job['id'])
    assert Store(tmp_path).job(job['id'])['status']=='canceled'
    assert store.claim('worker') is None

def test_save_strategy_is_immutable_new_version(tmp_path):
    store=Store(tmp_path)
    first=store.save_strategy('A',{'family':'breakout'})
    second=store.save_strategy('B',{'family':'flip_zone'},first)
    assert first!=second and len(store.strategies())==2
    assert store.strategies()[0]['parent_id']==first

def test_invalid_state_requests(tmp_path):
    store=Store(tmp_path)
    with pytest.raises(StateError): store.create_job('trade_live',{})
    with pytest.raises(StateError): store.cancel('missing')
    with pytest.raises(StateError): store.job('missing')
