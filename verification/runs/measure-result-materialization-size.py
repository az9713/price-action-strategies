"""Prespecified owned nonfinancial storage fixture; explicitly not numerical execution."""
from pathlib import Path
from types import SimpleNamespace
import gc,gzip,hashlib,json,os,sqlite3,sys,tempfile,time,tracemalloc
root=Path.cwd();sys.path.insert(0,str(root))
from backend.lab.store import Store
from backend.lab.config import canonical,identity
from backend.lab.result_index import ResultIndex
contract=json.loads((root/'verification/fixtures/result-materialization-size-contract.json').read_text(encoding='utf-8'));out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);observations=[]
with tempfile.TemporaryDirectory(prefix='owned-result-size-',dir=root/'data') as directory:
 owned=Path(directory).resolve();assert owned.is_relative_to((root/'data').resolve())
 for count in contract['counts']:
  lab=SimpleNamespace(root=owned/str(count));lab.store=Store(lab.root);index=ResultIndex(lab);jid='owned-storage-'+str(count)
  payload=dict(fixture_kind='nonfinancial_owned_storage',configurations=[dict(fixture_ordinal=n) for n in range(count)])
  raw=canonical(payload);payload_hash=identity(payload)
  with lab.store.db() as db:db.execute('INSERT INTO jobs(id,kind,payload,status,created,updated) VALUES(?,?,?,?,?,?)',(jid,'search',raw,'completed',0,0))
  folder=index.folder(jid);(folder/'parts').mkdir(parents=True)
  selected=count-1;ids=[identity(c) for c in payload['configurations']]
  report=dict(fixture_kind='nonfinancial_owned_storage',part=selected,config_id=ids[-1]);container=dict(config_id=ids[-1],payload_hash=payload_hash,report=report)
  part=gzip.compress(canonical(container).encode(),mtime=0);part_path=folder/'parts'/(str(selected).zfill(6)+'.json.gz');part_path.write_bytes(part);part_hash=hashlib.sha256(part).hexdigest()
  rows=[dict(part=n,config_id=ids[n],report_sha256=part_hash if n==selected else None,fixture_ordinal=n) for n in range(count)]
  accounts=[dict(part=n,config_id=ids[n],fixture_kind='nonfinancial_diagnostic') for n in range(count)]
  value=dict(job_id=jid,kind='search',payload_hash=payload_hash,fixture_kind='nonfinancial_owned_storage',rows=rows,search_statistics=dict(accounts=accounts),search_screen=dict(accounts=accounts))
  original=gzip.compress(canonical(value).encode(),mtime=0);path=folder/'result.json.gz';path.write_bytes(original);original_hash=hashlib.sha256(original).hexdigest()
  with lab.store.db() as db:lab.store.event('result_saved',jid,dict(sha256=original_hash),db)
  started=time.perf_counter();index.build(jid,value);build_seconds=time.perf_counter()-started
  # Reconcile every row and diagnostic against the original in a separate,
  # deliberately unbounded audit before the bounded-read measurement.
  with index.snapshot(jid) as (db,meta,event):
   all_rows=[json.loads(row[0]) for row in db.execute('SELECT value FROM rows ORDER BY part')]
   all_statistics=[json.loads(row[0]) for row in db.execute("SELECT value FROM auxiliary WHERE kind='statistics' ORDER BY part")]
   all_screen=[json.loads(row[0]) for row in db.execute("SELECT value FROM auxiliary WHERE kind='screen' ORDER BY part")]
  assert all_rows==rows and all_statistics==accounts and all_screen==accounts
  expected=dict(root_sha256=original_hash,rows_hash=identity(rows),statistics_hash=identity(accounts),screen_hash=identity(accounts),payload_hash=payload_hash,part_sha256=part_hash)
  del payload,raw,value,original,rows,accounts,all_rows,all_statistics,all_screen,ids;gc.collect()
  tracemalloc.start();started=time.perf_counter();summary=index.summary(jid);page=index.rows(jid,50,max(0,count-50));stats=index.auxiliary(jid,'statistics',20,max(0,count-20));screen=index.auxiliary(jid,'screen',20,max(0,count-20));selected_report=index.part(jid,selected);seconds=time.perf_counter()-started;current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
  assert selected_report==report and summary['row_count']==count and page['rows'][-1]['part']==selected and stats['accounts'][-1]['part']==selected and screen['accounts'][-1]['part']==selected
  summary_bytes=len(canonical(summary).encode());page_bytes=len(canonical(page).encode());assert summary_bytes<=contract['budgets']['summary_bytes'] and page_bytes<=contract['budgets']['page_bytes'] and peak<=contract['budgets']['read_python_heap_bytes']
  assert hashlib.sha256(path.read_bytes()).hexdigest()==original_hash and hashlib.sha256(part_path.read_bytes()).hexdigest()==part_hash
  observations.append(dict(count=count,build_seconds=build_seconds,read_seconds=seconds,read_traced_python_peak_bytes=peak,summary_bytes=summary_bytes,page_bytes=page_bytes,root_compressed_bytes=path.stat().st_size,derived_bytes=sum(p.stat().st_size for p in folder.glob('*.view.sqlite3')),all_rows_and_diagnostics_exact=True,numerical_accounts_executed=0,other_part_artifacts_certified=False,**expected))
result=dict(scope=contract['scope'],observations=observations,native_process_rss_measured=False,numerical_accounts_executed=0);(out/'result-materialization-size.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
