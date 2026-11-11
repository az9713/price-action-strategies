"""Generic result routes must not bypass original qualification authority."""
import importlib.util
from pathlib import Path
from fastapi.testclient import TestClient
from backend.lab.api import create_app

spec=importlib.util.spec_from_file_location('qualification_api_authored_store',Path(__file__).with_name('research-owned-qualification-boundaries.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
originals=fixtures.originals;clone_authored=fixtures.clone_authored


def test_original_qualification_summary_and_result_routes_refuse_missing_candidate_freeze(originals,tmp_path):
    lab=clone_authored(originals['complete'],tmp_path);jid=originals['job_id'];app=create_app(lab.root,run_worker=False)
    with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
        client.headers['X-Lab-Token']=client.get('/api/session').json()['token']
        before=client.get('/api/jobs/'+jid+'/result-summary');assert before.status_code==200,before.text
        summary=before.json()
        assert len(before.content)<49152 and summary['original_evidence_verified'] is True
        assert summary['version_count']==2 and summary['candidate_count']==0
        assert 'rows' not in summary and 'candidate_freeze' not in summary
        with lab.store.db() as db:db.execute('DELETE FROM funnel_candidate_freezes WHERE study_id=?',(originals['study_id'],))
        assert client.get('/api/jobs/'+jid+'/result').status_code==409
        assert client.get('/api/jobs/'+jid+'/result-summary').status_code==409
