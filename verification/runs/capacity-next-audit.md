# Next measured-capacity investigation

Current core d0d24e6e256499458f47ee45cfb070e782ace2777bc9b7905558bd9a18b53c9f. No source changes made for these notes.

The declared one-session real-data100 search and exact same-seed repeat passed at29.53/29.18s, around187MB absolute process high-water mark,596kB job outputs.1000 completed in359.76s,196153344-byte process peak and5661154-byte job output,1000 completed trial attempts under the same900-second frozen cap. Other isolated mutation verification ran concurrently; throughput is observed under that host load, not an exclusive-machine optimum. No10000/100000 completion claim.

Code inspection identifies scaling concerns to profile and test before optimization:

1. Worker._many rehashes identity(job['payload']) for every configuration, traversing the entire N-configuration payload N times. Hoist an immutable job-context digest once, preserve per-part identity and full pre-publication trial-plan verification.
2. run_once.cancel() uses Store.job(), decoding the whole payload for a cancellation boolean. Add a narrow authenticated/owned cancellation-state read, preserving lease/ownership/cancel/shutdown failure semantics. Heartbeat SELECT * also materializes unused payload.
3. API public_job strips configurations only after loading them and retains full sampling proposals. Polling many large job plans needs bounded summaries while complete proposal history remains accessible in saved evidence.
4. Do not cache prices across authoritative source/manifest checks or weaken final/borrow/news guards as a shortcut. Preserve all accounting tolerances and original failed measurements.

Before source changes: wait for all recorded checks to terminate; define regression expectations for cheap cancellation/progress reads, no per-config full-plan rehash, actual stale-owner/cancel/corruption behavior and unchanged complete numerical outcomes; sharpen existing PERF-001 without deleting cases. Keep0.16 coherent checkpoint historical; after changes run appropriate full regression/coverage/recovery/browser/mutations and actual identical-sample capacity, not extrapolated claims. The main8767 service still awaits user stop of verified34016 after forced termination was rejected by automatic approval review;8770 is a separate current verification store.

## After D037 implementation

D037 removes Python whole-plan cancellation decoding, per-part whole-plan hashes and per-minute pandas subgroup creation. Its actual100 measurements remain around26–30s under concurrent verification; no speedup is claimed. Current1000 worker computation has completed; exact saved-account comparison remains a separate phase.

Further inspected scalability concerns, not yet measured conclusions:

- Job lifecycle fields and large immutable payload still share one SQLite record. Narrow SQL projection avoids Python decoding, but SQLite overflow traversal/updates may still incur payload-size work; profile before claiming constant storage IO. Consider separating immutable plans and mutable lifecycle state with an explicit transactional, backward-compatible migration, retaining all corruption/ownership guarantees. Do not weaken payload verification.
- The comparison verifier calls Lab.report for each account; that rereads/decompresses/parses the full root result, full job plan and job events N times. This is visibly quadratic code work and is outside the recorded worker-throughput timer. Use once-verified root/job/event authority plus per-part content verification for future large audit helpers; never skip original root/part/input authority.
- Public per-part report access and job-list polling also need measured large-plan response/memory bounds. Complete metadata/history must remain accessible without sending every generation proposal on every polling request.
- Do not start long10000/100000 acceptance workloads before remaining planned functionality and the final source/fixture subject are frozen; earlier component measurements remain explicitly scoped. No larger completion claim follows from1000.
