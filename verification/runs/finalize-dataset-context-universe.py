"""Publish the corrected universe-preserving D040 checkpoint; retain every earlier scope/failure."""
from pathlib import Path
import json
root=Path.cwd()
def receipt(label,code=0):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];r=json.loads(p.read_text(encoding='utf-8'));assert r['command']['exit_code']==code
 return p,r
labels={
 'tests':'dataset-context-unrestricted-universe-current-92-focused-regression',
 'browser':'dataset-context-unrestricted-universe-and-original-four-desktop-workflows',
 'mutants':'dataset-context-unrestricted-universe-eight-isolated-source-mutations',
 'audit':'dataset-context-unrestricted-universe-four-account-independent-facts-and-all-pages',
 'original':'dataset-context-unrestricted-universe-original-authored-api-csv-offline-contract',
 'build':'dataset-context-universe-preserving-authoritative-label-typed-build',
 'runtime':'dataset-context-unrestricted-universe-managed-owner-after-own-contract-job-completed',
 'plan':'dataset-context-unrestricted-universe-83-422-120-plan-inventory',
 'checkpoint':'dataset-context-unrestricted-universe-eight-receipt-recovery-checkpoint',
}
items={k:receipt(v) for k,v in labels.items()}
checkpoint=json.loads((root/next(a['path'] for a in items['checkpoint'][1]['artifacts'] if a['path'].endswith('/checkpoint.json'))).read_text(encoding='utf-8'));assert len(checkpoint['selected_receipts'])==8 and len(checkpoint['historical_failures_retained'])==11
def rel(k):return items[k][0].relative_to(root).as_posix()
def failed(label):return receipt(label,1)[0].relative_to(root).as_posix()
p=root/'verification/defects.json';ledger=json.loads(p.read_text(encoding='utf-8'))
row=next(d for d in ledger['defects'] if d['id']=='D-AGGREGATE-DATASET-PROVENANCE-001')
row.update(status='fixed_universe_preserving_component_workers_csv_four_desktops_and_independent_audit_pass_final_conformance_pending',regression_receipt=rel('original'),browser_regression_receipt=rel('browser'),independent_regression_receipt=rel('audit'))
extra=[
 dict(id='D-VERIFY-DATASET-API-PAGE-COUNT-001',status='corrected_exact_added_and_original_pages_no_price_guard_preserved',area='Existing presenter API fixture',observed='The expanded API run passed59 and failed the old four-page total after four provenance pages were added.',fix='Require exactly eight pages, the exact four new titles and all original account/uncertainty content; keep raw-price/sealed-data access forbidden. Corrected60-case protocol regression passes; current92 checks include this adapter test.',initial_evidence=failed('dataset-context-current-existing-api-http-import-export-and-study-protocol-regression'),regression_receipt=receipt('dataset-context-existing-api-exact-added-and-original-pages-http-study-regression')[0].relative_to(root).as_posix(),current_regression_receipt=rel('tests')),
 dict(id='D-DATASET-UNIVERSE-CAP-001',status='fixed_preexisting_import_scope_preserved_actual_21_symbol_worker_and_four_desktops_pass',area='Introduced metadata-only instrument cap',observed='An actual21-instrument import was eligible, but new metadata validation rejected analysis with409. The importer had no corresponding20-instrument analysis limit.',fix='Remove the new cap. Retain complete canonical arrays and all indexed facts. Page20 UI labels; whole-list facts show a sourced count above20 with every member on indexed pages. Keep original upload/quality/presentation budgets. The exact21-member control and restoring-cap mutant verify the correction.',initial_evidence=failed('dataset-context-authored-preexisting-twenty-one-instrument-universe-first-regression'),regression_receipt=rel('tests'),browser_regression_receipt=rel('browser'),mutation_regression_receipt=rel('mutants')),
 dict(id='D-VERIFY-DATASET-RUNTIME-IDLE-001',status='corrected_sequential_runtime_after_own_job_completed_original_guard_preserved',area='Verification orchestration dependency',observed='Runtime idle assertion ran concurrently with the original-contract verifier creating its own actual job. It failed while the contract workflow subsequently completed.',fix='Wait for that workflow to complete, then rerun the unchanged idle/owner/asset/duplicate checks sequentially. No worker/queue guard, job state or assertion was relaxed.',initial_evidence=failed('dataset-context-unrestricted-universe-managed-owner-exact-assets-and-duplicate-refusal'),regression_receipt=rel('runtime')),
]
ids={d['id'] for d in ledger['defects']}
for record in extra:assert record['id'] not in ids;ledger['defects'].append(record)
p.write_text(json.dumps(ledger,indent=2)+'\n',encoding='utf-8')
def prefix(base):
 def link(k,title):return '['+title+']('+('verification/' if base=='status' else '')+'receipts/'+items[k][0].name+')'
 return '\n\n'.join([
 '## Current0.20 — universe-preserving provenance checkpoint',
 'The managed app answers at http://127.0.0.1:8767. Current core is `f165bc304b0f712ca5c5929793f42daa42333391ce697b5f02b00ae353a6c10b`; frontend is `index-Dao8IxvZ.js`. The goal remains active and **not ready for final release**. Full current regression/all18 numerical gates and the coherent422-case final audit remain mandatory; the1579-test/all17-module result below is historical0.19.',
 'D040 freezes only verified-manifest dataset identity/hash, declared kind/source and complete canonical instruments before every analysis queue/study registration. Validate before financing/prices, retain exact saved context in roots/accounts/CSVs/UI/offline facts, exclude arbitrary metadata/future actions, and distinguish absent legacy records. Explicit historical_market_data is recognized; unknown/unverified declarations are not inferred from current UI selections.',
 'The introduced20-instrument metadata cap is removed. An actual21-instrument eligible import now executes. The UI pages20 labels without dropping any members. The whole-list fact retains the entire array; above20 it displays an independently formatted count and points to pages containing every individual member. Existing upload, data-quality and presentation budgets are unchanged. Imports run off the HTTP loop under a per-app publication lock, preserving validation and atomic identity.',
 link('tests','92 focused checks')+' pass across all analysis workers, independent/shared study screening and consumed-final trade CSVs, corruption-before-read, removed-live-manifest exports, nullable behavior descriptors, legacy records, exact large-universe formatting and concurrent import/health controls. dataset_context.py has100% statements/branches in the focused run; this is not the complete18-module gate.',
 link('browser','Four desktop workflow tests')+' pass at1920x1080 and1280x720, including historical-selection isolation, actual old unclassified evidence, larger-import next/previous controls and saved Reports. '+link('audit','Independent manifests, complete accounts and offline facts')+' reconcile four saved account instances and84 offline-page PNGs. All four browser accounts have zero trades and remain unchanged. Separate actual synthetic study controls verify nonempty final trade CSVs. These are software controls, not a profitable strategy or untouched market replication.',
 link('mutants','Eight isolated source mutations')+' are detected, including restoring the accidental cap. Baseline43 passes; no collection errors/skips and original sources remain unchanged. '+link('original','The original aggregate-provenance contract')+' passes unchanged. '+link('build','Typed frontend build')+' passes; the large-bundle warning remains.',
 link('runtime','Managed owner, exact assets and duplicate-store refusal')+' pass after the verifier-owned job completes. Current managed session18377 has HTTP47800/worker40348 and holds the store lease. Previous managed sessions exited after Ctrl+C; interruption status1 is retained. Native PID inventory remains uncertified. No manual taskkill is needed.',
 link('checkpoint','Coherent component recovery checkpoint')+f" verifies8 identical-source passing receipts/{checkpoint['artifact_files_checked']} artifacts, retains11 historical failures and archives{checkpoint['source_archive_files']} source/fixture/build/input files. Credentials, traces, cached prices, source-video media and installed dependencies are excluded. This is not clean-install reproduction, global privacy certification or full release acceptance.",
 link('plan','Planning inventory')+' remains83 requirements/422 mandatory cases/120 baseline combinations. Next: bound job-status/list/control materialization and response sizes while preserving full immutable inputs on demand. The prior1000-config queued measurement returned986799 status bytes; it was not1000 numerical backtests. Actual10000/bounded100000 scale verification remains required.',
 'Source: [AI Pathways/Brendan video](https://www.youtube.com/watch?v=z97PnFIPoFg). Ten families and visible dials use declared US-stock/ETF adaptations with free data and explicit borrowing assumptions. Exact private engine/grid/six named recipe definitions remain unknown. Automated30920-frame analysis and1031 visual samples plus37 focused4K captures/15 prompt pages were not manual inspection of every frame. Balanced spread,10000 matched trade twins, era/replication/stability/family ensembles and remaining detector/dial/lifecycle/performance/accessibility/security/privacy/clean-reproduction/final conformance work remain mandatory. Futures, forex and crypto remain later options.',
 ('See [defects](verification/defects.json).' if base=='status' else 'See [defects](defects.json).')+' All first failures remain, including unsourced label digits, null descriptors, whole-list omission, blocked import health, legacy JSON spelling, stale page-count expectation, accidental universe cap and runtime-check orchestration. No financial formula, outcome, tolerance or final-date policy was altered.',
 ])+'\n\n'
for name,base in [('STATUS.md','status'),('verification/evidence-index.md','evidence')]:
 p=root/name;old=p.read_text(encoding='utf-8');assert old.startswith('## Current0.20')
 p.write_text(prefix(base)+old.replace('## Current0.20','## Historical0.20 preliminary',1),encoding='utf-8')
print(json.dumps(dict(focused_tests=92,desktop_tests=4,source_mutations=8,independent_accounts=4,offline_pngs=84,defect_records=len(ledger['defects']),full_current_regression_certified=False,final_acceptance=False)))
