# Continuation — GPU Serial Batch Production Stabilization V1

Checkpoint: 2026-10-09T05:02Z

## Runner delivery

- Baseline HEAD checked: 661fa47274d796f98322ff56a9914776042b3cef; branch codex/apcd-gpu-production-runner-v1; upstream ahead/behind 0/0 before this delivery. The report commit is the current branch head after push.
- The exact changed Runner files and SHA256 values are in SHA256_INVENTORY_V1.json. The production-code changes are limited to license preflight/revalidation, generic post-entry failure closeout, and Task Scheduler persistence settings.
- Focused remote tests: 112 passed, 40 subtests passed, 37.14s; exit 0. git diff --check passed.
- Current global admission check read-only result: PASS, hold 0, generation 27; active hold/lease/reservation lists empty. No production DB writes were made.

## Current case and queue state

- G026 / attempt_001 / K6V2_G026_20261009T025353Z_06303b44 has one entry, one invocation, zero replay, no truth. The formal generic closeout receipt and verification are at the paths and hashes in FINAL_REPORT.md and SHA256_INVENTORY_V1.json. Live Runner validation returned true.
- Coupling continues to reject resume with UNAUTHORIZED_FAILED_POSTENTRY_CASE:K6GDP2_DEV_G026. Coupling owner action: import/reconcile the generic G026 receipt and align its ledger/controller state; do not rerun G026 or invent truth.
- After that reconciliation, Coupling may use its existing serial_queue controller and the Runner formal resume_controller_task API. That API validates the stop/reconcile receipt, reinstalls the controller Scheduler task with PT0S, and starts it. Do not invoke the stale task action manually. The current task is Ready and still bound to G026 request bb93248ca2dff9605d7885554a319394 with PT72H, LastTaskResult 2.
- The next unentered case in the current sequence is G027 / attempt_001, subject to Coupling's current authority and final launch revalidation. This Runner task did not authorize or start it.
- Existing progress remains 38 entered / 34 truth-valid / 34 labels-valid / 90 unentered; confirmation data remains sealed and unaccessed.

## Persistence evidence and limits

SSH-disconnect and controller-exit probes were isolated, server-side Task Scheduler tasks with zero Runner invocation and zero solver entry. They validate helper/controller-worker lifecycle only. User logout, RDP disconnect, reboot, and a real FDTD solver/postprocessor process survival were not tested. Production task identity remains DELL/Interactive; therefore logout survival is not claimed. One earlier isolated probe observed 0xC000013A without a preserved Task Scheduler event; cause remains unknown.

The license check proves two FDTD API sessions and engine-feature checkouts can be created and closed under the scheduled worker environment. It does not prove the next GPU engine launch. No continuous real production case ran in this stabilization task; continuous duration observed is zero hours.

## Next — Coupling owns this action

Reconcile the formal G026 receipt into the Coupling ledger using Coupling's supported exception-closeout path; then resume the existing queue through the official Runner API. Keep single-slot execution, one entry per existing attempt, zero automatic replay, and truth-before-next. No G027 entry has been consumed by this task.
