"""Actual isolated D046 guard mutations, with assertion-only kills and intact originals."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.trace_privacy import Sanitizer
private=root/'data/private-evidence/trade-twins-mutations'/out.name;private.mkdir(parents=True,exist_ok=False)
owned=root/'data/dev026'/('core-mutations-'+out.name[:22]);owned.mkdir(exist_ok=False)
specs=[
 ('whole-cohort', 'return bool(self.sources) and all(self.pools)', 'return bool(self.sources) and any(self.pools)', 'bins_real_moments'),
 ('future-atr', 'if self.atr_available_at > self.entry_at:', 'if False:', 'candidate_schema'),
 ('original-entry-exclusion', 'if (moment.symbol, moment.entry_at) not in original_entries:', 'if True:', 'bins_real_moments'),
 ('thirty-minute-bin', 'return (local.hour * 60 + local.minute - 570) // 30', 'return (local.hour * 60 + local.minute - 570) // 60', 'bins_real_moments'),
 ('transported-target', 'return price - side * stop_distance * atr, price + side * target_distance * atr', 'return price - side * stop_distance * atr, price - side * target_distance * atr', 'source_cohort_plan'),
 ('unbiased-rejection', 'ceiling = domain - domain % size', 'ceiling = domain', 'actual_coordinate_hash'),
 ('exact-ten-thousand', 'eligible = plan.eligible and complete == TOTAL_SETS and failed == 0', 'eligible = plan.eligible and complete > 0 and failed == 0', 'no_partial_failed'),
 ('ties-count', 'exceedances += Decimal(str(row.net_profit)) >= real', 'exceedances += Decimal(str(row.net_profit)) > real', 'exact10000_source_fraction'),
 ('strict-five-percent', 'adapted_pass=20 * exceedances < TOTAL_SETS if eligible else None', 'adapted_pass=20 * exceedances <= TOTAL_SETS if eligible else None', 'exact10000_source_fraction'),
 ('exact-cutoff', 'if cutoff not in boundaries:', 'if False:', 'dst_same_new_york_bin')]
inputs=[*sorted((source/'backend').rglob('*.py')),*sorted((source/'verification').glob('*.py')),
 *[source/p for p in ['pyproject.toml','RULEBOOK.md','strategy.schema.json','requirements.lock','tests/conftest.py','tests/test_trade_twins.py']]]
originals={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
def copy(name):
 target=owned/name;target.mkdir()
 for p in inputs:
  relative=p.relative_to(source);assert not p.is_symlink() and not any(part.lower().startswith('.env') for part in relative.parts)
  dest=target/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 return target
def mutate(raw,before,after):
 needle=before.encode();assert raw.count(needle)==1,(before,raw.count(needle))
 changed=raw.replace(needle,after.encode(),1);compile(changed,'owned-twin-mutant','exec');return changed
module=source/'backend/lab/trade_twins.py'
for name,before,after,selection in specs:mutate(module.read_bytes(),before,after)
def run(name,folder,selection):
 evidence=out/name;evidence.mkdir();env=os.environ.copy();env.update(PYTHONPATH=str(folder),PYTHONNOUSERSITE='1',PA_EVIDENCE_RUN_DIR=str(evidence))
 started=time.monotonic();p=subprocess.run([sys.executable,'-m','pytest','-q','-c','pyproject.toml','tests/test_trade_twins.py','-k',selection,'--junitxml='+str(evidence/'junit.xml')],cwd=folder,env=env,capture_output=True,timeout=180)
 scrub=Sanitizer([(str(root),'<workspace>'),(str(Path.home()),'<user-home>')]);decoded=[p.stdout.decode('utf-8',errors='replace'),p.stderr.decode('utf-8',errors='replace')]
 for value in decoded:scrub.learn(value)
 lineage=[]
 for label,raw,value in zip(['stdout','stderr'],[p.stdout,p.stderr],decoded):
  original=private/(name+'-'+label+'.log');original.write_bytes(raw);derived=evidence/(label+'.log');derived.write_text(scrub.clean(value),encoding='utf-8')
  lineage.append(dict(private_original=original.relative_to(root).as_posix(),original_sha256=hashlib.sha256(raw).hexdigest(),derived=derived.relative_to(out).as_posix(),derived_sha256=hashlib.sha256(derived.read_bytes()).hexdigest()))
 suites=list(ET.parse(evidence/'junit.xml').iter('testsuite'));counts={key:sum(int(s.attrib.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped']}
 result=dict(name=name,exit_code=p.returncode,elapsed_seconds=time.monotonic()-started,**counts,privacy_lineage=lineage)
 print(json.dumps({k:v for k,v in result.items() if k!='privacy_lineage'}),flush=True);return result,evidence
selection=' or '.join(sorted({s[3] for s in specs}))
baseline,_=run('baseline',copy('baseline'),selection)
assert baseline['exit_code']==0 and baseline['tests']>0 and baseline['failures']==baseline['errors']==baseline['skipped']==0
mutants=[]
for name,before,after,selection in specs:
 folder=copy(name);path=folder/'backend/lab/trade_twins.py';raw=path.read_bytes();path.write_bytes(mutate(raw,before,after))
 result,evidence=run(name,folder,selection)
 assert result['exit_code']==1 and result['tests']>0 and result['failures']>0 and result['errors']==result['skipped']==0,name
 failures=list(ET.parse(evidence/'junit.xml').iter('failure'))
 assert all(f.attrib.get('message','').lstrip().startswith(('assert ','Failed: DID NOT RAISE')) or 'AssertionError:' in (f.text or '') for f in failures),(name,[f.attrib for f in failures])
 shutil.copyfile(path,evidence/'mutated-trade_twins.py');result.update(original_sha256=hashlib.sha256(raw).hexdigest(),mutated_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),target='backend/lab/trade_twins.py');mutants.append(result)
for name,digest in originals.items():assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest,name
value=dict(scope=__doc__,baseline=baseline,mutants=mutants,all_assertion_killed=True,original_development_source_unchanged=True,main_running_app_unchanged=True,financial_sets_executed=0,final_acceptance_certified=False)
(out/'trade-twins-core-mutations.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(dict(mutants_killed=len(mutants),green_baseline_cases=baseline['tests'],originals_unchanged=True,financial_sets_executed=0,final_acceptance_certified=False)))
