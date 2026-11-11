"""Actual API/frozen input/export projection with separate source-value rereading."""
from copy import deepcopy
import json
import pytest
from fastapi.testclient import TestClient
from backend.lab.api import create_app
from backend.lab.models import Study
from backend.lab.research import ResearchError
from backend.lab.data import DataError
from backend.lab.presenter import build_deck
from backend.lab.presentation_audit import audit_deck
from backend.lab.worker import Worker
from test_portfolio_studies import study_data,request,run,DAYS,CONFIGS


def test_actual_api_joint_screen_final_exports_and_all_frozen_rule_facts(study_data,monkeypatch):
    lab,m,_=study_data;app=create_app(lab.root,run_worker=False)
    with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',1)) as client:
        client.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':client.get('/api/session').json()['token']})
        response=client.post('/api/studies',json=request(m).model_dump(mode='json'));assert response.status_code==201,response.text
        sid=response.json()['id'];screen=client.post('/api/studies/'+sid+'/screen');assert screen.status_code==202
        assert client.post('/api/studies/'+sid+'/screen').status_code==409
        Worker(app.state.lab).run_once();assert client.get('/api/studies').json()[0]['status']=='screened'
        jid=screen.json()['id'];selection=client.get('/api/jobs/'+jid+'/result').json()
        assert selection['rows'][0]['config'] is None and len(selection['rows'][0]['configurations'])==2
        exported=client.get('/api/jobs/'+jid+'/export/presentation.json');assert exported.status_code==200,exported.text
        final=client.post('/api/studies/'+sid+'/final');assert final.status_code==202
        assert client.post('/api/studies/'+sid+'/final').status_code==409
        Worker(app.state.lab).run_once();assert client.get('/api/studies').json()[0]['status']=='final_complete'
        final_id=final.json()['id']
        # Exports/inspection must survive loss of the raw loader after completion.
        monkeypatch.setattr(app.state.lab,'_evaluation_input',lambda *a,**k:pytest.fail('Saved final inspection read raw prices.'))
        for job,window in [(jid,'discovery'),(jid,'validation'),(final_id,'report')]:
            params={'part':0,'window':window};saved=client.get('/api/jobs/'+job+'/export/json',params=params);assert saved.status_code==200
            report=saved.json();assert report['study_context']['study_id']==sid and report['study_context']['study_mode']=='portfolio'
            assert len(report['configurations'])==2 and len(report['chart_sets'])==2
            csv=client.get('/api/jobs/'+job+'/export/csv',params=params);assert csv.status_code==200 and 'strategy_id' in csv.text
            response=client.get('/api/jobs/'+job+'/export/presentation.json',params=params);assert response.status_code==200,response.text
            deck=response.json();source=deck['sources'][0]['name'];assert audit_deck({source:saved.content},deck)['facts_checked']==len(deck['facts'])
            paths={tuple(f['path']) for f in deck['facts'].values()}
            assert ('study_context','phase') in paths and ('study_context','selection_unit_id') in paths
            for i,member in enumerate(report['configurations']):
                assert ('configurations',i,'config_id') in paths
                for key in member['config']:assert ('configurations',i,'config',key) in paths
            assert all(len(p['notes'])<=3 for p in deck['pages'])
            assert client.get('/api/jobs/'+job+'/export/html',params=params).status_code==200
        assert client.get('/api/datasets/'+m['id']+'/preview',params={'symbol':'SPY','start':DAYS[4],'end':DAYS[5]}).status_code==409
        assert client.post('/api/studies/'+sid+'/final').status_code==409


@pytest.mark.parametrize('phase,fault',[(phase,fault) for phase in ['screen','final'] for fault in ['engine','dataset','registration']]+[('final','candidate_event'),('final','candidate_hash_consistent')])
def test_original_inputs_and_candidate_events_guard_queued_or_new_work_before_prices(study_data,monkeypatch,phase,fault):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id']
    if phase=='final':run(lab,lab.screen(sid))
    spec=lab.guard.study(sid)['spec']
    if fault=='engine':monkeypatch.setattr('backend.lab.service.core_hash',lambda:'changed')
    elif fault=='dataset':
        path=lab.datasets_root/m['id']/'manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'));manifest['metadata']['source']='Changed after registration';path.write_text(json.dumps(manifest),encoding='utf-8')
    elif fault in {'registration','candidate_event'}:
        kind='study_registered' if fault=='registration' else 'candidates_frozen'
        with lab.store.db() as db:db.execute('DELETE FROM events WHERE entity_id=? AND kind=?',(sid,kind))
    else:
        from backend.lab.config import identity
        spec['candidates']=[spec['configurations'][:1]];spec['candidate_hash']=identity(spec['candidates'])
        with lab.store.db() as db:db.execute('UPDATE studies SET spec=? WHERE id=?',(json.dumps(spec),sid))
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Changed frozen evidence read prices.'))
    if fault in {'candidate_event','candidate_hash_consistent'}:
        from backend.lab.store import StateError
        with pytest.raises(StateError):lab.final(sid)
        assert not lab.guard.study(sid)['spec'].get('reserved_final_job_id')
        assert not [j for j in lab.store.jobs() if j['kind']=='final']
        assert not [e for e in lab.store.events(sid) if e['kind']=='portfolio_final_reserved']
        assert not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']
    else:
        with pytest.raises((ResearchError,DataError)): (lab.screen if phase=='screen' else lab.final)(sid)


@pytest.mark.parametrize('fault',['candidate_event','candidate_hash_consistent'])
def test_already_reserved_final_rechecks_candidate_evidence_before_prices(study_data,monkeypatch,fault):
    lab,m,_=study_data;sid=lab.register_study(request(m))['id'];run(lab,lab.screen(sid))
    job=lab.final(sid);spec=lab.guard.study(sid)['spec']
    with lab.store.db() as db:
        if fault=='candidate_event':db.execute("DELETE FROM events WHERE entity_id=? AND kind='candidates_frozen'",(sid,))
        else:
            from backend.lab.config import identity
            spec['candidates']=[spec['configurations'][:1]];spec['candidate_hash']=identity(spec['candidates'])
            db.execute('UPDATE studies SET spec=? WHERE id=?',(json.dumps(spec),sid))
    monkeypatch.setattr(lab,'_evaluation_input',lambda *a,**k:pytest.fail('Queued final with changed evidence read prices.'))
    Worker(lab).run_once();assert lab.store.job(job['id'])['status']=='failed'
    assert not [e for e in lab.store.events(sid) if e['kind']=='final_unlock_consumed']


def test_mutated_request_instance_is_revalidated_before_registration(study_data):
    lab,m,_=study_data;value=request(m);value.configurations.append(value.configurations[0])
    with pytest.raises(ValueError):lab.register_study(value)
    assert lab.guard.studies()==[]


@pytest.mark.parametrize('candidates',[[],[{'target':'2R'}]])
def test_independent_candidate_membership_and_empty_final_cannot_bypass_frozen_events(study_data,candidates):
    lab,m,_=study_data;sid=lab.register_study(request(m,mode='independent'))['id']
    if candidates:
        with pytest.raises(ResearchError):lab.guard.screened(sid,'not-registered-rule',candidates)
    else:
        lab.guard.screened(sid,'explicit-no-candidates',[])
        with pytest.raises(ResearchError):lab.guard.begin_final(sid,'not-a-final-job',m)
