"""Record scoped durable-backend progress, original failures and the unfinished account/UI boundary."""
from pathlib import Path
import hashlib,json,os,shutil
root=Path.cwd();out=Path(os.environ['PA_EVIDENCE_RUN_DIR'])
ids=dict(checkpoint='20261109T131439007172Z-spread-durable-explicit-source-overlay-original-evidence-and-retained-failure-checkpoint',
 runtime='20261109T131433727202Z-spread-durable-post-verification-one-managed-server-tree-and-duplicate-store-refusal',
 gate='20261109T131000253723Z-spread-durable-current-four-module-unrounded-95-90-passing-gate',
 audit='20261109T123836194035Z-spread-durable-original-artifacts-independent-protocol-signal-and-registry-audit',
 full='20261109T122423390444Z-spread-durable-backend-current-full-isolated-regression-and-four-module-coverage',
 focused='20261109T124940000407Z-spread-expanded-current-focused-corruption-recovery-and-four-module-coverage',
 supplement='20261109T130625762092Z-spread-worker-final-21-current-cancel-contract-manifest-and-artifact-faults',
 mutations='20261109T130746905841Z-spread-durable-corrected-manifest-boundary-eight-isolated-guard-mutations',
 pending='20261109T130635969373Z-spread-account-continuation-owned-development-first-unimplemented-contract')
receipts={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for key,identifier in ids.items():
 p=root/'verification/receipts'/(identifier+'.json');r=json.loads(p.read_text(encoding='utf-8'));assert r['command']['exit_code']==(1 if key=='pending' else 0)
 for a in r['artifacts']:
  q=root/a['path'];q.resolve().relative_to(root);assert q.stat().st_size==a['bytes'] and sha(q)==a['sha256']
 receipts[key]=r
def artifact(key,name):return json.loads((root/next(a['path'] for a in receipts[key]['artifacts'] if a['path'].endswith('/'+name))).read_text(encoding='utf-8'))
checkpoint=artifact('checkpoint','spread-durable-checkpoint.json');gate=artifact('gate','spread-durable-coverage-gates.json');runtime=artifact('runtime','current-process-tree.json');mutations=artifact('mutations','spread-durable-mutations.json')
assert gate['ready'] and len(gate['gates'])==4 and all(g['minimum_statements']==95 and g['minimum_branches']==90 for g in gate['gates'])
assert not runtime['separate_obsolete_project_python_detected'] and runtime['duplicate_store_start_rejected'] and not runtime['kill_performed']
assert mutations['all_test_killed'] and len(mutations['mutants'])==8 and mutations['baseline']['tests']==68
ledger_path=root/'verification/defects.json';ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
for index,failure in enumerate(checkpoint['historical_failures_retained'],1):
 identifier='D-SPREAD-DURABLE-'+str(index).zfill(3)
 if any(d['id']==identifier for d in ledger['defects']):continue
 pending='owned-development-first-unimplemented-contract' in failure['receipt']
 ledger['defects'].append(dict(id=identifier,status='open_account_continuation_not_implemented' if pending else 'retained_original_failure_scoped_durable_checks_passed',
  area=failure['receipt'].split('Z-',1)[-1].removesuffix('.json'),initial_evidence=failure['receipt'],
  evidence_scope='Original authored missing behavior, test-harness failure or coverage failure; see exact receipt. No original failure removed.',
  current_checkpoint='verification/receipts/'+ids['checkpoint']+'.json',current_coverage='verification/receipts/'+ids['gate']+'.json',final_acceptance_certified=False))
for d in ledger['defects']:
 if d['id'].startswith('D-SPREAD-DEVELOPMENT-'):d['status']='isolated_core_worker_api_checked_account_ui_and_final_integration_pending'
ledger_path.write_text(json.dumps(ledger,indent=2),encoding='utf-8');(out/'defects.json').write_bytes(ledger_path.read_bytes())
for name in ['PLAN.md','VERIFICATION_PLAN.md']:
 p=root/name;q=out/'documentation-overlay'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,q)
 assert (root/'data/dev025/src'/name).read_bytes()==p.read_bytes()
def prefix(relative):
 def link(key,label):return '['+label+']('+relative+ids[key]+'.json)'
 return '\n\n'.join([
  '## D045 in progress — durable spread backend verified in isolation',
  'The project remains active and not ready for release. The verified0.24 app remains at http://127.0.0.1:8767. The new backend lives in data/dev025/src; it has not been merged into the running app or its UI. No credentials, real cached prices, main database or installed dependencies were copied.',
  'Restartable deterministic batch preparation freezes every bounded proposal before first signals. An owned transactional original journal anchors each checkpoint and staged probe attempt. Complete primary-only signal artifacts are verified before reuse and again before publication. Event replay streams; status and journal pages are bounded. Preview/create/status/event/result APIs are implemented in isolation. Three actual owned interpreter-death/recovery boundaries preserve original checkpoints and distinct attempts.',
  link('full','Full isolated backend regression:2036 passing tests')+'. '+link('focused','254 focused corruption/recovery cases')+' and '+link('supplement','21 worker-fault cases')+' pass. Counts overlap and must not be added. '+link('gate','All four new module gates')+' meet the unchanged95% statement/90% branch minima using independently reconciled actual coverage databases on identical backend sources. No inferred coverage or threshold reduction is used.',
  link('audit','Independent original-artifact audit')+' reconciles80 frozen proposals,36 original protocol events, nine actual synthetic primary-signal probes (eight zero, one110) and one selected rule with its original registry. Zero financial accounts were executed by qualification. This is not an independent detector,40000-version source execution, full resource bound or market-edge proof.',
  link('mutations','Eight actual isolated persistence mutations')+' are assertion-killed against a68-case green baseline, with zero collection errors/skips. '+link('checkpoint','Explicit reconstructible source overlay')+' preserves original evidence and17 historical failures. The plan/verification documentation delta is preserved with this status receipt. Credentials, cached prices, databases, raw traces/coverage DBs, video media and installed dependencies are excluded.',
  link('pending','Nine authored account-continuation cases')+' currently fail because create_spread_accounts is absent. This is an explicit open implementation gap. Next implement the complete selected-manifest-to-account handoff under original assumptions, one atomic linked child, primary/protected scope and original-parent checks; then bounded selection paging and UI workflows. RULEBOOK0.25, integrated full regression/browser/resource/mutation evidence and final plan-wide conformance remain pending.',
  link('runtime','Current native ownership and duplicate-start check')+' observes one managed launcher34720 -> HTTP40760 -> worker20832 tree,348 idle jobs and no separate obsolete project Python process in the bounded inventory. Duplicate same-store startup is refused. No process was killed and no manual taskkill is needed.',
  'The original83 requirements/422 mandatory cases/120 baseline combinations remain binding.10000 matched trade twins, era/instrument replication/stability/equal-family ensembles, actual bounded100000 numerical stress, remaining detector/dial/lifecycle/input/scale boundaries, mobile/accessibility/security/privacy/clean reproduction and one final conformance certificate remain mandatory. Source: [AI Pathways/Brendan video](https://www.youtube.com/watch?v=z97PnFIPoFg). Exact private recipes/grid/engine remain unknown. Futures, forex and crypto remain later options. The older isolated-core and0.24 entries below are historical checkpoints.'
 ])+'\n\n'
for name,relative in [('STATUS.md','verification/receipts/'),('verification/evidence-index.md','receipts/')]:
 p=root/name;old=p.read_text(encoding='utf-8');assert not old.startswith('## D045 in progress — durable spread backend');p.write_text(prefix(relative)+old,encoding='utf-8');(out/p.name).write_bytes(p.read_bytes())
(out/'durable-documentation.json').write_text(json.dumps(dict(scope=__doc__,receipt_ids=ids,retained_failures=len(checkpoint['historical_failures_retained']),core_worker_api_isolated=True,account_continuation_implemented=False,main_app_source_replaced=False,final_acceptance_certified=False),indent=2),encoding='utf-8');print(json.dumps(dict(retained_failures=len(checkpoint['historical_failures_retained']),account_continuation_implemented=False,main_app_source_replaced=False,final_acceptance_certified=False)))
