"""Actual current production preparation mutations; assertion-only kills required."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev026/next-src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);sys.path.insert(0,str(root))
from verification.record_check import source_paths
from verification.trace_privacy import Sanitizer
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
owned=root/'data/dev026/preparation-mutations'/out.name;owned.mkdir(parents=True,exist_ok=False)
private=root/'data/private-evidence/preparation-mutations'/out.name;private.mkdir(parents=True,exist_ok=False)
features='backend/lab/trade_twin_features.py';amounts='backend/lab/trade_twin_amounts.py';results='backend/lab/trade_twin_results.py';reader='backend/lab/trade_twin_source.py'
specs=[
 ('completed-boundary',features,"np.searchsorted(boundaries,row.timestamp.value,side='right')","np.searchsorted(boundaries,row.timestamp.value,side='left')",'setup_chart_completed and 1m'),
 ('atr-row-definition',features,"value=float(atr[index])/float(row.factor)","value=float(atr[min(index+1,len(atr)-1)])/float(row.factor)",'random_ohlc'),
 ('unfinished-current-candle-lookahead',features,"value=float(atr[index])/float(row.factor)","value=float(atr[min(index+2,len(atr)-1)])/float(row.factor)",'unfinished_current_candle'),
 ('setup-not-trigger',features,'chart=aggregate(frame,cfg.timeframe)','chart=aggregate(frame,cfg.trigger)','setup_atr_not_trigger'),
 ('raw-split-units',features,'value=float(atr[index])/float(row.factor)','value=float(atr[index])','split_units'),
 ('source-validation-cancel',features,"if cancel and validation_index%100==0 and cancel():\n                raise InterruptedError('Twin feature preparation canceled during original price validation.')","if False:\n                raise InterruptedError('Twin feature preparation canceled during original price validation.')",'cancellation_is_bounded_during_original_price'),
 ('moment-cancel',features,'if cancel and ordinal%100==0 and cancel():','if False:','cancellation_is_bounded_during_causal_moment'),
 ('finite-sum-context',amounts,'context.prec=precision','context.prec=28','cohort_baseline_sum or sum_matches_independent_fraction'),
 ('binary-float-roundtrip',results,'exceedances+=Decimal(row.net_profit)>=real','exceedances+=Decimal(str(float(row.net_profit)))>=real','exact_large and 9999'),
 ('ties-count',results,'exceedances+=Decimal(row.net_profit)>=real','exceedances+=Decimal(row.net_profit)>real','exact_large and 10000000000.0'),
 ('strict-five-percent',results,'adapted_pass=20*exceedances<TOTAL_SETS','adapted_pass=20*exceedances<=TOTAL_SETS','threshold and 500'),
 ('complete-denominator',results,'eligible=plan.eligible and complete==TOTAL_SETS and failed==0','eligible=plan.eligible and complete>0 and failed==0','partial_and_cancelled'),
 ('original-complete-profit',reader,'closed=exact_total(profits)','closed=sum(profits,Decimal(0))','actual_original_account_retains_tiny'),
 ('canonical-original-text',amounts,'if str(amount)!=value:','if False:','original_saved_money_refuses_numeric_and_alternate_spelling')]
inputs=[*sorted((source/'backend').rglob('*.py')),*sorted((source/'verification').glob('*.py')),*sorted((source/'tests').glob('*.py')),*sorted((source/'verification/fixtures').glob('*.json')),*[source/n for n in ['pyproject.toml','requirements.lock','RULEBOOK.md','strategy.schema.json']]]
def copy(name):
 target=owned/name;target.mkdir()
 for p in inputs:
  relative=p.relative_to(source);assert not p.is_symlink() and not any(part.lower().startswith('.env') for part in relative.parts)
  dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 return target
def mutate(raw,needle,replacement,name):
 newline=b'\r\n' if b'\r\n' in raw else b'\n'
 before=needle.encode().replace(b'\n',newline);after=replacement.encode().replace(b'\n',newline)
 assert raw.count(before)==1,(name,raw.count(before))
 changed=raw.replace(before,after,1);compile(changed,name,'exec');return changed
for name,path,needle,replacement,_ in specs:
 mutate((source/path).read_bytes(),needle,replacement,name)
def run(name,folder,selection):
 evidence=out/name;evidence.mkdir();env=os.environ.copy();env.update(PYTHONPATH=str(folder),PYTHONNOUSERSITE='1',PA_EVIDENCE_RUN_DIR=str(evidence))
 started=time.perf_counter();p=subprocess.run([sys.executable,'-m','pytest','-q','-c','pyproject.toml','tests/test_trade_twin_features.py','tests/test_trade_twin_amounts.py','tests/test_trade_twin_results.py','tests/test_trade_twin_preparation.py','-k',selection,'--junitxml='+str(evidence/'junit.xml')],cwd=folder,env=env,capture_output=True,timeout=240)
 scrub=Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')])
 for raw in [p.stdout,p.stderr]:scrub.learn(raw.decode('utf-8',errors='replace'))
 lineage=[]
 for label,raw in [('stdout',p.stdout),('stderr',p.stderr)]:
  original=private/(name+'-'+label+'.log');original.write_bytes(raw);derived=evidence/(label+'.log');derived.write_text(scrub.clean(raw.decode('utf-8',errors='replace')),encoding='utf-8')
  lineage.append(dict(private_original=original.relative_to(root).as_posix(),original_sha256=hashlib.sha256(raw).hexdigest(),derived=derived.relative_to(out).as_posix(),derived_sha256=sha(derived)))
 suites=list(ET.parse(evidence/'junit.xml').iter('testsuite'));counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
 value=dict(name=name,exit_code=p.returncode,elapsed_seconds=time.perf_counter()-started,**counts,privacy_lineage=lineage)
 print(json.dumps({k:v for k,v in value.items() if k!='privacy_lineage'}),flush=True);return value,evidence
selection=' or '.join('('+s[4]+')' for s in specs);baseline,_=run('baseline',copy('baseline'),selection)
assert baseline['exit_code']==0 and baseline['tests']>0 and baseline['failures']==baseline['errors']==baseline['skipped']==0
mutants=[]
for name,path,needle,replacement,selection in specs:
 folder=copy(name);p=folder/path;raw=p.read_bytes();p.write_bytes(mutate(raw,needle,replacement,name))
 value,evidence=run(name,folder,selection)
 assert value['exit_code']==1 and value['tests']>0 and value['failures']>0 and value['errors']==value['skipped']==0,name
 failures=list(ET.parse(evidence/'junit.xml').iter('failure'))
 assert all(f.get('message','').lstrip().startswith(('assert ','Failed: DID NOT RAISE')) or 'AssertionError:' in (f.text or '') for f in failures),(name,[f.attrib for f in failures])
 shutil.copyfile(p,evidence/('mutated-'+Path(path).name));value.update(target=path,original_sha256=hashlib.sha256(raw).hexdigest(),mutated_sha256=sha(p));mutants.append(value)
assert before=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
value=dict(scope=__doc__,baseline=baseline,mutants=mutants,all_assertion_killed=True,current_production_source_unchanged=True,source_files=before,main_app_source_replaced=False,final_acceptance_certified=False)
(out/'current-preparation-mutations.json').write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(dict(actual_mutants=len(mutants),all_assertion_killed=True,current_source_unchanged=True)))
