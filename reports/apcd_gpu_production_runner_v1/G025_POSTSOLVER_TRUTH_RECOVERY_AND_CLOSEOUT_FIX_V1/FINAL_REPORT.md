
# G025 Postsolver Truth Recovery and Closeout

## Status

**PARTIAL overall; G025 truth recovery and formal closeout are complete.** The original post-solver interruption substep cannot be determined because the worker did not persist its exception or stage record.

## Case and original evidence

- Case/attempt: K6GDP2_DEV_G025 / attempt_001
- Run: K6V2_G025_20261008T140327Z_454d6858
- Coupling controller request: bb93248ca2dff9605d7885554a319394
- Runner scheduled request: 28c992f00bb8b032ecf06f4d8e8dc431
- Original solver accounting remains entry=1, invocation=1. Recovery invocation count is 0; automatic replay count is 0.
- The original Lumerical log records 314,700 iterations, "Finished collecting data", and successful simulation completion. The run FSP and sibling native H5 were present; the durable truth H5, validation, and final hashes were absent or pending at intake.
- The worker Task Scheduler result was 0xC000013A; no original exception/traceback or durable phase record exists. Thus the evidence places the unresolved transition after the solver's logged completion and before Runner truth/terminal closeout, but it does not identify whether the original failure was in callback return, post-solver handling, truth export/validation, archive, or state commit. The receipt records solver_callback_return_observed=false. The outer SCHEDULED_WORKER_REQUIRES_RECONCILIATION message is not treated as the root cause.
- A recovery attempt captured OSError: [Errno 9] Bad file descriptor while fsyncing a read-only copy handle. The copy was changed to a writable durable handle and covered by a regression test. This is a recovery-tool issue, not evidence of the original worker failure.

## Zero-solver recovery and closeout

The isolated recovery used the existing production NativeAdapter.fresh_load_validate path against the saved FSP and sibling H5. It did not call run() or start an engine. It recovered truth.h5, raw complex fields, state, orders, and projection artifacts; checked hashes and finite complex E/H data for the required MON_IN, MON_PRENP, and MON_POSTNP monitors; then performed the Runner terminal transitions and archived the stale control markers byte-identically.

Fresh LOAD result:

- fresh_load_verified, monitors_valid, state_valid, and scientific_valid: all true.
- Each monitor returned shape [349, 59, 1, 21], with six finite complex E/H components and 21 actual wavelengths from 440 to 460 nm.
- Actual z samples: IN -100.7877394088879 nm; PRENP 1152.0 nm; POSTNP 1801.9999999999932 nm.
- Maximum energy closure: 1.1102230246251565e-16.

Durable Runner state is DONE; the registry has one G025 row with entry/invocation 1, replay 0, and the recovery proof hash. The scheduled request is TERMINAL with exit code 0. .runner.lock, active_run.json, and scheduler_worker_v1.lock are absent from the live root; their original bytes and hashes are preserved under archived_control_markers. At the final live check there were no FDTD engine processes and no G025 recovery/worker process. Global control remained PASS at generation 27, hold 0; this task did not modify the control database. G026 was not started.

## Minimal generic fix and validation

runner.py now tracks coarse execution phases and, when Python catches an exception, durably writes the original exception type, message, phase, solver-entry state, and traceback before returning the wrapped error. This improves evidence for caught Python failures; it cannot recover an exception after an external hard process termination.

The new zero-solver recovery API validates the exact request, contract and artifact pins; requires the unique entered G025 attempt and idle worker/engine state; uses isolated input copies and fresh LOAD only; verifies the truth bundle; then records terminal state, release evidence, and a scheduled result. It is case/run pinned and does not add replay behavior.

Validation on the production Runner worktree:

- Python compile check: passed for all four changed Python files.
- Focused post-entry recovery tests: 6 passed.
- git diff --check: passed.
- Real G025 saved-FSP fresh LOAD proof: PASS, recorded in the receipt.
- No full Runner suite or new canary was run; no solver was run during recovery.

## Consumer handoff

Formal recovery receipt:
D:/apcd_runtime/gpu_production_runner_v1/recovery/K6GDP2_DEV_G025/attempt_001/K6V2_G025_20261008T140327Z_454d6858/postentry_truth_recovery_20261008T155828634686Z/recovery_receipt.json

Receipt file SHA256: e547914ccceead7d761e0e9c0ca1edaa0fa0b44df7001181792db23159422ef7

The receipt, terminal result.json, truth artifacts, and this inventory are the Runner-side inputs for Coupling to reconcile G025 and align its ledger/controller. GPU Runner did not edit the Coupling ledger or controller request and did not start G026. The original interruption substep remains unknown; the Coupling-side reconciliation is still pending.
