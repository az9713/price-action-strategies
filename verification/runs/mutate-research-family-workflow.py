"""Eight actual source mutations against original-account workflow counterexamples."""
from pathlib import Path
import ast,hashlib,json,os,shutil,subprocess,sys,xml.etree.ElementTree as ET
root=Path.cwd();stage=root/'data/dev027/research-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
subject={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
home=root/'data/dev027/workflow-mutations'/out.name.split('-')[0];home.mkdir(parents=True,exist_ok=False)
jobs='backend/lab/research_family_jobs.py';source='backend/lab/research_family_source.py'
contracts=root/'verification/runs/research-family-job-contracts.py';boundaries=root/'verification/runs/research-family-boundary-contracts.py'
mutations=[
 ('ignore-frozen-parent-binding',jobs," or _binding(source)!=payload['family_parent']",'',str(boundaries)+'::test_changed_original_source_root_does_not_rebind_reserved_family'),
 ('ignore-original-account-closing',jobs,'    source.guard()\n    with lab.store.db() as db:\n        db.execute(\'BEGIN\');closing',"    pass\n    with lab.store.db() as db:\n        db.execute('BEGIN');closing",str(contracts)+'::test_saved_family_publication_faults_refuse_without_repair_or_new_jobs[parent_part]'),
 ('ignore-original-computation-event',jobs,"    if len(rows)!=1 or rows[0]['bytes']>4096 or json.loads(rows[0]['details'])!=expected or rows[0]['id']>=checkpoint:",'    if False:',str(contracts)+'::test_saved_family_publication_faults_refuse_without_repair_or_new_jobs[analysis_computation_missing]'),
 ('ignore-original-attempt-digest',jobs,"    if (attempt is None or attempt['state']!='checkpointed' or attempt['computed_sha256']!=computed or attempt['artifact_sha256']!=digest):",'    if False:',str(contracts)+'::test_saved_family_publication_faults_refuse_without_repair_or_new_jobs[analysis_attempt]'),
 ('replace-missing-publication-on-resume',jobs,"        if row['state'] in {'checkpointed','completed'} or checkpoint is not None:",'        if False:',str(boundaries)+'::test_owned_resume_cannot_replace_missing_original_publication_even_if_trial_state_changed[True]'),
 ('ignore-original-reservation-binding',jobs," or existing!=dict(child_id=saved['id'],family=family,payload_hash=sha,binding=binding)",'',str(boundaries)+'::test_original_reservation_corruption_refuses_both_read_and_replacement[wrong_binding]'),
 ('ignore-closing-analysis-root',jobs,"        if closing_sha!=sha or _root_event(db,jid)!=(event,digest) or file_hash(lab.output_path(jid))!=digest:",'        if False:',str(boundaries)+'::test_closing_analysis_root_change_is_refused_after_all_original_source_checks'),
 ('accept-duplicate-original-publication',source,"    if len(rows)!=1 or rows[0]['bytes']>4096:","    if len(rows)==0 or rows[0]['bytes']>4096:",str(contracts)+'::test_saved_family_publication_faults_refuse_without_repair_or_new_jobs[analysis_result_duplicate]'),
]
results=[]
for name,module,needle,replacement,test in [('baseline',None,None,None,None),*mutations]:
 folder=home/name;folder.mkdir()
 for relative in subject:
  target=folder/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(stage/relative,target)
 mutation=None
 if module:
  path=folder/module;text=path.read_text();assert text.count(needle)==1,(name,text.count(needle))
  path.write_text(text.replace(needle,replacement));ast.parse(path.read_text())
  mutation=dict(module=module,original_sha256=subject[module],mutant_sha256=sha(path),needle=needle,replacement=replacement)
 env=os.environ.copy();env.update(PYTHONPATH=str(folder)+os.pathsep+str(folder/'tests'),PYTHONNOUSERSITE='1')
 case=out/name;case.mkdir();env['PA_EVIDENCE_RUN_DIR']=str(case);junit=case/'junit.xml'
 tests=[m[-1] for m in mutations] if name=='baseline' else [test]
 result=subprocess.run([sys.executable,'-m','pytest','-q','-c','pyproject.toml',*tests,'--import-mode=importlib','--junitxml='+str(junit)],cwd=folder,env=env,capture_output=True,text=True,timeout=240)
 (case/'stdout.txt').write_text(result.stdout,encoding='utf-8');(case/'stderr.txt').write_text(result.stderr,encoding='utf-8')
 tree=ET.parse(junit);suites=list(tree.iter('testsuite'));counts={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','errors','failures','skipped']}
 if name=='baseline':assert result.returncode==0 and counts==dict(tests=8,errors=0,failures=0,skipped=0),(counts,result.stdout[-3000:])
 else:
  assert result.returncode==1 and counts==dict(tests=1,errors=0,failures=1,skipped=0),(name,counts,result.stdout[-3000:])
  assert any('DID NOT RAISE' in (f.text or '') or 'AssertionError' in (f.text or '') for f in tree.iter('failure')),(name,'No assertion kill')
 results.append(dict(name=name,mutation=mutation,exit_code=result.returncode,counts=counts,assertion_killed=name!='baseline'))
 (out/'workflow-mutation-progress.json').write_text(json.dumps(dict(results=results,complete=False),indent=2),encoding='utf-8')
 print(json.dumps(results[-1]),flush=True)
assert subject=={p.relative_to(stage).as_posix():sha(p) for p in source_paths(stage)}
(out/'workflow-mutation-summary.json').write_text(json.dumps(dict(scope=__doc__,source_files=subject,current_source_unchanged=True,results=results,actual_mutations=8,all_assertion_killed=True,errors_counted_as_kills=False,global_gate=False,final_product_acceptance=False),indent=2),encoding='utf-8')
