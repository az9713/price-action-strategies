"""Real interpreter death and original family-account reuse across restart."""
import hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path
from threading import Event
import pytest
from test_research_family_source import original
from backend.lab.worker import Worker
from backend.lab.research_family_jobs import create_analysis,inspect_analysis

CHILD=Path(__file__).with_name('research-family-death-child.py')
spec=importlib.util.spec_from_file_location('authored_family_death',CHILD)
death=importlib.util.module_from_spec(spec);spec.loader.exec_module(death)


@pytest.mark.parametrize('boundary',list(death.BOUNDARIES))
def test_actual_family_process_deaths_keep_whole_original_cohort_and_publication(original,tmp_path,monkeypatch,boundary):
    lab,parent=original;child=create_analysis(lab,parent['id'],'change_of_character');jid=child['id']
    original_root=hashlib.sha256(lab.output_path(parent['id']).read_bytes()).hexdigest();marker=tmp_path/'observed-death.json'
    result=subprocess.run([sys.executable,str(CHILD),str(lab.root),jid,boundary,str(marker)],env=os.environ.copy(),capture_output=True,timeout=90)
    assert result.returncode==death.BOUNDARIES[boundary],result.stderr.decode(errors='replace')
    observed=json.loads(marker.read_text());assert observed['boundary']==boundary
    # Lease expiry is authored only after the child is observably dead.
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(jid,))
    def no_prices(*a,**k):raise AssertionError('Restart cannot rerun financial accounts.')
    monkeypatch.setattr(lab,'_evaluation_input',no_prices)
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='completed'
    value=inspect_analysis(lab,jid);assert len(value['rows'])==3
    assert hashlib.sha256(lab.output_path(parent['id']).read_bytes()).hexdigest()==original_root
    with lab.store.db() as db:
        attempts=db.execute('SELECT attempts FROM trial_plans WHERE job_id=?',(jid,)).fetchone()[0]
        assert attempts==(1 if boundary in {'after_publication','after_view'} else 2)
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==2
    if boundary in {'after_publication','after_view'}:
        assert hashlib.sha256(lab.output_path(jid).read_bytes()).hexdigest()==observed['root_sha256']


@pytest.mark.parametrize('boundary',['after_computation','after_root_file','after_publication','after_view'])
@pytest.mark.parametrize('mode',['cancel','shutdown'])
def test_actual_family_cancellation_and_shutdown_resume_original_job(original,monkeypatch,boundary,mode):
    lab,parent=original;child=create_analysis(lab,parent['id'],'change_of_character');jid=child['id'];stop=Event()
    def requested():
        if mode=='cancel':lab.store.cancel(jid)
        else:stop.set()
    with monkeypatch.context() as patch:
        fired=death.install(patch,lab,jid,boundary,requested)
        assert Worker(lab,stop).run_once() and fired==[True]
    assert lab.store.job(jid)['status']==('canceled' if mode=='cancel' else 'queued')
    if mode=='cancel':lab.store.resume(jid)
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='completed'
    assert len(inspect_analysis(lab,jid)['rows'])==3
