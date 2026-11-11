"""Generate the planning inventory, never test outcomes or passing receipts."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parent
# id, requirement, verification method, discriminating checks with expected behavior
ROWS = [
('SPEC-001','Source attribution and declared differences','document + browser',[
 'Video title, URL and screenshot references resolve; source claims are attributed',
 'Source rules versus equity adaptations are distinguished in rulebook and UI',
 'Undisclosed presets and original futures results are not represented as reproduced']),
('SPEC-002','Committed scope and plan conformance','document + static inventory',[
 'Every mandatory plan behavior maps to a requirement, code and executed acceptance case',
 'Optional/deferred markets and features are not advertised as implemented',
 'New behavior or material deviation updates decisions, cases and scope before acceptance']),
('ENV-001','Clean locked installation','clean environment integration',[
 'Supported Windows/Python/Node install from dependency locks completes without undocumented global packages',
 'Build and test commands preserve actual exit codes and report missing/incompatible prerequisites']),
('ENV-002','Local launch and lifecycle','process + browser',[
 'One documented launch command serves the real frontend/API/worker on loopback',
 'Occupied port produces a clear recoverable error without killing unrelated processes',
 'Shutdown/restart cleans up owned processes and preserves saved work']),
('ENV-003','Offline cached operation','network-disabled integration',[
 'Saved datasets, strategies, runs and reports reopen with external network disabled',
 'Uncached provider request fails clearly without presenting a stale cache as a new download']),
('ENV-004','Dependency and license inventory','static + clean build',[
 'Actual shipped packages are pinned and license/attribution notices accompany exports where required',
 'Release manifest identifies supported versions and build hashes']),
('DATA-001','Credentials and free-provider contract','mocked errors + live smoke',[
 'Missing, invalid or revoked key/secret yields a useful redacted error',
 'Authenticated historical SIP query succeeds for all six initial symbols on declared sample dates',
 'Feed refusal is explicit; no silent IEX substitution, trading request or subscription change occurs']),
('DATA-002','Complete multi-symbol pagination','integration + provider fixture',[
 'Follow cursors to exhaustion and return every requested symbol across symbol-sorted pages',
 'Repeated page/cursor and duplicate records cannot duplicate or silently truncate the dataset',
 'Empty, unavailable and unsupported symbols retain explicit separate outcomes']),
('DATA-003','Retry, interruption and ingestion recovery','fault injection',[
 '429 honors bounded backoff/retry policy and timeout/5xx errors retain meaningful state',
 'Interrupted download resumes or restarts idempotently with identical accepted rows and no false completion',
 'Cancellation preserves a labeled partial download that cannot be used as a complete audited dataset']),
('DATA-004','CSV and Parquet import','integration + malformed fixtures',[
 'Valid CSV/Parquet normalize to identical typed OHLCV and metadata',
 'Empty, malformed, nonfinite, wrong-schema and oversized files are rejected with row/field diagnostics',
 'Ambiguous aliases, units and adjustment state require explicit mapping rather than silent guessing']),
('DATA-005','Price and timestamp integrity','unit + property',[
 'Invalid high/low/open/close relationships, negative volume and nonfinite values are flagged',
 'Unordered, identical-duplicate and conflicting-duplicate timestamps follow distinct documented policies',
 'No repair fabricates a missing price; exclusions and transformations are recorded']),
('DATA-006','Calendar and missing-bar audit','calendar fixtures + full audit',[
 'Expected bars match ordinary sessions, holidays and early closes without false gap alarms',
 'Missing, zero-volume and halted intervals are differentiated and affect eligibility according to policy',
 'Full declared symbol/date-range audit persists counts, boundaries, gaps and blocking issues']),
('DATA-007','Timezone and aggregation','hand-computed fixtures',[
 'UTC/bar-open versus availability timestamps and daylight-saving changes preserve correct ET session dates',
 'All six aggregations have exact expected OHLCV, open/close time and incomplete-length flags',
 'Hourly/4h final remainders and daily bars do not leak across sessions or become available before close']),
('DATA-008','Raw and adjusted representations','corporate-action fixtures + sample check',[
 'Raw/adjusted timestamps align and adjustment factors have a recorded source/version',
 'Forward and reverse splits update prices/quantities exactly once without manufacturing equity',
 'Unknown adjustment state, action mismatch or double adjustment is blocked']),
('DATA-009','Distributions and symbol history','event fixtures + integration',[
 'Distribution entitlement/payment timing and long/short cash-flow signs match the declared contract',
 'Symbol renames preserve entity identity; missing/delisted history is explicit',
 'Fixed-watchlist results do not claim point-in-time stock-universe validity']),
('DATA-010','Immutable datasets and quality gates','storage corruption + API',[
 'Dataset identity binds raw input hash, provider query/feed, calendar, adjustments and normalization version',
 'Changed/corrupt files are detected before execution and cannot silently reuse old results',
 'Blocking audit errors prevent runs and nonblocking limitations appear in reports']),
('RULE-001','Versioned explicit rulebook','schema + worked examples',[
 'Every family, detector, filter, entry/stop/target/exit has a precise definition and version',
 'Pivot ties, trend initialization, clustering/expiry, overlapping-zone and order priorities are resolved before expected fixtures',
 'Configuration JSON round-trips without silently changing defaults or meanings']),
('RULE-002','Causal detectors and information timing','truncation + property',[
 'Future append/truncate or perturbation cannot change prior available pivots, levels, signals or decisions',
 'Confirmed pivot lag and higher-timeframe completion prevent premature availability',
 'Constant/equal-price, short warm-up and irregular-minute histories produce defined stable outcomes']),
('RULE-003','Full dial and constraint inventory','generated parameter coverage',[
 'Every supported value is exercised and serialized with units/defaults',
 'Each valid-combination predicate has accepted/rejected boundary tests through API and UI',
 'No unsupported parameter is accepted and then silently ignored']),
('RULE-004','Confirmation, filters and trigger charts','pairwise + targeted interactions',[
 'Each confirmation and filter changes only its declared eligibility/size/timing behavior on discriminating fixtures',
 'Same/lower trigger mappings and daily/hourly special case use only completed available bars',
 'Trend/session/news/run/choppiness/depth/gap settings and missing-news data have explicit tested policies']),
('STR-001','Level bounce','independent path fixtures',[
 'Positive touch and bounce yields intended side/level/availability; outside-tolerance negative does not',
 'Touch counts, expiry, invalidation and repeated touches respect the rulebook without duplicate orders']),
('STR-002','Breakout','independent path fixtures',[
 'First qualifying completed close through the threshold signals; wick/equality do not unless explicitly configured',
 'Buffer, one-break-per-level, failed break and retest variants match independent expected events']),
('STR-003','Flip zone','independent path fixtures',[
 'Confirmed prior break and valid first retest signal in the correct direction',
 'Wrong-side approach, expired retest, reclamation and invalidated zone do not create stale signals']),
('STR-004','Trend pullback','independent path fixtures',[
 'Established causal trend and qualifying depth/confirmation yield the expected first pullback event',
 'First/later pullback policy and depth equality/bounds reject wrong cases and broken trends']),
('STR-005','Trend line','independent path fixtures',[
 'Declared confirmed anchors, slope and projected-touch calculation match the manual geometry',
 'Line invalidation/expiry and future pivots cannot repaint prior decisions']),
('STR-006','Break-of-structure continuation','independent path fixtures',[
 'Qualifying break agrees with established trend and uses the correct confirmed structure',
 'Equality, wick-only, uninitialized trend, confirmation lag and level reuse follow the contract']),
('STR-007','Change-of-character reversal','independent path fixtures',[
 'First opposite confirmed break yields reversal with correct swing stop and independently calculated 1R target',
 'Mixed/uninitialized trend, no-sweep versus required-sweep and later breaks remain distinguishable']),
('STR-008','Sweep and reclaim','independent path fixtures',[
 'Penetration and reclaim inside the declared window signal only when reclaim is known',
 'Wrong depth, boundary equality, close beyond without reclaim and expired reclaim reject as specified']),
('STR-009','Supply/demand zone','independent path fixtures',[
 'Impulse length/ATR and base boundaries create the expected zone only after confirmation',
 'First/later returns, mitigation/expiry and overlapping zones use deterministic tested priority']),
('STR-010','Fair-value gap','independent path fixtures',[
 'Three-candle gap is known after the third close and has exact expected boundaries',
 'Equality, first mitigation, full fill, expiry and invalidation produce separate expected events']),
('STR-011','Directional and no-signal modes','parameterized integration',[
 'Long-only and short-only exclude the opposite side; both mode accepts both with declared priority',
 'No-signal, one-signal, insufficient warm-up and simultaneous-signal states remain valid and transparent']),
('STR-012','Cross-parameter interactions','generated pairwise + explicit tuples',[
 'Pairwise suite covers every compatible dial-value pair with a saved coverage report',
 'Execute lag/chart/confirmation, limit/expiry/gap, ambiguous-bar/short, session/early-close/timeout interactions',
 'Execute corporate-action/daily-fill, news/risk/exposure and borrow/distribution/overnight interactions']),
('EXEC-001','Market entry timing','hand-computed order paths',[
 'Completed signal fills at next eligible minute open, including next-session daily entry',
 'Signal at last available minute/no next bar produces a defined unfilled outcome',
 'Same-close alternate is explicit and cannot silently become the default']),
('EXEC-002','Limits and targets','hand-computed order paths',[
 'Exact touch versus required trade-through produces the specified distinct fill outcome',
 'Limit/target gap behavior cannot assume undeclared favorable price improvement',
 'Expiry, cancellation and partial/unavailable-liquidity policy are applied without invented fills']),
('EXEC-003','Hard stops and ambiguous bars','mirrored long/short paths',[
 'Normal stop and gap-through-stop use independently specified adverse prices and slippage',
 'Same-minute stop and target resolve stop-first under the selected conservative policy',
 'Entry-minute ambiguity respects event order and does not use pre-entry price movement']),
('EXEC-004','Close, structure and timed exits','mirrored event paths',[
 'Close-based stop waits for the correct trigger close and uses only available information',
 'Structure, 24/96-bar and session-flat exits occur at declared eligible times',
 'Overlapping exit causes and early-close sessions obey deterministic priority']),
('EXEC-005','Order eligibility and exclusivity','API + engine fixtures',[
 'Nonpositive risk, invalid stop/target, missing fill bar and unavailable short borrow reject with reasons',
 'One active position/pending-order policy and signal/re-entry priority are enforced',
 'Direction reversal and end-of-data liquidation follow the declared policy without phantom trades']),
('EXEC-006','Costs and order audit','ledger fixtures',[
 'Commissions, per-side fees, spread and slippage apply to the intended events exactly once',
 'Zero/nonzero and higher-cost fixed-trade scenarios reconcile to independently calculated net outcomes',
 'Reference futures assumptions are labeled and not silently applied as equity defaults']),
('ACCT-001','Whole-share risk sizing','exact-decimal fixtures',[
 'Capital/risk/distance produce expected integer size including minimum/zero/rounding boundaries',
 'Insufficient capital/exposure/borrow rejects or scales according to the explicit contract']),
('ACCT-002','Shared capital and simultaneous positions','multi-symbol event fixtures',[
 'Cash, symbol and total gross exposure constraints hold for every accepted order',
 'Simultaneous strategies allocate deterministically and cannot double-spend shared capital',
 'Independent result sums cannot be represented as a constrained portfolio result']),
('ACCT-003','Event and daily equity reconciliation','independent reference ledger',[
 'Every event/trade/day reconciles starting cash, cash flows, positions, liabilities and equity',
 'Open losses affect daily marked equity/drawdown even without an exit that day',
 'Rounding occurs only at documented events; negative equity and gap losses remain explicit']),
('ACCT-004','Short financing and collateral','exact-decimal calendar fixtures',[
 'Short sale proceeds/collateral cannot create spendable capital outside the declared model',
 'Borrow charges accrue over elapsed calendar days including weekends and changing rates',
 'Unavailable borrow, recall and missing historical availability obey labeled scenario policies']),
('ACCT-005','Corporate-action position accounting','long/short action fixtures',[
 'Forward/reverse split transforms open positions and orders without changing economic value',
 'Long distributions credit and short distributions debit on declared entitlement/payment dates',
 'Split-plus-distribution/overnight gaps reconcile with no duplicate adjustment or cash flow']),
('ACCT-006','Independent engine parity','differential integration',[
 'Simple reference and production engines agree event-by-event on all order/accounting fixtures',
 'Random seeded finite paths match discrete decisions exactly and amounts within frozen tolerances',
 'Reference expected values do not reuse production detector/order/accounting logic']),
('MET-001','Return, Sharpe and undefined statistics','known-series fixtures',[
 'Capital basis, aligned daily returns, risk-free setting and annualization match reference calculations',
 'Zero-variance, no-trade, all-win/all-loss and insufficient-length series yield defined or explicitly undefined outputs',
 'Undefined/infinite values cannot become a favorable numeric badge']),
('MET-002','Drawdown and risk measures','known-equity fixtures',[
 'Intraday/open-position and daily drawdowns follow their labeled sampling conventions',
 'Profit factor, win rate, R, exposure and trade counts use correct denominators and cost inclusion']),
('MET-003','Benchmarks','reference portfolio fixtures',[
 'Cash and buy/hold use consistent dates, initial capital and distributions',
 'Exposure/volatility comparison declares its transformation and cannot compare incompatible units']),
('MET-004','Comparative labels and provenance','negative-profit UI fixtures',[
 'Two losing alternatives can show relative improvement without a profitable-strategy label',
 'Every percentage/curve records market, date range, configuration subset, denominator and units',
 'Rounded display values cannot be reused to recalculate unrounded effects']),
('MET-005','Concentration and paired ablations','known contribution fixtures',[
 'Top days/trades and top-ten-day exclusion match independent recalculation with ties defined',
 'Original and stress results remain distinct and exclusion is not an ex-post executable trading rule',
 'Paired comparisons change only declared settings and expose changed samples/eligibility']),
('RES-001','Experiment and candidate freeze','API + tamper fixtures',[
 'Freeze dates, rules, costs, gates, seeds and candidate hashes before evaluation',
 'Invalid ordering, overlap, warm-up and tampered definitions reject before running',
 'Amendments create versioned records and cannot silently overwrite the original']),
('RES-002','Holdout access protection','all-loader negative integration',[
 'Optimizer, API, preview/chart, cache and report paths cannot read sealed observations before logged unlock',
 'Each access/unlock and final attempt is logged, including aborted/failed attempts',
 'Candidate/hash mismatch prevents final evaluation']),
('RES-003','Consumed-evidence handling','workflow recovery tests',[
 'After access, final observations remain visibly consumed for revisions',
 'New experiment IDs or copied dataset aliases cannot silently relabel consumed observations unseen',
 'Rerun/refusal/recovery policy preserves the original final result and access history']),
('RES-004','Sampling and trial registry','seeded generated fixtures',[
 'Configuration sampling respects constraints, uniqueness and prespecified balance policy',
 'Stable per-configuration streams produce identical choices after sorting, parallelism and restart',
 'All attempts/rejections/failures retain distinct counts and cannot vanish from search history']),
('RES-005','Candidate and family gates','threshold boundary fixtures',[
 'Signal count versus executed trade count, profit and Sharpe thresholds use declared separate denominators',
 'Era and instrument replication are distinct from untouched chronological validation',
 'Zero candidates and insufficient data produce honest terminal results, not fabricated winners']),
('RES-006','Matched random controls','independent seeded fixtures',[
 'Random entries match declared direction, time bucket, risk/target, holding/cost and eligible-date constraints',
 'Random shifted levels obey distance/lifetime restrictions without using future outcomes',
 'All resampling seeds and control counts are saved; control profit sign is not forced to match the host']),
('RES-007','Bootstrap and uncertainty','known-data reference calculations',[
 'Whole-session/block resamples preserve the declared dependence unit and produce reproducible intervals',
 'Unresolved events, low samples, absent controls and degenerate distributions are labeled honestly']),
('RES-008','Search-aware statistics','independent formula/reference fixtures',[
 'Statistic matches published/reference values with declared return distribution and effective-trial assumptions',
 'Sensitivity to trial counts and degenerate inputs is shown; nominal individual thresholds are not global error guarantees']),
('RES-009','No-future-information mutation controls','intentional isolated mutations',[
 'Tests detect injected future pivot availability and deliberate sealed-data access',
 'Future-peeking test fixture cannot be selected or run through production UI/API']),
('JOB-001','Durable job lifecycle','API/DB/worker integration',[
 'Queued/running/canceling/canceled/failed/completed states persist correctly through real work',
 'Incomplete chunks or failed finalization cannot produce a completed job',
 'Progress and error messages identify actual processed work and retained artifacts']),
('JOB-002','Restart and exactly-once effects','fault injection',[
 'Browser closure and API restart preserve worker progress and final results',
 'Worker termination mid-chunk recovers without duplicate trade/result writes',
 'Concurrent workers cannot claim the same chunk and final results match uninterrupted execution']),
('JOB-003','Cancel, resume and rerun','timed workflow tests',[
 'Cancellation is acknowledged within 2 seconds and reaches checkpoint stop within 10 seconds on declared load',
 'Resume returns the identical result and seed stream without stale completed claims',
 'Rerun creates an identifiable new record with original provenance preserved']),
('JOB-004','Atomic persistence and corruption','disk/write failure injection',[
 'Interrupted write/export and insufficient disk produce recoverable explicit state',
 'Corrupt/missing artifacts are detected and cannot be served as verified cached results']),
('UI-001','Data screen journey','real browser E2E',[
 'Download/import real or labeled fixture data and inspect source, coverage, quality and eligibility',
 'Empty, invalid, missing-credential, provider-error and cached-offline states have usable recovery']),
('UI-002','Strategy editing journey','real browser E2E',[
 'Select each real family, change/save dials and inspect exact rule/configuration meaning',
 'Validation errors identify conflicting values; reload preserves the saved configuration']),
('UI-003','Experiment and comparison journey','real browser E2E',[
 'Create single and bounded-search jobs; inspect real progress, cancel/resume and completed comparisons',
 'No-data/no-trade/no-candidate/failure cases remain distinguishable and no action is inert']),
('UI-004','Trade inspector journey','browser + ledger reconciliation',[
 'Select actual long/short trades and align source minute bars, higher-chart availability, entries/exits and annotations',
 'Displayed size, costs, financing, R and P&L reconcile to the saved ledger',
 'Zoom/timezone/render downsampling cannot alter numerical execution or historical decisions']),
('UI-005','Validation and report journey','real browser E2E',[
 'Freeze candidates, inspect access state, run final evaluation and view the correct separate outputs',
 'Export and reopen reports/CSV/JSON from actual stored results and trace displayed values']),
('UI-006','Plain-language accessibility','keyboard + automated/manual inspection',[
 'Keyboard navigation, focus, labels, error announcements and glossary explain the required concepts',
 'Contrast, readable typography, reduced motion and non-color status cues pass documented checks']),
('UI-007','Responsive and visual conformance','actual browser screenshots',[
 '390x844, 1280x720 and 1920x1080 preserve all essential controls and readable charts without clipping',
 'Compare layout/type/palette/labels/spacing to the source-inspired design and record intentional differences',
 'Every shipped control works; source images and placeholder metrics do not substitute for real UI']),
('RPT-001','Numerical provenance and independent reread','export + independent parser',[
 'Every displayed figure resolves to a stored row/field/calculation and matches independent reread',
 'CSV/JSON/report/UI amounts, units, dates and rounding agree with the ledger']),
('RPT-002','Offline presentation export','network-disabled browser E2E',[
 'Self-contained report opens without external assets/network and contains no raw sealed data or credentials',
 'Committed presentation navigation/menu/replay/camera/pointer/highlight controls work and preserve content',
 'Screenshots cover required presenter states at both desktop viewports']),
('RPT-003','Safe exports and retained failures','adversarial export fixtures',[
 'Untrusted text is escaped and spreadsheet-formula injection is neutralized according to export policy',
 'Export filenames/paths cannot traverse outside allowed storage',
 'Original failed verification receipts/logs survive later successful reruns']),
('SEC-001','Local-only access boundary','HTTP integration + process inspection',[
 'Service binds loopback only and untrusted Host/Origin requests fail',
 'Mutation requests require intended same-origin/session protection, including missing-Origin attack cases']),
('SEC-002','Secret and endpoint confinement','static + runtime artifact inspection',[
 'Credentials never enter frontend bundles, console/logs, receipts, exports or screenshots',
 'Provider requests use approved data endpoints and no trading/subscription-management endpoint',
 'Local .env remains ignored and is never archived or hashed into receipt artifacts']),
('SEC-003','Upload and rendering boundaries','adversarial integration',[
 'Path traversal, arbitrary URL imports, code uploads and oversized inputs cannot escape permitted operations',
 'HTML/script payloads in symbols, filenames, configuration names and imported text remain inert']),
('PERF-001','Measured scale and storage','actual benchmark executions',[
 'Execute 100/1000/10000 configurations on frozen declared real discovery data with time/memory/storage receipts',
 'Execute 100000 actual bounded-fixture configurations end-to-end and verify counts/checksums',
 'Report operating envelope and estimates separately; do not imply full host-workload reproduction']),
('PERF-002','Responsiveness and memory budget','load + resource measurement',[
 'Status API p95 is at most 2 seconds under declared local load while worker executes',
 'Recorded worker/RAM budget leaves system headroom without OOM, corrupt output or data loss',
 'Chart decimation affects rendering only and cannot silently reduce execution fidelity']),
('REPRO-001','Reproducible results','clean-cache + restart differential',[
 'Same subject/input/seed produces identical discrete events and values within frozen tolerances',
 'Cache/no-cache/restarted/parallel execution agrees and dependency/environment effects are recorded']),
('REPRO-002','Fresh release installation and full conformance','clean environment + release audit',[
 'Rebuild from locks and execute the actual required suite on the final source manifest',
 'All mandatory requirements have code/test mappings and current coherent passing receipts',
 'Release report links artifacts, source differences and defects with no unmet mandatory requirement']),
('FAULT-001','Critical mutation detection','controlled fault injection',[
 'Wrong stop priority, omitted fees/borrow and wrong distribution sign cause the relevant cases to fail',
 'Truncated pagination and falsely persisted completed status cause acceptance failures',
 'Deliberately corrupt receipts/hashes/stale subjects/unknown cases fail the evidence gate']),
]

FAMILIES = [
 ('level_bounce','STR-001'), ('breakout','STR-002'), ('flip_zone','STR-003'),
 ('trend_pullback','STR-004'), ('trend_line','STR-005'), ('break_of_structure','STR-006'),
 ('change_of_character','STR-007'), ('sweep_reclaim','STR-008'),
 ('supply_demand','STR-009'), ('fair_value_gap','STR-010'),
]
TIMEFRAMES = ['1m','5m','15m','1h','4h','1d']

EXTRA_CASES = [{'id': 'ACCT-002-C04',
  'requirement_id': 'ACCT-002',
  'title': 'Portfolio requests freeze one to64 unique complete rules; duplicate/empty/oversized '
           'input rejects and reversed input order preserves allocation.',
  'expected': 'Portfolio requests freeze one to64 unique complete rules; duplicate/empty/oversized '
              'input rejects and reversed input order preserves allocation.',
  'method': 'model + actual service/API',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'ACCT-002-C05',
  'requirement_id': 'ACCT-002',
  'title': 'Two simultaneous rules cannot reuse starting cash; the hand-authored79-share case '
           'matches its one-account loss and differs from a sum of independently funded losses.',
  'expected': 'Two simultaneous rules cannot reuse starting cash; the hand-authored79-share case '
              'matches its one-account loss and differs from a sum of independently funded losses.',
  'method': 'authored Decimal cash fixture + independent reference',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'ACCT-002-C06',
  'requirement_id': 'ACCT-002',
  'title': 'All rules share instrument/reference-minute entry participation across '
           'next-open/limit/same-close boundaries; new samples reset, instruments separate, '
           'immediate stops do not replenish.',
  'expected': 'All rules share instrument/reference-minute entry participation across '
              'next-open/limit/same-close boundaries; new samples reset, instruments separate, '
              'immediate stops do not replenish.',
  'method': 'mirrored authored volume-budget fixtures + independent reference',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'ACCT-002-C07',
  'requirement_id': 'ACCT-002',
  'title': 'Saved signals/trades identify exact rules; attribution sums actual shared-account '
           'trades and each trade selects its own saved chart timeframe.',
  'expected': 'Saved signals/trades identify exact rules; attribution sums actual shared-account '
              'trades and each trade selects its own saved chart timeframe.',
  'method': 'report reconciliation + browser chart data',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'ACCT-002-C08',
  'requirement_id': 'ACCT-002',
  'title': 'Portfolio creation and direct evaluation reject sealed instrument/date windows before '
           'reading any price rows.',
  'expected': 'Portfolio creation and direct evaluation reject sealed instrument/date windows '
              'before reading any price rows.',
  'method': 'negative guarded-loader integration',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'ACCT-002-C09',
  'requirement_id': 'ACCT-002',
  'title': 'Canceled portfolios publish no partial completed account; same-input resumed execution '
           'equals uninterrupted joint execution and tampered inputs fail.',
  'expected': 'Canceled portfolios publish no partial completed account; same-input resumed '
              'execution equals uninterrupted joint execution and tampered inputs fail.',
  'method': 'actual worker cancel/resume + corruption integration',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'ACCT-002-C10',
  'requirement_id': 'ACCT-002',
  'title': 'At both desktop viewports a user selects two saved rules on different clocks, runs one '
           'account, inspects both rule charts and exports matching JSON/CSV evidence.',
  'expected': 'At both desktop viewports a user selects two saved rules on different clocks, runs '
              'one account, inspects both rule charts and exports matching JSON/CSV evidence.',
  'method': 'real browser + API/export reconciliation',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'ACCT-002-C11',
  'requirement_id': 'ACCT-002',
  'title': 'Actual saved historical multi-rule ledgers/trades/daily equity and basic metrics match '
           'independent Decimal execution on the frozen supplied signals within stated tolerances.',
  'expected': 'Actual saved historical multi-rule ledgers/trades/daily equity and basic metrics '
              'match independent Decimal execution on the frozen supplied signals within stated '
              'tolerances.',
  'method': 'historical differential + independent metric calculation',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'UI-004-C04',
  'requirement_id': 'UI-004',
  'title': 'Actual exit price and sticky trade-column headings remain readable; fit-all puts '
           'stop/target within the chart pane and price-only view preserves the saved bars/trade.',
  'expected': 'Actual exit price and sticky trade-column headings remain readable; fit-all puts '
              'stop/target within the chart pane and price-only view preserves the saved '
              'bars/trade.',
  'method': 'browser coordinate assertions + actual visual review',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'MET-001-C04',
  'requirement_id': 'MET-001',
  'title': 'Zero/negative equity preserves losses and drawdown, uses null returns on nonpositive '
           'bases, and never emits nonfinite JSON or a favorable Sharpe.',
  'expected': 'Zero/negative equity preserves losses and drawdown, uses null returns on '
              'nonpositive bases, and never emits nonfinite JSON or a favorable Sharpe.',
  'method': 'independent equity paths + JSON strict encoding',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'RES-008-C03',
  'requirement_id': 'RES-008',
  'title': 'Primary-paper DSR moment examples and independently computed sample moments agree '
           'within prespecified tolerances; invalid assumptions are explicitly undefined.',
  'expected': 'Primary-paper DSR moment examples and independently computed sample moments agree '
              'within prespecified tolerances; invalid assumptions are explicitly undefined.',
  'method': 'published rounded examples + independent stdlib reference',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'MET-003-C03',
  'requirement_id': 'MET-003',
  'title': 'Passive entries use one causal prior-volume attempt with initial weight/cash/post-cost '
           'exposure constraints; unused allocation and passive drift assumptions remain visible.',
  'expected': 'Passive entries use one causal prior-volume attempt with initial '
              'weight/cash/post-cost exposure constraints; unused allocation and passive drift '
              'assumptions remain visible.',
  'method': 'authored accounting and causal volume fixtures',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'MET-003-C04',
  'requirement_id': 'MET-003',
  'title': 'Passive splits precede ex-date entitlement; fractional quantities, payments and unpaid '
           'receivables reconcile to marked equity and net trade profit.',
  'expected': 'Passive splits precede ex-date entitlement; fractional quantities, payments and '
              'unpaid receivables reconcile to marked equity and net trade profit.',
  'method': 'independent hand corporate-action fixtures',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'MET-003-C05',
  'requirement_id': 'MET-003',
  'title': 'Actual benchmark API/worker jobs freeze data and numerical subjects, reject sealed '
           'reads before raw access, persist outputs and recover without publishing partial '
           'accounts.',
  'expected': 'Actual benchmark API/worker jobs freeze data and numerical subjects, reject sealed '
              'reads before raw access, persist outputs and recover without publishing partial '
              'accounts.',
  'method': 'actual guarded service/API/worker integration',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'MET-003-C06',
  'requirement_id': 'MET-003',
  'title': 'Both desktop browser journeys run and reopen real benchmarks, export matching JSON/CSV '
           'and show strategy differences only for compatible frozen inputs.',
  'expected': 'Both desktop browser journeys run and reopen real benchmarks, export matching '
              'JSON/CSV and show strategy differences only for compatible frozen inputs.',
  'method': 'real browser + independent export reread',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'RES-006-C04',
  'requirement_id': 'RES-006',
  'title': 'Canonical maximum-cardinality matching preserves a fixed real subset across replicas, '
           'with distinct moments and independent stable hash streams.',
  'expected': 'Canonical maximum-cardinality matching preserves a fixed real subset across '
              'replicas, with distinct moments and independent stable hash streams.',
  'method': 'independent exhaustive graphs + stdlib hash reference',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'RES-006-C05',
  'requirement_id': 'RES-006',
  'title': 'Source ATR-relative geometry, side and weight transfer correctly to known '
           'completed-candle features; future outcome fields and unclosed setup candles cannot '
           'affect eligibility.',
  'expected': 'Source ATR-relative geometry, side and weight transfer correctly to known '
              'completed-candle features; future outcome fields and unclosed setup candles cannot '
              'affect eligibility.',
  'method': 'mirrored hand geometry + causal feature fixtures',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'RES-006-C06',
  'requirement_id': 'RES-006',
  'title': 'Full and matched accounts retain distinct denominators; '
           'unmatched/no-trade/negative-profit outcomes remain explicit and intervals/exceedance '
           'follow the prespecified definition.',
  'expected': 'Full and matched accounts retain distinct denominators; '
              'unmatched/no-trade/negative-profit outcomes remain explicit and '
              'intervals/exceedance follow the prespecified definition.',
  'method': 'known-account statistics and zero/missing cases',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'RES-006-C07',
  'requirement_id': 'RES-006',
  'title': 'Guarded API/worker control jobs freeze inputs and checkpoint complete accounts; resume '
           'verifies hashes, rejects corrupt parts and never publishes a partial completed study.',
  'expected': 'Guarded API/worker control jobs freeze inputs and checkpoint complete accounts; '
              'resume verifies hashes, rejects corrupt parts and never publishes a partial '
              'completed study.',
  'method': 'actual service/API/worker recovery + independent execution',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'RES-006-C08',
  'requirement_id': 'RES-006',
  'title': 'Both desktop browser journeys run matched historical controls, inspect actual '
           'surrogate trades/charts, reopen results and export matching aggregate/account JSON and '
           'trade CSV.',
  'expected': 'Both desktop browser journeys run matched historical controls, inspect actual '
              'surrogate trades/charts, reopen results and export matching aggregate/account JSON '
              'and trade CSV.',
  'method': 'real browser + artifact reconciliation',
  'mandatory': True,
  'initial_status': 'not_run'},
 {'id': 'RES-006-C09',
  'requirement_id': 'RES-006',
  'title': 'The default20-control historical run executes all frozen matched accounts; '
           'independently recalculate eligibility/ranking and execution/accounting without '
           'imposing the host profit sign.',
  'expected': 'The default20-control historical run executes all frozen matched accounts; '
              'independently recalculate eligibility/ranking and execution/accounting without '
              'imposing the host profit sign.',
  'method': 'actual20-account run + independent reference',
  'mandatory': True,
  'initial_status': 'not_run'}]

ROWS.append(('RES-010','Price behavior experiments and shifted feature lifetimes','independent price/session oracles + real API/worker/browser',['Exact mirrored touch and gap-fill thresholds, touch-close priority, near/far geometry, full50-bar eligibility, unresolved and censored paths agree with an independent oracle.', 'Shifted geometry uses deterministic1–3 birth ATR draws, avoids every birth-known real interval by0.5 ATR, has independent visits/invalidation and never reopens after birth invalidation.', 'Confirmed feature births, scheduled expiry, close-time geometry updates and trend-line supersession are causal; later prices cannot change earlier identities or shift draws.', 'All six chart inputs and fixed source parameters are validated; default five-chart/default20 historical study saves every requested chart and actual stand-in record without silent workload reduction.', 'Primary hold fractions include unresolved touches; resolved-only measures, matched-cohort counts, full-real counts, no-event and missing-control outcomes remain distinct.', 'Whole-session2000-draw paired bootstrap matches an independent calculation, includes zero-event sessions, needs at least two sessions and leaves intervals undefined when any draw lacks denominators.', 'BOS/CHoCH and other forward measures use10/20/50 complete candles and known prior ATR; matched, unmatched and censored source assessments and actual random timestamps reconcile.', 'Actual API/worker sealed-date guards run before raw reads; cancel/resume verifies complete-chart hashes, corrupt parts fail, orphans recompute and partial work cannot become completed.', 'Both real desktop browser journeys run historical behavior studies, inspect every diagnostic/group, actual candles/geometry, reopen saved results and reject late responses from an older selection.', 'Root JSON, each diagnostic CSV and selected-chart JSON reconcile to saved records, include fingerprints/provenance and never imply executed fills or profitable strategy returns.', 'levels_vs_shifted: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'touch_count: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'wall_target: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'shrinking_bounces: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'line_vs_zone: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'wick_vs_close: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'flip_zones: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'bos_forward: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'choch_forward: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'sweep_vs_close: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'sweep_started_trends: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'trend_lines: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'gap_hold_fill: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'supply_demand_returns: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'pullback_depth: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'engulfing_at_levels: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.', 'rejection_at_levels: a discriminating positive fixture, negative/absent fixture, correct metric/category/horizon mapping and independent matched/full/censored denominators are verified.']))

ROWS.append(('RES-011','Paired one-rule ablations','independent paired-session/account oracles + real API/worker/browser',['Baseline and1–32 alternative values validate complete configurations, differ in exactly one public field, reject duplicates/unknown fields/invalid dependencies and preserve every other declared assumption.', 'All arm rules, calendar, costs, account, input hashes and paired comparison policy freeze before prices; payload tampering rejects before raw reads.', 'Each arm regenerates causal signals and simulates its own complete account; input order and later prices cannot mutate frozen alternatives or earlier signals.', 'Paired P&L uses identical complete session calendars including no-trade days; trade/signal overlap and changed eligibility have separate denominators.', 'Positive/negative/zero paired differences and five-session2000-draw dollar intervals match independent calculations; no executed trades or insufficient sessions leaves uncertainty explicitly undefined.', 'Missing/reordered sessions, unequal costs/capital/windows, nonfinite values and inconsistent account identities cannot produce a comparison.', 'Ordinary ablation preflight and worker/cache access reject sealed warm-up or evaluation dates before any raw price read.', 'Cancel/resume preserves completed content-bound arms; corrupt parts reject, orphans recompute and incomplete studies cannot publish completed results.', 'Root and arm JSON plus comparison and arm-trade CSV exports match actual persisted configuration, counts, ledger and daily records.', 'Both desktop browser journeys run a real historical ablation, inspect every arm, download root/comparison/arm evidence, reopen and reject late responses from another selected job.', 'Historical baseline and three alternatives execute on declared equity data; independently audit every supplied-signal account and paired interval without imposing a favorable result.', 'Derived trigger/configuration changes, insufficient samples, post-hoc selection limits and host-versus-equity differences remain visible; news/calendar gaps are rejected explicitly.']))
EXTRA_CASES.append({'id': 'RES-004-C04', 'requirement_id': 'RES-004', 'title': 'Every new analysis plan is recorded atomically before any outcome read; all configurations/windows/accounts/charts have immutable role and payload identities.', 'expected': 'Every new analysis plan is recorded atomically before any outcome read; all configurations/windows/accounts/charts have immutable role and payload identities.', 'method': 'transactional registry/recovery/sampling fixtures and real browser exports', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'RES-004-C05', 'requirement_id': 'RES-004', 'title': 'Raw occurrences, computation attempts, distinct configurations and separate control/benchmark/behavior roles retain distinct counts; no raw count is advertised as effective independent trials.', 'expected': 'Raw occurrences, computation attempts, distinct configurations and separate control/benchmark/behavior roles retain distinct counts; no raw count is advertised as effective independent trials.', 'method': 'transactional registry/recovery/sampling fixtures and real browser exports', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'RES-004-C06', 'requirement_id': 'RES-004', 'title': 'Failed/canceled/interrupted/retried computations and verified checkpoint reuse persist without double counting execution; a never-started plan has zero attempts.', 'expected': 'Failed/canceled/interrupted/retried computations and verified checkpoint reuse persist without double counting execution; a never-started plan has zero attempts.', 'method': 'transactional registry/recovery/sampling fixtures and real browser exports', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'RES-004-C07', 'requirement_id': 'RES-004', 'title': 'Seeded sampling preserves every proposal outcome, duplicate/rejection reason and count; unselected invalid/duplicate proposals cannot disappear from the declared generation history.', 'expected': 'Seeded sampling preserves every proposal outcome, duplicate/rejection reason and count; unselected invalid/duplicate proposals cannot disappear from the declared generation history.', 'method': 'transactional registry/recovery/sampling fixtures and real browser exports', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'RES-004-C08', 'requirement_id': 'RES-004', 'title': 'Payload/frozen-study/part tampering prevents execution or reuse; output hashes bind actual completed computations and records remain inspectable after restart.', 'expected': 'Payload/frozen-study/part tampering prevents execution or reuse; output hashes bind actual completed computations and records remain inspectable after restart.', 'method': 'transactional registry/recovery/sampling fixtures and real browser exports', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'RES-004-C09', 'requirement_id': 'RES-004', 'title': 'Paginated listings and full selected-job export include history beyond500 jobs with complete aggregate counters; legacy reconstruction is explicitly post-hoc, never relabeled prespecified.', 'expected': 'Paginated listings and full selected-job export include history beyond500 jobs with complete aggregate counters; legacy reconstruction is explicitly post-hoc, never relabeled prespecified.', 'method': 'transactional registry/recovery/sampling fixtures and real browser exports', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'RES-004-C10', 'requirement_id': 'RES-004', 'title': 'Registry reads/exports do not access sealed or ordinary raw market prices and expose no credentials; unsupported request validation is distinguished from an evaluated research hypothesis.', 'expected': 'Registry reads/exports do not access sealed or ordinary raw market prices and expose no credentials; unsupported request validation is distinguished from an evaluated research hypothesis.', 'method': 'transactional registry/recovery/sampling fixtures and real browser exports', 'mandatory': True, 'initial_status': 'not_run'})


ROWS.append(('DATA-011','Versioned scheduled-news calendars','authored causal/import/provider/fault/API/browser evidence',[
 'JSON/CSV import creates immutable content-bound versions with coverage, selected event kinds, source provenance and explicit completeness; old versions remain unchanged.',
 'Malformed, duplicate, naive-time, conflicting, oversized, path-traversal and undeclared-kind inputs fail without publishing a usable calendar.',
 'Retrospective reconstruction, recorded-knowledge and synthetic modes remain distinct in UI, saved inputs, reports and offline presentation; no historical publication time is invented.',
 'Recorded knowledge applies at or after its exact timestamp on the New York event date; DST, overnight confirmation and future-appended events cannot alter earlier decisions.',
 'Free allowlisted official BLS/Fed acquisition parses independently checked dates, excludes overflow/notation/unscheduled rows, handles cross-month meetings and fails on changed or missing coverage.',
 'Bounded retry, HTTP redirects/errors, timeout, cancellation and size limits retain useful job outcomes and no false complete calendar.',
 'Per-job completed-document receipts and body hashes support crash/resume; altered checkpoints/sources fail and uncommitted orphans cannot masquerade as verified reuse.',
 'Experiments and searches freeze exact calendar versions/snapshots; missing, incomplete, out-of-coverage or modified versions fail before raw price reads and stored jobs never silently update.',
 'Shared-capital portfolios freeze one calendar; long/short risk weights and simultaneous exposures remain independently reconciled.',
 'Matched random comparisons apply skip eligibility and match half-risk news regimes with fixed denominators; all accounts retain exact calendar provenance.',
 'Paired news-rule alternatives share one frozen calendar and independently executed complete accounts; incompatible calendar versions cannot be compared.',
 'Study registration freezes calendar and complete date coverage before screening/final evaluation; corruption blocks before price reads and cannot amend a frozen study silently.',
 'Real two-desktop browser acquisition/import/select/run/inspect/export journeys match saved API/worker/calendar records, including error and cancellation states.',
 'A bounded actual official-source receipt is dated separately from authored/mock fixtures; source bytes/hashes and all first failures survive, with no credentials or raw sealed prices in calendar evidence.'
]))


# D034: original411 cases remain mandatory.
EXTRA_CASES.append({'id': 'ACCT-004-C04', 'requirement_id': 'ACCT-004', 'title': 'Frozen borrowing inputs reject malformed dates/times, duplicate or undeclared symbol events, nonfinite rates, incomplete coverage and unsupported fields without a usable job.', 'expected': 'Frozen borrowing inputs reject malformed dates/times, duplicate or undeclared symbol events, nonfinite rates, incomplete coverage and unsupported fields without a usable job.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C05', 'requirement_id': 'ACCT-004', 'title': 'Piecewise annual rates accrue over calendar seconds including weekends; future-appended events cannot rewrite earlier charges or decisions.', 'expected': 'Piecewise annual rates accrue over calendar seconds including weekends; future-appended events cannot rewrite earlier charges or decisions.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C06', 'requirement_id': 'ACCT-004', 'title': 'New shorts use actual next-open, limit-attempt or synthetic-close eligibility; availability alone does not close loans and longs are unaffected.', 'expected': 'New shorts use actual next-open, limit-attempt or synthetic-close eligibility; availability alone does not close loans and longs are unaffected.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C07', 'requirement_id': 'ACCT-004', 'title': 'Recalls latch per existing loan even after clearance; first observed opening market exits precede gap exits with declared costs and no phantom weekend fills.', 'expected': 'Recalls latch per existing loan even after clearance; first observed opening market exits precede gap exits with declared costs and no phantom weekend fills.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C08', 'requirement_id': 'ACCT-004', 'title': 'Borrow changes and recalls interact with splits, distributions and overnight gaps; independent ledgers reconcile unchanged tolerances.', 'expected': 'Borrow changes and recalls interact with splits, distributions and overnight gaps; independent ledgers reconcile unchanged tolerances.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C09', 'requirement_id': 'ACCT-004', 'title': 'Multiple symbols/configurations share capital and liquidity while applying their own borrow states; attribution sums to one account.', 'expected': 'Multiple symbols/configurations share capital and liquidity while applying their own borrow states; attribution sums to one account.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C10', 'requirement_id': 'ACCT-004', 'title': 'All applicable account jobs freeze scenario Costs; unsupported coverage/symbols reject before prices and cannot silently amend queued/resumed work.', 'expected': 'All applicable account jobs freeze scenario Costs; unsupported coverage/symbols reject before prices and cannot silently amend queued/resumed work.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C11', 'requirement_id': 'ACCT-004', 'title': 'Study borrowing inputs freeze before screening/final access; invalid inputs reject before final consumption/prices and saved exports retain assumptions.', 'expected': 'Study borrowing inputs freeze before screening/final access; invalid inputs reject before final consumption/prices and saved exports retain assumptions.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C12', 'requirement_id': 'ACCT-004', 'title': 'Real two-desktop input/error/run/trade-ledger/report/offline flows match frozen API/worker/JSON records and show assumptions as safe text.', 'expected': 'Real two-desktop input/error/run/trade-ledger/report/offline flows match frozen API/worker/JSON records and show assumptions as safe text.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C13', 'requirement_id': 'ACCT-004', 'title': 'Borrow sensitivity executes separate0/3/10/30 percent accounts with identical other inputs, preserving absolute profit and differences rather than rescaling P&L.', 'expected': 'Borrow sensitivity executes separate0/3/10/30 percent accounts with identical other inputs, preserving absolute profit and differences rather than rescaling P&L.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})
EXTRA_CASES.append({'id': 'ACCT-004-C14', 'requirement_id': 'ACCT-004', 'title': 'Declared event/symbol/date bounds, deterministic replay/recovery and interruption/corruption reject explicitly; independent oracle and coverage receipts supplement final acceptance.', 'expected': 'Declared event/symbol/date bounds, deterministic replay/recovery and interruption/corruption reject explicitly; independent oracle and coverage receipts supplement final acceptance.', 'method': 'authored independent Decimal/account/API/worker/browser/fault evidence', 'mandatory': True, 'initial_status': 'not_run'})

def build():
    requirements=[]
    cases=[]
    for rid,title,method,checks in ROWS:
        ids=[]
        for i,expected in enumerate(checks,1):
            cid=f'{rid}-C{i:02}'
            ids.append(cid)
            cases.append(dict(id=cid,requirement_id=rid,title=expected,expected=expected,
                              method=method,mandatory=True,initial_status='not_run'))
        requirements.append(dict(id=rid,title=title,mandatory=True,case_ids=ids))
    for family,rid in FAMILIES:
        for timeframe in TIMEFRAMES:
            for direction in ['long','short']:
                cid=f'MATRIX-{family}-{timeframe}-{direction}'
                case=dict(id=cid,requirement_id=rid,title=f'{family}: {timeframe}, {direction}',
                          expected='Constructed positive and discriminating negative fixture: exact causal signal/availability, intended nonempty trade, correct side/entry/exit/size/costs and independent ledger reconciliation; changing future prices cannot alter earlier decisions.',
                          method='independent fixture + actual production engine + reconciliation',
                          family=family,timeframe=timeframe,direction=direction,
                          mandatory=True,initial_status='not_run')
                cases.append(case)
                next(r for r in requirements if r['id']==rid)['case_ids'].append(cid)
    for case in EXTRA_CASES:
        cases.append(case.copy())
        next(r for r in requirements if r['id']==case['requirement_id'])['case_ids'].append(case['id'])
    catalog=dict(version=8,prepared_date='2026-11-07',status='planned_not_executed',
                 specification_files=['PLAN.md','VERIFICATION_PLAN.md'],
                 requirements=requirements,cases=cases,
                 strategy_matrix=dict(families=[f for f,_ in FAMILIES],timeframes=TIMEFRAMES,
                                      directions=['long','short'],expected_case_count=120),
                 note='Planning inventory only. Coverage CSV initial statuses are not executed test outcomes. Add expanded fixtures/parameter cases before claiming all supported values and constraints verified.')
    (ROOT/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    with (ROOT/'coverage.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=['case_id','requirement_id','title','method','mandatory','initial_status','receipt'])
        writer.writeheader()
        for c in cases:
            writer.writerow(dict(case_id=c['id'],requirement_id=c['requirement_id'],title=c['title'],
                                 method=c['method'],mandatory=c['mandatory'],initial_status='not_run',receipt=''))
    mapping=ROOT/'implementation-map.json'
    if not mapping.exists():
        mapping.write_text(json.dumps({'status':'not_implemented','requirements':[
            dict(id=r['id'],implementation=[],tests=[],rulebook_sections=[]) for r in requirements
        ]},indent=2),encoding='utf-8')
    print(json.dumps({'requirements':len(requirements),'acceptance_cases':len(cases),'strategy_matrix_cases':120,'executed_product_tests':0}))

if __name__=='__main__':
    build()
