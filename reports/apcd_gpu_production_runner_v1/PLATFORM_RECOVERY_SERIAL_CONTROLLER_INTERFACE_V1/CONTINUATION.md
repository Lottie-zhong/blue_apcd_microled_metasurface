# Continuation — Runner serial-controller Scheduler interface

Runner worktree: D:\project\worktrees\blue_apcd_gpu_production_runner_v1
Branch: codex/apcd-gpu-production-runner-v1
Base HEAD before this implementation: a97245c4f64d737cb9e26763ceabc82b1cb82658.

## Completed

- Added a versioned Task Scheduler host contract for a Coupling-owned bounded serial controller. The existing Runner single-case worker remains the only case execution API.
- Added manual install/start/query/reconcile-and-resume commands with exact source/queue hash pins, ordered bounded case IDs, one active case, one entry per case, zero automatic replay and truth-before-next.
- Fixed Windows task principal SID binding for install and resume.
- Full Runner suite after final code changes: 174 passed, 50 subtests passed across 15 modules; focused Scheduler/controller suite: 35 passed.
- Real Windows Task Scheduler synthetic test passed across separate SSH calls: controller progress after client return, duplicate start refusal, exit 73 surfaced for reconciliation, status-bound resume exited 0, fake truth-before-next verified. Entry, FDTD and replay counts were zero.
- Deleted only the named temporary synthetic task. Kept small proof files beside the report.
- No Coupling files or ledger, production case authority, production task, queue or solver was modified or started.

## Live Coupling compatibility snapshot

Runner and Coupling manifest validators both pass for the current Coupling working-tree candidate serial_queue.py SHA256 5ede3c2b2d85c225f73041a5d9332397bfa6fa03d91c39c8bba40089131d5ae5 and queue manifest raw SHA256 fbcac249c59e3f242e48dfa16a8e92298c98bab48f5fe7256900b8feed10bca7, using read-only case K6LDA1_DEV_D2_P05. No status path was created.

The claimed official source hash 3499b93302857cf3e93cdf4b3832e042e0680574a2e2692ffc739eb40947ce05 was rejected by Runner as a source SHA mismatch. The current Coupling source is dirty; current content SHA is 5ede3c2b... while the committed HEAD copy SHA is 8865671d... . Coupling must resolve this pin/working-tree mismatch and provide an approved clean version before production Task Scheduler installation. The Runner task has not installed or started the production Coupling controller.

The current source includes a P05 FAILED_PREENTRY reconciliation path, but this Runner audit did not invoke it. Fresh Coupling-owned reconciliation and durable receipt remain preconditions for a production queue start.

## Next, in order

1. Coupling owner resolves the official source SHA discrepancy and supplies the exact clean source and manifest.
2. Coupling owner performs and records startup reconciliation of the P05 FAILED_PREENTRY state; preserve G023 as entered/no-truth with no replay.
3. Re-run the live manifest validator against the approved committed source hash and queue manifest.
4. Install the production controller task only after source/manifest and execution authority are reviewed. Installation does not start it.
5. Review the exact case subset and budgets before a manual start. On loss, query and reconcile; resume only with status-bound receipt and terminal Runner handoffs.

Task Scheduler uses DELL InteractiveToken. SSH disconnect survival was verified; logoff behavior was not.


## Reproducible verification

Run from D:\project\worktrees\blue_apcd_gpu_production_runner_v1:

    N:\anaconda_envs\RCP_LCP\python.exe -m pytest -q scripts/shared_fdtd/gpu_runner_v1/test_controlled_admission_v1.py scripts/shared_fdtd/gpu_runner_v1/test_controlled_monitor_extraction_v1.py scripts/shared_fdtd/gpu_runner_v1/test_controlled_preentry_h5_v1.py scripts/shared_fdtd/gpu_runner_v1/test_d6_m05_orphan_closeout_v1.py scripts/shared_fdtd/gpu_runner_v1/test_d6_p05_orphan_preentry_recovery_v1.py scripts/shared_fdtd/gpu_runner_v1/test_g023_postentry_closeout_v1.py scripts/shared_fdtd/gpu_runner_v1/test_gpu_runner_v1.py scripts/shared_fdtd/gpu_runner_v1/test_gpu_runner_v1_adapter.py scripts/shared_fdtd/gpu_runner_v1/test_k6_v2_solver_budget_v1.py scripts/shared_fdtd/gpu_runner_v1/test_power_fraction_normalization.py scripts/shared_fdtd/gpu_runner_v1/test_queue21_exception_and_global_hold_v1.py scripts/shared_fdtd/gpu_runner_v1/test_queue_controller_lifecycle_v1.py scripts/shared_fdtd/gpu_runner_v1/test_queue_controller_task_scheduler_v1.py scripts/shared_fdtd/gpu_runner_v1/test_session_lifecycle_v1.py scripts/shared_fdtd/gpu_runner_v1/test_task_scheduler_v1.py

Final result: 174 passed, 50 subtests passed. Focused Scheduler result: 35 passed. Specific duplicate-owner, process-loss/reconcile, one-slot/zero-replay and truth-before-next coverage is listed in FINAL_REPORT.md.

Pre-commit snapshot: branch codex/apcd-gpu-production-runner-v1; base HEAD a97245c4f64d737cb9e26763ceabc82b1cb82658; upstream divergence 0/0; exact Runner allowlist only. The final Git commit and push result are in the completion response.


## Query status key fix

A delegated live snapshot reported Task Scheduler State=Running (LastTaskResult 267009 / 0x41301) and controller status RUNNING for K6GDP2_DEV_G024, but Runner query mislabeled it as exited. Windows returns State with uppercase S. Runner now normalizes state keys case-insensitively across worker/controller task consumers and fails closed on conflicting duplicates.

Exact targeted command, from the Runner worktree:

    N:\anaconda_envs\RCP_LCP\python.exe -m pytest -q scripts/shared_fdtd/gpu_runner_v1/test_task_scheduler_v1.py scripts/shared_fdtd/gpu_runner_v1/test_queue_controller_lifecycle_v1.py scripts/shared_fdtd/gpu_runner_v1/test_queue_controller_task_scheduler_v1.py scripts/shared_fdtd/gpu_runner_v1/test_gpu_runner_v1_adapter.py

Result: 61 passed in 26.39s. Regression tests supply Task Scheduler-shaped State=Running and LastTaskResult=267009: query returns RUNNING and resume refuses an active task. This fix was tested offline only; the running production task was not queried or touched. Solver, FDTD and replay counts for this fix are zero.


## Task Scheduler request resource binding and Windows State normalization (2026-10-07)

Runner V1 now reads the Task Scheduler State property case-insensitively. Windows-shaped records such as {"State":"Running","LastTaskResult":267009} remain RUNNING; conflicting case-variant state keys fail closed. The same helper is used by request query, controller query/start/resume, and worker wait logic.

The scheduled run-one request now snapshots validated APCD_GPU_RESOURCE_NAME into its durable request body. The request SHA covers this field, and a second submission for the same pinned request with a different resource name is rejected as SCHEDULED_REQUEST_ID_COLLISION. The Task Scheduler worker passes the request-bound value explicitly to NativeAdapter; worker correctness no longer depends on inheriting the submitter's process environment.

This fixes the reported G024 failure path: RUNNER_ERROR:SCHEDULED_WORKER_FAILED:GPU_RESOURCE_NAME_REQUIRED (runner log SHA256 4fb05209de2e51d3e2846f308bb8297b3450dd4eedde1baa343cea9dc0668d1a). Supplied runtime evidence classifies it as pre-entry: no Runner registry row or attempt directory was created and entered_count remains 35. Coupling must reconcile that case as zero-entry/pre-entry before any later queue call. This Runner change did not query or modify the production Task Scheduler task and did not resubmit G024.

Validation: targeted Task Scheduler, controller lifecycle, controller Task Scheduler, and adapter tests: 63 passed. No production case, FDTD run, solver entry, replay, or training was started.
