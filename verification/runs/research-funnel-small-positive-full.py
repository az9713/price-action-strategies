"""Actual both-10000-policy financial controls through original two-instrument final.

All data and signal clocks are authored. This verifies execution and original
research orchestration, not real detector efficacy or a profitable market edge.
"""
from collections import Counter
from decimal import Decimal
from pathlib import Path
import gzip,hashlib,importlib.util,json,os,time,uuid,zipfile
from backend.lab import research_funnel_jobs,research_funnel_final
from backend.lab.worker import Worker
from backend.lab.trade_twins import EXECUTION_POLICIES,TOTAL_SETS
from backend.lab.trade_twin_views import Originals
from backend.lab.research_funnel_exports import build_export
from verification_resources import current_resources

spec=importlib.util.spec_from_file_location('small_positive_full_fixture',Path(__file__).with_name('research-funnel-small-positive-controls.py'))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)

def test_actual_full_both_policy_controls_candidate_freeze_and_both_final_instruments(tmp_path,monkeypatch):
    project=Path(__file__).resolve().parents[2]
    out=Path(os.environ.get('PA_EVIDENCE_RUN_DIR',tmp_path))
    folder=project/'data/dev027/funnel-positive'/uuid.uuid4().hex
    started=time.perf_counter();progress=Worker._progress;resource_history=[]
    def record(worker,job,fraction,note,*args,**kwargs):
        value=progress(worker,job,fraction,note,*args,**kwargs)
        state=dict(job_id=job['id'],kind=job['kind'],fraction=fraction,note=note,elapsed_seconds=time.perf_counter()-started,
            authored_store=folder.relative_to(project).as_posix(),resources=current_resources())
        resource_history.append(state)
        (out/'positive-full-progress.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
        if job['kind']=='trade_twins':print(json.dumps(state),flush=True)
        return value
    monkeypatch.setattr(Worker,'_progress',record)
    lab,study,qualification,child=fixture.build_small_positive(folder,monkeypatch)
    print(json.dumps(dict(phase='original-five-arms-complete-controls-starting',study_id=study['id'],qualification_job_id=qualification['id'],
        control_job_id=child,authored_store=folder.relative_to(project).as_posix())),flush=True)
    assert TOTAL_SETS==10000 and len(EXECUTION_POLICIES)==2
    assert Worker(lab).run_once()
    child_job=lab.store.job(child)
    assert child_job['status']=='completed',child_job
    original=Originals(lab,child)
    counts={p:Counter() for p in EXECUTION_POLICIES};seen={p:set() for p in EXECUTION_POLICIES}
    real=Decimal(original.report['summaries'][EXECUTION_POLICIES[0]]['real_profit'])
    evidence=[]
    for header in original.headers:
        with lab.store.db() as db:
            db.execute('BEGIN');_,_,path=original.part(db,header['part'])
        raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==header['sha256']
        part=json.loads(gzip.decompress(raw))
        for row in part['sets']:
            result=row['outcome'];policy=result['policy'];ordinal=result['set_index']
            assert policy in counts and ordinal not in seen[policy] and result['trade_count']==41
            assert result['state']=='completed' and len(row['members'])==len(row['draw']['matches'])==41
            seen[policy].add(ordinal);counts[policy]['completed']+=1
            counts[policy]['exceedances']+=Decimal(result['net_profit'])>=real
        evidence.append(dict(part=header['part'],sha256=header['sha256'],bytes=len(raw),sets=len(part['sets'])))
    original.guard()
    for policy in EXECUTION_POLICIES:
        summary=original.report['summaries'][policy]
        assert seen[policy]==set(range(10000))
        assert summary['expected_sets']==summary['observed_sets']==summary['complete_sets']==10000
        assert summary['failed_sets']==0 and summary['exceedances']==counts[policy]['exceedances']
        assert summary['adapted_pass'] is (counts[policy]['exceedances']<500)
        assert summary['adapted_pass'] is True,summary
    with lab.store.db() as db:
        trial_count=db.execute("SELECT COUNT(*) FROM trial_plans WHERE job_id=? AND role='trade_twin_set' AND state='completed'",(child,)).fetchone()[0]
        assert trial_count==20000
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==0
    assert Worker(lab).run_once()
    assert lab.store.job(qualification['id'])['status']=='completed'
    qualified=research_funnel_jobs.inspect_qualification(lab,qualification['id'])
    assert len(qualified['candidate_freeze']['candidate_ids'])==1
    freeze=qualified['candidate_freeze'];final=research_funnel_final.create_final(lab,study['id'])
    assert Worker(lab).run_once()
    assert lab.store.job(final['id'])['status']=='completed'
    result=research_funnel_final.inspect_final(lab,final['id'])
    assert result['report']['instrument_count']==2 and result['report']['version_count']==1
    assert len(result['rows'])==1 and result['rows'][0]['candidate'] is True
    assert set(result['rows'][0]['reports'])=={'primary_final','replication_final'}
    for arm in result['rows'][0]['reports'].values():
        assert arm['metrics']['trades']==29 and arm['metrics']['net_profit']>0 and arm['final_gate_pass'] is True
    assert research_funnel_jobs.inspect_qualification(lab,qualification['id'])['candidate_freeze']==freeze
    with lab.store.db() as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='final_unlock_consumed'").fetchone()[0]==1
    exports=[]
    for jid,expected in [(qualification['id'],5),(final['id'],2)]:
        built=build_export(lab,jid,'zip')
        try:
            with zipfile.ZipFile(built['path']) as archive:
                manifest=json.loads(archive.read('manifest.json'))
                for name,record in manifest['entries'].items():
                    raw=archive.read(name)
                    assert hashlib.sha256(raw).hexdigest()==record['sha256'] and len(raw)==record['bytes']
                accounts=[name for name in archive.namelist() if name.startswith('accounts/')]
                assert len(accounts)==expected
            exports.append(dict(job_id=jid,sha256=hashlib.sha256(built['path'].read_bytes()).hexdigest(),bytes=built['path'].stat().st_size,
                original_phase_accounts=expected,all_member_hashes_verified=True))
        finally:built['path'].unlink(missing_ok=True)
    (out/'positive-full-original-evidence.json').write_text(json.dumps(dict(scope=__doc__,authored_store=folder.relative_to(project).as_posix(),
        elapsed_seconds=time.perf_counter()-started,study_id=study['id'],control_job_id=child,qualification_job_id=qualification['id'],final_job_id=final['id'],
        original_financial_trials=trial_count,original_source_trades=41,policies={p:dict(counts[p]) for p in EXECUTION_POLICIES},
        full_original_control_summaries=original.report['summaries'],original_financial_part_digests=evidence,candidate_freeze=freeze,
        final_report=result['report'],exports=exports,actual_detector_efficacy=False,real_market_edge_claimed=False,
        resources_at_completion=current_resources(),resource_observations=resource_history),indent=2),encoding='utf-8')
