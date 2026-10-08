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