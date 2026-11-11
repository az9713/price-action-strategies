"""Real abrupt worker exits preserve committed units and recompute uncommitted work."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,sys
import pytest
from backend.lab import service
from backend.lab.config import identity
from backend.lab.service import compressed_read
from backend.lab.worker import Worker

spec=importlib.util.spec_from_file_location('actual_batch_recovery_fixture',Path(__file__).with_name('account-batch-financial-contracts.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
EXITS={'private_candidates':130,'first_promotion':131,'last_receipt':132,'closing_source':133,'committed_unit':134}


@pytest.mark.parametrize('phase',list(EXITS))
def test_actual_batch_worker_death_recovers_exact_original_financial_accounts(tmp_path,monkeypatch,phase):
    lab,job=fixture.build_case(tmp_path/'interrupted',9);marker=tmp_path/'actual-death.json'
    child=Path(__file__).with_name('account-batch-death-child.py')
    result=subprocess.run([sys.executable,str(child),str(lab.root),job['id'],phase,str(marker)],
        cwd=Path.cwd(),env=os.environ.copy(),capture_output=True,timeout=105)
    assert result.returncode==EXITS[phase],(result.returncode,result.stderr.decode(errors='replace')[-2000:])
    observed=json.loads(marker.read_text());committed=phase=='committed_unit'
    assert observed['phase']==phase and observed['actual_started_attempts']==8
    assert len(observed['originals'])==(8 if committed else 0)
    assert observed['report_files_visible']==dict(private_candidates=0,first_promotion=1,last_receipt=8,closing_source=8,committed_unit=8)[phase]
    # The exact owned child has observably exited. No live worker lease is reset.
    with lab.store.db() as db:db.execute('UPDATE jobs SET lease_until=0 WHERE id=?',(job['id'],))
    calls=[]
    def authored(frame,config,*a,**k):calls.append(config.level_age);return fixture.authored(frame,config,*a,**k)
    monkeypatch.setattr(service,'generate_signals',authored)
    assert Worker(lab).run_once() and lab.store.job(job['id'])['status']=='completed'
    assert calls==([104] if committed else list(range(96,105)))
    with lab.store.db() as db:
        rows=[dict(r) for r in db.execute('SELECT * FROM trial_plans WHERE job_id=? ORDER BY part',(job['id'],))]
        assert len(rows)==9 and [r['attempts'] for r in rows]==([1]*9 if committed else [2]*8+[1])
        assert all(r['state']=='completed' for r in rows)
        assert db.execute("SELECT COUNT(*) FROM events WHERE entity_id=? AND kind='result_saved'",(job['id'],)).fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM trial_attempts WHERE trial_id IN (SELECT id FROM trial_plans WHERE job_id=?)',(job['id'],)).fetchone()[0]==(9 if committed else 17)
    for part,digest in observed['files'].items():
        path=lab.output_path(job['id']).parent/'parts'/f'{int(part):06d}.json.gz'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    baseline,original=fixture.build_case(tmp_path/'uninterrupted',9)
    monkeypatch.setattr(service,'generate_signals',fixture.authored)
    assert Worker(baseline).run_once();expected,parts=fixture.original_parts(baseline,original)
    actual=lab.result(job['id'])
    assert actual['job_id']==job['id'] and expected['job_id']==original['id']
    assert {k:v for k,v in actual.items() if k!='job_id'}=={k:v for k,v in expected.items() if k!='job_id'}
    for row,(raw,value) in zip(rows,parts):
        path=lab.output_path(job['id']).parent/'parts'/f"{row['part']:06d}.json.gz"
        assert path.read_bytes()==raw and compressed_read(path)==value
        assert row['artifact_sha256']==hashlib.sha256(raw).hexdigest() and row['computed_sha256']==identity(value['report'])
    if os.environ.get('PA_EVIDENCE_RUN_DIR'):
        Path(os.environ['PA_EVIDENCE_RUN_DIR'],f'original-batch-death-{phase}.json').write_text(json.dumps(dict(
            scope=__doc__,phase=phase,actual_child_exit_code=result.returncode,committed_originals_preserved=len(observed['originals']),
            recovered_job=job['id'],recovered_accounts=9,recovery_financial_computations=len(calls),
            total_actual_attempts=9 if committed else 17,complete_original_part_bytes_equal=True,
            distinct_original_job_ids_verified=True,market_edge_claimed=False),indent=2),encoding='utf-8')
