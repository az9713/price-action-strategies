"""Original final account, chronology, one-time access and public read faults."""
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.lab import service
from backend.lab.api import create_app
from backend.lab.store import StateError
from backend.lab.worker import Worker
from backend.lab import research_funnel_final as flow

spec=importlib.util.spec_from_file_location('final_boundary_authored_qualification',Path(__file__).with_name('research-owned-qualification-boundaries.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
originals=fixtures.originals;clone_authored=fixtures.clone_authored


@pytest.fixture(scope='module')
def finals(originals,tmp_path_factory):
    root=tmp_path_factory.mktemp('authored-two-instrument-final');lab=clone_authored(originals['complete'],root/'source')
    job=flow.create_final(lab,originals['study_id']);ready=clone_authored(lab,root/'ready')
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(service,'generate_signals',lambda *a,**k:[])
        assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
    return dict(complete=lab,ready=ready,study_id=originals['study_id'],job_id=job['id'],qualification_job_id=originals['job_id'])


def move_event(lab,db,entity,kind,*,window=None):
    query='SELECT id,details FROM events WHERE entity_id=? AND kind=?';args=[entity,kind]
    if window is not None:query+=" AND json_extract(details,'$.window')=?";args.append(window)
    row=db.execute(query+' ORDER BY id LIMIT 1',args).fetchone();assert row is not None
    db.execute('DELETE FROM events WHERE id=?',(row['id'],));lab.store.event(kind,entity,json.loads(row['details']),db)


@pytest.mark.parametrize('fault',['account_checkpoint_after_result','consumption_after_accounts','reservation_after_consumption'])
def test_original_final_event_chronology_cannot_be_rewritten_after_computation(finals,tmp_path,fault):
    lab=clone_authored(finals['complete'],tmp_path);jid=finals['job_id'];sid=finals['study_id']
    with lab.store.db() as db:
        if fault=='account_checkpoint_after_result':move_event(lab,db,jid,'trial_checkpoint_saved',window='primary_final')
        elif fault=='consumption_after_accounts':move_event(lab,db,sid,'final_unlock_consumed')
        else:move_event(lab,db,sid,'funnel_final_reserved')
    with pytest.raises(StateError):flow.inspect_final(lab,jid)


@contextmanager
def client_for(lab):
    app=create_app(lab.root,run_worker=False)
    with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
        client.headers['X-Lab-Token']=client.get('/api/session').json()['token'];yield client


def test_public_final_summary_and_rows_cannot_bypass_damaged_original_account(finals,tmp_path):
    lab=clone_authored(finals['complete'],tmp_path);jid=finals['job_id']
    with client_for(lab) as client:
        base='/api/jobs/'+jid
        assert client.get(base+'/result-summary').status_code==200
        assert client.get(base+'/result-rows').status_code==200
        path,_=flow._path(lab,jid,0,'replication_final');path.write_bytes(b'changed original final account')
        assert client.get(base+'/result').status_code==409
        assert client.get(base+'/result-summary').status_code==409
        assert client.get(base+'/result-rows').status_code==409


def test_public_final_report_reads_explicit_original_instrument_without_new_prices(finals,tmp_path,monkeypatch):
    lab=clone_authored(finals['complete'],tmp_path);jid=finals['job_id']
    def forbidden(*args,**kwargs):raise AssertionError('Saved final report access must not reopen final prices.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    with client_for(lab) as client:
        for key in ['primary_final','replication_final']:
            response=client.get('/api/jobs/'+jid+'/report',params=dict(part=0,window=key))
            assert response.status_code==200,response.text
            assert response.json()==flow.read_final_account(lab,jid,0,key)
        assert client.get('/api/jobs/'+jid+'/report',params=dict(part=0,window='report')).status_code==409
