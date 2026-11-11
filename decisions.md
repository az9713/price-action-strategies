# Implementation decisions

## D-001 — Evidence-backed conformance is mandatory

Date: 2026-11-07. Basis: the user's request for exhaustive verification and receipts throughout implementation and final acceptance.

Adopt [VERIFICATION_PLAN.md](VERIFICATION_PLAN.md), the versioned requirement/case catalog and the receipt schema as binding parts of [PLAN.md](PLAN.md). The initial inventory contains 80 mandatory requirements and 330 acceptance cases, including all 120 strategy/timeframe/direction combinations. Initial product status is `not_run`; neither the source screenshots nor the bounded Alpaca probe satisfies application acceptance.

Maintain plan → requirement → implementation → test → executed receipt → artifact traceability. Preserve failures and require current evidence after relevant changes. Use independent expected values and reference accounting, actual browser journeys and explicit unsupported/unknown outcomes. Do not equate profitability or a comparative improvement with correctness. The final release remains blocked by any unmet mandatory use case.

This adds verification requirements without reducing the previously authorized application scope. Routine implementation decisions and fixes remain authorized. Material scope reductions or weaker acceptance criteria cannot be adopted merely to obtain a passing release.

Future entries must record the source/user requirement, affected IDs, ambiguity, chosen behavior, reason and verification consequences. Source-inspired choices should cite the relevant video timestamp or screenshot rather than suggesting undisclosed host code was inspected.

## D-002 — Explicit causal equity rule contract

Date: 2026-11-07. Affects DATA, RULE, STR, EXEC and ACCT requirements. Source: the ten setup cards and technical prompt pages, linked from PLAN.md.

`RULEBOOK.md` version 0.1 specifies unique symmetric pivots confirmed after k bars, forward normalization using only effective past splits, session-close information timing, distinct ten-family event definitions and an equity execution/accounting contract. This resolves source ambiguities without claiming identical host trades. Nonapplicable nondefault dials are rejected. The same-close alternate is explicitly synthetic; a limit entry receives no target credit in its ambiguous entry minute. Planned risk reserves modeled adverse stop execution and both commissions. New orders use whole shares; corporate-action fractional quantities remain until exit.

The contract is under verification, not a frozen/final accepted release. Component fixture failures and fixes are retained in `verification/defects.json`. Changes must preserve causal-prefix and independent cash-ledger checks, with expanded family and interaction fixtures before V3 acceptance.

## D-003 — Preserve missing historical bars and audit selections

Date: 2026-11-07. Affects DATA-005, DATA-006, DATA-010 and product eligibility.

The January 2022 six-symbol SIP download has one absent DIA minute at 2022-01-03T19:28:00Z. Preserve the original ineligible dataset and do not invent a bar. An explicitly selected five-symbol child (SPY, QQQ, IWM, AAPL, MSFT) is separately reaudited and retains its parent ID. This is an instrument selection, not a repaired six-symbol history. Ordinary runs require the selected dataset's full declared session audit to pass and corporate-action issues to be absent.

## D-004 — Record actual implementation checks without acceptance inflation

Date: 2026-11-07. `verification/record_check.py` preserves real command logs, exit status, subject/data hashes, output artifacts and schema-validated **implementation** receipts. Unit/component passes are reported by the test runner but do not auto-certify the 330 broader product acceptance cases. The final release gate continues to require coherent verification receipts, completed mappings and full conformance evidence.

## D-005 — Protect final dates across product read routes and preserve exposure

Date: 2026-11-07. Affects holdout, job recovery, data access and provenance requirements. A final window is protected by instrument and date, including copied datasets. Preview, experiment, search, selection and CLI analysis share the access guard. Registration rejects previously viewed dates; existing provider probes and prototype analysis dates are migrated into the viewed-date registry. Acquisition/audit metadata alone do not make a date window viewed through the product. This is a research-workflow boundary, not protection against the owner reading local files or already knowing market history.

Freeze engine and dataset fingerprints plus the candidate list. Consume final evidence transactionally **before** first analytical access, including a failed or canceled evaluation. Resuming the same job is a labeled continuation; it does not create new untouched evidence. Final trade inspection uses saved output charts. No-candidate screening is a valid terminal outcome. The current minimum-trade/positive-profit/Sharpe gates are an initial implementation; random controls and search-aware corrections remain required work rather than implied certification.

## D-006 — Dedicated worker process and content-bound recovery

Date: 2026-11-07. The HTTP service launches a spawned numerical worker process, keeping heavy calculations outside the request process as PLAN.md requires. Leases, heartbeat, checkpoint hashes and input/code identities protect recovery. Graceful shutdown returns work to the queue; a parent-liveness watcher stops orphan workers. A forced termination can leave a lease that must expire before recovery. Never mark completion without a saved result and recorded hash. Corrupt checkpoints and modified results fail explicitly.

Source identity must describe code loaded by the process. Rehashing edited files after execution can incorrectly label an old process with new source. Cache its startup fingerprint, reject new research if disk source changes, and restart after edits. Evidence recording now captures source hashes before commands and flags changes during commands. Earlier implementation receipts cannot serve as final coherent release certificates.

## D-007 — Implement the source-inspired UI with real persisted outputs

Date: 2026-11-07. The seven-section React/TypeScript application uses the source's navy/cyan/amber direction, an explicit research chain, system fonts for offline operation and actual API/worker/storage outputs. `verification/frontend-design.md` records the design choices and critique. Empty financial screens contain no invented results; imported synthetic data remain labeled. TradingView chart attribution remains enabled. A passing TypeScript/Vite build does not satisfy browser-flow acceptance. Advanced research controls and offline HTML presentation remain visibly unfinished until implemented and verified.

## D-008 — Separate functional completion from measured performance

Date: 2026-11-07. Affects ENV-002, UI journeys, PERF-001 and PERF-002. Early diagnostic tests used arbitrary combined deadlines that were not the plan's operating envelope. A cold spawned-worker startup was measured at 37.69 seconds, followed by a three-session job at 4.38 seconds. A real five-symbol/month browser job later took 96.19 seconds, exceeding the browser harness's initial 60-second completion wait; it completed with valid saved evidence and no duplicate claim. Retain that failed run (`20261108T043845619606Z-chart-and-real-browser-regression`) as a latency concern.

Measure startup separately; retain a 20-second diagnostic for the tiny execution fixture after readiness. The browser functional journey now waits at most 180 seconds for background work within a 240-second test, records actual job elapsed time, and explicitly does **not** certify performance. This harness clarification does not change the plan's resource, responsiveness or staged 100/1,000/10,000/100,000 gates; they remain unmet until measured and accepted on a defined envelope. Do not erase the timeout or advertise the present engine as suitable for large searches. Optimization and responsiveness measurements remain necessary.

## D-009 — Audits must not expose protected financial action details

Date: 2026-11-07. An API audit initially returned the full local manifest, including future dividend amounts and inherited raw provider action payloads. Ordinary audit and subset responses now return quality/provenance metadata and a full-manifest fingerprint without that financial payload. The immutable manifest remains intact locally; the workflow guard is not protection against its owner reading files. A regression fixture protects a future distribution amount across both ordinary audit and discovery-only selection routes.

## D-010 — Independent execution reference and decimal boundaries

Date: 2026-11-08 UTC. Affects EXEC-001–006 and ACCT-001–006. RULEBOOK.md is now version0.4. The independent reference in verification/reference_execution.py uses standard-library Decimal arithmetic, its own event clock/ledger and exhaustive feasible-share enumeration; it imports no production module, NumPy or pandas. It consumes primitive supplied signals. Independently authored family geometry separately tests detector outputs; supplied-signal execution parity does not independently certify all detector options.

Authored expected quantities/events exposed production errors in binary tick/participation comparisons, fee-aware sizing, pending-order priority, same-close marks, borrow timing and a limit fill opening through its hard stop. Correct those mechanics rather than changing expected outputs. Buy limits round down, sell limits up; exact trade-through thresholds use decimal comparisons. Size is the largest feasible whole-share quantity. Older orders precede newer ones; ties resolve by symbol/configuration/signal identity. Current closing marks determine same-close capital. Borrow includes the held final minute and accrues on the last known notional between observations. A conservatively filled limit opening past its stop exits immediately at that opening stop execution. See the versioned rulebook and frozen execution-reference-contract.json.

Retain the first failed reference and decimal-boundary receipts. The reference initially had its own argument-name collision and a test helper used the default Decimal precision; these were corrected without changing the hand-expected JSON values. The bounded random differential has96 saved seeds. The real January2022 five-symbol supplied-signal comparison independently reconciles ledger/trades/daily equity and basic statistics; net profit is333.6822077820252, not the older engine's334.4222236168862. Old reports keep their original identity; the UI flags reports created under another numerical contract. Neither value establishes an investment edge.

## D-011 — Deterministic setup overlaps and independent fixture geometry

Date: 2026-11-08 UTC. Affects STR and RULE requirements. The ten-family matrix has120 positive/mirrored/timeframe cases with hand-specified signal time/level, a matching executed trade, causal-prefix checks, independent execution parity and flat negative controls. It does not exhaust every supported dial. Family-boundary cases additionally distinguish the detector names, first visits, expiry, invalidation and first returns.

RULEBOOK0.4 resolves simultaneous setups using newest creation/anchor; equally new opposing candidates are ambiguous before the direction filter. This avoids bias from iterating long or short candidates first. Same-direction gap existence remains available even when an opposite gap is newer. A level bounce can emit once per qualifying visit. A fair-value-gap strategy cannot require its own gap as an independent confluence setting; reject that nondefault parameter.

The first delayed-demand-expiry fixture accidentally added positive0.02-body candles to a large impulse, creating a newer valid zone. Its failure was a fixture error, not evidence that age2 should admit the old zone. Change the away candles to zero bodies so the independently known original zone has age3 at the return. The expiry rule and expected rejection remain unchanged. The original failure and corrected37-case rerun are preserved. No expected output was copied from production to bless the fixture.

## D-012 — Numerical subjects and actual HTTP body limits

Date: 2026-11-08 UTC. Affects identity, reports and security requirements. A numerical subject includes all backend modules, the full rulebook, generated schema, dependency lock and numerical/service runtime versions. Cache this subject at process import; a saved subject must hash to its name. Reports carry the full numerical contract. The new source-identity fixtures and full component run test rulebook/schema/lock drift and corrupt cached subjects.

BoundedBody counts actual received chunks before JSON or multipart parsing; a false/missing Content-Length cannot bypass the request envelope. Authorization remains outside buffering. Disconnects abort and non-HTTP scopes pass through. This is bounded per-request buffering; global concurrent-request memory and operating budgets still need measured enforcement. No claim of a fully hardened release follows from these component checks.

## D-013 — Browser installation drift is an environment failure

Date: 2026-11-08 UTC. The browser attempt20261108T061033647905Z failed before any product action because the per-user Chrome path disappeared. Chrome exists under Program Files. The test runner now resolves an existing per-user or machine-wide Chrome executable and accepts an explicit PA_BROWSER_EXECUTABLE override. Record the actual browser build with each journey. Retain the failed launch; it provides no product-flow pass. No browser is installed or user browsing profile modified by this repair.

## D-014 — Preserve stale-worker failures and prove current parent-liveness behavior

Date: 2026-11-08 UTC. Affects ENV-002 and JOB recovery requirements. The first current-browser attempt after fixing Chrome passed1920 but failed1280: the queued job was claimed and rejected because its engine identity differed. Read-only Windows process inspection confirmed an orphan from this workspace (PID40092, prior parent51672). Stop only that confirmed project process. Its relationship to the mismatched claim is supported by the subsequent clean two-viewport rerun; no unrelated Python processes were stopped. Keep the failed job, trace, CWD diagnostic and actual termination receipts.

The new actual forced-parent-death test bypasses normal API/Python daemon cleanup. It owns an exact Windows process handle to its child, forcibly terminates that child's parent, and requires the current worker to exit within10 seconds. The run measured0.7012s and passed; normal API spawn/shutdown also passed. This bounds a specific current recovery path and does not establish complete restart/cancel/checkpoint conformance. The browser harness now recognizes failed/canceled terminal jobs promptly and reports their actual error instead of waiting180 seconds for an impossible Completed label.

## D-015 — Detect new source files during evidence execution

Date: 2026-11-08 UTC. The receipt runner already detected edits/deletions to files present at command start. Review found that it did not detect a newly added source file. Re-enumerate the source inventory after execution, record any addition as an incoherent subject, and return status2 for source drift or missing requested artifacts while retaining the actual child command exit code in its receipt. Add the receipt schema itself to the source manifest. Tests must exercise actual recorder execution against an isolated miniature workspace, without modifying this project's source.

Redact JSON-escaped Windows workspace paths as well as plain/forward-slash paths. This improves future diagnostic receipts; historical evidence is preserved with its original hashes. All stage receipts remain implementation-only with no inferred acceptance passes.

## D-016 — Implement portfolios as one shared execution clock

Date:2026-11-08 UTC. Affects ACCT-002, UI experiments/results/trade inspection, research access and JOB recovery requirements. RULEBOOK0.5 adds the portfolio input/report contract. An explicit PortfolioExperiment model freezes one to64 unique configurations; canonical configuration-hash ordering removes input-list allocation bias. All generated signals pass through one existing minute-event account with a signal-to-configuration map, one marked-equity budget and the same costs/limits. No independent-account sum is a portfolio. The input cap is not an advertised tested performance envelope.

Use the common guarded evaluation loader for single and portfolio runs. Store rule identities on signals/trades, full rule-set definitions, shared-account attribution and a chart set per configuration/timeframe. Ordinary portfolio runs cannot access sealed dates; portfolio-level final-study freezing remains unfinished rather than implied by an ordinary job. Cancel/resume must recompute one joint account rather than concatenate separately reset accounts. The frozen synthetic contract independently specifies two simultaneous rules,79 funded shares,125.98 entry,115.97 gap-stop exit and-790.79 shared P&L versus-1581.58 from two separately funded runs. Independent Decimal execution must agree event by event.

The UI adds saved-rule selection and shared-account attribution. It labels daily drawdown explicitly. VIS-001 uses a distinct actual-exit price line and an in-bar marker without floating text; VIS-002 keeps trade-table headers sticky during internal scrolling. Retain prior visual observations and require fresh browser assertions/screenshots before closing those findings.

## D-017 — Share the entry-volume budget and audit it from saved results

Date:2026-11-08 UTC. The new manual portfolio liquidity cases exposed the same omitted shared-resource assumption in both production and reference: each rule could reuse the full prior-volume cap. Agreement between two implementations alone did not detect this; the independent100-volume×0.29=29-shares invariant did. Retain the first result24 failures/5 passes (20261108T064355480334Z-aggregate-entry-liquidity-first). Do not change those expected quantities.

RULEBOOK0.6 assigns entry participation to instrument/reference-minute, across every rule. A same-close and the following opening entry share the same completed volume sample; genuinely new samples reset the allowance, separate instruments have separate allowances, and immediate stop-outs do not replenish consumed entry shares. The production engine uses a bounded sample counter. The independent Decimal reference recomputes consumed volume from its accepted-entry history and still enumerates feasible whole shares independently. Both ledgers now expose the reference sample and budget before/after every accepted entry. Exit liquidity remains the declared bar-model assumption, not an observed historical guarantee. Expanded mirrored next-open/limit/same-close/gap/reset cases must pass before this fix is considered verified.

## D-018 — Expand portfolio acceptance and show all trade levels

Date:2026-11-08 UTC. The original330 mandatory cases are retained. Add ACCT-002-C04–C11 and UI-004-C04, making339 cases across80 requirements. These explicit cases cover the new shared-account workflow and graphical inspection; all begin uncertified until final-subject acceptance execution.

The first portfolio browser run exposed a harness locator timeout: the native select had the correct accessible combobox name but the exact wrapped-label query did not resolve. Preserve that failure and its interrupted second-profile attempt. Use the accessible combobox role/name and bound UI actions to15 seconds; background completion retains its separate180-second diagnostic. The corrected four journeys passed.

Visual review then found that chart autoscaling could leave a distant target outside the pane. Default to fitting all saved entry/exit/stop/target levels, with an explicit price-only toggle, and show raw stop/target values below. Assert actual price-to-coordinate outputs, preserve per-rule bars across the toggle, and capture readable chart-element screenshots as well as full-page context. This changes graphical inspection, not execution data. VIS-001/002/003 require current screenshots and browser assertions before closure.

## D-019 — Measure image geometry and fail numerical coverage independently

Date:2026-11-08 UTC. The first chart-element artifact reader assumed350 CSS pixels implied350 PNG pixels. It failed on real351-pixel images. Installed Playwright1.65 source (Helper.enclosingIntRect in coreBundle.js) encloses fractional document coordinates using floor/ceil with1e-3 epsilon. Record actual CSS rectangles, enforce350 CSS height, and compare exact enclosing PNG dimensions; keep pointer hover text away from saved labels. Preserve the failed reader receipt. Financial tolerances and financial expected values were not changed.

489 backend tests passed under branch instrumentation, but that is not a coverage pass. Add an executable hashed-source/coverage-artifact gate for config,data,signals,engine,metrics and service; service includes numerical attribution/sampling. Keep95% statement/90% branch thresholds and reject stale/tampered/missing evidence. Raw-count boundary, drift and integrity fixtures must pass. The current data/signals/metrics/service gates remain unmet. Do not turn a green test count or a manually formatted coverage table into release certification.

## D-020 — Test release evidence with deliberately incomplete inventories

Date:2026-11-08 UTC. Affects SPEC-002 and final conformance. The user requires exhaustive declared-use-case evidence throughout implementation. Make the per-change evidence cycle and final case-by-case conformance table explicit in VERIFICATION_PLAN.md; correct stale overview wording while retaining all339 mandatory cases and all original requirements.

The first isolated gate suite passed26 cases but failed three expected rejection assertions: omitted, duplicate and unknown requirement mappings could return ready. Preserve receipt20261108T073758032173Z-release-gate-fault-first. The release path previously validated only rows that were present; it now compares the complete mapped-ID inventory with catalog requirements and rejects empty, duplicate or inconsistent catalog definitions. No product behavior or financial tolerance changed.

Use temporary synthetic workspaces for gate tests, never repository product receipts. Exercise actual missing/modified files, invalid receipts, failed commands, stale subjects, code/test/rulebook links and explicit chronological supersession. A green synthetic fixture establishes checker behavior only. The actual release remains incomplete until the full frozen product suite and independent conformance audit pass.

## D-021 — Keep insolvency visible and reproduce primary statistical examples

Date:2026-11-08 UTC. Metrics first-contract run20261108T074245100094Z retained29 failures/9 passes: nonpositive-equity returns, nonfinite assumptions, missing DSR moment entry point and bootstrap validation. RULEBOOK0.7 keeps dollar loss/total return/drawdown, nulls a return with a nonpositive base, and makes Sharpe undefined after nonpositive equity. A later independently authored extreme-finite case also exposed overflow (20261108T075122101861Z); reject arithmetic outside finite numeric range instead of exporting infinity. Tolerances and expected losses were not relaxed.

Read the authors' rendered PDF pages9–10 and freeze their three rounded DSR example probabilities before implementing a moment-level helper. Use independent stdlib NormalDist and sample-moment estimators as additional oracles. Trial dispersion is converted from annual to observation units explicitly; raw trial count is not automatically effective independence. Invalid assumptions yield null. Bootstrap batches preserve the original seeded stream and circular block contract while bounding intermediate arrays.

## D-022 — Add a separate guarded passive account with actual allocations

Date:2026-11-08 UTC. Implements part of MET-003 and research comparisons. Cash and buy-and-hold are separate same-capital/date books, not fictitious stop-based strategy signals. RULEBOOK0.7 defines one prior-volume entry attempt, equal initial target weights, actual post-cost entry constraints, no rebalancing, splits/distributions/receivables and final selling costs. Explain that passive risk/exposure need not match the active strategy. Reject incompatible inputs rather than displaying an unqualified strategy delta. Ordinary benchmark reads use the existing holdout guard.

The first benchmark contract run20261108T074619885437Z failed because the feature was absent. The first implemented run passed12 and failed one test harness call: httpx Headers.update takes a mapping, not keyword headers. Correct that call without changing the expected API behavior. Retain both failures and require service/worker/API/cancel/reopen/actual-browser/export evidence before acceptance.

Catalog version3 adds six explicit cases while retaining all339 prior definitions. Review found build_catalog.py had not retained the nine version2 additions; fix the generator from the existing normative case definitions and test complete regeneration in isolation so a later rebuild cannot silently remove scope. Final verification remains open; no component receipt is promoted to release acceptance.

## D-023 — Conditional controls keep matching and execution denominators explicit

Date:2026-11-08 UTC. Source prompt page8 actually specifies20 random bars per event, same chart/direction/30-minute clock bucket. RULEBOOK0.8 adds equity instrument/duration and fixed prior-ATR/close bands, avoiding future-fitted quantiles. This is a documented adaptation. It is a retrospective conditional randomization: source ATR-relative geometry is transplanted to each candidate's own completed close/prior ATR. It is not described as an independently executable online strategy. Future outcomes never enter matching or edge ranking.

Freeze a canonical maximum-cardinality source subset before random replicas, then require distinct matched moments for exactly that subset in every account. Save full-real context separately; never compare a larger real sample with a smaller random sample. Stable SHA streams depend on seed/config/source/replica/candidate identities, not run order or total requested replicas. Independent brute-force small graphs and stdlib hash examples must check this behavior. Use the same actual execution engine/cost/account policy, while independent Decimal supplied-signal execution checks every synthetic account.

The initial absent-feature receipt20261108T081622705818Z retained18 failures/3 errors. The first implementation retained three harness failures: test dictionaries changed unused helper argument names, and create_app was not imported. Correct fixture construction/imports without changing expected no-match/API outcomes. A newly authored subject assertion then exposed a real report bug: configuration JSON was stored as numerical_contract instead of the full frozen core subject (20261108T082021558850Z). Preserve the failed assertion and fix metadata. A later negative suite exposed aggregate trade-CSV500 and zero-weight matching (20261108T082734096743Z); reject ambiguous aggregate CSV with an account-selection error and mark nonpositive source weight invalid.

The39-test run20261108T082421656550Z passed tests but its --cov path named a file rather than an importable module, so no coverage was collected. It is not coverage evidence. The corrected instrumented run20261108T082618208779Z measured100% statements/89.29% branches, below the required branch threshold. Add meaningful empty/incomplete/cancellation boundaries and keep the threshold unchanged. Checkpoint each complete account with a persisted hash; recompute untrusted orphans, reject corruption and never publish incomplete final output. Add six mandatory cases without removing prior scope.


## D024 — Behavior lifetime, censoring and descriptive comparisons (2026-11-08 UTC)

RES-010; RULEBOOK0.9. Source: prompt_page_08.png and prompt_page_09.png, from https://www.youtube.com/watch?v=z97PnFIPoFg. Implement all17 visible diagnostics, with stock/ETF marginals replacing NQ/ES verdicts. Explicit equity adaptations: own shifted visits instead of copying real timestamps; touch-close ordering and full-horizon eligibility; frozen birth offsets and permanent birth invalidation; separate primary/resolved-only denominators; whole-session bootstrap requires at least two sessions and2000 valid draws; price measurements never imply executed returns. Preserve every original351 case and add27 detailed behavior cases. Retain first failures and regressions; current passes remain implementation evidence, not final certification.


## D025 - Preserve UTF-8 and the original catalog serialization (2026-11-08 UTC)

The combined ten-flow browser run passed eight and failed both portfolio labels. A default Windows cp1252 read during this implementation had corrupted the main UI Unicode text and the preexisting rulebook/decision prose. Restore exactly that encoding layer using explicit UTF-8 I/O. The original rulebook prefix is restored (apart from its declared0.9 version); no detector/order/accounting algorithm changes. A new engine fingerprint and fresh verification are required because RULEBOOK.md is content-bound. Retain the original exact portfolio assertion and failed traces.

An additional catalog-preservation oracle initially mismatched the prior351 physical fingerprint because it serialized LF while the recorded Windows catalog used CRLF. Correct the oracle to the recorded original CRLF/no-final-newline format, keeping the original da886c4b84a8f42ab68c34ec838d468188cefb7a6c955984e6656fff9499c86b expectation. That exact digest matches: all prior351 requirement/case contents remain unchanged. This is an evidence-measurement correction, not a change to the acceptance criteria.


## D026 - One-rule account comparisons and complete trial accounting (2026-11-08 UTC)

Source: newly inspected prompt pages10–13, particularly page12's everything-else-equal rule comparisons. Implement independent accounts with only one changed public Strategy field, paired on identical complete daily calendars rather than trade IDs. Use the existing dollar bootstrap policy and preserve zero/negative/no-trade outcomes. The immutable ledger distinguishes planned occurrences, executed attempts, retries and independently meaningful hypotheses; role-specific counts and legacy post-hoc provenance stay explicit. Add12 ablation and seven registry acceptance cases while preserving every previous378 case. The source10000-twin-set funnel is a remaining gap; current20-account studies cannot represent its acceptance gate. No additional domain preference or approval is required for this authorized implementation.


## D027 - Honest short-block uncertainty and streamed ledger snapshots (2026-11-08 UTC)

Before historical ablation acceptance, a three-session fixture exposed a mechanically zero-width interval: a circular block spanning the entire sample always has its full-sample total. Keep the exact dollar difference but require more than one five-session block (at least six sessions), plus executed trades in both accounts, before reporting ablation uncertainty. This strengthens the initial minimum; the raw block sampler and older general-call mathematical tests are unchanged. It is a minimum against this artifact, not a claim of adequate statistical power. Retain the first failing receipt and independent six-session quantile expectations.

A separate cross-thread snapshot test reproduced SQLite ProgrammingError during streamed exports. The installed Starlette iterator uses sequential AnyIO thread-pool next() calls. Use a private query-only export connection allowing sequential thread handoff, while ordinary write connections remain thread-bound. Preserve one read transaction despite concurrent job writes. Primary reference: https://docs.python.org/3.13/library/sqlite3.html#sqlite3.connect (check_same_thread). Source inspection and a deterministic actual two-thread counterexample are recorded; no dependency was added.


## D028 - Confirmation-day filters and discriminating selector acceptance (2026-11-08 UTC)

RULEBOOK0.11. The authored Monday-setup/Tuesday-confirmation cases reproduce10 failures: news skip/half incorrectly uses Monday and the3-session run filter excludes an extra known close. Use the New York date when the signal becomes known. The execution date remains a separate clock. Preserve the original setup timestamp/identity and all other eligibility/size semantics. No versioned-calendar acquisition/UI claim follows from selector tests with a supplied date set.

Freeze confirmation/filter-contract.json before the implementation fix. Injected completed-context tables independently isolate all six confirmation modes, every1–24 waiting window, mirrored directions, strict/equal wick/body/level boundaries, trend availability, DST/open-session boundaries,3/5 prior sessions, gap direction and fresh flips. Real minute/detector/daily-hourly fixtures and independent Decimal account execution supplement that unit layer. They do not certify detector completeness or all compatible dial pairs. Existing RULE-003/RULE-004/STR-011/STR-012 cases remain mandatory; catalog stays82/397. The first wrapper had a target versus target_swing schema mistake; correct that field only, preserve its receipt, and isolate the10 genuine calendar failures before production changes.


## D029 - Early control validation and the authoritative study-job guard (2026-11-08 UTC)

The data/service boundary run passes40 tests and exposes two genuine control-context validation-order failures: unsupported news scenarios reach the input loader before rejection. Validate the complete strategy and unsupported news contract before any price loading. This is consistent with existing public request rejection and does not implement a versioned news calendar.

The same run's other two failures are verifier error-type assumptions. Inspection and execution prove Store.create_job already checks all active study jobs transactionally, without the latest500 history bound. Preserve that guard. Test both the visible service precheck (ResearchError) and the authoritative all-history store refusal (StateError), then assert exactly one study job exists after rejection. No duplicate was admitted and no new store helper is needed. Keep the first receipt, malformed-input/integrity fixtures and corrected counter checks.


## D030 - Private raw evidence and derived review artifacts (2026-11-08 UTC)

D-PRIVACY-001 exposed captured internal session tokens. Preserve raw captures privately before recording; derive deterministic sanitized review copies, retain source/result hashes and actual child status, and reject unsupported archives or unsafe publication. No .env discovery/read/hash is used. Authored faults, real successful/failed captures and an independent known-session-value scan support this bounded policy; installed viewer playback and complete historical migration remain required. Secret recognition is scoped to controlled credential contexts, not arbitrary unknown text/images.

## D031 - Saved-output offline presenter (2026-11-08 UTC)

RULEBOOK0.12 adds the output contract from research/screenshots/prompt_page_15.png and prompt_page_16.png, under existing RPT-001/RPT-002/RPT-003. No trading formula changes. Use integrity-checked saved result/part JSON only. Project explicit aggregate/daily findings with per-cell source hashes/paths and a separate Decimal provenance/format reader before writing self-contained HTML. All behavior rows are retained in six-row finding groups, rather than selecting attractive marginal results. Combined sources retain distinct numerical subjects and are not implicitly comparable. Bounds and unsupported outputs reject explicitly. No host profit, hidden preset or survival label is invented.

Retain first authored missing-module failures, the corrected HTML-entity CSP verifier assertion, real source-selection/Windows UTF-8 diagnostic failure and SVG glyph-overhang layout counterexample. Fix the glyph margin; keep half-logical-pixel layout tolerance consistent, while checking the camera guide computed CSS width exactly. This replaces a verifier assertion tighter than browser subpixel geometry, not a financial tolerance. Actual every-page offline screenshots and controls must pass before presenter completion is claimed.


D031 regression follow-up: the first complete1135-test baseline retained1132 passes and three failures. Presenter model insertion accidentally moved StrategySave.parent_id; restore it to the owning model and retain existing save/parent and bounded-body tests. Update the Unicode/version assertion to the explicitly adopted0.12 header. The next actual browser run found JSON.stringify normalizes negative zero in downloaded provenance; download the original embedded manifest JSON text instead, preserving parsed signed-zero values. No financial expectation or tolerance changes.

The historical trace conversion depends only on unchanged verification/trace_privacy.py and its frozen policy. Its broad recorder inventory may become incoherent while these unrelated application fixes proceed. Keep that receipt and its original subject explicit; do not promote it to acceptance. Re-audit all derived archives, original hashes, known-session absence and the unchanged transform/policy hashes in a fresh current-subject receipt afterward. No originals or prior receipts are rewritten.


## D032 - Versioned news knowledge and public schedule acquisition (2026-11-08 UTC)

Source news trade/skip/half day filter becomes an auditable calendar workflow under RULEBOOK0.13 and DATA-011. BLS https://www.bls.gov/schedule/2022/01_sched.htm shows jobs Jan7/CPI Jan12; Fed https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm shows scheduled Jan26 decision. Raw official pages and dated hashes were captured in research/news_probe and byte-identical parser fixtures. They are retrieved-now reconstructions, not historical as-of publication evidence. The BLS January page reports a February25 modification; do not invent advance knowledge from it.

Retrospective calendars explicitly assume advance-known dates. Recorded-knowledge imports require aware known_at and filter only at/after knowledge on the New York decision day. Synthetic scenarios are labeled. Ordinary and shared accounts, random candidates, paired arms and frozen studies share immutable source-bound snapshots; news is eligibility/risk sizing rather than forced exits. Random half-risk controls additionally match the news sizing regime. Public raw news_dates lists are replaced with version IDs; low-level authored set fixtures remain explicitly unversioned mathematical inputs.

Preserve397 prior cases byte-for-byte and add14 calendar cases. New numerical news.py belongs to the same95% statement/90% branch gates. Initial19 absent-module failures and the eight assignment-validator recursion counterexamples are retained; corrected foundations and existing selectors/controls pass395 focused tests. Complete live acquisition, fault/recovery, all job integrations and both desktop browser evidence remain mandatory before any calendar completion claim.


## D033 — News input/recovery and late-result navigation corrections (2026-11-08)

The0.13 boundary is explicit calendar dates and aware recorded knowledge, not Pydantic epoch coercion or silent submicrosecond truncation. Authored counterexamples exposed accepted unsupported inputs and weak source metadata; preserve the initial failing receipt20261108T153302065465Z and subsequent strict validation. The actual resumed-worker counterexample20261108T153621468193Z completed after raw-source corruption; revalidate the immutable calendar and sources before cached download-result reuse. A prior recovery verifier incorrectly used the completed-only public result accessor on a canceled job; its failure is retained separately and corrected to inspect the on-disk checkpoint fixture.

The Reports banner failure was a late openResult redirect overwriting a newer navigation choice, not an absent banner component. Central navigation revisions prevent older asynchronous loads from changing the selected page. Both desktop journeys deliberately hold a real report response until Reports is selected; receipt20261108T153053609073Z passes every scenario and offline page. Earlier failed journeys remain evidence.

Release evidence must reject private captures and unreviewed traces even when hashes and receipt structure are valid. The first new verifier accidentally removed its required execution log, so its negative results were non-discriminating; retain that failure, restore the log, demonstrate the three actual gate bypasses (20261108T153816414203Z), then enforce the same boundary as the recorder, including renamed ZIPs. Positive sanitized-trace and full scoped regressions pass20261108T153839529437Z. No global privacy or final product certification follows from these fixes.

## D034 — Explicit changing borrow states (2026-11-08)

The host uses futures; the equity adaptation already requires changing availability, rates and recalls under ACCT-004. Freeze a complete nested Costs.borrow_scenario with NY date/symbol coverage and full-state aware minute events. Initial state uses existing constant costs. Availability blocks new attempts; recalls latch on existing loans and exit at the next observed opening even after later clearance. Recall market exits precede ordinary gap stops; interest continues until actual exit. Piecewise rates use365 calendar days and known marks, preserving action ordering and tolerances. This is not exact Alpaca lending/billing: current official documentation describes360-day HTB fees and changing asset borrow_status. Sources and validation are frozen in borrow-scenario-contract.json. No paid data or live orders are introduced. Preserve the recorded physical411-case catalog and add eleven cases without removing scope. Sensitivity remains separate complete accounts at0/3/10/30 percent.

## D035 — Four complete flat-rate borrowing counterfactuals (2026-11-08)

Complete the already-required borrowing sensitivity workflow without changing the422-case inventory. Fixed annual0/3/10/30 percent replaces both initial and event rates, while original Costs/hash and every non-rate input remain frozen. This policy is shown explicitly, including retained original scenario names/notes. Execute four full accounts: changed financing can alter later integer sizing and total returns, so scaling saved P&L is invalid. A pre-authored capital10050/short50-share/next-long50-versus49-share fixture discriminates this behavior. Compare complete daily dollar outcomes against zero rate, preserving absolute profits and no-short/empty/loss states. Difference tables are descriptive, without new significance or intervals; account-level uncertainty remains separate. Distinct trial-role identities represent complete Strategy-plus-Costs scenarios, not independent statistical hypotheses. Verification, durability, pre-price/protected-data guards and UI/export scope are frozen in borrow-sensitivity-contract.json. Source video attribution and all broader final requirements remain unchanged.

## D036 — One frozen shared portfolio is the selection unit (2026-11-08)

Add explicit Study.study_mode with independent default and portfolio alternative. One portfolio contains one to64 unique complete rules, sorted by identity before freezing. Screen that same shared-capital account separately in discovery and validation, and either freeze the entire set as one candidate or record no candidate. Never add independently reset profits or recombine individually selected winners after inspecting validation. Final consumes its dates once for the unchanged set and account assumptions. Portfolio trial-role counts describe joint accounts, not independent member hypotheses. Registration/candidate events bind inputs before queued work, reuse and final access. Existing study guards and saved part formats extend to portfolio-shaped configurations, with actual phase/source identities and saved per-rule charts. This equity extension is not established as a host feature. The existing83 requirements/422 cases remain binding; the exact verification contract is portfolio-study-contract.json.

## D037 — OS store ownership and bounded plan-processing overhead (2026-11-08)

Repeated hidden verification servers were left alive; wrapper, HTTP, multiprocessing worker and tracker PIDs made manual cleanup confusing. Retire obsolete instances; use managed foreground sessions and a noninherited OS-held lease per resolved data store, with finally cleanup and parent-owned Ctrl+C. Stale files/PIDs do not establish ownership. One explicit verification store can run separately, with cleanup verified afterward. Actual100/1000 historical capacity and a separately labeled instrumented profile identify repeated full-plan cancellation reads/hashes and per-minute DataFrame construction. Stream the same sorted rows and read/hash only required lifecycle/context data; preserve all numerical events, ownership, pre-price and final/trial/content guards. RULEBOOK0.17 changes operational implementation/provenance, not strategy or accounting formulas. The83/422/120 inventory and all original numerical tolerances stay binding; see runtime-capacity-contract.json.

## D038 — Prespecified DSR sensitivity for complete searches (2026-11-08)

D038/RULEBOOK0.18 implements the existing RES-008 diagnostic workflow under unchanged83/422/120 scope. Follow verification/fixtures/search-statistics-contract.json. Freeze effective-trial assumptions and empirical/assumed cross-trial SR dispersion before queueing; calculate from all saved complete daily marked accounts, not selected winners. Default powers-of-ten/count assumptions are sensitivity scenarios, never an independence estimate. Use per-session units, bias-corrected moments and the existing Bailey/Lopez de Prado formula; preserve undefined/null/loss outcomes and single-trial zero benchmark. Keep original profit separate from model scores and explain prior-search/serial-dependence limits. Provide complete saved-only JSON/long CSV/offline projection, actual UI/API/worker/recovery and independent numerical/fact evidence. No DSR score changes candidate/final gates. The source-style sampling/trade-twin/era/replication funnel and larger workloads remain mandatory. Primary source: https://davidhbailey.com/dhbpapers/deflated-sharpe.pdf .


## D039 — explicit common sampling and initial grading

The video pages10–12 distinguish broad balanced sampling, an explicit common grid and40/40/20 random common-style filters. Implement the common modes with published finite equity variants, actual grid cardinalities and complete frozen proposal history, not the private14016-grid claim. Keep legacy byte-stable choices. Signals and executed trades have separate gates; expose initial discovery flags/denominators and preserve all failed outcomes. No initial pass becomes a frozen candidate or final unlock. Source outcome-qualified400-candidate spread, six unknown named recipes, trade twins, eras, replication and ensembles remain separate mandatory work. See verification/fixtures/common-sampling-contract.json.


## Saved dataset context — D040 / version0.20

Follow verification/fixtures/dataset-context-contract.json. Freeze only dataset ID/manifest hash, declared input kind, source and canonical instruments before queueing/registration; validate before prices. Preserve exact context in new roots, reports, CSVs, UI and offline facts. Distinguish unverified/unknown imports and absent legacy records; never infer from the selected UI dataset or rewrite old outputs. Exclude protected action details, arbitrary metadata and credentials. Verify every analysis path, actual workers, recovery, saved-only exports, corruption-before-read, exact independent CSV/fact parity, formula/XSS escaping and both desktop dataset-switching journeys. Financial formulas, all83 requirements/422 cases/120 matrix cases and host-engine differences remain binding. The numerical coverage gate additionally includes dataset_context.py at unchanged95% statements/90% branches.


D040 follow-up: offline context retains both the entire instrument list as one independently formatted source fact and individual instrument facts. Recognize the explicit historical_market_data import classification; preserve unknown/unverified kinds. Nullable behavior descriptors remain sourced Undefined values. Import parsing/normalization/publication runs outside the HTTP event loop under one per-app import lock, preserving original size/action/date validation and atomic publication. Verify controlled held normalization with an unchanged two-second concurrent-health deadline, equal concurrent imports, and the original browser import deadline; retain first failures. These changes do not alter trading rules, cash/account formulas or final-window policy.


D040 universe preservation: metadata must not impose a new twenty-instrument analysis limit on existing eligible imports. Retain the entire canonical instrument array; the UI pages twenty labels at a time, and offline rendering retains every indexed symbol. The complete-list fact displays the full joined list up to twenty members, otherwise an independently formatted count with indexed-page direction; its raw source value remains the whole array. Existing upload, data-quality and presentation budgets remain unchanged. Verify an actual eligible twenty-one-instrument import, worker account, complete source facts, UI next/previous controls and saved-only export. The first introduced-cap failure is retained.


## Bounded job monitoring — D041 / version0.21

Follow verification/fixtures/job-status-contract.json. Preserve full immutable inputs/trials/results while transactionally caching bounded, fingerprint-bound status projections. Poll/list/control responses read small cached input metadata and live lifecycle columns, not the full plan JSON. Single-job status is at most64KiB; at most500 list records fit2MiB. Explicit on-demand input export and derived-index repair verify original frozen inputs; corrupt cache is visibly unverified, never silently reconstructed from current UI/data. Backfill legacy indexes without rewriting original evidence. Test actual byte/materialization budgets with large plans, complete input exports, cache/original corruption, migration, controls, ownership and browser journeys. No financial formula, universe limit, trial count or final-date policy changes. Study-list/result-read scaling and actual numerical10000/bounded100000 workloads remain mandatory, separately verified. All83 requirements/422 cases/120 matrix cases remain binding.


## Bounded study monitoring and isolated legacy recovery - D042 / version0.22

Follow verification/fixtures/study-status-contract.json. This extends existing RES-001/002/003/004, JOB-001/002/004, UI-003/005, PERF-001/002 and evidence/mutation requirements without changing83 requirements/422 mandatory cases/120 baseline combinations. Small fingerprint-bound study projections support a64KiB detail response and at most500 history records within2MiB; full verified inputs remain explicit on-demand downloads. Polling and protected-scope checks must not read/decode raw studies.spec. Preserve the exact instrument/date intersection, live lifecycle and permitted final-job conditions in a transactional snapshot; missing/corrupt scope fails closed before prices or viewed-window writes. Cache lifecycle/candidate/reservation projections atomically with original transitions; original registration, candidate and final events remain authority. Never impose a new instrument/configuration/input limit.

Actual current legacy plan reconstruction already streams a SQLite cursor. Preserve that one-plan-at-a-time behavior and add per-job rollback/isolation so unreadable or unreconstructible originals do not abort valid neighbors or startup. Keep original bytes, zero fabricated attempts and honest legacy/unverified provenance; never invent a valid frozen plan. No strategy, accounting, sampling, eligibility or final-date formula changes.

Before implementation, retain authored failing API/SQL-authorizer/corruption/malformed-legacy contracts. Verify10/1000/100000-configuration registrations and complete HTTP downloads separately from numerical throughput;500-record pagination; original/cache tampering; all protected-scope boundaries, copies and concurrent final/lifecycle transitions; original worker screening/final guards and exactly-once continuation; desktop download/control/selection/error screenshots; independent fingerprints/complete exports; critical isolated mutations; full current regression/coverage and one coherent source/evidence checkpoint. Preserve first failures. Large result loading, research-funnel work, numerical scale and final conformance remain separate mandatory work.

Source: https://www.youtube.com/watch?v=z97PnFIPoFg . These are operational improvements around the declared equity adaptation; unavailable private engine/grid/named recipes remain explicit differences.


## Bounded saved-result views and older-job browsing - D043 / version0.23

Follow verification/fixtures/result-materialization-contract.json under the unchanged83 requirements/422 mandatory cases/120 baseline combinations. Add an explicitly derived64KiB root summary, default50/max100 result rows within2MiB, bounded diagnostic pages and selected-part lookup without decoding unrelated root/configuration arrays. Keep complete original result/input/report/statistic/screen exports and original financial values. Missing legacy views expose a verified build-from-original action; absence is not empty evidence.

Use a separate content-addressed SQLite view artifact per original root, anchored by an event, rather than a long main job/lease DB write transaction. Publish new views from the worker's constructed output; verify originals before legacy build/repair. Stream original compressed-root, derived-file and exact input-byte hashes in64KiB chunks in consistent read snapshots; keep canonical frozen-input identity distinct from raw-byte identity. Same-length corruption, bad cache, wrong part/window/job and interrupted publication must fail safely. Do not substitute size/mtime for integrity, rewrite old outputs, change financial rules or impose new input/universe/configuration limits. Preserve worker cancel/resume and existing complete-result/report behavior.

Older-job and result/diagnostic pages need separate state from selected-report identity. Verify stale success/failure, current errors/retry, exact page labels and matching exports. Preserve all existing portfolio/final/data-context/ownership flows. Scope study-history toolbar styling to its own controls. The planned result-index module joins the unchanged95% statement/90% branch gate when implemented.

Before implementation retain authored failing API/materialization/part/corruption contracts. Verify worker publication/recovery and all-row/config/candidate/metric/diagnostic parity against originals; large metadata/part measurements separate from numerical10000/100000; both desktop history/page/inspect/export/keyboard/error flows; independent original/account/fact audit; critical mutations; full current regression/gates and one coherent source/evidence checkpoint. Explicitly retain legacy/null/loss/empty cases and first failures. Remaining research funnel, measured numerical scale and final conformance remain mandatory.

Source video: https://www.youtube.com/watch?v=z97PnFIPoFg . Incremental I/O references: https://docs.python.org/3.13/library/sqlite3.html and https://www.sqlite.org/c3ref/blob_open.html . Owned UTF-8/same-length-corruption capability probe: verification/receipts/20261109T055143679582Z-result-materialization-owned-sqlite-text-stream-and-same-length-integrity-capability-probe.json . No new dependency or market is added by this step.


## Verified job-scoped evaluation cache - D044 / version0.24

Follow [the preimplementation cache contract](verification/fixtures/evaluation-cache-contract.json). The actual one-session1000-account run took155.296s; its profile identifies repeated price preparation and base-candle aggregation. Cache those verified intermediates within one job under128MiB of accounted retained bytes, with eviction/fallback rather than a new input limit. Preserve current source-byte/manifest/protected-date checks, all configuration-specific calculations, original trial/account authority and cleanup/isolation. Context/detector/signal/account outcomes are not memoized.

Prove cached/uncached complete-value parity, all six chart clocks, source corruption and protected-date rejection before cache use, bounded eviction and all exit paths before scaling. Compare complete actual100/1000 parts against uncached0.23 results with separately validated source provenance. Actual10000 remains required under the original900s/3GiB/2GiB limits;100000 numerical stress is separate. This implements the existing performance requirements without changing83 requirements/422 cases/120 baseline combinations or any numerical formula. Source: https://www.youtube.com/watch?v=z97PnFIPoFg .

D044 performance follow-up: exact1200 complete account comparisons pass, and cached1000 improves155.296s to119.312s. Reuse one job-local read-only SQLite control connection, querying current cancellation/owner/status every time in autocommit mode. No control state is memoized and no transaction is held between reads. Require live cross-connection changes, raw-payload prohibition, root/thread/nested isolation and every-exit cleanup before repeating the unchanged capacity gates.

D044 actual10000 first attempt stopped at the unchanged900s bound with4663 durable parts; it is a retained failure. An owned16MiB SQLite probe shows control-field reads through the large row scale poorly, while a covering index avoids that read. Default planning and ANALYZE kept the slow plan in this fixture. Add jobs_live_control(id,status,owner,cancel_requested) and bind only the two finalized cancellation/trial-owner SELECTs to that covering plan, using INDEXED BY as a regression requirement after the measured alternatives. Preserve original bytes/rowids/events, all per-configuration checkpoints and existing durability. Require old-store upgrade parity, actual EXPLAIN plans, missing-index fail-closed behavior, the existing live-state guards and a fresh bounded10000 run. See the source/probe receipts in verification/fixtures/evaluation-cache-contract.json.

D047 —2026-11-10 UTC: implement the source research funnel additively. Retain complete all-version original-account family means as descriptive research aggregation, separate from executable shared-capital portfolios. Own and checkpoint a saved analysis without new prices/signals/finance; preserve all source/computation/publication authority and complete exports. Freeze five development axes and two all-version/two-instrument final arms before outcomes. The old basic Study path cannot unlock a funnel through its candidate-only final. Equity replication, additional chronological validation and conservative union scope are explicit adaptations; private-engine/preset/stability gaps stay visible. Preserve83/422/120, original failures, all unchanged coverage/resource thresholds, isolated browser ownership and final conformance. Current family/registration receipts are component evidence only.
