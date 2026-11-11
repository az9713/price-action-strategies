"""Actual isolated source mutations; no running-app edits and no source-scale claim."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.trace_privacy import Sanitizer
private=root/'data/private-evidence/spread-mutations'/out.name;private.mkdir(parents=True)
owned=root/'data/dev025'/('mutations-'+out.name[:22]);owned.mkdir(exist_ok=False)
specs=[
 ('score-sign','spread.py','total+=(2*SCALE//(k-1))','total-=(2*SCALE//(k-1))','tests/test_spread.py','fraction_oracle'),
 ('forty-boundary','spread.py',"if answer['signal_count']<settings.minimum_signals:","if answer['signal_count']<=settings.minimum_signals:",'tests/test_spread.py','every_plan_batch'),
 ('publication-integrity','spread.py','access();plan.verify();complete=not exhausted','access();complete=not exhausted','tests/test_spread.py','corruption_during_probe'),
 ('forgot-authority','spread.py','        authorize()\n','        pass\n','tests/test_spread.py','replay_corruption_and_authorization'),
 ('retry-ordinal','spread.py',"access();ordinal+=1;attempts+=1;emit(dict(kind='probe_started',**coordinate,attempt=ordinal))","access();ordinal=1;attempts+=1;emit(dict(kind='probe_started',**coordinate,attempt=ordinal))",'tests/test_spread.py','uncommitted_probe_result'),
 ('subset-cache-alias','service.py','key=(dataset_id,identity(manifest),warmup_start,end)+((tuple(selected),) if symbols is not None else ())','key=(dataset_id,identity(manifest),warmup_start,end)','tests/test_spread_probe.py','primary_subset_cache'),
 ('forgot-primary-predicate','service.py',"expected_manifest=context['dataset_manifest_hash'],symbols=[primary])","expected_manifest=context['dataset_manifest_hash'],symbols=None)",'tests/test_spread_probe.py','does_not_open_another'),
 ('ignored-news-hash','service.py',"if identity(calendar)!=context['news_calendar_hash']:raise DataError('Frozen spread news calendar hash changed.')","if False:raise DataError('Frozen spread news calendar hash changed.')",'tests/test_spread_probe.py','frozen_news_context'),
 ('boolean-count','spread.py',"type(answer['signal_count']) is not int","not isinstance(answer['signal_count'],int)",'tests/test_spread.py','bad_probe_counts'),
 ('forgot-price-guard','service.py',"        self.guard.access(selected,warmup_start,end,'final' if final_job_id else 'analysis',study_id,final_job_id)","        pass # owned mutant omits the pre-price guard",'tests/test_spread_probe.py','rejects_invalid_scope'),
]
inputs=[*sorted((source/'backend').rglob('*.py')),*sorted((source/'verification/fixtures').rglob('*')),
 *[source/p for p in ['pyproject.toml','RULEBOOK.md','strategy.schema.json','requirements.lock','tests/conftest.py','tests/test_spread.py','tests/test_spread_probe.py']]]
inputs=[p for p in inputs if p.is_file()];originals={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
def copy(name):
 destination=owned/name;destination.mkdir()
 for p in inputs:
  relative=p.relative_to(source);assert not p.is_symlink() and not any(part.lower().startswith('.env') for part in relative.parts)
  q=destination/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 return destination
def run(name,folder,args):
 evidence=out/name;evidence.mkdir();environment=os.environ.copy();environment['PYTHONPATH']=str(folder);environment['PYTHONNOUSERSITE']='1';environment['PA_EVIDENCE_RUN_DIR']=str(evidence)
 started=time.monotonic();result=subprocess.run([sys.executable,'-m','pytest','-q',*args,'--junitxml='+str(evidence/'junit.xml')],cwd=folder,env=environment,capture_output=True)
 scrub=Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')]);texts=[result.stdout.decode('utf-8',errors='replace'),result.stderr.decode('utf-8',errors='replace')]
 for value in texts:scrub.learn(value)
 lineage=[]
 for label,raw,text in zip(['stdout','stderr'],[result.stdout,result.stderr],texts):
  original=private/(name+'-'+label+'.log');original.write_bytes(raw);derived=evidence/(label+'.log');derived.write_text(scrub.clean(text),encoding='utf-8')
  lineage.append(dict(private_original=original.relative_to(root).as_posix(),original_sha256=hashlib.sha256(raw).hexdigest(),derived=derived.relative_to(out).as_posix(),derived_sha256=hashlib.sha256(derived.read_bytes()).hexdigest()))
 suites=list(ET.parse(evidence/'junit.xml').iter('testsuite'));counts={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
 value=dict(name=name,exit_code=result.returncode,elapsed_seconds=time.monotonic()-started,**counts,privacy_lineage=lineage)
 print(json.dumps({k:v for k,v in value.items() if k!='privacy_lineage'}),flush=True);return value,evidence
baseline,_=run('baseline',copy('baseline'),['tests/test_spread.py','tests/test_spread_probe.py'])
assert baseline['exit_code']==0 and baseline['tests']==47 and baseline['failures']==baseline['errors']==baseline['skipped']==0
mutants=[]
for name,module,before,after,test,selection in specs:
 folder=copy(name);path=folder/'backend/lab'/module;original=path.read_bytes();text=original.decode('utf-8');assert text.count(before)==1,(name,text.count(before));path.write_text(text.replace(before,after),encoding='utf-8')
 value,evidence=run(name,folder,[test,'-k',selection]);assert value['exit_code']==1 and value['failures']>0 and value['errors']==value['skipped']==0 and value['tests']>0,name
 shutil.copyfile(path,evidence/('mutated-'+module));value.update(original_sha256=hashlib.sha256(original).hexdigest(),mutated_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),target='backend/lab/'+module)
 mutants.append(value)
for name,digest in originals.items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
value=dict(scope=__doc__,baseline=baseline,mutants=mutants,all_test_killed=True,original_development_source_unchanged=True,main_running_app_unchanged=True,final_acceptance_certified=False)
(out/'spread-mutations.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(mutants_killed=len(mutants),green_baseline_cases=baseline['tests'],originals_unchanged=True,final_acceptance_certified=False)))
