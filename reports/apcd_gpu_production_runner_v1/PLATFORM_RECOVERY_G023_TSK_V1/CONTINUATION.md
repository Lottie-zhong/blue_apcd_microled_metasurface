# PLATFORM-RECOVERY-G023-TSK-V1 Continuation

Read this file before resuming.

## State

- Remote host: `DESKTOP-NNE313K`, user `desktop-nne313k\dell`.
- Runner worktree: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1`; branch `codex/apcd-gpu-production-runner-v1`.
- Task Scheduler API code and G023 post-entry closeout are present in the Runner worktree; report inventory records their hashes.
- G023 `attempt_001` is formally `FAILED_POSTENTRY_NO_TRUTH`, one entry consumed, zero replay, quarantined. Never relaunch it.
- Production Scheduler task `\APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER` remains installed. Synthetic test tasks were unregistered after evidence capture.
- No real solver/FDTD was launched by this task.

## Serial contract

One active case maximum. The current case must terminalize, persist and validate truth, reconcile with Coupling, and release the Runner slot before a subsequent case may dispatch. Pre-entry failures are not scientific entries but must be reconciled before later dispatch; retire the old run ID. Post-entry failure consumes entry budget and is never automatically replayed.

## Required integration before qualification

Coupling must implement a versioned, bounded queue-controller entrypoint that owns queue progression, Runner request submit/query, terminal reconciliation, and stop conditions for its entire lifetime. Task Scheduler must launch that controller directly; a Scheduler worker behind an SSH-owned `serial_queue.py` process does not satisfy the requirement. Do not run current `serial_queue.py --execute`: it is unbounded over the 93 remaining cases.

Runner P05 recovery at `4c0de1c613612d9e23dd1ad9d8e17023322087c9` returned `RECOVERED_FAILED_PREENTRY`, entry=0/replay=0, with 26 offline tests passing. Coupling fixture reconciliation nevertheless returned `ENTERED_CASE_NEEDS_AUDIT:K6LDA1_DEV_D6_P05`. The Coupling owner must add an explicit versioned pre-entry reconciliation fix before queue progression. Preserve all unrelated dirty Coupling worktree files.

After code is available: run offline contract/concurrency/reconcile tests, install the bounded full-controller Scheduled Task, perform zero-solver caller-disconnect and controller-restart lifecycle tests, verify only one active case and no replay, and inspect Task Scheduler history. This task does not authorize any solver start. Actual desktop logoff remains untested for the current `InteractiveToken` worker.

## G023 evidence

See `FINAL_REPORT.md`, `TASK_SCHEDULER_SIMULATION_EVIDENCE_V1.json`, and `SHA256_INVENTORY_V1.json`. Formal receipt lives under the G023 runtime `postentry_closeout_v1` directory. Do not alter Coupling ledger from this Runner worktree; Coupling owner owns its reconciliation.


## Latest final host census

The final read-only audit observed eight `fdtd-solutions.exe -server -hide` API processes with Python metadata/API script parents. CPU time did not materially increase over a 3-second sample. No FDTD engine, MPI process, or Runner/Coupling queue controller process was found. The API processes were not stopped. GPU showed 1% utilization and 2164/10240 MiB in use by shared desktop applications; do not treat this as proof of free GPU capacity. See `FINAL_RESOURCE_CENSUS_V1.json`.


## Follow-up hard blocker (2026-10-07)

No full Coupling queue task was installed because current Coupling `serial_queue.py` is still an unbounded `--execute` loop and its current startup reconciliation rejects P05's Runner `RECOVERED_FAILED_PREENTRY` state (`ENTERED_CASE_NEEDS_AUDIT`, serial_queue lines 949-951). The source is SHA256 `87ca459881e641ab5bf026767928bc09ec6470a4a0404d886331bddab4519966` at Coupling HEAD `bb4e105308cdb45e2a2df300cd08af3e01fdb920`; Coupling worktree was dirty and untouched. Do not register/run it until Coupling owner supplies versioned pre-entry reconciliation plus a safe bounded/restartable controller interface. No solver was started.

Synthetic Runner lifecycle test module `test_queue_controller_lifecycle_v1.py` now covers detached submit, controller exit/worker continuation and stale-state reconciliation, pre-entry stale-claim fail-closed behavior, and duplicate submission. Focused tests: 43 passed. These do not qualify the real Coupling controller.

Historical V3 provenance is recorded in `TASK_SCHEDULER_SIMULATION_EVIDENCE_V1.json`; only atomic persistence and fail-closed dead-process reconciliation principles are reused. No V3 loop, retry, hold release, task trigger, allocator or queue is ported.
