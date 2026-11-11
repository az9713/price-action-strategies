# Proposed bounded account publication unit

Status: design and authored contracts only; not adopted into production while the
7ac7b05e original10000 benchmark is active. No budget or acceptance reduction.

Evidence: the nonblocking current worker profile
20261110T215106991510Z selected211 main samples: checkpoint publication45.97%
inclusive, original trial verification25.12%, static source checks18.48%, and
main progress/heartbeat16.59%. Inclusive percentages overlap. This is a short
profile, not a complete bottleneck or market-capacity certificate.

Proposed first change:

- Prepare at most8 independent complete account reports. Every real computation
  keeps its own original configuration, start/attempt/computed record and report.
- Bound retained report batches by8MiB canonical encoded bytes (an encoded-size
  bound, not an RSS guarantee). A larger single account uses the existing single
  publication path. Jobs smaller than8 accounts retain individual publication.
- Write private candidate files before acquiring the writer. In one BEGIN
  IMMEDIATE transaction, freshly verify the complete original plan and source,
  then validate every original attempt/computed result before promotion.
- Verify ownership/cancellation and candidate hashes, preserve prior uncommitted
  files, promote the original bytes, and record each original window checkpoint.
  Commit the whole unit. A failed unit certifies none of its candidate files;
  previously committed units remain original and reusable.
- Whole-plan verification may be shared only inside this same exclusive writer
  snapshot. No expected projection or passing result bypasses a later transaction.
  Closing source/owner/cancel checks remain required.
- Display progress after actual committed units. Flush the final partial unit;
  checkpoints/events/attempts and exact result rows retain all individual accounts.
  Cancellation is checked during computations and immediately before publication.
- Preserve small-job callback/death contracts; add real8/9/16-account process-death,
  canceled/owner/source/window/hash/candidate corruption and rollback boundaries.
  Original proof after restart must not trust a progress integer or orphan file.

Required evidence before adoption: exact original one-account API compatibility;
SHA-bound old/new complete financial account parity; full-plan fresh queries once
per real writer snapshot; no passing gate outside that snapshot; all8 original
attempts/events/files retained; real process death/recovery at candidate and
transaction boundaries; actual encoded bound/oversized/tail/reuse behavior; fresh
100/repeat1000/10000 capacities under unchanged900s/3GiB/2GiB limits; full control,
51-module95/90,83/422/120 and final acceptance unchanged. The root/stage plans must
be updated before implementation, after the current recorded run is terminal.
