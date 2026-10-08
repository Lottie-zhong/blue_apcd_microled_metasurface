# Continuation — K6 V2 controller bootstrap compatibility and resume

**Last checkpoint:** 2026-10-08 05:56 UTC. Read this file and `REPORT.md` before resuming.

## Environment and authority

- Remote host: `DESKTOP-NNE313K`, user `dell`.
- Coupling worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`, branch `work/mdc-np-coupling-ml-v1`.
- GPU Runner worktree: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1`.
- Runtime: `D:\apcd_runtime\gpu_production_runner_v1`.
- Python: `N:\anaconda_envs\RCP_LCP\python.exe`.
- Current request: `bb93248ca2dff9605d7885554a319394`; current manifest SHA `bb93248ca2dff9605d7885554a31939418007dde6bfbcd007fdedbb2e7303618`.
- Queue manifest raw SHA: `fbcac249c59e3f242e48dfa16a8e92298c98bab48f5fe7256900b8feed10bca7`; canonical SHA `ecbb9b32105f5a26adf051d614bef68fcf793e0f089eae391510e6b86a138e32`.
- Bound `serial_queue.py` SHA: `aad9813f4d45d114e81ad91920d113382d879d6eeb350b74edc4549da2f9a270`.

## Latest verified state

The queue is `STOPPED_RECONCILED`; Task Scheduler is `Ready` with last result 2. Counts are 36 entered, 33 truth-valid, 33 labels-valid, 92 unentered, replay 0, training 0, P_scale 0, confirmation-response access 0. G023/G024 remain failed-postentry and are excluded from successor cases. G025 / attempt_001 is still unentered. No solver, Runner case request, FDTD service or shared lock was started or modified by reconciliation.

Current request receipt is `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\resume_receipt_bb93248ca2dff9605d7885554a319394.json`, SHA `e4433b17229c9149255d71cd652fa3f8856f4e0f6958132ca81efde426310a5e`. It follows the generation-1 receipt, which is preserved as `resume_receipt_bb93248ca2dff9605d7885554a319394_generation_1.json`.

## Blocker and recovery entry

G025 fresh LOAD-only proof passes. The official formal setup preflight fails because Ansys licensing cannot bind port 61208; read-only `netstat` shows existing Ansys license service PID 8448 already listening on that port with active FDTD clients. Do not kill or reconfigure those shared processes here. Production is not resumed until the platform owner safely resolves the licensing port/service issue.

After resolution, first verify host/user, current Git HEAD, Runner task binding, current receipt SHA, Scheduler state, and that no task/solver is active. Run the complete `serial_queue.py --dry-run` with request `bb93248ca2dff9605d7885554a319394` and the current manifest/receipt hashes. Then resume only through Runner `task_scheduler_v1.py resume-controller-task` using the current receipt. Do not call `start-controller-task` again. Confirm actual G025 Runner entry, then wait for durable truth and label validation before reporting resumed production. Do not rerun any previously entered case, start training, or access confirmation responses.

The dry-run summary currently prints sequence index 4 while the queue ledger and pre-entry receipt use 37. Treat the persisted queue cursor as authoritative; resolve this reporting discrepancy only with an appropriately versioned controller change and formal Runner rebind before execution.

## Code and tests

- Compatibility code/tests: commit `980af2ca` pushed to `origin`.
- Generation-scoped repeated pre-entry reconciliation and focused tests are in the follow-up exact-allowlist change for this task.
- Last focused test result: 26 passed; `py_compile` passed.
- Detailed evidence and hashes: `REPORT.md` and `SHA256_INVENTORY.json` in this directory.

## Checkpoint 2026-10-08 13:05 UTC  generation 2 pre-entry exit

- Formal resume-controller-task for request bb93248ca2dff9605d7885554a319394 was accepted with the supplied generation-2 receipt. The resumed controller exited with Scheduler result 2 at G025 LIVE_ENTRY_GATE, before run-one; no Runner request, run envelope, attempt directory, registry row, solver entry, or replay exists.
- The G025 setup preflight remains the bound formal PASS: result SHA-256 f14e809588fb3e68cacefcc277d3ae600716deb6e468add36e3b27eb7e69b786, adapter SHA-256 8860254b701fe2461def30644158117bf211b826f1d3adf3e5919c02c48c550a. The production queue invokes adapter.py from the Runner worktree, so this is the repair version used by the worker.
- The exact LIVE_ENTRY_GATE exception was not persisted. Task Scheduler Operational logging is disabled. The generation-2 evidence records the passing setup result and both formal preflight-log hashes; the old failure log remains unchanged.
- The existing Coupling pre-entry reconciler was narrowly updated to accept the recorded ledger ENSURE_CURRENT_ROUTE_AND_PREFLIGHT / batch LIVE_ENTRY_GATE phase pair, while still rejecting a run-one phase or any run ID. Focused tests: 13 passed; py_compile passed.
- Formal reconciliation completed for G025 / attempt_001, sequence 37. Current status is STOPPED_RECONCILED; current receipt is generation 3, SHA-256 5f0ca50f67dde5e7af19a000b8e19e94eb47e7f22ebcf7bc163aa566cec7b523. Generation-2 evidence SHA-256 1b551ddcbdd176dc511b49aacf2d217d8760daa653ae6e23a0db6a084ae9c383. G025 remains unentered; totals remain 36 entered / 33 truth-valid / 33 labels-valid / 92 unentered; replay, training, P_scale and confirmation-response access remain zero.
- The post-exit read-only diagnostic at 13:05 UTC found the global entry hold PASS and no active-run or runner-lock file, but runner_owner_probe=True. Inspection of the probe shows it fails closed when any historical FAILED_POSTENTRY row lacks solver-process lineage. The only non-exempt row is G024 (K6V2_G024_20261007T123943Z_713590ad); S35 is separately exempted by its recovered-truth disposition. This is the leading explanation for the gate stop, but not a captured exception from the 12:55 UTC attempt.
- Do not resume the queue while the official owner probe remains busy. Do not change the Runner gate or touch shared processes as a workaround. The next resume requires a case-scoped Runner-authority resolution for G024's missing lineage, then a fresh formal reconciliation receipt; do not replay a case that has entered.

Recovery evidence: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\CONTROLLER_PREENTRY_INTERRUPTION_EVIDENCE_bb93248ca2dff9605d7885554a319394_K6GDP2_DEV_G025_RESUME_GENERATION_2.json.
