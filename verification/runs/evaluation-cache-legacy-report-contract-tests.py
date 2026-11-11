"""Supplement frozen-source legacy direct-report compatibility, not a replacement for the full regression."""
from pathlib import Path
import hashlib,sys
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tests')]
import pytest
from backend.lab.worker import Worker
from test_api import client_lab,seed,payload

@pytest.fixture
def legacy(client_lab):
 client,lab=client_lab;manifest=seed(lab);created=client.post('/api/searches',json=payload(manifest)|dict(count=2,families=['break_of_structure'],timeframes=['1m']));assert created.status_code==202;jid=created.json()['id'];assert Worker(lab).run_once();assert lab.store.job_status(jid)['status']=='completed';expected=lab.report(jid,1)
 folder=lab.root/'data/jobs'/jid;originals={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in [folder/'result.json.gz',*sorted((folder/'parts').glob('*.json.gz'))]}
 with lab.store.db() as db:db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_view_saved'",(jid,))
 return client,lab,jid,expected,originals


def test_legacy_direct_part_remains_exact_without_building_a_view(legacy):
 client,lab,jid,expected,originals=legacy;response=client.get('/api/jobs/'+jid+'/report?part=1');assert response.status_code==200,response.text;assert response.json()==expected
 assert client.get('/api/jobs/'+jid+'/result-summary').json()['requires_index'] is True
 assert all(hashlib.sha256(path.read_bytes()).hexdigest()==digest for path,digest in originals.items())

@pytest.mark.parametrize('fault',['unknown_part','missing_window','corrupt_part'])
def test_legacy_direct_request_rejects_bad_identity_window_and_artifact(legacy,fault):
 client,lab,jid,expected,originals=legacy;query='?part=1'
 if fault=='unknown_part':query='?part=999'
 if fault=='missing_window':query='?part=1&window=validation'
 if fault=='corrupt_part':
  path=lab.root/'data/jobs'/jid/'parts/000001.json.gz';raw=path.read_bytes();path.write_bytes(b'X'+raw[1:])
 response=client.get('/api/jobs/'+jid+'/report'+query);assert response.status_code==409,response.text
 assert client.get('/api/jobs/'+jid+'/result-summary').json()['requires_index'] is True
