# Focused screenshot findings

Review date: 2026-11-07. This supplements [VIDEO_REVIEW.md](VIDEO_REVIEW.md) and changes [PLAN.md](PLAN.md).

Captured 37 new, full-resolution 3840×2160 PNG screenshots directly from the downloaded video: 22 presentation/chart states and 15 technical prompt pages. The [screenshot index](research/screenshots/README.md) links every image to its video time. [The manifest](research/screenshot-manifest.json) records requested timestamps, source paths and SHA-256 hashes. These are local research captures; the underlying results remain the creator's claims, not independently reproduced results.

The three PNGs and transcript already present at the workspace root were also inspected. They are preserved unchanged. The new captures cover the detailed results and technical pages beyond those three overview images.

## Gaps filled or narrowed

| Screenshot | Observation | Consequence for the application |
|---|---|---|
| [Example trade, 14:35](research/screenshots/example_trade.png) | The footer identifies **NQ, 4-hour, July 11, 2024**. A bearish reversal is drawn below the preceding higher low, with entry at the reversal candle's close, stop beyond the preceding high and a lower target. | We now have a dated visual fixture for a future NQ replication check. It predates the source's August 1, 2024 holdout. Exact time, contract adjustment and unrounded prices still require the original data. It is a discovery-period example, not an unseen-period validation trade. |
| [Confirmation, 10:41](research/screenshots/confirmation.png) | The displayed annual comparison is approximately **−$1,093** for entering at the level and **−$373** after confirmation. The headline improvement is **+$719 per year**, with 4.3 price points given up. | A favorable comparison can still lose money. Show absolute net profitability, relative improvement, statistical evidence and later-date validation separately. The rounded bars imply $720, so do not reconstruct unrounded effects by subtracting rounded labels. |
| [Stops, 11:05](research/screenshots/stop_models.png) | Both displayed alternatives are negative: **−$158** for hard stops and **−$290** for close-based stops; the displayed difference is **−$132 per year** for the latter. | Preserve both absolute outcomes and the difference; never interpret a better stop rule as a profitable standalone strategy. These are aggregate comparison values, not guaranteed trade outcomes. |
| [Family robustness, 13:10](research/screenshots/family_robustness.png) | **39/48** refers to usual-settings NQ versions. **66%** refers to **314 common NQ versions**; the separate ES common-version figure is **54.5%**. | Every success rate needs its instrument, configuration subset, numerator/denominator and evaluation dates. Do not attribute 39/48 or 66% to both markets. |
| [Family robustness, 13:10](research/screenshots/family_robustness.png) | The slide says gains in the original sample were concentrated in a few large days. New York-session versions still made money after removing their ten best days, according to the displayed claim. | Add best-day contribution, top-ten-day exclusion and trade-concentration diagnostics. These are descriptive robustness checks, not rules allowed to remove losing or winning days from a tradable strategy after seeing them. |
| [Timeframes, 08:02](research/screenshots/timeframe_costs.png) | The screen specifies **46.0%** of gross profit consumed by costs for one-minute setups and **3.9%** for daily setups. Its heading limits this comparison to the original 40,000, NQ discovery. | The narration's approximate 40% should not replace the on-screen 46%. Report market, dates and sample group with each chart. Define the denominator of cost/gross-profit ratios, including zero/negative cases. |
| [Common trend rules, 10:27](research/screenshots/common_trend_rules.png) | Named comparisons include a trend line from the first to second low, a reversal flip, sweep followed by change, change without a sweep requirement, and delayed entry on a five-minute break. | These become explicit comparative variants rather than being collapsed into one generic trend family. The chart identifies a trend-line anchor idea but still does not specify pivot ties, line invalidation or all trade rules. |
| [Prompt page 4, 16:12](research/screenshots/prompt_page_04.png) | The source fixes swing-strength choices, cluster tolerances, touch counts, timeframe relationships and ATR timing. | The allowed parameter menu is substantially specified. Remaining gaps concern exact detector behavior and valid-combination predicates, not the entire menu. |
| [Prompt page 7, 16:17](research/screenshots/prompt_page_07.png) | Execution is checked on minute bars. The source specifies a one-tick trade-through for limits/targets, adverse stop-gap pricing, stop-first ambiguous bars, $4 round-trip futures commission and selected slippage rules. | These are explicit source assumptions and belong in a reference execution preset. Stock costs and financing remain a separate model. The image specifies rules; it does not prove that the hidden code followed them. |
| [Prompt pages 12–14](research/screenshots/prompt_page_12.png) | Candidate rules, matched controls, market replication and final-window handling have distinct gates. | Preserve separate discovery, replication and final-test states. A comparison badge and a profitable result cannot share a single undifferentiated success flag. |

The example screenshot shows approximate price levels, but no exact numeric fill labels. Do not estimate exact trade profit or assert a match from the picture alone. The source date and direction narrow the future search; the corresponding original data and engine definitions remain necessary.

## Presentation details checked

The screenshots preserve chart layout, annotations, legends, colors, section labels and the host's lower-right camera overlay. The prompt pages specify the underlying offline presenter and its controls. The main deck's page count changes from 66 to 67 across captured scenes; therefore the earlier reference to a fixed 66-page deck was too definite. Index the evidence by video timestamp and screenshot ID. A revised deck or edited recording is a possible explanation, not an established fact.

The screen layouts can guide the presentation mode. They still do not demonstrate an interactive data uploader, strategy editor or experiment scheduler. Those remain application features to build.

## Remaining implementation gaps

- Exact pivot ties, trend initialization, level clustering/expiry, zone construction, gap mitigation, pending-order priority and re-entry behavior are still not fully defined.
- The six named presets are labeled, but their complete configurations are not supplied.
- Original market data, contract-roll history, full source code and saved result tables remain unavailable.
- Equity corporate actions, borrowing availability, borrowing charges and capital constraints still need the planned explicit treatment.
- The source's favorable numerical results remain unverified. The captures provide observable claims and specifications, not independent validation.

## Alpaca dependency check

The user subsequently added the secret key to the local `.env`. Authentication succeeded on eight bounded read-only market-data requests, including historical consolidated SIP data. Credentials were sent only to Alpaca's official data host over HTTPS for authentication; no value was printed or saved in the results. [Probe results](research/alpaca_probe/README.md) record the evidence. [Official authentication documentation](https://docs.alpaca.markets/us/docs/about-market-data-api)

Sample historical access is now verified, including ETF minute bars from 2016 and 2022 and recent stock/ETF bars. Complete multi-year coverage, full corporate-action handling and borrowing data remain unverified. `.gitignore` excludes local `.env` files. Screenshot extraction and review are complete independently of provider access.
