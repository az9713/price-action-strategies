"""Actual one-worker durable search capacity on a frozen one-session historical sample."""
from pathlib import Path
from threading import Event,Timer
import hashlib,json,os,shutil,subprocess,sys,time
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.service import Lab,sample_configurations,compressed_read
from backend.lab.store import Store
from backend.lab.models import Search
from backend.lab.worker import Worker
from backend.lab.data import read_manifest
from backend.lab.config import identity
from backend.lab.research import core_hash
contract=json.loads((root/'verification/runs/capacity-real-sample-contract.json').read_text(encoding='utf-8'))
count=int(sys.argv[1]);assert count in contract['counts']
output=Path(os.environ['PA_EVIDENCE_RUN_DIR']);main=Lab(root)
instance=(root/'data/capacity-real-instance').resolve();instance.relative_to(root/'data')
if not instance.exists():
 store=Store(instance)
 with main.store.db() as source,store.db() as target:
  for table in ['studies','viewed_windows','events']:
   fields=[r[1] for r in source.execute('PRAGMA table_info('+table+')')]
   target.executemany('INSERT INTO '+table+' ('+','.join(fields)+') VALUES ('+','.join('?' for _ in fields)+')',source.execute('SELECT '+','.join(fields)+' FROM '+table).fetchall())
 lab=Lab(instance)
 shutil.copytree(main.datasets_root/contract['source_dataset_id'],lab.datasets_root/contract['source_dataset_id'])
 selected=lab.select(contract['source_dataset_id'],contract['symbols'],**contract['selection'])
 (instance/'selection.json').write_text(json.dumps(selected),encoding='utf-8')
else:lab=Lab(instance);selected=json.loads((instance/'selection.json').read_text(encoding='utf-8'))
dataset_id=selected['id'];manifest=read_manifest(lab.datasets_root,dataset_id)
assert manifest['quality']['eligible'] and manifest['quality']['symbols']==contract['symbols']
assert manifest['quality']['start']==contract['selection']['start'] and manifest['quality']['end']==contract['selection']['end']
main.guard.access(contract['symbols'],contract['selection']['start'],contract['evaluation']['end'],'external_capacity_benchmark')
request=Search(dataset_id=dataset_id,name='Frozen real-sample capacity '+str(count),count=count,seed=contract['seed'],families=contract['families'],timeframes=contract['timeframes'],**contract['evaluation'])
measurements=[]
for replica in range(2 if count==contract['pilot_count'] else 1):
 shutdown=Event();timer=Timer(contract['budget']['wall_seconds_per_count'],shutdown.set);timer.daemon=True
 start=time.perf_counter();timer.start();job=lab.create_experiment(request);created=time.perf_counter()
 Worker(lab,shutdown).run_once();elapsed=time.perf_counter()-start;timer.cancel()
 state=lab.store.job(job['id']);assert state['status']=='completed',(state['status'],state['error'],state['checkpoint'])
 result=lab.result(job['id']);assert result['count']==count and len(result['rows'])==count
 assert job['payload']['sampling']['unique']==count and len({r['config_id'] for r in result['rows']})==count
 with lab.store.db() as db:
  plans=db.execute('SELECT state,attempts,reuses,artifact_sha256 FROM trial_plans WHERE job_id=?',(job['id'],)).fetchall()
  attempts=db.execute('SELECT COUNT(*) FROM trial_attempts a JOIN trial_plans p ON a.trial_id=p.id WHERE p.job_id=?',(job['id'],)).fetchone()[0]
 assert len(plans)==attempts==count and all(p['state']=='completed' and p['attempts']==1 and p['reuses']==0 and p['artifact_sha256'] for p in plans)
 parts=[];signals=trades=0
 for row in result['rows']:
  path=instance/'data/jobs'/job['id']/'parts'/(str(row['part']).zfill(6)+'.json.gz');raw=path.read_bytes();digest=hashlib.sha256(raw).hexdigest()
  assert digest==row['report_sha256'];saved=compressed_read(path);report=saved['report']
  assert report['config_id']==row['config_id']==identity(job['payload']['configurations'][row['part']])
  assert saved['payload_hash']==identity(job['payload']) and report['core_hash']==core_hash() and report['dataset_manifest_hash']==identity(manifest)
  signals+=len(report['signals']);trades+=len(report['trades']);parts.append(dict(part=row['part'],config_id=row['config_id'],sha256=digest,bytes=len(raw),signals=len(report['signals']),trades=len(report['trades'])))
 # The OS high-water mark covers this complete Python process, including imports,
 # planning and result verification. It excludes the short memory-query child.
 peak=subprocess.run(['powershell.exe','-NoProfile','-Command','(Get-Process -Id '+str(os.getpid())+').PeakWorkingSet64'],capture_output=True,text=True,check=True)
 peak_bytes=int(peak.stdout.strip());files=[p for p in (instance/'data/jobs'/job['id']).rglob('*') if p.is_file()]
 size=sum(p.stat().st_size for p in files)
 assert elapsed<=contract['budget']['wall_seconds_per_count'] and peak_bytes<=contract['budget']['peak_working_set_bytes'] and size<=contract['budget']['output_bytes_per_count']
 item=dict(replica=replica,job_id=job['id'],count=count,creation_seconds=created-start,total_seconds=elapsed,configurations_per_second=count/elapsed,absolute_process_peak_working_set_bytes=peak_bytes,job_output_bytes=size,job_output_files=len(files),signals=signals,trades=trades,trial_attempts=attempts,parts=parts)
 measurements.append(item);(output/('replica-'+str(replica)+'.json')).write_text(json.dumps(item,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in item.items() if k!='parts'}),flush=True)
if count==contract['pilot_count']:
 assert measurements[0]['parts']==measurements[1]['parts'],'Identical request did not preserve complete saved-report bytes'
result=dict(scope=__doc__,core_hash=core_hash(),dataset_id=dataset_id,dataset_manifest_hash=identity(manifest),symbols=manifest['quality']['symbols'],sample_sessions=1,regular_minute_rows=390,workers=1,count=count,replicas=len(measurements),same_seed_complete_part_bytes_equal=True if len(measurements)==2 else None,limitations=contract['limitations'],measurements=[{k:v for k,v in m.items() if k!='parts'} for m in measurements])
(output/'capacity-summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
