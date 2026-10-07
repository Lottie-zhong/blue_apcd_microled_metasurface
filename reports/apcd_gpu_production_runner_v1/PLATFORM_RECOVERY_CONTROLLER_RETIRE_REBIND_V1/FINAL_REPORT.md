# Runner V1 controller retire/rebind closeout

STATUS: PARTIAL — the versioned controller lifecycle API is implemented and validated offline. Production retirement/rebind was not executed.

GPU Runner owns the single-case worker and versioned, journaled controller retirement/rebind API. Coupling ML owns queue reconciliation and scientific case dispatch.

## Implemented and verified

- task_scheduler_v1.py adds lifecycle serialization and a journaled retire/rebind transaction. It verifies owner retirement evidence and pinned hashes, current queue/status and request reconciliation, old task/process/slot state, and an allowlisted successor-manifest delta. It creates the successor task disabled, switches the binding, then enables it without launching the task. Journal phases are monotonic and recoverable.
- Worker/request execution paths stay outside the lifecycle mutex; the existing one-worker slot, entry behavior, and no-replay policy are unchanged.
- test_queue_controller_task_scheduler_v1.py adds synthetic rejection, isolation, state-drift, and interrupted-transaction recovery tests.
- DESKTOP-NNE313K, base HEAD 671745718a8d70bc5076b59a2236e8a3ea8703f: pytest scripts/shared_fdtd/gpu_runner_v1 -q = 204 passed, 50 subtests passed in 42.40s. Ruff passed on both changed files. git diff --check passed.
- No production controller rebind was run.

## Live evidence and blocker

The current binding still targets request f0aeb35290a77db5c05c0346f1a40f81 and queue K6V2V128REMAINING20261007105811Z. Binding-file SHA: 1593BF3514014AAF7D3F4EA028F01AF33FB196E39EF3FE7909320996745BA5AA.

Coupling status CONTROLLER_STATUS_K6V2SERIAL20261007T105811Z_ce8009d2 remains RUNNING/current case K6GDP2_DEV_G024, with no runner request IDs. Status SHA: 0090880A1F0D5F6A34FBF1A557C0093E506276159C59C9B16C2FD89726EEE400. Runner G024 is terminal FAILED_POSTENTRY_NO_TRUTH: one entry, no truth, no physical GPU engine observation, replay 0. Runner closeout records CONTROLLER_EXITED_NEEDS_RECONCILIATION, so the Coupling status/queue snapshot is stale for retirement. No successor manifest or owner retirement receipt was found. Old binding remains and API was not called.

At the live process check, Runner tasks were Ready/enabled, runner slot/lifecycle markers absent, and no fdtd-engine-msmpi.exe. Eight fdtd-solutions.exe -server -hide API processes and three python.exe - processes remained: PIDs 29236 and 33316 are parents of two API instances; PID 18936 has parent PID 45704 and its script purpose is not identifiable from its command line. No fdtd-engine-msmpi.exe was present, and none of these processes were terminated.

This maintenance: solver entry 0, FDTD run 0, replay 0, case launches 0. Do not replay G024 or create a replacement attempt.

## Sole next step

Coupling owner reconciles terminal G024 in the current queue/controller ledger and provides a successor manifest plus current owner-approved retirement receipt and queue snapshot. Runner then revalidates those exact inputs and invokes the versioned API. Until then no queue case starts.
