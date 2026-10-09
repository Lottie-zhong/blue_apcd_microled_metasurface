# GPU_RUNNER_LEGACY_CONTROLLER_PT72H_REBIND_COMPATIBILITY_FIX_V1

Status: PASS for formal retire/rebind only; this is not a whole-platform or continuous-production claim.

Observed 2026-10-09 UTC on DESKTOP-NNE313K as desktop-nne313k\dell.

## Rebind result

The official Runner transaction is COMPLETE. Installed task APCD_GPU_RUNNER_V1_COUPLING_SERIAL_QUEUE_CONTROLLER now points to successor request bbb7f19186776ceff07f93a17fded92b. Live Scheduler state is Ready with PT0S and IgnoreNew. It has not been started by this task.

Predecessor bb93248ca2dff9605d7885554a319394 was STOPPED_RECONCILED in the Coupling retirement receipt. The Scheduler task was replaced in place; the active action no longer references the predecessor. Its historical start_claim.json remains preserved.

Transaction: b02087204164ae25428af0794915423304931c81cfb817f601fedea1df5a139f
Durable journal: D:\apcd_runtime\gpu_production_runner_v1\scheduler_controller_v1\rebind_transactions\b02087204164ae25428af0794915423304931c81cfb817f601fedea1df5a139f\journal.json
Journal SHA256: 6f6f85ce5dabd4f6c28836c020aa7012d80cee0218cec9d1a4df16b19bed0620

The final API retry lost its SSH response. The COMPLETE journal and fresh live Scheduler/binding readback confirm the result; the rebind API was not replayed.

## Fix and validation

Root cause: predecessor validation incorrectly applied the successor's strict PT0S requirement. Windows reported the legacy task as PT72H when XML omitted ExecutionTimeLimit. Runner now validates the predecessor against a narrowly recognized legacy contract and continues to require the successor's strict PT0S, IgnoreNew, owner, identity, manifest, action, and live Scheduler checks.

Two runtime migration defects were also fixed: the admin rebind CLI was falsely counted as an active owner, and Scheduler XML omitted Enabled even though COM state showed the successor Ready. The process census now selects actual controller/worker/engine processes; when XML omits Enabled, validation uses live COM state and rejects explicit mismatch.

Focused scheduler/controller tests: 62 passed. Pushed code commits: bc5dd05c7874dc81db6a1fa45479338e44148058, 9a4c0ad718876b26ab2649846ce4fbdd8d835520, d4dc99fd5ffb0ecefc7a1b09d6e2c940c4eb2ccb.

## Successor binding

Request bbb7f19186776ceff07f93a17fded92b; manifest SHA256 bbb7f19186776ceff07f93a17fded92b036224eeaff9f95f0d1269347c58a87f.
Runtime binding file SHA256 155b81aeab5227aa99ac55bf5a9778f0c2e3fd2e79a31c1d17c9b2474dd65193; internal binding_sha256 30f8e7947c77792f6a147c49e2385728f82161b057e18515472704237595422b.
Action runs N:\anaconda_envs\RCP_LCP\python.exe and Coupling serial_queue.py, whose live SHA256 is 93d29da19fcc5b8d5df826646683a3090f785673177ece82697be01542980947.
The bound queue manifest SHA is fbcac249c59e3f242e48dfa16a8e92298c98bab48f5fe7256900b8feed10bca7. Queue snapshot SHA is 951323df115a052933afb9bd360b1500dbc8a8a3ca6c6491f6b7dabd6d6bce4d; retirement receipt SHA is 0158543576913be51462dbce1bb61a99bbd1533a38dcfe23220a0db11fa9ae52; owner decision SHA is 1d6670211141e861a6468e19f34c3d4d0d594f9b2d4ac732fe086af342cc4991.

The successor contains G027-G116 only (90 cases), max concurrency 1, one entry per case, zero automatic replay, and truth-before-next. Snapshot records zero active cases, zero pending replay, and G027-G116 remaining.

## Safety and next action

Active Runner markers were absent and the targeted controller/worker/engine process query returned zero. No duplicate active owner was observed. No solver entry was created. G026 remains FAILED_POSTENTRY_NO_TRUTH: one consumed Runner entry, replay=0, no truth, physical engine entry UNKNOWN. G027 remains unstarted.

Coupling FINAL_REPORT.md still says the successor is unbound. Coupling has unrelated dirty/staged files; none were changed or staged here. Coupling owner should refresh that handoff before dispatch.

The successor is unstarted, so Coupling owner must use the official first-start command once:
N:\anaconda_envs\RCP_LCP\python.exe D:\project\worktrees\blue_apcd_gpu_production_runner_v1\scripts\shared_fdtd\gpu_runner_v1\task_scheduler_v1.py start-controller-task bbb7f19186776ceff07f93a17fded92b
Do not use resume-controller-task for this successor. Runner owner did not start G027.

PT0S and IgnoreNew are verified on the installed task. This stage did not validate logout/reboot survival or continuous scientific production; the task principal remains DELL/InteractiveToken.