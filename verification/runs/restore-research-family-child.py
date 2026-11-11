"""Fresh-interpreter verification of restored source and authored saved accounts."""
import hashlib,json,sys
from pathlib import Path
from fastapi.testclient import TestClient
import backend
from backend.lab import service
from backend.lab.api import create_app
from backend.lab.research import core_hash
from backend.lab.research_family_jobs import create_analysis,inspect_analysis
from backend.lab.service import Lab

source,store,jid,parent,expected_core,output=sys.argv[1:]
assert Path(backend.__file__).resolve().parents[1]==Path(source).resolve()
assert core_hash()==expected_core
lab=Lab(Path(store));root=lab.output_path(jid);before=hashlib.sha256(root.read_bytes()).hexdigest()
def forbidden(*a,**k):raise AssertionError('Restoration cannot rerun prices, signals or financial accounts.')
lab._evaluation_input=forbidden;service.generate_signals=forbidden
value=inspect_analysis(lab,jid)
assert len(value['rows'])==value['report']['version_count']==51
assert create_analysis(lab,parent,'change_of_character')['id']==jid
assert lab.result_index.summary(jid)['requires_index'] is True
repaired=lab.repair_result_view(jid);assert repaired['index_integrity']
assert inspect_analysis(lab,jid)==value
app=create_app(Path(store),run_worker=False)
with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',50000)) as client:
 response=client.get('/api/jobs/'+jid+'/family-analysis');assert response.status_code==200
 assert response.json()['version_count']==51
 rows=client.get('/api/jobs/'+jid+'/family-analysis/members?limit=1&offset=50').json()['rows']
 assert len(rows)==1 and rows[0]['source_part']==50
 exported=client.get('/api/jobs/'+jid+'/family-analysis/export/json')
 assert exported.status_code==200 and exported.json()==value
after=hashlib.sha256(root.read_bytes()).hexdigest();assert before==after
with lab.store.db() as db:
 assert db.execute('SELECT attempts FROM trial_plans WHERE job_id=?',(jid,)).fetchone()[0]==1
 assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]==1
Path(output).write_text(json.dumps(dict(restored_core=core_hash(),source_import_verified=True,versions=51,original_root_sha256=before,original_root_unchanged=True,existing_reservation_reused=True,derived_view_rebuilt_without_prices=True,complete_json_matches_original=True,api_summary_and_last_member_verified=True,financial_accounts_recomputed=0,fresh_python_process=True,dependency_environment_reused=True,fresh_machine_install_tested=False,installed_app_replaced=False),indent=2),encoding='utf-8')
