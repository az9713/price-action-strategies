"""Actual original parts beyond the decoded LRU; warm reads keep live authority."""
from copy import deepcopy
from contextlib import contextmanager
from decimal import Decimal
import gzip,hashlib,importlib.util,json,os,time
from pathlib import Path
import pytest
from backend.lab import trade_twin_parts as parts
from backend.lab.config import canonical,identity
from backend.lab.store import StateError
from test_trade_twin_source import original
from test_trade_twin_parts import owned


def test_six_actual_parts_evicted_reads_exact_originals_and_warm_authority_faults(original,monkeypatch):
    lab,job,owner,prepared,journal=owned(original,parts)
    values=[];timings=[]
    for n in range(6):
        started=time.perf_counter();values.append(journal.execute(n));timings.append(time.perf_counter()-started)
    assert len(journal.cache)<=4 and journal.spec['expected_sets']==10000
    assert sum(len(v['sets']) for v in values)==1200
    assert len(journal.part_proofs)==5 # last newly published part is checked at next boundary
    opened=[];hashed=[];open_original=parts.gzip.open;hash_original=parts.file_hash
    def opening(*a,**k):opened.append(str(a[0]));return open_original(*a,**k)
    def hashing(*a,**k):hashed.append(str(a[0]));return hash_original(*a,**k)
    monkeypatch.setattr(parts.gzip,'open',opening);monkeypatch.setattr(parts,'file_hash',hashing)
    assert journal._prefix()==6
    opened.clear();hashed.clear();statements=[];db_original=lab.store.db
    @contextmanager
    def traced_db(*a,**k):
        with db_original(*a,**k) as db:
            db.set_trace_callback(statements.append)
            yield db
    with monkeypatch.context() as trace:
        trace.setattr(lab.store,'db',traced_db)
        with lab.store.control_reads():assert journal._prefix()==6 and journal._prefix()==6
    assert opened==[] and len(hashed)==12
    attempts_read=sum('SELECT * FROM trial_attempts WHERE trial_id=' in s for s in statements)
    assert attempts_read==2400
    first=values[0];assert first['books']
    journal.cache.clear();journal.cache_bytes=0
    with lab.store.control_reads(),journal._unit():
        journal._prefix();opened.clear()
        for _ in range(3):
            for entry in first['books']:
                assert journal.book(entry['key'],entry['sha256'])==entry['book']
        assert len(opened)==1
        detached=journal.book(first['books'][0]['key'],first['books'][0]['sha256']);detached['net_profit']='-999999'
        assert journal.book(first['books'][0]['key'],first['books'][0]['sha256'])==first['books'][0]['book']
        journal._prefix()
    assert journal.unit is None and journal.unit_books is None and journal.unit_book_sources is None
    with lab.store.control_reads(),journal._unit():
        journal._prefix()
        for value in values:
            journal._validate_values(value)
            for row in value['sets']:
                books=[journal.book(m['book_key'],m['book_sha256']) for m in row['members']]
                assert row['outcome']['state']=='completed'
                assert Decimal(row['outcome']['net_profit'])==sum((Decimal(b['net_profit']) for b in books),Decimal(0))
        journal._prefix()

    with lab.store.db() as db:
        trial=dict(db.execute("SELECT * FROM trial_plans WHERE job_id=? AND role='trade_twin_set' ORDER BY part,window LIMIT 1",(job['id'],)).fetchone())
        publication=dict(db.execute("SELECT * FROM events WHERE entity_id=? AND kind='twin_part_committed' ORDER BY id LIMIT 1",(job['id'],)).fetchone())
        checkpoint=dict(db.execute("SELECT * FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved' AND json_extract(details,'$.trial_id')=?",(job['id'],trial['id'])).fetchone())
        start=dict(db.execute("SELECT * FROM events WHERE entity_id=? AND kind='trial_computation_started' AND json_extract(details,'$.trial_id')=?",(job['id'],trial['id'])).fetchone())
        computed=dict(db.execute("SELECT * FROM events WHERE entity_id=? AND kind='trial_computation_recorded' AND json_extract(details,'$.trial_id')=?",(job['id'],trial['id'])).fetchone())
        binding=dict(db.execute('SELECT * FROM trade_twin_book_index WHERE job_id=? AND part=0 LIMIT 1',(job['id'],)).fetchone())
    mutations=[
        ('trial_plans','state','planned','id',trial['id'],trial['state']),
        ('trial_plans','computed_sha256','0'*64,'id',trial['id'],trial['computed_sha256']),
        ('trial_plans','artifact_sha256','0'*64,'id',trial['id'],trial['artifact_sha256']),
        ('trial_plans','attempts',trial['attempts']+1,'id',trial['id'],trial['attempts']),
        ('trial_attempts','computed_sha256','0'*64,'trial_id',trial['id'],trial['computed_sha256']),
        ('trial_attempts','state','started','trial_id',trial['id'],'checkpointed'),
        *[('events','details','{}','id',event['id'],event['details']) for event in [publication,checkpoint,start,computed]],
        ('trade_twin_book_index','book_offset',999999,'book_key',binding['book_key'],binding['book_offset']),
        ('trade_twin_book_index','book_sha256','0'*64,'book_key',binding['book_key'],binding['book_sha256']),
    ]
    refused=[]
    for table,column,bad,key,where,good in mutations:
        with lab.store.db() as db:db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(bad,where))
        try:
            with pytest.raises((StateError,ValueError)):journal._prefix()
            refused.append(table+'.'+column)
        finally:
            with lab.store.db() as db:db.execute(f'UPDATE {table} SET {column}=? WHERE {key}=?',(good,where))
        assert journal._prefix()==6
    path=journal.folder/json.loads(publication['details'])['filename'];raw=path.read_bytes()
    try:
        path.write_bytes(raw+b'changed')
        with pytest.raises(StateError):journal._prefix()
    finally:path.write_bytes(raw)
    assert journal._prefix()==6
    value=journal._load(0);saved=deepcopy(value);value['sets'][0]['members'][0]['source_id']='mutated-memory'
    with pytest.raises(StateError,match='cache changed'):journal._load(0)
    value.clear();value.update(saved)
    assert journal._load(0)==values[0]
    def forbidden(*a,**k):raise AssertionError('Committed financial outcomes must not be recomputed')
    monkeypatch.setattr(parts,'execute_twin',forbidden)
    # Preserved original reader verifies exactly the same original records.
    reference_path=Path(__file__).with_name('trade-twin-parts-original-pre-projection-verified.py')
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest()=='62039d8e540fa922c1baffbe4b40921d01724f38876b6b7b141e7c39883c73b3'
    assert b'PART_PROOF_BYTES' not in reference_path.read_bytes()
    spec=importlib.util.spec_from_file_location('backend.lab.original_parts_reference',reference_path)
    reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
    monkeypatch.setattr(reference,'execute_twin',forbidden)
    with lab.store.control_reads():old=reference.FinancialParts(lab,job,owner,prepared)
    assert old.execute(0)==journal.execute(0)==values[0]
    reopened=parts.FinancialParts(lab,job,owner,prepared)
    assert reopened.execute(0)==values[0]
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state IN ('checkpointed','completed')",(job['id'],)).fetchone()[0]==1200
        assert db.execute("SELECT MAX(attempts) FROM trial_plans WHERE job_id=? AND role='trade_twin_set'",(job['id'],)).fetchone()[0]==1
    out=os.environ.get('PA_EVIDENCE_RUN_DIR')
    if out:Path(out,'part-projection-actual-six-parts.json').write_text(json.dumps(dict(parts=6,actual_set_occurrences=1200,complete_control_comparison=False,sets_per_policy_required=10000,part_seconds=timings,warm_prefix_gzip_decodes=0,warm_prefix_original_file_hashes=12,warm_prefix_fresh_attempt_sql_reads=attempts_read,unit_original_gzip_decodes=1,authority_faults_refused=refused,original_reader_equal=True,original_reader_sha256=hashlib.sha256(reference_path.read_bytes()).hexdigest(),original_reference_matches_recorded_pre_optimization_source=True,reopen_equal=True),indent=2),encoding='utf-8')
    lab.store.release(job['id'],owner)


def test_projection_eviction_oversized_fallback_unit_limits_and_cancel(original,monkeypatch):
    lab,job,owner,prepared,journal=owned(original,parts);value=journal.execute(0);journal._prefix()
    proof_bytes=journal.part_proof_bytes
    assert proof_bytes>0
    monkeypatch.setattr(parts,'PART_PROOF_BYTES',proof_bytes)
    journal._remember_part(1,*[journal.part_proofs[0][0][0],value,[],[]])
    assert journal.part_proof_bytes<=proof_bytes
    monkeypatch.setattr(parts,'PART_PROOF_BYTES',1)
    journal.part_proofs.clear();journal.part_proof_bytes=0
    assert journal._prefix()==1 and not journal.part_proofs
    monkeypatch.setattr(parts,'UNIT_BOOK_ENTRIES',1)
    with journal._unit():
        journal._prefix();journal._load(0)
        assert len(journal.unit_books)<=1
        outer=journal.unit_books
        with journal._unit():assert journal.unit_books is not outer
        assert journal.unit_books is outer
        monkeypatch.setattr(parts,'UNIT_BOOK_BYTES',1)
        journal.unit_books.clear();journal.unit_book_bytes=0;journal.unit_book_sources.clear()
        journal._load(0);assert len(journal.unit_books)==0 and journal.unit_book_bytes==0
    journal.cancel=lambda:True
    with pytest.raises(InterruptedError):journal.book(value['books'][0]['key'],value['books'][0]['sha256'])
    journal.cancel=None
    lab.store.cancel(job['id'])
    with pytest.raises((StateError,InterruptedError)):journal._prefix()
