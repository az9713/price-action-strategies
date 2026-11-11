"""Update status and evidence links only after successful coherent checkpoint; preserve historical failures."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
root=Path.cwd()
def latest(label):
 p=sorted((root/'verification/receipts').glob('*-'+label+'.json'))[-1];return p,json.loads(p.read_text(encoding='utf-8'))
checkpoint_path,checkpoint_receipt=latest('search-statistics-current-twelve-receipt-source-fixture-build-recovery-checkpoint')
assert checkpoint_receipt['command']['exit_code']==0
checkpoint=json.loads((root/next(a['path'] for a in checkpoint_receipt['artifacts'] if a['path'].endswith('/checkpoint.json'))).read_text(encoding='utf-8'))
items=checkpoint['selected_receipts'];assert len(items)==12
lookup={r['receipt'].split('Z-',1)[1]:root/'verification/receipts'/(r['receipt']+'.json') for r in items}
full=next(p for label,p in lookup.items() if 'source-full-regression' in label);receipt=json.loads(full.read_text(encoding='utf-8'))
xml=root/next(a['path'] for a in receipt['artifacts'] if a['path'].endswith('junit.xml'));suites=list(ET.parse(xml).iter('testsuite'))
tests=sum(int(s.attrib['tests']) for s in suites);assert tests==1517 and not any(int(s.attrib.get(k,0)) for s in suites for k in ['failures','errors','skipped'])
labels={
 'full':'search-statistics-final-locator-source-full-regression-and-sixteen-module-coverage',
 'coverage':'search-statistics-final-locator-sixteen-module-numerical-coverage-gate',
 'build':'search-statistics-final-locator-current-typed-build',
 'mutations':'search-statistics-final-locator-five-isolated-source-mutations',
 'eight_mutations':'search-statistics-final-locator-eight-prescribed-source-mutations',
 'dsr_browser':'search-statistics-current-main-corrected-accessible-name-two-desktop-workflows',
 'dsr_audit':'search-statistics-twelve-historical-browser-accounts-independent-decimal-csv-moments-offline',
 'existing_browser':'search-statistics-current-main-valid-synthetic-tag-fourteen-desktop-workflows',
 'twenty_audit':'search-statistics-current-twenty-existing-browser-accounts-independent-decimal',
 'six_audit':'search-statistics-current-six-joint-study-accounts-independent-decimal-csv-offline',
 'runtime':'search-statistics-final-locator-main-http-owner-and-obsolete-endpoint-probes',
 'inventory':'search-statistics-final-locator-422-plan-inventory',
}
paths={k:lookup[v] for k,v in labels.items()};paths['checkpoint']=checkpoint_path;paths['release']=latest('search-statistics-current-422-release-remains-incomplete')[0]
def link(key,title):return '['+title+']('+paths[key].relative_to(root).as_posix()+')'
paragraphs=[
 '## Current0.18 — verified diagnostic checkpoint',
 'The managed app answers at http://127.0.0.1:8767 with core `'+checkpoint['core_hash']+'` and frontend `index-CQOVzNA7.js`. The full objective remains active: **not ready for final release**. All83 requirements/422 mandatory cases and120 baseline cases remain binding.',
 link('runtime','Actual managed owner, duplicate-store refusal, current served assets and obsolete-endpoint probes')+' pass. Session82583 remains the managed main. Former session62773 and its original launcher/HTTP/worker exited after Ctrl+C, whose tool status1 is retained as an interruption rather than relabeled0. Known old8768..8771 health endpoints did not respond to bounded probes. Native OS TCP inventory omitted the answering main endpoint, so no new OS-wide closed-port certificate is claimed.',
 'The proliferation came from leftover verification servers and exceptional shutdown without finally cleanup. D037 now gives each store a noninherited OS lease, rejects duplicate worker-enabled APIs and manages worker shutdown from the parent. A normal app has launcher/HTTP/worker children; historical fourth-child types were not recorded. Agent-managed restarts replace manual taskkill requests.',
 'D038 connects the existing Deflated Sharpe Ratio formula to complete saved searches. Trial-count/dispersion assumptions freeze before queueing; empirical dispersion includes losses; daily units, undefined values and original profit remain explicit. Scores are diagnostics under assumptions, not inferred independence or candidate gates. Prior searches and serial dependence remain limitations.',
 link('full','Full current regression')+f': **{tests} passed**,4 warnings, no failures/skips. '+link('coverage','All sixteen numerical coverage gates')+' meet unchanged95% statements/90% branches; search_statistics100%/93.75%. Coverage and test totals do not establish all-case acceptance.',
 link('dsr_browser','Two actual diagnostic desktop journeys')+' pass at1920x1080 and1280x720, including every28-page offline deck per profile, invalid-input no-queue rejection, saved exports and all18 scenario rows. '+link('dsr_audit','Independent twelve-account audit')+' verifies complete supplied-signal Decimal accounting, daily returns, every statistical moment/score, all CSV rows, saved facts and58 PNGs. Each fixed six-config seed42 cohort has five no-trade accounts and one four-trade losing account (about-$1158.16); all are retained, with30 undefined and6 defined scenario scores across both profiles. These are repeated scenario instances, not independent market replications or a profitable strategy claim.',
 link('existing_browser','Fourteen existing desktop workflows')+' pass, including frozen whole-portfolio screening/final cancel-resume, fixed/changing borrowing, news, ordinary/shared accounts and response ownership. '+link('twenty_audit','Twenty complete existing-workflow accounts')+' and '+link('six_audit','Six complete joint-study accounts')+' independently reconcile. Synthetic joint-study prices/lending and historical cached prices remain distinguished. The prior real SPY/QQQ screen still had no_candidates; no new untouched final result is claimed here.',
 link('mutations','Five DSR mutations')+' plus '+link('eight_mutations','eight prescribed causal/order/accounting/guard/persistence mutations')+' are killed by assertions; unmodified baselines pass with zero collection errors/skips and original sources unchanged. '+link('build','Typed frontend build')+' passes; the large-bundle warning remains.',
 link('checkpoint','Coherent recovery checkpoint')+f" checks12 identical-subject passing receipts/{checkpoint['artifact_files_checked']} artifacts and archives{checkpoint['source_archive_files']} source/fixture/build/input files. Credentials, all traces, source-video media, market-data caches and installed dependencies are excluded. This is not clean-install reproduction or global privacy certification.",
 link('inventory','Planning inventory')+' remains83/422/120. '+link('release','Release gate')+' correctly rejects completion:0/422 final-certified means no complete frozen release certificate, not zero implemented/tested behavior. Every original acceptance obligation remains.',
 'First failures remain in [defects](verification/defects.json): authored geometry initially produced no trades, presenter keyword/page bounds failed, browser locator omitted help text, synthetic prefix violated symbol rules, native-inventory parsing failed and the API preflight requested an unsupported route. Corrections preserve original zero-trade controls, seed/configuration cohort, rendering bounds, validation rules, exact numerical tolerances and zero-network assertions.',
]
status=root/'STATUS.md';old=status.read_text(encoding='utf-8');tail=old[old.index('## Source fidelity and differences'):]
tail=tail.replace('The0.17 checkpoint had1468 passed','The historical0.17 checkpoint had1468 passed')
status.write_text('# Implementation status\n\n'+'\n\n'.join(paragraphs)+'\n\n'+tail,encoding='utf-8')
index=root/'verification/evidence-index.md';oldindex=index.read_text(encoding='utf-8');(root/'verification/runs/evidence-index-search-statistics-progress.md').write_text(oldindex,encoding='utf-8')
tail=oldindex[oldindex.index('## Historical0.17'):];prefix='## Current0.18 — coherent diagnostic checkpoint\n\nSee [status](../STATUS.md) for remaining scope and source-video differences. This is component evidence, not final422-case acceptance.\n\n'
for key,title in [('full','1517-test full regression'),('coverage','Sixteen-module coverage gate'),('build','Typed frontend build'),('dsr_browser','Two diagnostic desktop journeys'),('dsr_audit','Twelve independent historical diagnostic accounts'),('existing_browser','Fourteen existing desktop journeys'),('twenty_audit','Twenty existing accounts'),('six_audit','Six joint-study accounts'),('mutations','Five DSR source mutations'),('eight_mutations','Eight prescribed mutations'),('runtime','Managed ownership/source/assets/obsolete endpoint probes'),('inventory','83/422/120 inventory'),('release','Release rejection retained'),('checkpoint','Twelve-receipt recovery archive')]:
 prefix+='- ['+title+']('+paths[key].relative_to(root/'verification').as_posix()+').\n'
index.write_text(prefix+'\n'+tail,encoding='utf-8')
path=root/'verification/defects.json';data=json.loads(path.read_text(encoding='utf-8'))
for d in data['defects']:
 if d['id']=='D-VERIFY-DSR-UI-LOCATOR-001':d.update(status='corrected_same_fixture_two_desktops_and_independent_accounts_passed',regression_receipt=paths['dsr_browser'].relative_to(root).as_posix())
ids={d['id'] for d in data['defects']}
for d in [
 dict(id='D-VERIFY-DSR-SYNTHETIC-TAG-001',status='corrected_original_symbol_validation_preserved_fourteen_workflows_passed',area='Verification runtime fixture prefix',observed='The first fourteen-workflow run passed12; two synthetic imports rejected the runner-supplied dsr-current-regression prefix as Invalid symbol.',fix='Use valid fresh DSQ synthetic symbols, retaining original import checks, positive-control geometry, all20 symbols and complete screen/final/cancel/resume assertions. No market result is claimed from synthetic labels.',initial_evidence='verification/receipts/20261108T213152712776Z-search-statistics-current-main-fourteen-existing-desktop-workflows.json',regression_receipt=paths['existing_browser'].relative_to(root).as_posix()),
 dict(id='D-VERIFY-DSR-HISTORICAL-ROUTE-001',status='corrected_existing_audit_route_same_prespecified_cohort_passed',area='Historical API preflight route',observed='The first preflight requested unsupported /api/datasets/{id} and received404 before queueing.',fix='Use documented /api/datasets/{id}/audit; retain same frozen count6/seed42/families/frames and no profit requirement. Actual six accounts complete, one loses and five do not trade.',initial_evidence='verification/receipts/20261108T213621148883Z-search-statistics-prespecified-historical-api-worker-preflight.json',regression_receipt='verification/receipts/20261108T213635622838Z-search-statistics-prespecified-historical-existing-audit-route-api-preflight.json'),
]:
 if d['id'] not in ids:data['defects'].append(d)
path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('Current status, evidence index and all retained failures updated from completed receipts.')
