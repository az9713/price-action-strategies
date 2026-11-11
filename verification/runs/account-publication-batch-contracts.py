"""Owned original report publication batches; synthetic lifecycle, not finance capacity."""
import hashlib,json
from pathlib import Path
from threading import Event
import pytest
from backend.lab import account_checkpoints as checkpoints
from backend.lab.config import Strategy,identity
from backend.lab.data import atomic_json
from backend.lab.service import Lab,compressed_read,compressed_write
from backend.lab.store import StateError
from backend.lab.worker import Worker


def prepared(tmp_path,count=8,pad_bytes=0):
    lab=Lab(tmp_path);worker=Worker(lab)
    configs=[Strategy(family='breakout',level_age=96+i).model_dump() for i in range(count)]
    created=lab.store.create_job('search',{'configurations':configs,'authored_lifecycle_fixture':True})
    job=lab.store.claim(worker.owner);assert job['id']==created['id']
    items=[]
    for part,config in enumerate(configs):
        report={'config_id':identity(config),'fixture':'authored lifecycle report','net':part-3}
        if pad_bytes:report['padding']='x'*pad_bytes
        lab.store._trials.start(job['id'],part,'report',worker.owner)
        lab.store._trials.computed(job['id'],part,'report',worker.owner,report)
        value={'config_id':identity(config),'report':report}
        path=tmp_path/'data/jobs'/job['id']/'parts'/f'{part:06d}.json.gz'
        items.append((part,path,path.with_suffix('.sha256.json'),value,['report']))
    return lab,worker,job,items


def publish(worker,job,items,cancel=lambda:False,write=compressed_write,receipt=atomic_json):
    if hasattr(checkpoints,'publish_checkpoints'):
        return checkpoints.publish_checkpoints(worker,job,items,cancel,write,receipt)
    # Execute actual prior behavior for the retained red counterexamples;
    # absence of the proposed API must not be the only failing observation.
    return [checkpoints.publish_checkpoint(worker,job,*item,cancel,write,receipt) for item in items]


def verify_originals(lab,job,items,digests):
    assert len(digests)==len(items)
    with lab.store.db() as db:
        for item,digest in zip(items,digests):
            part,path,receipt,value,windows=item
            assert compressed_read(path)==value
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
            row=lab.store._trials.row(db,job['id'],part,'report')
            assert row['attempts']==1 and row['state']=='checkpointed'
            assert row['artifact_sha256']==digest and row['computed_sha256']==identity(value['report'])
            attempt=db.execute('SELECT * FROM trial_attempts WHERE trial_id=?',(row['id'],)).fetchone()
            assert attempt['ordinal']==1 and attempt['state']=='checkpointed' and attempt['artifact_sha256']==digest
        events=list(db.execute("SELECT kind,details FROM events WHERE entity_id=? AND kind IN ('trial_computation_started','trial_checkpoint_saved') ORDER BY id",(job['id'],)))
        selected={item[0] for item in items}
        assert len([e for e in events if json.loads(e['details'])['part'] in selected])==2*len(items)


def test_eight_original_accounts_share_only_one_fresh_writer_snapshot(tmp_path,monkeypatch):
    lab,worker,job,items=prepared(tmp_path);calls=[];original=lab.store._trials.verify
    def verify(jid,db=None):
        assert db is not None and db.in_transaction
        calls.append(jid);return original(jid,db)
    monkeypatch.setattr(lab.store._trials,'verify',verify)
    digests=publish(worker,job,items)
    assert calls==[job['id']]
    verify_originals(lab,job,items,digests)


def test_single_checkpoint_wrapper_retains_the_exact_original_api(tmp_path):
    lab,worker,job,items=prepared(tmp_path,1);item=items[0]
    digest=checkpoints.publish_checkpoint(worker,job,*item,lambda:False,compressed_write,atomic_json)
    verify_originals(lab,job,items,[digest])


def test_every_later_batch_freshly_revalidates_original_plan(tmp_path):
    lab,worker,job,items=prepared(tmp_path)
    first=publish(worker,job,items[:4]);verify_originals(lab,job,items[:4],first)
    with lab.store.db() as db:
        db.execute("UPDATE trial_plans SET config_id='changed' WHERE job_id=? AND part=7",(job['id'],))
    with pytest.raises(StateError):publish(worker,job,items[4:])
    for item,digest in zip(items[:4],first):assert hashlib.sha256(item[1].read_bytes()).hexdigest()==digest
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL",(job['id'],)).fetchone()[0]==4


@pytest.mark.parametrize('fault',['computed','attempt','start_event','config_id'])
def test_changed_last_original_cannot_certify_any_candidate_in_the_batch(tmp_path,fault):
    lab,worker,job,items=prepared(tmp_path)
    with lab.store.db() as db:
        row=lab.store._trials.row(db,job['id'],7,'report')
        if fault=='computed':db.execute("UPDATE trial_plans SET computed_sha256=? WHERE id=?",('0'*64,row['id']))
        elif fault=='attempt':db.execute("UPDATE trial_attempts SET state='running' WHERE trial_id=?",(row['id'],))
        elif fault=='start_event':
            db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_computation_started' AND json_extract(details,'$.trial_id')=?",(job['id'],row['id']))
        else:db.execute("UPDATE trial_plans SET config_id='changed' WHERE id=?",(row['id'],))
    with pytest.raises(StateError):publish(worker,job,items)
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL",(job['id'],)).fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'",(job['id'],)).fetchone()[0]==0


@pytest.mark.parametrize('after',[1,4,8])
def test_receipt_failure_rolls_back_all_original_authority_and_preserves_retry(tmp_path,after):
    lab,worker,job,items=prepared(tmp_path);calls=[]
    def fail(path,value):
        atomic_json(path,value);calls.append(path)
        if len(calls)==after:raise OSError('Authored receipt boundary')
    with pytest.raises(OSError):publish(worker,job,items,receipt=fail)
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL",(job['id'],)).fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'",(job['id'],)).fetchone()[0]==0
    verify_originals(lab,job,items,publish(worker,job,items))


@pytest.mark.parametrize('boundary',['during_private_write','during_publication','closing_publication'])
def test_cancel_refuses_entire_unit_without_original_checkpoint_events(tmp_path,boundary):
    lab,worker,job,items=prepared(tmp_path);stop=Event();calls=[]
    def write(path,value):
        compressed_write(path,value);calls.append(path)
        if boundary=='during_private_write' and len(calls)==4:stop.set()
    def receipt(path,value):
        atomic_json(path,value)
        if boundary=='during_publication' or boundary=='closing_publication' and path==items[-1][2]:stop.set()
    with pytest.raises(InterruptedError):publish(worker,job,items,stop.is_set,write,receipt)
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'",(job['id'],)).fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL",(job['id'],)).fetchone()[0]==0


def test_duplicate_part_paths_and_empty_units_are_rejected_without_publication(tmp_path):
    lab,worker,job,items=prepared(tmp_path)
    for invalid in [[],[items[0],items[0]]]:
        with pytest.raises(StateError):publish(worker,job,invalid)
    assert not any(item[1].exists() for item in items)


def test_stale_owner_cannot_overwrite_an_already_committed_unit(tmp_path):
    lab,worker,job,items=prepared(tmp_path);digests=publish(worker,job,items)
    with lab.store.db() as db:db.execute("UPDATE jobs SET owner='new-owner' WHERE id=?",(job['id'],))
    with pytest.raises(StateError):publish(worker,job,items)
    for item,digest in zip(items,digests):assert hashlib.sha256(item[1].read_bytes()).hexdigest()==digest


def test_multiple_reports_above_encoded_budget_are_rejected_before_publication(tmp_path):
    lab,worker,job,items=prepared(tmp_path,2,5*1024*1024)
    with pytest.raises(StateError,match='encoded'):publish(worker,job,items)
    assert not any(item[1].exists() for item in items)


def test_one_oversized_account_retains_the_existing_single_publication_path(tmp_path):
    lab,worker,job,items=prepared(tmp_path,1,9*1024*1024)
    verify_originals(lab,job,items,publish(worker,job,items))


def test_earlier_private_candidate_is_rehashed_after_later_candidates_are_written(tmp_path):
    lab,worker,job,items=prepared(tmp_path);written=[]
    def write(path,value):
        compressed_write(path,value);written.append(path)
        if len(written)==8:written[0].write_bytes(written[0].read_bytes()+b'changed private candidate')
    with pytest.raises(StateError):publish(worker,job,items,write=write)
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL",(job['id'],)).fetchone()[0]==0


@pytest.mark.parametrize('fault',['too_many','malformed','same_path'])
def test_invalid_units_are_refused_before_writing_candidates(tmp_path,fault):
    lab,worker,job,items=prepared(tmp_path)
    if fault=='too_many':items=items+[items[0]]
    elif fault=='malformed':items=[items[0][:-1]]
    else:items=items[:-1]+[(items[-1][0],items[0][1],*items[-1][2:])]
    with pytest.raises(StateError):publish(worker,job,items)
    assert not any(item[1].exists() for item in items if len(item)>1)


def test_changed_committed_bytes_between_preflight_and_promotion_are_not_repaired(tmp_path):
    lab,worker,job,items=prepared(tmp_path);originals=publish(worker,job,items);changed=[]
    def receipt(path,value):
        atomic_json(path,value)
        if not changed:
            changed.append(1);items[-1][1].write_bytes(items[-1][1].read_bytes()+b'changed original after preflight')
    with pytest.raises(StateError,match='earlier committed'):publish(worker,job,items,receipt=receipt)
    assert hashlib.sha256(items[-1][1].read_bytes()).hexdigest()!=originals[-1]
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'",(job['id'],)).fetchone()[0]==8
        assert db.execute('SELECT SUM(reuses) FROM trial_plans WHERE job_id=?',(job['id'],)).fetchone()[0]==0


def test_real_cancel_after_private_writes_is_checked_from_the_owned_database(tmp_path):
    lab,worker,job,items=prepared(tmp_path);written=[]
    def write(path,value):
        compressed_write(path,value);written.append(path)
        if len(written)==8:lab.store.cancel(job['id'])
    with pytest.raises(InterruptedError):publish(worker,job,items,write=write)
    assert lab.store.job(job['id'])['cancel_requested']==1
    assert not any(item[1].exists() for item in items)


def test_closing_source_guard_refusal_rolls_back_all_eight_original_bindings(tmp_path,monkeypatch):
    lab,worker,job,items=prepared(tmp_path);calls=[];source=checkpoints.require_current_source
    def refused():
        calls.append(1)
        if len(calls)==3:raise StateError('Authored closing source guard refusal')
        return source()
    monkeypatch.setattr(checkpoints,'require_current_source',refused)
    with pytest.raises(StateError,match='closing source'):publish(worker,job,items)
    assert len(calls)==3 and all(item[1].exists() for item in items)
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL",(job['id'],)).fetchone()[0]==0


@pytest.mark.parametrize('field',['owner','cancel_requested'])
def test_closing_same_transaction_state_corruption_cannot_certify_a_unit(tmp_path,monkeypatch,field):
    lab,worker,job,items=prepared(tmp_path);checkpoint=lab.store._trials.checkpoint_owned
    def corrupted(db,jid,part,window,owner,report,artifact):
        result=checkpoint(db,jid,part,window,owner,report,artifact)
        if part==7:
            if field=='owner':db.execute("UPDATE jobs SET owner='injected-other-owner' WHERE id=?",(jid,))
            else:db.execute('UPDATE jobs SET cancel_requested=1 WHERE id=?',(jid,))
        return result
    monkeypatch.setattr(lab.store._trials,'checkpoint_owned',corrupted)
    with pytest.raises(StateError if field=='owner' else InterruptedError):publish(worker,job,items)
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL",(job['id'],)).fetchone()[0]==0
    state=lab.store.job(job['id']);assert state['owner']==worker.owner and state['cancel_requested']==0
