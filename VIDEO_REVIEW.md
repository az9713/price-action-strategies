# Video evidence and replication gaps

Source: [Claude Tested 100,000 Price Action Strategies (Here's What Works)](https://www.youtube.com/watch?v=z97PnFIPoFg), AI Pathways, uploaded 2026-10-28 according to downloaded YouTube metadata. Review prepared 2026-11-07.

## Coverage and provenance

The entire video was acquired locally, including the first six seconds. A 3840×2160 representation was retained for enlargements and a 1920×1080 representation for review. The latter contains 30,920 video frames at 30 fps, lasting 1030.666667 seconds; the audio/video container is slightly longer. All frames were decoded in an automated scene-change pass. Visual review used 1,031 one-second samples across 21 contact sheets, 0.5-second samples through the rapid end-of-video prompt sequence, and enlarged prompt pages. All 15 technical pages of the 16-page prompt deck were visually read; its other page is an overview.

This is not a claim that a human-style visual inspection was performed on each of the 30,920 individual frames. The visual coverage is substantial, with every observed application state and technical prompt page inspected. Automatic scene detection is not proof that every tiny transient change was understood. Timestamp links below address the source video; frame-sheet labels are approximate sample times rather than exact transition boundaries.

The English automatic-caption track was acquired after an initial HTTP 429 failure. Narration was read through deduplicated, timestamped captions, not independently checked word-for-word against audio. An attempted local speech-recognition fallback was stopped once captions became available. No inference depends solely on an unverified transcription of a technical number: important rules were checked visually against the prompt pages.

Local source files, screenshots and full captions are research evidence, not a redistributed prompt/transcript package. The documents paraphrase technical content. No original source code, price data or experiment results were acquired. The source manifest records hashes and coverage.

## What is actually being recreated

The visible interface is a slide-like dark dashboard. Counters show totals of 66 on some screens and 67 on later screens; the full underlying deck is not exposed. At [16:29](https://www.youtube.com/watch?v=z97PnFIPoFg&t=989s), the dashboard prompt explicitly describes a self-contained, offline HTML presenter built from previously saved research outputs. It does not read raw or withheld price data.

The follow-up [screenshot findings](SCREENSHOT_FINDINGS.md) and [37-image index](research/screenshots/README.md) add direct full-resolution evidence. In particular, the example trade is labeled NQ 4h, July 11, 2024; it is in discovery, before the stated final window. Several favorable comparison badges coexist with negative absolute performance, so the recreated application must separate these meanings.

Therefore there are two deliverables to distinguish: a numerical research engine that produces auditable files, and a presentation that displays them. Upload widgets, interactive strategy editing, job queues, cancellation, recovery, data-provider setup and a persistent research workspace are proposed additions required to make this a usable application.

## Visible screens and implied capabilities

| Approximate source interval | Observed screen/content | Requirement captured |
|---|---|---|
| 01:05–03:23 | Annotated price-action diagram | Levels, trend, structure breaks, reversal, sweep, confirmation, stop/target, six timeframe choices |
| 03:24–03:58 | Ten illustrated setup cards | Ten strategy families listed below |
| 04:12–04:21 | Different hand-drawn interpretations of one chart | Replace subjective interpretation with reproducible rules |
| 03:59–04:11 and 04:22–06:58 | Methodology summary | Rule dials, two sampling groups, costs, random controls, cross-market comparison and withheld dates |
| 06:59–07:23 | Search funnel | Generated → sufficient trades → net profitable → risk-adjusted gate, grouped by sampling set |
| 07:24–07:52 | Win-rate/profit scatter | One point per version; timeframe legend; correlation and high-win-rate count |
| 07:53–08:28 | Timeframe comparison | Profitability, trade frequency and costs by timeframe |
| 08:29–08:49 | Real levels versus random lines | Paired hold-rate comparison by timeframe |
| 08:50–09:41 | Touch-count comparison | Outcome by number of prior touches; compare with matched controls |
| 09:42–10:10 | Level-rule effects with intervals | Touch count, wall/target, weakening pushes, line/zone and flip-zone effects |
| 10:11–10:17 | Break/CHoCH follow-through | Forward moves after events compared with matched random moments |
| 10:18–10:22 | Trend strategy comparison | Net performance by trend-related family |
| 10:23–10:33 | Common trend formulations | Sweep requirement and other rule variants |
| 10:34–10:58 | Confirmation comparison | Entry at level versus waiting, with price penalty and net outcome |
| 10:59–11:18 | Stop comparison | Immediate hard-stop versus candle-close exit |
| 11:19–11:28 | Context/filter effects | Session, recent multi-day run and trend filter |
| 11:29–11:55 | Results in both markets | Family/timeframe robustness across discovery eras and variant groups |
| 11:56–12:01 | Final-window market chart | Describe withheld period's market behavior |
| 12:02–12:30 | Final-window timeframe ladder | Fraction of common configurations profitable by timeframe |
| 12:31–13:05 | Selected-version equity curves | Discovery/final boundary; NQ and ES outcomes |
| 13:06–13:15 | 4-hour family summary | Neighborhood/common-version robustness rather than one selected curve |
| 13:16–14:21 | Takeaways | Summarize tests, with interpretation separate from evidence |
| 14:22–14:49 | Annotated example trade | Trend, CHoCH, entry, stop and target on an actual displayed chart |
| 14:50–15:55 | Comparison with earlier videos | Contextual claims only; those other videos are outside this investigation |
| 15:56–17:00 | Five prompts across 16 pages | Technical workflow, data contract, engine rules, research gates and presentation controls |

## Strategy families

At [03:24](https://www.youtube.com/watch?v=z97PnFIPoFg&t=204s), the ten cards identify: level bounce; breakout; flip zone; trend pullback; trend line; break-of-structure continuation; change-of-character reversal; sweep and reclaim; supply/demand zone; fair-value gap.

In plain English, these cover reacting to an established price area, trading through it, retesting it after a break, following a trend, and reversing after a trend loses its structure. Their labels do not define a unique algorithm. Each requires an explicit detector and rules for entry, exit, costs and overlapping signals.

## Technical details from the five prompt layers

These are source requirements, not claims that the original code implemented or passed them. The prompts reveal substantially more detail than the spoken summary.

### Layer 1: data and parameter definitions, about 16:02–16:13

Pages 2–5 specify a Python project with isolated environment, saved artifacts, decision log, one master random seed, preregistered amendments and a guarded withheld-data directory.

The supplied source input is one-minute continuous front-month NQ/ES data, with a back-adjusted file per market, optional aligned unadjusted prices and a roll table. The schema includes UTC bar-open timestamps, OHLC, volume and contract ID; raw inputs receive SHA-256 hashes. The video does not supply these files or identify enough acquisition details to reproduce the dataset.

The futures session is 18:00–17:00 America/New_York, dated by session end; the 17:00 halt hour is excluded. Audit duplicates, ordering, gaps at several durations, OHLC consistency, zero volume and adjustment steps. Count gaps rather than filling them. Restrict entries ahead of contract rolls and close existing positions before rolls. Include a sourced macro-news calendar.

The displayed original date split is:

- Warm-up: 2021-10-01 through 2021-12-31, building detector state without trades.
- Discovery: 2022-01-03 through 2024-07-31, divided into 2022 and 2023–July 2024 eras.
- Final: 2024-08-01 through the supplied data ending 2026-10-16.

Final-window data is hashed and guarded; reads require a named step and explicit unlock, recorded in an access log. For alternate dates the prompt suggests a short warm-up, roughly 2.5 discovery years and roughly two withheld years.

Five-minute, 15-minute, hourly, 4-hour and daily candles are aggregated from minute data. The 4-hour futures boundaries are explicitly anchored at 18:00 ET, with a shorter last interval ending at 17:00. Higher-timeframe values become available only at candle close. ATR uses Wilder's 14-bar construction and preceding bars.

The parameter families include:

| Family | Source values/examples |
|---|---|
| Setup/trigger timeframe | Six setup charts: 1m, 5m, 15m, 1h, 4h, daily; trigger at same or lower charts, with a special daily/hourly rule |
| Swings and structure | Pivot strength 2, 3, 5, 8; trend from successive confirmed swing highs/lows; first close through a confirmed swing in or against the trend |
| Levels | Cluster radius 0.1, 0.25, 0.5 ATR; 1–4 touches; line versus zone |
| Other detectors | Trend lines, 2–5-candle supply/demand impulses spanning 1.5–3 ATR, three-candle gaps |
| Confirmation | None, close back, rejection wick, engulfing, either candle, lower-timeframe structure break |
| Entry | Completed-candle close or limit back at a level |
| Stop | Hard or close-based; beyond level, touch wick, latest swing or gap middle candle; buffer 0, 0.1, 0.25 ATR |
| Target | 1R, 1.5R, 2R, 3R, 4R, 5R or next swing |
| Holding/exit | Hold versus structure-change exit; session-flat or 24-/96-bar timeout |
| Filters | Trend at several horizons; choppiness; direction of 3-/5-day run; fresh breakout; news skip/half size; session; pullback depth; gap confluence |
| Setup-specific | Flip-zone retest window; sweep depth and reclaim period |

Invalid combinations are removed. The exact full enumeration and dependency predicates are not supplied, so the source's theoretical configuration count is not a reproducibility target for this build.

### Layer 2: execution and behavior tests, about 16:14–16:21

Pages 6–9 require signals on truncated histories to match full-history signals up to the same cutoff. This applies to all detectors and all strategy families.

The source engine models one futures contract per trade, one position at a time per strategy and overnight holding unless a time exit applies. It resolves every fill on one-minute data regardless of signal timeframe. It applies $4 round-trip commission and one tick of adverse slippage to specified market/stop/structure exits. Limits and targets need a one-tick trade-through; a gapped limit receives no favorable price improvement. A gapped hard stop fills beyond the opening price with specified slippage. If a minute bar can touch both stop and target, the stop takes priority. Some time/roll/limit exits have no slippage in the source model.

These are futures modeling assumptions, not an execution-quality guarantee and not directly applicable stock costs. A half-contract news setting is also a normalized research exposure, not a literal single-contract exchange fill.

Trade records include times, reasons, points, dollars and net R. Source daily P&L places realized profit on exit days and zero on sessions without exits; its Sharpe is annualized from those daily dollar values. This can conceal interim open-position risk. The proposed equities system will use daily mark-to-market equity and returns, retaining any compatibility calculation separately.

Checks include mirrored synthetic paths; stop/limit/gap behavior; timeouts; rolls; exclusivity and half-size exposure. A random-entry control and an intentionally future-peeking positive control are described. Their reported historical outcomes must not become fixed expected profits/losses on another dataset.

Behavior tests use default swing strength 3 and 0.25 ATR tolerance. They compare real price features with random substitutes on discovery data, separately by timeframe and pooled. A level holds if a one-ATR retreat precedes a close more than 0.25 ATR through it; after 50 bars it can remain unresolved. Random lines are shifted 1–3 ATR while avoiding nearby real levels; random moments are matched on chart, direction and time-of-day bucket.

The described test inventory includes levels and touch counts, weakening bounces, lines versus boxes, wick versus close breaks, flips, structure follow-through at 10/20/50 bars, sweeps, trend lines, gaps, supply/demand revisits, pullback depth, engulfing and rejection candles. Confidence intervals use 2,000 whole-session bootstrap resamples. Source verdicts combine interval direction, ES agreement and agreement between discovery eras. The equity app should prefer descriptive evidence labels over declaring a broad claim universally true or false.

### Layer 3: configuration search and funnel, about 16:22–16:25

Pages 10–12 specify a stratified broad sample of 40,000 versions, 4,000 per setup. Candidate selection attempts balanced parameter coverage, subject to a minimum discovery signal count. A second group combines a 14,016-version common-settings grid with 47,329 sampled common-style configurations, totaling 61,345. Source common-style sampling uses 40% no filter, 40% one filter and 20% two filters. Six named presets are also mentioned, but their full rule definitions and exact membership/deduplication policy are not exposed.

For each configuration, save rules and hash them before execution. Discovery gates include at least 30 executed trades, positive net profit, Sharpe at least 0.5, performance versus matched random entries, and a cross-market check. The prompts additionally discuss at least 40 discovery signals for inclusion; signals and executed trades are different denominators.

The matched-entry test creates 10,000 control sets, retaining direction, time-of-day bucket, ATR-normalized risk/target distances, holding-time and cost characteristics. Fewer than 5% outperforming the tested version is the described gate. ES replication additionally requires profit and Sharpe at least 0.3; both discovery eras must be profitable for a final candidate.

Families are also evaluated by equal-weight average daily P&L across their versions. Source family gates require positive annualized profit and Sharpe at least 0.5, with positive results in each discovery era. Store configurations, metrics, daily P&L, family results and candidate hashes before final testing. Report funnel attrition, timeframe effects, paired parameter changes, and named-preset outcomes.

This does not establish adequate multiple-testing control across all searched versions. The proposed build adds a trial registry and search-aware uncertainty; a nominal 5% random-control threshold is not an overall 5% false-discovery guarantee after a large search.

### Layer 4: withheld final evaluation, about 16:26–16:28

Pages 13–14 freeze the engine, rules, thresholds and candidate lists before unlocking final data. Verify configuration hashes. Rehearse the final path on a transformed discovery subset; then open the final window through the guard and log it. The source script is instructed to refuse a rerun when final results already exist.

Prior discovery data supplies detector warm-up only. The source describes an additional session-completeness rule and closing trades before dropped sessions. That exact futures rule is unsuitable for equity early-close days without adaptation. Final evaluation runs all saved versions on both markets, with selected candidates and families separately identified. It saves every version's metrics and daily P&L. A positive net result and Sharpe of at least 0.5 is the described final version criterion.

Later analysis uses saved outputs rather than reopening withheld prices. The application's holdout guard is a research workflow safeguard on a user-controlled computer, not a security boundary against its owner. Any revised test after viewing final outcomes must be visibly marked as using consumed evidence.

### Layer 5: presentation, about 16:29 onward

Pages 15–16 specify a self-contained offline HTML file on a scaled 1920×1080 stage. Navy background `#0b0f1a`, cyan/amber accents, monospaced section labels, rounded cards, green/red outcomes and sparse explanatory text are visible. Findings generally use one chart, at most two headline statistics and a short evidence verdict. A lower-right 520×368-pixel area is reserved for a camera overlay.

The prompt requires each displayed number to map to a saved file/row/column and an independent reread, with missing or disagreeing provenance blocking the build. Presentation controls include arrows, Space, Page Up/Down, Home/End, numbered URL fragments, a section menu, replay, a camera-area toggle, pointer ring and fading drawn highlights. These controls are specified in the prompt; the video does not demonstrate each one being operated.

Checks include 1920×1080 and 1280×720 layouts, no content outside the stage or in the camera reserve, screenshots and a page inventory. The recreated app should retain this as optional presentation output while using a normal responsive workspace for research.

## Interpretation and gaps

The creator reports that a four-hour CHoCH reversal without a sweep, with a stop past the previous swing and a 1R target, survived their tests. The displayed selected configuration enters at candle close. These are source-reported futures findings. They have not been independently reproduced, do not establish an equities edge, and should not be preloaded into the application as its own successful test results.

The narration compresses ES cross-market replication and chronological final validation into an informal out-of-sample description. The prompt pages clarify that ES discovery data participates in candidate evaluation. In a recreation, distinguish another instrument used during development from a genuinely untouched later-date test.

The major unresolved gaps are:

1. **Data identity:** original vendor, contract rolls, revisions, missing sessions, back-adjustment construction and actual input hashes are unavailable.
2. **Code and artifacts:** no original engine, complete detector implementation, trade ledger, full dashboard, independent audit or successful test logs are supplied.
3. **Ambiguous rules:** pivot ties and confirmation timing; precise trend-line selection; zone boundaries, merging and expiry; gap mitigation; choppiness definition; recent-run filters; named presets; full invalid-combination rules; pending-order/re-entry priority all need explicit decisions.
4. **Execution limits:** one-minute OHLC cannot reveal all intraminute paths or actual liquidity. The source's stop-first choice is an assumption, not verified fill history.
5. **Equity accounting:** corporate actions, delistings, dividends, price gaps, borrowing, recalls, shared capital and margin are outside the original futures demonstration.
6. **Statistical selection:** many variants share signals and price paths. A large simulated trade count does not mean that many independent observations. Searching a huge space and finding a favorable neighborhood still requires fresh validation and correction for selection.
7. **UI scope:** the visible presentation does not establish a working strategy editor, provider integration, run management or live broker connection. Those are product design tasks.
8. **Exact replication:** public prompts are a useful specification, but not sufficient to reproduce the original numerical results. A functional recreation is feasible; an exact clone of undisclosed code/data is not substantiated.

The implementation plan addresses these gaps explicitly and treats favorable, unfavorable and inconclusive outcomes as equally valid outputs.
