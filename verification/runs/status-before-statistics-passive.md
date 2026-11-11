# Implementation status

Goal remains active: a fully functional, fully verified localhost strategy-testing application under PLAN.md and VERIFICATION_PLAN.md. **NOT VERIFIED / NOT READY for final release.** Current work is implementation and bounded verification, not final acceptance certification.

## Current application

- Locked Python3.13 and React/TypeScript/Vite environments; same-origin localhost API, spawned numerical worker, SQLite jobs, immutable strategies and saved results across seven UI sections.
- Read-only Alpaca SIP acquisition, paging/retry/checkpoints, CSV/Parquet import, immutable hashes, actual XNYS session audits, causal split normalization and six charts. Source video/captures and market data remain local.
- Ten distinct causal setup detectors, confirmations/filters, parameter applicability and RULEBOOK.md **version0.6**. The120-case baseline matrix passes; full supported-value/pairwise/interaction and mutation conformance remains unfinished.
- Minute-event shared-capital long/short execution, fees/borrow/distributions/splits, deterministic priorities, conservative fills, clock/structure exits and daily marked equity. Independent Decimal execution uses its own clock/ledger/enumeration on supplied signals.
- **Shared-capital portfolio experiments:** choose one to64 distinct saved rules, freeze one account/cost/date set, generate signals per rule and run one joint account. Save per-rule identities, attribution and correct per-rule chart timeframes. Duplicate numerical rules reject.64 is an input bound, not a measured operating guarantee.
- Entry participation now belongs to an instrument/reference completed minute across all rules. Synthetic-close and following-open orders share the same sample. Every accepted entry saves reference volume and budget before/after. Exits retain the stated conservative bar-model liquidity assumption.
- Frozen independent studies, guarded dates across aliases/API/CLI, consumed-final continuation, saved-chart final inspection and result/checkpoint integrity. Portfolio-level frozen final studies and study amendment/abandonment remain unfinished.
- Loopback/origin/token/body-size boundaries, frozen numerical subjects and old-report warnings. Browser/API/worker recovery has targeted evidence; complete recovery/privacy/security acceptance remains open.
- JSON/CSV exports, actual candles/equity/ledgers, explicit daily drawdown and shared-account attribution. Trade headings stay visible; actual exit,raw stop/target and an all-levels/price-only chart toggle are implemented. Offline HTML presentation and advanced research controls remain unfinished.

## Current executed evidence

Verification-contract update2026-11-08 UTC: the plan now explicitly requires the per-change evidence cycle and a final one-row-per-case conformance table. The current80/339/120 inventory lints without errors ([receipt](verification/receipts/20261108T074018050510Z-verification-contract-plan-inventory.json)). **45 evidence-system tests pass** ([current regression](verification/receipts/20261108T074008343859Z-verification-contract-gates-final-regression.json)); they include36 isolated release-gate fault cases, six numerical-gate cases and three recorder cases. The first release-gate test preserved three false-pass failures for omitted/duplicate/unknown mappings; the corrected gate validates the full inventory. The actual [current release audit](verification/receipts/20261108T074017990514Z-verification-contract-real-release-unmet.json) still fails:339 cases remain uncertified. These additions change verification infrastructure/documentation, not the running numerical engine or UI.

| Check | Actual outcome | Receipt |
|---|---|---|
| Full backend with branch instrumentation | **489 tests pass**, including120 matrix cases, independent execution, portfolio/account/API/worker tests; coverage is not yet sufficient | [full run](verification/receipts/20261108T065143557916Z-complete-backend-coverage-portfolio.json) |
| Targeted joint-account/reference/volume run |184 tests pass after the aggregate volume fix | [regression](verification/receipts/20261108T064957663404Z-portfolio-and-reference-aggregate-volume.json) |
| Current TypeScript/bundle |Build passes; large-bundle warning remains | [build](verification/receipts/20261108T070643128182Z-trade-level-range-typed-build.json) |
| Current real browser |**Four journeys pass**, single rule and two-rule1h/15m portfolios at1920×1080 and1280×720; exact risk coordinates,toggle preservation,sticky headings,JSON/CSV and actual image geometry | [browser](verification/receipts/20261108T071411342147Z-portfolio-browser-exact-capture-geometry.json) |
| Independent current artifact reread |Four reports,**30 screenshots**,four traces; JSON and real portfolio CSV reconcile; largest summed-trade/account discrepancy2.52e-10 dollars | [reread](verification/receipts/20261108T071615577943Z-exact-geometry-browser-output-reread.json) |
| Historical portfolio numerical reference |Both actual portfolio outputs match independent Decimal execution: **63 trades,12,780 ledger events,20 daily equity points**, plus basic metrics and attribution | [reference](verification/receipts/20261108T065937115216Z-historical-portfolios-independent-reference.json) |
| Current exports linked to that reference |Both latest JSON exports are byte-identical to the independently checked reports, and numerical source hashes remain identical | [explicit reuse proof](verification/receipts/20261108T071615636351Z-exact-geometry-portfolio-reference-link.json) |
| Current targeted visual review |Four chart elements and one portfolio results page actually inspected; VIS-001/002/003 fixed at targeted scope | [review integrity](verification/receipts/20261108T072556964489Z-portfolio-visual-review-integrity.json) |
| Numerical coverage-gate safety |Six exact-boundary/drift/integrity tests pass | [gate tests](verification/receipts/20261108T072556886697Z-numerical-coverage-gate-boundaries.json) |
| Actual numerical coverage gate |**Fails correctly** for current data/signals/metrics/service coverage | [unmet gate](verification/receipts/20261108T072556925891Z-current-numerical-coverage-gate-unmet.json) |
| Current plan inventory |80 requirements,**339 mandatory cases**,120 matrix cases,no lint errors | [inventory](verification/receipts/20261108T072557015528Z-portfolio-plan-current-inventory.json) |
| Actual release gate |**Fails correctly**: no frozen final subject or certified acceptance results | [release gate](verification/receipts/20261108T071615628152Z-expanded-release-gate-unmet.json) |

The portfolio's simulated1128.12-dollar result is execution/integration evidence on already viewed discovery data. It does not establish a trading edge. Current browser reports use numerical subject01345f0c72b6628c930708d8bcc25333d225fab2f08ddceec492cdf0f74a684d and bundle index-HlLncVb9.js. The full numerical run predates later UI/test/catalog amendments; current numerical-source agreement is checked explicitly. No mixture of these implementation receipts is represented as a frozen final release.

## Coverage still required

Thresholds remain95% statements and90% branches for the declared numerical modules; critical financial/holdout/provider paths and full use-case acceptance remain additional gates.

| Module | Statements | Branches | Threshold outcome |
|---|---:|---:|---|
| config |98.96%|91.67%|pass |
| data |98.03%|80.30%|unmet |
| signals |92.98%|82.88%|unmet |
| engine |98.47%|90.98%|pass |
| metrics |100.00%|83.33%|unmet |
| service |94.67%|73.47%|unmet |

[Raw uncovered lines/branches](verification/runs/coverage-gaps-01345f0c.json) and the hashed coverage JSON identify the next numerical cases. Coverage does not establish statistical validity; supplied-signal reference parity does not independently certify every detector option. Subprocess CLI/startup coverage is not silently inferred from the instrumented parent report.

## Retained failures and input limits

The first portfolio liquidity suite had24 failures and5 passes: both production and reference could reuse a29-share allowance across rules. The independent hand quantity exposed the common omitted assumption. Expected quantities were preserved while production and reference were corrected separately. Other retained failures include the portfolio test's wrapped-label locator timeout, a typed-chart build error and the reader's incorrect350-PNG-pixel assumption. Exact measured capture geometry fixed the reader; financial tolerances were unchanged. See [defects](verification/defects.json), [decisions](decisions.md) and [evidence index](verification/evidence-index.md).

The six-symbol January2022 original still has one missing DIA minute and remains ineligible. Five-symbol child90f347229b2fb03ec112ee71 was separately audited; no price was invented. These dates are already viewed discovery data. Borrow availability/rates and corporate-action completeness retain their explicit assumptions/gaps.

Cold startup/job timings vary. Earlier37.69s startup and96.19s historical-job observations remain retained. Current functional timings do not certify an operating envelope. Acquisition/buffering, duplicate per-rule chart serialization, memory budgets and large-search execution require measured optimization/partitioning. No100/1,000/10,000/100,000-scale acceptance is claimed.

## Required next work

1. Finish independently authored confirmation/filter/day-boundary and supported-value/combination/pairwise/higher-order cases. Add statistical-reference/nonpositive-equity and missing data/API/accounting boundaries; meet coverage and mutation gates without weakening them.
2. Implement versioned news-calendar and remaining short-financing scenarios, behavior experiments, matched random entries/levels, cash/buy-and-hold, paired ablations and search-aware/trial-registry reporting.
3. Complete portfolio-level frozen final studies, study amendments/abandonment and remaining real final/cancel/restart/failure/report journeys.
4. Complete offline HTML presentation, broader mobile/keyboard/accessibility/privacy/security/offline validation and fresh-install/reproduction.
5. Implement measured resource limits, cache/partition/optimize only with reference agreement; execute required staged real searches and actual bounded100,000-configuration stress handling.
6. Freeze the complete final source/specification/dependency/data subject. Execute every mandatory acceptance case and deliver the linked plan-to-code-to-test-to-receipt conformance report.

The original330 mandatory cases remain; nine explicit portfolio/inspection cases were added. **All339 final product acceptance cases remain uncertified.** The map has partial implementation links for49/80 requirements. Implementation receipts intentionally carry no acceptance passes. Goal is active and unfinished.
