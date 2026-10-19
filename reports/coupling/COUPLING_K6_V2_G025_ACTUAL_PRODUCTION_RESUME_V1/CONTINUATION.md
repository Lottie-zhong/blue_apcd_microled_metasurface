# Continuation - K6 V2 G025 Actual Production Resume

Read this file first on recovery, then inspect the linked evidence JSON and the current official Runner handoff before acting.

## Result captured 2026-10-08T14:27:20.236420+00:00

- Host verified: DESKTOP-NNE313K / desktop-nne313k\dell.
- Coupling worktree D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1, branch work/mdc-np-coupling-ml-v1, HEAD 877d62bddecbe38156ab544bc734be74353de9a5; it is dirty with pre-existing work and this task's reports. Preserve all unrelated items.
- Runner worktree D:\project\worktrees\blue_apcd_gpu_production_runner_v1, branch codex/apcd-gpu-production-runner-v1, HEAD a87b2296e359515217e0b9f2162207437aa5fdf9 (expected a87b2296e359515217e0b9f2162207437aa5fdf9), clean.
- Controller request bb93248ca2dff9605d7885554a319394, generation 3; manifest SHA bb93248ca2dff9605d7885554a31939418007dde6bfbcd007fdedbb2e7303618; consumed receipt SHA 5f0ca50f67dde5e7af19a000b8e19e94eb47e7f22ebcf7bc163aa566cec7b523. Formal resume was accepted once. Do not resume again until formal post-entry reconciliation.
- G025 attempt_001 sequence 37 entered once as K6V2_G025_20261008T140327Z_454d6858; Runner status SOLVER_ENTERED, solver_invocations=1. Solver log confirms completion and solved FSP exists (SHA be006f194b07df6d19105812ca49fdce5a8d9660fff983559f91c9d3fc948572).
- truth.h5 is absent; validation and hashes are PENDING. Runner output: RUNNER_ERROR:SCHEDULED_WORKER_REQUIRES_RECONCILIATION:NEEDS_RECONCILIATION (SHA 74eb6a944ef3a40c6049f7a202a4b940849762ac0035c02660d1c016ef8230f0). G025 is not truth-valid or label-valid. G026 did not start.
- Persisted ledger remains unreconciled at 36/33/33/92; G025 is still current. Entry evidence implies 37 entered, 33 truth-valid, 33 labels-valid, 91 unentered after consuming G025, but these are not yet reconciled official ledger counters.
- Formal stop-only reconciliation rejected: QUEUE_STOP:CONTROLLER_STOP_BOUNDARY_HAS_ACTIVE_CASE_OR_REQUEST. Runner lock/active pointer remain; do not clear them or replay.
- No G026, replay, training, P_scale fit, or confirmation-response access occurred.

## Evidence

- Evidence JSON: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_G025_ACTUAL_PRODUCTION_RESUME_V1\G025_ACTUAL_PRODUCTION_RESUME_EVIDENCE_V1.json; SHA-256 f29540d5a2e99f7c1ffff59c33fa2821a02ce18bc41c20525b76e7553e39263d.
- Resume API stdout/stderr: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\resume_captures\RESUME_CAPTURE_bb93248ca2dff9605d7885554a319394_GEN3_20261008T140319Z\resume_api_stdout.txt (dca0b73e31010938a554babff6785da11bf943e816cee4c67d1cfcacab525fc1) / D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\resume_captures\RESUME_CAPTURE_bb93248ca2dff9605d7885554a319394_GEN3_20261008T140319Z\resume_api_stderr.txt (e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855).
- Runner CLI gate output: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\RUNNER_CLI_OUTPUT_K6V2_G025_20261008T140327Z_454d6858.log (74eb6a944ef3a40c6049f7a202a4b940849762ac0035c02660d1c016ef8230f0).
- Stop-reconcile stdout/stderr: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\resume_captures\RESUME_CAPTURE_bb93248ca2dff9605d7885554a319394_GEN3_20261008T140319Z\formal_stop_reconcile_20261008T141916Z\stdout.txt (e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855) / D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1\resume_captures\RESUME_CAPTURE_bb93248ca2dff9605d7885554a319394_GEN3_20261008T140319Z\formal_stop_reconcile_20261008T141916Z\stderr.txt (84d9d81b57733e03074e89d3e807463d9951b7f279e7dc5fc571c8dcde6d2e8a).
- G025 status/log/FSP: D:\apcd_runtime\gpu_production_runner_v1\runs\K6GDP2_DEV_G025\attempt_001\K6V2_G025_20261008T140327Z_454d6858\status.json (ef48847fa53c0205a9270ee19303981a059bb16e0c73092daf8090e08f98629f), D:\apcd_runtime\gpu_production_runner_v1\runs\K6GDP2_DEV_G025\attempt_001\K6V2_G025_20261008T140327Z_454d6858\run_p0.log (c29baae70d6bfc7c69378303eaedfb54b8dc39a11ee37bacc6ca515784be6ce0), D:\apcd_runtime\gpu_production_runner_v1\runs\K6GDP2_DEV_G025\attempt_001\K6V2_G025_20261008T140327Z_454d6858\run.fsp (be006f194b07df6d19105812ca49fdce5a8d9660fff983559f91c9d3fc948572).

## Next action

Ask the GPU Runner owner for a G025-specific post-entry recovery/closeout path that either extracts and validates truth from the solved FSP without another solver entry, or formally closes G025 as FAILED_POSTENTRY_NO_TRUTH. Do not reuse case-bound G023/G024/S35 helpers. After the owner receipt exists, reconcile request inventory, ledger, active pointer, and lock via official interfaces, issue a fresh request-specific STOPPED_RECONCILED receipt, then resume at G026. Do not hand-edit status/ledger, clear the lock, rerun G025, or resume before that evidence chain.

Raw Task Scheduler controller stdout/stderr are not available because the installed task definition has no output redirection. Resume API stdout/stderr and Runner CLI combined output are preserved.
