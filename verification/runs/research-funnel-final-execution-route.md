# Both-instrument all-version final: next implementation route

Implement the authored contracts in `research-funnel-final-contracts.py`. The retained absence receipt20261110T095040914956Z proves the module is still missing; do not repeat that check as if it were implementation progress. Preserve all83 requirements/422 mandatory cases/120 baseline combinations.

## Source fidelity

The [AI Pathways/Brendan video](https://www.youtube.com/watch?v=z97PnFIPoFg), retained layer4 observations in VIDEO_REVIEW.md, evaluates **all saved versions on both markets**, with selected candidates/families identified separately. Do not inherit the basic Study candidate-only final path or refuse the complete final cohort merely because the qualified candidate list is empty. US-stock/ETF instrument replication remains an explicit adaptation, not ES futures or verified private-engine parity.

## One original reservation and consumption

Use one original `funnel_final` job per study, a unique SQL link, an original reservation event and a reverse original-job check. Bind the completed owned qualification root/publication/candidate-freeze hash, original study-input/cohort/core hashes, complete original configurations, both frozen final-arm definitions and all financial assumptions. Creating/reserving the job may read original evidence/metadata but must not decode final prices or consume final access. Concurrent retries return the same original job, including failed/canceled/completed jobs; damaged original reservations are refused.

Before the first final `_evaluation_input`, verify the original qualification/freeze and both source manifests, then atomically consume once. The existing guard already permits only the same `study_id`/`final_job_id` in consumed/final_complete/final_failed states. Reuse `spec.final_job_id`, the existing `final_unlock_consumed` event and verified StudyIndex scope update so ordinary reads stay blocked. The input hash already excludes final_job_id. Avoid setting reserved_final_job_id without adapting StudyIndex.anchor: that existing key is tied to `portfolio_final_reserved`. A dedicated funnel reservation table/event can leave it absent.

Do not call basic Guard.begin_final: it requires basic screened candidates and would drop the zero-candidate/all-version source contract. The custom consume path must prove the dedicated original reservation and candidate/family freeze. Keep the basic funnel screen/final bypass refused. If failure occurs after consumption but before/during a first price read, retain the consumed state and permit recovery only through the same final job. Mark final_failed/final_complete consistently with the owning final job; graceful shutdown keeps the consumed identity and queues original work for continuation.

Full original qualification inspection belongs outside a write transaction: its D046 verification uses its own BEGIN IMMEDIATE. Inside final reservation/consumption/publication transactions, recheck bounded original input/reservation/root/freeze identities with existing-transaction helpers; do not introduce nested write-lock deadlocks. Recheck full evidence before final evaluation/publication and after derived view construction, with owner/cancel/source checks immediately before commit.

## Original accounts and checkpoints

Suggested layout: one part ordinal per frozen configuration and one trial window/file per arm, `primary_final` and `replication_final`. Freeze all2*N strategy occurrences plus one descriptive aggregate occurrence before any final price evaluation. Keep strategy config IDs equal across instruments while trial identities include their distinct window. This preserves the2*N account count, N distinct rule versions and separate aggregate role.

Persist each instrument/configuration account independently, so death after one market/version does not recompute committed financial accounts. Reuse account_checkpoints preflight/load/publish/reuse with a single window per file and a context binding job/payload/core/configuration/part/arm definition. It already checks original starts/computations/attempts/checkpoints and refuses missing committed bytes; sidecars are derived and may be repaired from originals. Different original arm reports must carry the correct complete dataset context and only their declared evaluated symbol. Worker._trial overwrites report.dataset_context when its payload has a single dataset_context; omit that ambiguous global field for a two-dataset final job or supply each arm context explicitly before computation recording.

Call the existing Lab.evaluate with frozen arm dataset/window/costs/portfolio/news/seed, selected symbol, study_id and the same consumed final_job_id. Preserve every original report/entry trace/cashflow audit. No candidate filtering is applied to account execution.

## Final reduction and saved authority

Use a bounded original arm-report mapping to compute the existing exact equal-weight family arithmetic over **every original family member** on each final instrument. Keep marked-equity versus realized-exit-day conventions separate. Preserve all zero/loss/undefined versions. Final version gates use the frozen policy (positive net profit and Sharpe0.5); do not invent an additional host gate or reinterpret an undefined statistic as zero/pass.

Root rows may remain N configuration rows with two explicit original report references, original candidate/family flags and complete per-arm metrics. The root aggregate records both instruments, complete membership, family results, source gaps and original candidate-freeze identity. A strict final reader must check original reservation/consumption/input/root/aggregate occurrence and every referenced account's complete original trial/attempt/start/checkpoint/artifact authority before granting saved final authority. Expose `inspect_final` and `read_final_account` as authored contracts require. Generic result/summary/report routes must not bypass this reader.

Publish aggregate computation/root and original checkpoint bindings atomically under the active uncanceled owner; preserve precommit file orphans. Recheck after view build on both new and reused results. Final access remains consumed even if source/financial/derived-view work fails after first access; restore original evidence and resume the same job rather than making a new final hypothesis.

## Verification and integration still required

Execute actual zero-candidate two-market/all-version accounts, first-price-read observation of one prior consumption, same-job canceled/failed recovery, concurrent reservation reuse, all-source/freeze/role/cohort/window faults, actual process deaths at consumption/part/root/view boundaries, and assertion-killed source mutations. Include actual positive candidate/control integration once the backend is stable. Close unchanged95/90 numerical coverage gates with original raw-DB reconciliation.

Then integrate public registration/qualification/final APIs, bounded dependency/row/family/stability/attrition inspection, beginner-readable UI and complete JSON/CSV/offline exports. Generation of large cohorts must happen before outcomes on the server using the existing validated sampling machinery; do not require an85MB100000-configuration HTTP request through the64MB body limit or silently replace the original frozen universe. Keep source/US-equity adaptations and unknown private recipes visible. Complete real isolated browser flows, current full regression, fresh locked installation, actual market-data100/1000/10000 workloads, separate global100000 stress and83/422/120 acceptance before installation/final certification.
