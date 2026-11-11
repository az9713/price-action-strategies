"""Five isolated D038 numerical source mutations; no original file is edited."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,xml.etree.ElementTree as ET
ROOT=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=sorted((ROOT/'backend').rglob('*.py'))+[ROOT/p for p in ['tests/conftest.py','tests/test_search_statistics.py','verification/reference_statistics.py','RULEBOOK.md','strategy.schema.json']]
baseline={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
mutations=[
 ('annualized-sharpe-in-daily-formula','sr=average/sigma;','sr=average/sigma*math.sqrt(252);'),
 ('winner-only-trial-dispersion',"if reason is None]","if reason is None and _['metrics']['net_profit']>0]"),
 ('raw-count-replaces-prespecified-scenarios','for trials in settings.effective_trials:','for trials in [len(rows)]:') ,
 ('undefined-scores-replaced-with-zero','undefined=reason;score=None','undefined=reason;score=0.0'),
 ('dispersion-unit-multiplied-by-annualizer','0 if trials==1 else dispersion)','0 if trials==1 else dispersion*math.sqrt(252))'),
]
records=[]
with tempfile.TemporaryDirectory(prefix='priceaction-search-statistics-mutants-') as temporary:
 work=Path(temporary).resolve();assert work.is_relative_to(Path(tempfile.gettempdir()).resolve())
 for p in paths:
  target=work/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
 env=os.environ.copy();env.update(PYTHONPATH=str(work),PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1');env.pop('PA_EVIDENCE_RUN_DIR',None)
 def run(name):
  xml=out/(name+'-junit.xml')
  p=subprocess.run([sys.executable,'-m','pytest','-q','tests/test_search_statistics.py','--basetemp',str(work/'state'),'--junitxml',str(xml)],cwd=work,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
  for suffix,value in [('stdout',p.stdout),('stderr',p.stderr)]: (out/(name+'-'+suffix+'.log')).write_text(value.replace(str(work),'<isolated-search-statistics-mutant>'),encoding='utf-8')
  suites=list(ET.parse(xml).iter('testsuite'))
  return dict(exit_code=p.returncode,**{k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']})
 first=run('baseline');assert first['exit_code']==0 and first['tests']>=30 and first['failures']==first['errors']==first['skipped']==0,first
 target=work/'backend/lab/search_statistics.py';original=target.read_text(encoding='utf-8')
 for name,before,after in mutations:
  assert original.count(before)==1,(name,before);changed=original.replace(before,after);target.write_text(changed,encoding='utf-8')
  (out/(name+'-source.py')).write_text(changed,encoding='utf-8');result=run(name)
  assert result['exit_code']==1 and result['tests']==first['tests'] and result['failures']>0 and result['errors']==result['skipped']==0,(name,result)
  records.append(dict(name=name,replacement=dict(before=before,after=after),mutant_sha256=sha(target),result=result,status='killed_by_assertions'))
  target.write_bytes((ROOT/'backend/lab/search_statistics.py').read_bytes())
assert all(sha(ROOT/name)==digest for name,digest in baseline.items())
value=dict(scope=__doc__,baseline=first,source_manifest=baseline,mutations=records,original_source_unchanged=True)
(out/'search-statistics-mutations.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(dict(baseline=first,mutants=len(records),killed=len(records),original_source_unchanged=True)))
