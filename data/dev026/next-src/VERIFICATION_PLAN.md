# Verification contract and evidence plan

D046 preparation supplement: verify every completed setup-chart as-of boundary, Wilder warm-up and recurrence, raw split units, future suffix invariance, exact original/source/set money sums, canonical encoding/bounds, strict499/500/tie/complete-cohort grading and cancel before/during each preparation phase and before return. Use an actual saved two-trade numerical-boundary account to expose tiny-profit loss beside a large trade; keep its original computation/trace/ledger authority and independently computed Fraction baseline. Preserve every prior83/422/120 case. These component checks do not certify durable/API/UI completion.

D045 additionally requires the [UI and original-link recovery supplement](verification/fixtures/spread-ui-integration-contract.json), including source-default versus small-run scope, every declared desktop/mobile flow, stale response ownership, original child preservation after dual parent-record loss, indexed bounded metadata, public-model schema parity and owned test-process retirement. Preserve authored failures and actual receipts; rerun on the integrated source. This supplements the unchanged83 requirements/422 mandatory cases/120 baseline combinations and cannot substitute for final conformance.

Version 3, durable spread continuation details updated 2026-11-09 UTC. This is a binding part of [PLAN.md](PLAN.md). Implementation and bounded component/browser verification are in progress; the product has not passed final acceptance. [STATUS.md](STATUS.md) separates executed implementation checks from the still-uncertified422 mandatory acceptance cases. Source-video captures and provider probes retain their investigation/preflight scope.

D045 must satisfy every check in the authored [worker contract](verification/fixtures/spread-worker-contract.json) and [account continuation contract](verification/fixtures/spread-account-handoff-contract.json): real process death at durable boundaries; original-byte/hash-chain/registry reconciliation; corrupted, redirected and oversized inputs; no premature signal/P&L reads; one atomic child under concurrency; all original selected configurations/assumptions frozen before accounts; primary-only/protected-date checks before new/reused work; complete account/CSV/lineage and saved offline viewing; UI/cancel/resume/error/keyboard/mobile journeys; resource and critical mutation evidence. Every new numerical/persistence module requires at least95% statements and90% branches, without rounding. Combining actual coverage requires identical backend sources and independent raw-database-to-recorded-JSON reconciliation for each successful run; inferred hits are prohibited. Small fixtures, metadata-only stress, component gates and overlapping test counts never replace final422-case conformance or actual source-scale execution.

## Meaning of strict implementation and exhaustive verification

Every committed requirement must have a stable ID, specified behavior, named acceptance cases, implementation references, an executed result and inspectable evidence. The canonical inventory is [verification/catalog.json](verification/catalog.json); [verification/coverage.csv](verification/coverage.csv) is its initial human-readable coverage view. Its initial `not_run` entries are not test results.

“Exhaustive” means no declared use case, supported option, identified boundary, error path or release gate is omitted from this inventory. It does not mean that finite testing proves correctness on every possible price path, proves future profitability, or explores the source's roughly 20-trillion parameter combinations. Unsupported inputs and unsupported combinations must be rejected explicitly. Use equivalence classes, boundary analysis, generated property checks, pairwise combinations and targeted higher-order combinations to cover the supported space systematically; disclose the exact tested domain.

The implementation must conform to the plan **and** the versioned rulebook, data/accounting contract and acceptance criteria. Clarifying missing source rules is required before testing; document the choice in `decisions.md`. A bug fix that restores the contract needs no new user approval. Material scope reductions or weaker acceptance criteria cannot be used to turn a failure into a pass; disclose them and obtain the user's explicit agreement before removing a required behavior. Do not add approval pauses for routine implementation choices already authorized.

## Release decisions

The final statement “implemented and verified according to plan” requires all of the following:

1. Every mandatory requirement has implementation file/symbol references and every mandatory case has a current passing receipt. A skipped, expected-failure, blocked, inconclusive, missing or stale case is not a pass.
2. The ten strategy families, six signal timeframes and both directions have their complete baseline cross-product executed: **120 strategy cases**, not one strategy copied into ten menu labels. Each needs actual signals/trades on a constructed fixture with independently specified expected behavior. An empty-trade run cannot satisfy a positive-path case.
3. Positive, negative, boundary and failure cases in the catalog pass. Every supported parameter value is exercised; all invalid-combination rules have an accepted and rejected boundary case. Special interaction suites below also pass.
4. Numerical outputs reconcile to independent expected values and reference calculations within tolerances frozen before the run. No unexplained discrepancy remains.
5. Deterministic offline acceptance passes on the release build. Live-provider integration evidence is separate and dated; stale cached data is never presented as a fresh provider success.
6. All product flows work through the actual browser/API/worker/storage stack. Tests do not replace the numerical engine with canned results. Mocked provider tests are labeled and complemented by bounded real-provider checks.
7. Code, dependency locks, rulebook, catalog, input manifests and output artifacts match the hashes in the receipts. Final verification runs after the last relevant code change. Final status is written to a separate release report so it does not silently alter the frozen specification.
8. There are no unresolved defects that violate mandatory behavior, no unexplained skipped tests and no silent deviations. Improvements outside committed scope may be deferred visibly. Futures/forex/crypto, runtime AI, extended-hours trading and Yahoo fallback remain later/optional unless separately added to the committed release scope; they cannot be advertised as verified features.

Financial loss is a valid research result. “No candidate passed,” insufficient observations and inconclusive evidence are valid product outcomes when correctly computed and labeled. Software acceptance does not require finding a profitable strategy.

If a dependency blocks a mandatory integration case, publish the blocker and remaining work and call the release incomplete. Do not claim full completion with an untested mandatory capability.

## Required records during implementation

Apply the following evidence cycle to each implemented requirement and meaningful correction. Preserve records at the time of execution; do not reconstruct successes at final delivery.

| Step | Required action and evidence |
|---|---|
| Before implementation | Identify requirement/case IDs, precise expected behavior, independent fixture/oracle, tolerances and affected source-video adaptation. Add missing use cases before claiming the behavior is supported. |
| First execution | Run the applicable checks against the actual implementation. Save command, start/end times, source/input hashes, real exit code, expected/observed assertions and raw output. When exposing a defect, retain that first failure before editing the fix. |
| Correction | Link the defect, code/rulebook decision and unchanged expected contract. Run affected regression and integration checks; broader reruns are required when shared behavior changes. Never weaken an expectation solely to obtain a pass. |
| Checkpoint | Update implementation mappings and the evidence index. Report what passed, what failed, which acceptance cases remain open and the precise build/data limits. Screenshots supplement numerical/ledger evidence. |
| Final freeze and audit | Freeze the complete source/specification/lock/data subject, execute every mandatory case, independently inspect the inventory and raw evidence, and run integrity/coverage gates. Any relevant change requires a new subject and affected current evidence. |

The final conformance table must contain one row per mandatory case: requirement ID, case ID, planned behavior, code symbol, test identifier, expected/observed result, status, subject hash, receipt link and artifact links. Also provide grouped counts by requirement, strategy/timeframe/direction and product flow, so an untested area cannot disappear inside a large test total. Current planning CSV entries remain separate from executed results.

Maintain these records as work proceeds, not reconstructed from memory at handoff:

| Record | Required content |
|---|---|
| `decisions.md` | Decision ID/date, affected requirement/cases, source timestamp or screenshot, ambiguity, chosen behavior, rationale, validation implication; explicit distinction between source rule and our adaptation |
| `verification/implementation-map.json` | Requirement ID → production files/symbols, test IDs/files, rulebook section, dependency/data contracts; missing mappings block release |
| `verification/defects.json` | Defect ID, reproducer, expected/observed result, impact, affected cases, fix reference, regression receipt; never overwrite the original failure |
| `verification/runs/<run-id>/` | Captured commands, exit statuses, stdout/stderr, environment, test reports, screenshots/traces, fixture and dataset manifests, comparison/reconciliation tables, resource measurements |
| `verification/release-subject.json` | Frozen specification, complete production/test/fixture source inventory, rulebook, dependency locks and input-manifest hashes for the final baseline |
| `verification/receipts/<receipt-id>.json` | Machine-readable evidence receipt conforming to [receipt.schema.json](verification/receipt.schema.json) |
| `verification/release-report.md` | Tested build, requirement/case counts by actual status, links to receipts, defects, approved differences, bounded claims, reproduction instructions and final verdict |

IDs and timestamps must be genuine. A test script existing, a screenshot existing, a completed subprocess, a copied source-video image or an assistant's narrative is not by itself a passing receipt for a product use case.

## Receipt contract

Each verification receipt records:

- A unique receipt ID, evidence kind, start/end UTC timestamps and local timezone; test runner and OS/runtime/browser versions.
- The exact tested subject: source file manifest/hash, frozen plan and catalog hashes, rulebook hash, dependency lock hashes and input-data manifest hashes. Use relative paths in shareable records. Never hash or archive `.env` as evidence.
- A redacted executable command/argument list, working directory, seed, exit code and test configuration. Capture the actual exit code directly; do not allow a pipe or truncated output to hide a failure.
- Each case ID, expected result, observed result, explicit assertions, status and associated artifact references. Parameterized cases identify their family, timeframe, direction and selected options.
- Artifact paths, SHA-256, size and purpose. Evidence must exist, be readable and match its recorded hash. Screenshots need route/state, viewport, browser build and actual run context; financial figures need machine-readable ledger and reconciliation evidence too.
- Live versus synthetic versus mocked/cached input provenance. Synthetic prices must be labeled in the UI and reports. Provider checks must not be mislabeled as a full historical quality audit.

Allowed case outcomes are `pass`, `fail`, `blocked`, `not_run`, `inconclusive`, `stale`; release passes only current `pass` outcomes for every mandatory case. `not_applicable` is permitted only for an explicitly optional capability outside committed scope, with a recorded reason and scope reference; it cannot excuse a required family, timeframe, direction or core flow. The initial catalog contains mandatory release cases only.

Planning and implementation receipts may document work but cannot satisfy verification cases. Never create passing placeholders or set a result to pass from an intention. Automated validators can check structure and integrity, not establish that an assertion or screenshot is honest; actual tests, independent expected values and human-style inspection remain necessary.

Capture failures before fixing them. Reruns create new receipts linked to the original defect; they do not erase failed logs. A source/specification/input change invalidates affected receipts. Final acceptance requires a coherent current baseline; cross-run evidence cannot combine incompatible builds. Preserve old receipts for audit history. A later current passing receipt can supersede an earlier current non-pass only for the same case, with an explicit receipt-ID link and a later execution time. Stale receipts are reported and cannot contribute passing coverage.

## Final conformance audit procedure

Apply this procedure after the required functionality is implemented. A planning lint, aggregate test count or implementation receipt cannot substitute for it. The current baseline is catalog v8: **83 requirements and 422 mandatory cases**, including 120 strategy matrix cases; add cases whenever the supported contract expands. Historical inventory counts in expansion notes are not competing release targets.

1. **Audit specification completeness.** Review every implementation-plan paragraph, source-video difference, rulebook clause, supported option and user workflow against the catalog. Map each to requirement/case IDs or an explicit already-agreed later-scope decision. Inventory positive, negative, empty, boundary, failure and recovery states. Publish any gap before execution; do not treat an omitted case as implicitly passed.
2. **Audit test adequacy.** For every case, identify the production symbol, executable test/assertion, fixture, independently authored expected value, tolerance and required artifacts. Inspect whether the assertion actually establishes the promised behavior. A shared production/reference calculation, empty positive-path result, mocked engine or screenshot without assertions cannot establish numerical or end-to-end correctness. Record the exact supported-option and interaction domain exercised.
3. **Freeze the subject.** Create the complete release source/specification/fixture/lock/input inventory, environment versions and seeds. Record the source/build identifiers and all previously viewed data windows. Exclude credentials and private raw captures. Freeze resource budgets and numerical tolerances before measuring results.
4. **Execute the complete release suite.** Run deterministic, independent-reference, integration, actual browser, fault/security/privacy, offline, scale and clean-reproduction cases as specified. Record actual command status and per-case expected/observed assertions. Retain failures immediately; a dependent case whose prerequisites fail is blocked, never passed. Date live-provider evidence and identify its actual request/sample scope.
5. **Reconcile evidence and defects.** Produce a row for every mandatory case with requirement, behavior, production symbol, test ID, fixture/oracle, expected/observed result, outcome, subject hash, receipt and artifact links. Group totals by work package and by strategy/timeframe/direction; totals must reconcile exactly to the catalog. Separately list all defects, superseding regressions, deviations, stale receipts and unexecuted work. Check original and derived artifact hashes without reading or hashing `.env`.
6. **Independently inspect the final product.** Reread financial exports with a separate calculation path and compare with UI/report values and source denominators. Replay selected sanitized browser traces, inspect all required visual states and verify offline exports with network disabled. Audit that saved evidence establishes each case rather than merely existing. This is a separate review pass; no external reviewer or extra agent is implied.
7. **Issue the release decision.** Execute the inventory, numerical coverage and release-evidence gates on the frozen subject. Report their actual exit codes. An intentionally rejecting release gate is evidence that the gate rejected incomplete evidence, not a product pass. Write `verification/release-report.md` only from executed results, with all required links and a PASS/INCOMPLETE verdict. PASS requires every mandatory case current and passing, all prescribed coverage/mutation gates met, zero unresolved mandatory defects and no unexplained discrepancy.

After a relevant fix, record its impact analysis, create a new subject where necessary and rerun affected cases plus cross-cutting regression. The final evidence must describe one coherent release; earlier passing receipts cannot silently certify changed behavior. Do not lower thresholds, delete required cases or rename consumed data to obtain acceptance.

The reviewable delivery includes the conformance table, machine-readable receipts/test reports, sanitized browser artifacts, independent numerical comparisons, benchmarks, defect history, source-video differences and reproduction instructions. Private raw diagnostics remain local with explicit lineage to safe derived review artifacts. Report implementation progress and final-certified coverage separately throughout the work; neither a large test count nor favorable backtest returns establish completion.

## Test layers and independent oracles

| Layer | What it establishes | Required evidence |
|---|---|---|
| Contract/rulebook | Algorithms and assumptions have precise definitions | Versioned schema, worked examples, source/adaptation references and allowed-value/constraint inventory |
| Deterministic unit/property | Numerical mechanics and causal decisions | Hand-calculated fixtures, assertion results, property seeds/counterexamples and coverage report |
| Independent differential | Optimized engine implements the contract | Simple reference implementation that does not share production detector/order/accounting logic; event-by-event and daily-equity diffs |
| API/storage/provider integration | Components exchange and persist correct data | Actual request/response assertions, DB transitions, file hashes, import/export parity, retry and corruption tests |
| Browser end-to-end | A user can complete real workflows | Trace/screenshots, actions/assertions, resulting experiment/trade/report IDs and their ledger receipts |
| Recovery/security/load | Failure and operating boundaries hold | Fault-injection logs, bounded resource measurements, adversarial requests, recovery diffs and no-secret findings |
| Release reproduction | Another clean installation can reproduce the supported workflow | Locked install/build logs, deterministic rerun comparison, dated real-provider check and release manifest |

Expected results must be authored independently from production outputs. Do not “bless” an unexplained output as the golden fixture. For money, use exact decimal/cents calculations in the reference ledger and the documented rounding event. For prices/order times, assert tick/rounding and availability explicitly. Freeze per-metric floating tolerances, return-series alignment and rounding rules before results; do not widen tolerances to accommodate a bug.

Coverage targets: 100% of mandatory acceptance cases and critical accounting/order/holdout branches; at least 95% line and 90% branch coverage of numerical production modules, with every uncovered branch explained. Exercise every registered strategy and order event. UI acceptance is based on tested flows and states, not a line-coverage proxy. Code coverage alone never overrides a failed case.

Mutation checks must deliberately introduce future pivot availability, incorrect stop priority, omitted fees/borrow, a wrong dividend sign, truncated pagination, holdout bypass and an unpersisted completed-job status. Each mutation must be detected by its relevant tests. A deliberately future-peeking numerical control belongs only in isolated test fixtures; it must never be a runnable user strategy.

## Use-case inventory and combination coverage

The generated catalog is normative for test execution. Every check below has an executable case ID in it. New supported behavior must add cases before being marked complete.

### Data and installation

Test clean locked installation, localhost launch/shutdown, occupied ports, process cleanup, supported Python/Node versions and cached offline restart. Check credentials absent/invalid/revoked without exposing them. Check SIP success, provider rejection, timeout, 429 retry/backoff, interrupted pagination and final-cursor exhaustion for **every** requested symbol. No silent switch to IEX.

Test CSV and Parquet round-trip, schema aliases, empty/malformed/oversized input, duplicate/conflicting timestamps, unordered rows, nonfinite or inconsistent OHLCV, timezone ambiguity and path traversal. Audit missing bars against the actual expected session calendar; do not confuse a holiday/early close with a feed fault, or invent missing prices. Exercise minute/hour/day/4h boundaries, daylight-saving transitions and partial final bars.

Corporate-action fixtures must cover a forward and reverse split with an open long/short, cash distributions and short distribution liabilities, raw/adjusted price alignment and symbol mapping. Missing action records and ambiguous adjustments must block affected conclusions or produce an explicit unsupported-data failure, rather than double-adjusting or silently ignoring the event. Verify immutable dataset hashes and change/corruption detection. Real-provider checks corroborate fixtures but cannot replace them.

### Strategy families

Every family uses positive/negative, mirrored-direction and boundary fixtures plus every applicable baseline timeframe/direction case:

| Family | Specific required discriminating cases |
|---|---|
| Level bounce | Touch within tolerance versus outside; touch count; confirmed level only; invalidated/expired level; repeated touches do not create duplicate orders |
| Breakout | First qualifying completed close versus wick/equality; threshold buffer; one break per level; failed breakout and retest variant |
| Flip zone | Prior confirmed break, valid first retest, wrong-side approach, retest expiry, reclaimed/invalidated zone |
| Trend pullback | Established causal trend; first versus later pullback; depth bounds; broken trend and confirmation timing |
| Trend line | Declared confirmed anchors, slope/side, projected touch, line break/expiry; future pivots cannot move historical decisions |
| Break of structure | Break with established trend; exact equality/wick rejection; confirmation lag; level reuse and invalidated structure |
| Change of character | First opposite confirmed break; uninitialized/mixed trend; sweep-required versus no-sweep; swing-based stop and 1R target |
| Sweep and reclaim | Wick penetration and reclaim window; close beyond without reclaim; depth equality/bounds; no future reclaim information |
| Supply/demand zone | Qualifying impulse length/ATR, base geometry, first/later return, mitigation/expiry, overlapping-zone priority |
| Fair-value gap | Three-candle gap known only after third close; boundary equality; first mitigation versus full fill; invalidation/expiry |

For all: long-only, short-only and both modes; zero signals, one signal, simultaneous signals, insufficient warm-up, constant prices, equal highs/lows, irregular missing minutes and unusually large gaps. Check confirmation modes, stop references/buffers, target/exit choices, all enabled filters and every supported dial value. Every valid-combination predicate needs a boundary test and a rejected-combination API/UI test. Undefined source behavior must be resolved in the rulebook before expected values are set.

Baseline coverage is the full 10 × 6 × 2 cross-product, with 1m/5m/15m/1h/4h/daily setups and long/short directions. Test same/lower trigger-chart mappings and the daily/hourly special case separately. Use pairwise coverage over the remaining supported dials; additionally execute these higher-order interactions: pivot lag × higher chart × confirmation; limit entry × expiry × gap; stop/target × ambiguous minute × short; daily signal × next-session fill × dividend/split; session filter × early close × timeout; news sizing × risk sizing × exposure; borrow availability × distribution × overnight gap; overlapping strategies × shared capital × cancellation/restart. Record the generated combinations and uncovered constraints.

### Execution, accounting and metrics

Hand-calculated paths cover next-eligible-minute entry, daily next-session entry, alternate same-close assumption labels, limit trade-through, exact touch, target/stop same minute, gap past stop, close-based stop, time/structure exits and pending-order cancellation. Check invalid stop distance, zero/negative price, no eligible fill and insufficient volume/availability according to the declared fill policy. No hidden future or favorable gap fill is allowed.

Reconcile each event, trade, day and portfolio: starting cash + external/corporate cash flows + marked position value − liabilities = equity under the documented short-collateral model. Charge each fee once; accrue borrowing across elapsed calendar days including weekends; apply long/short distributions with correct entitlement timing; update split quantities/prices without creating value. Risk sizing, whole-share rounding, cash, symbol and aggregate limits must hold at the time of each accepted order. Reject excess simultaneous orders deterministically; do not sum independent backtests as a feasible portfolio.

Metric fixtures cover open losses, flat/no-trade series, all wins/losses, zero standard deviation, undefined profit factor/Sharpe, missing dates, rounding and benchmarks with distributions and consistent exposure/capital. Check absolute loss versus relative improvement separately, denominator labels, concentration and paired-ablation matching. For a fixed trade list, increased fees cannot increase net P&L; distinguish this identity from a rerun whose sizing/trade selection may change.

### Research integrity

Exercise experiment freeze, invalid date ordering, insufficient warm-up, discovery/validation separation, candidate hashing and dataset/rulebook tampering. Enforce holdout access guards through every data-loading route, API, preview, chart, cache and report path, not only the optimizer. Record unlock and consumed-window status, failed/aborted final tests and rerun behavior. A new experiment ID or copied dataset cannot silently relabel already-consumed observations unseen. This is a workflow safeguard on a user-controlled PC, not a claim of preventing the owner from reading files.

Check sampling uniqueness/constraint balance, stable per-configuration seeds under sorting/parallelism/restart, trial counts including failed/rejected cases with distinct denominators, threshold boundaries, zero passing candidates, era/instrument checks, matched controls, session/block bootstrap, effective-trial-count sensitivity and a reference calculation for the search-aware statistic. Validate output schemas and undefined-statistic labels. Numerical controls may produce different profit signs on a new dataset; never require the host's reported profit as a correctness oracle.

### Product flows, recovery, privacy and reports

Exercise the seven main screens with both positive and negative states. A complete user journey must create/import a dataset, inspect quality, edit/save a strategy, run it, inspect an actual trade and daily equity, compare runs, freeze candidates, perform final evaluation and export/reopen reports. Also cover no data, no trades, no candidates, failed provider, failed worker, stale data, canceled run and invalid parameter combinations. A hidden required control or an inert button fails acceptance.

Test queue persistence, browser closure, API restart, worker termination mid-chunk, process restart after atomic writes, duplicate-worker claims, cancel/resume, idempotent retries and interrupted exports. Recovered results must match an uninterrupted run; incomplete results cannot appear completed. Keep progress responsive and retain logs even when no candidate wins.

Verify keyboard-only operation, labels/focus/error announcements, readable glossary/help, contrast and reduced motion; no horizontal loss of essential controls at 390×844, 1280×720 and 1920×1080. Compare actual screenshots to source-inspired visual requirements, documenting deliberate differences in layout, typography, palette, chart labeling and presentation behavior. Never use source screenshots as a substitute for working UI.

Check loopback binding and reject untrusted Host/Origin, mutation requests without the intended same-origin/session protection, path traversal, untrusted uploads, HTML/script injection and unsafe CSV formulas. Verify no trading endpoint is invoked. Check that keys, auth headers, `.env` content and sensitive paths are absent from bundles, console/logs, test artifacts and exports. Receipts store provider response metadata and market bars, not credentials. Test cached offline operation with network access disabled; provider downloads should explain the offline failure.

Every displayed statistic must link to a stored result and a row/field or calculation record; an independent reader recalculates it. CSV/JSON import/export and saved report values must agree, including rounding, units, instrument, subset and dates. Open exported HTML with network disabled, verify that it contains no raw sealed data/secrets and inspect presentation keyboard navigation/replay/menu/camera-area toggle/pointer/highlight if included in the committed presenter. New screenshots need actual browser receipts.

### Scale and reproducibility

Run 100, 1,000 and 10,000 configurations on a fixed declared real-data discovery sample and report elapsed time, throughput, peak memory, storage, sample dimensions and worker count. Exercise 100,000 actual configurations end-to-end on a bounded deterministic stress fixture to verify queue/chunk/storage handling; estimates are not an executed 100,000-case result. These workloads do not claim the host's 327-million-trade research was reproduced. Any advertised operating envelope must have a measured test; unmeasured full-history runtimes remain estimates.

Freeze budgets before benchmarks: UI/API status response p95 ≤2 seconds under the declared local load; cancellation acknowledged within 2 seconds and worker stops at a checkpoint within 10 seconds; no out-of-memory failure, corrupt output or completed-job data loss. Default worker memory budget must be set from available RAM at launch and recorded, leaving system headroom. If the machine cannot meet the declared envelope, fix the implementation or document the unmet mandatory gate; do not conceal it behind progress animation. Downsampling is allowed for chart rendering, never to silently change backtest execution data.

Rerun the same manifest from clean caches and after restart with the same seed: discrete events/configuration choices must match exactly; numerical differences obey frozen tolerances. Record environment-dependent nondeterminism explicitly. Rebuild from dependency locks in a clean environment and rerun the release suite.

## Verification order and checkpoint receipts

| Checkpoint | Minimum evidence required to claim this checkpoint |
|---|---|
| V0 Specification freeze | Every plan paragraph assigned to a requirement/scope decision; rulebook/schema completed; cases/oracles/tolerances/fixtures frozen; catalog lints; no ambiguous mandatory behavior |
| V1 Data | Clean install/start receipt; full declared-range ingestion audit; deterministic import/calendar/action fixtures; bounded live-provider receipt; dataset hash manifest |
| V2 First vertical slice | CHoCH numerical fixture receipts, causal/invariant tests, reference-engine diffs, ledger reconciliation and browser trade-inspection trace |
| V3 Complete strategy engine | All 120 baseline cases, family discriminating cases, all dials/constraints and interaction suite; accounting/metric/mutation coverage gates |
| V4 Research workflow | Freeze/holdout/candidate/trial/controls/statistics/recovery cases; immutable manifests and final-window access logs |
| V5 Product and scale | All end-to-end/report/security/accessibility/visual/offline cases; scale measurements, fresh install/reproduction and current evidence audit |
| V6 Final conformance | Plan-to-code-to-case-to-receipt reconciliation; zero unmet mandatory requirements; current coherent release build; open-defect/deviation report and linked final release verdict |

Record receipts at each checkpoint and after meaningful fixes. Progress updates should link the checkpoint receipt, summarize what actually passed and name remaining failures; they must not say “verified” merely because implementation is present. Tests may run early and repeatedly as needed, but expensive or live checks need reruns only when affected code/data, stale evidence or failures justify them.

## Final delivery evidence

Deliver a runnable localhost app, launch instructions, exact tested source/dependency versions, rulebook and assumptions, coverage ledger, implementation map, raw machine-readable test reports, financial reconciliation samples, actual browser screenshots/traces, benchmark results, holdout-access history and a concise final conformance report linking all receipts. Keep large price data and source-video captures local; do not publish them or secrets.

The final report must explicitly answer: what was required, where it was implemented, how it was tested, which build/data were tested, where the evidence is, which differences from the host remain, and whether any mandatory case is unmet. At present the correct product verdict is **NOT VERIFIED / NOT READY**.


## Expanded portfolio acceptance inventory

The original330 acceptance cases remain mandatory. Catalog version2 adds nine explicit cases for portfolio input/identity, shared cash, aggregate entry volume, per-rule chart/attribution, sealed-date guards, cancel/resume/corruption, real browser/export journeys, independent historical joint-account reconciliation and trade-level visibility. That historical version contained 339 mandatory cases, including the original 120-case strategy matrix. The current catalog v6 contains 82 requirements and 397 mandatory cases. The additions are ACCT-002-C04 through C11 and UI-004-C04. They begin uncertified; component/browser evidence is not automatically promoted to final acceptance.

The executable numerical threshold gate is [check_numerical_coverage.py](verification/check_numerical_coverage.py). Its declared module scope includes config,data,signals,engine,metrics,service (including shared-account attribution/sampling) and benchmarks/controls. Both comparison modules are subject to the same thresholds, not exempted as a comparison feature. It verifies the executed coverage artifact hash and current source hashes, computes percentages from raw covered/total counts, and fails below95% statements or90% branches. This supplements the critical-provider/holdout/order/accounting, functional, mutation and full-release requirements above.

## Verify the evidence machinery itself

The release checker must reject an absent/duplicate/unknown requirement mapping, empty or inconsistent catalog, missing implementation/test/rulebook links, missing subject or receipts, source/specification/input drift, modified artifacts, unsafe or credential paths, nonzero command exit, unknown/duplicate case results and impossible execution timestamps. Planning/component receipts cannot certify product acceptance. A current non-pass remains unresolved until an explicitly linked, later, current passing receipt supersedes it for that same case.

[tests/test_release_evidence.py](tests/test_release_evidence.py) exercises these conditions in isolated synthetic temporary workspaces. Those fixtures test the gate and cannot certify the real product. The numerical coverage gate and evidence recorder also have dedicated fault tests. A green integrity checker establishes completeness and hash consistency of submitted evidence; independent oracle review and actual UI/financial assertions remain necessary to establish that the evidence tests the intended behavior.

## Statistical and passive-benchmark acceptance expansion

Catalog version3 retains all339 existing cases and adds six: MET-001-C04 (nonpositive equity/finite JSON), RES-008-C03 (published and independently calculated DSR), and MET-003-C03–C06 (causal passive allocation, corporate actions, guarded/recoverable jobs and real browser/export comparisons). That historical version contained 345 mandatory cases, including the unchanged 120-case matrix. The current catalog v6 contains 82 requirements and 397 mandatory cases. None is automatically certified by component results. Regeneration itself must preserve every existing case and implementation mapping; tests/test_catalog_generation.py compares the complete generated catalog with the normative inventory in a temporary directory.

## Conditional random-control acceptance expansion

Catalog version4 preserved all345 prior cases and added RES-006-C04–C09, bringing that inventory to80 requirements and351 mandatory cases. The added cases require independently checked maximal matching, fixed source denominators, causal candidate features, mirrored risk geometry, invalid/missing/negative cases, actual guarded/checkpointed accounts, corruption recovery, both desktop UI journeys and an actual default20-account historical run. Shifted levels and the broader behavior inventory remain required under the existing cases; matched entries do not substitute for them.

Include controls.py in the numerical95% statement/90% branch gate. Assert that metadata actually identifies the frozen numerical subject, aggregate CSV rejects ambiguous multi-account output with a useful error, and selected account CSV/JSON agree. Use an independent exhaustive assignment oracle on small graphs and a separate stdlib hash calculation for seeded ranking, in addition to independent supplied-signal execution. Record a failed coverage measurement as such even if its tests passed; absent coverage data cannot meet a coverage gate.


## Behavior verification expansion

Catalog version5 preserves every prior351 mandatory case and adds RES-010-C01 through C27: ten mechanics/product checks plus one explicit case for each of17 diagnostics. That historical version contained 81 requirements/378 mandatory cases; that expansion used catalog v6 with 82 requirements/397 mandatory cases. RULEBOOK0.9 and decisions D024 define the visible video requirements and equity adaptations. Verify mirrored thresholds, causal feature birth/update/expiry, independent shifted visits/invalidation, full follow-up and unmatched/censored counts, both hold denominators,10/20/50 horizons, independently recalculated whole-session intervals, actual default20/five-chart work, all17 table mappings, guarded API/worker recovery and both real desktop browser/export journeys. The numerical coverage gate now includes behavior.py with the same95%/90% thresholds. Component checks and screenshots cannot certify these final cases; current frozen-subject receipts and independent audit are mandatory.


## Paired ablations and trial-ledger verification expansion

RULEBOOK0.10/decision D026 implement the one-rule comparison visible on source prompt page12. Catalog version6 preserves all previous378 cases and adds RES-011-C01–C12 plus RES-004-C04–C10:82 requirements/397 mandatory cases. Add independent complete-account/day-pairing fixtures, strict one-field validation, input/calendar compatibility and overlap denominators, positive/negative/undefined paired statistics, sealed-date guards, checkpoint corruption/recovery, actual historical arm audits and both real desktop/export journeys. Trial-ledger cases cover atomic pre-execution plans, role-aware distinct denominators, every actual attempt/retry/interruption, complete sampler proposal outcomes, frozen input/output integrity, legacy provenance and all-history pagination/export without raw-price reads. Prior351 and378 inventories retain their exact recorded physical fingerprints when projected back; original expectations are not weakened.

The source page12 funnel additionally specifies10000 matched trade-twin sets and era/ES replication. Current20-account conditional comparisons are separate; they do not complete the full source funnel. Named/common/spread sampling, full signal/family/replication gates and search-aware sensitivity remain required. No final conformance certificate can be issued from this expansion's component receipts.


Ablation intervals additionally require six or more sessions to avoid the mechanically zero-variance single-circular-block case (D027). Verify this using an unchanged three-session counterexample and an independent six-session bootstrap. Trial exports must preserve a stable read snapshot across sequential thread-pool handoffs and concurrent job writes; actual cross-thread failure/regression evidence is required. Numerical coverage now includes ablations.py and trials.py at the same95%/90% thresholds, alongside critical lifecycle/integrity use cases.


## Confirmation and filter acceptance closure

RULEBOOK0.11/D028 and verification/fixtures/confirmation-filter-contract.json sharpen existing RULE-003/RULE-004/STR-011/STR-012 acceptance without removing or adding catalog cases (82 requirements/397 mandatory cases). Verify every supported confirmation/waiting-window value, equal/strict thresholds, known-state trend and prior-session references, DST/session boundaries, gap/fresh-breakout direction, news weight/risk/exposure and overnight confirmation-day semantics. Distinguish injected completed-context selector tests from real minute/detector/daily-hourly integration and independent account execution. Retain both genuine product counterexamples and corrected verifier-schema failures. Full pairwise/higher-order, versioned calendar, mutation and final release acceptance remain required beyond these fixtures.


The confirmation/filter closure additionally uses verification/critical_signal_mutations.py: run the unmodified selected fixtures first, then isolated actual source changes for setup-date regression, a one-candle-short window, strict half-wick threshold, future-trend inclusion, equal-run rejection and late control validation. Each mutant must fail assertions with zero collection errors/skips; preserve mutant sources, hashes, XML and logs. This six-mutant scope supplements, and does not complete, the full detector/execution/accounting/security mutation requirement. Data/service fault fixtures additionally cover malformed imports, atomic-write cleanup, all dataset identity layers, prior exposure migration, incomplete warm-up, unsupported input rejection before price reads, saved-report identity/window faults and the transactional study-job guard beyond500 records.


## Evidence privacy derivation

D-PRIVACY-001 requires a private-raw/review-artifact boundary. Future browser captures begin under data/private-evidence, outside receipt output trees. Preserve actual child exit codes and immutable originals. Produce deterministic sanitized copies before artifact recording, removing authentication/session headers, cookie fields, credential JSON/log/query/password values, known long-value propagation and workspace/home paths. Preserve financial values, images, timestamps, event ordering and source/resource links; explicitly record before/after whole-file hashes and nonsecret edit counts. Unsupported/malformed/unsafe/oversized traces or credentials in unsupported binary content fail closed, never publish raw/partial output. Historical originals and receipts remain unchanged/local/private with separately derived review artifacts. Secret-sentinel tests, real success/failure captures, installed viewer playback, provenance and exclusion of private captures supplement the unchanged82/397 final inventory. Hash/CRC integrity does not imply privacy acceptance. See verification/fixtures/trace-privacy-contract.json.


## Versioned scheduled-news calendars

RULEBOOK0.13/D032, catalog v7. Preserve every prior397 case and add DATA-011-C01–C14:83 requirements/411 mandatory cases, including the unchanged120-case strategy matrix. Source prompt pages4–6 supply news trade/skip/half choices; exact private event files are unavailable. Our free preset selects BLS consumer-price and jobs reports plus scheduled Fed decision days. Other announcements, unscheduled events and corporate earnings are not inferred from price bars. Custom reviewed CSV/JSON calendars cover additional events.

Freeze immutable calendar coverage/types/mode/events and source metadata/body hashes into every new applicable job and study. Current official pages provide a retrospective schedule reconstruction; historical advance knowledge is an explicit assumption, not point-in-time proof. Recorded-knowledge imports apply only at/after known_at on the New York confirmation date. Skip/half affect new signal eligibility/planned risk, not forced liquidation of existing positions. Controls exclude skipped moments and match half-risk regimes; paired arms share the same calendar. Validate completeness, coverage, snapshots and sources before price reads, including recovery/final work.

Official acquisition uses only fixed BLS monthly and Fed-calendar URLs, bounded bodies/date spans, no redirects/credentials, cancellation/retry limits and persisted per-job document receipts. Partial/orphan/corrupt work cannot publish a complete version. Keep actual dated live acquisition separate from authored/mock tests. Execute all14 new cases, the original cases and affected numerical/API/browser/recovery regressions; expand fixtures and interaction coverage rather than promoting component passes. See verification/fixtures/news-calendar-contract.json.


Calendar boundary/recovery acceptance also rejects implicit numeric/timestamp calendar dates, numeric/naive/overprecision knowledge times, blank/control-character names and malformed source metadata before publication. Test the same malformed metadata on hash-consistent disk manifests, including metadata-only listing. Actual worker tests must cover cancel, shutdown, missing checkpoint reconstruction from committed events, corrupt source/checkpoint rejection and source revalidation before cached completed-result reuse. Final-worker transition fixtures must distinguish injected candidates from genuine screening success, verify exact frozen calendar export and prove corrupt calendars reject before final unlock or prices. Real desktop journeys deliberately delay report loading while navigating to Reports; preserve the selected page, visible knowledge notice, exact JSON and all offline pages. These sharpen existing DATA-011 cases without removing any prior expectations.

Final release artifact validation shares the recorder's private-root/raw-trace boundary. A correct hash cannot legitimize a private capture or unreviewed trace archive, including a ZIP renamed with another extension. Verify failures using complete synthetic receipts with their execution logs retained, and a positive audited derived-trace fixture. This closes one boundary; broader privacy/security acceptance remains mandatory.

## Time-varying short-borrow verification

D034/RULEBOOK0.14/catalog v8 retains all411 prior cases and adds eleven ACCT-004 cases:83 requirements/422 mandatory cases. Use verification/fixtures/borrow-scenario-contract.json for independent hand calculations, full schema/scope rejection, exact minute/weekend financing, future-append invariance, entry-stage availability, latched recalls, opening-gap precedence, actions/shared-capital accounting, immutable job/study/recovery/final guards and actual desktop/export flows. Clearly distinguish synthetic lending assumptions from historical observations. Execute separate0/3/10/30 percent sensitivity accounts. The reference engine must not share production borrowing helpers. Retain every first failure and unchanged tolerances; all prior full-project acceptance remains mandatory.

Run verification/critical_borrow_mutations.py against isolated copies: first the unmodified33-case borrowing baseline, then actual future-rate, omitted-financing, forgotten-recall, wrong same-close clock and availability-forced-exit mutations. Each mutant must fail assertions with all33 cases collected and zero collection errors/skips; retain changed sources, hashes, XML and logs. Preserve original source bytes and verified temporary cleanup boundaries. This targeted set supplements the unchanged broader mutation requirement.

## Four-rate complete-account verification

D035/RULEBOOK0.15 uses the existing422-case inventory. Execute verification/fixtures/borrow-sensitivity-contract.json: independent50/49-share nonlinear arithmetic and Decimal accounts; original/frozen cost transformation identity; empty/losing/no-short outcomes; complete dated differences; actual four-part worker output; every pre-price/news/borrow/protected-window guard; committed part and root-result tampering; orphan/cancel/shutdown/resume behavior; four prespecified scenario identities/attempts/reuse; full JSON/CSV/trade inspection/offline adapters; stale/delayed UI response ownership; both desktop profiles/every page and fresh independent saved historical reconciliation. Numerical sensitivity code is subject to95% statement/90% branch gates. Retain all failures and unchanged tolerances. Existing account-level uncertainty is separate from descriptive rate differences. Component evidence cannot certify the full release.

## Frozen shared-portfolio final verification

D036/RULEBOOK0.16 sharpens existing RES-001/002/003/004, ACCT-002 and UI-004 cases without dropping any of422 mandatory cases. Execute verification/fixtures/portfolio-study-contract.json: strict mode/set bounds; original/candidate input hashes; actual nonempty winning screening/final and honest empty/loss outcomes; independent Decimal joint-account accounting for all three windows; portfolio-role trial occurrences; protected reads/aliases; manifest/news/borrowing/input corruption; cancel/shutdown/orphan/part/root recovery before and after final consumption; exactly one final unlock; complete saved inspection/JSON/CSV/offline exports; real two-desktop flows and source-provenance rereads. Keep synthetic geometry and injected transition tests distinct from real screening success. Preserve tolerances and first failures. The default independent workflow must retain its semantics; full regression and numerical coverage/mutation gates remain required. Component checks cannot certify final release.

The frozen-study expansion also includes research.py in the95% statement/90% branch gate, because original-input binding, candidate identity, reservation and consumed-window decisions are essential to interpreting the numerical result. This requirement is frozen before the new full-suite measurement. Existing coverage thresholds and every other module remain unchanged.

## Runtime ownership and measured overhead regression

Execute D037/RULEBOOK0.17 verification/fixtures/runtime-capacity-contract.json before claiming runtime/capacity closure. Use real OS leases/processes for same-store duplicate rejection and owner crash/restart, actual exception/start-failure cleanup and spawned worker Ctrl+C behavior; record remaining process trees/ports. SQL-authorizer fixtures must refuse full-payload reads during cancellation/heartbeat; cover wrong/missing/terminal ownership and lost-owner final safety. Actual searches must have bounded whole-plan reads/hash calls independent of member count; preserve cancel/shutdown/corrupt-part and full pre-publication integrity checks. Reconcile streamed sparse/multi-symbol execution to independent Decimal accounts and every historical100/1000 report field except exact named source fingerprints. Freeze budgets/sample before timing, separate instrumented profiling, state host concurrency and retain failed budgets/mutations. These supplement existing422 cases, unchanged15-module95/90 gates and broader complete final acceptance.

## Search-statistic application and saved-only evidence

D038/RULEBOOK0.18 implements the existing RES-008 diagnostic workflow under unchanged83/422/120 scope. Follow verification/fixtures/search-statistics-contract.json. Freeze effective-trial assumptions and empirical/assumed cross-trial SR dispersion before queueing; calculate from all saved complete daily marked accounts, not selected winners. Default powers-of-ten/count assumptions are sensitivity scenarios, never an independence estimate. Use per-session units, bias-corrected moments and the existing Bailey/Lopez de Prado formula; preserve undefined/null/loss outcomes and single-trial zero benchmark. Keep original profit separate from model scores and explain prior-search/serial-dependence limits. Provide complete saved-only JSON/long CSV/offline projection, actual UI/API/worker/recovery and independent numerical/fact evidence. No DSR score changes candidate/final gates. The source-style sampling/trade-twin/era/replication funnel and larger workloads remain mandatory. Primary source: https://davidhbailey.com/dhbpapers/deflated-sharpe.pdf .


## Common-grid/random sampling and discovery-stage verification

D039/RULEBOOK0.19 follows verification/fixtures/common-sampling-contract.json. Exhaustively validate the complete declared grid against independent family/chart cardinalities and Strategy constraints. Independently calculate exact40/40/20 accepted filter quotas, conditional groups, stable per-slot streams and canonical ordering. Preserve every proposal, duplicate/rejection and failed partial plan without executing it. Actual API/worker/recovery/news/corruption and both desktop flows must retain all accounts and source-part hashes; independent JSON/CSV/offline readers verify threshold boundaries and cumulative/family/chart denominators. Freeze thresholds before prices; twins/eras/replication/final remain not_run. Add sampling.py to unchanged95% statements/90% branches and require current full regression and actual assertion-killed mutations. No83/422/120 acceptance obligation is removed or promoted from component tests.


D039 signal qualification counts only saved primary decisions whose available_at New York session date lies within the requested discovery window. Warm-up signal evidence remains intact but cannot inflate the signal gate. Verify a real late-window account with earlier saved signals, DST/date boundaries and exact source counts. Retain zero-generated frozen family/chart cells with zero count denominators rather than silently dropping them.


D039 export completeness requires original sampling_policy and frozen news calendar ID/snapshot in each new root search summary, explicit mode/news/recipe identity columns in CSV, and offline mode/news/recipe/window-signal/scope facts. A calendar-bearing search remains a search; acquisition routing must inspect kind, not merely presence of a calendar ID. Preserve incomplete prototype originals with an explicit legacy-metadata notice rather than rewriting their evidence. The v2 desktop fixture retains the original48-grid and six-random cases and adds a six-random calendar-bearing case per profile, without changing any profit/selection threshold. Source quotation and exact-host-recipe gaps remain unchanged.


## Saved dataset context — D040 / version0.20

Follow verification/fixtures/dataset-context-contract.json. Freeze only dataset ID/manifest hash, declared input kind, source and canonical instruments before queueing/registration; validate before prices. Preserve exact context in new roots, reports, CSVs, UI and offline facts. Distinguish unverified/unknown imports and absent legacy records; never infer from the selected UI dataset or rewrite old outputs. Exclude protected action details, arbitrary metadata and credentials. Verify every analysis path, actual workers, recovery, saved-only exports, corruption-before-read, exact independent CSV/fact parity, formula/XSS escaping and both desktop dataset-switching journeys. Financial formulas, all83 requirements/422 cases/120 matrix cases and host-engine differences remain binding. The numerical coverage gate additionally includes dataset_context.py at unchanged95% statements/90% branches.


D040 follow-up: offline context retains both the entire instrument list as one independently formatted source fact and individual instrument facts. Recognize the explicit historical_market_data import classification; preserve unknown/unverified kinds. Nullable behavior descriptors remain sourced Undefined values. Import parsing/normalization/publication runs outside the HTTP event loop under one per-app import lock, preserving original size/action/date validation and atomic publication. Verify controlled held normalization with an unchanged two-second concurrent-health deadline, equal concurrent imports, and the original browser import deadline; retain first failures. These changes do not alter trading rules, cash/account formulas or final-window policy.


D040 universe preservation: metadata must not impose a new twenty-instrument analysis limit on existing eligible imports. Retain the entire canonical instrument array; the UI pages twenty labels at a time, and offline rendering retains every indexed symbol. The complete-list fact displays the full joined list up to twenty members, otherwise an independently formatted count with indexed-page direction; its raw source value remains the whole array. Existing upload, data-quality and presentation budgets remain unchanged. Verify an actual eligible twenty-one-instrument import, worker account, complete source facts, UI next/previous controls and saved-only export. The first introduced-cap failure is retained.


## Bounded job monitoring — D041 / version0.21

Follow verification/fixtures/job-status-contract.json. Preserve full immutable inputs/trials/results while transactionally caching bounded, fingerprint-bound status projections. Poll/list/control responses read small cached input metadata and live lifecycle columns, not the full plan JSON. Single-job status is at most64KiB; at most500 list records fit2MiB. Explicit on-demand input export and derived-index repair verify original frozen inputs; corrupt cache is visibly unverified, never silently reconstructed from current UI/data. Backfill legacy indexes without rewriting original evidence. Test actual byte/materialization budgets with large plans, complete input exports, cache/original corruption, migration, controls, ownership and browser journeys. No financial formula, universe limit, trial count or final-date policy changes. Study-list/result-read scaling and actual numerical10000/bounded100000 workloads remain mandatory, separately verified. All83 requirements/422 cases/120 matrix cases remain binding.

D041 derived-metadata integrity additionally places job_index.py under the existing95% statement/90% branch gate. The combined gate now covers19 modules; a focused component percentage is not a substitute for the full current regression artifact.


## Bounded study monitoring and isolated legacy recovery - D042 / version0.22

Follow verification/fixtures/study-status-contract.json. This extends existing RES-001/002/003/004, JOB-001/002/004, UI-003/005, PERF-001/002 and evidence/mutation requirements without changing83 requirements/422 mandatory cases/120 baseline combinations. Small fingerprint-bound study projections support a64KiB detail response and at most500 history records within2MiB; full verified inputs remain explicit on-demand downloads. Polling and protected-scope checks must not read/decode raw studies.spec. Preserve the exact instrument/date intersection, live lifecycle and permitted final-job conditions in a transactional snapshot; missing/corrupt scope fails closed before prices or viewed-window writes. Cache lifecycle/candidate/reservation projections atomically with original transitions; original registration, candidate and final events remain authority. Never impose a new instrument/configuration/input limit.

Actual current legacy plan reconstruction already streams a SQLite cursor. Preserve that one-plan-at-a-time behavior and add per-job rollback/isolation so unreadable or unreconstructible originals do not abort valid neighbors or startup. Keep original bytes, zero fabricated attempts and honest legacy/unverified provenance; never invent a valid frozen plan. No strategy, accounting, sampling, eligibility or final-date formula changes.

Before implementation, retain authored failing API/SQL-authorizer/corruption/malformed-legacy contracts. Verify10/1000/100000-configuration registrations and complete HTTP downloads separately from numerical throughput;500-record pagination; original/cache tampering; all protected-scope boundaries, copies and concurrent final/lifecycle transitions; original worker screening/final guards and exactly-once continuation; desktop download/control/selection/error screenshots; independent fingerprints/complete exports; critical isolated mutations; full current regression/coverage and one coherent source/evidence checkpoint. Preserve first failures. Large result loading, research-funnel work, numerical scale and final conformance remain separate mandatory work.

Source: https://www.youtube.com/watch?v=z97PnFIPoFg . These are operational improvements around the declared equity adaptation; unavailable private engine/grid/named recipes remain explicit differences.

D042 adds study_index.py to the unchanged95% statement/90% branch gate:20 modules. Component percentages do not replace the full current regression artifact or final422-case evidence.

D042 history pages must remain reachable from the UI after list bounding. Verify newest/newer/older controls, exact returned page labels, stale refresh suppression and long-poll serialization without changing result/report ownership. Page counts are metadata, not certification of numerical registrations.


## Bounded saved-result views and older-job browsing - D043 / version0.23

Follow verification/fixtures/result-materialization-contract.json under the unchanged83 requirements/422 mandatory cases/120 baseline combinations. Add an explicitly derived64KiB root summary, default50/max100 result rows within2MiB, bounded diagnostic pages and selected-part lookup without decoding unrelated root/configuration arrays. Keep complete original result/input/report/statistic/screen exports and original financial values. Missing legacy views expose a verified build-from-original action; absence is not empty evidence.

Use a separate content-addressed SQLite view artifact per original root, anchored by an event, rather than a long main job/lease DB write transaction. Publish new views from the worker's constructed output; verify originals before legacy build/repair. Stream original compressed-root, derived-file and exact input-byte hashes in64KiB chunks in consistent read snapshots; keep canonical frozen-input identity distinct from raw-byte identity. Same-length corruption, bad cache, wrong part/window/job and interrupted publication must fail safely. Do not substitute size/mtime for integrity, rewrite old outputs, change financial rules or impose new input/universe/configuration limits. Preserve worker cancel/resume and existing complete-result/report behavior.

Older-job and result/diagnostic pages need separate state from selected-report identity. Verify stale success/failure, current errors/retry, exact page labels and matching exports. Preserve all existing portfolio/final/data-context/ownership flows. Scope study-history toolbar styling to its own controls. The planned result-index module joins the unchanged95% statement/90% branch gate when implemented.

Before implementation retain authored failing API/materialization/part/corruption contracts. Verify worker publication/recovery and all-row/config/candidate/metric/diagnostic parity against originals; large metadata/part measurements separate from numerical10000/100000; both desktop history/page/inspect/export/keyboard/error flows; independent original/account/fact audit; critical mutations; full current regression/gates and one coherent source/evidence checkpoint. Explicitly retain legacy/null/loss/empty cases and first failures. Remaining research funnel, measured numerical scale and final conformance remain mandatory.

Source video: https://www.youtube.com/watch?v=z97PnFIPoFg . Incremental I/O references: https://docs.python.org/3.13/library/sqlite3.html and https://www.sqlite.org/c3ref/blob_open.html . Owned UTF-8/same-length-corruption capability probe: verification/receipts/20261109T055143679582Z-result-materialization-owned-sqlite-text-stream-and-same-length-integrity-capability-probe.json . No new dependency or market is added by this step.

D043 result_index.py is now included in the unchanged95% statement/90% branch gate, totaling21 modules. First seven saved-view/streaming/corruption contracts pass; this does not establish current full regression/21 gates or final conformance.


## Verified job-scoped evaluation cache - D044 / version0.24

Follow [the preimplementation cache contract](verification/fixtures/evaluation-cache-contract.json). The actual one-session1000-account run took155.296s; its profile identifies repeated price preparation and base-candle aggregation. Cache those verified intermediates within one job under128MiB of accounted retained bytes, with eviction/fallback rather than a new input limit. Preserve current source-byte/manifest/protected-date checks, all configuration-specific calculations, original trial/account authority and cleanup/isolation. Context/detector/signal/account outcomes are not memoized.

Prove cached/uncached complete-value parity, all six chart clocks, source corruption and protected-date rejection before cache use, bounded eviction and all exit paths before scaling. Compare complete actual100/1000 parts against uncached0.23 results with separately validated source provenance. Actual10000 remains required under the original900s/3GiB/2GiB limits;100000 numerical stress is separate. This implements the existing performance requirements without changing83 requirements/422 cases/120 baseline combinations or any numerical formula. Source: https://www.youtube.com/watch?v=z97PnFIPoFg .

D044 performance follow-up: exact1200 complete account comparisons pass, and cached1000 improves155.296s to119.312s. Reuse one job-local read-only SQLite control connection, querying current cancellation/owner/status every time in autocommit mode. No control state is memoized and no transaction is held between reads. Require live cross-connection changes, raw-payload prohibition, root/thread/nested isolation and every-exit cleanup before repeating the unchanged capacity gates.

D044 actual10000 first attempt stopped at the unchanged900s bound with4663 durable parts; it is a retained failure. An owned16MiB SQLite probe shows control-field reads through the large row scale poorly, while a covering index avoids that read. Default planning and ANALYZE kept the slow plan in this fixture. Add jobs_live_control(id,status,owner,cancel_requested) and bind only the two finalized cancellation/trial-owner SELECTs to that covering plan, using INDEXED BY as a regression requirement after the measured alternatives. Preserve original bytes/rowids/events, all per-configuration checkpoints and existing durability. Require old-store upgrade parity, actual EXPLAIN plans, missing-index fail-closed behavior, the existing live-state guards and a fresh bounded10000 run. See the source/probe receipts in verification/fixtures/evaluation-cache-contract.json.

### D045 — balanced spread verification

Use verification/fixtures/spread-selection-contract.json without weakening the83/422/120 inventory. First preserve authored failures. Independently recompute the exact all-bin discrepancy with Fraction arithmetic, every candidate rank and ordinal tie; exercise every applicable public field and conditional catalog domain across all ten families/six charts. Prove every bounded proposal file and manifest is frozen before the first signal callback, repeat bytes exactly, and reject source/manifest/file/context changes before probes. Check the40-signal boundary, malformed/zero/bool/negative evidence, accepted/failed/within-batch duplicates, exhaustive no-eligible termination and absence of a successful partial selected manifest.

Exercise every probe/journal interruption boundary, deterministic replay with no repeated committed numerical probe, prefix corruption, authorization and cancellation before both new and reused work. Execute actual synthetic primary-instrument signals with complete hash evidence and excluded warm-up decisions. Pure sampler fixtures and configured40000 defaults are not an executed40000-source-qualified pool or100000 numerical stress. Durable registry/worker/cancel/recovery/guard/API/UI/export, actual resource measurements, full regression/coverage/mutations and coherent final acceptance remain separate mandatory proofs before declaring this workflow complete.

### D046 — complete executed-trade twins

Use [the authored contract](verification/fixtures/trade-twins-contract.json). Preserve the first authored assertion failure and all subsequent failures. Independently enumerate full pools and exact rational geometry with a separate time-zone implementation; prove complete exchange clocks, all-or-none real cohorts, original-entry exclusions,30-minute boundaries, DST/early-close/holiday/weekend/cutoff cases and forbidden future-outcome inputs. Exercise strict original identities/types, visible working bounds, immutable detached snapshots and cancellation before preparation and during streamed draws. Verify the exact independent SHA-256 coordinates and rejection branch, replacement/collision retention, seed differentiation and ordinal-prefix/resume stability. Measure actual10000 matching draws separately from financial sets.

For grading independently check exactly10000 unique bound outcomes, all-or-none completion, retained failures/empty/undefined/losses, ties and499/500 strict boundaries. Reconcile raw and plus-one fractions separately and invert binomial tails to verify the exact95% Monte Carlo interval. This interval is conditional on independent set draws under the frozen diagnostic, not a source-style extra gate or uncertainty about markets/search selection.

Then independently verify original entry traces and protected parent/data/account authority; every numerical field for both execution interpretations, actions/borrow/cost/tick/duration boundaries; actual durable worker deaths/recovery/cancel/reuse/publication; one original linked child; bounded metadata; complete API/UI/CSV/JSON/offline/source-difference/mobile/keyboard/privacy evidence; actual10000 numerical sets and resource bounds; critical mutations and unchanged95% statement/90% branch gates. Matching-only fixtures and supplied outcome totals never certify these later obligations. Preserve83 requirements/422 mandatory cases/120 combinations and final requirement-by-requirement conformance.


## D046 supplement — canonical original cash flows and saved comparisons

Source: https://www.youtube.com/watch?v=z97PnFIPoFg (AI Pathways / Brendan). All original83 requirements,422 mandatory cases and120 baseline combinations remain binding.

The original float account and Decimal twin engine can report different numerical values for identical cash flows. New compatible independent accounts must therefore produce a Decimal80 observed-fill audit before the original report is committed and before any twin assignments or outcomes. Preserve original fills, whole initial quantities, traces, order roles, clocks, legacy metrics and immutable report/attempt/part authority. Reconstruct only their executed fees, split-adjusted basis/shares, dividend entitlements and borrowing from authoritative known raw marks and calendar rates; do not rerun signals, order selection or allocation. Preserve the exact sum of original reported profits separately. Reconcile each component within the existing absolute1e-7 accounting boundary; strict exceedance grading uses the canonical audit with no comparison epsilon. Reject mixed precision cohorts. Historical reports stay readable; never invent audit fields in them.

Freeze and publish the canonical baseline, original reported sum, precision policy, audit digest and difference with the original child assumptions. The continuation API accepts only a strict original part ordinal. It cannot override strategy, costs, seed, quantity or the10000-set workload. Provide start, progress, cancel/resume, original-child reuse, saved reopening and paired summaries. Distinguish ineligible original cohorts (no generated financial sets), failed candidate sets (retained failures), complete comparisons and missing evidence. Complete original saved-set/book inspection and full exports remain required.

Verification must include actual original/twin identical positive and negative cash flows; long/short, fees and financing ties; independent Fraction/Decimal fee, action, dividend and changing-rate/weekend/DST totals; zero-duration/empty inputs; large-plus-tiny cohort sums; malformed clocks, cohorts and rehashed audit corruption; original saved authority and absence of regenerated signals. Use an actual owned10000-set-per-policy worker with original20001 occurrences, all deterministic draws/whole memberships/exact totals and every unique complete book independently audited. Preserve completed trial states and all original checkpoint events. Record wall time, disk and peak worker memory even when a later assertion fails. Missing memory evidence remains missing; audit-process memory cannot substitute.

Exercise real API/local session boundaries, repeated continuation, cancellation/resumption, reload, delayed responses and accessible desktop/mobile saved summaries. Retain screenshots, downloads, traces, source hashes, original failed receipts, actual coverage databases and mutation baselines. Test missing fees, missing borrowing/dividends, reversed splits, float baselines, weakened exact grading and omitted input binding with actual assertion kills. No harness/import/runtime error counts as an assertion kill.

Current component evidence:127 original-source/integration cases (20261110T001252129978Z);133 broader financial/boundary cases (20261110T001704179259Z); canonical current93-case gate rerendered from actual coverage DB (20261110T002550477221Z);63 API/reservation/worker cases (20261110T002344621919Z); eight assertion-killed mutations against a green94-case baseline (20261110T003432123825Z); actual completed20000 occurrences/20001 checkpoints/28 complete independent books (20261110T003606554008Z); three desktop/mobile actual lifecycle and completed saved-summary journeys (20261110T003731257785Z). These are bounded component subjects, not a coherent global38-module gate or final product acceptance. The first full-workload checker failed because it expected checkpointed instead of completed trial states; its failed receipt remains. Peak worker memory was not retained in that run.
