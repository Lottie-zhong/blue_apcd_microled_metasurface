# Continuation — APCD_GPU_RUNNER_CONTROLLED_CASE_ADMISSION_DESIGN_V1

Read these files first, in order:

1. `CONTROLLED_CASE_ADMISSION_DESIGN_V1.md`
2. `CONTROLLED_CASE_ADMISSION_POLICY_V1.json`
3. `OFFLINE_VALIDATION_REPORT_V1.json`

## Current authority boundary

- Host: `DESKTOP-NNE313K`; user: `desktop-nne313k\dell`.
- Runner worktree: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1`.
- Runner branch baseline: `codex/apcd-gpu-production-runner-v1`, starting HEAD `1afa3e30f1de5e0192be6240a3754c89e2eb6f25`.
- Coupling worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`.
- Current Coupling worktree snapshot: 346 porcelain entries, SHA256 `55b742c0459898b70f5447fd2c529323690db3db6e2ff9163aef01fa00ff6297`. It differed from the earlier 332-entry audit before this task's remote write and advanced through unrelated activity while this task ran. Preserve the captured snapshot. Each Runner write compared the Coupling porcelain bytes before and after and found no task mutation.
- Source handoff inputs in `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\COUPLING_ML_EXT02_TWO_AIR_PLANES_VALIDATION_V1`: `CONTINUATION.md` SHA256 `d77a27d3131cb7e8ce5144d8f3a1c9b2c65d6e9da4cef00a4a99bac3a5de9621`; `RUNNER_COMPATIBILITY_AUDIT_V1.json` SHA256 `847ddf174bae8fe8d6016253b454e756cac7a6687d5097b2e68bb5ccd44d4fd8`; `PROPOSED_DIAGNOSTIC_CONTRACT_V1.json` SHA256 `7cdd82b56c7538e7b295806958a43c1e9d041229e803d4e6b38d9e7621b08a8d`.
- Source Runner handoff is `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\docs\APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.md` at input HEAD `1afa3e30f1de5e0192be6240a3754c89e2eb6f25`.
- The production authority contains exactly the original 12 IDs. The production adapter and runner core remain frozen and unchanged.

## Completed in this task

- Designed two separate case classes: fixed-contract K6 geometry variants and a one-monitor EXT02 diagnostic.
- Added a design-only reference validator and synthetic unit tests. They do not import production code, invoke Lumerical, stage a real FSP, call `run-one`, or dispatch a solver.
- Distinguished new-case pre-entry setup LOAD proof from post-entry truth recovery.
- Production case admission was not changed. EXT02 and future K6 geometries are still not accepted by production Runner V1.

## Resume restrictions

- Do not start EXT02 or any new dataset case from this design continuation.
- Do not replay any entered attempt.
- Do not change the production contract hash to hide the monitor overlay.
- Preserve the one-slot GPU, serial dispatch, completion barrier, truth-before-DONE, fresh LOAD truth validation and no-post-entry-replay invariants.
- Before real EXT02 validation, materialize its own 5 nm contract/setup/source manifest/staged FSP and pre-entry LOAD proof in a versioned controlled authority route. The old 2 nm seed FSP and the proposal fingerprint are not acceptable substitutes.
- Next intended scientific case after that route is complete: `K6V1_EXT02 / attempt_001` under the separate controlled authority root; solver budget one entered run, no automatic replay. The historical seed-DB `attempt_001` remains distinct.

## Git closeout

Commit only the exact new files listed in the task's final handoff. Do not stage unrelated files or the Coupling worktree's pre-existing untracked state. Push the Runner branch normally after tests and final status checks.
