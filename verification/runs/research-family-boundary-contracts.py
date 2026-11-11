"""Actual original reservation, membership, closing and restart counterexamples."""
import gzip,hashlib,json
import pytest
from test_research_family_source import original
from backend.lab import research_family_jobs as flow
from backend.lab.research_family_source import FamilyReports
from backend.lab.service import compressed_read,compressed_write
from backend.lab.store import StateError
from backend.lab.worker import Worker


@pytest.fixture
def saved(original):
    lab,parent=original;child=flow.create_analysis(lab,parent['id'],'change_of_character')
    assert Worker(lab).run_once() and lab.store.job(child['id'])['status']=='completed'
    assert flow.inspect_analysis(lab,child['id'])['report']['version_count']==3
    return lab,parent,child


def reanchor(lab,jid,value=None,raw=None):
    path=lab.output_path(jid)
    if raw is None:compressed_write(path,value)
    else:path.write_bytes(gzip.compress(raw,mtime=0))
    with lab.store.db() as db:
        db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(json.dumps(dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest())),jid))


@pytest.mark.parametrize('fault',['missing_link','missing_reservation','duplicate_reservation','malformed_reservation','wrong_child','wrong_binding'])
def test_original_reservation_corruption_refuses_both_read_and_replacement(saved,fault):
    lab,parent,child=saved
    with lab.store.db() as db:
        row=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='family_analysis_reserved'",(parent['id'],)).fetchone()
        value=json.loads(row['details'])
        if fault=='missing_link':db.execute('DELETE FROM family_analysis_links WHERE child_id=?',(child['id'],))
        elif fault=='missing_reservation':db.execute('DELETE FROM events WHERE id=?',(row['id'],))
        elif fault=='duplicate_reservation':lab.store.event('family_analysis_reserved',parent['id'],value,db)
        else:
            if fault=='wrong_child':value['child_id']=parent['id']
            elif fault=='wrong_binding':value['binding']['root_sha256']='0'*64
            db.execute('UPDATE events SET details=? WHERE id=?',('{' if fault=='malformed_reservation' else json.dumps(value),row['id']))
    with pytest.raises(StateError):flow.inspect_analysis(lab,child['id'])
    with pytest.raises(StateError):flow.create_analysis(lab,parent['id'],'change_of_character')
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==2


@pytest.mark.parametrize('fault',['wrong_job','missing_member','wrong_member','wrong_computed_witness','trial_digest','unparseable_original'])
def test_hash_consistent_artifact_changes_still_need_original_members_and_computation(saved,fault):
    lab,parent,child=saved;jid=child['id'];value=compressed_read(lab.output_path(jid))
    if fault=='trial_digest':
        with lab.store.db() as db:db.execute('UPDATE trial_plans SET computed_sha256=? WHERE job_id=?',('0'*64,jid))
    elif fault=='unparseable_original':reanchor(lab,jid,raw=b'not a complete JSON object')
    else:
        if fault=='wrong_job':value['job_id']='0'*32
        elif fault=='missing_member':value['rows'].pop()
        elif fault=='wrong_member':value['rows'][0]['source_part']=999
        else:value['rows'][0]['witness'][0]='0'*64
        reanchor(lab,jid,value)
    with pytest.raises(StateError):flow.inspect_analysis(lab,jid)


def test_changed_original_source_root_does_not_rebind_reserved_family(saved):
    lab,parent,child=saved;root=compressed_read(lab.output_path(parent['id']));root['changed_metadata']='after reservation'
    reanchor(lab,parent['id'],root)
    with pytest.raises(StateError,match='differs from its reservation'):flow.inspect_analysis(lab,child['id'])


def test_registration_missing_original_file_is_a_domain_refusal(original):
    lab,parent=original;lab.output_path(parent['id']).unlink()
    with pytest.raises(StateError,match='registration evidence'):flow.create_analysis(lab,parent['id'],'change_of_character')
    with lab.store.db() as db:assert db.execute('SELECT COUNT(*) FROM jobs').fetchone()[0]==1


def test_closing_analysis_root_change_is_refused_after_all_original_source_checks(saved,monkeypatch):
    lab,parent,child=saved;guard=FamilyReports.guard;observed=[]
    def changed(self):
        guard(self);observed.append(True);path=lab.output_path(child['id']);path.write_bytes(path.read_bytes()+b'after source inspection')
    monkeypatch.setattr(FamilyReports,'guard',changed)
    with pytest.raises(StateError,match='changed during inspection'):flow.inspect_analysis(lab,child['id'])
    assert observed==[True]


@pytest.mark.parametrize('alter_mutable_state',[False,True])
def test_owned_resume_cannot_replace_missing_original_publication_even_if_trial_state_changed(saved,alter_mutable_state):
    lab,parent,child=saved;jid=child['id']
    with lab.store.db() as db:
        db.execute("UPDATE jobs SET status='failed' WHERE id=?",(jid,))
        db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_saved'",(jid,))
        if alter_mutable_state:db.execute("UPDATE trial_plans SET state='interrupted' WHERE job_id=?",(jid,))
    lab.store.resume(jid)
    assert Worker(lab).run_once() and lab.store.job(jid)['status']=='failed'
    with lab.store.db() as db:
        assert db.execute('SELECT attempts FROM trial_plans WHERE job_id=?',(jid,)).fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()[0]==0


def test_direct_family_page_contracts_and_cancellation_are_not_coerced(saved):
    lab,parent,child=saved
    with pytest.raises(StateError):flow.inspect_analysis(lab,parent['id'])
    with pytest.raises(InterruptedError):flow.inspect_analysis(lab,child['id'],cancel=lambda:True)
    for table,limit,offset in [('members',True,0),('members',1,False),('winners',1,0),('marked',101,0)]:
        with pytest.raises(StateError):flow.analysis_page(lab,child['id'],table,limit,offset)
