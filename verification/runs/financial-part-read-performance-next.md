# Remaining financial-part read bottleneck

This is an implementation handoff, not a completed feature or acceptance receipt.
Keep all83 requirements,422 mandatory cases,120 baseline combinations,51 numerical
modules,95/90 coverage thresholds and both original10000-set policies unchanged.

## Observed evidence

- The stable92b24901 source executed six genuine paired parts,288 financial sets,
  before normal cancellation. No final dates were consumed. The sixth part took
  767.09s after the four-part decoded cache stopped holding every original book
  source. Preserve the canceled full-run receipt rather than claiming completion.
- `20261110T145004120145Z-control-part6-live-profile` sampled the real owned
  worker:85% in `_entry`,79% in `_load`,75% in `_book_shape`,59% in `_control_db`.
- Physical-file identity polling is now implemented. Its19 tests pass and the
  120000-query benchmark retains every fresh SQL query, reducing median30000-poll
  time from14.328s to4.319s. Numerical outcomes are unaffected.
- Pure book-manifest digest reuse is now implemented, with fresh book hashes,
  manifest verification and cancellation checks. Its corrected60-case regression
  passed in receipt20261110T155951599290Z; its wall time includes6020.7s of
  observed Modern Standby. Original durations remain intact.

## Code-level cause still requiring closure

`FinancialParts._prefix` calls `_load` on every committed part at both boundaries
of each new part. `_load` parses original set/book JSON and revalidates all book
manifests and occurrence witnesses. `_entry` also loads a complete old part when
the decoded LRU evicts it. Thus a bounded four-part cache can repeatedly decode
and validate the same unchanged originals. Do not merely enlarge the cache or
skip original file, event, input, trial, attempt or checkpoint checks.

## Required approach to implement and verify

1. Factor the existing occurrence checks into one shared routine without changing
   their predicates or error behavior. It must re-read the current trial,
   attempt, original start/computation/checkpoint events and publication order.
   Keep the expected computed-row digest bound to the original part bytes.
2. After a complete original part has been validated, retain only a bounded,
   immutable projection: original publication ID/details/file digest, exact book
   bindings, and each set's ordinal/policy/computed digest plus original event
   witnesses. This is expected data projected from verified immutable bytes,
   not a boolean pass flag or a financial result.
3. A prefix-only check can use that projection only after freshly verifying
   current owned inputs, original publication identity, complete original file
   digest, exact current book index and every current occurrence witness. Refuse
   changed authority. Reparse and fully validate after projection eviction or
   when no verified projection exists. Never silently adopt a replacement
   original publication.
4. Book retrieval must still check its current index locator and complete book
   and manifest digests. Within one existing before/after authority unit, retain
   bounded immutable serialized entries from each fully read original part so
   an evicted decoded part need not be reparsed for every different book. Verify
   original closing authority before publishing; retain no unit authority across
   a boundary without fresh original checks. Outside a unit, perform the complete
   required original checks. Enforce explicit entry/byte bounds and honest RSS
   measurements; serialized-size estimates alone do not bound process memory.
5. Keep the existing original saved readers independent of mutable derived views.
   No prices, signals, financial outcomes, gates, draw membership, random seed,
   original quantity, execution policy or set count may change.

## Verification required before another long run

- Generate real small owned parts through the existing worker/plan. Exercise at
  least six parts or an intentionally smaller decoded-cache budget that forces
  eviction; keep the actual10000-set plans. A partial fixture is not a complete
  statistical-control proof.
- Compare complete books, rows, digests and independent exact totals before and
  after the read optimization. Count actual JSON decodes, book-manifest builds,
  original-file hashing and SQL witness reads across repeated prefix/book access.
- Alter original bytes, publication IDs/details, book locators/bindings, trial
  state/attempt/digests, start/computation/checkpoint events and protected source
  inputs after warm-up and during an authority unit. Include rehashed mutable
  metadata and a changed witness near the end. Every mutation must be refused
  before a new part/result is certified.
- Verify cancellation/lost owner at cache hits and misses, nested scope cleanup,
  memory/entry limits, oversized fallback, eviction, absent/changed originals,
  publication failure and legitimate retry/reopen. No new financial computation
  may replace a committed original part.
- Measure real eviction-boundary latency and RSS. Then run the untouched complete
  both10000-policy positive fixture, original candidate freeze, both final
  instruments/all versions and full exports on one stable source.
- Finish the complete base/research regression and actual51-module gates, real
  market/resource and100000financial stress, locked installation and full final
  conformance audit. Do not promote partial fixtures or microbenchmarks to them.

## Verification tooling follow-up

The live progress plugin now uses `len(session.items)` during collection and
reconciles terminal counts. The real19-test follow-up reported19 collected and
19 passed. Long runs have a process-scoped Windows system-idle request, released
on completion; manual sleep is respected. Receipt20261110T175753682962Z verifies
the request was acquired and released. Do not edit recorded inputs during a run.
