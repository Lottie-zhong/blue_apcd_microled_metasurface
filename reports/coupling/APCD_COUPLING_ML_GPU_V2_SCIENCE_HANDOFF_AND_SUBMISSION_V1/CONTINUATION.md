# Continuation — GPU V2 science handoff

Read this file first when resuming the Coupling/GPU V2 handoff.

## Snapshot

Observed 2026-10-10 08:01 UTC on DESKTOP-NNE313K as dell. Coupling branch work/mdc-np-coupling-ml-v1 began at HEAD a0747605c3e5fefe4e111aa5d16e3a148328ed37 (one commit ahead of origin before this task). The worktree already contained extensive unrelated staged/unstaged/untracked state; do not clean, reset, stash, or stage broadly. The GPU V2 worktree was clean at its checked HEAD e662a92a4485a768ffbebe56c2d759c1e416722a and was not modified.

## Result and stop boundary

G027_SCIENCE_ADMISSION_BLOCKED. Coupling budget check passes for the exact G027 candidate, but formal V2 admission refuses FORMAL_SCIENCE_RELEASE_MISSING_OR_UNBOUND. Installed SCIENCE_RELEASE_DENY.json remains DENY and Controller task APCD_GPU_V2_SERIAL_CONTROLLER remains disabled. No CLI/controller launch was performed.

Counts from the current Coupling ledger: 128 authorized, 38 entered, 34 truth-valid, 34 labels-valid, 90 unentered; replay=0; confirmation-response access=0. G027 attempt_001 is FAILED_PREENTRY_NO_ENTRY with entry_consumed=false. G026 is FAILED_POSTENTRY_NO_TRUTH with its existing entry consumed. The 32 confirmation cases stay sealed.

No solver entry, real FDTD, replay, production training fit, or confirmation-response read occurred. Zero-solver tests used isolated fixture data only.

## Recovery entry points

1. Read GPU_V2_SCIENCE_HANDOFF.md and G027_SCIENCE_ADMISSION_REPORT.md.
2. Read COUPLING_TO_GPU_V2_INTERFACE.md for the installed request/controller/receipt API.
3. Read G027_SUBMISSION_MANIFEST.md and G027_REQUEST_AUDIT.json for exact bindings and current deny.
4. Read GPU_V2_LEDGER_RECONCILIATION.md and GPU_V2_AUTOMATED_QUEUE_PLAN.md before any subsequent reconciliation or queue design.
5. Run the task-scoped tests only if code changes or a report inconsistency requires it; do not re-run scientific work.

## Files and ownership

Task-owned Coupling files are the read-only adapter scripts/coupling_ml/k6_v2_pipeline/gpu_v2_submission.py, tests/coupling_ml/k6_v2_pipeline/test_gpu_v2_science_handoff.py, and files in this report directory. Other dirty paths belong to existing work and must remain untouched. No file in the GPU V2 worktree or installed runtime is task-owned.

The installed V2 request is a hash-bound candidate, not an approval. The next science action requires explicit Chat authorization for the single G027 attempt_001 using its exact request/admission hashes and an owner-issued matching release. Until then, keep Controller Disabled and release DENY. Do not resume Legacy V1, Shared V3, or any other execution path.
