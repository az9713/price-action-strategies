"""Eight real final-process deaths: one consumption, original account reuse."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from backend.lab import service,research_funnel_final as flow
from backend.lab.worker import Worker

spec=importlib.util.spec_from_file_location('final_death_authored_originals',Path(__file__).with_name('research-funnel-final-boundaries.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
originals=fixtures.originals;finals=fixtures.finals;clone_authored=fixtures.clone_authored
CODES=dict(inside_consumption=200,after_consumption=201,first_account_committed=202,second_instrument_committed=203,
           inside_root=204,root_committed=205,inside_view=206,first_account_file_uncommitted=207)


@pytest.mark.parametrize('point',list(CODES))
def test_actual_final_process_death_recovers_same_job_and_original_accounts(finals,tmp_path,monkeypatch,point):
    lab=clone_authored(finals['ready'],tmp_path);jid=finals['job_id'];sid=finals['study_id']
    with lab.store.db() as db:
        original_sources=[tuple(r) for r in db.execute("SELECT id,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE job_id!=? ORDER BY id",(jid,))]
    child=subprocess.run([sys.executable,str(Path(__file__).with_name('funnel-final-death-child.py')),str(lab.root),jid,point],capture_output=True,text=True,timeout=240)
    assert child.returncode==CODES[point],(child.returncode,child.stdout,child.stderr)
    before_root=lab.output_path(jid).read_bytes() if lab.output_path(jid).exists() else None
    with lab.store.db() as db:
        consumed=db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='final_unlock_consumed'",(sid,)).fetchone()[0]
        assert consumed==(0 if point=='inside_consumption' else 1)
        # This lease belongs only to the subprocess whose actual exit was observed.
        db.execute("UPDATE jobs SET lease_until=0 WHERE id=? AND status IN ('running','canceling')",(jid,))
        committed=[tuple(r) for r in db.execute("SELECT part,window,attempts,artifact_sha256 FROM trial_plans WHERE job_id=? AND role='strategy' AND state='checkpointed' ORDER BY part,window",(jid,))]
    monkeypatch.setattr(service,'generate_signals',lambda *args,**kwargs:[])
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='completed',lab.store.job(jid)['error']
    assert lab.guard.study(sid)['status']=='final_complete'
    saved=flow.inspect_final(lab,jid)
    assert len(saved['rows'])==2 and saved['report']['instrument_count']==2
    assert flow.create_final(lab,sid)['id']==jid and Worker(lab).run_once() is False
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='final_unlock_consumed'",(sid,)).fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]==1
        accounts=[tuple(r) for r in db.execute("SELECT part,window,attempts FROM trial_plans WHERE job_id=? AND role='strategy' ORDER BY part,window",(jid,))]
        for part,key,attempts in accounts:assert attempts==(2 if point=='first_account_file_uncommitted' and part==0 and key=='primary_final' else 1)
        for part,key,attempt,digest in committed:
            row=db.execute('SELECT attempts,artifact_sha256 FROM trial_plans WHERE job_id=? AND part=? AND window=?',(jid,part,key)).fetchone()
            assert tuple(row)==(attempt,digest)
        aggregate=db.execute("SELECT attempts FROM trial_plans WHERE job_id=? AND window='aggregate'",(jid,)).fetchone()[0]
        assert aggregate==(2 if point=='inside_root' else 1)
        assert [tuple(r) for r in db.execute("SELECT id,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE job_id!=? ORDER BY id",(jid,))]==original_sources
    if point in {'root_committed','inside_view'}:assert lab.output_path(jid).read_bytes()==before_root
    if point=='inside_root':
        assert any(p.read_bytes()==before_root for p in lab.output_path(jid).parent.glob('orphan-final-*.json.gz'))
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/('final-death-'+point+'.json')).write_text(json.dumps(dict(
            scope=__doc__,point=point,actual_exit_code=child.returncode,consumptions_before_recovery=consumed,
            final_consumptions=1,original_committed_accounts_reused=len(committed),account_attempts=accounts,
            aggregate_attempts=aggregate,original_development_accounts_and_qualification_unchanged=True,
            predeath_root_sha256=hashlib.sha256(before_root).hexdigest() if before_root is not None else None,
            final_job_status=lab.store.job(jid)['status']),indent=2),encoding='utf-8')
