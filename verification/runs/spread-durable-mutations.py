"""Eight actual isolated persistence mutations with a green owned synthetic baseline."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.trace_privacy import Sanitizer
private=root/'data/private-evidence/spread-durable-mutations'/out.name;private.mkdir(parents=True)
owned=root/'data/dev025'/('durable-mutations-'+out.name[:22]);owned.mkdir(exist_ok=False)
specs=[
 ('assembly-hash','spread_preparation.py',"if size!=original['bytes'] or digest.hexdigest()!=original['sha256']:","if False:",'test_spread_preparation.py','batch_changed_after_commit'),
 ('append-owner','spread_jobs.py',"db.execute('BEGIN IMMEDIATE');self.store._trials.owned(db,self.job['id'],self.owner);self._binding(db);state,p=self._state(db)","db.execute('BEGIN IMMEDIATE');self._binding(db);state,p=self._state(db)",'test_spread_journal.py','failed_projection_or_lost_owner'),
 ('staged-parent','spread_jobs.py',"if phase.get('proposal_plan_id')!=sealed or any(r[k]!=v for k,v in expected.items())", "if any(r[k]!=v for k,v in expected.items())",'test_spread_journal.py','self_hashes and changed_parent_plan'),
 ('staged-owner','spread_jobs.py',"or [(a['ordinal'],a['owner']) for a in attempts]!=starts[part]", "or [a['ordinal'] for a in attempts]!=[a[0] for a in starts[part]]",'test_spread_journal.py','self_hashes and changed_attempt_owner'),
 ('final-evidence-recheck','spread_worker.py',"for envelope in journal.iter_envelopes():", "for envelope in []:",'test_spread_worker.py','late_committed_signal_corruption'),
 ('signal-context','spread_worker.py'," or report['context']!=context", "",'test_spread_worker_faults.py','new_signal_artifact and context'),
 ('saved-root-context','spread_worker.py',"['job_id','kind','payload_hash','core_hash','context','selection_manifest','selection_manifest_hash']", "['job_id','kind','payload_hash','core_hash','selection_manifest','selection_manifest_hash']",'test_spread_worker_faults.py','saved_root_recovery and context'),
 ('one-master-seed','models.py',"if 'seed' in self.settings and self.settings['seed']!=self.seed:","if False:",'test_spread_worker.py','one_master_seed'),
]
names=['test_spread_preparation.py','test_spread_journal.py','test_spread_worker.py','test_spread_worker_faults.py','test_spread_probe.py']
inputs=[*sorted((source/'backend').rglob('*.py')),*sorted((source/'verification/fixtures').rglob('*')),
 *[source/p for p in ['pyproject.toml','RULEBOOK.md','strategy.schema.json','requirements.lock','tests/conftest.py',*['tests/'+n for n in names]]]]
inputs=[p for p in inputs if p.is_file()];originals={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
def copy(name):
 destination=owned/name;destination.mkdir()
 for p in inputs:
  relative=p.relative_to(source);assert not p.is_symlink() and not any(part.lower().startswith('.env') for part in relative.parts)
  q=destination/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 return destination
def run(name,folder,args):
 evidence=out/name;evidence.mkdir();environment=os.environ.copy();environment['PYTHONPATH']=str(folder);environment['PYTHONNOUSERSITE']='1';environment['PA_EVIDENCE_RUN_DIR']=str(evidence)
 started=time.monotonic();result=subprocess.run([sys.executable,'-m','pytest','-q',*args,'--junitxml='+str(evidence/'junit.xml')],cwd=folder,env=environment,capture_output=True,timeout=360)
 scrub=Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')]);texts=[result.stdout.decode('utf-8',errors='replace'),result.stderr.decode('utf-8',errors='replace')]
 for value in texts:scrub.learn(value)
 lineage=[]
 for label,raw,value in zip(['stdout','stderr'],[result.stdout,result.stderr],texts):
  original=private/(name+'-'+label+'.log');original.write_bytes(raw);derived=evidence/(label+'.log');derived.write_text(scrub.clean(value),encoding='utf-8')
  lineage.append(dict(private_original=original.relative_to(root).as_posix(),original_sha256=hashlib.sha256(raw).hexdigest(),derived=derived.relative_to(out).as_posix(),derived_sha256=hashlib.sha256(derived.read_bytes()).hexdigest()))
 suites=list(ET.parse(evidence/'junit.xml').iter('testsuite'));counts={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
 value=dict(name=name,exit_code=result.returncode,elapsed_seconds=time.monotonic()-started,**counts,privacy_lineage=lineage)
 print(json.dumps({k:v for k,v in value.items() if k!='privacy_lineage'}),flush=True);return value,evidence
baseline,_=run('baseline',copy('baseline'),['tests/'+n for n in names])
assert baseline['exit_code']==0 and baseline['tests']>0 and baseline['failures']==baseline['errors']==baseline['skipped']==0
mutants=[]
for name,module,before,after,test,selection in specs:
 folder=copy(name);path=folder/'backend/lab'/module;original=path.read_bytes();value=original.decode('utf-8');assert value.count(before)==1,(name,value.count(before));path.write_text(value.replace(before,after),encoding='utf-8')
 value,evidence=run(name,folder,['tests/'+test,'-k',selection]);assert value['exit_code']==1 and value['failures']>0 and value['errors']==value['skipped']==0 and value['tests']>0,name
 shutil.copyfile(path,evidence/('mutated-'+module));value.update(original_sha256=hashlib.sha256(original).hexdigest(),mutated_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),target='backend/lab/'+module);mutants.append(value)
for name,digest in originals.items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
value=dict(scope=__doc__,baseline=baseline,mutants=mutants,all_test_killed=True,original_development_source_unchanged=True,main_running_app_unchanged=True,final_acceptance_certified=False)
(out/'spread-durable-mutations.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(mutants_killed=len(mutants),green_baseline_cases=baseline['tests'],originals_unchanged=True,final_acceptance_certified=False)))
