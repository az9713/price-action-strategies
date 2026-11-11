"""Real local API authorization and immutable source-assumption contracts."""
import pytest
from test_api import client_lab
from conftest import minute_frame
from backend.lab import service
from backend.lab.data import save_dataset,normalize,prepare
from backend.lab.models import Experiment
from backend.lab.worker import Worker
from test_reference_execution import CFG,ZERO,ACCOUNT,sig


@pytest.fixture
def original(client_lab,monkeypatch):
    client,lab=client_lab;frame=minute_frame('2026-11-04')
    manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='API original source fixture',corporate_actions_complete=True))
    signal=sig(prepare(normalize(frame)[0]),at=20)
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[signal])
    parent=lab.create_experiment(Experiment(dataset_id=manifest['id'],start='2026-11-04',end='2026-11-04',strategy=CFG,costs=ZERO,portfolio=ACCOUNT))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
    return client,lab,parent


def test_trade_twin_continuation_route_is_implemented(original):
    client,lab,parent=original
    response=client.post('/api/jobs/'+parent['id']+'/trade-twins',json={'part':0})
    assert response.status_code==202,response.text
    child=response.json();saved=lab.store.job(child['id'])
    assert saved['kind']=='trade_twins' and saved['payload']['twin_parent']['job_id']==parent['id']
    assert saved['payload']['twin_protocol']['sets_per_policy']==10000
    assert client.post('/api/jobs/'+parent['id']+'/trade-twins',json={'part':0}).json()['id']==child['id']


@pytest.mark.parametrize('body',[{'part':True},{'part':0.0},{'part':-1},{'part':'0'},{'part':0,'seed':7},{'part':0,'sets':1},{'part':0,'costs':{}},{'part':0,'strategy':{}}])
def test_caller_cannot_override_source_or_weaken_workload(original,body):
    client,lab,parent=original
    response=client.post('/api/jobs/'+parent['id']+'/trade-twins',json=body)
    assert response.status_code==422,response.text
    with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='trade_twins'").fetchone()[0]==0


@pytest.mark.parametrize('headers',[{'Origin':'http://evil.test'},{'X-Lab-Token':'wrong'},{'Sec-Fetch-Site':'cross-site'}])
def test_trade_twin_creation_obeys_existing_local_session_boundary(original,headers):
    client,lab,parent=original
    assert client.post('/api/jobs/'+parent['id']+'/trade-twins',json={'part':0},headers=headers).status_code==403
    with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='trade_twins'").fetchone()[0]==0
