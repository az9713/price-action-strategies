"""Real numerical buffer overflow and noncontiguous committed-account reuse."""
from pathlib import Path
import hashlib,importlib.util
from types import MethodType
from backend.lab import service,account_checkpoints as checkpoints
from backend.lab.config import canonical,identity
from backend.lab.research import core_hash
from backend.lab.service import compressed_write
from backend.lab.data import atomic_json
from backend.lab.worker import Worker

spec=importlib.util.spec_from_file_location('batch_buffer_financial_fixture',Path(__file__).with_name('account-batch-financial-contracts.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


def same_results(before,after,old_parts,new_parts):
    assert before['job_id']!=after['job_id']
    assert {k:v for k,v in before.items() if k!='job_id'}=={k:v for k,v in after.items() if k!='job_id'}
    assert old_parts==new_parts


def test_real_encoded_limit_flushes_pending_reports_before_eight_accounts(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'generate_signals',fixture.authored)
    reference,original=fixture.build_case(tmp_path/'reference',9);old=Worker(reference)
    old._many=MethodType(fixture.prior_worker()._many,old);assert old.run_once()
    before,old_parts=fixture.original_parts(reference,original)
    bound=max(len(canonical(value).encode()) for _,value in old_parts)
    current,job=fixture.build_case(tmp_path/'current',9);units=[];publish=checkpoints.publish_checkpoints
    monkeypatch.setattr(checkpoints,'MAX_BATCH_ENCODED_BYTES',bound)
    def observed(worker,j,items,*args):
        encoded=sum(len(canonical(item[3]).encode()) for item in items)
        assert encoded<=bound;units.append([item[0] for item in items])
        return publish(worker,j,items,*args)
    monkeypatch.setattr(checkpoints,'publish_checkpoints',observed)
    assert Worker(current).run_once();after,new_parts=fixture.original_parts(current,job)
    same_results(before,after,old_parts,new_parts)
    assert [part for unit in units for part in unit]==list(range(9))
    assert len(units)>2 and all(len(unit)<8 for unit in units)


def test_pending_accounts_flush_before_reusing_a_genuine_later_original(tmp_path,monkeypatch):
    calls=[]
    def authored(frame,config,*a,**k):calls.append(config.level_age);return fixture.authored(frame,config,*a,**k)
    monkeypatch.setattr(service,'generate_signals',authored)
    lab,job=fixture.build_case(tmp_path/'current',9);worker=Worker(lab)
    assert lab.store.claim(worker.owner)['id']==job['id'];p=job['payload'];config=p['configurations'][1]
    report=worker._trial(job,1,'report',lambda:worker._evaluate(p,config,p['start'],p['end'],lambda:False))
    value=dict(config_id=identity(config),payload_hash=identity(p),core_hash=core_hash(),report=report)
    path=lab.output_path(job['id']).parent/'parts/000001.json.gz';receipt=path.with_suffix('.sha256.json')
    original_digest=checkpoints.publish_checkpoint(worker,job,1,path,receipt,value,['report'],lambda:False,compressed_write,atomic_json)
    lab.store.release(job['id'],worker.owner);units=[];publish=checkpoints.publish_checkpoints
    def observed(w,j,items,*args):
        units.append([item[0] for item in items]);return publish(w,j,items,*args)
    monkeypatch.setattr(checkpoints,'publish_checkpoints',observed)
    assert worker.run_once();after,new_parts=fixture.original_parts(lab,job)
    assert calls==[97,96,*range(98,105)]
    assert units==[[0],list(range(2,9))]
    assert hashlib.sha256(path.read_bytes()).hexdigest()==original_digest
    with lab.store.db() as db:
        assert db.execute('SELECT reuses FROM trial_plans WHERE job_id=? AND part=1',(job['id'],)).fetchone()[0]==1
    reference,original=fixture.build_case(tmp_path/'reference',9)
    monkeypatch.setattr(service,'generate_signals',fixture.authored)
    assert Worker(reference).run_once();before,old_parts=fixture.original_parts(reference,original)
    same_results(before,after,old_parts,new_parts)
