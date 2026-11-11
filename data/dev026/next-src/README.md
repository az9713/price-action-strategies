# Price Action Research Lab

Private Windows localhost application inspired by [AI Pathways' source video](https://www.youtube.com/watch?v=z97PnFIPoFg). US stocks and ETFs, free historical Alpaca SIP data, explicit long/short execution and financing assumptions. No live-order capability or paid runtime AI dependency.

**Development build. Final conformance is not verified.** Read `STATUS.md`, `PLAN.md`, `RULEBOOK.md` and `VERIFICATION_PLAN.md` before interpreting any research. The host's ten strategy families are implemented as documented numerical adaptations; identical host trades or reported futures profits are not claimed.

## Install and launch

Supported baseline: Python 3.13 and Node 22.22. Run from this folder in PowerShell:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Set-Location frontend
npm ci --ignore-scripts
npm run build
Set-Location ..
.\start.ps1
```

Open `http://127.0.0.1:8765`. The service binds loopback and serves the frontend and API on the same origin. An independent spawned worker process executes durable jobs. Closing the browser does not cancel a job. Ctrl+C stops the service; work is checkpointed or recovered from an expired lease on restart. Use `-Port 8766` if the default port is occupied.

Keep `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` in the local `.env`. They are used by the backend only. The UI reports configuration status without exposing values. Credentials, downloaded data and local job records are excluded from version control. No key is needed to inspect cached results or use synthetic imports offline.

## Workflow

1. **Data:** download or import raw one-minute OHLCV; inspect session completeness and corporate-action issues. Missing prices are never filled. Create an explicitly audited subset when needed. Previewing prices records the dates as viewed.
2. **Strategies:** choose a family and numerical parameters, then save an immutable rule version. Invalid combinations are rejected by the backend.
3. **Experiments:** select dates and sizing/cost assumptions. Start with a single configuration, or select distinct saved rules to run together in one shared-capital portfolio. Portfolio orders compete for the same cash, gross exposure and entry participation; results are not sums of independently funded runs. Search sampling is seeded, unique, and different from the host's undisclosed grid. Large-search operating limits remain to be measured.
4. **Results:** inspect daily marked equity, trades, drawdown, uncertainty, concentration and undefined-statistic explanations. Synthetic results retain their label.
5. **Trade inspector:** inspect saved candles, signal availability, fills, fees, borrowing and cash movements. Use Fit all trade levels to see entry/exit/stop/target together, or switch to the price-only view. Portfolio trades load their own rule/timeframe. Saved final-test inspection does not reopen raw protected data.
6. **Validation:** register untouched final dates before exploring them; freeze the rules and screen discovery/validation windows. No-candidate is a valid outcome. Final dates are consumed before reading. Copies of the data do not reset this record.
7. **Reports:** export full JSON evidence and trade CSV. Offline HTML presentation is available; broader statistical workflows and full release verification remain unfinished.

CSV/Parquet imports need symbol, timestamp, open, high, low, close, volume. Timestamps are minute opens with explicit offset/UTC; naive timestamps require a timezone. Imports accept raw tradable prices only. Historical imports require a declaration of complete split/dividend metadata; this is a user attestation, not independent corroboration. Corporate-action JSON records use `symbol`, `ex_date`, `kind` (`split`/`dividend`), positive `value` (new/old share ratio or cash/share), and optional `pay_date`.

January 2022 prototype dates were already viewed. The six-symbol original has one missing DIA minute; its five-symbol child is separately audited. Neither is an untouched final test. Final windows must use genuinely new evidence. Futures, forex and crypto remain later market options.

## Checks and receipts

```powershell
.\.venv\Scripts\python.exe verification/check_evidence.py plan
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe verification/record_check.py --label component-check -- .venv/Scripts/python.exe -m pytest -q
```

`verification/receipts/` retains actual commands, hashes and logs. Implementation checks do not automatically certify product acceptance cases. The release checker deliberately fails until every mandatory requirement and case has current evidence. Financial success does not substitute for software correctness.

Shared-capital experiments accept one to64 unique rules; this is an input bound, not a measured maximum-history/runtime guarantee. Portfolio-level frozen final studies and advanced statistical workflows remain unfinished. Versioned news calendars are implemented under continuing verification.

The current verification catalog has83 requirements and422 mandatory cases. See [the evidence index](verification/evidence-index.md) and [current status](STATUS.md) for actual check scopes and retained failures. The independent numerical coverage gate is verification/check_numerical_coverage.py; it checks95% statement/90% branch coverage for config,data,signals,engine,metrics,service,benchmarks,controls,behavior,ablations,trials,news,borrow,sensitivity and research from a hashed executed coverage receipt. Provider/recovery/privacy and UI acceptance remain additional gates. A passing pytest count alone is insufficient.

Cash and buy-and-hold comparisons are available on Validation. Select audited data/dates and account/cost assumptions, or use the open strategy’s exact inputs, then run and reopen a saved benchmark job. JSON includes the passive cash/action ledger and actual allocations; CSV includes its executed trades. The passive basket has no stop/rebalancing and is not assumed to match strategy risk or exposure. A displayed strategy difference requires identical saved dataset/manifest, dates, numerical subject, costs and account settings. Matched random-entry accounts are available on Validation with exact matched/unmatched denominators, saved surrogate trades and hash-verified per-account checkpoints. Choose the source rule and2–200 random accounts (default20). This retrospective conditional comparison is not a standalone tradable strategy. Behavior and paired ablation studies are available under continuing verification. Complete source-funnel sampling,10,000 matched twin sets and search-aware reporting remain unfinished.


Price behavior diagnostics are available on Validation after selecting saved audited data and dates. The default request uses20 shifted stand-ins and five charts. The17 diagnostics save source geometry, own shifted visits, complete/censored/unresolved outcomes, matched forward moments and whole-session uncertainty. Inspect chart records and download study JSON, each diagnostic CSV and chart JSON. These are price measurements rather than simulated returns. RULEBOOK0.11 documents the source-video adaptations and exact boundaries. The full declared release remains unverified; consult STATUS.md and verification/evidence-index.md for actual checks and outstanding requirements.

Paired rule comparisons on Validation run a baseline and up to32 distinct one-field alternatives with the same data, dates, costs and account. Inspect every separate account, daily difference and descriptive interval; download study/account JSON and CSV. The research trial ledger records frozen plans, actual attempts, interruptions, saved-work reuse and sampler outcomes. Its selected-job export includes all records beyond the current page; legacy plans are explicitly post-hoc and unverified. These counts are not independent-trial estimates or statistical-significance certificates.

Confirmation/news/run calendar filters use the New York date when a signal becomes known, including next-day confirmation. Setup time and later execution time remain separate. News skip/half requires a complete versioned calendar covering the run. Invalid calendars reject before loading prices, including resumed work.


On Reports, the offline research presenter combines completed saved accounts, passive/random comparisons, behavior tables, paired rule comparisons and supported search summary windows. Add one to sixteen distinct saved sources, then download the self-contained HTML. The current saved account also has direct HTML/provenance links. Open the file offline; arrow keys/Space/PageUp/PageDown navigate, Home/End jump, #N selects a page, M opens sections, R replays and F shows a reserved camera guide. Drag to highlight temporarily. No webcam or network is required. Save provenance inside the file for the full page/fact/source manifest. Undefined results, losses and original denominators remain explicit.

Presenter export reads only integrity-checked saved outputs and does not reopen protected dates. It independently rereads displayed values before building, but does not independently certify the saved trading results. Different saved source fingerprints remain distinct. Explicit source/page/point/byte guards reject oversized or unsupported output without silently removing rows. All422 acceptance cases and the final frozen-release audit remain mandatory. The presenter verification instance uses http://127.0.0.1:8767; the prior8765/8766 services were stopped at the recorded checkpoint. Launch a chosen port with `./start.ps1 -Port 8767`.


Scheduled news calendars are managed on Data. Acquire the free preset from public BLS schedules and scheduled Fed decision dates, or import reviewed CSV with `date,kind,label,known_at`. Explicit dates use YYYY-MM-DD; recorded knowledge times require an ISO timestamp with timezone and at most microsecond precision. Select the immutable version on Experiments or Validation and choose normal/skip/half risk under Strategies → Additional rules and context filters. The calendar coverage must include the entire run or registered study. Existing positions are not forcibly closed.

Official pages retrieved today reconstruct the schedule; their historical advance availability is assumed. Recorded-knowledge imports apply only once the supplied knowledge time is reached; those times remain an input assumption. Synthetic calendars are clearly labeled scenarios. The preset excludes earnings, unscheduled announcements and other releases unless explicitly imported. Calendar source URLs, retrieval times, raw-body hashes, event versions and knowledge assumptions are saved with the job and shown/exported on Reports. Cancel/resume preserves only verified documents committed to that acquisition job; corrupted sources fail without silent replacement.


Changing short borrowing is available under Experiments → Execution costs and short borrowing. Add a named scenario, declare every covered instrument/date, and enter full lending states at explicit UTC minute boundaries. Annual rates in the editor are percentages:10 means10% per year. An unavailable state blocks new shorts; a recall also requires existing shorts to close at the next observed minute opening. A later clearance does not erase a recall on an older loan. Long positions are unaffected. Initial constant borrowing settings apply until an instrument's first event. Import/export validated scenario JSON for reuse; blank rates reject rather than becoming free borrowing.

Every applicable account freezes the entire scenario inside Costs. Invalid or incomplete scope blocks before raw prices and final access. Financing follows piecewise annual rates over calendar seconds including weekends, using the declared365-day convention and known marks. This is a labeled research model; exact broker lending history, locate inventory, collateral and billing are not established. Results, the trade inspector, full JSON and offline presentation expose the saved assumptions/events. Validation also provides a four-rate comparison at0%,3%,10% and30% annually. Each complete account overrides both initial and scheduled rates, retaining availability, recalls and every other input. Original costs remain separately saved; original scenario names/notes remain context. Inspect absolute profit, borrowing charges, complete daily differences, each account and trial records; cancel/resume and download aggregate or account JSON/CSV/offline HTML. Differences are descriptive; no new difference interval or independent-trial count is inferred. Final acceptance of this workflow remains under verification. RULEBOOK0.14/catalog v8 retains all prior cases and declares83 requirements/422 mandatory acceptance cases, with the same120-case strategy matrix.

RULEBOOK0.15 retains the existing422-case inventory and freezes the flat-rate account policy. Small per-share and per-dollar fees in the sensitivity presenter use exact decimal labels so a nonzero fee is not displayed as zero by currency rounding.

## Frozen shared-portfolio studies

On Validation, choose independent rule accounts or one shared-capital portfolio before registering a study. Portfolio mode selects up to64 unique immutable saved rules. Both screening windows execute that entire set in one shared account and apply gates to the joint result; separately selected members and independently reset profits are never recombined. The complete set is either the one candidate or no candidate. The original inputs and candidate event are hash-bound. Final queueing reserves one job identity; cancel/failure resumes that job, and final dates are consumed once before price access. Saved reports identify phase and selection unit, retain all rule-specific charts/attribution and export complete JSON/CSV/offline provenance. The whole workflow remains under verification; all422 final acceptance cases remain binding. Source-video/private-code differences remain those documented in PLAN.md.

Runtime ownership: launch the app in a managed foreground terminal (`./start.ps1 -Port 8767`) and use Ctrl+C to stop it. Worker-enabled instances now require an OS lease on their resolved store; starting another port for the same store must fail clearly. Separate verification stores are explicitly isolated and retired after checks. Multiple PIDs inside one server tree are normal multiprocessing children; do not terminate unrelated Python processes. The lock file alone is not a live-owner signal. D037/runtime-capacity-contract.json defines the actual lifecycle and measured-capacity verification; larger search completion is never inferred from the100/1000 sample.

## Search statistics

D038/RULEBOOK0.18 implements the existing RES-008 diagnostic workflow under unchanged83/422/120 scope. Follow verification/fixtures/search-statistics-contract.json. Freeze effective-trial assumptions and empirical/assumed cross-trial SR dispersion before queueing; calculate from all saved complete daily marked accounts, not selected winners. Default powers-of-ten/count assumptions are sensitivity scenarios, never an independence estimate. Use per-session units, bias-corrected moments and the existing Bailey/Lopez de Prado formula; preserve undefined/null/loss outcomes and single-trial zero benchmark. Keep original profit separate from model scores and explain prior-search/serial-dependence limits. Provide complete saved-only JSON/long CSV/offline projection, actual UI/API/worker/recovery and independent numerical/fact evidence. No DSR score changes candidate/final gates. The source-style sampling/trade-twin/era/replication funnel and larger workloads remain mandatory. Primary source: https://davidhbailey.com/dhbpapers/deflated-sharpe.pdf .


Common search modes are under D039 implementation/verification. Their complete published equity grid and40/40/20 filter-group sample are adaptations of the source video's prompt pages10–12, not a claim to reproduce its private14016 grid or six named presets. Initial discovery gates keep signals/trades/profit/Sharpe separate and do not establish a surviving strategy or unlock final dates. See PLAN.md, RULEBOOK.md and verification/fixtures/common-sampling-contract.json; full project verification remains active.


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
