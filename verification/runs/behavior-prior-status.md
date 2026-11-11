# Implementation status

Current work in progress (2026-11-08 UTC): RULEBOOK0.9 adds the17 behavior diagnostics and shifted-feature lifetimes. The current localhost core is71fa1c65e7ded3222676abf759451d2b7dccdeec470ba020f7c4b45fe946858c.36 focused behavior/recovery tests and a typed UI build pass; full current regression, independent default20/five-chart SPY audit and browser evidence are still running. The checkpoint below is historical evidence from RULEBOOK0.8, not current final certification. Catalog version5 retains all351 previous cases and adds27 behavior cases:81 requirements/378 mandatory cases,0 final-certified.

Goal remains active: a fully functional, fully verified localhost strategy-testing application under PLAN.md and VERIFICATION_PLAN.md. **NOT VERIFIED / NOT READY for final release.** Current evidence is implementation and bounded verification, not frozen final acceptance.

## Current application

- Locked Python3.13/React/TypeScript/Vite, private loopback API, separate spawned worker, durable SQLite jobs, immutable strategy/results and seven working sections.
- Read-only free Alpaca SIP acquisition/import, session/data/action audits and immutable hashes; six causal signal charts and ten distinct price-action families. RULEBOOK **0.8** defines the equity adaptations.120 baseline strategy/timeframe/direction cases run; full supported-option/pairwise/higher-order/mutation acceptance remains open.
- Minute execution and shared-capital long/short portfolios: fees, borrowing, splits, distributions, deterministic order priority, reference-minute aggregate entry volume, daily marked equity and per-rule attribution/chart clocks. One to64 rules is an input bound, not a measured operating envelope.
- Independent study freeze/guard/consumed-final/saved-chart workflows. Portfolio-level frozen final studies, amendment/abandonment and complete final/recovery cases remain unfinished.
- Cash/passive-equity books use explicit capital/date/cost/allocation/action/entry-volume assumptions. Actual books, allocations, ledgers and JSON/CSV persist. Passive drift/risk differences remain explicit; incompatible inputs cannot acquire a strategy delta.
- **Conditional matched random-entry studies:** select a rule and2–200 accounts, default20. Match symbol, direction, trigger duration, New York30-minute close-time and fixed prior-ATR/close bands. Freeze one maximum-cardinality source subset across replicas, use distinct moments per account and independent hash-ranked streams. Save full-real context separately from matched-real comparisons; transfer ATR-relative geometry to known candidate features. This retrospective comparison is not a standalone live strategy.
- Each complete control account is checkpointed with job/plan/core identity and a persisted hash. Cancel/resume reuses verified accounts; corrupted parts reject and untrusted orphans are recomputed. Sealed dates reject before raw reads. The UI inspects actual surrogate trades/charts and exports aggregate/account JSON plus selected-account CSV. Ambiguous aggregate CSV returns400 with guidance. Late account responses cannot populate a newly selected study.
- Finite/nonpositive-equity metrics, independently checked DSR examples and seeded bounded daily block resampling. Full trial-registry/search-aware reporting and shifted-level/behavior/ablation experiments remain unfinished.
- Real charts, ledgers and saved JSON/CSV. Sticky trade headers, actual exit/stop/target levels and fit-all/price-only views; saved-version warnings and health polling. Full mobile/accessibility/privacy/offline/restart/schema recovery and HTML presenter remain open.

## Latest executed evidence

| Check | Actual result | Receipt |
|---|---|---|
| Full backend and branch instrumentation | **642 pass**, including120 family/timeframe/direction cases and41 control-specific cases;243.16s. All authored fixture inputs are hashed | [full run](verification/receipts/20261108T083402678603Z-full-backend-matched-controls-coverage.json) |
| Current typed UI build |Pass; bundle index-D-B3rjDP.js; large-bundle warning remains | [build](verification/receipts/20261108T084151044238Z-controls-selection-generation-typed-build.json) |
| Actual browser/API/worker/storage |**Eight journeys pass** at1920×1080 and1280×720: single rule, portfolio, passive books and random controls. Includes real delayed-response study switching, reload, charts and exports | [browser](verification/receipts/20261108T084153985533Z-all-eight-current-control-browser-journeys.json) |
| Independent current artifact reread |Eight reports/traces,**40 screenshots**, actual CSV/JSON and exact chart geometry; selected surrogate books exactly match the independently audited default-run books | [reread](verification/receipts/20261108T084832951290Z-current-eight-flow-artifacts-final-reread.json) |
| Actual default20 historical controls |**22 accounts** (full real,matched real,20 random);13/13 source events matched. Own Decimal hourly candles/prior ATR, volatility bands, maximal matching/hash ranks/geometry and every supplied-signal account agree | [default20 reference](verification/receipts/20261108T083424444585Z-default20-control-historical-independent-audit.json) |
| Independent default20 comparison statistics |Mean/real/exceedance/paired interval recomputed from independent equity; largest difference8.46e-11 dollars | [statistics](verification/receipts/20261108T083737061811Z-default20-comparison-statistics-independent-reference.json) |
| Current two-control UI statistics and passive reuse |Both UI study summaries independently recalculate; maximum difference2.08e-10. Passive financial books equal prior independently checked books with unchanged owning numerical modules | [financial/source proof](verification/receipts/20261108T084927356119Z-current-control-statistics-and-component-reuse-proof.json) |
| Current independent single execution |13 signals,10 trades,411 ledger events,20 daily points; basic metrics agree | [single reference](verification/receipts/20261108T084549252687Z-controls-current-real-single-reference.json) |
| Current independent portfolio execution |Both reports match63 trades,12,780 ledger events,20 daily points and attribution/entry budgets | [portfolio reference](verification/receipts/20261108T084557961355Z-controls-current-portfolio-reference.json) |
| Targeted current visual inspection |Both unmodified current control panels actually viewed, including separate source/trade denominators, negative relative comparison and selected trade chart | [visual record](verification/runs/matched-controls-current-visual-review.json) |
| Eight-module numerical coverage |Five modules pass; data/signals/service remain unmet. Overall gate correctly fails | [coverage](verification/receipts/20261108T084204179937Z-eight-module-control-numerical-coverage.json) |
| Plan/catalog inventory |80 requirements,**351 mandatory acceptance cases**,120 matrix cases,no lint errors; all345 prior cases retained | [inventory](verification/receipts/20261108T083458777216Z-matched-controls-351-case-plan-inventory.json) |
| Actual final release gate |**Not ready**; no frozen final subject;0 certified/351 uncertified acceptance cases | [release audit](verification/receipts/20261108T084258173392Z-matched-controls-351-release-unmet.json) |

Current numerical subject is05e6f63e9699dc2b372ab39f1224b5ec2f48dcf6684f27313974bab549839f8b. Later changes to the controls UI/test and verification helpers are disclosed separately from the full backend subject; current numerical/backend-test agreement is explicit. README usage wording was subsequently clarified. Original receipt subjects are retained, never rewritten into a final certificate.

The default20 study took110.43s including independent auditing in that run; this is a bounded functional observation, not a general operating guarantee.9/20 random accounts were at least as profitable as the matched real account. The descriptive exceedance is0.4762 and the paired dollar interval includes zero. This examined January2022 month does not establish a trading edge. All dates were already viewed discovery data. The historical independent feature audit is hourly/action-free and uses supplied setup signals; it does not independently certify every detector, market-data completeness or corporate-action path. Separate hand/reference cases cover those action mechanics.

## Remaining numerical thresholds

Required95% statements/90% branches remain unchanged, with additional critical accounting/order/provider/holdout, mutation and use-case acceptance gates.

| Module | Statements | Branches | Outcome |
|---|---:|---:|---|
| config |98.96%|91.67%|pass |
| data |98.03%|80.30%|unmet |
| signals |92.98%|82.88%|unmet |
| engine |98.47%|90.98%|pass |
| metrics |100%|100%|pass |
| service |95.06%|74.51%|unmet |
| benchmarks |100%|97.50%|pass |
| controls |100%|94.05%|pass |

[Raw remaining branches](verification/runs/coverage-gaps-05e6f63e.json) are retained. Some defensive matching/zero-quantity branches are unreachable under the tested invariants; they are not forced into fake user scenarios. Coverage does not replace independent numerical/causality checks or establish statistical validity.

## Retained failures and data limits

The initial control feature was absent (18 failures/3 errors). Later tests exposed a wrong aggregate numerical-contract field, ambiguous CSV500 and zero-weight matching. Expected rejection behavior was preserved through intermediate409 responses until explicit400 handling passed. A39-test command collected no coverage because --cov named a filename; it is not coverage evidence. The corrected coverage first measured89.29% branches and remained unmet until meaningful incomplete/cancellation cases reached94.05%.

The first browser run passed six journeys and failed both control labels. A new delayed-response test then reproduced stale-account display at both profiles before the generation guard fixed it. Failed screenshots/traces/commands remain alongside passing reruns. Earlier statistical overflow, portfolio liquidity, locator/build/image-geometry and source-identity histories remain in [defects](verification/defects.json), [decisions](decisions.md) and [evidence index](verification/evidence-index.md).

The original six-symbol January dataset still lacks one DIA minute and remains ineligible. Five-symbol child90f347229b2fb03ec112ee71 is separately audited; no price was invented. Historical borrowing/actions/universe assumptions remain explicit. Functional timings do not certify search scale, memory or response budgets; old latency variability and duplicate chart serialization remain recorded.

## Required next work

1. Implement shifted random levels and the full behavior inventory, paired ablations, parameter/era/instrument stability, complete trial registry and search-aware reporting/sensitivity. Preserve the source inventory; matched entries do not replace those tests.
2. Finish versioned news calendars, changing short-financing/recall scenarios, every supported confirmation/filter/day-boundary/pairwise/higher-order case, critical mutations and the remaining data/signals/service numerical gates.
3. Finish portfolio-level frozen final studies, amendment/abandonment and all final/cancel/restart/corruption/error workflows.
4. Finish offline HTML presentation, mobile/keyboard/accessibility/privacy/security/offline acceptance and clean locked install/reproduction.
5. Implement measured resource envelopes/cache/partitioning with reference agreement; execute real100/1,000/10,000 searches and actual bounded100,000-configuration stress handling. No scale acceptance is currently claimed.
6. Freeze the complete final subject, execute every mandatory acceptance case and deliver plan-to-code-to-test-to-receipt conformance with no unmet mandatory behavior.

All original330 cases remain, plus nine portfolio, six statistical/passive and six matched-control cases. **All351 final acceptance cases remain uncertified.** The map is partial. The full objective remains active and unfinished.
