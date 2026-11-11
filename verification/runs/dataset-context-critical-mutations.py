"""Seven isolated actual context, export, independent-reader and import-loop mutations.
Passing this check requires assertion kills, not collection errors or skipped tests.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
paths=set((root/'backend').rglob('*.py'))|set((root/'tests').rglob('*.py'))|set((root/'verification').glob('*.py'))|set((root/'verification/fixtures').rglob('*.json'))
paths|={root/name for name in ['RULEBOOK.md','strategy.schema.json','PLAN.md','VERIFICATION_PLAN.md','requirements.lock','pyproject.toml']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline={p.relative_to(root).as_posix():sha(p) for p in paths};records=[]
mutations=[
 ('remove-manifest-context-binding','dataset_context','value!=freeze_context(manifest)','False'),
 ('allow-duplicate-or-unsorted-symbols','dataset_context','symbols==sorted(set(symbols))','True'),
 ('remove-csv-formula-neutralization','dataset_context','return "\'"+value if','return value if'),
 ('invent-historical-kind-for-missing-metadata','dataset_context',"metadata.get('input_kind','unknown')","metadata.get('input_kind','historical')"),
 ('bypass-preprice-context-validation','worker','dataset_context=self.lab.dataset_context_input(payload)',"dataset_context=payload.get('dataset_context')"),
 ('block-http-loop-during-import','api','return await asyncio.to_thread(parse_and_publish)','return parse_and_publish()'),
 ('wrong-independent-list-format','presentation_audit',"return ', '.join(rendered)","return '|'.join(rendered)"),
]
with tempfile.TemporaryDirectory(prefix='pa-dataset-context-mutants-') as directory:
 work=Path(directory)
 for p in paths:
  target=work/p.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 env=os.environ.copy();env.update(PYTHONPATH=str(work),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1');env.pop('PA_EVIDENCE_RUN_DIR',None)
 def run(name):
  xml=out/(name+'-junit.xml');p=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_dataset_context.py','tests/test_import_responsiveness.py','-k','whitelist or malformed or absent_metadata or corrupt_context or non_object or limits or missing_context or legacy_and_corrupt or health_responds or complete_twenty','--basetemp',str(work/'state'),'--junitxml',str(xml)],cwd=work,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
  for suffix,value in [('stdout',p.stdout),('stderr',p.stderr)]:(out/(name+'-'+suffix+'.log')).write_text(value.replace(str(work),'<isolated-dataset-context-mutant>'),encoding='utf-8')
  suites=list(ET.parse(xml).iter('testsuite'));failures=[f for s in suites for f in s.iter('failure')]
  assertions=sum('AssertionError' in f.attrib.get('message','')+(f.text or '') or 'DID NOT RAISE' in f.attrib.get('message','')+(f.text or '') or 'TimeoutError' in f.attrib.get('message','')+(f.text or '') for f in failures)
  return dict(exit_code=p.returncode,assertion_failures=assertions,**{k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']})
 first=run('baseline');assert first['exit_code']==0 and first['tests']>=40 and first['failures']==first['errors']==first['skipped']==0,first
 for name,module,before,after in mutations:
  relative='backend/lab/'+module+'.py';original=(root/relative).read_text(encoding='utf-8');assert original.count(before)==1,(name,before)
  target=work/relative;changed=original.replace(before,after);target.write_text(changed,encoding='utf-8');(out/(name+'-source.py')).write_text(changed,encoding='utf-8');result=run(name)
  assert result['exit_code']==1 and result['tests']==first['tests'] and result['failures']>0 and result['assertion_failures']>0 and result['errors']==result['skipped']==0,(name,result)
  records.append(dict(name=name,module=relative,mutant_sha256=sha(target),replacement=dict(before=before,after=after),result=result,status='killed_with_explicit_test_failure'));target.write_bytes((root/relative).read_bytes())
assert all(sha(root/name)==digest for name,digest in baseline.items())
(out/'dataset-context-mutation-results.json').write_text(json.dumps(dict(scope=__doc__,baseline=first,source_manifest=baseline,mutations=records,original_source_unchanged=True),indent=2),encoding='utf-8')
print(json.dumps(dict(baseline_tests=first['tests'],mutants=len(records),killed=len(records),original_source_unchanged=True)))
