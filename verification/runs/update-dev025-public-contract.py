"""Allowlisted isolated contract update; never touches live source or user data."""
from pathlib import Path
import hashlib,json,os,shutil,sys
root=Path.cwd();dev=root/'data/dev025/src';sys.path.insert(0,str(dev))
from backend.lab.config import Strategy,Costs,Portfolio,APPLICABILITY
from backend.lab.models import SpreadExperiment,SpreadContinuation
from backend.lab.spread import SpreadSettings
targets=['backend/lab/api.py','RULEBOOK.md','strategy.schema.json','tests/test_catalog_generation.py','verification/implementation-map.json']
def hashes():return {p:hashlib.sha256((dev/p).read_bytes()).hexdigest() for p in targets}
before=hashes()
p=dev/'backend/lab/api.py';s=p.read_text(encoding='utf-8');needle="        'sampling_policy':SearchSampling.model_json_schema(),";assert s.count(needle)==1
addition="\n        'spread_settings':SpreadSettings.model_json_schema(),'spread_run':SpreadExperiment.model_json_schema(),\n        'spread_continuation':SpreadContinuation.model_json_schema(),"
if addition not in s:s=s.replace(needle,needle+addition);p.write_text(s,encoding='utf-8')
p=dev/'strategy.schema.json';s=json.loads(p.read_text(encoding='utf-8'));assert set(s)=={'strategy','costs','portfolio','applicability'}
assert s['strategy']==Strategy.model_json_schema() and s['portfolio']==Portfolio.model_json_schema()
# The retained first failure discovered the earlier saved Costs contract lacked
# the already implemented borrow_scenario and its definition. Verify exactly
# that historical omission before regenerating; no execution model is changed.
current_costs=Costs.model_json_schema();legacy_costs=json.loads(json.dumps(current_costs));legacy_costs.pop('$defs');legacy_costs['properties'].pop('borrow_scenario')
assert s['costs']==legacy_costs
s['costs']=current_costs
s.update(spread_settings=SpreadSettings.model_json_schema(),spread_run=SpreadExperiment.model_json_schema(),spread_continuation=SpreadContinuation.model_json_schema());p.write_text(json.dumps(s,indent=2)+'\n',encoding='utf-8')
p=dev/'RULEBOOK.md';s=p.read_text(encoding='utf-8');assert s.startswith('# Numerical rulebook — version 0.24');s=s.replace('# Numerical rulebook — version 0.24','# Numerical rulebook — version 0.25',1)
s+='''

## Balanced spread and frozen account continuation — D045 / version0.25

This is an explicit equities adaptation of [AI Pathways / Brendan's source video](https://www.youtube.com/watch?v=z97PnFIPoFg), especially captured prompt page10. The demonstrated target is40000 selected versions across ten setup families,4000 per family, with400 proposals at each greedy choice and at least40 primary discovery-window signals.400 is not the final selected count. Exact private recipes, the14016 grid, private engine, distance and tie policy are unavailable. Our complete conditional dial catalog, prior-centered distance, deterministic ties and finite budget are published choices. Six named host recipes are not claimed as reproduced. Futures, forex and crypto are later options.

The default maximum is8000 batches per family: across ten families this permits80000 preparation batches and32million proposals. It is a bounded allowance, not an executed capacity result or completion-time estimate. Each batch can select at most one version. The selected target cannot exceed100000. The minimum signal setting cannot be below40. One strict integer seed from0 through2147483647 binds master and spread settings; booleans and floats are refused. The small UI preset requests one break-of-structure version, one-minute setups,40 proposals and two batches. It retains the40-signal floor and is separate from source scale.

Every conditional Strategy field is accounted for by the versioned recipe. Each proposal's independent generator key hashes protocol version, frozen seed, family, batch and ordinal. Freeze every bounded proposal file and its manifest before signal prices. Durable deterministic gzip preparation checkpoints are anchored to the original owned protocol journal. A committed checkpoint is verified and reused rather than redrawn; interrupted attempts, orphan files and failures remain evidence.

Balance is maintained separately by family and conditional parent context. For a context with k>1 choices, counts n_j and N=sum(n_j), its score is60/(k-1) times(k times sum(n_j squared) minus N squared), minus60N. The exact integer score change for adding choice j is120/(k-1) times(k n_j minus N). Sum active contexts, rank by the smallest change, and break ties by original proposal ordinal. The subtraction centers the uniform-prior expectation; lower score is a balancing choice, not a profit score or inferred source-host formula. Rank a frozen batch, skip already selected duplicates, and count actual primary discovery signals until one eligible version is selected or the batch is exhausted. Only accepted versions update balance.

Qualification performs no financial simulation. Full primary signal documents, including excluded warm-up signals, are content addressed and anchored with their original committed attempt. Date and primary predicates exclude other instruments from signal/account computation, displayed charts and viewed-window records. Whole-parent integrity hashing still covers all Parquet bytes; row groups may physically contain other instruments. Source-dataset context remains separate from actual primary scope. News variants require a frozen complete calendar and explicit knowledge assumptions. Current source, original proposal/signal bytes and protected-date authority are checked before work, reuse and publication. Journal replay is streamed. Failed, duplicate and unprobed proposals have distinct denominators from committed signal probes and financial accounts.

An exhausted budget is completed partial qualification evidence, never a successful partial financial cohort. Only the complete original unique qualified selection may freeze accounts. Replay the whole original qualification without new signals; verify its original result, journal, proposal and signal artifacts. Atomically reserve one child and freeze all selected rules, in order, before account P&L. Inherit original primary instrument, data identity, dates, seed, costs and borrow assumptions, capital/sizing, news, statistical assumptions and initial screening gates. The continuation body is an empty object; caller overrides are errors. Repeated and concurrent requests return the same original child, including canceled/failed children for original resume. Verify original authority before new/reused account work and again before financial publication. All complete accounts, losses and undefined scores remain saved. These are separately funded rule accounts, not a summed shared portfolio.

The immutable qualification root keeps account_phase=not_started. Financial progress and outcomes belong to the original separate child. Bounded parent status reconciles the original relationship event, forward link and indexed child reservation. A reverse lookup from bounded child-input metadata detects an orphan even if both parent-side records are lost; missing or incompatible indexes refuse replacement. Browsing saved metadata does not reopen prices or require the current financial engine. Explicit repair may restore a missing derived link only from intact original parent/result/child bindings. It never invents a missing original relationship, overwrites a conflicting link or creates another account.

Selected-rule pages use a verified partial seek index over original selected envelopes, with default50/max100 rows,16KiB per original row and2MiB response. Indexed selected counts must match saved metadata. Missing/corrupt selected events cannot become plausible empty results. A page verifies its requested original envelope/input/configuration identities; it is not full-prefix or final-product certification. Status remains within64KiB. Full original inputs, qualification result, journal/registry pages, complete child reports and JSON/CSV/standalone presentation exports remain available. New-spread controls and saved frozen assumptions are explicitly distinct; obsolete success and error responses cannot replace a newer job/page selection.

This component does not certify the40000-version source run, full resource envelope, vendor correctness or a trading edge.10000 matched trade twins, era/instrument replication, stability, equal-family ensembles, actual bounded100000 numerical stress and all remaining83-requirement/422-case/120-combination acceptance remain mandatory. Numerical coverage minima remain95% statements/90% branches with no exclusions or inferred hits. Original first failures, actual worker recovery, independent account/fact audits, browser/mobile/keyboard/privacy evidence and one coherent final acceptance are required.
'''
p.write_text(s,encoding='utf-8')
p=dev/'tests/test_catalog_generation.py';s=p.read_text(encoding='utf-8');assert s.count('version 0.24')==1;p.write_text(s.replace('version 0.24','version 0.25'),encoding='utf-8')
for source,target in [('spread-public-schema-authored.py','test_spread_public_schema.py'),('spread-reverse-index-supplement.py','test_spread_reverse_index.py')]:shutil.copyfile(root/'verification/runs'/source,dev/'tests'/target)
p=dev/'verification/implementation-map.json';mapping=json.loads(p.read_text(encoding='utf-8'));ids=[r['id'] for r in mapping['requirements']]
groups={
 'SPEC-001':(['RULEBOOK.md','frontend/src/SpreadFlow.tsx'],['tests/test_spread_public_schema.py']),
 'RES-001':(['backend/lab/spread_accounts.py'],['tests/test_spread_account_handoff.py','tests/test_spread_account_authority.py']),
 'RES-004':(['backend/lab/spread.py','backend/lab/spread_preparation.py','backend/lab/spread_jobs.py','backend/lab/spread_worker.py','backend/lab/spread_accounts.py','frontend/src/SpreadFlow.tsx'],['tests/test_spread.py','tests/test_spread_worker.py','tests/test_spread_account_handoff.py','tests/test_spread_orphan_reservation.py']),
 'RES-005':(['backend/lab/spread.py','backend/lab/spread_accounts.py'],['tests/test_spread_probe.py','tests/test_spread_account_exports.py']),
 'RES-008':(['backend/lab/spread_accounts.py','frontend/src/SearchStatistics.tsx'],['tests/test_spread_account_exports.py']),
 'JOB-001':(['backend/lab/spread_jobs.py','backend/lab/spread_worker.py','frontend/src/SpreadFlow.tsx'],['tests/test_spread_api.py','tests/test_spread_selection_pages.py','tests/test_spread_link_repair.py']),
 'JOB-002':(['backend/lab/spread_preparation.py','backend/lab/spread_jobs.py','backend/lab/spread_accounts.py','backend/lab/store.py'],['tests/test_spread_account_handoff.py','tests/test_spread_orphan_reservation.py','tests/test_spread_reverse_index.py']),
 'JOB-003':(['backend/lab/spread_worker.py','frontend/src/SpreadFlow.tsx'],['tests/test_spread_worker.py']),
 'UI-003':(['frontend/src/App.tsx','frontend/src/SpreadFlow.tsx'],['tests/test_spread_api.py']),
 'UI-006':(['frontend/src/SpreadFlow.tsx'],['tests/test_spread_public_schema.py']),
 'UI-007':(['frontend/src/SpreadFlow.tsx'],['tests/test_spread_selection_pages.py']),
 'RPT-002':(['backend/lab/presenter.py','frontend/src/SpreadFlow.tsx'],['tests/test_spread_account_exports.py']),
 'RPT-003':(['backend/lab/spread_jobs.py','backend/lab/api.py','frontend/src/SpreadFlow.tsx'],['tests/test_spread_selection_pages.py','tests/test_spread_selection_scale.py','tests/test_spread_link_repair.py'])}
for item in mapping['requirements']:
 if item['id'] not in groups:continue
 for field,values in zip(['implementation','tests'],groups[item['id']]):
  for path in values:
   # A missing historical test filename must not become a false mapping.
   assert (dev/path).is_file(),path
   ref=dict(path=path,scope='D045 component reference under verification; not final case certification')
   if ref not in item[field]:item[field].append(ref)
 if 'Balanced spread and frozen account continuation — D045 / version0.25' not in item['rulebook_sections']:item['rulebook_sections'].append('Balanced spread and frozen account continuation — D045 / version0.25')
assert ids==[r['id'] for r in mapping['requirements']] and len(ids)==83
p.write_text(json.dumps(mapping,indent=2)+'\n',encoding='utf-8')
out=Path(os.environ['PA_EVIDENCE_RUN_DIR']);(out/'isolated-public-contract-update.json').write_text(json.dumps(dict(before=before,after=hashes(),live_source_unchanged=True,requirements=83,mandatory_cases=422,matrix=120),indent=2),encoding='utf-8')
