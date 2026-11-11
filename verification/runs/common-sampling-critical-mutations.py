"""Twelve isolated actual source mutations of sampling, time-window counting, gates and proposal integrity."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,xml.etree.ElementTree as ET
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
paths=set((root/'backend').rglob('*.py'))|set((root/'tests').rglob('*.py'))|set((root/'verification').glob('*.py'))|set((root/'verification/fixtures').rglob('*.json'))
paths|={root/name for name in ['RULEBOOK.md','strategy.schema.json','PLAN.md','VERIFICATION_PLAN.md','requirements.lock','pyproject.toml']}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
baseline={p.relative_to(root).as_posix():sha(p) for p in paths}
mutations=[
 ('wrong-filter-quota','sampling','quotas(total,[4,4,2])','quotas(total,[4,3,3])'),
 ('duplicate-configurations-accepted','sampling','duplicate=cid in seen','duplicate=False'),
 ('filter-groups-with-replacement','sampling','size=filters,replace=False','size=filters,replace=True'),
 ('utc-date-instead-of-equity-session','sampling',"at.astimezone(ZoneInfo('America/New_York')).date().isoformat()",'at.date().isoformat()'),
 ('warmup-signals-counted','sampling','counted+=start<=day<=end','counted+=1'),
 ('signal-threshold-exclusive','sampling','signals>=policy.minimum_signals','signals>policy.minimum_signals'),
 ('trade-threshold-exclusive','sampling','trades>=policy.minimum_trades','trades>policy.minimum_trades'),
 ('zero-profit-admitted','sampling','profitable=profit>0','profitable=profit>=0'),
 ('sharpe-threshold-exclusive','sampling','sharpe>=policy.minimum_sharpe','sharpe>policy.minimum_sharpe'),
 ('cumulative-gate-reset','sampling','passed=passed and flag','passed=flag'),
 ('wrong-source-part-hash','sampling',"source_part_sha256=row['report_sha256']","source_part_sha256=row['config_id']"),
 ('proposal-identity-check-removed','trials',"if identity(configuration)!=cid:raise self.error('Saved sampler proposal configuration identity changed.')","if False:raise self.error('Saved sampler proposal configuration identity changed.')"),
]
records=[]
with tempfile.TemporaryDirectory(prefix='priceaction-common-mutations-') as temporary:
 work=Path(temporary).resolve();parent=Path(tempfile.gettempdir()).resolve();assert work.is_relative_to(parent) and work!=parent and work.name.startswith('priceaction-common-mutations-')
 for p in paths:
  target=work/p.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 env=os.environ.copy();env.update(PYTHONPATH=str(work),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1');env.pop('PA_EVIDENCE_RUN_DIR',None)
 def run(name):
  xml=out/(name+'-junit.xml');p=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_common_sampling.py','tests/test_common_sampling_integration.py::test_full_proposal_hash_is_validated_before_atomic_registration','--basetemp',str(work/'state'),'--junitxml',str(xml)],cwd=work,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
  for suffix,value in [('stdout',p.stdout),('stderr',p.stderr)]: (out/(name+'-'+suffix+'.log')).write_text(value.replace(str(work),'<isolated-common-sampling-mutant>'),encoding='utf-8')
  suites=list(ET.parse(xml).iter('testsuite'));failures=[f for suite in suites for f in suite.iter('failure')]
  assertions=sum('AssertionError' in (f.attrib.get('message','')+(f.text or '')) or 'DID NOT RAISE' in (f.attrib.get('message','')+(f.text or '')) for f in failures)
  return dict(exit_code=p.returncode,assertion_failures=assertions,**{k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']})
 first=run('baseline');assert first['exit_code']==0 and first['tests']==53 and first['failures']==first['errors']==first['skipped']==0,first
 for name,module,before,after in mutations:
  relative='backend/lab/'+module+'.py';original=(root/relative).read_text(encoding='utf-8');assert original.count(before)==1,(name,before)
  target=work/relative;changed=original.replace(before,after);target.write_text(changed,encoding='utf-8');(out/(name+'-source.py')).write_text(changed,encoding='utf-8');result=run(name)
  assert result['exit_code']==1 and result['tests']==53 and result['failures']>0 and result['assertion_failures']>0 and result['errors']==result['skipped']==0,(name,result)
  records.append(dict(name=name,module=relative,mutant_sha256=sha(target),replacement=dict(before=before,after=after),result=result,status='killed_with_explicit_assertion_failure'));target.write_bytes((root/relative).read_bytes())
assert all(sha(root/name)==digest for name,digest in baseline.items())
(out/'common-sampling-mutation-results.json').write_text(json.dumps(dict(scope=__doc__,baseline=first,source_manifest=baseline,mutations=records,original_source_unchanged=True),indent=2),encoding='utf-8')
print(json.dumps(dict(baseline_tests=first['tests'],mutants=len(records),killed=len(records),original_source_unchanged=True)))
