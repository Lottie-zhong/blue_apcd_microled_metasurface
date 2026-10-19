# Continuation — K6 V2 G025 Recovery / G026 Failure

Updated: 2026-10-09T03:00:28.075173+00:00

## First read
Read this continuation, then FINAL_STATE_V1.json, G025_LEDGER_RECONCILIATION_OUTPUT_V1.json, and G026_POSTENTRY_FAILURE_AUDIT_V1.json before any further action.

## Verified state
- Host: DESKTOP-NNE313K / desktop-nne313k\dell.
- Coupling worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1; branch work/mdc-np-coupling-ml-v1; HEAD 877d62bddecbe38156ab544bc734be74353de9a5.
- Runner worktree HEAD: 661fa47274d796f98322ff56a9914776042b3cef.
- Request bb93248ca2dff9605d7885554a319394, manifest SHA bb93248ca2dff9605d7885554a31939418007dde6bfbcd007fdedbb2e7303618, resume generation 4 was accepted by the formal Runner API.
- G025 (K6V2_G025_20261008T140327Z_454d6858) was recovered with fresh LOAD only, then imported via the frozen Coupling importer. It is LABEL_PASS; one original entry, zero recovery invocations, zero replay.
- After G025 the queue automatically entered G026 (K6V2_G026_20261009T025353Z_06303b44, sequence 38). It consumed one entry and failed FAILED_POSTENTRY with RunnerError:LUMERICAL_LICENSE_STARTUP_FAILED in SOLVER_EXECUTION. No truth.h5 was produced; validation and hash manifests remain PENDING. Child log reports ANSYSLI/license interconnect could not read its server port and could not connect to the configured license server.
- G026 underlying license infrastructure cause remains unresolved. The original G025 worker exit 0xC000013A and unknown interrupted substep remain preserved.

## Current counters and queue boundary
- entered 38 / truth-valid 34 / labels-valid 34 / unentered 90.
- training fits 0 / P_scale fits 0 / confirmation response access 0 / automatic replay 0.
- Task Scheduler query is CONTROLLER_EXITED_NEEDS_RECONCILIATION; controller status still has the unresolved G026 pointer. Runner active pointer and lock are absent. G027 has no Runner row and was not started.
- Read-only Coupling reconcile returns StopQueue: UNAUTHORIZED_FAILED_POSTENTRY_CASE:K6GDP2_DEV_G026. Do not rerun G026, do not invent a truth receipt, and do not resume at G027 until a formally authorized G026 post-entry disposition/reconciliation is available.

## Recovery entry point
G026_POSTENTRY_FAILURE_AUDIT_V1.json and its G026_EVIDENCE directory preserve exception, status, preflight, child log, timeline, process-exit evidence, and Coupling CLI output. A future continuation must start from these files and the current official ledger, then follow the Runner owner's formal case-scoped closeout/reconciliation path. No further solver or runner was started after the G026 failure. No model fit, confirmation access, G026 retry, or G027 dispatch occurred.
