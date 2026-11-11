"""D037 bounded orchestration work and independently reconciled streamed events."""
from contextlib import contextmanager
import sqlite3
import pandas as pd
import pytest
from backend.lab import worker as worker_module
from backend.lab.config import Strategy,Costs
from backend.lab.models import Search
from backend.lab.store import Store,StateError
from backend.lab.worker import Worker
from test_research_service import lab_data,experiment
from test_reference_execution import rows,sig,run_both,assert_parity
from test_portfolio_studies import study_data,request,run


@pytest.mark.parametrize('requested',[False,True])
def test_owned_lifecycle_reads_work_when_sql_payload_access_is_denied(tmp_path,monkeypatch,requested):
    store=Store(tmp_path);job=store.create_job('download',{'large_plan':'x'*100000})
    store.claim('owner')
    if requested:store.cancel(job['id'])
    original=store.db
    @contextmanager
    def restricted(*a,**kw):
        with original(*a,**kw) as db:
            db.set_authorizer(lambda operation,table,column,*rest:
                sqlite3.SQLITE_DENY if operation==sqlite3.SQLITE_READ and table=='jobs' and column=='payload' else sqlite3.SQLITE_OK)
            yield db
    monkeypatch.setattr(store,'db',restricted)
    assert store.heartbeat(job['id'],'owner',progress=.5,note='checkpoint',checkpoint=2) is requested
    assert store.cancellation_requested(job['id'],'owner') is requested


@pytest.mark.parametrize('state',['unknown','wrong_owner','queued','completed','released'])
def test_lifecycle_cancellation_rejects_missing_or_unowned_work(tmp_path,state):
    store=Store(tmp_path);job=store.create_job('download',{})
    if state not in {'unknown','queued'}:store.claim('owner')
    if state=='completed':store.finish(job['id'],'owner','completed')
    if state=='released':store.release(job['id'],'owner')
    with pytest.raises(StateError):
        store.cancellation_requested('absent' if state=='unknown' else job['id'],'other' if state=='wrong_owner' else 'owner')


@pytest.mark.parametrize('count',[3,20])
def test_actual_search_has_bounded_full_plan_reads_and_hashes(lab_data,monkeypatch,count):
    lab,m=lab_data
    job=lab.create_experiment(Search(**experiment(m).model_dump(),count=count,timeframes=['1m']))
    full_reads=[];hashes=[];read=lab.store.job;digest=worker_module.identity
    def record_read(jid):full_reads.append(jid);return read(jid)
    def record_hash(value):
        if isinstance(value,dict) and 'configurations' in value and 'sampling' in value:hashes.append(1)
        return digest(value)
    monkeypatch.setattr(lab.store,'job',record_read);monkeypatch.setattr(worker_module,'identity',record_hash)
    assert Worker(lab).run_once()
    assert read(job['id'])['status']=='completed'
    assert len(full_reads)<=4,('Full plans were read in the per-bar/per-part control loop',len(full_reads),count)
    assert len(hashes)<=3,('Whole N-rule plan was hashed N times',len(hashes),count)
    result=lab.result(job['id']);assert result['count']==count
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND state='completed' AND attempts=1",(job['id'],)).fetchone()[0]==count


@pytest.mark.parametrize('reverse',[False,True])
def test_streamed_sparse_multisymbol_account_and_batched_row_conversion(monkeypatch,reverse):
    spy=rows(120,'SPY');qqq=rows(120,'QQQ').drop(index=[3,4,10,11]).reset_index(drop=True)
    frame=pd.concat([spy,qqq],ignore_index=True)
    if reverse:frame=frame.iloc[::-1].reset_index(drop=True)
    signals=[sig(spy,name='long_spy'),sig(qqq,side=-1,name='short_qqq')]
    calls=[];original=pd.DataFrame.itertuples
    def record(self,*a,**kw):calls.append(len(self));return original(self,*a,**kw)
    monkeypatch.setattr(pd.DataFrame,'itertuples',record)
    actual,expected=run_both(frame,signals,costs=Costs())
    assert len(expected['trades'])==2;assert_parity(actual,expected)
    assert len(calls)<=4,('Rebuilt a pandas row class/subframe per timestamp',len(calls))


@pytest.mark.parametrize('shutdown',[False,True])
def test_lost_owner_cannot_publish_a_terminal_state(lab_data,monkeypatch,shutdown):
    lab,m=lab_data;job=lab.create_experiment(experiment(m));worker=Worker(lab)
    def lose_ownership(j,cancel):
        with lab.store.db() as db:db.execute("UPDATE jobs SET owner='replacement' WHERE id=?",(j['id'],))
        if shutdown:worker.shutdown.set()
        raise InterruptedError('Ownership transferred during a computation')
    monkeypatch.setattr(worker,'_execute',lose_ownership)
    worker.run_once()
    state=lab.store.job(job['id']);assert state['owner']=='replacement' and state['status']=='running'
    assert not any(e['kind'] in {'job_failed','job_canceled','job_completed','worker_shutdown_checkpoint'} for e in lab.store.events(job['id']))


@pytest.mark.parametrize('shutdown',[False,True])
def test_lost_final_owner_preserves_consumption_and_replacement_can_finish(study_data,monkeypatch,shutdown):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];run(lab,lab.screen(sid))
    job=lab.final(sid);worker=Worker(lab)
    def transfer(*a,**kw):
        assert lab.guard.study(sid)['status']=='consumed'
        with lab.store.db() as db:db.execute("UPDATE jobs SET owner='replacement' WHERE id=?",(job['id'],))
        if shutdown:worker.shutdown.set()
        raise InterruptedError('Transfer after actual final consumption')
    monkeypatch.setattr(worker,'_evaluate',transfer);worker.run_once()
    assert lab.store.job(job['id'])['status']=='running' and lab.guard.study(sid)['status']=='consumed'
    assert not any(e['kind']=='job_failed' for e in lab.store.events(job['id']))
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed'
    assert lab.guard.study(sid)['status']=='final_complete'
    assert len([e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed'])==1
