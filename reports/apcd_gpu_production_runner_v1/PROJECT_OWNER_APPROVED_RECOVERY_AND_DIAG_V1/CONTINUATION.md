# Continuation - project-owner-approved queue21 recovery and EXT02 diagnostic

Status: **OWNER DECISION RECORDED; COUPLING CONSUMER EXCLUSION IN PROGRESS; HOLD ACTIVE; NO SOLVER ENTRY**.

- Runner worktree: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1`, branch `codex/apcd-gpu-production-runner-v1`, HEAD `50c00dc23cce4735277719b5034a48dd7b082878`, upstream `0/0`. Tracked worktree was clean before this task's report files.
- Project-owner decision and scoped delegation were directly recorded from the user message in task `APCD_GPU_RUNNER_PROJECT_OWNER_APPROVED_RECOVERY_AND_DIAG_V1`. The user self-identifies as project owner; legal name is not supplied; there is no digital signature and no signature verification. This is a new versioned record, not a backfilled historical registration.
- Queue21 remains `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`, events 1499/1506, physical solver-entry count `UNKNOWN`. Original V1 disposition and raw events remain unchanged. New V2 disposition records owner acceptance and keeps all quarantine restrictions active.
- The sole current global hold is `hold-4a6eab94af3b4a6d8510ba2fe32a5b66`, reason `SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`, generation 26, `new_entry_hold=1`; the only other lifecycle row is already RELEASED. The Runner V1 adapter reads `D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3`. No direct DB edits have been made.
- Current Runner registry has 12 historical records and no active case or queue21/diagnostic row; root lock and active marker are absent. The live Shared V3 slots are FREE, active capacity leases/reservations are empty. No `fdtd-engine-msmpi.exe`, `mpiexec.exe`, or Fluent solver was observed. Eight `fdtd-solutions.exe -server -hide` are long-lived Lumerical API contexts parented by Python FSP inventory jobs; they were left untouched.
- Focused Runner V1 zero-solver tests on the current source passed: 36 tests and 39 subtests. No entry, FDTD run, or replay occurred.
- Coupling Codex thread `耆合ML4` was explicitly asked to add and test the official consumer exclusion before hold release; that task is still active. Coupling worktree contains unrelated untracked files and is not to be cleaned or staged by GPU Runner.
- Current controlled route authority `d2b35c1b376e3ca5e1c7b38650861be2fb33ebc713e86772f8d82a9ebb634f56` still keeps the independent EXT02 diagnostic unauthorized with budget 0. The existing setup proof is not yet final for this owner-approved execution. A later versioned Runner authority change will require Coupling's route source manifest and formal preflight envelope to be rebound and freshly loaded.

## Resume sequence

1. Verify Coupling's exact consumer exclusions, tests, code/registry SHA, and its own commit/push. Do not release the hold until the consumers reject queue21/uncertain provenance and accept a distinct valid fixture.
2. Recheck current controls, all active holds, Runner process/lock state, GPU engine lineage, scheduled tasks, and the queue21 block. Capture a fresh SQLite backup snapshot using SQLite backup API, not file copying or raw edits.
3. Create and commit a specific release-authority record, then call the deployed official `ControlDB.release_hold` only for the queue21 containment hold. Preserve the duplicate metric and verify exactly the actual generation/event/status returned. Stop if any other active reason or current owner conflict appears.
4. After release, version the exact Runner authority to allow at most one entry for `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001` and zero automatic replay; keep all 160 K6 V2 solver budgets at 0. Push Runner authority before use.
5. Ask Coupling owner to rebind only diagnostic route/source manifest inputs to the new Runner authority hash and run official `preflight-setup` for a fresh LOAD-only proof. Preserve the setup FSP, contract, monitor, geometry, and protocol unchanged.
6. Verify the new diagnostic has zero prior entry, issue immutable run manifest, refresh all FINAL_LAUNCH_REVALIDATION and resource/owner/process gates immediately before `run-one`, then consume one entry only. No post-entry replay or attempt_002. Extract both monitor planes, durable FSP/H5, fresh LOAD, actual coordinates and metadata; leave the frozen scientific comparison to Coupling.

## Exact records

- `PROJECT_OWNER_DECISION_RECORD_V1.json`
- `PROJECT_OWNER_EXECUTION_DELEGATION_V1.json`
- `EXCEPTION_DISPOSITION_V2.json`
- `SHA256_INVENTORY_V1.json`
- Source history remains under `UNRECOVERABLE_LINEAGE_DISPOSITION_AND_CONTROLLED_RECOVERY_V1`.
