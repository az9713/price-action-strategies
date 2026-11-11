"""Original metadata, serialization and historical raw-configuration boundaries."""
import copy,gzip,hashlib,json
import pytest
from test_research_family_source import original,reader
from backend.lab.service import compressed_read,compressed_write
from backend.lab.store import StateError
from backend.lab.worker import Worker


def _rehash_root(lab,jid,value):
    path=lab.output_path(jid);compressed_write(path,value)
    with lab.store.db() as db:
        db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(json.dumps(dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest())),jid))


@pytest.mark.parametrize('fault',['not_completed','malformed_original_event','bad_result_digest','bad_attempt_history','wrong_root_configuration','wrong_part_context'])
def test_additional_original_boundary_faults_refuse_even_with_current_mutable_rows(reader,original,fault):
    lab,job=original;jid=job['id']
    with lab.store.db() as db:
        if fault=='not_completed':db.execute("UPDATE jobs SET status='failed' WHERE id=?",(jid,))
        elif fault=='malformed_original_event':
            db.execute("INSERT INTO events(at,kind,entity_id,details) VALUES(0,'trial_computation_started',?,'{')",(jid,))
        elif fault=='bad_result_digest':db.execute("UPDATE events SET details=? WHERE entity_id=? AND kind='result_saved'",(json.dumps(dict(sha256='not-a-sha256')),jid))
        elif fault=='bad_attempt_history':
            trial=db.execute('SELECT id FROM trial_plans WHERE job_id=? AND part=0',(jid,)).fetchone()[0]
            lab.store.event('trial_computation_started',jid,dict(trial_id=trial,part=0,window='report',attempt=True),db)
    if fault=='wrong_root_configuration':
        root=compressed_read(lab.output_path(jid));root['rows'][0]['config_id']='0'*64;_rehash_root(lab,jid,root)
    elif fault=='wrong_part_context':
        path=lab.output_path(jid).parent/'parts/000000.json.gz';part=compressed_read(path);part['payload_hash']='0'*64;compressed_write(path,part)
        root=compressed_read(lab.output_path(jid));root['rows'][0]['report_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();_rehash_root(lab,jid,root)
    with pytest.raises(StateError):reader.read_saved_family(lab,jid,'change_of_character')


def test_raw_numeric_configuration_identity_is_refused_before_saved_publication(reader,original):
    lab,first=original
    payload=copy.deepcopy(first['payload']);configuration=payload['configurations'][0]
    configuration['min_touches']=1.0
    payload.update(configurations=[configuration],count=1,sampling=None)
    # An internal raw payload keeps 1.0 while Strategy validates integer 1.
    # The original worker must reject that identity mismatch before publication.
    job=lab.store.create_job('search',payload)
    assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='failed'
    assert not lab.output_path(job['id']).exists()
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(job['id'],)).fetchone()[0]==0
    with pytest.raises(StateError):
        reader.read_saved_family(lab,job['id'],'change_of_character')


def test_original_serialization_size_expansion_and_object_shape_are_all_checked(reader,tmp_path,monkeypatch):
    path=tmp_path/'original.json.gz'
    monkeypatch.setattr(reader,'MAX_ARTIFACT_BYTES',100)
    path.write_bytes(b'x'*101)
    with pytest.raises(StateError,match='serialization'):
        reader._load(path,hashlib.sha256(path.read_bytes()).hexdigest())
    path.write_bytes(gzip.compress(json.dumps({'expanded':'x'*1000}).encode(),mtime=0))
    assert path.stat().st_size<100
    with pytest.raises(StateError,match='expansion'):
        reader._load(path,hashlib.sha256(path.read_bytes()).hexdigest())
    path.write_bytes(gzip.compress(b'[]',mtime=0))
    with pytest.raises(StateError,match='complete object'):
        reader._load(path,hashlib.sha256(path.read_bytes()).hexdigest())
