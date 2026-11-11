"""Family workflow's actual loopback routes and complete bounded pages."""
import csv,io,json
import pandas as pd
import pytest
from test_api import client_lab
from conftest import minute_frame
from backend.lab import service
from backend.lab.data import save_dataset
from backend.lab.models import Search
from backend.lab.worker import Worker


@pytest.fixture
def original_api(client_lab,monkeypatch):
    client,lab=client_lab
    frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04']],ignore_index=True)
    manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Family API authority fixture',corporate_actions_complete=True))
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    parent=lab.create_experiment(Search(dataset_id=manifest['id'],start='2026-11-02',end='2026-11-04',count=3,families=['change_of_character'],timeframes=['1m']))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
    return client,lab,parent


def test_actual_family_routes_complete_pages_reload_and_full_exports(original_api):
    client,lab,parent=original_api;base='/api/jobs/'+parent['id']+'/family-analyses'
    response=client.post(base,json=dict(family='change_of_character'));assert response.status_code==202,response.text
    child=response.json();jid=child['id'];url='/api/jobs/'+jid+'/family-analysis'
    assert client.post(base,json=dict(family='change_of_character')).json()['id']==jid
    assert client.get(url).status_code==409
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='completed'
    summary=client.get(url);assert summary.status_code==200,summary.text
    value=summary.json();assert value['version_count']==3 and value['marked']['gate_pass'] is False
    assert 'daily' not in value['marked'] and 'members' not in value and 'source_report_hashes' not in value
    assert len(summary.content)<16000
    members=[client.get(url+'/members',params=dict(limit=1,offset=i)).json()['rows'][0] for i in range(3)]
    assert {row['source_part'] for row in members}=={0,1,2}
    daily=client.get(url+'/daily',params=dict(convention='marked',limit=2,offset=0)).json()
    assert len(daily['rows'])==2 and daily['pagination']['total']==3
    assert client.get(url+'/daily',params=dict(convention='marked',limit=2,offset=2)).json()['rows'][0]['date']=='2026-11-04'
    assert client.get(url).json()==value
    exported=client.get(url+'/export/json');assert exported.status_code==200
    complete=exported.json();assert len(complete['rows'])==3 and len(complete['report']['marked']['daily'])==3
    table=client.get(url+'/export/csv');assert table.status_code==200
    records=list(csv.DictReader(io.StringIO(table.text)));assert len(records)==6
    assert {row['convention'] for row in records}=={'marked','realized_exit_day_compatibility'}
    assert all(row['mean_pnl_numerator']=='0' and row['mean_pnl_denominator']=='1' for row in records)


@pytest.mark.parametrize('body',[{},dict(family='invented'),dict(family=True),dict(family='change_of_character',minimum_sharpe=0),dict(family='change_of_character',members=[]),dict(family='change_of_character',costs={})])
def test_family_caller_cannot_supply_results_shrink_membership_or_weaken_threshold(original_api,body):
    client,lab,parent=original_api
    assert client.post('/api/jobs/'+parent['id']+'/family-analyses',json=body).status_code==422
    with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='family_analysis'").fetchone()[0]==0


@pytest.mark.parametrize('headers',[{'Origin':'http://evil.test'},{'X-Lab-Token':'wrong'},{'Sec-Fetch-Site':'cross-site'}])
def test_family_creation_obeys_local_session_boundary(original_api,headers):
    client,lab,parent=original_api
    assert client.post('/api/jobs/'+parent['id']+'/family-analyses',json=dict(family='change_of_character'),headers=headers).status_code==403


@pytest.mark.parametrize('suffix',['/members?limit=0','/members?limit=101','/members?offset=-1','/daily?convention=winning_only','/daily?limit=101','/daily?offset=-1'])
def test_family_pages_have_strict_bounded_public_query_contracts(original_api,suffix):
    client,lab,parent=original_api
    # Query validation precedes artifact access, even for an unknown analysis ID.
    assert client.get('/api/jobs/'+parent['id']+'/family-analysis'+suffix).status_code==422
