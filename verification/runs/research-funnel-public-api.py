"""Real local HTTP -> original registration -> worker -> protected final.

Authored synthetic datasets and empty signals isolate workflow/account authority;
these cases are not detector, market edge or completed random-control proof.
"""
import importlib.util
from pathlib import Path
import pytest
from backend.lab import service
from backend.lab.api import create_app
from backend.lab.config import identity
from backend.lab.models import Search
from backend.lab.service import sample_configurations
from backend.lab.research import ResearchError
from backend.lab.worker import Worker
from test_search_statistics_integration import client,headers

spec=importlib.util.spec_from_file_location('public_funnel_registration_fixtures',Path(__file__).with_name('research-funnel-registration-contracts.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
inputs=fixtures.inputs


def counts(lab):
    with lab.store.db() as db:
        return {name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ['studies','jobs','trial_plans','trial_attempts','viewed_windows','events']}


def blueprint(request,**generation):
    payload=request.model_dump(mode='json');payload.pop('configurations')
    payload['generation']=dict(mode='common_random',count=6,families=['break_of_structure'],timeframes=['1m'],**generation)
    return payload


def test_generated_original_cohort_matches_existing_seeded_sampler_and_is_price_free(inputs,monkeypatch):
    lab,request,*_=inputs
    def forbidden(*args,**kwargs):raise AssertionError('Registration cannot decode prices or execute financial accounts.')
    monkeypatch.setattr(service.Lab,'_evaluation_input',forbidden)
    payload=blueprint(request)
    expected,sampling=sample_configurations(Search(dataset_id=request.dataset_id,start=request.discovery.start,end=request.discovery.end,seed=request.seed,
        count=6,families=['break_of_structure'],timeframes=['1m'],sampling_policy={'mode':'common_random'}))
    with client(lab) as c:
        auth=headers(c)
        response=c.post('/api/funnel-studies/generated',headers=auth,json=payload)
        assert response.status_code==201,response.text
        summary=response.json();sid=summary['id']
        assert len(response.content)<49152 and summary['spec']['configuration_count']==6
        assert summary['spec']['funnel_version']==1 and summary['spec']['primary_symbol']=='SPY' and summary['spec']['replication_symbol']=='QQQ'
        stored=c.get('/api/studies/'+sid+'/inputs');assert stored.status_code==200
        original=lab.guard.study(sid)['spec']
        assert original['configurations']==expected and original['cohort_generation']['sampling']==sampling
        assert original['cohort_generation']['configuration_universe_hash']==identity(expected)
        assert original['cohort_generation']['price_or_outcome_dependent'] is False
        assert original['cohort_generation']['host_private_recipe_reproduced'] is False
        assert 'cohort_generation' in stored.text
        listing=c.get('/api/studies').json();assert listing[0]['spec']['funnel_version']==1
        before=counts(lab)
        again=c.post('/api/funnel-studies/generated',headers=auth,json=payload)
        assert again.status_code==409,again.text
        assert counts(lab)==before and lab.guard.study(sid)['spec']['configurations']==expected
    current=counts(lab)
    assert current['jobs']==current['trial_plans']==current['trial_attempts']==current['viewed_windows']==0


def test_public_frozen_registration_through_qualification_and_all_version_final(inputs,monkeypatch):
    lab,request,*_=inputs
    monkeypatch.setattr(service,'generate_signals',lambda *args,**kwargs:[])
    with client(lab) as c:
        auth=headers(c);response=c.post('/api/funnel-studies',headers=auth,json=request.model_dump(mode='json'))
        assert response.status_code==201,response.text
        sid=response.json()['id'];base='/api/studies/'+sid
        before=counts(lab);status=c.get(base+'/funnel-workflow')
        assert status.status_code==200,status.text
        assert counts(lab)==before and status.json()['qualification'] is None and status.json()['dependencies']['total']==0
        assert c.post(base+'/funnel-final',headers=auth,json={}).status_code==409
        queued=c.post(base+'/qualification',headers=auth,json={});assert queued.status_code==202,queued.text
        jid=queued.json()['id']
        assert c.post(base+'/qualification',headers=auth,json={}).json()['id']==jid
        before=counts(lab);page=c.get(base+'/funnel-workflow',params={'limit':2,'offset':1})
        assert page.status_code==200,page.text
        state=page.json();assert state['qualification_job_id']==jid and state['dependencies']['total']==5
        assert len(state['dependencies']['rows'])==2 and state['dependencies']['counts']=={'queued':5}
        assert counts(lab)==before
        assert c.post(base+'/screen',headers=auth,json={}).status_code==409
        assert c.post(base+'/final',headers=auth,json={}).status_code==409
        for _ in range(6):assert Worker(lab).run_once()
        assert lab.store.job(jid)['status']=='completed',lab.store.job(jid)['error']
        q=c.get('/api/jobs/'+jid+'/result-summary');assert q.status_code==200 and q.json()['candidate_count']==0
        reserved=c.post(base+'/funnel-final',headers=auth,json={});assert reserved.status_code==202,reserved.text
        fid=reserved.json()['id'];assert c.post(base+'/funnel-final',headers=auth,json={}).json()['id']==fid
        status=c.get(base+'/funnel-workflow').json()
        assert status['final_job_id']==fid and status['final_consumed'] is False
        assert Worker(lab).run_once() and lab.store.job(fid)['status']=='completed',lab.store.job(fid)['error']
        status=c.get(base+'/funnel-workflow');assert status.status_code==200,status.text
        assert status.json()['status']=='final_complete' and status.json()['final_consumed'] is True
        full=c.get('/api/jobs/'+fid+'/result');assert full.status_code==200,full.text
        assert len(full.json()['rows'])==2 and all(len(row['reports'])==2 and row['candidate'] is False for row in full.json()['rows'])
        before=counts(lab)
        for _ in range(2):
            assert c.get(base+'/funnel-workflow').status_code==200
            assert c.get('/api/jobs/'+fid+'/result-summary').status_code==200
        assert counts(lab)==before and Worker(lab).run_once() is False
        assert c.get('/api/jobs/'+fid+'/result-summary').json()['study_id']==sid
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==1


@pytest.mark.parametrize('mutate',[lambda p:p.update(configurations=[]),lambda p:p.update(configurations=[{}]),lambda p:p['generation'].update(count=0),
    lambda p:p['generation'].update(count=100001),lambda p:p['generation'].update(count=True),lambda p:p['generation'].update(mode='legacy'),
    lambda p:p['generation'].update(families=['unknown']),lambda p:p['generation'].update(families=['breakout','breakout']),
    lambda p:p['generation'].update(timeframes=[]),lambda p:p.update(replication_symbol='SPY'),lambda p:p.update(candidate_freeze={}),
    lambda p:p['era_two'].update(start='2026-11-02'),lambda p:p['generation'].update(include_news=True)])
def test_generated_invalid_blueprints_leave_no_partial_registration(inputs,mutate):
    lab,request,*_=inputs;payload=blueprint(request);mutate(payload);before=counts(lab)
    with client(lab) as c:
        response=c.post('/api/funnel-studies/generated',headers=headers(c),json=payload)
        assert response.status_code in {409,422},response.text
    assert counts(lab)==before


def test_grid_count_mismatch_cannot_register_partial_cohort(inputs):
    lab,request,*_=inputs;payload=blueprint(request);payload['generation'].update(mode='common_grid',count=1)
    before=counts(lab)
    with client(lab) as c:
        response=c.post('/api/funnel-studies/generated',headers=headers(c),json=payload)
        assert response.status_code==409 and 'exactly 48' in response.text,response.text
    assert counts(lab)==before


def test_public_controls_require_same_origin_and_session_and_refuse_overrides(inputs):
    lab,request,*_=inputs;payload=request.model_dump(mode='json')
    with client(lab) as c:
        before=counts(lab)
        assert c.post('/api/funnel-studies',json=payload).status_code==403
        auth=headers(c)
        assert c.post('/api/funnel-studies/generated',headers={'Origin':'http://elsewhere.invalid','X-Lab-Token':auth['X-Lab-Token']},json=blueprint(request)).status_code==403
        assert counts(lab)==before
        response=c.post('/api/funnel-studies',headers=auth,json=payload);assert response.status_code==201
        base='/api/studies/'+response.json()['id'];before=counts(lab)
        for route in ['/qualification','/funnel-final']:
            assert c.post(base+route,headers=auth,json={'minimum_trades':1}).status_code==422
        for params in [{'limit':101},{'limit':0},{'offset':-1}]:
            assert c.get(base+'/funnel-workflow',params=params).status_code==422
        assert counts(lab)==before


def test_workflow_status_refuses_changed_original_dependency_and_registration(inputs):
    lab,request,*_=inputs
    with client(lab) as c:
        auth=headers(c);response=c.post('/api/funnel-studies',headers=auth,json=request.model_dump(mode='json'));assert response.status_code==201
        base='/api/studies/'+response.json()['id']
        q=c.post(base+'/qualification',headers=auth,json={});assert q.status_code==202
        with lab.store.db() as db:db.execute('DELETE FROM funnel_dependencies WHERE parent_id=?',(q.json()['id'],))
        assert c.get(base+'/funnel-workflow').status_code==409
