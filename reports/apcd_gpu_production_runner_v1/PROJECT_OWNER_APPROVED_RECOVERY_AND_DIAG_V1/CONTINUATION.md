# Continuation — project-owner-approved queue21 recovery and EXT02 diagnostic

Status: **Owner decision recorded; Coupling consumer quarantine enforced; release authority prepared and committed; official hold release is the next action. No solver entry.**

## Authority and disposition

- Owner authorization source: direct user instruction in `APCD_GPU_RUNNER_PROJECT_OWNER_APPROVED_RECOVERY_AND_DIAG_V1`; the user self-identifies as project owner. Personal name is not supplied. No independent approver, digital signature, or signature verification is recorded. The GPU Runner Codex is only the scoped execution delegate.
- Queue21 remains `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`, events 1499/1506, physical launch count **UNKNOWN**. Events and truth were not edited. The duplicate metric remains 1.
- Coupling consumer exclusion is implemented and pushed at commit `8019c12c9627dad414bbbfff3579a0bffcda6aa4`; registry SHA `01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261`; focused tests 32 passed. Queue21/linked uncertain provenance is blocked at Coupling imports, training, ranking/evaluation, confirmation, diagnostic and local-affine consumers; distinct valid old32 provenance passes its positive test.
- Current hold is still expected to be `hold-4a6eab94af3b4a6d8510ba2fe32a5b66`, generation 26. Do not call release unless the immediate live check confirms this exact hold/generation, no other active GLOBAL hold, no active Runner case/lease/engine, and the quarantine commit/evidence are unchanged. Release only through deployed `ControlDB.release_hold`; preserve duplicate metric.

## Current platform and evidence

- Runner worktree `D:\project\worktrees\blue_apcd_gpu_production_runner_v1`, branch `codex/apcd-gpu-production-runner-v1`, HEAD `88c8ba7afe99ab8e58a4f41f0698b56f65bc0b35`, upstream `0/0`; tracked worktree clean at pre-release capture. Current adapter performs read-only admission against `D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3`, so this hold applies. Earlier prose describing filesystem-only authority is superseded by current code.
- Live pre-release audit: `D:\apcd_runtime\gpu_production_runner_v1\owner_recovery\queue21_owner_release_20261004T125006.229320Z\PRE_RELEASE_LIVE_AUDIT_V1.json`, SHA `d71e1deec57336ff512d162b0f33bd4d96da90ce68a91fc94506451f7947fc6c`. Consistent SQLite backup: sibling `control_pre_release.sqlite3`, SHA `76e849cff3f938bd972a17dc112b089a2420497e766c8a129b797081de1022ad`; snapshot quick-check passed and relevant state matched live DB. Scheduler window audit SHA `c2643d6e22a622c0647a32a0ef279e55a936b07b99aa6f095db9e0d827448da3`.
- No active V1 lock/active marker, engine/MPI/Fluent process, capacity lease, or reservation. Eight `fdtd-solutions.exe -server -hide` API contexts remain untouched; they are not engine processes and own no active Runner slot. The RTX 3080 reading is supplementary only. Old Shared V3 seed controller is disabled; the only near-term repeating task is recovery-only Coupling reconciler, whose pinned source contains no dispatch or hold-release path. No old 3-slot scheduler is restored.
- Focused current Runner tests: 36 passed and 39 subtests passed. Coupling focused tests: 32 passed.

## Ordered next steps

1. Revalidate live hold, generation, no other active hold, active resources/processes, Coupling commit/registry hashes immediately before release; call only the official API for the exact hold using the committed `HOLD_RELEASE_AUTHORITY_V1.json` hash. Record API result, event id and actual generation. Stop if anything changed.
2. After successful release, update and push only the controlled Runner authority for `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001`: maximum one entry, zero automatic replay. Keep the 160 V2 case budgets at 0.
3. Ask Coupling to rebind its case-specific source manifest and formal setup preflight envelope to the new Runner authority hash and generate a fresh setup LOAD-only proof. Do not modify the FSP or science contract.
4. Verify diagnostic event history remains zero. Perform complete `FINAL_LAUNCH_REVALIDATION`, including route, contract/FSP/manifest/proof hashes, control generation, ownership/resource/process state. Then execute exactly once through official Runner `run-one`. No automatic replay or attempt_002.
5. Require GPU lineage, completion barrier, durable FSP+H5, fresh LOAD, `SCIENTIFIC_VALID`, truth-before-DONE and formal release. Extract both planes' six complex E/H fields, actual coordinates, wavelengths and metadata. Coupling performs the frozen scientific comparison; do not claim it passes here.

Current counts: solver entry 0; FDTD run 0; post-entry replay 0; diagnostic authorization still false/0 until the released-hold route authority is versioned.
