"""Current managed study-index owner, complete served assets and competing-store refusal."""
from pathlib import Path
source=Path('verification/runs/check-dataset-context-managed-runtime.py').read_text(encoding='utf-8')
assert source.count('==31792')==1 and source.count('managed_session=19735')==1
source=source.replace('==31792','==38808').replace('managed_session=19735','managed_session=29880')
source=source.replace(",stop_observation='verification/runs/dataset-context-managed-restart-observation.json'",'')
check="assert not [j for j in json.loads(get('/api/jobs')) if j['status'] in ['queued','running','canceling']]"
verified=check+"\nimport sqlite3\ndb=sqlite3.connect('file:'+(root/'data/lab.sqlite3').as_posix()+'?mode=ro',uri=True)\ntry:\n db.execute('BEGIN');total,pending=db.execute(\"SELECT COUNT(*),COALESCE(SUM(status IN ('queued','running','canceling')),0) FROM jobs\").fetchone();assert pending==0\nfinally:db.close()"
assert source.count(check)==1;source=source.replace(check,verified)
source=source.replace('native_process_absence_certified=False','database_jobs_observed=total,pending_jobs=0,native_process_absence_certified=False')
exec(compile(source,'study-status-managed-runtime-resolved.py','exec'))
