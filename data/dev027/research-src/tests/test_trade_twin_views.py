"""Saved-only financial evidence APIs; first real ineligible/legacy boundaries."""
import hashlib,io,json,zipfile
import pytest
from test_trade_twin_api import original
from test_api import client_lab
from backend.lab import trade_twin_jobs as jobs
from backend.lab.models import Experiment
from backend.lab.worker import Worker
from backend.lab.trade_twin_views import sets_page,repair_view,export_archive


@pytest.fixture
def empty(original,monkeypatch):
    client,lab,first=original
    monkeypatch.setattr('backend.lab.service.generate_signals',lambda *a,**k:[])
    payload=first['payload']
    parent=lab.create_experiment(Experiment(dataset_id=payload['dataset_id'],start=payload['start'],end=payload['end']))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
    child=jobs.create(lab,parent['id']);assert Worker(lab).run_once()
    assert lab.store.job(child['id'])['status']=='completed'
    return client,lab,parent,child


def fingerprints(lab,jid):
    with lab.store.db() as db:
        trials=[tuple(r) for r in db.execute('SELECT * FROM trial_plans WHERE job_id=? ORDER BY id',(jid,))]
        attempts=[tuple(r) for r in db.execute('SELECT a.* FROM trial_attempts a JOIN trial_plans p ON a.trial_id=p.id WHERE p.job_id=? ORDER BY a.id',(jid,))]
        results=[tuple(r) for r in db.execute("SELECT * FROM events WHERE entity_id=? AND kind IN ('result_saved','trial_computation_started','trial_computation_recorded','trial_checkpoint_saved') ORDER BY id",(jid,))]
    return hashlib.sha256(lab.output_path(jid).read_bytes()).hexdigest(),trials,attempts,results


def test_real_ineligible_saved_pages_repair_and_complete_zip_are_not_financial_work(empty,monkeypatch):
    client,lab,parent,child=empty;before=fingerprints(lab,child['id'])
    def forbidden(*a,**k):raise AssertionError('Saved inspection/export must perform no financial or price recomputation.')
    monkeypatch.setattr('backend.lab.trade_twin_parts.execute_twin',forbidden)
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    for policy in ['barrier_capped_elapsed_v1','fixed_elapsed_v1']:
        assert sets_page(lab,child['id'],policy)['rows']==[]
        response=client.get('/api/jobs/'+child['id']+'/trade-twins/sets',params={'policy':policy})
        assert response.status_code==200,response.text
        assert response.json()['rows']==[] and response.json()['pagination']['total']==0
    response=client.post('/api/jobs/'+child['id']+'/trade-twins/repair-view',json={})
    assert response.status_code==200,response.text
    assert response.json()['financial_recomputations']==0
    response=client.get('/api/jobs/'+child['id']+'/trade-twins/export')
    assert response.status_code==200,response.text
    assert response.headers['X-Evidence-SHA256']==hashlib.sha256(response.content).hexdigest()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.testzip() is None
        done=json.loads(archive.read('COMPLETE.json'))
        assert done['financial_occurrences']==done['unique_books']==0 and done['original_trials']==20001
        assert json.loads(archive.read('original-source-account.json'))==lab.report(parent['id'])
        assert len(archive.read('original-trials.jsonl').splitlines())==20001
        assert not any(n.startswith('original-parts/') for n in archive.namelist())
    assert before==fingerprints(lab,child['id'])
    assert not list((lab.output_path(child['id']).parent/'twins/exports').glob('*.zip'))


@pytest.mark.parametrize('query',[{'offset':'0.0'},{'offset':'true'},{'offset':'-1'},{'offset':'10001'},{'limit':'0'},{'limit':'101'},{'limit':'25.0'},{'policy':'invented'}])
def test_saved_api_page_arguments_are_strict_before_work(original,query):
    client,lab,parent=original
    response=client.get('/api/jobs/'+parent['id']+'/trade-twins/sets',params=query)
    assert response.status_code==422,response.text


def test_wrong_job_unfinished_child_and_missing_derived_view_never_create_evidence(original):
    client,lab,parent=original
    assert client.get('/api/jobs/'+parent['id']+'/trade-twins/sets').status_code==409
    child=jobs.create(lab,parent['id'])
    assert client.get('/api/jobs/'+child['id']+'/trade-twins/sets').status_code==409
    assert client.post('/api/jobs/'+child['id']+'/trade-twins/repair-view',json={}).status_code==409
    assert not any(e['kind']=='trade_twin_view_saved' for e in lab.store.events(child['id']))


def test_source_parent_cannot_be_changed_by_caller_at_repair(empty):
    client,lab,parent,child=empty
    assert client.post('/api/jobs/'+child['id']+'/trade-twins/repair-view',json={'seed':7}).status_code==422
    assert client.post('/api/jobs/'+child['id']+'/trade-twins/repair-view',json={},headers={'Origin':'http://evil.test'}).status_code==403
