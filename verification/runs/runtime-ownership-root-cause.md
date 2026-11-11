# Old-server root cause and corrective evidence

Scope: the price-action project only. This is an operational investigation, not final application acceptance.

Three causes are distinguished:

1. Agent workflow left separate, deliberately isolated verification servers alive after their checks. The old0.15 store on8769 and0.16 verification store on8770 were later retired after checking both queues empty. Future server work uses a managed foreground session and explicit retirement, rather than detached launchers. The user authorized the agent to terminate owned obsolete servers; no further manual PID requests are needed.
2. The currently verified managed Windows tree contains virtual-environment launcher44564, actual HTTP interpreter30100 and spawned numerical worker33240. These are parent/child processes, not three independent HTTP services. The fourth child types in earlier taskkill outputs were not recorded, so they are not labeled as trackers or console hosts. The user's34016/T/F command already removed that tree; a later “not found” response was expected. An outdated repeated prompt was an agent cleanup/communication error.
3. The prior API lifespan put worker shutdown after yield without finally. The first authored execution actually left its spawned worker alive when the lifespan body raised. The old worker also received console SIGINT directly, as observed during managed Ctrl+C shutdown.

D037 corrections:

- An OS-held, noninherited StoreLease protects each resolved data store for the complete worker-enabled API lifespan. Another port cannot start a second API/worker for that store. Stale lock-file existence is not ownership; unrelated processes/listeners are untouched. Separate explicit test stores are still possible, with cleanup required.
- finally handles normal and exceptional lifespan exit and failed spawn. The worker ignores console SIGINT; the parent drives the stop event and existing durable shutdown path. The existing parent-death watcher remains.
- Health reports actual HTTP/worker PIDs and whether the store lease is held. The managed main session can be stopped with Ctrl+C by the agent; no shutdown HTTP endpoint or arbitrary process-killing feature was added.

Evidence:

- First contract execution: verification/receipts/20261108T195458151748Z-runtime-capacity-authored-contract-first-execution.json —17 failed/1 passed. It retains the actual exceptional-lifespan worker leak and overhead counterexamples; missing new capabilities are distinguished from existing product failures.
- Current75-test regression: verification/receipts/20261108T200252304073Z-runtime-capacity-final-owner-replacement-real-parent-crash-and-sigint-regression.json — all passed, including real OS ownership/crash/restart, actual spawned worker lifecycle, child signal handling, final ownership transfer and existing API/recovery cases.
- Actual main duplicate launch: verification/receipts/20261108T200502458837Z-runtime-ownership-actual-main-duplicate-other-port-refused-and-obsolete-instances-closed.json —8771 startup exited3 with the store-owned error; the original HTTP30100/worker33240 stayed live.8768/8769/8770/8771 were closed. Current numerical subject3e7b6f8e87fa792e6d6caa828f2ba72646e1e17914a80df5d2bd988e57143d4e.

Full regression, broader workflow/capacity and final conformance results have their own receipts. This investigation does not promote their pending outcomes to passes.

Completed actual managed restart: before-stop identity snapshot20261108T203458018529Z, post-stop proof20261108T203512561967Z and restarted-current-main proof20261108T203545872728Z. The old three process objects exited,8767 closed and the OS lease was reacquired. The Ctrl+C tool reported interruption status1; the application logged completed shutdown without a worker KeyboardInterrupt traceback. It is not relabeled exit0. The final restarted main has HTTP34232/worker49400 at this capture time. These identifiers are observations, never instructions to kill a PID later. Full1468 and all15 numerical gates pass; broader release acceptance remains incomplete.
