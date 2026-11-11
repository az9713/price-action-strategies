"""Original arm checkpoints survive actual deaths; unfinished outputs are not approved."""
import importlib.util,json,os,subprocess,sys,hashlib
from pathlib import Path
import pytest
from backend.lab import service
from backend.lab.worker import Worker
from backend.lab.research_funnel_arms import queue_arms,verify_arm
from backend.lab.research_family_source import read_saved_family

spec=importlib.util.spec_from_file_location('actual_arm_fixture',Path(__file__).with_name('research-funnel-arm-contracts.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
inputs=fixture.inputs;registration=fixture.registration;planned=fixture.planned
EXITS={'after_first_checkpoint':111,'after_second_checkpoint':112,'after_part_receipt':113,'inside_root_transaction':114,'after_root_commit':115}


@pytest.mark.parametrize('boundary',list(EXITS))
def test_actual_arm_death_reuses_only_original_committed_checkpoints(planned,monkeypatch,tmp_path,boundary):
    lab,study=planned;reserved=queue_arms(lab,study['id'])
    with lab.store.db() as db:jid=db.execute("SELECT id FROM jobs WHERE status='queued' ORDER BY created,id LIMIT 1").fetchone()[0]
    marker=tmp_path/'actual-death.json'
    result=subprocess.run([sys.executable,str(Path(__file__).with_name('research-arm-death-child.py')),str(lab.root),jid,boundary,str(marker)],env=os.environ.copy(),capture_output=True,timeout=90)
    assert result.returncode==EXITS[boundary],result.stderr.decode(errors='replace')
    observed=json.loads(marker.read_text(encoding='utf-8'));assert observed['boundary']==boundary
    # Expire only the observably dead child's lease, never a live worker here.
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(jid,))
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='completed'
    with lab.store.db() as db:
        attempts=[row[0] for row in db.execute('SELECT attempts FROM trial_plans WHERE job_id=? ORDER BY part',(jid,))]
        assert attempts==([2,1] if boundary=='after_part_receipt' else [1,1]),'An unfinished artifact needs a new actual computation, not a fabricated checkpoint reuse.'
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]==1
    assert verify_arm(lab,lab.store.job(jid))['study_id']==study['id']
    assert read_saved_family(lab,jid,'change_of_character')['version_count']==2
    assert queue_arms(lab,study['id'])['arms']==reserved['arms']
    for name,digest in observed['files'].items():
        if name.startswith('parts/') and name.endswith('.json.gz') and boundary!='after_part_receipt':
            assert hashlib.sha256((lab.output_path(jid).parent/name).read_bytes()).hexdigest()==digest
