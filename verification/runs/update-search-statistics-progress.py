"""Update untracked status/evidence commentary without editing the frozen implementation subject."""
from pathlib import Path
import json
root=Path.cwd();status=root/'STATUS.md';old=status.read_text(encoding='utf-8')
archive=root/'verification/runs/status-before-search-statistics-018.md'
if not archive.exists():archive.write_text(old,encoding='utf-8')
status.write_text('''# Implementation status

**Active; not ready for final release.** The binding inventory remains83 requirements/422 mandatory acceptance cases, including120 baseline strategy cases. Component passes do not certify the full plan.

## Current0.18 — search-bias workflow under verification

The managed app answers at http://127.0.0.1:8767 with current core `1687e8ae0d76a6eab75155727db6961b3fbdca96c25fc237e1add547ed4e2da0` and frontend `index-CQOVzNA7.js`. Server session82583 owns the store; HTTP PID40468/worker15640 were recorded. The prior managed tree exited after Ctrl+C. The actual duplicate-store startup exits3 while the original owner remains healthy. [Current HTTP/source/asset and duplicate-start receipt](verification/receipts/20261108T213135168889Z-search-statistics-current-main-http-owner-duplicate-refusal-and-served-assets.json). Native TCP inventory currently omits this answering endpoint, so no new OS-wide closed-port certificate is claimed. Two failed inventory verifiers are retained.

The duplicate-server root cause was leftover verification instances plus exceptional shutdown without finally cleanup. D037 adds a noninherited OS lease per store and parent-managed worker shutdown. Normal launcher/HTTP/worker children account for several PIDs; historical fourth-child types were not recorded. Future managed restarts are the agent's responsibility. No further manual taskkill is required.

D038 connects the existing Deflated Sharpe Ratio formula to complete parameter-search accounts. Assumptions freeze before queueing; empirical dispersion includes losing accounts; per-session units and undefined results remain explicit. JSON, full long CSV, UI and saved-only presentations carry all accounts and scenarios. It is a diagnostic under trial-count assumptions, never an inferred independent count, profitability claim or candidate gate. Prior searches and serial dependence remain uncorrected.

- [76 focused checks pass](verification/receipts/20261108T212406712342Z-search-statistics-current-complete-focused-export-boundaries.json), including the actual nonempty API/worker search, invalid policy pre-price rejection, recovery/tampering, unsupported/legacy exports and presentation facts. Original zero-trade controls are retained.
- [Five isolated statistical mutants killed](verification/receipts/20261108T212647293615Z-search-statistics-five-isolated-critical-numerical-source-mutations.json), with an unmodified34-test passing baseline and no collection errors/skips. The originals remain byte-identical.
- [Typed build passes](verification/receipts/20261108T212436893196Z-search-statistics-current-typed-frontend-build.json). Large-bundle warning remains.
- [First two-desktop diagnostic journey failed before queueing](verification/receipts/20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution.json): the test omitted help text from an exact accessible-name locator. Correct the locator after live recorded checks terminate, preserving the six-config seed42 fixture and all assertions.
- Full current backend regression/16-module95% statement/90% branch coverage and fourteen existing desktop workflows are running. No pass is claimed until receipts finish. Independent full-account/CSV/statistical/offline reread is pending.

## Source fidelity and differences

Source: [AI Pathways/Brendan video](https://www.youtube.com/watch?v=z97PnFIPoFg). Automated change analysis covered30,920 decoded frames; visual review sampled1,031 frames plus37 focused4K captures and15 prompt pages. This was not manual inspection of every frame. Local evidence is under research/screenshots and the implementation plan documents provenance.

Ten price-action families and visible dials have explicit equities rules. The private engine and complete six named preset definitions are unavailable; exact parity is not established. US stocks/ETFs replace the host's futures-first setting. We use free Alpaca historical data with explicit data/universe/corporate-action/lending limits. Borrowing availability and fees are assumptions unless supported by an imported scenario. Futures, forex and crypto remain later options.

The current parameter sampler and signal-conditional controls differ from the host's balanced/common sampling and10,000 matched-trade-twin funnel. Era, replication and equal-family ensemble stages remain unfinished. DSR does not replace these stages. Historical January2022 prices already viewed are discovery data, never an untouched final test. The prior SPY/QQQ shared study honestly produced no_candidates; final dates were not consumed or unlocked.

## Remaining mandatory work

1. Finish source-style balanced/common/named sampling,10,000 matched trade twins, era/replication/parameter stability and ensemble research workflows; maintain explicit unknown host recipes.
2. Complete detector lifetime/omission/birth-interval, every supported dial and compatible interaction, fault/critical-branch and mutation adequacy.
3. Complete all portfolio-study, amendment/abandonment, final-consumption and error/recovery acceptance beyond existing component cases.
4. Measure10,000 searches and bounded actual100,000 stress after final functionality freezes; bound large-plan job polling/control/result reads. Prior100/1000 measurements are component observations on one390-minute sample, not full-history throughput guarantees.
5. Complete mobile/keyboard/accessibility/security/privacy/export boundaries and locked clean-install reproduction.
6. Freeze one coherent final subject; provide case-by-case plan/code/test/receipt mappings and independent audit for all422 cases. The release gate still rejects final certification;0/422 final-certified does not mean zero behavior implemented or tested.

## Historical checkpoints

The0.17 checkpoint had1468 passed and all15 numerical module gates passing; fourteen desktop journeys and independent accounts also passed. Those receipts certify their historical source, not this0.18 implementation. [Prior full status snapshot](verification/runs/status-before-search-statistics-018.md), [runtime root cause](verification/runs/runtime-ownership-root-cause.md), [evidence index](verification/evidence-index.md), [retained defects](verification/defects.json).
''',encoding='utf-8')
index=root/'verification/evidence-index.md';text=index.read_text(encoding='utf-8')
if not text.startswith('## Current0.18'):
 text=text.replace('## Current0.17','## Historical0.17',1)
 prefix='''## Current0.18 — verification in progress

See [current status](../STATUS.md) for the live verdict and source-video differences. Full current regression/browser/account audits are pending; the previous0.17 checkpoint below is historical.

- [76 focused diagnostic/API/worker/export/presentation checks](receipts/20261108T212406712342Z-search-statistics-current-complete-focused-export-boundaries.json).
- [Five isolated DSR source mutants](receipts/20261108T212647293615Z-search-statistics-five-isolated-critical-numerical-source-mutations.json).
- [Current typed build](receipts/20261108T212436893196Z-search-statistics-current-typed-frontend-build.json).
- [Current managed HTTP owner, duplicate-store refusal and served assets](receipts/20261108T213135168889Z-search-statistics-current-main-http-owner-duplicate-refusal-and-served-assets.json).
- [Retained first browser locator failure](receipts/20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution.json), no search queued.
- Retained native-inventory verifier failures: [first](receipts/20261108T212947517626Z-search-statistics-current-managed-main-source-assets-and-single-store-owner.json), [second](receipts/20261108T213032070779Z-search-statistics-current-managed-main-native-powershell-owner-and-assets.json). Empty OS inventory is not proof that this answering server is absent; the final runtime receipt deliberately limits its claim to HTTP identities, lease/duplicate refusal and served assets.

'''
 index.write_text(prefix+text,encoding='utf-8')
path=root/'verification/defects.json';value=json.loads(path.read_text(encoding='utf-8'));ids={d['id'] for d in value['defects']}
records=[
 dict(id='D-DSR-AUTHORED-GEOMETRY-001',status='corrected_nonempty_and_original_zero_trade_controls_retained',area='Search diagnostic integration geometry',observed='Original jump geometry and first descending-cycle revision produced no trades under the unchanged sampled skip-run filters.',fix='Prespecified v2 rising daily baseline with descending intraday cycles supplies prior-session context and actual short signals. Keep original zero-trade control, same seed/config sampler and no profit requirement.',initial_evidence='verification/receipts/20261108T210716709776Z-search-statistics-actual-api-worker-recovery-full-csv-and-offline-first-integration.json',regression_receipt='verification/receipts/20261108T212406712342Z-search-statistics-current-complete-focused-export-boundaries.json'),
 dict(id='D-DSR-PRESENTER-API-001',status='fixed_original_page_limits_preserved_focused_regression_passed',area='Saved diagnostic presentation',observed='Actual nonempty integration first used unsupported metrics keyword, then exceeded existing two-large-statistics bound.',fix='Use stats keyword and split moments/scenarios into bounded pages; preserve max2 statistics/max3 notes and independent exact saved-fact audit.',initial_evidence='verification/receipts/20261108T211338360848Z-search-statistics-authored-skip-run-compatible-control-and-complete-exports.json',second_failure='verification/receipts/20261108T211645355813Z-search-statistics-correct-presenter-contract-and-complete-boundary-regression.json',regression_receipt='verification/receipts/20261108T212406712342Z-search-statistics-current-complete-focused-export-boundaries.json'),
 dict(id='D-VERIFY-DSR-UI-LOCATOR-001',status='identified_correction_pending_live_frozen_checks',area='Browser test accessible-name locator',observed='Both profiles stopped before queueing because the configuration-count label includes its help text.',fix='Use the observed accessible-name prefix, retaining the original seed/count/all assertions. No product field or numerical threshold is changed.',initial_evidence='verification/receipts/20261108T212531847400Z-search-statistics-current-main-two-desktop-workflows-first-execution.json'),
 dict(id='D-VERIFY-RUNTIME-INVENTORY-001',status='bounded_http_owner_check_passed_os_inventory_not_certified',area='Native runtime verifier inventory',observed='Both nested native PowerShell inventory commands returned empty output despite a live responding main endpoint; parsing failed. Ad hoc optional-psutil/nonexistent-lease-method checks also failed and are not evidence of lease reacquisition.',fix='Do not infer no listener from empty output. Verify actual HTTP identities/source/assets and duplicate-store startup refusal, explicitly excluding OS-wide inventory from scope.',initial_evidence='verification/receipts/20261108T212947517626Z-search-statistics-current-managed-main-source-assets-and-single-store-owner.json',regression_receipt='verification/receipts/20261108T213135168889Z-search-statistics-current-main-http-owner-duplicate-refusal-and-served-assets.json'),
]
value['defects'].extend(d for d in records if d['id'] not in ids);path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
print('Status, evidence index and retained-defect notes updated; no implementation subject edited.')
