
# Continuation - G025 Postsolver Truth Recovery

Checkpoint: 2026-10-08T16:06:51Z

## Runner result

- Case/run: K6GDP2_DEV_G025 / attempt_001 - K6V2_G025_20261008T140327Z_454d6858
- Coupling controller request: bb93248ca2dff9605d7885554a319394
- Runner scheduled request: 28c992f00bb8b032ecf06f4d8e8dc431
- State: DONE; scheduled request: TERMINAL, exit code 0.
- Counts: original solver entry 1; recovery solver invocation 0; replay 0; G026 starts 0.
- Final read-only check: no FDTD engine process, no live Runner lock/active pointer, Runner controller and worker Task Scheduler entries are Ready. The worker's last result remains 0xC000013A from the original interruption, not the recovery request result. No target G025 worker/recovery process was running at closeout.
- Runner registry hash: 87be083bb44ed2249b2a743c5ed20a588e4eae619083d1b89b4b83ec0debe634; the G025 row is terminal DONE with one entry, zero replay, and proof hash 0c7f82200042da8ceb828e6959fab3421bad2e160cc0f3eb7f6c365545f0054e.
- Live root markers are absent; the original marker files are preserved under the recovery directory with hashes in the receipt.
- Global control snapshot remained PASS, generation 27, hold 0. No control DB mutation was performed.

## Coupling handoff

Use the Runner receipt at:

D:/apcd_runtime/gpu_production_runner_v1/recovery/K6GDP2_DEV_G025/attempt_001/K6V2_G025_20261008T140327Z_454d6858/postentry_truth_recovery_20261008T155828634686Z/recovery_receipt.json

Receipt file SHA256: e547914ccceead7d761e0e9c0ca1edaa0fa0b44df7001181792db23159422ef7

Runner terminal result:

D:/apcd_runtime/gpu_production_runner_v1/requests/scheduled_run_one_v1/28c992f00bb8b032ecf06f4d8e8dc431/result.json

Result file SHA256: 4b2ce650de491af681590d8eeb26bf69595742c895b5fb9ab08f40e1b33f953f

Truth bundle is under:

D:/apcd_runtime/gpu_production_runner_v1/runs/K6GDP2_DEV_G025/attempt_001/K6V2_G025_20261008T140327Z_454d6858/

Coupling should consume the receipt and result, reconcile G025's ledger/controller state and label counts, and only then decide its next queue action under its existing authority. GPU Runner did not write Coupling files or restart the queue.

## Remaining boundary

The original worker persisted no exception/phase record. Its exact post-solver failure substep remains UNKNOWN; the receipt preserves this, plus solver_callback_return_observed=false. Do not infer the initial failure from the recovery result. No G025 replay or G026 run is authorized by this closeout.

The generic Runner patch adds phase tracking and durable traceback output for Python-caught exceptions. This does not capture externally terminated processes after termination; any remaining controller-level cancellation path must be investigated separately if Coupling requests it.
