# Continuation — project-owner-approved queue21 recovery and EXT02 diagnostic

Status: **queue21 exception accepted as UNKNOWN and quarantined; Coupling consumers fail closed; exact queue21 hold released through official API; diagnostic entry authorization and run still pending.**

## Durable owner and exception records

- The approval source is the direct user instruction in task `APCD_GPU_RUNNER_PROJECT_OWNER_APPROVED_RECOVERY_AND_DIAG_V1`. The user self-identifies as project owner. Personal name is not supplied; no digital signature or cryptographic verification is claimed. The GPU Runner V1 Codex acted only as execution delegate. Owner record SHA `da6176fe98a1e7f38e149db417e419455720922527d6d9699772456f308a752a`; delegation SHA `14ee2b2e84fb291775b9e2c4dbfb501b253c3d10b5ab88ecda9abea2575d55f1`.
- Queue21 `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`, events 1499/1506, remains physical entry count **UNKNOWN**. Events/truth were not edited; duplicate metric remains 1. Durable disposition V3 marks all queue21/linked unverified provenance quarantined. Coupling enforcement commit `8019c12c9627dad414bbbfff3579a0bffcda6aa4`, registry SHA `01d8073efb121c3fd667d7da72e33fdfd5f2b09964be4eacdbeabcd9b5582261`; focused suite 32 passed.

## Hold release evidence

- Only `hold-4a6eab94af3b4a6d8510ba2fe32a5b66` (`SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`) was released. The deployed official `ControlDB.release_hold` returned `RELEASED`, generation 27, `global_hold=false`; `new_entry_hold=0`, active global holds `[]`, health `PASS`, duplicate metric still 1. Pre-release generation was 26. No other hold, lease, slot, queue event, truth or attempt was changed by the task.
- Immutable owner-scoped authority SHA `7b2412e3271aa518fe67deb9b6cd8b74cf7da99e1c8331bee948e493aad0b7d2`. Runtime API result: `D:\apcd_runtime\gpu_production_runner_v1\owner_recovery\queue21_owner_release_20261004T125006.229320Z\OFFICIAL_HOLD_RELEASE_RESULT_V1.json`, SHA `9b2b31924ddc2e1a400b5e07e2b480d053ab9b4c627b32dbd6d720b55b7e54d7`. Consistent pre-release DB backup: same directory `control_pre_release.sqlite3`, SHA `76e849cff3f938bd972a17dc112b089a2420497e766c8a129b797081de1022ad`; it passed `quick_check` and matched the relevant pre-release state.
- Current Runner V1 remains single-slot. Current code reads the global hold snapshot; older prose claiming no control DB dependency is superseded by current code. The old seed controller is disabled; the only near-term recurring task is the recovery-only reconciler and it contains no dispatch or hold-release path. Eight Lumerical API server contexts remain untouched; no FDTD engine, active Runner case/marker, lease, or reservation was observed.

## Next — diagnostic only

1. Version the existing controlled Runner authority for exactly `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001`, `max_solver_entries=1`, solver authorization true, and automatic replay 0. Keep all 160 V2 case budgets at 0. Push before use.
2. Send the new Runner authority SHA to Coupling. Coupling updates only the diagnostic source manifest and formal preflight envelope, and obtains a fresh setup LOAD-only proof using the official preflight route. Do not alter its FSP, geometry, physical contract, monitor, or comparison protocol.
3. Recheck current generation 27 and no active hold, inspect diagnostic attempt event count remains 0, validate all route/contract/FSP/manifest/proof/resource/owner/process evidence, then complete `FINAL_LAUNCH_REVALIDATION`.
4. Invoke the existing single-slot official Runner exactly once. Require GPU lineage, hard completion barrier, durable FSP+H5, fresh LOAD, `SCIENTIFIC_VALID`, truth-before-DONE and release. Any post-entry fault is zero-solver recovery; no replay or attempt_002. Extract both planes' six complex E/H fields and actual coordinates/metadata; Coupling owns the frozen scientific comparison.

Current execution counts remain: solver entry 0; FDTD run 0; post-entry replay 0. Diagnostic authorization is still false/0 until the next versioned authority commit. No K6 V2 case is solver-authorized.
