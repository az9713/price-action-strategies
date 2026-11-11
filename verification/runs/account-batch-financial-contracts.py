"""Actual original gains/losses/zeros versus the SHA-bound prior publication loop.

Signals are authored causal decisions: these tests verify publication/economic
equivalence, not detector accuracy, investment edge or market capacity.
"""
from pathlib import Path
from types import MethodType
import ast,hashlib,importlib.util,json,os
import pytest
from conftest import minute_frame
from test_reference_execution import CFG,ACCOUNT,sig
from backend.lab import service,account_checkpoints as checkpoints
from backend.lab.config import Costs,identity,canonical
from backend.lab.data import save_dataset
from backend.lab.models import Search
from backend.lab.service import Lab,compressed_read
from backend.lab.worker import Worker


def authored(frame,config,*args,**kwargs):
    mode=config.level_age%3
    if mode==2:return []
    return [sig(frame,side=1 if mode==0 else -1,at=20,name='authored-causal-batch-decision')]


def build_case(root,count):
    lab=Lab(root);day='2026-11-04';frame=minute_frame(day)
    frame.loc[21,'high']=106.
    manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',
        provider='Authored original batch publication equivalence; no market edge',corporate_actions_complete=True))
    request=Search(dataset_id=manifest['id'],name='Original batch financial equivalence',start=day,end=day,count=count,
        families=['breakout'],timeframes=['1m'],strategy=CFG,portfolio=ACCOUNT,
        costs=Costs(commission_per_share=.005,spread_bps=1,slippage_bps=1,borrow_annual=.03))
    draft=lab.create_experiment(request);lab.store.cancel(draft['id']);payload=draft['payload']
    configs=[CFG.model_copy(update={'family':'breakout','level_age':96+i}).model_dump() for i in range(count)]
    payload['configurations']=configs
    payload['sampling']=dict(attempts=count,unique=count,duplicates=0,rejected=0,seed=42,
        method='Authored prespecified complete publication fixture',proposals=[dict(attempt=i+1,status='accepted',
            config_id=identity(c),family=c['family'],timeframe=c['timeframe']) for i,c in enumerate(configs)])
    return lab,lab.store.create_job('search',payload)


def prior_worker():
    folder=Path(__file__).with_name('account-publication-batch-before')
    provenance=json.loads((folder/'provenance.json').read_text())
    for name in ['worker.py','account_checkpoints.py']:
        assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==next(
            r['sha256'] for r in provenance['files'] if r['path']=='backend/lab/'+name)
    # Single-account publication remains literally the prior algorithm.
    def publisher(raw):
        return next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name=='publish_checkpoint')
    assert ast.dump(publisher((folder/'account_checkpoints.py').read_bytes()),include_attributes=False)==ast.dump(
        publisher(Path(checkpoints.__file__).read_bytes()),include_attributes=False)
    spec=importlib.util.spec_from_file_location('backend.lab.prior_publication_worker',folder/'worker.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.Worker


def original_parts(lab,job):
    assert lab.store.job(job['id'])['status']=='completed'
    result=lab.result(job['id']);parts=[]
    assert result['count']==len(result['rows'])==len(job['payload']['configurations'])
    with lab.store.db() as db:
        trials=list(db.execute('SELECT * FROM trial_plans WHERE job_id=? ORDER BY part',(job['id'],)))
        assert len(trials)==result['count'] and all(t['state']=='completed' and t['attempts']==1 for t in trials)
        for row,trial in zip(result['rows'],trials):
            path=lab.output_path(job['id']).parent/'parts'/f"{row['part']:06d}.json.gz"
            raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
            value=compressed_read(path)
            assert digest==trial['artifact_sha256']==row['report_sha256']
            assert trial['computed_sha256']==identity(value['report'])
            assert value['payload_hash']==identity(job['payload'])
            parts.append((raw,value))
    return result,parts


@pytest.mark.parametrize('count',[8,9,16])
def test_complete_original_financial_books_are_byte_identical_to_prior_loop(tmp_path,monkeypatch,count):
    monkeypatch.setattr(service,'generate_signals',authored)
    reference,original=build_case(tmp_path/'reference',count);old=Worker(reference)
    old._many=MethodType(prior_worker()._many,old)
    assert old.run_once();before,old_parts=original_parts(reference,original)
    current,job=build_case(tmp_path/'current',count);units=[];publisher=checkpoints.publish_checkpoints
    def observed(worker,j,items,*args):
        units.append(dict(parts=[item[0] for item in items],encoded_bytes=sum(len(canonical(item[3]).encode()) for item in items)))
        return publisher(worker,j,items,*args)
    monkeypatch.setattr(checkpoints,'publish_checkpoints',observed)
    assert Worker(current).run_once();after,new_parts=original_parts(current,job)
    assert identity(original['payload'])==identity(job['payload'])
    assert before['job_id']==original['id'] and after['job_id']==job['id'] and original['id']!=job['id']
    assert old_parts==new_parts
    assert {k:v for k,v in before.items() if k!='job_id'}=={k:v for k,v in after.items() if k!='job_id'}
    assert [len(u['parts']) for u in units]==([8] if count==8 else [8,1] if count==9 else [8,8])
    assert all(u['encoded_bytes']<=checkpoints.MAX_BATCH_ENCODED_BYTES for u in units)
    profits=[p[1]['report']['metrics']['net_profit'] for p in new_parts]
    assert any(p>0 for p in profits) and any(p<0 for p in profits) and any(p==0 for p in profits)
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        Path(os.environ['PA_EVIDENCE_RUN_DIR'],f'original-financial-batch-{count}.json').write_text(json.dumps(dict(
            scope=__doc__,count=count,units=units,complete_part_bytes_equal=True,root_equal_except_verified_distinct_job_id=True,
            original_job=original['id'],current_job=job['id'],financial_attempts_per_arm=count,
            net_profits=profits,part_sha256=[hashlib.sha256(raw).hexdigest() for raw,_ in new_parts],
            market_edge_claimed=False),indent=2),encoding='utf-8')


def test_oversized_reports_flush_to_original_single_path_without_losing_accounts(tmp_path,monkeypatch):
    monkeypatch.setattr(service,'generate_signals',authored)
    reference,original=build_case(tmp_path/'reference',9);old=Worker(reference)
    old._many=MethodType(prior_worker()._many,old);assert old.run_once()
    before,old_parts=original_parts(reference,original)
    current,job=build_case(tmp_path/'current',9)
    monkeypatch.setattr(checkpoints,'MAX_BATCH_ENCODED_BYTES',1)
    def forbidden(*a,**k):raise AssertionError('Every real report is larger than the authored1-byte batching bound.')
    monkeypatch.setattr(checkpoints,'publish_checkpoints',forbidden)
    assert Worker(current).run_once();after,new_parts=original_parts(current,job)
    assert before['job_id']==original['id'] and after['job_id']==job['id'] and original['id']!=job['id']
    assert {k:v for k,v in before.items() if k!='job_id'}=={k:v for k,v in after.items() if k!='job_id'}
    assert old_parts==new_parts
