"""Actual saved-account family jobs; synthetic source accounts, never user data."""
import importlib,importlib.util,json
import pytest
from test_research_family_source import original
from backend.lab.worker import Worker
from backend.lab.store import StateError


def test_family_job_workflow_is_implemented():
    assert importlib.util.find_spec('backend.lab.research_family_jobs') is not None,'Durable saved-family workflow is not implemented.'


@pytest.fixture
def workflow():return importlib.import_module('backend.lab.research_family_jobs')


def test_original_family_job_runs_once_and_inspects_complete_saved_evidence(workflow,original,monkeypatch):
    lab,parent=original
    child=workflow.create_analysis(lab,parent['id'],'change_of_character')
    assert workflow.create_analysis(lab,parent['id'],'change_of_character')['id']==child['id']
    with lab.store.db() as db:
        trial=db.execute('SELECT role,state FROM trial_plans WHERE job_id=?',(child['id'],)).fetchone()
        assert tuple(trial)==('research_family','planned')
    def forbidden(*a,**k):raise AssertionError('Family workflow cannot run prices, signals or new financial accounts.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    assert Worker(lab).run_once() and lab.store.job(child['id'])['status']=='completed'
    value=workflow.inspect_analysis(lab,child['id'])
    assert value['report']['version_count']==3 and len(value['rows'])==3
    assert value['report']['marked']['gate_pass'] is False
    assert {r['source_part'] for r in value['rows']}=={0,1,2}
    def no_math(*a,**k):raise AssertionError('Saved inspection cannot recompute the family.')
    monkeypatch.setattr(workflow,'family_average',no_math)
    assert workflow.inspect_analysis(lab,child['id'])==value
    with lab.store.db() as db:
        assert db.execute('SELECT attempts FROM trial_plans WHERE job_id=?',(child['id'],)).fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(child['id'],)).fetchone()[0]==1
    assert workflow.create_analysis(lab,parent['id'],'change_of_character')['id']==child['id']


@pytest.mark.parametrize('fault',['parent_root','parent_part','parent_trial','analysis_root','analysis_result_missing','analysis_result_duplicate','analysis_attempt','analysis_computation_missing'])
def test_saved_family_publication_faults_refuse_without_repair_or_new_jobs(workflow,original,fault):
    lab,parent=original;child=workflow.create_analysis(lab,parent['id'],'change_of_character')
    assert Worker(lab).run_once() and lab.store.job(child['id'])['status']=='completed'
    if fault in {'parent_root','parent_part','analysis_root'}:
        path=lab.output_path(child['id'] if fault=='analysis_root' else parent['id'])
        if fault=='parent_part':path=path.parent/'parts/000000.json.gz'
        path.write_bytes(path.read_bytes()+b'changed')
    else:
        with lab.store.db() as db:
            if fault=='parent_trial':db.execute("UPDATE trial_plans SET computed_sha256=? WHERE job_id=? AND part=0",('0'*64,parent['id']))
            elif fault=='analysis_result_missing':db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_saved'",(child['id'],))
            elif fault=='analysis_result_duplicate':
                value=json.loads(db.execute("SELECT details FROM events WHERE entity_id=? AND kind='result_saved'",(child['id'],)).fetchone()[0]);lab.store.event('result_saved',child['id'],value,db)
            elif fault=='analysis_attempt':db.execute("UPDATE trial_attempts SET computed_sha256=? WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=?)",('0'*64,child['id']))
            else:db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_computation_recorded'",(child['id'],))
    with pytest.raises(StateError):workflow.inspect_analysis(lab,child['id'])
    with lab.store.db() as db:assert db.execute("SELECT COUNT(*) FROM jobs WHERE kind='family_analysis'").fetchone()[0]==1


def test_parent_changed_after_reservation_never_publishes_family(workflow,original):
    lab,parent=original;child=workflow.create_analysis(lab,parent['id'],'change_of_character')
    path=lab.output_path(parent['id']).parent/'parts/000000.json.gz';path.write_bytes(path.read_bytes()+b'changed')
    assert Worker(lab).run_once() and lab.store.job(child['id'])['status']=='failed'
    assert not lab.output_path(child['id']).exists()
