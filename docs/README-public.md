# Price Action Research Lab

A local strategy-research application inspired by [AI Pathways' YouTube video, starting at 6:41](https://www.youtube.com/watch?v=z97PnFIPoFg&t=401s). US stocks and ETFs first, free historical Alpaca data, long/short simulation and explicit execution and borrowing assumptions.

**Paused on November 10, 2026, Pacific time. This is an unfinished development snapshot, not a verified release.** GitHub Pages hosts static documentation; the application requires its local Python backend.

## Status and complete history

- [Live documentation](https://az9713.github.io/price-action-strategies/)
- [HTML handoff and remaining tasks](https://az9713.github.io/price-action-strategies/handoff.html)
- [Complete development journey](https://az9713.github.io/price-action-strategies/development-journey.html)
- [Searchable verification history](https://az9713.github.io/price-action-strategies/verification-history.html)
- Local HTML: [handoff](docs/handoff.html), [journey](docs/development-journey.html), [verification history](docs/verification-history.html).
- [Pause state](PAUSE_STATE.json), [implementation plan](PLAN.md), [verification plan](VERIFICATION_PLAN.md), [rulebook](RULEBOOK.md), [decisions](decisions.md).

The root application is the historical 0.25 development checkpoint; package manifests still say 0.1.0. The newest uninstalled research source is under `data/dev027/research-src`, with source-only comparison snapshots under `data/dev026`. These are separate subjects, not two certified releases.

The newest build passed **86 focused checks**, including exact financial-output comparisons at 64, 65 and 128 accounts and transaction/connection/failure checks. Its **829-test run was interrupted after 787 reported passes**. The remaining outcomes are unknown; it has no terminal passing receipt.

The latest actual 10,000-configuration benchmark, on the preceding revision, failed at **5,488 configurations in 903.85 seconds**. That prior revision passed 675 numerical checks, all 120 baseline combinations and a 1,000-configuration run in 65.68 seconds. Those results do not certify the newest changes.

The additional news acceptance run had 24 passes and three failures: two HTML fixtures are absent from the research stage, and its clean-clone verifier copies JSON fixtures only. The intended acquisition-crash boundaries were not reached. This gap was preserved at the pause.

## Implemented behavior

Audited acquisition/imports, immutable strategies, seeded searches, independent/shared-capital accounts, saved trades/charts/ledgers, research studies, conditional random comparisons, behavior studies, one-field ablations, borrowing scenarios/sensitivity, versioned news calendars and offline exports.

Ten numerical strategy-family adaptations: level bounce, breakout, flip zone, trend pullback, trend line, break of structure, change of character, sweep/reclaim, supply/demand and fair-value gap. The host's private engine, full grid and complete named presets were unavailable. Identical host trades or reported futures profits are not claimed. Futures, forex and crypto remain later options.

## Remaining work

1. Correct the declared fixture inventory and rerun actual news acquisition crashes.
2. Finish numerical/recovery/lease regression and reconcile the 120-case matrix.
3. Pass current real-data 100/repeat, 1,000 and 10,000 resource gates.
4. Complete both original 10,000-set financial controls, qualification, candidate freeze, both final instruments/all versions and full exports.
5. Execute actual 100,000-configuration financial stress.
6. Complete all 51 numerical coverage gates, current browser/mobile/keyboard/accessibility/security/privacy/offline/restart/clean-install checks.
7. Audit evidence for all 83 requirements and 422 mandatory cases, then install and verify a release.

Do not automatically restart archived coordinators. Their process handles and source hashes are historical. Development stays paused until explicitly resumed.

## Stack and local setup

Supported baseline: **Windows/PowerShell, Python 3.13, Node 22.22**. FastAPI/Pydantic, a spawned worker, SQLite WAL, NumPy/pandas/PyArrow/SciPy/Numba; React/TypeScript/Vite, Lightweight Charts/Recharts. Verification uses pytest/Hypothesis/coverage, independent Decimal references and Playwright. Exact dependencies: [requirements.lock](requirements.lock), [frontend/package-lock.json](frontend/package-lock.json).

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
Set-Location frontend
npm ci --ignore-scripts
npm run build
Set-Location ..
.\start.ps1 -Port 8765
```

Open `http://127.0.0.1:8765`. This starts the root development checkpoint. Use Ctrl+C in its terminal to stop it; closing the browser does not cancel a job. A responding server is not promised at the pause. GitHub Pages cannot run the Python/SQLite application.

Create your own local `.env` with `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` for provider acquisition. Never commit populated credentials. Free history depends on actual account entitlement and availability. Synthetic imports and locally saved results do not need an API key. No downloaded market dataset or original user database is included.

## Assumptions and limitations

Imports use raw minute OHLCV with symbol, explicit timezone/UTC timestamp, open/high/low/close/volume. Missing prices are not filled; audits and corporate-action declarations control eligibility. One-minute bars cannot establish intrabar sequence or queue position. Fees, ticks, gaps, spread/slippage, participation, borrow rates/availability/recalls and collateral follow declared simulation assumptions.

Fixed watchlists do not prove point-in-time universe validity. Reconstructed news calendars are retrospective unless supported by recorded knowledge. Previously viewed history cannot become untouched final evidence. Synthetic positive fixtures and diagnostics do not establish an investment edge. The app has no live-order capability. It is useful for exploratory smaller tests and saved-result inspection, with the unfinished reliability limits above.

## Evidence, privacy and cost

The run ledger includes every original receipt and timestamped run directory captured at publication, including failures and absent terminal receipts. Repeated historical passes are not independent coverage. Public evidence copies are privacy-derived; [the publication manifest](PUBLICATION-MANIFEST.json) records original and published hashes. They do not certify privacy-rewritten source bytes.

Credentials, price caches, original databases, raw command/browser traces, environments, source video and full video transcript are excluded. User names, machine/home paths, device identifiers and live credential values are scrubbed from the published tree and fresh Git history. Emails are permitted; public attribution and license notices remain. [Privacy report](docs/pause/PRIVACY-REPORT.json).

Build calendar elapsed: **75h 44m 24s**. Completed/aborted work-turn union: **71h 46m 44s**. Separate active-goal counter: **71h 28m 59s**. Do not add these overlapping clocks.

The reconciled 4,950-response ledger contains **1,163,094,748 input/output tokens**, including **1,147,371,904 cached-input tokens**. Uncached input plus output: **15,722,844**. Actual dollar cost is unavailable; no subscription usage is relabeled as an API bill. [Accounting](docs/pause/journey-accounting.json).

The complete rendered history combines [part 1](DEVELOPMENT-JOURNEY.md), [part 2](DEVELOPMENT-JOURNEY-2.md), [part 3](DEVELOPMENT-JOURNEY-3.md) and [part 4 through the pause](DEVELOPMENT-JOURNEY-4.md). [Video review](VIDEO_REVIEW.md) and [screenshot findings](SCREENSHOT_FINDINGS.md) distinguish full automated decoding from sampled visual inspection.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). This snapshot grants no project-wide open-source license; dependencies retain their own terms.
