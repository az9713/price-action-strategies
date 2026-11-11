"""Preserve original synthetic work and stop obsolete checks before fixing a measured defect."""
from pathlib import Path
import json,os,sqlite3,sys,tempfile
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.store import Store
targets=[(root/'data/dev027/funnel-positive/e58de6783305457f86fa8fd07bf48e28','be79eae61d8147df8b6f36428b7e12b4')]
base=Path(tempfile.gettempdir())/'pytest-of-user'
for pattern in ['pytest-*/test_complete_owned_original_p*/data/lab.sqlite3','pytest-*/test_six_actual_parts_evicted_*/data/lab.sqlite3']:
    for path in base.glob(pattern):
        if 'current' in path.parts:continue
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            for row in db.execute("SELECT id,status,owner FROM jobs WHERE kind='trade_twins' AND status='running'"):
                if row['id']=='13a4ffa4da364697948122a69e4db209' or (pattern.startswith('pytest-*/test_six') and row['owner']=='paired-part-owner'):
                    targets.append((path.parent.parent,row['id']))
seen=set();observations=[]
for folder,jid in targets:
    folder=folder.resolve()
    if (folder,jid) in seen:continue
    seen.add((folder,jid))
    assert folder.is_relative_to(root/'data/dev027/funnel-positive') or folder.is_relative_to(base.resolve())
    manifests=list((folder/'data/datasets').glob('*/manifest.json'));assert manifests
    assert all(json.loads(p.read_text())['metadata']['input_kind']=='synthetic' for p in manifests)
    store=Store(folder)
    with store.db() as db:
        job=dict(db.execute('SELECT id,kind,status,owner FROM jobs WHERE id=?',(jid,)).fetchone())
        assert job['kind']=='trade_twins' and job['status'] in {'running','canceling','queued','completed','canceled'}
        before=db.execute('SELECT COUNT(*) FROM trade_twin_part_index WHERE job_id=?',(jid,)).fetchone()[0]
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
    if job['status'] in {'running','queued','canceling'}:store.cancel(jid)
    observations.append(dict(job_id=jid,original_status=job['status'],committed_original_parts_before_request=before,
        normal_cancellation_requested=job['status'] in {'running','queued','canceling'},source_prices_are_synthetic=True))
Path(os.environ['PA_EVIDENCE_RUN_DIR'],'normal-owned-verification-cancellation.json').write_text(json.dumps(dict(
    scope=__doc__,reason='Actual10000 benchmark failed at106 accounts; heartbeat thread database-lock failure and repeated whole-plan verification in atomic checkpoint publication require a production fix.',
    observations=observations,original_files_deleted=False,source_changed=False,project_paused=False,
    failed_or_canceled_runs_are_not_passes=True),indent=2),encoding='utf-8')
print(json.dumps(observations))
