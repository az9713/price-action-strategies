"""Six real interpreter deaths; original accounts never silently rerun.

Control deaths stop before any financial diagnostic set executes. They do not
certify the still-required complete10000-set positive-control path.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from backend.lab.worker import Worker
from backend.lab import research_funnel_jobs as flow

spec=importlib.util.spec_from_file_location('owned_death_authored_originals',Path(__file__).with_name('research-owned-qualification-boundaries.py'))
fixtures=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixtures)
originals=fixtures.originals;positive_originals=fixtures.positive_originals;clone_authored=fixtures.clone_authored
CODES=dict(preliminary_inside_transaction=241,preliminary_committed=242,control_reserved=243,
           waiting_committed=244,root_inside_transaction=245,root_committed=246)


@pytest.mark.parametrize('point',list(CODES))
def test_real_qualification_process_death_recovers_original_checkpoint_and_same_control(point,originals,positive_originals,tmp_path):
    source=positive_originals if point in {'control_reserved','waiting_committed'} else originals
    lab=clone_authored(source['ready'],tmp_path);jid=source['job_id'];helper=Path(__file__).with_name('owned-qualification-death-child.py')
    with lab.store.db() as db:
        finance_before=[tuple(r) for r in db.execute("SELECT id,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE role='strategy' ORDER BY id")]
    result=subprocess.run([sys.executable,str(helper),str(lab.root),jid,point],capture_output=True,text=True,timeout=180)
    assert result.returncode==CODES[point],(result.returncode,result.stdout,result.stderr)
    # Only the observed-dead test subprocess's own lease may be expired.
    assert result.returncode is not None
    before_root=lab.output_path(jid).read_bytes() if lab.output_path(jid).exists() else None
    with lab.store.db() as db:
        db.execute("UPDATE jobs SET lease_until=0 WHERE id=? AND status IN ('running','canceling')",(jid,))
        controls=[r[0] for r in db.execute("SELECT id FROM jobs WHERE kind='trade_twins'")]
        if point in {'control_reserved','waiting_committed'}:assert len(controls)==1
        if point=='root_inside_transaction':
            assert db.execute('SELECT COUNT(*) FROM funnel_candidate_freezes').fetchone()[0]==0
            assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]==0
    if point=='waiting_committed':
        claimed=lab.store.claim('authored-restart-control-owner');assert claimed['id']==controls[0]
        lab.store.release(claimed['id'],'authored-restart-control-owner')
        assert lab.store.job(jid)['status']=='queued'
    else:
        assert Worker(lab).run_once()
        if point=='control_reserved':
            assert lab.store.job(jid)['status']=='queued'
            with lab.store.db() as db:
                assert [r[0] for r in db.execute("SELECT id FROM jobs WHERE kind='trade_twins'")]==controls
                assert db.execute("SELECT child_id FROM funnel_dependencies WHERE parent_id=? AND role='control:000000'",(jid,)).fetchone()[0]==controls[0]
        else:
            assert lab.store.job(jid)['status']=='completed',lab.store.job(jid)['error']
            saved=flow.inspect_qualification(lab,jid)
            assert saved['report']['candidate_ids']==[] and saved['candidate_freeze']['candidate_ids']==[]
            if point=='root_committed':assert lab.output_path(jid).read_bytes()==before_root
    with lab.store.db() as db:
        assert [tuple(r) for r in db.execute("SELECT id,attempts,computed_sha256,artifact_sha256 FROM trial_plans WHERE role='strategy' ORDER BY id")]==finance_before
        preliminary=db.execute("SELECT attempts FROM trial_plans WHERE job_id=? AND window='preliminary'",(jid,)).fetchone()[0]
        assert preliminary==(2 if point=='preliminary_inside_transaction' else 1)
        final=db.execute("SELECT attempts FROM trial_plans WHERE job_id=? AND window='report'",(jid,)).fetchone()[0]
        assert final==(0 if point in {'control_reserved','waiting_committed'} else 2 if point=='root_inside_transaction' else 1)
        assert db.execute("SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans t ON t.id=a.trial_id WHERE t.role='trade_twin_set'").fetchone()[0]==0
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]==(0 if point in {'control_reserved','waiting_committed'} else 1)
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/('death-'+point+'.json')).write_text(json.dumps(dict(
            scope=__doc__,point=point,actual_exit_code=result.returncode,checkpoint_attempts=dict(preliminary=preliminary,report=final),
            original_account_occurrences=len(finance_before),original_account_attempts_and_hashes_unchanged=True,
            original_control_ids=controls,diagnostic_financial_sets_executed=0,
            predeath_root_sha256=hashlib.sha256(before_root).hexdigest() if before_root is not None else None,
            job_status=lab.store.job(jid)['status']),indent=2),encoding='utf-8')
