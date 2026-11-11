"""Update D039 status only after a complete coherent checkpoint; keep startup failure visible."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET
root=Path.cwd()
def latest(label):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1]
 r=json.loads(p.read_text(encoding='utf-8'));assert r['command']['exit_code']==0,label
 for name,digest in r['subject']['source_files'].items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name
 return p,r
checkpoint_path,checkpoint_receipt=latest('common-sampling-current-fourteen-receipt-source-fixture-build-recovery-checkpoint')
checkpoint=json.loads((root/next(a['path'] for a in checkpoint_receipt['artifacts'] if a['path'].endswith('/checkpoint.json'))).read_text(encoding='utf-8'));assert len(checkpoint['selected_receipts'])==14
keys={
 'full':'common-sampling-unchanged-source-serial-full-regression-and-seventeen-module-coverage',
 'coverage':'common-sampling-current-seventeen-module-numerical-coverage-gate',
 'existing':'common-sampling-current-main-fourteen-existing-desktop-workflows',
 'twenty':'common-sampling-current-twenty-existing-browser-accounts-independent-decimal',
 'six':'common-sampling-current-six-joint-study-accounts-independent-decimal-csv-offline',
 'runtime':'common-sampling-current-managed-main-duplicate-refusal-and-served-assets',
}
items={k:latest(label) for k,label in keys.items()}
full=items['full'][1];xml=root/next(a['path'] for a in full['artifacts'] if a['path'].endswith('junit.xml'));suites=list(ET.parse(xml).iter('testsuite'))
assert sum(int(s.attrib['tests']) for s in suites)==1579 and not any(int(s.attrib.get(k,0)) for s in suites for k in ['failures','errors','skipped'])
coverage=items['coverage'][1];gate=json.loads((root/next(a['path'] for a in coverage['artifacts'] if a['path'].endswith('/numerical-coverage-gate.json'))).read_text(encoding='utf-8'));assert gate['ready'] and len(gate['modules'])==17
for name in ['STATUS.md','verification/evidence-index.md']:
 p=root/name;old=p.read_text(encoding='utf-8');assert old.count('A full unchanged rerun is still required; no full0.19 regression pass is claimed here.')==1
 def link(path,title):return '['+title+']('+('verification/' if name=='STATUS.md' else '')+'receipts/'+path.name+')'
 old=old.replace('Current0.19 — common sampling verification in progress','Current0.19 — verified common sampling component checkpoint',1)
 old=old.replace('A full unchanged rerun is still required; no full0.19 regression pass is claimed here.','The '+link(items['full'][0],'full unchanged rerun')+' now passes all1579 tests with no failures/skips. '+link(items['coverage'][0],'All17 numerical coverage gates')+' meet the unchanged95% statements/90% branches; sampling.py reaches100%/100%. The first timeout remains retained and its root cause is unproved; no production change or deadline extension was made.',1)
 additions=link(items['existing'][0],'Fourteen existing desktop workflows')+' pass on this source. '+link(items['twenty'][0],'Twenty complete existing-workflow accounts')+' and '+link(items['six'][0],'Six complete joint-study accounts')+' independently reconcile. These are repeated software workflows, not independent market replications or a fresh profitable final test.\n\n'
 additions+=link(checkpoint_path,'Coherent recovery checkpoint')+f" verifies14 identical-source passing receipts/{checkpoint['artifact_files_checked']} artifacts and archives{checkpoint['source_archive_files']} source/fixture/build/input files. It separately preserves the unchanged failed full-run receipt. Credentials, all traces, source-video media, market caches and installed dependencies are excluded. This is not clean-install reproduction, global privacy certification or final422-case acceptance.\n\n"
 additions+=link(items['runtime'][0],'Latest managed-runtime and obsolete-endpoint check')+' confirms the current worker, idle queue, exact served assets and duplicate-store refusal. Known old health endpoints8768/8769/8770/8771 did not respond to bounded probes; this is not an OS-wide listener inventory certificate.\n\n'
 gap=sorted((root/'verification/receipts').glob('*-aggregate-provenance-authored-fresh-synthetic-job-api-csv-offline-first-contract.json'))[-1]
 assert json.loads(gap.read_text(encoding='utf-8'))['command']['exit_code']==1
 additions+=link(gap,'Fresh aggregate-provenance counterexample')+' confirms18 missing context fields/locations across a new synthetic job payload, saved aggregate, CSV and offline facts. D040 remains open; individual account provenance does not complete aggregate provenance. This failing contract is deliberately retained beside the passing D039 regression, and prevents a full-product completion claim.\n\n'
 measured=sorted((root/'verification/receipts').glob('*-common-sampling-prespecified-10-100-1000-queued-status-payload-measurement-no-account-execution.json'))[-1]
 additions+=link(measured,'Prespecified queued-status payload measurement')+' finds986799 bytes for one1000-configuration job and1112700 bytes for a three-job list. Counts100/1000 exceed the authored64KiB per-job diagnostic budget; this remains unfinished capacity work. The measurement executed no numerical accounts and started no server. Measurement completion is not a passing performance gate or a1000-search throughput benchmark.\n\n'
 marker='## Historical0.18';assert marker in old
 p.write_text(old.replace(marker,additions+marker,1),encoding='utf-8')
p=root/'verification/defects.json';defects=json.loads(p.read_text(encoding='utf-8'))
row=next(d for d in defects['defects'] if d['id']=='D-VERIFY-COMMON-WORKER-STARTUP-001')
row['status']='unchanged_isolated_and_full_serial_pass_root_cause_unproved_first_timeout_retained'
row['full_regression_receipt']=items['full'][0].relative_to(root).as_posix()
row['fix']+=' Full unchanged serial rerun passes1579; this is a nonreproduction, not proof of the original cause or an implemented production correction.'
p.write_text(json.dumps(defects,indent=2)+'\n',encoding='utf-8')
notes=root/'verification/runs/common-sampling-next-acceptance-notes.md'
notes.write_text('Current D039 checkpoint: full unchanged1579-case regression and all17 numerical gates now pass. The original timeout remains retained with unproved root cause. Source/fixture/build checkpoint: '+checkpoint_path.relative_to(root).as_posix()+'. The pre-checkpoint investigation wording below records chronology.\n\n'+notes.read_text(encoding='utf-8'),encoding='utf-8')
print(json.dumps(dict(full_tests=1579,numerical_module_gates=17,checkpoint_receipts=14,retained_original_timeout=True,final_acceptance=False)))
