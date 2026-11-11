# Development Journey — Price Action Research Lab, through the pause

**Build cutoff:** 2026-11-11T04:17:17Z (November 10, 8:17:17 p.m. Pacific). The implementation goal was explicitly paused at the user's request. Documentation, privacy review and Git publication follow that cutoff and are not included in these build totals.

**Read the complete history:** DEVELOPMENT-JOURNEY.md, DEVELOPMENT-JOURNEY-2.md, DEVELOPMENT-JOURNEY-3.md, then this installment. The rendered development journey combines all four. Earlier history is reconstructed from those retained journals, decisions, public-message milestones and original execution receipts. This installment records the latest observed work. None is a final product acceptance certificate.

**Inspiration:** [AI Pathways — Claude Tested 100,000 Price Action Strategies (Here's What Works)](https://www.youtube.com/watch?v=z97PnFIPoFg&t=401s).

## 1. The brief and the boundary of the reconstruction

The initial request was:

> build me the same application for testing price action strategies as described in this video. you must capture the details by examining the video frame by frame. let me know what the gaps are and any requirements or dependencies. come up with a plan first. AMIAQ

The user subsequently chose US stocks and ETFs, a private localhost application, free data, Alpaca, and both long and short simulation with explicit borrowing assumptions. The user prioritized accuracy and reliability over selecting unfamiliar trading terminology. Later requests made source attribution, differences from the host, exhaustive use-case verification, evidence receipts, a full development journey and time/token accounting binding deliverables. The pause is a deliberate stop with unfinished work, not a redefinition of success.

The source was a research presentation rather than a demonstration of a complete interactive application. Automated decoding covered 30,920 frames. Visual inspection covered 1,031 one-second samples, 37 focused 4K captures and 15 technical prompt pages. It would be false to describe this as a person manually examining every individual frame. The host's private code, complete grid and six named preset recipes were not available. Ten families and visible research concepts could be adapted; identical host trades, performance and private strategy definitions could not be established.

## 2. Technology, architecture and reproducibility

The supported development environment is Windows/PowerShell, Python 3.13 and Node 22.22. The Python and JavaScript dependencies have separate checked-in locks. Package versions below are the recorded locks at this pause, not a claim that they are the latest available versions.

| Layer | Recorded choices and purpose |
| --- | --- |
| HTTP/backend | Python, FastAPI 0.162.2, Uvicorn 0.54.0, Pydantic 2.14.3; validated requests and a loopback API |
| Numerical/data | NumPy 2.3.5, pandas 2.3.3, PyArrow 24.0.0, SciPy 1.18.1, Numba 0.68.1, DuckDB 1.5.6 |
| Calendars | exchange_calendars 4.13.2 and pinned timezone data; regular sessions, holidays, early closes and DST |
| Market data | Backend-only Alpaca historical bars/corporate actions; paginated, content-bound acquisition; no order routing |
| Persistence | SQLite WAL, explicit independent transactions, job leases, original trials/attempts/events and compressed report parts |
| Frontend | React 19.3.1, TypeScript 7.0.2, Vite 8.3.6, Lightweight Charts 5.2.1, Recharts 3.10.1 |
| Verification | pytest 9.2.0, pytest-cov 7.1.0, Hypothesis 6.170.15, Playwright 1.65.0, independent Decimal execution/statistical references |
| Exports | Complete JSON/CSV, ZIP and standalone offline HTML presentations with saved provenance |

The browser talks to the local HTTP process. A separately spawned numerical worker claims durable jobs, checks live owner/cancellation state, executes independent financial accounts and publishes content-bound parts. A result index supports bounded inspection; original files, trial rows and events remain authoritative. Imported or downloaded prices become audited datasets. Strategies are immutable versions. Studies freeze inputs and protect final dates by instrument and date. Final evidence is consumed before the first analytical access, including an evaluation that later fails.

The root application is the installed development checkpoint, historically described as version 0.25. Its package manifest still says 0.1.0; the checkpoint labels describe implementation revisions rather than a published package release. The newest research source is separately staged at `data/dev027/research-src`. It was not installed over the root application. Keeping these subjects separate prevented old tests from silently certifying edited code, but also increased operational complexity and the risk of confusing historical and current status.

The current staged numerical core is `010175e4f595a2ff53a8306a85a097d4448bfbf2bbd6d6981dec318ec311b1ac`. This is the original local fingerprint before publication redaction. Publication must record any changed source bytes rather than claim historical receipts certify a rewritten tree.

## 3. Development process and decisions from the beginning

Investigation preceded implementation. The video, prompt pages, free-data access and screenshots informed the first plan. A numerical rulebook defined what a candle, signal, fill, stop, target, cost, share quantity and final test meant. The user asked for an exhaustive verification plan, so the project adopted a catalog: 83 requirements, 422 mandatory cases and 120 baseline family/chart/direction combinations. Every case still requires evidence on a coherent final subject.

The first implementation connected real data/imports, a strategy editor, experiments, results, a saved trade inspector, studies and reports. Independent Decimal execution exposed tick, participation, fee-aware size, pending-order priority, closing-mark, borrowing and gap-stop mistakes. Expected hand-authored values were retained when production was corrected. A separate shared-liquidity counterexample showed that two implementations could agree while sharing a conceptual error: multiple strategies had reused the same reference-bar volume. Both needed an aggregate participation budget.

Subsequent work added shared-capital portfolios, marked-equity metrics, passive benchmark accounts, conditional random comparisons, behavior studies, one-field ablations, causal confirmation/filter tests, offline presentations, versioned news calendars, changing borrowing scenarios and sensitivity accounts. The earlier journeys explain the individual failures and their evidence. The complete run ledger preserves passing, failing and interrupted attempts instead of presenting only the final green runs.

Large plans exposed unbounded metadata and result reads. Bounded job/status/study indexes and saved-result pagination were introduced. Balanced/common sampling and frozen continuation corrected the earlier sampler's difference from the host's workflow. Original source, prices, manifests, selected versions and provenance had to survive UI navigation, exports, restart and cancellation.

The next research stage added financial trade twins, two execution interpretations, original-account authority, both 10,000-set control policies, all-version family aggregation, chronological development roles, replication on a second instrument, qualification, frozen candidates and both-instrument final evaluation. Partial matching plans and partial financial parts were never equivalent to completed statistical controls. The positive complete-control/final workflow on the release subject remains unfinished.

No subagents were used in the observed implementation history. The independent reference engines were separately written algorithms, not separate human review or an unrelated team sign-off. Concurrency came from tool calls, worker processes and owned test subprocesses. The dev-journey skill was used for this requested retrospective. No memory store was changed.

## 4. The latest crux: integrity work dominated large-search throughput

The code preserved strong original-record checks, but repeatedly decoding or verifying an entire frozen plan per account made large searches expensive. SQLite writer contention and heartbeat timing also caused failures. The fixes had to preserve original financial accounts and live authority, rather than reduce configurations, substitute supplied profit totals or relax the resource budget.

The plans retained a 900-second wall budget, 3-GiB peak-working-set budget and 2-GiB job-output budget for the bounded real-data 100/1,000/10,000 workloads. That benchmark uses one complete 390-minute SPY session with no earlier warm-up. It is a measured capacity envelope, not a guarantee for multi-year histories. The separate actual 100,000-configuration financial stress remains mandatory and has not completed.

### 4.1 Failures and corrections after the previous journal

The first eight-account publication unit bounded retained canonical data to 8 MiB. Each report kept its own actual computation, attempt, original compressed bytes and checkpoint event. Complete original-plan verification was shared only inside one exclusive writer transaction. Financial comparisons retained gains, losses and zero-trade accounts. Oversized reports used the single-account publisher. Real process-death tests exercised recovery before and after commit.

A selected 199-case regression initially had 196 passes and three failures related to Windows startup timing and leaked subprocess pipes. The verification harness was corrected to capture early stderr, close pipes and separate startup allowance from the actual post-crash deadline. Eight focused lifecycle checks passed. The actual 15-second post-parent-crash worker-exit assertion was retained.

A later run aborted after 19 passes because Windows refused replacement of an optional live-progress JSON file. The observer was changed to tolerate that publication failure. A real locked-reader test passed. This did not change test results or let an observer failure mark an implementation pass.

The next selected run had 197 passes and two timeout failures in actual research-arm death probes. Imports and setup had consumed the same deadline as the crash boundary. The replacement probe retained a native process handle, allowed 120 seconds for startup and kept the original 90-second boundary allowance. Five real death cases and one deliberate timeout-retirement case passed. Their process exits and markers were separately reconciled.

A real 10,000-configuration run on core `e5d2219868...` stopped at 6,440 original committed accounts in 901.61 seconds. It failed. All original trial rows, attempts and report hashes were checked before canceling its owned queued continuation. A short nonblocking profile suggested repeated detector context and integrity work remained material.

### 4.2 Detector-context reuse

The next change cached complete deterministic detector context for a verified dataset/window/instrument/chart and all 12 configuration fields actually read by the context routine. It kept the existing 128-MiB job-local LRU, defensive copies, cancellation checkpoints and fresh source/price/manifest/protected-window checks. Signals and financial accounts still executed separately for every configuration.

On the resulting `d2f1e593...` core, 675 numerical/context/reference/matrix checks passed in 201.19 seconds, and a separate audit reconciled all 120 baseline combinations. The actual 100 pilot and exact byte-repeat passed in 11.01 and 8.44 seconds; 1,000 configurations passed in 65.68 seconds. These are historical component results for that source.

Its 10,000 run still failed: **5,488 committed accounts in 903.85 seconds**, with no lease failure. Peak working set was 310,280,192 bytes. A short external nonblocking profile was taken during the run; this interference is disclosed rather than omitted. The failed receipt is `20261111T033747231640Z-adopted-numerical-real-market-10000-capacity`. Preservation receipt `20261111T035330416176Z-retire-current-context-capacity-preserving-5488-original-accounts` checked the original records and canceled the queued continuation. The clean-release dispatcher refused to launch after the failed prerequisite.

### 4.3 The current uninstalled performance change

Both plans were updated before editing production, and exact prior source/plan bytes were archived under `verification/runs/large-account-unit-before`.

Large jobs now permit up to 64 independently computed reports in a publication unit, keeping the same 8-MiB encoded bound. Jobs below 64 configurations retain the earlier eight-account behavior. An uncommitted large unit can require up to 64 recomputations after a crash; private files still do not authorize reuse. Individual original accounts, attempt counts, source checks, owner/cancel checks, whole-plan checks in every exclusive writer transaction, order and financial outputs remain.

One SQLite connection can be reused inside a synchronous many-account operation. Each db context keeps an independent transaction, fresh queries, WAL/foreign-key/FULL durability and its own bounded wait. Nested simultaneous contexts and thread handoff use separate connections. Unfinished transactions roll back on context exit. Scope exit closes the handle; physical database replacement is refused. This caches a connection, not an authorization verdict.

The separately tested byte-witness implementation was adopted for complete original payload hashing and ordered typed trial projections. It retains complete cold verification, semantic JSON fallback, store/thread identity, eviction and fresh witness reads. No source-file revalidation was removed.

**All 86 focused checks passed in 244.93 seconds.** These include real 64/65/128-account comparisons against the SHA-bound prior single-account algorithm, exact complete report bytes, positive/negative/zero results, late receipt/source/owner/cancel rollback, last-record corruption and scoped connection lifetime/isolation. This is not a passing 10,000 benchmark.

## 5. Exact state at the pause

The current 829-test numerical/recovery/lease run was interrupted at the user's request. Its last observer recorded **787 passed, zero failures/errors/skips reported, 829 collected** at `2026-11-11T04:16:38.541863Z`. It has no terminal receipt and cannot be called a passing full run. The controller exited with status 1 after Ctrl+C. The subsequent capacity and clean-release stages did not start. A bounded process inventory found no matching project Python workers after shutdown; unrelated applications were left alone.

Twenty-four new news acceptance checks passed for future-event prefix invariance, overnight confirmation at exact knowledge timestamps, matched-control news eligibility/weights/denominators and incompatible calendar-version refusal. Three additional actual acquisition-crash cases failed before their intended crash boundary. The stored job error was `Internal FileNotFoundError. See the failed job event; no result was certified.`

The cause was a missing verification dependency: `news-bls-2022-01.html` and `news-fomc.html` exist under the root fixtures but are absent from the staged research fixtures. The clean-install verifier currently copies only JSON fixtures, so it would repeat this omission. This was found immediately before the user requested a pause. **It has not been fixed.** The failure is evidence of an incomplete fixture inventory, not proof that the intended calendar crash/recovery path passed or failed.

The draft acceptance audit contains all 422 cases: **145 assertion reviews complete, 28 partial, 249 pending; zero final release certifications**. The zero means no final coherent case-by-case release certificate, not zero implemented behavior. The newest core has no completed whole-suite/51-module coverage certificate and no passing current capacity certificate.

## 6. Work clock, tokens and cost through the pause

The usage collector reconciled 4,950 distinct response records with the cumulative ledger, and reconciled the previous journal's prefix. Email and private machine paths are unnecessary to that arithmetic.

| Measurement | Value |
| --- | ---: |
| Chat created | 2026-11-08T00:32:52.534Z |
| Explicit goal pause | 2026-11-11T04:17:17Z |
| Calendar elapsed | 272,664.466 seconds = 75h 44m 24s |
| Union of completed/aborted work-turn intervals | 258,403.573 seconds = 71h 46m 44s |
| Recorded turn envelope, including two open intervals clipped at cutoff | 268,991.990 seconds = 74h 43m 12s |
| Separate active-goal counter at pause | 257,339 seconds = 71h 28m 59s |
| All input tokens | 1,156,472,421 |
| Cached input, a subset of input | 1,147,371,904 |
| Uncached input | 9,100,517 |
| Output tokens | 6,622,327 |
| Reasoning output, already inside output | 3,928,437 |
| Total input plus output | 1,163,094,748 |
| Uncached input plus output | 15,722,844 |
| Distinct response records | 4,950 |

The clocks overlap and must not be added. They include tool execution/waiting and are not CPU time, uninterrupted generation or billable person-hours. Cached input and reasoning output must not be added again to their parent categories. The total does not describe 1.16 billion newly generated tokens. The build cutoff excludes the later handoff/privacy/publication work.

**Actual project dollar cost is unavailable.** No attributable invoice, credit-debit ledger or subscription allocation was present. Applying a public API rate to this application's subscription usage would invent a bill. The machine-readable accounting snapshot retains `dollar_cost: null` with the reason.

## 7. All regression and verification runs

The public verification-history page inventories every original receipt and every timestamped run directory present at publication, including directories with no terminal receipt. Each entry distinguishes the command exit, source-change/coherence notes, available JUnit counts, timestamps and artifact references. An exit-zero command is a component observation, not an automatic acceptance-case pass. Passing counts across revisions and repeats must never be added and presented as independent test coverage.

Original private command logs, browser traces, market prices, databases and temporary fixture stores remain local. Public receipt copies and metadata are privacy-derived, with original and published hashes in the publication manifest. Redaction can change bytes; those copies are not represented as untouched original evidence. Earlier fixed-cutoff receipt/failure ledgers remain part of the complete chronology. Missing or interrupted receipts are explicit.

The strongest latest evidence is the 86-pass focused regression. The 675/120 numerical matrix and 100/1,000 capacity results belong to the preceding core. The interrupted 829 run is incomplete. The news run ended with 24 passes and three missing-fixture failures. Earlier full suites, numerical coverage, browser journeys and independent financial audits certify their recorded historical subjects only.

## 8. Assumptions, source differences and limitations

US equities/ETFs replace the host's NQ/ES futures context. The ten documented families are numerical adaptations: level bounce, breakout, flip zone, trend pullback, trend line, break of structure, change of character, sweep/reclaim, supply/demand and fair-value gap. Unknown private presets remain unknown. Matching family names does not establish identical strategy definitions, generated signals, fills or profits.

Free historical access depends on the provider/account's actual entitlement and availability. Initial access probes do not certify complete coverage for every symbol/date. The application must not silently replace consolidated history with a narrower feed. Fixed watchlists do not prove point-in-time universe validity; delisted histories, symbol changes and survivorship remain explicit audit concerns. Provider symbol mapping exists implicitly, but an explicit frozen mapping/as-of contract still needs assessment and evidence.

One-minute OHLCV cannot reveal the actual sequence of prices inside a candle or guarantee queue position. Conservative ambiguity, gaps, commissions, spreads, slippage, participation, ticks and margin/short-collateral rules are modeling assumptions. Historical borrowing availability, changing rates and recalls are scenarios unless independently supplied; a constant borrow fee is not observed historical lending data. Split/distribution completeness for imported history can depend on user attestation. News reconstructed from current official pages is retrospective, not proof of what was known in advance.

Final-date protection is a product workflow guard. It cannot make information unknown to the computer's owner or undo previously viewed history. January 2022 prototype windows were already examined and are discovery data. Synthetic positive fixtures prove mechanics, not predictive investment edge. No-candidate outcomes and losing/zero-trade accounts must be retained. DSR, bootstrap intervals and random controls are diagnostics under assumptions and do not remove selection bias automatically.

The root app is useful for exploratory smaller tests and saved-result inspection. The latest localhost health request did not confirm a responding server, and no server availability is promised at this pause. Large-search capacity, complete research controls/finals, all-case conformance and a freshly reproduced latest release remain unfinished. Futures, forex and crypto are later options, not supported first-release markets.

## 9. What remains, in dependency order

1. Preserve the pause snapshot and inspect the missing-fixture failure. On explicit resume, inventory all required fixture types, copy/hash the two HTML news fixtures into the stage and extend the clean clone's fixture inventory. Re-run the three actual news crashes plus the related parser/recovery checks without relaxing assertions.
2. Complete the interrupted numerical, 64-account actual crash/recovery, original checkpoint/arm/final/store/trial and lease regression on an unchanged subject. Do not infer the last 42 outcomes from 787 reported passes. Reconcile all 120 matrix cases against actual JUnit evidence.
3. Execute real 100/repeat, 1,000 and 10,000 numerical workloads with the original wall/memory/output bounds. A component speedup or opening-count reduction does not satisfy this gate. If it fails, profile and correct the measured bottleneck before another expensive run.
4. Complete both actual original 10,000-set financial control policies through positive qualification, frozen candidates, both final instruments, all original versions and full saved exports. Do not substitute one source, partial parts, sampled rows or supplied P&L totals.
5. Execute the separate actual 100,000-configuration deterministic financial stress, retaining every original attempt, part/hash and final result row. The prior 60-account smoke is only a smoke test.
6. Run the complete base/research suite and reconcile actual coverage database counts for all 51 declared numerical modules against unchanged 95% statement and 90% branch thresholds. Fix uncovered critical branches and failures; do not round or omit modules.
7. Complete current-build browser journeys, mobile/keyboard/accessibility/privacy/security/error paths, complete JSON/CSV/ZIP/offline exports, restart/no-network behavior and a new locked clean installation. Historical browser success is not current-build acceptance.
8. Complete the assertion/evidence review for all 83 requirements and 422 mandatory cases, including the identified provider/calendar/stock-universe/borrow assumptions. Bind every case to current artifacts and independently audit conformance before installing/promoting a release.
9. Install only that verified release, verify served source/assets and worker ownership, retire owned verification services, and update the journey, accounting and user instructions. Never require the user to kill a succession of stale PIDs manually.

The earlier claim that the project was almost done was too optimistic. Performance and evidence completion remained substantial. Documentation makes the remaining state reviewable; it does not turn it into completed work.

## 10. Publication and safe resumption

The user requested a public repository named `price-action-strategies` and GitHub Pages for the HTML documents. Pages hosts static documentation only. It cannot run the Python API, SQLite worker or private trading-research app. No credentials, downloaded price caches, original user database, raw trace archives, source video or full video transcript should be published.

The publication snapshot scrubs personal names, machine/home paths, device identifiers and live credential values. Email addresses are permitted by the user's instruction. Public source attribution and third-party license notices remain. A fresh repository has no earlier commits to conceal private data; inspect the staged tree and reachable history before pushing. Public Git metadata uses a generic author name. Privacy-derived historical receipts retain their relationship to local originals explicitly.

Read the HTML handoff, PAUSE_STATE.json, PLAN.md, VERIFICATION_PLAN.md, RULEBOOK.md and the missing-fixture evidence before resuming. Recheck actual processes; old session handles and PIDs are historical. Do not automatically launch the preserved coordinators. The goal remains paused until the user explicitly resumes it.
