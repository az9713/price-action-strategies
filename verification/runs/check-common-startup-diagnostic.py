"""Retain the actual startup failure, unchanged isolated pass, and overlapping run times.
Overlap is evidence of concurrent load, not proof of the timeout's root cause.
"""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
labels={
 'full':'common-sampling-current-full-regression-and-seventeen-module-coverage',
 'isolated':'common-sampling-retained-worker-startup-failure-same-envelope-isolated-diagnostic',
 'mutations':'common-sampling-twelve-isolated-critical-source-mutations',
 'browser':'common-sampling-complete-assumptions-grid-random-calendar-two-desktop-workflows',
}
receipts={k:json.loads(sorted((root/'verification/receipts').glob('*-'+v+'.json'))[-1].read_text(encoding='utf-8')) for k,v in labels.items()}
for r in receipts.values():
 for name,digest in r['subject']['source_files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
full,isolated=receipts['full'],receipts['isolated']
assert full['command']['exit_code']==1 and isolated['command']['exit_code']==0
def suites(r):
 p=root/next(a['path'] for a in r['artifacts'] if a['path'].endswith('junit.xml'))
 return list(ET.parse(p).iter('testsuite'))
fs,is_=suites(full),suites(isolated)
assert sum(int(s.attrib['tests']) for s in fs)==1579
assert sum(int(s.attrib['failures']) for s in fs)==1
failures=[t for s in fs for t in s.findall('testcase') if t.find('failure') is not None]
assert len(failures)==1 and failures[0].attrib['name']=='test_actual_spawned_worker_process_and_clean_shutdown'
assert 'Worker did not become ready' in failures[0].find('failure').text
assert len(is_)==1 and is_[0].attrib['tests']=='1' and is_[0].attrib['failures']=='0'
properties={p.attrib['name']:float(p.attrib['value']) for p in is_[0].iter('property')}
assert properties['worker_startup_seconds']<60 and properties['three_session_job_seconds']<20
start=datetime.fromisoformat(full['started_at_utc']);end=datetime.fromisoformat(full['finished_at_utc'])
overlap={k:max(0,(min(end,datetime.fromisoformat(r['finished_at_utc']))-max(start,datetime.fromisoformat(r['started_at_utc']))).total_seconds()) for k,r in receipts.items() if k in {'mutations','browser'}}
assert all(v>0 for v in overlap.values())
value=dict(scope=__doc__,tests=1579,original_passes=1578,original_failures=1,isolated_properties=properties,overlapping_execution_seconds=overlap,thresholds_unchanged=True,production_source_changed=False,root_cause='Unproved. Concurrent mutation/browser execution overlapped; isolated unchanged test passed. Full unchanged rerun remains required.',receipts={k:r['receipt_id'] for k,r in receipts.items()})
(out/'startup-diagnostic.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value,indent=2))
