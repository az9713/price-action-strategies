"""Read saved reports in place; allow only derived-view additions, preserve originals."""
from pathlib import Path
import hashlib,json,os,sqlite3,sys,urllib.request
from verification_awake import awake
root=Path.cwd();sys.path.insert(0,str(root))
from verification.frontend_check import browser_run
from verification.record_check import source_paths
run=Path(os.environ['PA_EVIDENCE_RUN_DIR']);ids=['20d37c0992984a44bdb103bd0d0c3b0a','4e851c9015634b7a9dbf06619770d894']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def sources():return {p.relative_to(root).as_posix():sha(p) for p in source_paths(root)}
def rows(db,table,limit):
 h=hashlib.sha256();count=0
 for row in db.execute('SELECT * FROM '+table+' WHERE rowid<=? ORDER BY rowid',(limit,)):
  h.update(json.dumps(list(row),separators=(',',':'),allow_nan=False).encode());h.update(b'\n');count+=1
 return dict(rows=count,sha256=h.hexdigest())
def dbopen():return sqlite3.connect((root/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)
tables=['jobs','events','trial_plans','trial_attempts','strategies','studies','viewed_windows']
with dbopen() as db:
 assert db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','canceling')").fetchone()[0]==0
 limits={t:db.execute('SELECT COALESCE(MAX(rowid),0) FROM '+t).fetchone()[0] for t in tables};before={t:rows(db,t,limits[t]) for t in tables}
files={}
for jid in ids:
 folder=root/'data/jobs'/jid
 for p in [folder/'result.json.gz',*sorted((folder/'parts').glob('*.json.gz'))]:assert p.is_file();files[p.relative_to(root).as_posix()]=sha(p)
source=sources();os.environ['PA_BROWSER_BASE_URL']='http://127.0.0.1:8767'
with urllib.request.urlopen(os.environ['PA_BROWSER_BASE_URL']+'/api/health') as response:health=json.load(response)
assert health['source_current'] and health['worker_ready'];code=2
try:
 with awake():code=browser_run(['exec','--','playwright','test','--config=../verification/runs/live025-saved-browser.config.ts'])
finally:
 assert sources()==source
 for name,digest in files.items():assert sha(root/name)==digest
 with dbopen() as db:
  after={t:rows(db,t,limits[t]) for t in tables};assert before==after
  additions={t:db.execute('SELECT COUNT(*) FROM '+t+' WHERE rowid>?',(limits[t],)).fetchone()[0] for t in tables}
  assert all(additions[t]==0 for t in tables if t!='events')
  new_events=list(db.execute('SELECT kind,entity_id FROM events WHERE rowid>?',(limits['events'],)));assert all(kind=='result_view_saved' and jid in ids for kind,jid in new_events)
  assert db.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('queued','running','canceling')").fetchone()[0]==0
 with urllib.request.urlopen(os.environ['PA_BROWSER_BASE_URL']+'/api/health') as response:current=json.load(response)
 assert all(current[k]==health[k] for k in ['server_pid','worker_pid','core_hash']) and current['worker_ready']
 value=dict(scope=__doc__,child_exit_code=code,source_unchanged=True,original_database_prefixes_preserved=before,original_saved_file_hashes=files,additions=additions,new_event_kinds=[kind for kind,jid in new_events],no_financial_jobs_created=True,price_cache_copied=False,credentials_accessed=False,owns_server=False,existing_server_left_running=True,health=current)
 (run/'saved-live-original-preservation.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
raise SystemExit(code)
