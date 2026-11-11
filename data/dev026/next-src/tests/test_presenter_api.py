"""Actual saved API/worker integration; no substitute numerical report response."""
from pathlib import Path
import json
import pytest
from backend.lab.worker import Worker
from test_api import client_lab,seed,payload


def completed(client,lab):
    data=payload(seed(lab));response=client.post('/api/experiments',json=data)
    assert response.status_code==202
    jid=response.json()['id'];Worker(lab).run_once()
    assert lab.store.job(jid)['status']=='completed'
    return jid


def test_saved_html_and_combined_export_read_no_prices_and_keep_identity(client_lab,monkeypatch):
    client,lab=client_lab;jid=completed(client,lab)
    def forbidden(*args,**kwargs):raise AssertionError('A presenter must not access raw/sealed data.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    monkeypatch.setattr(lab.guard,'access',forbidden)
    monkeypatch.setattr('backend.lab.service.load_window',forbidden)
    response=client.get(f'/api/jobs/{jid}/export/html')
    assert response.status_code==200 and response.headers['content-type'].startswith('text/html')
    assert 'attachment' in response.headers['content-disposition']
    manifest=client.get(f'/api/jobs/{jid}/export/presentation.json').json()
    assert manifest['audit']['facts_checked']>0 and len(manifest['pages'])==8
    assert [p['title'] for p in manifest['pages'][:4]]==[
        'Saved input classification','Complete instrument list','Saved instruments','Dataset fingerprints']
    assert len([p for p in manifest['pages'] if p['section']!='Data provenance'])==4
    assert {'Strategy account','Daily profit','Uncertainty'}<={p['title'] for p in manifest['pages'][4:]}
    assert 'charts' not in json.dumps(manifest) and 'ledger' not in json.dumps(manifest)
    result=client.post('/api/presentations',json={'sources':[{'job_id':jid}]}).json()
    assert result['manifest']==manifest and result['html']==response.text
    assert manifest['sources'][0]['name']==jid+'/report.json'


@pytest.mark.parametrize('suffix',['?part=99','?window=invalid','?window=discovery','?table=bos_forward'])
def test_saved_export_invalid_selection_rejects(client_lab,suffix):
    client,lab=client_lab;jid=completed(client,lab)
    assert client.get(f'/api/jobs/{jid}/export/html'+suffix).status_code==409


def test_corrupt_and_unfinished_outputs_cannot_export(client_lab):
    client,lab=client_lab;jid=completed(client,lab)
    path=lab.output_path(jid);raw=path.read_bytes();path.write_bytes(raw+b'corrupt')
    assert client.get(f'/api/jobs/{jid}/export/html').status_code==409
    response=client.post('/api/experiments',json=payload(seed(lab)))
    assert response.status_code==202
    assert client.get('/api/jobs/'+response.json()['id']+'/export/html').status_code==409


@pytest.mark.parametrize('sources',[[],[{'job_id':'../secret'}],[{'job_id':'0'*32,'part':-1}],
    [{'job_id':'0'*32,'window':'discovery'}],[{'job_id':'0'*32}]*2,[{'job_id':f'{i:032x}'} for i in range(17)]])
def test_batch_invalid_contract_and_path_reject(client_lab,sources):
    client,_=client_lab
    assert client.post('/api/presentations',json={'sources':sources}).status_code==422


def test_combined_endpoint_requires_same_origin_and_local_session(client_lab):
    client,_=client_lab
    assert client.post('/api/presentations',json={'sources':[{'job_id':'0'*32}]},headers={'X-Lab-Token':'wrong'}).status_code==403
