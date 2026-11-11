"""Actual computed accounts and original checkpoint authority under faults."""
import gzip,hashlib,importlib.util,json
from pathlib import Path
import pytest
from backend.lab import service,worker as workers
from backend.lab import account_checkpoints as checkpoints
from backend.lab.config import identity
from backend.lab.research_funnel_arms import queue_arms
from backend.lab.store import StateError
from backend.lab.worker import Worker

spec=importlib.util.spec_from_file_location('checkpoint_original_fixture',Path(__file__).with_name('research-funnel-arm-contracts.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
inputs=fixture.inputs;registration=fixture.registration;planned=fixture.planned


@pytest.fixture
def computed(planned,monkeypatch):
    lab,study=planned;queue_arms(lab,study['id']);worker=Worker(lab);job=lab.store.claim(worker.owner);p=job['payload']
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    configuration=p['configurations'][0]
    def calculate():
        report=worker._evaluate(p,configuration,p['start'],p['end'],lambda:False,p['study_id'])
        report['research_arm_context']=p['funnel_arm'];return report
    report=worker._trial(job,0,'report',calculate)
    assert report['trades']==[] and report['metrics']['net_profit']==0
    context=dict(config_id=identity(configuration),payload_hash=identity(p),core_hash=p['core_hash'])
    value=context|dict(report=report);path=lab.output_path(job['id']).parent/'parts/000000.json.gz';receipt=path.with_suffix('.sha256.json')
    return lab,worker,job,path,receipt,context,value


def publish(item,cancel=lambda:False):
    lab,worker,job,path,receipt,context,value=item
    return checkpoints.publish_checkpoint(worker,job,0,path,receipt,value,['report'],cancel,workers.compressed_write,workers.atomic_json)


@pytest.fixture
def committed(computed):
    digest=publish(computed);lab,worker,job,path,receipt,context,value=computed
    loaded,windows,actual=checkpoints.load_checkpoint(lab,job['id'],0,path,receipt,context,['report'])
    assert loaded==value and windows=={'report'} and actual==digest
    return computed


@pytest.mark.parametrize('fault',['missing_file','missing_attempt','wrong_digest','wrong_receipt','oversized_receipt','wrong_context','bad_gzip','bad_receipt_json','bad_object','missing_original_checkpoint'])
def test_committed_checkpoint_corruption_cannot_be_recomputed_or_adopted(committed,fault):
    lab,worker,job,path,receipt,context,value=committed;jid=job['id']
    if fault=='missing_file':path.unlink()
    elif fault in {'missing_attempt','wrong_digest','missing_original_checkpoint'}:
        with lab.store.db() as db:
            trial=db.execute('SELECT id FROM trial_plans WHERE job_id=? AND part=0',(jid,)).fetchone()[0]
            if fault=='missing_attempt':db.execute('DELETE FROM trial_attempts WHERE trial_id=?',(trial,))
            elif fault=='wrong_digest':db.execute('UPDATE trial_plans SET artifact_sha256=? WHERE id=?',('0'*64,trial))
            else:db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved' AND json_extract(details,'$.trial_id')=?",(jid,trial))
    elif fault=='wrong_receipt':receipt.write_text(json.dumps(dict(sha256='0'*64)),encoding='utf-8')
    elif fault=='oversized_receipt':receipt.write_text('x'*4097,encoding='utf-8')
    elif fault=='wrong_context':context=context|dict(config_id='0'*64)
    elif fault in {'bad_gzip','bad_object'}:
        path.write_bytes(b'not gzip' if fault=='bad_gzip' else gzip.compress(b'[]',mtime=0))
        receipt.write_text(json.dumps(dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest())),encoding='utf-8')
    else:receipt.write_text('{',encoding='utf-8')
    with pytest.raises(StateError):checkpoints.load_checkpoint(lab,jid,0,path,receipt,context,['report'])


def test_missing_sidecar_is_repaired_only_from_original_committed_evidence(committed):
    lab,worker,job,path,receipt,context,value=committed;original=path.read_bytes();receipt.unlink()
    loaded,digest=checkpoints.reuse_checkpoint(worker,job,0,path,receipt,context,['report'],lambda:False)
    assert loaded==value and path.read_bytes()==original and json.loads(receipt.read_text())==dict(sha256=digest)
    with lab.store.db() as db:
        assert db.execute('SELECT attempts FROM trial_plans WHERE job_id=? AND part=0',(job['id'],)).fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='account_receipt_restored'",(job['id'],)).fetchone()[0]==1


@pytest.mark.parametrize('fault',['no_computation','missing_start','early_stop','closing_stop'])
def test_publication_requires_actual_computation_start_and_live_control(computed,fault):
    lab,worker,job,path,receipt,context,value=computed;calls=[]
    if fault in {'no_computation','missing_start'}:
        with lab.store.db() as db:
            if fault=='no_computation':db.execute("UPDATE trial_plans SET state='planned',computed_sha256=NULL WHERE job_id=? AND part=0",(job['id'],))
            else:db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_computation_started' AND json_extract(details,'$.part')=0",(job['id'],))
    def cancel():calls.append(True);return fault=='early_stop' or fault=='closing_stop' and len(calls)==2
    with pytest.raises(InterruptedError if fault.endswith('stop') else StateError):publish(computed,cancel)
    assert not path.exists() and not receipt.exists()


def test_different_uncommitted_bytes_are_preserved_while_actual_account_is_published(computed):
    lab,worker,job,path,receipt,context,value=computed;path.parent.mkdir(parents=True,exist_ok=True)
    orphan=gzip.compress(b'{"not_original_evidence":true}',mtime=0);path.write_bytes(orphan)
    digest=publish(computed)
    assert any(p.read_bytes()==orphan for p in path.parent.glob('orphan-part-*.json.gz'))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    assert checkpoints.load_checkpoint(lab,job['id'],0,path,receipt,context,['report'])[1]=={'report'}


def test_publisher_cannot_silently_repair_changed_original_committed_bytes(committed):
    lab,worker,job,path,receipt,context,value=committed;path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(StateError,match='earlier committed'):publish(committed)


def test_reuse_refuses_uncommitted_output_and_observes_closing_controls(computed):
    lab,worker,job,path,receipt,context,value=computed
    with pytest.raises(StateError,match='Only original'):checkpoints.reuse_checkpoint(worker,job,0,path,receipt,context,['report'],lambda:False)
    publish(computed)
    with pytest.raises(InterruptedError):checkpoints.reuse_checkpoint(worker,job,0,path,receipt,context,['report'],lambda:True)


def test_original_bytes_are_rechecked_between_load_and_owned_reuse(committed,monkeypatch):
    lab,worker,job,path,receipt,context,value=committed;load=checkpoints.load_checkpoint
    def changed(*args,**kwargs):
        result=load(*args,**kwargs);path.write_bytes(path.read_bytes()+b'changed-after-load');return result
    monkeypatch.setattr(checkpoints,'load_checkpoint',changed)
    with pytest.raises(StateError,match='changed before'):checkpoints.reuse_checkpoint(worker,job,0,path,receipt,context,['report'],lambda:False)


def test_malformed_original_checkpoint_event_is_not_ignored(computed):
    lab,worker,job,*_=computed
    with lab.store.db() as db:db.execute("INSERT INTO events(at,kind,entity_id,details) VALUES(0,'trial_checkpoint_saved',?,'{')",(job['id'],))
    with pytest.raises(StateError,match='malformed'):checkpoints.preflight(lab,job['id'])
