"""Original paired work-unit contracts; financial parts are not supplied totals."""
import importlib
import importlib.util
import pytest

from backend.lab import trade_twin_jobs as jobs
from backend.lab.trade_twin_preparation import prepare
from backend.lab.store import StateError
from backend.lab.trade_twins import draw_set, EXECUTION_POLICIES
from test_trade_twin_source import original


def test_original_paired_financial_parts_are_implemented():
    assert importlib.util.find_spec('backend.lab.trade_twin_parts') is not None, 'Original paired financial parts are not implemented.'


@pytest.fixture
def parts():
    return importlib.import_module('backend.lab.trade_twin_parts')


@pytest.mark.parametrize('count,expected', [(0,100),(1,100),(10,100),(11,90),(100,10),(1000,1),(1001,1),(20000,1)])
def test_partition_is_declared_from_original_cohort_and_never_slices_a_large_set(parts, count, expected):
    spec = parts.partition(count)
    assert spec['sets_per_part'] == expected
    assert spec['part_count'] == (10000 + expected - 1) // expected
    assert spec['source_count'] == count
    ranges = [parts.part_range(spec, n) for n in range(spec['part_count'])]
    assert ranges[0][0] == 0 and ranges[-1][1] == 10000
    assert all(a[1] == b[0] for a,b in zip(ranges,ranges[1:]))


@pytest.mark.parametrize('count', [True,False,-1,20001,1.,'1',None])
def test_partition_rejects_implicit_or_out_of_bound_cohorts(parts,count):
    with pytest.raises(ValueError):parts.partition(count)


def owned(original, parts):
    lab,parent,_ = original
    child = jobs.create(lab,parent['id']);owner = 'paired-part-owner'
    job = lab.store.claim(owner)
    assert job['id'] == child['id']
    prepared = prepare(lab,job,owner)
    return lab,job,owner,prepared,parts.FinancialParts(lab,job,owner,prepared)


def test_actual_paired_part_freezes_original_draws_and_complete_financial_books(original,parts):
    from backend.lab.trade_twin_amounts import exact_total, read_amount
    lab,job,owner,prepared,journal = owned(original,parts)
    assert job['payload']['work_partition'] == parts.partition(len(prepared['plan'].sources))
    value = journal.execute(0)
    assert value['start'] == 0 and value['stop'] == 100
    assert len(value['sets']) == 200
    for row in value['sets']:
        ordinal = row['outcome']['set_index']
        assert row['draw'] == draw_set(prepared['plan'],job['payload']['seed'],ordinal)
        assert [m['source_id'] for m in row['members']] == [s.trade_id for s in prepared['plan'].sources]
        books = [journal.book(m['book_key'],m['book_sha256']) for m in row['members']]
        assert row['outcome']['trade_count'] == len(books)
        if all(b['status']=='complete' for b in books):
            assert read_amount(row['outcome']['net_profit']) == exact_total([b['net_profit'] for b in books])
        else:
            assert row['outcome']['state'] == 'failed' and row['outcome']['net_profit'] is None
    assert {r['outcome']['policy'] for r in value['sets']} == set(EXECUTION_POLICIES)
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state='checkpointed'",(job['id'],)).fetchone()[0] == 200
    lab.store.release(job['id'],owner)


def test_reopen_and_repeated_part_reuse_originals_without_new_financial_execution(original,parts,monkeypatch):
    lab,job,owner,prepared,journal = owned(original,parts)
    first = journal.execute(0)
    def forbidden(*args,**kwargs):raise AssertionError('A committed original part cannot be recomputed.')
    monkeypatch.setattr(parts,'execute_twin',forbidden)
    reopened = parts.FinancialParts(lab,job,owner,prepared)
    assert reopened.execute(0) == first
    assert len([e for e in lab.store.events(job['id']) if e['kind']=='twin_part_committed']) == 1
    with lab.store.db() as db:
        assert db.execute("SELECT MAX(attempts) FROM trial_plans WHERE job_id=? AND role='trade_twin_set'",(job['id'],)).fetchone()[0] == 1
    lab.store.release(job['id'],owner)


@pytest.mark.parametrize('damage',['part_file','commit_event','part_index','book_index','book_binding','trial_checkpoint'])
def test_committed_part_or_book_damage_cannot_be_replaced_by_new_computation(original,parts,damage):
    lab,job,owner,prepared,journal = owned(original,parts)
    journal.execute(0)
    if damage=='part_file':
        event = next(e for e in lab.store.events(job['id']) if e['kind']=='twin_part_committed')
        path = lab.output_path(job['id']).parent/'twins/parts'/event['details']['filename']
        path.write_bytes(path.read_bytes()+b'changed')
    else:
        with lab.store.db() as db:
            if damage=='commit_event':db.execute("DELETE FROM events WHERE entity_id=? AND kind='twin_part_committed'",(job['id'],))
            elif damage=='part_index':db.execute('DELETE FROM trade_twin_part_index WHERE job_id=?',(job['id'],))
            elif damage=='book_index':db.execute('DELETE FROM trade_twin_book_index WHERE job_id=?',(job['id'],))
            elif damage=='book_binding':db.execute("UPDATE trade_twin_book_index SET book_sha256=? WHERE job_id=?",('f'*64,job['id']))
            else:db.execute("DELETE FROM events WHERE entity_id=? AND kind='trial_checkpoint_saved' AND json_extract(details,'$.window')!='prepare'",(job['id'],))
    with pytest.raises(StateError):
        parts.FinancialParts(lab,job,owner,prepared).execute(0)
    lab.store.release(job['id'],owner)


def test_partial_computation_failure_retains_attempts_and_diagnostic_without_publishing_bank(original,parts,monkeypatch):
    lab,job,owner,prepared,journal = owned(original,parts)
    execute = parts.execute_twin;calls = []
    def fail(*args,**kwargs):
        calls.append(True)
        if len(calls)==2:raise ArithmeticError('Authored second-book numerical failure.')
        return execute(*args,**kwargs)
    monkeypatch.setattr(parts,'execute_twin',fail)
    with pytest.raises(ArithmeticError):journal.execute(0)
    assert not any(e['kind']=='twin_part_committed' for e in lab.store.events(job['id']))
    assert any(e['kind']=='twin_part_failed' for e in lab.store.events(job['id']))
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM trade_twin_book_index WHERE job_id=?',(job['id'],)).fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans t ON a.trial_id=t.id WHERE t.job_id=? AND t.role='trade_twin_set'",(job['id'],)).fetchone()[0] == 200
    lab.store.release(job['id'],owner)

def test_each_actual_saved_book_matches_independent_full_financial_reference(original,parts):
    from dataclasses import asdict
    from decimal import Decimal
    import json, os
    from pathlib import Path
    from verification.trade_twin_reference import execute_reference
    from test_trade_twin_execution import primitive
    lab,job,owner,prepared,journal=owned(original,parts)
    value=journal.execute(0);bars=primitive(prepared['regular'])
    def compare(actual,expected):
        if isinstance(expected,Decimal):
            assert isinstance(actual,str) and abs(Decimal(actual)-expected)<=Decimal('0.0000001')
        elif isinstance(expected,dict):
            assert set(actual)==set(expected)
            for key in expected:compare(actual[key],expected[key])
        elif isinstance(expected,list):
            assert len(actual)==len(expected)
            for a,b in zip(actual,expected):compare(a,b)
        else:assert type(actual) is type(expected) and actual==expected
    def external_json(value):
        if isinstance(value,Decimal):return str(value)
        if isinstance(value,dict):return {k:external_json(v) for k,v in value.items()}
        if isinstance(value,list):return [external_json(v) for v in value]
        return value
    records=[]
    for entry in value['books']:
        inputs=entry['inputs']
        expected=execute_reference(bars,inputs['match'],inputs['strategy'],inputs['costs'],inputs['portfolio'],[asdict(a) for a in prepared['actions']],inputs['policy'])
        compare(entry['book'],expected)
        records.append(dict(key=entry['key'],inputs=inputs,actual=entry['book'],independent_reference=external_json(expected)))
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        (Path(os.environ['PA_EVIDENCE_RUN_DIR'])/'actual-part-independent-financial-books.json').write_text(json.dumps(dict(bars=bars,actions=[asdict(a) for a in prepared['actions']],books=records,unique_books=len(records),occurrences=len(value['sets']),scope='Actual saved original synthetic-account paired part; complete reference comparison, not market-edge evidence.'),indent=2))
    assert records
    lab.store.release(job['id'],owner)


def test_closing_authority_failure_keeps_original_attempt_and_retry_never_adopts_orphan_books(original,parts,monkeypatch):
    lab,job,owner,prepared,journal=owned(original,parts)
    check=journal._authority;calls=[]
    def changed():
        calls.append(True)
        if len(calls)==2:raise StateError('Authored closing original source failure.')
        return check()
    monkeypatch.setattr(journal,'_authority',changed)
    with pytest.raises(StateError,match='closing original'):journal.execute(0)
    assert not any(e['kind']=='twin_part_committed' for e in lab.store.events(job['id']))
    path=journal.folder/'part-000000-attempt-000001.json.gz';original_bytes=path.read_bytes()
    with lab.store.db() as db:
        assert db.execute('SELECT COUNT(*) FROM trade_twin_book_index WHERE job_id=?',(job['id'],)).fetchone()[0]==0
    lab.store.release(job['id'],owner)
    new_owner='financial-retry';claimed=lab.store.claim(new_owner)
    again=prepare(lab,claimed,new_owner)
    result=parts.FinancialParts(lab,claimed,new_owner,again).execute(0)
    assert result['attempt']==2 and path.read_bytes()==original_bytes
    assert (journal.folder/'part-000000-attempt-000002.json.gz').is_file()
    lab.store.release(job['id'],new_owner)


def test_later_parts_reuse_only_exact_original_books_and_preserve_each_occurrence(original,parts,monkeypatch):
    from backend.lab.config import identity
    lab,job,owner,prepared,journal=owned(original,parts)
    first=journal.execute(0);old={b['key'] for b in first['books']}
    expected=set()
    for ordinal in range(100,200):
        draw=draw_set(prepared['plan'],job['payload']['seed'],ordinal)
        for policy in EXECUTION_POLICIES:
            for match in draw['matches']:expected.add(identity(journal._descriptor(match,policy)))
    execute=parts.execute_twin;calls=[]
    def counted(*args,**kwargs):
        calls.append(True);return execute(*args,**kwargs)
    monkeypatch.setattr(parts,'execute_twin',counted)
    second=journal.execute(1)
    assert len(calls)==len(expected-old)==len(second['books'])
    assert [r['outcome']['set_index'] for r in second['sets']]==[n for n in range(100,200) for _ in EXECUTION_POLICIES]
    journal._validate_values(second)
    lab.store.release(job['id'],owner)


def test_actual_unfillable_candidates_retain_all_failed_whole_sets_and_books(tmp_path,monkeypatch,parts):
    from conftest import minute_frame
    from backend.lab.service import Lab
    from backend.lab.data import prepare as prepare_data,normalize,save_dataset
    from backend.lab.models import Experiment
    from backend.lab.worker import Worker
    from test_reference_execution import CFG,ZERO,ACCOUNT,sig
    lab=Lab(tmp_path);frame=minute_frame('2026-11-04')
    frame.loc[14:18,'volume']=0
    manifest=save_dataset(lab.datasets_root,frame,dict(input_kind='synthetic',provider='unfillable candidate contract',corporate_actions_complete=True))
    regular=prepare_data(normalize(frame)[0]);signal=sig(regular,at=20)
    monkeypatch.setattr('backend.lab.service.generate_signals',lambda *a,**k:[signal])
    parent=lab.create_experiment(Experiment(dataset_id=manifest['id'],start='2026-11-04',end='2026-11-04',strategy=CFG,costs=ZERO,portfolio=ACCOUNT))
    assert Worker(lab).run_once() and lab.store.job(parent['id'])['status']=='completed'
    assert lab.result(parent['id'])['report']['trades']
    child=jobs.create(lab,parent['id']);owner='unfillable';job=lab.store.claim(owner)
    prepared=prepare(lab,job,owner);assert prepared['plan'].eligible
    result=parts.FinancialParts(lab,job,owner,prepared).execute(0)
    assert len(result['sets'])==200
    assert all(r['outcome']['state']=='failed' and r['outcome']['net_profit'] is None and r['members'] for r in result['sets'])
    assert all(b['book']['status']=='failed' and b['book']['rejected'] for b in result['books'])
    lab.store.release(job['id'],owner)

def test_one_unit_bounds_repeated_full_original_part_validation_without_omitting_book_checks(original,parts,monkeypatch):
    lab,job,owner,prepared,journal=owned(original,parts)
    journal.execute(0);load=journal._load;calls=[]
    def measured(*args,**kwargs):
        calls.append(args[0]);return load(*args,**kwargs)
    monkeypatch.setattr(journal,'_load',measured)
    value=journal.execute(1)
    assert len(value['sets'])==200 and len(calls)<=12
    lab.store.release(job['id'],owner)


@pytest.mark.parametrize('damage',['original_event_identity','original_file'])
def test_origin_authority_cannot_change_during_a_unit_even_when_book_bytes_are_cached(original,parts,monkeypatch,damage):
    lab,job,owner,prepared,journal=owned(original,parts)
    journal.execute(0);entry=journal._entry;changed=[]
    def altered(*args,**kwargs):
        result=entry(*args,**kwargs)
        if result is not None and not changed:
            changed.append(True)
            with lab.store.db() as db:
                event=db.execute("SELECT id,details FROM events WHERE entity_id=? AND kind='twin_part_committed'",(job['id'],)).fetchone()
                if damage=='original_event_identity':
                    new_id=db.execute('SELECT MAX(id)+100 FROM events').fetchone()[0]
                    db.execute('UPDATE events SET id=? WHERE id=?',(new_id,event['id']))
                    db.execute('UPDATE trade_twin_part_index SET event_id=? WHERE job_id=? AND part=0',(new_id,job['id']))
                else:
                    import json
                    path=journal.folder/json.loads(event['details'])['filename']
                    path.write_bytes(path.read_bytes()+b'changed during verified cache use')
        return result
    monkeypatch.setattr(journal,'_entry',altered)
    with pytest.raises(StateError):journal.execute(1)
    assert changed
    assert len([e for e in lab.store.events(job['id']) if e['kind']=='twin_part_committed'])==1
    lab.store.release(job['id'],owner)
