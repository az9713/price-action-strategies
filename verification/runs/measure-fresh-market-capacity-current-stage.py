"""Actual durable numerical searches on a freshly acquired independent real sample."""
from pathlib import Path
from threading import Event,Timer
import hashlib,json,os,sys,time
root=Path.cwd();sys.path.insert(0,str(root/'data/dev027/research-src'))
from backend.lab.config import identity
from backend.lab.data import read_manifest
from backend.lab.models import Search
from backend.lab.research import core_hash,require_current_source
from backend.lab.service import Lab,compressed_read
from backend.lab.worker import Worker
from verification_resources import current_resources

contract=json.loads((root/'verification/runs/capacity-real-sample-contract.json').read_text(encoding='utf-8'))
origin_path=root/sys.argv[1];origin=json.loads(origin_path.read_text(encoding='utf-8'));count=int(sys.argv[2])
assert count in contract['counts'] and origin['fresh_provider_acquisition']
assert not origin['user_market_cache_copied'] and not origin['original_user_store_copied']
folder=(root/origin['benchmark_root']).resolve();assert folder.is_relative_to(root/'data/dev027/capacity-market')
require_current_source();lab=Lab(folder);dataset=origin['dataset_id'];manifest=read_manifest(lab.datasets_root,dataset)
assert manifest['quality']['eligible'] and manifest['quality']['symbols']==contract['symbols']
assert manifest['quality']['start']==manifest['quality']['end']==contract['selection']['start']
assert manifest['quality']['regular_rows']==390
request=Search(dataset_id=dataset,name='Fresh independent market capacity '+str(count),count=count,
    seed=contract['seed'],families=contract['families'],timeframes=contract['timeframes'],**contract['evaluation'])
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);measurements=[];progress=Worker._progress
def observed(worker,job,fraction,note,*a,**k):
    result=progress(worker,job,fraction,note,*a,**k)
    (out/'capacity-live-progress.json').write_text(json.dumps(dict(job_id=job['id'],count=count,
        fraction=fraction,note=note,resources=current_resources()),indent=2),encoding='utf-8')
    return result
Worker._progress=observed
try:
    for replica in range(2 if count==contract['pilot_count'] else 1):
        with lab.store.db() as db:
            pending = db.execute(
                "SELECT id FROM jobs WHERE status IN ('queued','running','canceling') LIMIT 1"
            ).fetchone()
        assert pending is None, 'Owned benchmark registry must have no other runnable jobs.'
        stop=Event();timer=Timer(contract['budget']['wall_seconds_per_count'],stop.set);timer.daemon=True
        started=time.perf_counter();timer.start()
        try:
            job=lab.create_experiment(request);created=time.perf_counter()
            worker=Worker(lab,stop);assert worker.run_once()
            elapsed=time.perf_counter()-started
        finally:timer.cancel()
        state=lab.store.job(job['id'])
        if state['status']!='completed':
            (out/'capacity-incomplete-diagnostic.json').write_text(json.dumps(dict(job_id=job['id'],count=count,
                elapsed_seconds=elapsed,status=state['status'],error=state['error'],checkpoint=state['checkpoint'],
                lease_failure=getattr(worker,'last_lease_failure',None),resources=current_resources(),
                completed_capacity=False),indent=2),encoding='utf-8')
        assert state['status']=='completed',(state['status'],state['error'],state['checkpoint'],getattr(worker,'last_lease_failure',None))
        result=lab.result(job['id']);assert result['count']==len(result['rows'])==count
        assert job['payload']['sampling']['unique']==count and len({r['config_id'] for r in result['rows']})==count
        with lab.store.db() as db:
            trials=[dict(r) for r in db.execute('SELECT state,attempts,reuses,artifact_sha256 FROM trial_plans WHERE job_id=?',(job['id'],))]
            attempts=db.execute('SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans t ON a.trial_id=t.id WHERE t.job_id=?',(job['id'],)).fetchone()[0]
        assert len(trials)==attempts==count and all(t['state']=='completed' and t['attempts']==1 and t['reuses']==0 and t['artifact_sha256'] for t in trials)
        records=[];signals=trades=0
        payload_hash=identity(job['payload']);manifest_hash=identity(manifest);subject_core=core_hash()
        for row in result['rows']:
            path=folder/'data/jobs'/job['id']/'parts'/(str(row['part']).zfill(6)+'.json.gz')
            raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest();assert digest==row['report_sha256']
            saved=compressed_read(path);report=saved['report']
            assert report['config_id']==row['config_id']==identity(job['payload']['configurations'][row['part']])
            assert saved['payload_hash']==payload_hash and report['core_hash']==subject_core and report['dataset_manifest_hash']==manifest_hash
            signals+=len(report['signals']);trades+=len(report['trades'])
            records.append(dict(part=row['part'],config_id=row['config_id'],sha256=digest,bytes=len(raw),signals=len(report['signals']),trades=len(report['trades'])))
        resources=current_resources();files=[p for p in (folder/'data/jobs'/job['id']).rglob('*') if p.is_file()]
        stored=sum(p.stat().st_size for p in files)
        item=dict(replica=replica,job_id=job['id'],count=count,creation_seconds=created-started,
            worker_complete_seconds=elapsed,complete_original_read_seconds=time.perf_counter()-started,
            configurations_per_second=count/elapsed,resources=resources,job_output_bytes=stored,
            job_output_files=len(files),signals=signals,trades=trades,trial_attempts=attempts,parts=records)
        (out/('capacity-replica-'+str(replica)+'.json')).write_text(json.dumps(item,indent=2),encoding='utf-8')
        measurements.append(item)
        assert elapsed<=contract['budget']['wall_seconds_per_count']
        assert resources['peak_working_set_bytes']<=contract['budget']['peak_working_set_bytes']
        assert stored<=contract['budget']['output_bytes_per_count']
        print(json.dumps({k:v for k,v in item.items() if k!='parts'}),flush=True)
    if len(measurements)==2:assert measurements[0]['parts']==measurements[1]['parts']
    require_current_source()
    (out/'capacity-summary.json').write_text(json.dumps(dict(scope=__doc__,core_hash=core_hash(),
        benchmark_root=origin['benchmark_root'],dataset_id=dataset,dataset_manifest_hash=identity(manifest),
        sample_regular_minute_rows=390,sample_sessions=1,workers=1,count=count,
        same_seed_complete_part_bytes_equal=True if len(measurements)==2 else None,
        no_user_data_or_credentials_copied=True,limitations=contract['limitations'],
        measurements=[{k:v for k,v in item.items() if k!='parts'} for item in measurements]),indent=2),encoding='utf-8')
finally:Worker._progress=progress
