"""Source-only recoverable financial twin component; no final workflow certificate."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,xml.etree.ElementTree as ET,zipfile
root=Path.cwd();source=root/'data/dev026/src';out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
sys.path.insert(0,str(root));from verification.record_check import source_paths
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def receipt(identifier,success=True):
 p=root/'verification/receipts'/(identifier+'.json');r=read(p)
 assert (r['command']['exit_code']==0)==success and not any(n.startswith(('Source changed','Missing requested')) for n in r['notes'])
 files={}
 for a in r['artifacts']:
  q=root/a['path'];assert q.resolve().is_relative_to(root.resolve()) and q.stat().st_size==a['bytes'] and sha(q)==a['sha256'];files[q.name]=q
 return r,files
ids=dict(full=sys.argv[1],gate=sys.argv[2],
 books='20261109T201249896282Z-trade-twins-original-financial-artifact-independent-replay-cash-fee-borrow-and-entitlement-audit',
 financial_mutations='20261109T201055617736Z-trade-twins-eleven-financial-mutations-with-self-consistent-wrong-split-account',
 source_mutations='20261109T195035640748Z-trade-twins-ten-actual-source-authority-mutations-corrected-paired-byte-fixture',
 core_mutations='20261109T182047874386Z-trade-twins-ten-actual-cohort-time-geometry-randomness-denominator-and-gate-mutations',
 entry_mutations='20261109T183017262617Z-trade-twins-four-actual-original-entry-atr-stop-ledger-and-capture-mutations',
 feature_prototype='20261109T202353799660Z-trade-twins-uninstalled-feature-prototype-all-six-positive-warmup-timeframes-and-clean-float-fixtures',
 feature_mutations='20261109T203013788007Z-trade-twins-six-actual-uninstalled-feature-asof-future-atr-split-trigger-clock-cancel-mutations',
 exact_grade_prototype='20261109T203954399901Z-trade-twins-uninstalled-exact-financial-grading-with-exponent-span-safe-cohort-sums',
 exact_grade_mutations='20261109T204252231701Z-trade-twins-six-actual-exact-money-grading-roundtrip-sum-tie-threshold-denominator-and-identity-mutations',
 financial_set_prototype='20261109T202726676713Z-trade-twins-uninstalled-actual-10000-paired-financial-sets-from-original-synthetic-account',
 authority_profile='20261109T204758419722Z-trade-twins-original-synthetic-source-authority-versus-draw-and-verified-cache-cost-profile',
 clock_boundaries='20261109T205723083189Z-trade-twins-eight-hand-accounted-preceding-close-versus-exact-opening-cutoff-boundaries')
records={k:receipt(v) for k,v in ids.items()};current={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
subject=read(records['full'][1]['baseline-source-subject.json']);assert current==subject['source_files'] and not subject['changed_during_check']
reconciled=read(records['full'][1]['baseline-regression-reconciliation.json']);lineage=read(records['full'][1]['case-lineage.json']);counts=lineage['counts']
assert counts==dict(tests=2646,passed=2646,unresolved=0) and len(lineage['cases'])==2646
assert reconciled['current_source_files']==current and reconciled['original_global_command_exit_code']==1 and not reconciled['single_all_green_invocation']
assert reconciled['exact_guard_correction_verified'] and reconciled['normal_discovery_boundary_cases']==4
gate=read(records['gate'][1]['trade-twins-current-full-gate.json']);assert gate['all30_module_gate_pass'] and gate['source_files_verified']==len(current)
assert all(m['sha256']==current[m['module']] for m in gate['modules']) and len(gate['modules'])==30
clocks=read(records['clock_boundaries'][1]['coincident-boundary-audit.json']);assert clocks['cases']==8 and clocks['all_hand_calculated_and_full_reference_parity'] and not clocks['staged_source_edited']
books=read(records['books'][1]['financial-books-audit.json']);assert books['books']==114 and books['all_saved_fields_replayed'] and books['source_files_verified']==len(reconciled['original_source_files'])
prototype=read(records['financial_set_prototype'][1]['prototype-financial-10000-summary.json'])
assert prototype['staged_source_files']==reconciled['original_source_files'] and prototype['staged_source_unchanged'] and prototype['uninstalled_prototype']
assert all(current[name]==digest for name,digest in prototype['staged_source_files'].items() if name.startswith('backend/'))
assert prototype['complete_sets_per_policy']==10000 and prototype['complete_financial_occurrences']==20000 and prototype['new_independently_verified_financial_books']==28 and prototype['verified_reuses']==19972 and prototype['original_authority_reads']==10003
for summary in prototype['summaries'].values():assert summary['complete_sets']==10000 and summary['exceedances']==10000 and summary['adapted_pass'] is False
for key,filename,expected in [('feature_prototype','feature-prototype-junit.xml',48),('exact_grade_prototype','decimal-grading-prototype-junit.xml',35)]:
 suites=list(ET.parse(records[key][1][filename]).iter('testsuite'));assert sum(int(s.get('tests',0)) for s in suites)==expected
 assert all(int(s.get(k,0))==0 for s in suites for k in ['failures','errors','skipped'])
for key,filename in [('feature_mutations','feature-prototype-mutations.json'),('exact_grade_mutations','decimal-grading-prototype-mutations.json')]:
 proof=read(records[key][1][filename]);assert proof['all_assertion_killed'] and proof['original_prototype_unchanged'] and len(proof['mutants'])==6
 target=root/'verification/runs'/('trade_twin_features_draft.py' if key=='feature_mutations' else 'trade_twin_decimal_grading_draft.py')
 assert all(m['original_sha256']==sha(target) and m['exit_code']==1 and m['failures']>0 and m['errors']==m['skipped']==0 for m in proof['mutants'])
proofs=[]
for key,filename,n,target in [
 ('financial_mutations','trade-twins-financial-mutations.json',11,'backend/lab/trade_twin_execution.py'),
 ('source_mutations','trade-twins-source-authority-mutations.json',10,'backend/lab/trade_twin_source.py'),
 ('core_mutations','trade-twins-core-mutations.json',10,'backend/lab/trade_twins.py'),
 ('entry_mutations','trade-twins-entry-trace-mutations.json',4,'backend/lab/engine.py')]:
 proof=read(records[key][1][filename]);assert proof['all_assertion_killed'] and proof['original_development_source_unchanged'] and len(proof['mutants'])==n
 assert proof['baseline']['exit_code']==0 and proof['baseline']['tests']>0 and proof['baseline']['failures']==proof['baseline']['errors']==proof['baseline']['skipped']==0
 for m in proof['mutants']:assert m['target']==target and m['original_sha256']==current[target] and m['exit_code']==1 and m['failures']>0 and m['errors']==m['skipped']==0
 proofs.append(dict(receipt=ids[key],mutants=n,target=target,green_baseline=proof['baseline']['tests']))
failures=[]
for identifier,reason in [
 ('20261109T201009374946Z-trade-twins-current-complete-backend-regression-and-thirty-numerical-module-coverage','Original full command:2564 passing bodies and78 setup errors from a dev025-only fixture path. Retained as failed; exact current-root guard followup resolves all78 case identities without changing numerical code. This checkpoint uses explicit case lineage, not a single all-green invocation.'),
 ('20261109T213226103308Z-trade-twins-baseline-2642-actual-case-lineage-and-unchanged-numerical-source-coverage-reconciliation','First current actual-DB reconciliation exposed85.09% spread_jobs branch coverage. Four existing external boundary probes were added to normal discovery and rerun; the threshold and numerical source were unchanged.'),
 ('20261109T194429774545Z-trade-twins-ten-actual-original-source-cohort-identity-event-trial-and-late-authority-mutations','A redundant manifest guard mutation survived because read_manifest rejected the internally inconsistent test input; added a paired price/manifest replacement, without removing the upstream guard.'),
 ('20261109T194937825191Z-trade-twins-ten-actual-source-authority-mutations-with-paired-price-manifest-replacement','New fixture missing hashlib import; corrected test import, no production change.'),
 ('20261109T195837781741Z-trade-twins-financial-execution-authored-absence-assertion-before-kernel','Authored actual missing-kernel test-body assertion before production implementation.'),
 ('20261109T200047466627Z-trade-twins-financial-kernel-first-independent-decimal-full-book-contracts','Four dividend failures: cash-delta argument collided with entitlement amount keyword; renamed argument.'),
 ('20261109T200235752667Z-trade-twins-financial-prior-volume-staleness-authored-counterexample','Actual stale-prior-volume counterexample exposed the same mistake in producer and reference; both now require the expected preceding exchange minute.'),
 ('20261109T200650493967Z-trade-twins-financial-full-field-original-artifacts-hand-fees-weekend-dividends-and-30-module-declaration','Hand borrow expectation used a prior closing rather than the next known opening mark for a second minute; corrected the hand arithmetic without changing formulas/tolerance. A gate-list edit missed its exact syntax; added the actual 30th module.'),
 ('20261109T200906145927Z-trade-twins-eleven-actual-financial-accounting-clock-barrier-funding-and-liquidity-mutations','Bad split broke conservation and raised ArithmeticError: not an assertion-only kill. Replaced with a consistently wrong split across quantity and basis; the independent book comparison then kills it.')]:
 r,_=receipt(identifier,False);failures.append(dict(receipt=identifier,reason=reason,exit_code=r['command']['exit_code']))
base=root/'verification/runs/20261109T175838150884Z-integrated-version025-coherent-current-source-browser-account-mutation-and-recovery-checkpoint'
receipt(base.name);base_manifest=read(base/'integrated025-source-manifest.json')
files={m['path']:source/m['path'] for m in base_manifest};files.update({name:source/name for name in current})
for name in ['trade-twins-contract.json','trade-twin-financial-contract.json']:
 assert (root/'verification/fixtures'/name).read_bytes()==(source/'verification/fixtures'/name).read_bytes()
 files['verification/fixtures/'+name]=source/'verification/fixtures'/name
files['STATUS.md']=root/'STATUS.md'
helpers=['check-dev026.py','trade-twins-core-mutations.py','trade-twins-entry-trace-mutations.py','trade-twins-source-authority-mutations.py','trade-twins-financial-mutations.py','check-current-trade-twins-full-gate.py','audit-trade-twin-financial-books.py','checkpoint-trade-twins-financial.py','restore-trade-twins-financial.py','trade-twins-next-execution-plan.md','trade-twins-financial-component-notes.md']
helpers+=['trade_twin_features_draft.py','test_trade_twin_features_prototype.py','check-trade-twin-feature-prototype.py','mutate-trade-twin-feature-prototype.py','trade_twin_decimal_grading_draft.py','test_trade_twin_decimal_grading_prototype.py','check-trade-twin-decimal-grading-prototype.py','mutate-trade-twin-decimal-grading-prototype.py','probe-trade-twins-10000-financial-sets.py']
helpers+=['profile-trade-twin-original-authority.py']
helpers+=['check-trade-twin-coincident-clock-boundaries.py']
helpers+=['trade-twins-durable-worker-design.md']
helpers+=['reconcile-trade-twins-baseline-regression.py','capture-spread-fixture-preimage.py','install-spread-boundary-tests.py','spread-read-repair-boundary-supplement.py','spread-empty-and-interrupted-boundaries.py']
files.update({'verification/runs/'+name:root/'verification/runs'/name for name in helpers})
manifest=[];archive=out/'trade-twins-financial-source.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
 for name,p in sorted(files.items()):
  assert p.is_file() and not p.is_symlink() and not name.startswith(('data/','frontend/node_modules/')) and not any(part.lower().startswith('.env') for part in Path(name).parts)
  assert p.suffix.lower() not in {'.sqlite3','.db','.parquet','.gz','.mp4','.webm','.png','.jpg','.zip'}
  raw=p.read_bytes();z.writestr(name,raw);manifest.append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
with zipfile.ZipFile(archive) as z:
 assert len(z.namelist())==len(manifest)
 for m in manifest:raw=z.read(m['path']);assert len(raw)==m['bytes'] and hashlib.sha256(raw).hexdigest()==m['sha256']
(out/'trade-twins-financial-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
env=os.environ.copy();env.update(PYTHONPATH=str(source),PYTHONNOUSERSITE='1')
probe=subprocess.run([sys.executable,'-c','from backend.lab.research import core_hash,current_core_hash;import json;print(json.dumps(dict(loaded=core_hash(),current=current_core_hash())))'],cwd=source,env=env,capture_output=True,text=True,check=True)
core=json.loads(probe.stdout);assert core['loaded']==core['current']
assert current=={p.relative_to(source).as_posix():sha(p) for p in source_paths(source)}
value=dict(scope=__doc__,source_files=current,isolated_core=core,archive_files=len(manifest),archive_sha256=sha(archive),resolved_case_lineage_counts=counts,original_global_command_exit_code=1,single_all_green_invocation=False,baseline_reconciliation_receipt=ids['full'],gate=gate,independent_books=books,mutation_proofs=proofs,retained_failures=failures,receipts=ids,
 durable_workflow_financial_sets_executed=0,separate_uninstalled_prototype=dict(sets_per_policy=10000,policies=2,financial_occurrences=20000,independent_unique_books=28,all_ties_retained=True,source_trades=1,minutes=390,elapsed_seconds=prototype['elapsed_seconds'],peak_working_set_bytes=prototype['absolute_process_peak_working_set_bytes']),main_app_source_replaced=False,final_acceptance_certified=False,
 remaining='Causal candidate ATR features and sealed original-authority preparation; durable financial sets/parts/trials/child/failures/recovery; actual10000 complete financial sets for both policies; API/UI/exports and integration; then remaining era/replication/stability/ensemble/stress and original83/422/120 final conformance.',
 recovery_limits='Source only. No installed dependencies, actual credentials, user prices, live DBs, private coverage DBs, browser traces or video. Existing locked environment is reused by the separate actual restore test; not a fresh installation.')
(out/'trade-twins-financial-checkpoint.json').write_text(json.dumps(value,indent=2),encoding='utf-8')
print(json.dumps(dict(source_files=len(current),archive_files=len(manifest),core=core,tests=counts['tests'],actual_component_mutants=35,separate_prototype_mutants=12,independent_books=114,durable_workflow_financial_sets_executed=0,uninstalled_prototype_sets_per_policy=10000,final_acceptance_certified=False),indent=2))
