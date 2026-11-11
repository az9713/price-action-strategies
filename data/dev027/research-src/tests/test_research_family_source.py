"""Complete original saved-family membership and authority before arithmetic."""
import copy,gzip,hashlib,importlib,importlib.util,json
from pathlib import Path
import pandas as pd
import pytest
from conftest import minute_frame
from backend.lab import service
from backend.lab.config import Strategy,identity
from backend.lab.data import save_dataset
from backend.lab.models import Search
from backend.lab.service import Lab,compressed_read,compressed_write
from backend.lab.store import StateError
from backend.lab.worker import Worker


def test_original_saved_family_reader_is_implemented():
    assert importlib.util.find_spec('backend.lab.research_family_source') is not None,'Original all-version saved-family reader is not implemented.'


@pytest.fixture
def reader():return importlib.import_module('backend.lab.research_family_source')


@pytest.fixture
def original(tmp_path,monkeypatch):
    lab=Lab(tmp_path)
    frame=pd.concat([minute_frame(day) for day in ['2026-11-02','2026-11-03','2026-11-04']],ignore_index=True)
    dataset=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='Original saved-family authority fixture',corporate_actions_complete=True))
    monkeypatch.setattr(service,'generate_signals',lambda *a,**k:[])
    job=lab.create_experiment(Search(dataset_id=dataset['id'],start='2026-11-02',end='2026-11-04',
        count=3,families=['change_of_character'],timeframes=['1m']))
    assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
    return lab,job


def fingerprints(lab,jid):
    with lab.store.db() as db:
        rows={name:[tuple(row) for row in db.execute('SELECT * FROM '+name+' ORDER BY 1')] for name in ['jobs','events','trial_plans','trial_attempts']}
    return identity(rows),hashlib.sha256(lab.output_path(jid).read_bytes()).hexdigest()


def test_actual_frozen_search_family_is_complete_original_saved_only_and_detached(reader,original,monkeypatch):
    lab,job=original;jid=job['id'];before=fingerprints(lab,jid)
    def forbidden(*a,**k):raise AssertionError('Saved family analysis must not regenerate signals, prices, accounts, jobs or derived views.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    monkeypatch.setattr(service,'generate_signals',forbidden)
    monkeypatch.setattr(lab.store,'create_job',forbidden)
    monkeypatch.setattr(lab.result_index,'part',forbidden)
    value=reader.read_saved_family(lab,jid,'change_of_character')
    assert value['version_count']==3 and len(value['members'])==3
    assert value['source_authority']['parts']==[0,1,2]
    assert value['source_authority']['original_job_id']==jid
    assert value['source_authority']['original_core_hash']==job['payload']['core_hash']
    assert value['source_authority']['root_sha256']==before[1]
    assert value['marked']['gate_pass'] is False and value['marked']['sessions']==3
    assert value['source_report_hashes']=={identity(c):identity(compressed_read(lab.output_path(jid).parent/'parts'/(str(part).zfill(6)+'.json.gz'))['report']) for part,c in enumerate(job['payload']['configurations'])}
    assert fingerprints(lab,jid)==before
    value['source_authority']['parts'].clear()
    assert reader.read_saved_family(lab,jid,'change_of_character')['source_authority']['parts']==[0,1,2]


@pytest.mark.parametrize('fault',['missing_result','duplicate_result','root_bytes','root_subset','part_bytes','trial_state','missing_start','missing_checkpoint','checkpoint_digest','attempt_digest','index_schema'])
def test_original_family_faults_never_produce_a_rehashed_partial_family(reader,original,fault):
    lab,job=original;jid=job['id']
    with lab.store.db() as db:
        if fault=='missing_result':db.execute("DELETE FROM events WHERE entity_id=? AND kind='result_saved'",(jid,))
        elif fault=='duplicate_result':
            row=db.execute("SELECT details FROM events WHERE entity_id=? AND kind='result_saved'",(jid,)).fetchone()
            lab.store.event('result_saved',jid,json.loads(row[0]),db)
        elif fault=='trial_state':db.execute("UPDATE trial_plans SET state='computed' WHERE job_id=? AND part=0",(jid,))
        elif fault in {'missing_start','missing_checkpoint','checkpoint_digest'}:
            kind='trial_computation_started' if fault=='missing_start' else 'trial_checkpoint_saved'
            trial=db.execute('SELECT id FROM trial_plans WHERE job_id=? AND part=0',(jid,)).fetchone()[0]
            row=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind=? AND json_extract(details,'$.trial_id')=?",(jid,kind,trial)).fetchone()
            if fault=='checkpoint_digest':
                value=json.loads(row['details']);value['sha256']='0'*64
                db.execute('UPDATE events SET details=? WHERE id=?',(json.dumps(value),row['id']))
            else:db.execute('DELETE FROM events WHERE id=?',(row['id'],))
        elif fault=='attempt_digest':
            db.execute('UPDATE trial_attempts SET computed_sha256=? WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=? AND part=0)',('0'*64,jid))
        elif fault=='index_schema':
            db.execute('DROP INDEX research_family_trial_events')
            db.execute('CREATE INDEX research_family_trial_events ON events(entity_id,id)')
    root=lab.output_path(jid)
    if fault=='root_bytes':root.write_bytes(root.read_bytes()+b'changed')
    elif fault=='root_subset':
        value=compressed_read(root);value['rows'].pop();value['count']=2;compressed_write(root,value)
        with lab.store.db() as db:db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(json.dumps(dict(sha256=hashlib.sha256(root.read_bytes()).hexdigest())),jid))
    elif fault=='part_bytes':
        path=root.parent/'parts/000000.json.gz';path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(StateError):reader.read_saved_family(lab,jid,'change_of_character')


def test_family_cancellation_and_unknown_families_never_create_or_repair_evidence(reader,original):
    lab,job=original;before=fingerprints(lab,job['id'])
    with pytest.raises(InterruptedError):reader.read_saved_family(lab,job['id'],'change_of_character',cancel=lambda:True)
    with pytest.raises(StateError):reader.read_saved_family(lab,job['id'],'invented')
    with pytest.raises(StateError):reader.read_saved_family(lab,job['id'],'breakout')
    assert fingerprints(lab,job['id'])==before


@pytest.mark.parametrize('fault',['root','first_part','first_trial','publication_event'])
def test_closing_guard_rechecks_earlier_originals_after_all_family_arithmetic(reader,original,monkeypatch,fault):
    lab,job=original;jid=job['id'];average=reader.family_average;seen=[]
    def changed_after_arithmetic(*args,**kwargs):
        value=average(*args,**kwargs);seen.append(True)
        if fault in {'root','first_part'}:
            path=lab.output_path(jid) if fault=='root' else lab.output_path(jid).parent/'parts/000000.json.gz'
            path.write_bytes(path.read_bytes()+b'changed-after-all-reads')
        else:
            with lab.store.db() as db:
                if fault=='first_trial':db.execute("UPDATE trial_plans SET computed_sha256=? WHERE job_id=? AND part=0",('0'*64,jid))
                else:db.execute("UPDATE events SET id=(SELECT MAX(id)+1 FROM events) WHERE entity_id=? AND kind='result_saved'",(jid,))
        return value
    monkeypatch.setattr(reader,'family_average',changed_after_arithmetic)
    with pytest.raises(StateError):reader.read_saved_family(lab,jid,'change_of_character')
    assert seen==[True]


def test_streaming_source_retains_only_bounded_live_report_objects(reader,original,monkeypatch):
    import weakref
    lab,job=original;load=reader._load;live=set();maximum=[];loads=[]
    class TrackedReport(dict):pass
    def track(path,*args,**kwargs):
        value=load(path,*args,**kwargs)
        if isinstance(value.get('report'),dict):
            report=TrackedReport(value['report']);token=object();live.add(token);loads.append(path.name)
            weakref.finalize(report,live.discard,token);value['report']=report;maximum.append(len(live))
        return value
    monkeypatch.setattr(reader,'_load',track)
    value=reader.read_saved_family(lab,job['id'],'change_of_character')
    assert value['version_count']==3 and len(loads)==6
    assert max(maximum)<=2 and not live
