"""Expanded bounded publication units retain every original financial account."""
from pathlib import Path
from types import MethodType
import importlib.util,json
import pytest
from backend.lab import service,account_checkpoints as checkpoints
from backend.lab.config import canonical
from backend.lab.store import StateError
from backend.lab.worker import Worker


def fixture(name):
    spec=importlib.util.spec_from_file_location('large_'+name.replace('-','_'),Path(__file__).with_name(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


financial=fixture('account-batch-financial-contracts')
publication=fixture('account-publication-batch-contracts')


@pytest.mark.parametrize('count,expected',[(64,[64]),(65,[64,1]),(128,[64,64])])
def test_complete_64_65_128_accounts_equal_original_single_publisher(tmp_path,monkeypatch,count,expected):
    monkeypatch.setattr(service,'generate_signals',financial.authored)
    reference,old_job=financial.build_case(tmp_path/'reference',count);old=Worker(reference)
    old._many=MethodType(financial.prior_worker()._many,old);assert old.run_once()
    before,old_parts=financial.original_parts(reference,old_job)
    current,job=financial.build_case(tmp_path/'current',count);units=[];publisher=checkpoints.publish_checkpoints
    def publish(worker,j,items,*args):
        assert sum(len(canonical(item[3]).encode()) for item in items)<=8*1024*1024
        units.append(len(items));return publisher(worker,j,items,*args)
    monkeypatch.setattr(checkpoints,'publish_checkpoints',publish)
    assert Worker(current).run_once();after,new_parts=financial.original_parts(current,job)
    assert units==expected and old_parts==new_parts
    assert {k:v for k,v in before.items() if k!='job_id'}=={k:v for k,v in after.items() if k!='job_id'}
    pnl=[v['report']['metrics']['net_profit'] for _,v in new_parts]
    assert any(x>0 for x in pnl) and any(x<0 for x in pnl) and any(x==0 for x in pnl)


def test_sixty_five_distinct_items_refused_before_any_write(tmp_path):
    lab,worker,job,items=publication.prepared(tmp_path,65)
    with pytest.raises(StateError,match='one to64'):publication.publish(worker,job,items)
    assert not any(item[1].exists() for item in items)


@pytest.mark.parametrize('fault',['last_computation','last_attempt','last_start','late_receipt','closing_source','closing_owner','closing_cancel','private_candidate'])
def test_full_64_unit_fault_never_certifies_a_partial_unit(tmp_path,monkeypatch,fault):
    lab,worker,job,items=publication.prepared(tmp_path,64)
    if fault in {'last_computation','last_attempt','last_start'}:
        with lab.store.db() as db:
            last=lab.store._trials.row(db,job['id'],63,'report')
            if fault=='last_computation':db.execute("UPDATE trial_plans SET computed_sha256=? WHERE id=?",('0'*64,last['id']))
            elif fault=='last_attempt':db.execute("UPDATE trial_attempts SET state='running' WHERE trial_id=?",(last['id'],))
            else:db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_computation_started' AND json_extract(details,'$.trial_id')=?",(job['id'],last['id']))
    source=checkpoints.require_current_source;checks=[]
    def check():
        checks.append(1)
        if len(checks)==3:
            if fault=='closing_source':raise StateError('Authored closing source fault')
            if fault=='closing_owner':
                # Mutate through the existing writer, avoiding an impossible second writer.
                db=connections[-1];db.execute("UPDATE jobs SET owner='other' WHERE id=?",(job['id'],))
            if fault=='closing_cancel':connections[-1].execute('UPDATE jobs SET cancel_requested=1 WHERE id=?',(job['id'],))
        return source()
    connections=[];original_owned=lab.store._trials.owned
    def owned(db,*args):connections.append(db);return original_owned(db,*args)
    monkeypatch.setattr(lab.store._trials,'owned',owned)
    monkeypatch.setattr(checkpoints,'require_current_source',check)
    receipts=[];write=publication.compressed_write;receipt=publication.atomic_json;written=[]
    def record(path,value):
        receipts.append(path)
        if fault=='late_receipt' and len(receipts)==63:raise OSError('Authored late receipt failure')
        return receipt(path,value)
    def prepare(path,value):
        write(path,value);written.append(path)
        if fault=='private_candidate' and len(written)==64:written[0].write_bytes(written[0].read_bytes()+b'corruption')
    with pytest.raises((StateError,InterruptedError,OSError)):
        publication.publish(worker,job,items,write=prepare,receipt=record)
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND artifact_sha256 IS NOT NULL',(job['id'],)).fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved'",(job['id'],)).fetchone()[0]==0


def test_second_large_unit_freshly_verifies_all_original_plan_rows(tmp_path):
    lab,worker,job,items=publication.prepared(tmp_path,128)
    digests=publication.publish(worker,job,items[:64]);publication.verify_originals(lab,job,items[:64],digests)
    with lab.store.db() as db:db.execute("UPDATE trial_plans SET config_id='changed' WHERE job_id=? AND part=127",(job['id'],))
    with pytest.raises(StateError):publication.publish(worker,job,items[64:])
    publication.verify_originals(lab,job,items[:64],digests)
