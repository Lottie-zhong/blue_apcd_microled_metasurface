# Continuation: COUPLING_ML_CONTROLLER_STATUS_PATH_CONTRACT_REPAIR_AND_PRODUCTION_RECOVERY_V1

Read this file first after any context loss. Do not start or resume request bbb7f19186776ceff07f93a17fded92b; its start claim is consumed and it exited before G027. Retire it through the formal Runner API after completing the official stop reconciliation, then bind a new request.

## Scope and authorization

User authorized a new successor and formal retire/rebind, followed by the existing K6 V2 development queue G027-G116 after all gates pass. No new case, no extra entry budget, no replay, one slot, truth-before-next, confirmation responses sealed, no training or solver outside the existing queue. Do not modify the bound predecessor manifest or terminate unrelated Lumerical API servers.

## Verified host and worktrees

Remote identity verified through NetBird SSH: DESKTOP-NNE313K / dell.
Coupling worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1, branch work/mdc-np-coupling-ml-v1.
Runner worktree: D:\project\worktrees\blue_apcd_gpu_production_runner_v1, branch codex/apcd-gpu-production-runner-v1.
Remote AGENTS.md was not present at the canonical project root or either worktree root; follow the user-provided AGENTS.md instructions.
Preserve all pre-existing staged, dirty and untracked Coupling files; only stage this task's exact allowlist.

## Root cause

The immutable predecessor request bbb7f19186776ceff07f93a17fded92b has manifest SHA-256 bbb7f19186776ceff07f93a17fded92b036224eeaff9f95f0d1269347c58a87f and binding SHA-256 155b81aeab5227aa99ac55bf5a9778f0c2e3fd2e79a31c1d17c9b2474dd65193. Its status_path points into the G026 task report directory. Coupling serial_queue.py requires the status file under the active queue report root, which is the parent of the frozen queue manifest. Runner accepted the broader Coupling-root path, so the request was bound and failed at Coupling startup with CONTROLLER_STATUS_PATH_OUTSIDE_REPORT_ROOT. The request was started once; status is missing, Scheduler is Ready with LastTaskResult=2, G027 has no attempt, and solver entry for this request is zero. Never retry the old request.

## Repair in progress

Coupling serial_queue.py now derives a request-specific CONTROLLER_STATUS_<controller_run_id>.json directly under the current queue-manifest report directory, validates the same root and filename, and has a narrowly constrained legacy validator for the already-bound predecessor only. The successor builder verifies old manifest/request/binding/source-manifest lineage and requires the predecessor's formal STOPPED_RECONCILED status before writing a new manifest exclusively. New manifest stays in the queue report root; the old manifest remains unchanged.
GPU Runner owner was sent a precise request to make _controller_manifest reject status_path outside the queue-manifest parent and add focused tests. Do not edit Runner worktree from this task.

## Latest verified starting counters and runtime state

At the last read-only snapshot: 38 entered, 34 truth-valid, 34 labels-valid, 90 unentered; automatic replay=0, training fits=0, P_scale fits=0, confirmation response access=0. G027 was absent from entered/truth/label sets, had no case record and no attempt_001 directory. Runner active_run.json and .runner.lock were absent. Controller task was Ready, LastTaskResult=2, ExecutionTimeLimit=PT0S, MultipleInstancesPolicy=IgnoreNew, LogonType=InteractiveToken. Eight fdtd-solutions.exe processes were observed in API server mode and were left untouched; none matched controller/worker/engine activity. The Runner slot check classifies fdtd-engine, not fdtd-solutions API servers, as active solver work.

## Current next action

1. Run official serial_queue.py --reconcile-controller-stop-only for predecessor bbb7... using its exact runtime manifest path, SHA and request ID. This is zero-solver; it should preserve status-missing-before-reconciliation and create the predecessor-specific stopped status/receipt and evidence.
2. Use the new Coupling builder to create a unique successor manifest in the frozen queue report root, keeping the authorized G027-G116 allowlist and current queue contract.
3. Wait for the Runner ownerºw^~)Þus validator fix. Generate owner-decision and queue-state evidence, then call formal retire_rebind_controller_task once using the verified hashes.
4. Read back the installed task, binding, PT0S/IgnoreNew action and status path. Complete full actual-code zero-solver dry-run and confirm G027 remains the first unentered case and confirmation data remain sealed.
5. Only then call formal start-controller-task once for the new request. Confirm actual G027 entry, truth and label acceptance before claiming production resumed. Stop immediately on a new license/post-entry ambiguity; never replay an entered case.

No stop reconciliation or new rebind has yet been performed at this checkpoint.