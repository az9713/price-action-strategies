"""Expected original metadata hashes never replace current original SQL witnesses."""
from concurrent.futures import ThreadPoolExecutor
from threading import get_ident
import json,sqlite3
import pytest
from backend.lab.config import canonical,identity
from backend.lab.store import Store,StateError
from test_trial_registry import payload


@pytest.fixture
def original_plan(tmp_path):
    store=Store(tmp_path);job=store.create_job('experiment',payload())
    store.verify_trial_plan(job['id'])
    return store,job


@pytest.mark.parametrize('field',['id','part','window','role','config_id','plan_hash','provenance'])
def test_each_immutable_original_field_is_fresh_after_warmup(original_plan,field):
    store,job=original_plan
    with store.db() as db:
        old=dict(db.execute('SELECT * FROM trial_plans WHERE job_id=?',(job['id'],)).fetchone())
        bad=old[field]+1 if field=='part' else 'changed'
        db.execute('UPDATE trial_plans SET '+field+'=? WHERE job_id=?',(bad,job['id']))
    with pytest.raises(StateError):store.verify_trial_plan(job['id'])


@pytest.mark.parametrize('fault',['payload','publication_id','coherent_row_and_anchor','frozen_metadata','invalid_payload_json'])
def test_original_metadata_and_coherent_rewrites_are_not_adopted(original_plan,fault):
    store,job=original_plan
    with store.db() as db:
        if fault=='payload':db.execute('UPDATE jobs SET payload=? WHERE id=?',(canonical(payload()|dict(seed=43)),job['id']))
        elif fault=='invalid_payload_json':db.execute("UPDATE jobs SET payload='{' WHERE id=?",(job['id'],))
        elif fault=='publication_id':
            event=db.execute("SELECT id FROM events WHERE entity_id=? AND kind='trial_plan_frozen'",(job['id'],)).fetchone()
            db.execute('UPDATE events SET id=? WHERE id=?',(event['id']+100,event['id']))
        else:
            event=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='trial_plan_frozen'",(job['id'],)).fetchone();frozen=json.loads(event['details'])
            if fault=='coherent_row_and_anchor':
                db.execute("UPDATE trial_plans SET role='coherently_changed' WHERE job_id=?",(job['id'],))
                entries=[dict(r) for r in db.execute("SELECT part,window,role,config_id,plan_hash,provenance FROM trial_plans WHERE job_id=? ORDER BY part,window",(job['id'],))]
                frozen['plan_hash']=identity(entries)
            else:frozen['added_after_original_verification']=True
            db.execute('UPDATE events SET details=? WHERE id=?',(canonical(frozen),event['id']))
    with pytest.raises((StateError,ValueError)):store.verify_trial_plan(job['id'])


def test_reordered_whitespace_and_unicode_payload_preserve_original_canonical_semantics(tmp_path):
    store=Store(tmp_path);value=payload()|dict(note='caf\u00e9 \u6e2c\u8a66')
    job=store.create_job('experiment',value);store.verify_trial_plan(job['id'])
    with store.db() as db:
        db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(dict(reversed(list(value.items()))),ensure_ascii=False,indent=2),job['id']))
    store.verify_trial_plan(job['id'])


def test_dynamic_financial_lifecycle_fields_are_not_immutable_plan_fields(original_plan):
    store,job=original_plan
    with store.db() as db:
        db.execute("UPDATE trial_plans SET state='running',attempts=1,reuses=2,note='test lifecycle' WHERE job_id=?",(job['id'],))
    store.verify_trial_plan(job['id'])


def test_cache_is_thread_isolated_and_eviction_revalidates_originals(original_plan,monkeypatch):
    store,job=original_plan;ledger=store._trials;original=ledger._verify_original;calls=[]
    def observed(*a,**k):calls.append(get_ident());return original(*a,**k)
    monkeypatch.setattr(ledger,'_verify_original',observed)
    def elsewhere():ledger.verify(job['id']);ledger.verify(job['id'])
    with ThreadPoolExecutor(max_workers=1) as pool:pool.submit(elsewhere).result(timeout=15)
    assert len(calls)==1 and calls[0]!=get_ident()
    for _ in range(65):
        child=store.create_job('experiment',payload());ledger.verify(child['id'])
    assert len(ledger.verification_proofs)<=64
    before=len(calls);ledger.verify(job['id']);assert len(calls)==before+1


def test_snapshot_failure_preserves_callers_transaction_and_does_not_leak_own_transaction(original_plan):
    store,job=original_plan
    with store.db() as db:
        assert not db.in_transaction
        store._trials.verify(job['id'],db);assert not db.in_transaction
        db.execute('BEGIN IMMEDIATE');db.execute("UPDATE trial_plans SET role='bad' WHERE job_id=?",(job['id'],))
        with pytest.raises(StateError):store._trials.verify(job['id'],db)
        assert db.in_transaction
        assert db.execute('SELECT role FROM trial_plans WHERE job_id=?',(job['id'],)).fetchone()[0]=='bad'
        db.execute('ROLLBACK')
    store.verify_trial_plan(job['id'])


def test_other_store_connection_cannot_reuse_original_plan_proof(original_plan,tmp_path):
    store,job=original_plan;other=Store(tmp_path/'other')
    with other.db() as db:
        with pytest.raises(StateError):store._trials.verify(job['id'],db)


@pytest.mark.parametrize('timeout',[True,-1,10001,.25,'250'])
def test_bounded_database_wait_is_a_strict_integer(original_plan,timeout):
    store,_=original_plan
    with pytest.raises(ValueError):
        with store.db(busy_timeout_ms=timeout):pass
