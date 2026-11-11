# Implementation status

Goal remains active: a fully functional, fully verified localhost strategy-testing application under PLAN.md and VERIFICATION_PLAN.md. **NOT VERIFIED / NOT READY for final release.** Current results are implementation and bounded verification, not final acceptance certification.

## Current application

- Locked Python3.13 and React/TypeScript/Vite; loopback same-origin API, spawned numerical worker, SQLite durable jobs, immutable strategies and results across seven screens.
- Read-only Alpaca SIP acquisition, checkpoints/retry, CSV/Parquet import, XNYS session audits, immutable hashes, causal split normalization and six signal charts.
- Ten distinct causal setup detectors, confirmations/filters, applicability validation and RULEBOOK **0.7**. All120 baseline family/timeframe/direction cases execute; complete supported-value/pairwise/higher-order/mutation acceptance remains unfinished.
- Minute-event long/short execution with one shared account, actual fees/borrow/distributions/splits, deterministic priorities, conservative fills, structure/time exits and daily marked equity. Aggregate entry participation belongs to an instrument/reference minute across rules, including synthetic-close/following-open boundaries.
- One to64 unique saved rules can compete in a portfolio. Save actual per-rule attribution and each rule's chart clock.64 remains an input bound, not a measured operating envelope.
- Frozen independent studies, guarded date/instrument reads across aliases/API/CLI, consumed-final continuation and saved-chart inspection. Portfolio-level frozen final studies and amendment/abandonment remain unfinished.
- **Cash and buy-and-hold comparisons:** real guarded API/worker jobs and Validation UI, same initial capital/dates/costs, one causal prior-volume entry attempt, actual equal-target allocations, whole shares/entry exposure/cash constraints, split/dividend/fractional-share/unpaid-receivable accounting and final selling fees. No passive stop/rebalance or equal-risk claim. Saved mismatched account/version inputs cannot acquire an unqualified strategy delta. Reopen and export actual JSON/CSV books.
- Metrics preserve losses and drawdown after nonpositive equity, null invalid percentage returns/Sharpe, reject nonfinite/overflowing inputs, reproduce primary-paper DSR moment examples and independently calculated sample moments, and validate/batch seeded circular daily-P&L resampling. Complete search-aware reporting/trial registry/sensitivity remains unfinished.
- Actual candles, cash ledgers, saved reports and JSON/CSV exports. Trade headings stay visible; actual exit/stop/target levels have an all-levels/price-only toggle. Saved benchmark fingerprints and older-version warnings are visible; health polling updates the running version. Full browser/API restart/schema recovery acceptance remains open.

## Latest executed evidence

| Check | Actual result | Receipt |
|---|---|---|
| Full backend with branch instrumentation and all authored fixture inputs | **601 pass**, including120 strategy matrix cases, independent execution, actual APIs/workers/recovery and new benchmark/statistical cases;224.32s | [full run](verification/receipts/20261108T080039313875Z-full-backend-passive-boundaries-current.json) |
| Current production/test source agreement | All production/test files still match that full run; only root README usage/count wording changed afterward. Original complete subject is retained | [explicit agreement](verification/receipts/20261108T080722800020Z-current-component-source-agreement.json) |
| Latest focused checkpoint after documentation update | **120 pass** across statistical/passive and evidence-system/catalog tests; independent from the120 strategy matrix count | [targeted run](verification/receipts/20261108T080644376194Z-statistical-passive-final-targeted-checkpoint.json) |
| Current typed frontend build | Pass; bundle index-nlEPeQec.js, large-bundle warning remains | [build](verification/receipts/20261108T080039150096Z-passive-compatible-comparison-typed-build.json) |
| Current actual browser stack | **Six journeys pass** at1920×1080/1280×720: single strategy, two-rule portfolio and benchmarks. Tests also run a genuinely different-capital benchmark, suppress its delta, reload saved results and export real files | [browser](verification/receipts/20261108T080057668858Z-passive-comparison-compatible-and-incompatible-browser.json) |
| Independent current browser artifact reread | Six JSON outputs/traces and **34 screenshots**, CSV values, exact chart geometry/current bundle; primary financial reports are byte-identical to independently checked reports | [reread/reuse proof](verification/receipts/20261108T080409441756Z-six-current-browser-artifacts-independent-reread.json) |
| Independent passive historical accounting | Both five-instrument passive reports: own Decimal quotes/fees/whole-share enumeration/ledger,20 daily marks and stdlib metrics; maximum money discrepancy **2e-11 dollars** | [passive reference](verification/receipts/20261108T075831273351Z-historical-passive-independent-decimal.json) |
| Independent current portfolio reference | Both reports match63 trades,12,780 ledger events,20 equity marks, attribution/basic metrics and62 entry-volume budgets | [portfolio reference](verification/receipts/20261108T080127679013Z-current-research-portfolio-independent-reference.json) |
| Independent current single-strategy reference |13 signals,10 trades,411 ledger events,20 daily points; basic metrics agree | [single reference](verification/receipts/20261108T080138101875Z-current-research-real-single-reference.json) |
| Targeted current visual review | Both unmodified current benchmark panels actually inspected; hash-recorded review and primary statistical-source manifest archived with focused checkpoint | [review](verification/runs/passive-visual-review-current.json) |
| Current numerical coverage gate | Metrics and passive books now pass. Data/signals/service still fail; overall gate remains unmet | [coverage gate](verification/receipts/20261108T080446231829Z-current-seven-module-numerical-coverage.json) |
| Current plan/catalog inventory |80 requirements,**345 mandatory acceptance cases**,120 matrix cases, no lint errors | [inventory](verification/receipts/20261108T075609876761Z-research-current-catalog-inventory.json) |
| Actual final release audit | **Fails correctly**: no frozen final subject and0 certified/345 uncertified acceptance cases | [release gate](verification/receipts/20261108T080446611629Z-current-345-case-release-unmet.json) |

Current numerical subject is26e6daf0932cd65a2b269596807bc47f8945c9d8c26db23ca4e4e947cf72e36c. All historical January2022 observations are already viewed discovery data. Positive active P&L and negative passive P&L are execution/integration observations, not a trading-edge finding. The historical passive Decimal oracle explicitly covers the action-free January sample; corporate-action paths have separate independent hand fixtures. Supplied-signal execution references do not independently certify all detector options. No implementation receipt is automatically promoted to acceptance.

## Numerical gates still required

Required thresholds remain95% statements/90% branches, with additional critical accounting/order/provider/holdout, mutation and complete use-case gates.

| Module | Statements | Branches | Outcome |
|---|---:|---:|---|
| config |98.96%|91.67%|pass |
| data |98.03%|80.30%|unmet |
| signals |92.98%|82.88%|unmet |
| engine |98.47%|90.98%|pass |
| metrics |100%|100%|pass |
| service |94.96%|74.49%|unmet |
| benchmarks |100%|97.50%|pass |

[Raw gaps](verification/runs/coverage-gaps-26e6daf0.json) retain remaining lines/branches. The passive feasible-quantity zero branch is unreachable from its positive-midpoint binary search; it is disclosed, not forced through a fake user path. Coverage does not prove correctness or replace financial/causality checks.

## Retained failures and limits

The initial statistical contracts retained29 failures/9 passes; a later extreme-finite case retained one failure/49 passes. Expected losses/rounding tolerances were preserved. The first benchmark implementation retained12 passes and a test-harness Headers.update error before correction. The feature-absent initial run and earlier portfolio volume, browser locator, typed build and image-geometry failures remain available. Catalog regeneration now retains every prior case and preserves existing implementation mappings; inspection found its older generator could omit the nine version2 additions. See [defects](verification/defects.json), [decisions](decisions.md) and [evidence index](verification/evidence-index.md).

The original six-symbol dataset3a96f0f067aee347ac149c19 remains ineligible because DIA lacks one January3 minute. The separately audited five-symbol child90f347229b2fb03ec112ee71 has no invented prices. Borrow history, action completeness and universe limitations remain explicit.

Functional timings do not certify performance. Prior37.69s startup/96.19s historical-job variability and the large UI bundle remain recorded. Acquisition/buffering, duplicated per-rule chart serialization, memory budgets and large searches require measured work. No100/1,000/10,000/100,000-scale acceptance is claimed.

## Required next work

1. Finish all supported confirmation/filter/day-boundary and pairwise/higher-order cases, causal invariants, missing data/API/accounting boundaries and critical mutations; meet the remaining data/signals/service coverage gates.
2. Implement matched random entries/shifted levels, behavior experiments, paired ablations, parameter/era/instrument stability, a complete trial registry and search-aware sensitivity/reporting. Add versioned news calendars and changing short-financing/recall scenarios.
3. Finish portfolio-level frozen final studies, amendment/abandonment and remaining real final/cancel/restart/corruption/error workflows.
4. Finish offline HTML presentation, mobile/keyboard/accessibility/privacy/security/offline acceptance and clean locked installation/reproduction.
5. Implement measured resource envelopes, cache/partition/optimize only with reference agreement; execute real100/1,000/10,000 workloads and actual bounded100,000-configuration stress handling.
6. Freeze the complete final subject and execute every mandatory acceptance case, then deliver the linked plan-to-code-to-test-to-receipt conformance report with no unmet mandatory behavior.

All original330 cases remain; nine portfolio and six statistical/passive cases were added. **All345 final acceptance cases remain uncertified.** The implementation map is partial. The full objective remains active and unfinished.
