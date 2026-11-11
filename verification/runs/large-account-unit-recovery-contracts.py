"""Real native process deaths before and after a 64-account publication commit."""
from pathlib import Path
import hashlib,importlib.util,json,os
import pytest
from backend.lab import service
from backend.lab.config import identity
from backend.lab.service import compressed_read
from backend.lab.worker import Worker
from owned_death_probe import run_probe

spec=importlib.util.spec_from_file_location('large_unit_recovery_financial_fixture',Path(__file__).with_name('account-batch-financial-contracts.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
EXITS={'private_candidates':130,'first_promotion':131,'last_receipt':132,'closing_source':133,'committed_unit':134}


@pytest.mark.parametrize('phase',list(EXITS))
def test_actual_large_unit_death_recovers_every_original_account(tmp_path,monkeypatch,phase):
    lab,job=fixture.build_case(tmp_path/'interrupted',65)
    marker=tmp_path/'actual-large-unit-death.json';ready=tmp_path/'large-unit-ready.json'
    child=Path(__file__).with_name('large-account-unit-death-child.py')
    result=run_probe(child,[str(lab.root),job['id'],phase,str(marker)],ready)
    assert result.returncode==EXITS[phase],(result.returncode,result.stderr.decode(errors='replace')[-2000:])
    observed=json.loads(marker.read_text());control=json.loads(ready.with_suffix('.controller.json').read_text())
    assert control['actual_process_exited'] and not control['timed_out'] and control['exit_code']==EXITS[phase]
    assert control['startup_seconds'] is not None
    committed=phase=='committed_unit'
    assert observed['phase']==phase and observed['actual_started_attempts']==64
    assert len(observed['originals'])==(64 if committed else 0)
    assert observed['report_files_visible']==dict(private_candidates=0,first_promotion=1,last_receipt=64,closing_source=64,committed_unit=64)[phase]
    # The controller owns and has joined this exact exited interpreter.
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
    calls=[]
    def authored(frame,config,*args,**kwargs):calls.append(config.level_age);return fixture.authored(frame,config,*args,**kwargs)
    monkeypatch.setattr(service,'generate_signals',authored)
    assert Worker(lab).run_once() and lab.store.job_status(job['id'])['status']=='completed'
    assert calls==([160] if committed else list(range(96,161)))
    with lab.store.db() as db:
        rows=[dict(r) for r in db.execute('SELECT * FROM trial_plans WHERE job_id=? ORDER BY part',(job['id'],))]
        assert len(rows)==65 and [r['attempts'] for r in rows]==([1]*65 if committed else [2]*64+[1])
        assert all(row['state']=='completed' for row in rows)
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(job['id'],)).fetchone()[0]==1
        actual_attempts=db.execute('SELECT COUNT(*) FROM trial_attempts WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=?)',(job['id'],)).fetchone()[0]
        assert actual_attempts==(65 if committed else 129)
    for part,digest in observed['files'].items():
        path=lab.output_path(job['id']).parent/'parts'/f'{int(part):06d}.json.gz'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    baseline,original=fixture.build_case(tmp_path/'uninterrupted',65)
    monkeypatch.setattr(service,'generate_signals',fixture.authored)
    assert Worker(baseline).run_once();expected,parts=fixture.original_parts(baseline,original)
    actual=lab.result(job['id'])
    assert actual['job_id']==job['id'] and expected['job_id']==original['id'] and job['id']!=original['id']
    assert {k:v for k,v in actual.items() if k!='job_id'}=={k:v for k,v in expected.items() if k!='job_id'}
    for row,(raw,value) in zip(rows,parts):
        path=lab.output_path(job['id']).parent/'parts'/f"{row['part']:06d}.json.gz"
        assert path.read_bytes()==raw and compressed_read(path)==value
        assert row['artifact_sha256']==hashlib.sha256(raw).hexdigest() and row['computed_sha256']==identity(value['report'])
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        Path(os.environ['PA_EVIDENCE_RUN_DIR'],f'large-original-batch-death-{phase}.json').write_text(json.dumps(dict(
            scope=__doc__,phase=phase,actual_child_exit_code=result.returncode,controller=control,
            committed_originals_preserved=len(observed['originals']),recovered_accounts=65,
            recovery_financial_computations=len(calls),total_actual_attempts=actual_attempts,
            complete_original_part_bytes_equal=True,distinct_original_job_ids_verified=True,
            market_edge_claimed=False),indent=2),encoding='utf-8')
