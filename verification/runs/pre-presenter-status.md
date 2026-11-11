# Implementation status

The full objective remains active. **NOT VERIFIED / NOT READY for final release.** Catalog v6:82 requirements/397 mandatory acceptance cases;0 final-certified. Passing regression, coverage, browser or numerical checks certify only their declared scope.

The [verification plan revision review](verification/plan-conformance-review.md) records the current binding work-package sequence and seven-step final audit. Inventory/link checks pass and 45 catalog/evidence/recorder regression tests pass. The actual release gate still rejects completion with 0/397 certified cases. Earlier implementation receipts below retain their original subjects; subsequent verification-tooling and plan changes are not covered by an earlier full-suite run.

## Current application and changes

Local application: http://127.0.0.1:8765. RULEBOOK0.11; numerical subject146b61d9ad329746736d6496f51f629c2d784c3e14c3f36ff8903ab4f4450eed; typed bundle index-BgAtH58J.js (frontend code unchanged). Source: [AI Pathways / Brendan's video](https://www.youtube.com/watch?v=z97PnFIPoFg). PLAN.md/RULEBOOK.md record numerical adaptations and source differences.

News and3/5-session run filters now use the New York date when a signal becomes known at confirmation, including next-day confirmation. Setup and later execution remain separate clocks. A supplied news date can skip or reduce risk on that confirmation day; the versioned calendar acquisition/UI is still unfinished. Unsupported control-news scenarios now reject before any price loading. The existing transactional store already prevents duplicate active study jobs beyond the latest500 UI records; no store change was needed.

The seven sections include ten strategy families/six charts, long/short accounts, shared-capital portfolios, passive comparisons, matched random accounts,17 price diagnostics, paired rule comparisons and a durable trial ledger. These remain under the complete verification plan. The previous0.10/780-test/12-journey/39-account checkpoint is retained in [prior status](verification/runs/paired-ledger-prior-to-confirmation-status.md) and [evidence index](verification/evidence-index.md). Its twelve-flow browser evidence is historical; only the two fresh research journeys below are current0.11 browser checks.

## Current executed evidence

| Check | Actual result and scope | Receipt |
|---|---|---|
| Full backend/current test source |1071 pass,3 warnings,566.18s; includes120 baseline matrix cases,247 confirmation/filter cases and44 data/service boundary cases | [full1071](verification/receipts/20261108T123524467665Z-confirmation-calendar-and-input-guards-full-regression.json) |
| All11 numerical coverage modules |All pass unchanged95% statements/90% branches; this gate is separate from final acceptance | [numerical gate](verification/receipts/20261108T124621611922Z-confirmation-calendar-current-eleven-module-numerical-coverage-gate.json) |
| Six actual isolated source mutants |Unmodified168 selected fixtures pass; all six wrong implementations fail assertions, zero collection errors/skips; source/hashes/XML/logs retained | [mutations](verification/receipts/20261108T123626231317Z-confirmation-calendar-final-subject-six-critical-mutants.json) |
| Actual mirrored overnight pipeline |Ten HTTP/worker cases on authored1560-minute data: actual aggregation/detectors/engulfing/news/run/ledger and independent account execution, no injected contexts | [ten cases](verification/receipts/20261108T124109831542Z-authored-overnight-correct-header-ten-real-pipeline-reference.json) |
| Current historical account |13 signals,10 trades,411 ledger events,20 daily marks; independent Decimal supplied-signal execution and basic metrics with1e-7 money/1e-10 dimensionless tolerances | [historical reference](verification/receipts/20261108T123654770247Z-confirmation-calendar-current-historical-supplied-signal-reference.json) |
| Current typed build |Pass; same index-BgAtH58J.js; large-bundle warning remains | [build](verification/receipts/20261108T123626153171Z-confirmation-calendar-current-typed-build.json) |
| Two current research browser journeys |1920x1080 and1280x720 pass,41.1s; actual UI/API/worker/inspection/downloads | [browser](verification/receipts/20261108T123713681287Z-confirmation-calendar-two-desktop-research-journeys.json) |
| Current browser artifacts and reference books |16 required images, JSON/CSV and chart geometry match saved books; both accounts exactly match the independently executed historical baseline; standalone interval differences<=2.67e-11 dollars | [artifacts](verification/receipts/20261108T124351409195Z-confirmation-calendar-current-two-browser-artifact-reread.json), [independent books](verification/receipts/20261108T124355745133Z-confirmation-calendar-both-ui-books-and-standalone-interval-reference.json) |
| Planning and final acceptance gates |82/397 inventory valid; final release correctly fails with0 certified cases | [inventory](verification/receipts/20261108T124621653123Z-confirmation-calendar-current-plan-inventory.json), [release](verification/receipts/20261108T124621719311Z-confirmation-calendar-397-case-release-not-ready.json) |

Current statement/branch percentages: config98.96/91.67; data99.51/98.48; signals100/97.30; engine98.47/90.98; metrics100/100; service100/94.12; benchmarks100/97.50; controls100/94.05; behavior99.66/97.50; ablations100/100; trials100/93. Coverage is not detector completeness or full pairwise/mutation acceptance.

Selector unit fixtures inject explicit completed-context tables; separate real-minute/daily-hourly/reference cases exercise actual production stages. All1–24 confirmation windows and six confirmation modes have mirrored boundaries. Targeted mutations cover setup-day regression, short waiting windows, strict half-wick threshold, future-trend leakage, equal-run rejection and late control validation. Complete compatible dial pairs and all detector/execution/accounting/security mutations remain required.

The overnight API fixture independently expects long full/half sizes100/50 and short full/half99/50 because the full short account hits its exposure cap. It verifies eligibility/risk/account constraints without treating half risk as exactly half the shares. Its supplied date sets are not a certificate of versioned calendar acquisition or real-market profitability.

The [current integrity checkpoint](verification/receipts/20261108T125410482430Z-confirmation-calendar-evidence-integrity-and-source-checkpoint.json) checks12 receipts/333 artifact files and both trace CRCs; all selected source/input hashes match. The [129-file code/fixture/build archive](verification/runs/20261108T125410482430Z-confirmation-calendar-evidence-integrity-and-source-checkpoint/source-checkpoint.zip) excludes credentials, raw traces, media, market-data caches and installed dependencies. Byte integrity is not privacy acceptance or a final release freeze. One current1280 trade-chart image was actually viewed;16 required captures have artifact reconciliation.

## Open evidence privacy finding

A targeted inspection found internal anti-CSRF session headers and session-response tokens in both raw Playwright traces. No Alpaca credential-header fields were found in those inspected network/JSON members. A controlled restart invalidated the captured internal tokens: both return403; the new-token control reaches schema validation422 without creating a mutation. [Finding and containment](verification/receipts/20261108T125027446132Z-trace-internal-session-token-finding-and-containment.json).

**Trace redaction remains required and blocks privacy/final acceptance.** Raw historical traces remain local/private, are not privacy-accepted and must not be published. Preserve provenance while producing sanitized review artifacts and preventing future capture leakage. The source checkpoint excludes traces/credentials. Numerical or trace-integrity success does not certify privacy. No token values or hashes are included in the finding report.

## Source differences and data limits

US stocks/ETFs replace the host's NQ/ES futures. Ten visible families have explicit numerical adaptations; identical hidden code/trades/futures profits are not claimed. The six private named versions, full hidden presets and source results are unavailable. Complete40000 balanced/common-style sampling and the10000 matched trade-twin candidate funnel remain required work; current20 random accounts are not that funnel.

Audited five-symbol January2022 child90f347229b2fb03ec112ee71 and SPY child750176b4e01da2060d4900ca are selected, action-free, already-viewed discovery data. The six-symbol parent retains one missing DIA minute and remains ineligible. No price was invented. Viewed data are never untouched final evidence. Historical action/universe/lending completeness remain explicit gaps. Futures, forex and crypto remain later market options.

Historical execution/reference audits consume saved generated signals/feature geometry. They do not independently certify every detector event/omission, complete birth-known intervals, all supported configurations or an investment edge. Source screenshots establish specifications, not product acceptance.

## Required next work

1. Fix future trace capture redaction, safely derive reviewable sanitized historical artifacts, and verify privacy without erasing original provenance or silently changing receipts.
2. Implement the source's offline self-contained HTML presenter and all navigation/menu/replay/camera-area/pointer/highlight/provenance/layout controls. Finish mobile/keyboard/accessibility/offline and clean locked reproduction.
3. Complete detector/lifetime/omission, supported-option and compatible pairwise/higher-order acceptance; all critical mutation scopes beyond these six.
4. Finish era/instrument/parameter stability, source balanced/common/named sampling,10000 twin-set funnel, search-aware reporting/sensitivity.
5. Finish versioned news calendars, changing borrow availability/cost/recall scenarios, portfolio frozen-final studies, amendment/abandonment and all final/error/recovery cases.
6. Measure cache/partition/resource envelopes with actual100/1000/10000 searches and bounded100000-configuration stress handling. No unmeasured maximum history/runtime claim.
7. Freeze the coherent final subject, execute all397 mandatory cases and every required full browser/provider/offline/privacy/scale gate, complete requirement/code/test/receipt mappings and deliver the final conformance audit. Missing/stale/skipped/blocked/inconclusive evidence prevents completion.

Retained product failures and corrected verifier mistakes are in verification/defects.json. PLAN.md and VERIFICATION_PLAN.md remain binding; no original scope was removed.
