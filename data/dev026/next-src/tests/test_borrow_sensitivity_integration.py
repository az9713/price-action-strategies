"""Actual API/worker/registry/checkpoint tests, with explicit synthetic inputs."""
from copy import deepcopy
from types import SimpleNamespace
import csv
from io import StringIO
import json
import pytest
from backend.lab import models
from backend.lab.config import Costs,Strategy,identity
from backend.lab.data import DataError
from backend.lab.worker import Worker
from backend.lab.service import compressed_read
from backend.lab.research import ResearchError
from test_api import client_lab,seed,payload,study_payload
from test_random_controls import saved
from test_borrow import scenario,event
from test_reference_execution import primitive,assert_parity
from verification.reference_execution import execute


def request_for(saved):
    lab,m,request,frame=saved
    inputs={k:v for k,v in request.model_dump(mode='json').items() if k!='replicas'}
    original=Costs(**(request.costs.model_dump()|dict(borrow_annual=.2,borrow_scenario=scenario(start='2026-10-05',end='2026-10-05',events=[event('2026-10-05T13:30:00Z',rate=.4)]))))
    return models.BorrowSensitivity(**(inputs|dict(costs=original.model_dump())))


def test_actual_four_account_worker_freeze_registry_and_independent_books(saved):
    lab,m,_,frame=saved;request=request_for(saved);original=deepcopy(request.costs.model_dump())
    job=lab.create_borrow_sensitivity(request)
    registry=lab.store.registry(job_id=job['id']);assert registry['totals']['planned_occurrences']==4
    assert registry['totals']['roles']['borrow_sensitivity']==dict(occurrences=4,distinct_configurations=4)
    assert registry['totals']['computation_attempts']==0
    request.costs.borrow_scenario.name='Edited external request after freeze'
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='completed',lab.store.job(job['id'])['error']
    report=lab.report(job['id']);assert report['original_costs']==original and report['original_costs_id']==identity(original)
    assert [r['annual_rate'] for r in report['comparison_rows']]==[0,.03,.1,.3]
    assert len(report['arms'])==len(report['daily_differences'])==4
    for arm in report['arms']:
        book=lab.report(job['id'],arm['part']);assert book['trades'] and book['costs']==arm['costs']
        assert book['borrow_sensitivity']['account_id']==arm['account_id']
        expected=execute(primitive(frame),[s|dict(config_id=book['config_id']) for s in book['signals']],{book['config_id']:book['config']},book['costs'],book['portfolio'],start=book['start'],end=book['end'])
        assert_parity(SimpleNamespace(**book),expected)
    registry=lab.store.registry(job_id=job['id']);assert registry['totals']['computation_attempts']==4
    assert all(row['state']=='completed' and row['attempts']==1 for row in registry['rows'])
    assert {r['config_id'] for r in registry['rows']}=={a['account_id'] for a in report['arms']}


def test_api_fixed_rate_policy_json_csv_and_parts(client_lab):
    client,lab=client_lab;m=seed(lab);body=payload(m)
    for extra in [dict(rates=[]),dict(cost_arms=[]),dict(rate_policy='custom')]:
        assert client.post('/api/borrow-sensitivity',json=body|extra).status_code==422
    assert lab.store.jobs()==[]
    created=client.post('/api/borrow-sensitivity',json=body);assert created.status_code==202,created.text
    jid=created.json()['id'];assert len(created.json()['payload']['cost_arms'])==4
    Worker(lab).run_once();assert lab.store.job(jid)['status']=='completed',lab.store.job(jid)['error']
    report=client.get('/api/jobs/'+jid+'/report').json();assert report['report_type']=='borrow_sensitivity'
    assert all(row['no_short_trades'] and row['net_profit']==0 for row in report['comparison_rows'])
    assert client.get('/api/jobs/'+jid+'/export/json').json()==report
    rows=list(csv.DictReader(StringIO(client.get('/api/jobs/'+jid+'/export/csv').text)));assert len(rows)==4
    assert [float(r['annual_rate']) for r in rows]==[0,.03,.1,.3]
    for part in range(4):
        book=client.get('/api/jobs/'+jid+'/report',params={'part':part}).json()
        assert book['costs']['borrow_annual']==[0,.03,.1,.3][part]
        assert client.get('/api/jobs/'+jid+'/export/json',params={'part':part}).json()==book
    assert client.get('/api/jobs/'+jid+'/export/csv',params={'table':'unsupported'}).status_code==400


@pytest.mark.parametrize('fault',['borrow_scope','news_missing','news_raw','protected'])
def test_preflight_guards_reject_before_any_prices_or_job(client_lab,monkeypatch,fault):
    client,lab=client_lab;m=seed(lab);body=payload(m)
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Invalid sensitivity preflight read prices.'))
    if fault=='borrow_scope':body['costs']=Costs(borrow_scenario=scenario()).model_dump()
    elif fault=='news_missing':body['strategy']=Strategy(news='skip').model_dump()
    elif fault=='news_raw':body['news_dates']=['2026-11-02']
    else:
        lab.register_study(models.Study(**study_payload(m)));body.update(start='2026-11-05',end='2026-11-06')
    response=client.post('/api/borrow-sensitivity',json=body)
    assert response.status_code in {409,422} and lab.store.jobs()==[]


@pytest.mark.parametrize('fault',['cancel','shutdown','corrupt_part','orphan_part','payload'])
def test_actual_worker_partial_recovery_and_corruption_preserve_frozen_arms(saved,monkeypatch,fault):
    lab,m,_,frame=saved;job=lab.create_borrow_sensitivity(request_for(saved));frozen=deepcopy(job['payload'])
    worker=Worker(lab);original=worker._progress
    def interrupt(j,f,n,checkpoint=None):
        original(j,f,n,checkpoint)
        if checkpoint==1:
            if fault=='shutdown':worker.shutdown.set()
            else:lab.store.cancel(job['id'])
    monkeypatch.setattr(worker,'_progress',interrupt);worker.run_once()
    assert lab.store.job(job['id'])['status']==('queued' if fault=='shutdown' else 'canceled')
    part=lab.output_path(job['id']).parent/'parts/000000.json.gz';raw=part.read_bytes()
    if fault=='corrupt_part':part.write_bytes(raw+b'corruption')
    elif fault=='orphan_part':
        with lab.store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='borrow_sensitivity_part_saved'",(job['id'],))
    elif fault=='payload':
        bad=deepcopy(frozen);bad['cost_arms'][1]['costs']['slippage_bps']=9
        with lab.store.db() as db:db.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(bad),job['id']))
    if fault in {'corrupt_part','payload'}:monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Corrupt sensitivity evidence read prices.'))
    if fault!='shutdown':lab.store.resume(job['id'])
    Worker(lab).run_once();state=lab.store.job(job['id'])
    if fault in {'corrupt_part','payload'}:
        assert state['status']=='failed' and not lab.output_path(job['id']).exists()
    else:
        assert state['status']=='completed',state['error'];assert state['payload']==frozen
        assert part.read_bytes()==raw
        registry=lab.store.registry(job_id=job['id'])
        assert registry['totals']['computation_attempts']==(5 if fault=='orphan_part' else 4)
        assert registry['rows'][0]['reuses']==(0 if fault=='orphan_part' else 1)
        assert len(lab.report(job['id'])['arms'])==4


def test_cached_root_cannot_hide_changed_part_on_resume(saved,monkeypatch):
    lab,m,_,frame=saved;job=lab.create_borrow_sensitivity(request_for(saved));worker=Worker(lab);original=worker._progress
    def interrupt(j,f,n,checkpoint=None):
        original(j,f,n,checkpoint)
        if n=='Results saved and content-bound.':lab.store.cancel(job['id'])
    monkeypatch.setattr(worker,'_progress',interrupt);worker.run_once()
    assert lab.store.job(job['id'])['status']=='canceled' and lab.output_path(job['id']).exists()
    part=lab.output_path(job['id']).parent/'parts/000002.json.gz';part.write_bytes(part.read_bytes()+b'corrupt')
    lab.store.resume(job['id']);monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Cached part corruption read prices.'))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='failed'
