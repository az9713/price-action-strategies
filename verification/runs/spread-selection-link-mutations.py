"""Actual isolated selected-envelope, reverse-reservation and repair guard mutations; original app/source never edited."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev025/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.trace_privacy import Sanitizer
private=root/'data/private-evidence/spread-selection-link-mutations'/out.name;private.mkdir(parents=True)
owned=root/'data/dev025'/('selection-link-mutations-'+out.name[:22]);owned.mkdir(exist_ok=False)
specs=[('orphan-continuation', 'store.py', "if (existing is None and children) or (existing is not None and children!=[existing['child_id']]):", 'if False:', 'test_spread_orphan_reservation.py', 'both_parent_side and continue'), ('orphan-status', 'spread_jobs.py', "if children:raise StateError('An original account child remains but its parent relationship is missing; a replacement is not authorized.')", "if False:raise StateError('An original account child remains but its parent relationship is missing; a replacement is not authorized.')", 'test_spread_orphan_reservation.py', 'both_parent_side and status'), ('repair-original-result', 'spread_jobs.py', "if not isinstance(result_event,dict) or result_event.get('sha256')!=event['result_sha256']:", 'if False:', 'test_spread_link_repair.py', 'cannot_invent and result_event'), ('selected-envelope', 'spread_jobs.py', " or identity(body)!=r['event_sha256'] or body['payload_sha256']!=job['payload_sha256']", " or body['payload_sha256']!=job['payload_sha256']", 'test_spread_selection_pages.py', 'changed_or_missing_selected and envelope'), ('selected-count', 'spread_jobs.py', 'if count!=expected or count>len(settings.families)*settings.per_family:', 'if False:', 'test_spread_selection_pages.py', 'changed_or_missing_selected and deleted_selected'), ('reverse-index-definition', 'store.py', "if schema is None or schema['bytes']>4096 or ''.join(schema['sql'].split()).lower()!=''.join(SPREAD_CHILD_PARENT_INDEX_SQL.split()).lower():", 'if False:', 'test_spread_orphan_reservation.py', 'reverse_reservation_index and wrong_definition')]

tests=['test_spread_orphan_reservation.py','test_spread_link_repair.py','test_spread_selection_pages.py']
support=['test_spread_probe.py','test_spread_worker.py','test_spread_api.py','test_reference_execution.py','test_spread_account_handoff.py']
inputs=[*sorted((source/'backend').rglob('*.py')),*sorted((source/'verification').glob('*.py')),*sorted((source/'verification/fixtures').rglob('*')),
 *[source/p for p in ['pyproject.toml','RULEBOOK.md','strategy.schema.json','requirements.lock','tests/conftest.py',*['tests/'+n for n in tests+support]]]]
inputs=[p for p in inputs if p.is_file()];originals={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
def copy(name):
 folder=owned/name;folder.mkdir()
 for p in inputs:
  relative=p.relative_to(source);assert not p.is_symlink() and not any(part.lower().startswith('.env') for part in relative.parts)
  q=folder/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 return folder
def run(name,folder,args):
 evidence=out/name;evidence.mkdir();environment=os.environ.copy();environment['PYTHONPATH']=str(folder);environment['PYTHONNOUSERSITE']='1';environment['PA_EVIDENCE_RUN_DIR']=str(evidence)
 started=time.monotonic();p=subprocess.run([sys.executable,'-m','pytest','-q',*args,'--junitxml='+str(evidence/'junit.xml')],cwd=folder,env=environment,capture_output=True,timeout=600)
 scrub=Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')]);texts=[p.stdout.decode('utf-8',errors='replace'),p.stderr.decode('utf-8',errors='replace')]
 for value in texts:scrub.learn(value)
 lineage=[]
 for label,raw,value in zip(['stdout','stderr'],[p.stdout,p.stderr],texts):
  original=private/(name+'-'+label+'.log');original.write_bytes(raw);derived=evidence/(label+'.log');derived.write_text(scrub.clean(value),encoding='utf-8')
  lineage.append(dict(private_original=original.relative_to(root).as_posix(),original_sha256=hashlib.sha256(raw).hexdigest(),derived=derived.relative_to(out).as_posix(),derived_sha256=hashlib.sha256(derived.read_bytes()).hexdigest()))
 suites=list(ET.parse(evidence/'junit.xml').iter('testsuite'));counts={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
 value=dict(name=name,exit_code=p.returncode,elapsed_seconds=time.monotonic()-started,**counts,privacy_lineage=lineage)
 print(json.dumps({k:v for k,v in value.items() if k!='privacy_lineage'}),flush=True);return value,evidence
def mutate(raw,before,after):
 old=before.encode('utf-8')
 if raw.count(old)!=1:
  old=before.replace('\n','\r\n').encode('utf-8')
 assert raw.count(old)==1,(before[:80],raw.count(old))
 offset=raw.index(old)+len(old)
 ending='\r\n' if b'\r\n' in old or raw[offset:].startswith(b'\r\n') else '\n'
 new=after.replace('\n',ending).encode('utf-8');changed=raw.replace(old,new,1)
 compile(changed,'owned-mutation-preflight','exec');return changed
# Validate every target and its syntax before the expensive green baseline.
for name,module,before,after,test,selection in specs:mutate((source/'backend/lab'/module).read_bytes(),before,after)
selection='both_parent_side or (reverse_reservation_index and wrong_definition) or (cannot_invent and result_event) or (changed_or_missing_selected and (envelope or deleted_selected))'
baseline,_=run('baseline',copy('baseline'),[*['tests/'+n for n in tests],'-k',selection]);assert baseline['exit_code']==0 and baseline['tests']>0 and baseline['failures']==baseline['errors']==baseline['skipped']==0
mutants=[]
for name,module,before,after,test,selection in specs:
 folder=copy(name);path=folder/'backend/lab'/module;raw=path.read_bytes();path.write_bytes(mutate(raw,before,after))
 value,evidence=run(name,folder,['tests/'+test,'-k',selection]);assert value['exit_code']==1 and value['failures']>0 and value['errors']==value['skipped']==0 and value['tests']>0,name
 failures=[n for n in ET.parse(evidence/'junit.xml').iter('failure')]
 assert all(n.attrib.get('message','').lstrip().startswith(('assert ','Failed: DID NOT RAISE')) or 'AssertionError:' in (n.text or '') for n in failures),(name,[n.attrib for n in failures])
 shutil.copyfile(path,evidence/('mutated-'+module));value.update(original_sha256=hashlib.sha256(raw).hexdigest(),mutated_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),target='backend/lab/'+module);mutants.append(value)
for name,digest in originals.items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
value=dict(scope=__doc__,baseline=baseline,mutants=mutants,all_assertion_killed=True,original_development_source_unchanged=True,main_running_app_unchanged=True,final_acceptance_certified=False)
(out/'spread-selection-link-mutations.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(mutants_killed=len(mutants),green_baseline_cases=baseline['tests'],originals_unchanged=True,final_acceptance_certified=False)))
