"""Same-query read-only SQLite reuse prototype; no production database change."""
from contextlib import contextmanager,closing
from pathlib import Path
from unittest.mock import patch
import json,os,sqlite3,statistics,sys,time
root=Path.cwd();stage=root/'data/dev027/research-src';sys.path.insert(0,str(stage))
from backend.lab.service import Lab
from backend.lab.store import Store
from backend.lab.research_funnel_final import final_summary
from backend.lab.config import identity
out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
folder=max((root/'data/dev027/funnel-browser').iterdir(),key=lambda p:p.stat().st_ctime_ns)
with closing(sqlite3.connect((folder/'data/lab.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
    row=db.execute("SELECT id FROM jobs WHERE kind='funnel_final' AND status='completed' ORDER BY created LIMIT 1").fetchone();assert row
lab=Lab(folder);real=Store.db

def state():
 with real(lab.store) as db:return {name:db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in ['jobs','trial_plans','trial_attempts','events','viewed_windows']}
before=state();results=[];digests=[]
for mode in ['original','read_only_reuse','read_only_reuse','original']:
    idle=[];all_connections=[];counter={'opens':0,'uses':0,'active':0,'peak_active':0}
    @contextmanager
    def pooled(store,thread_handoff=False):
        if store is not lab.store or thread_handoff:
            with real(store,thread_handoff) as db:yield db
            return
        if idle:db=idle.pop()
        else:
            db=sqlite3.connect(store.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=10,isolation_level=None)
            db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');db.execute('PRAGMA foreign_keys=ON');all_connections.append(db);counter['opens']+=1
        counter['uses']+=1;counter['active']+=1;counter['peak_active']=max(counter['peak_active'],counter['active'])
        try:yield db
        finally:
            if db.in_transaction:db.rollback()
            counter['active']-=1;idle.append(db)
    started=time.perf_counter();cpu=time.process_time()
    try:
        if mode=='original':
            with patch.object(Store,'db',real):value=final_summary(lab,row[0])
        else:
            with patch.object(Store,'db',pooled):value=final_summary(lab,row[0])
    finally:
        for db in all_connections:db.close()
    digest=identity(value);digests.append(digest);results.append(dict(mode=mode,wall_seconds=time.perf_counter()-started,cpu_seconds=time.process_time()-cpu,connections=counter,summary_sha256=digest))
assert len(set(digests))==1 and state()==before
medians={mode:statistics.median(r['wall_seconds'] for r in results if r['mode']==mode) for mode in ['original','read_only_reuse']}
value=dict(scope=__doc__,measurements=results,median_wall_seconds=medians,all_full_original_and_code_checks_retained=True,original_state_unchanged=True,production_reuse_not_implemented=True)
(out/'same-query-read-only-connection-prototype.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
