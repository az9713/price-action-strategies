"""Read-only checks of the actual completed protocol-two synthetic workload.

No outcomes or original events are fabricated. Isolated SQLite backups and
copies of this authored synthetic store permit destructive fault tests. No
credentials, real user data, new simulation or reduced set count are used.
"""
from pathlib import Path
from contextlib import closing
import csv,gzip,hashlib,io,json,os,shutil,sqlite3,time,uuid,zipfile
import pytest
from fastapi.testclient import TestClient
import backend
ROOT=Path(__file__).resolve().parents[2]
SUBJECT=Path(os.environ.get('PA_EVIDENCE_SUBJECT',str(ROOT/'data/dev026/evidence-src'))).resolve()
assert SUBJECT.is_relative_to((ROOT/'data/dev026').resolve())
assert Path(backend.__file__).resolve().is_relative_to(SUBJECT),'The verification must import its explicitly frozen development subject, never the installed app.'
from backend.lab.api import create_app
from backend.lab.service import Lab
from backend.lab.config import canonical,identity
from backend.lab.trade_twin_views import repair_view

SOURCE=ROOT/'data/dev026/full-owned/20261110T010321700433Z/store'
JID='3b9f36b31fee4bae838f5a2f6e638049'
RUN=Path(os.environ['PA_EVIDENCE_RUN_DIR'])


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def clone(source,destination):
    assert source.resolve().is_relative_to((ROOT/'data/dev026').resolve())
    assert destination.resolve().is_relative_to((ROOT/'data/dev026/view-checks').resolve())
    shutil.copytree(source/'data',destination/'data',ignore=shutil.ignore_patterns('lab.sqlite3','lab.sqlite3-wal','lab.sqlite3-shm'))
    path=(source/'data/lab.sqlite3').resolve()
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as old,closing(sqlite3.connect(destination/'data/lab.sqlite3')) as new:old.backup(new)


def originals(lab):
    with lab.store.db() as db:
        trials=[dict(r) for r in db.execute('SELECT * FROM trial_plans WHERE job_id=? ORDER BY id',(JID,))]
        attempts=[dict(r) for r in db.execute('SELECT a.* FROM trial_attempts a JOIN trial_plans p ON p.id=a.trial_id WHERE p.job_id=? ORDER BY a.id',(JID,))]
        counts=dict(db.execute('SELECT kind,COUNT(*) FROM jobs GROUP BY kind'))
    return dict(root_sha256=sha(lab.output_path(JID)),trials_sha256=identity(trials),attempts_sha256=identity(attempts),job_counts=counts)


@pytest.fixture(scope='module')
def golden():
    assert SOURCE.is_dir(),'Run the actual full protocol-two workload before this saved-evidence gate.'
    for path in (SOURCE/'data/datasets').glob('*/manifest.json'):
        assert json.loads(path.read_text())['metadata']['input_kind']=='synthetic'
    reused=os.environ.get('PA_EVIDENCE_SAVED_GOLDEN')
    origin=Path(reused).resolve() if reused else SOURCE
    if reused:assert origin.is_relative_to((ROOT/'data/dev026/view-checks').resolve())
    folder=ROOT/'data/dev026/view-checks'/RUN.name.split('-')[0]/'golden';clone(origin,folder)
    lab=Lab(folder);before=originals(lab)
    assert lab.store.job(JID)['status']=='completed'
    began=time.perf_counter()
    if reused:
        from backend.lab.trade_twin_views import saved_view
        with saved_view(lab,JID):pass
        view=dict(financial_recomputations=0,reused_verified_original_derived_view=True)
    else:view=repair_view(lab,JID)
    seconds=time.perf_counter()-began
    assert view['financial_recomputations']==0 and originals(lab)==before
    rows={};books={};original_parts={}
    for path in sorted((lab.output_path(JID).parent/'twins/parts').glob('*.json.gz')):
        value=json.loads(gzip.decompress(path.read_bytes()));original_parts[path.name]=sha(path)
        for row in value['sets']:rows[row['outcome']['policy'],row['outcome']['set_index']]=row
        for entry in value['books']:books[entry['key']]=entry
    assert len(rows)==20000 and len(books)==28 and len(original_parts)==100
    (RUN/'positive-view-build.json').write_text(json.dumps(dict(job_id=JID,actual_original_sets=len(rows),actual_unique_books=len(books),view_build_seconds=seconds,
        original_financial_state_unchanged=True,view=view,scope=__doc__),indent=2),encoding='utf-8')
    return folder,rows,books,original_parts


@pytest.fixture
def client(golden,monkeypatch):
    source,*_=golden;folder=source.parent/uuid.uuid4().hex;clone(source,folder)
    app=create_app(folder,run_worker=False);lab=app.state.lab
    def forbidden(*a,**k):raise AssertionError('Saved evidence must not load prices, redraw assignments or simulate financial books.')
    monkeypatch.setattr(lab,'_evaluation_input',forbidden)
    monkeypatch.setattr(lab.store,'create_job',forbidden)
    monkeypatch.setattr('backend.lab.service.generate_signals',forbidden)
    monkeypatch.setattr('backend.lab.trade_twin_parts.execute_twin',forbidden)
    monkeypatch.setattr('backend.lab.trade_twins.draw_set',forbidden)
    with TestClient(app,base_url='http://localhost:8765',client=('127.0.0.1',51000)) as browser:
        token=browser.get('/api/session').json()['token'];browser.headers.update({'Origin':'http://localhost:8765','X-Lab-Token':token})
        yield browser,lab


def view_path(lab):
    event=next(e for e in reversed(lab.store.events(JID)) if e['kind']=='trade_twin_view_saved')
    return lab.output_path(JID).parent/'twins/views'/event['details']['filename']


def test_all_20000_actual_original_outcomes_are_returned_in_bounded_api_pages(client,golden):
    browser,lab=client;_,expected,_,_=golden;before=originals(lab);count=maximum=0;began=time.perf_counter()
    for policy in ['barrier_capped_elapsed_v1','fixed_elapsed_v1']:
        offset=0
        while True:
            response=browser.get('/api/jobs/'+JID+'/trade-twins/sets',params=dict(policy=policy,offset=offset,limit=100))
            assert response.status_code==200,response.text;maximum=max(maximum,len(response.content))
            value=response.json();assert value['pagination']['total']==10000 and value['pagination']['offset']==offset
            assert len(value['rows'])==100
            for row in value['rows']:
                assert row['outcome']==expected[policy,row['outcome']['set_index']]['outcome'];count+=1
            offset=value['pagination']['next_offset']
            if offset is None:break
        response=browser.get('/api/jobs/'+JID+'/trade-twins/sets',params=dict(policy=policy,offset=10000))
        assert response.status_code==200 and response.json()['rows']==[]
    assert count==20000 and maximum<8*1024*1024 and before==originals(lab)
    (RUN/'actual-20000-api-pages.json').write_text(json.dumps(dict(job_id=JID,verified_original_outcomes=count,
        maximum_observed_response_bytes=maximum,seconds=time.perf_counter()-began,original_financial_state_unchanged=True),indent=2),encoding='utf-8')


def test_actual_members_and_every_array_match_complete_original_books(client,golden):
    browser,lab=client;_,expected,books,_=golden;before=originals(lab)
    for policy in ['barrier_capped_elapsed_v1','fixed_elapsed_v1']:
        for ordinal in [0,9999]:
            value=browser.get(f'/api/jobs/{JID}/trade-twins/sets/{ordinal}/members',params=dict(policy=policy)).json()
            assert value['pagination']['total']==1
            row=value['rows'][0];assert row['member']==expected[policy,ordinal]['members'][0]
            assert row['assignment']==expected[policy,ordinal]['draw']['matches'][0]
            book=books[row['member']['book_key']]['book']
            for kind in ['ledger','equity','encounters','rejected']:
                response=browser.get(f'/api/jobs/{JID}/trade-twins/sets/{ordinal}/books/0',params=dict(policy=policy,kind=kind))
                assert response.status_code==200,response.text;page=response.json()
                assert page['book']=={k:v for k,v in book.items() if k not in ['ledger','equity','encounters','rejected']}
                assert page['pagination']['total']==len(book[kind]) and page['rows']==book[kind][:25]
    assert before==originals(lab)


def test_complete_positive_zip_csv_and_standalone_report_have_no_missing_originals(client,golden):
    browser,lab=client;_,expected,books,parts=golden;before=originals(lab)
    response=browser.get('/api/jobs/'+JID+'/trade-twins/export')
    assert response.status_code==200,response.text
    assert response.headers['X-Evidence-SHA256']==hashlib.sha256(response.content).hexdigest()
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.testzip() is None;complete=json.loads(archive.read('COMPLETE.json'))
        assert complete['financial_occurrences']==20000 and complete['original_trials']==20001 and complete['unique_books']==28
        assert complete['tabular_rows']['sets']==complete['tabular_rows']['members']==20000
        for filename,digest in parts.items():assert hashlib.sha256(archive.read('original-parts/'+filename)).hexdigest()==digest
        sets=list(csv.DictReader(io.StringIO(archive.read('sets.csv').decode())))
        assert len(sets)==20000
        for row in sets:assert row['net_profit']==expected[row['policy'],int(row['set_index'])]['outcome']['net_profit']
        assert len(list(csv.DictReader(io.StringIO(archive.read('books.csv').decode()))))==28
        histories=list(csv.DictReader(io.StringIO(archive.read('financial-records.csv').decode())))
        for row in histories:assert json.loads(row['exact_record_json'])==books[row['book_key']]['book'][row['kind']][int(row['record_index'])]
        assert len(histories)==sum(len(entry['book'][kind]) for entry in books.values() for kind in ['ledger','equity','encounters','rejected'])
        assert b'https://www.youtube.com/watch?v=z97PnFIPoFg' in archive.read('standalone-report.html')
        assert b'<script' not in archive.read('standalone-report.html')
    assert before==originals(lab)
    (RUN/'complete-positive-export.json').write_text(json.dumps(dict(job_id=JID,download_sha256=hashlib.sha256(response.content).hexdigest(),download_bytes=len(response.content),completion=complete,
        original_part_hashes_checked=len(parts),exact_csv_outcomes_checked=len(sets),complete_financial_records_checked=len(histories),original_financial_state_unchanged=True),indent=2),encoding='utf-8')


@pytest.mark.parametrize('fault',['derived_row','derived_and_trial','derived_chunk','derived_book_manifest','missing_set','missing_computation','computation_order','checkpoint','original_part','part_index','book_index','trial_state','root_bytes','part_order','prep_order','manifest_event','manifest_order','publication_order'])
def test_rehashed_derived_views_and_damaged_originals_are_refused(client,golden,fault):
    browser,lab=client;policy='barrier_capped_elapsed_v1';path=view_path(lab)
    expected=golden[1][policy,0];key=expected['members'][0]['book_key']
    if fault.startswith('derived') or fault=='missing_set':
        with closing(sqlite3.connect(path)) as cache,cache:
            if fault in {'derived_row','derived_and_trial'}:
                row=json.loads(gzip.decompress(cache.execute('SELECT value FROM sets WHERE policy=? AND ordinal=0',(policy,)).fetchone()[0]));row['outcome']['net_profit']='1000'
                cache.execute('UPDATE sets SET value=?,row_hash=? WHERE policy=? AND ordinal=0',(gzip.compress(canonical(row).encode(),mtime=0),identity(row),policy))
            elif fault=='derived_chunk':
                chunk=json.loads(gzip.decompress(cache.execute("SELECT value FROM chunks WHERE book_key=? AND kind='ledger' AND ordinal=0",(key,)).fetchone()[0]));chunk[0]['cash_after']='1000000'
                cache.execute("UPDATE chunks SET value=? WHERE book_key=? AND kind='ledger' AND ordinal=0",(gzip.compress(canonical(chunk).encode(),mtime=0),key))
            elif fault=='derived_book_manifest':
                value=json.loads(gzip.decompress(cache.execute('SELECT evidence FROM books WHERE book_key=?',(key,)).fetchone()[0]));value['scalar_fields']['net_profit']='1000'
                cache.execute('UPDATE books SET evidence=?,evidence_sha256=? WHERE book_key=?',(gzip.compress(canonical(value).encode(),mtime=0),identity(value),key))
            else:cache.execute('DELETE FROM sets WHERE policy=? AND ordinal=9999',(policy,))
    with lab.store.db() as db:
        if fault=='derived_and_trial':
            trial=lab.store._trials.row(db,JID,0,policy);digest=identity(row)
            db.execute('UPDATE trial_plans SET computed_sha256=? WHERE id=?',(digest,trial['id']))
            db.execute('UPDATE trial_attempts SET computed_sha256=? WHERE trial_id=?',(digest,trial['id']))
        elif fault in {'missing_computation','computation_order','checkpoint'}:
            trial=lab.store._trials.row(db,JID,0,policy);kind='trial_checkpoint_saved' if fault=='checkpoint' else 'trial_computation_recorded'
            event=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind=? AND json_extract(details,'$.trial_id')=?",(JID,kind,trial['id'])).fetchone()
            if fault=='missing_computation':db.execute('DELETE FROM events WHERE id=?',(event['id'],))
            elif fault=='computation_order':db.execute('UPDATE events SET id=(SELECT MAX(id)+1 FROM events) WHERE id=?',(event['id'],))
            else:
                details=json.loads(event['details']);details['sha256']='f'*64;db.execute('UPDATE events SET details=? WHERE id=?',(canonical(details),event['id']))
        elif fault=='part_index':db.execute('UPDATE trade_twin_part_index SET event_id=event_id+1 WHERE job_id=? AND part=0',(JID,))
        elif fault=='book_index':db.execute('UPDATE trade_twin_book_index SET book_offset=book_offset+1 WHERE job_id=? AND book_key=?',(JID,key))
        elif fault=='trial_state':db.execute("UPDATE trial_plans SET state='computed' WHERE job_id=? AND part=0 AND window=?",(JID,policy))
        elif fault=='part_order':
            event=db.execute("SELECT id FROM events WHERE entity_id=? AND kind='twin_part_committed' AND json_extract(details,'$.part')=0",(JID,)).fetchone()[0]
            moved=db.execute('SELECT MAX(id)+1 FROM events').fetchone()[0]
            db.execute('UPDATE events SET id=? WHERE id=?',(moved,event));db.execute('UPDATE trade_twin_part_index SET event_id=? WHERE job_id=? AND part=0',(moved,JID))
        elif fault in {'prep_order','manifest_order','publication_order','manifest_event'}:
            kind='twin_preparation_sealed' if fault=='prep_order' else 'result_saved' if fault=='publication_order' else 'twin_financial_manifest_saved'
            event=db.execute('SELECT id FROM events WHERE entity_id=? AND kind=?',(JID,kind)).fetchone()[0]
            if fault=='manifest_event':db.execute('DELETE FROM events WHERE id=?',(event,))
            else:db.execute('UPDATE events SET id=(SELECT MAX(id)+1 FROM events) WHERE id=?',(event,))
    if fault=='original_part':
        part=next((lab.output_path(JID).parent/'twins/parts').glob('part-000000-*.json.gz'));part.write_bytes(part.read_bytes()+b'corrupt')
    elif fault=='root_bytes':lab.output_path(JID).write_bytes(lab.output_path(JID).read_bytes()+b'corrupt')
    if fault=='prep_order':
        # The authorized original reader must refuse this before any rows are
        # requested. A later per-row guard cannot authorize its constructor.
        from backend.lab.trade_twin_views import Originals
        from backend.lab.store import StateError
        with pytest.raises(StateError):Originals(lab,JID)
    endpoint=f'/api/jobs/{JID}/trade-twins/sets/0/books/0' if fault in {'derived_chunk','derived_book_manifest','book_index'} else f'/api/jobs/{JID}/trade-twins/sets'
    response=browser.post(f'/api/jobs/{JID}/trade-twins/repair-view',json={}) if fault=='prep_order' else browser.get(endpoint,params=dict(policy=policy))
    assert response.status_code==409,(fault,response.text[:1000])
