"""Eight isolated result integrity, pagination, legacy-path and cancellation mutations; require assertion kills."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
paths=set((root/'backend').rglob('*.py'))|set((root/'tests').rglob('*.py'))|set((root/'verification').glob('*.py'))|set((root/'verification/fixtures').rglob('*.json'))
paths|={root/n for n in ['RULEBOOK.md','strategy.schema.json','PLAN.md','VERIFICATION_PLAN.md','requirements.lock','pyproject.toml']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline={p.relative_to(root).as_posix():sha(p) for p in paths};records=[]
mutations=[
 ('skip-original-input-byte-binding','result_index',"input_bytes_hash(db,job['input_rowid'])!=view.get('input_raw_sha256')",'False'),
 ('skip-original-root-integrity','result_index',"original_hash(folder/'result.json.gz')!=original.get('sha256')",'False'),
 ('materialize-unrelated-input-json','result_index',"folder=self.folder(jid);cache=None","folder=self.folder(jid);cache=None;self.store.job(jid)"),
 ('ignore-result-page-offset','result_index',"SELECT value FROM rows ORDER BY part LIMIT ? OFFSET ?',(limit,offset)","SELECT value FROM rows ORDER BY part LIMIT ? OFFSET ?',(limit,0)"),
 ('ignore-diagnostic-page-offset','result_index',"SELECT value FROM auxiliary WHERE kind=? ORDER BY part LIMIT ? OFFSET ?',(kind,limit,offset)","SELECT value FROM auxiliary WHERE kind=? ORDER BY part LIMIT ? OFFSET ?',(kind,limit,0)"),
 ('miscount-portfolio-projection','result_index',"configuration_count=len(row['configurations'])","configuration_count=1+len(row['configurations'])"),
 ('silently-break-legacy-build-path','result_index',"if view is None:raise ViewUnavailable","if view is None:raise StateError"),
 ('ignore-result-publication-cancel','result_index',"if cancel and ordinal%64==0 and cancel():raise InterruptedError('Canceled while building the saved result view.')","if False:raise InterruptedError('Canceled while building the saved result view.')"),
]
with tempfile.TemporaryDirectory(prefix='pa-result-view-mutants-') as directory:
 work=Path(directory)
 for p in paths:
  target=work/p.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 env=os.environ.copy();env.update(PYTHONPATH=str(work),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1');env.pop('PA_EVIDENCE_RUN_DIR',None)
 def run(name):
  xml=out/(name+'-junit.xml');p=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_result_materialization.py','-k','worker_publishes or never_decode or same_length or diagnostic_pages or projection_omissions or publication_cancel or missing_legacy','--basetemp',str(work/'state'),'--junitxml',str(xml)],cwd=work,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
  for suffix,value in [('stdout',p.stdout),('stderr',p.stderr)]:(out/(name+'-'+suffix+'.log')).write_text(value.replace(str(work),'<isolated-result-view-mutant>'),encoding='utf-8')
  suites=list(ET.parse(xml).iter('testsuite'));failures=[f for s in suites for f in s.iter('failure')]
  assertions=sum('AssertionError' in f.attrib.get('message','')+(f.text or '') or 'DID NOT RAISE' in f.attrib.get('message','')+(f.text or '') for f in failures)
  return dict(exit_code=p.returncode,assertion_failures=assertions,**{k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']})
 first=run('baseline');assert first['exit_code']==0 and first['tests']==9 and first['failures']==first['errors']==first['skipped']==0,first
 for name,module,before,after in mutations:
  relative='backend/lab/'+module+'.py';original=(root/relative).read_text(encoding='utf-8');assert original.count(before)==1,(name,before,original.count(before))
  target=work/relative;changed=original.replace(before,after);target.write_text(changed,encoding='utf-8');(out/(name+'-source.py')).write_text(changed,encoding='utf-8');result=run(name)
  assert result['exit_code']==1 and result['tests']==first['tests'] and result['failures']>0 and result['assertion_failures']>0 and result['errors']==result['skipped']==0,(name,result)
  records.append(dict(name=name,module=relative,mutant_sha256=sha(target),replacement=dict(before=before,after=after),result=result,status='killed_with_explicit_assertion_failure'));target.write_bytes((root/relative).read_bytes())
assert all(sha(root/name)==digest for name,digest in baseline.items())
(out/'result-materialization-mutation-results.json').write_text(json.dumps(dict(scope=__doc__,baseline=first,source_manifest=baseline,mutations=records,original_source_unchanged=True),indent=2),encoding='utf-8')
print(json.dumps(dict(baseline_tests=first['tests'],mutants=len(records),killed=len(records),original_source_unchanged=True)))
