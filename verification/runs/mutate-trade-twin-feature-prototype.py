"""Actual isolated prototype mutations, without editing the frozen staged app."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
original=root/'verification/runs/trade_twin_features_draft.py';raw=original.read_bytes();digest=hashlib.sha256(raw).hexdigest()
specs=[
 ('completed-boundary-asof',"np.searchsorted(boundaries,row.timestamp.value,side='right')","np.searchsorted(boundaries,row.timestamp.value,side='left')",'setup_chart_completed and 1m'),
 ('hidden-future-atr',"value=float(atr[index]/row.factor)","value=float(atr[min(index+1,len(atr)-1)]/row.factor)",'random_ohlc'),
 ('raw-split-units',"value=float(atr[index]/row.factor)","value=float(atr[index])",'split_units'),
 ('setup-not-trigger',"chart=aggregate(frame,cfg.timeframe)","chart=aggregate(frame,cfg.trigger)",'setup_atr_not_trigger'),
 ('complete-original-clock',"if list(window.timestamp)!=expected:","if False:",'refuse_unknown and missing and not missing_columns'),
 ('minute-cancel',"if cancel and ordinal%100==0 and cancel():",'if False:','cancel_before and 4')]
for name,before,after,_ in specs:
 assert raw.count(before.encode())==1,name
 compile(raw.replace(before.encode(),after.encode(),1),'owned-feature-mutant','exec')
sys.path.insert(0,str(root));from verification.trace_privacy import Sanitizer
private=root/'data/private-evidence/feature-prototype-mutations'/out.name;private.mkdir(parents=True)
def run(name,code,selection):
 evidence=out/name;evidence.mkdir();module=evidence/'owned-feature.py';module.write_bytes(code)
 env=os.environ.copy();env.update(PYTHONPATH=os.pathsep.join([str(source),str(source/'tests')]),PYTHONNOUSERSITE='1',PA_FEATURE_PROTOTYPE_PATH=str(module),PA_EVIDENCE_RUN_DIR=str(evidence))
 began=time.perf_counter();p=subprocess.run([sys.executable,'-m','pytest','-q','-c',str(source/'pyproject.toml'),str(root/'verification/runs/test_trade_twin_features_prototype.py'),'-k',selection,'--junitxml='+str(evidence/'junit.xml')],cwd=source,env=env,capture_output=True,timeout=180)
 scrub=Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')])
 for value in [p.stdout,p.stderr]:scrub.learn(value.decode('utf-8',errors='replace'))
 lineage=[]
 for label,value in [('stdout',p.stdout),('stderr',p.stderr)]:
  original_log=private/(name+'-'+label+'.log');original_log.write_bytes(value);derived=evidence/(label+'.log');derived.write_text(scrub.clean(value.decode('utf-8',errors='replace')),encoding='utf-8')
  lineage.append(dict(private_original=original_log.relative_to(root).as_posix(),original_sha256=hashlib.sha256(value).hexdigest(),derived=derived.relative_to(out).as_posix(),derived_sha256=hashlib.sha256(derived.read_bytes()).hexdigest()))
 suites=list(ET.parse(evidence/'junit.xml').iter('testsuite'));counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
 result=dict(name=name,exit_code=p.returncode,elapsed_seconds=time.perf_counter()-began,**counts,original_sha256=digest,mutated_sha256=hashlib.sha256(code).hexdigest(),privacy_lineage=lineage)
 print(json.dumps({k:v for k,v in result.items() if k!='privacy_lineage'}),flush=True);return result,evidence
baseline,_=run('baseline',raw,' or '.join('('+s[3]+')' for s in specs))
assert baseline['exit_code']==0 and baseline['tests']>0 and baseline['failures']==baseline['errors']==baseline['skipped']==0
mutants=[]
for name,before,after,selection in specs:
 value,evidence=run(name,raw.replace(before.encode(),after.encode(),1),selection)
 assert value['exit_code']==1 and value['tests']>0 and value['failures']>0 and value['errors']==value['skipped']==0,name
 failures=list(ET.parse(evidence/'junit.xml').iter('failure'))
 assert all(f.attrib.get('message','').lstrip().startswith(('assert ','Failed: DID NOT RAISE')) or 'AssertionError:' in (f.text or '') for f in failures),(name,[f.attrib for f in failures])
 mutants.append(value)
assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
value=dict(scope=__doc__,baseline=baseline,mutants=mutants,all_assertion_killed=True,original_prototype_unchanged=True,prototype_installed=False,final_acceptance_certified=False)
(out/'feature-prototype-mutations.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(actual_mutants=len(mutants),all_assertion_killed=True)))
