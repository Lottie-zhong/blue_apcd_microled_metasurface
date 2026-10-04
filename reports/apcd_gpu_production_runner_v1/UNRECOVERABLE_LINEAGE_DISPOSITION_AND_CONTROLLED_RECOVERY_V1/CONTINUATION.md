# Continuation — unrecoverable queue21 lineage disposition

## Current state

- Runner branch: `codex/apcd-gpu-production-runner-v1`; base HEAD before this task `704cdfafd329e4dc53a8d4e1e6e84d0a56e720e8`.
- Historical queue21 physical solver-entry count is **UNKNOWN**; events 1499/1506 and the source DB are preserved.
- Versioned disposition and quarantine manifest are saved in this folder. The disposition validator is deliberately fixed to this case/attempt/hold and can never authorize release.
- Active global hold remains `hold-4a6eab94af3b4a6d8510ba2fe32a5b66`, generation 26, `new_entry_hold=1`.
- Current V1 Runner has zero active cases and no active root lock/marker. Eight idle Lumerical API processes and one interactive EDT are preserved. No FDTD engine process was found.
- Diagnostic remains solver-unauthorized with current budget 0; all V2 160 cases remain solver-unauthorized. No solver/FDTD/replay ran in this task.

## Changes in this closeout

1. Runner V1 blocks every attempt ID for the exact quarantined Traditional queue21 case before creating a run directory.
2. Production-root `run_one` requires the official adapter's pre-entry guard. The adapter rechecks contract/source/staged FSP hashes and performs a read-only, fail-closed check of global `new_entry_hold`, generation, and active global hold records. This check is not a distributed lease; the owner must serialize hold changes with dispatch. Setup preflight remains separate; no slot allocator or three-slot policy was restored.
3. Strict V1 manifest fields reject legacy token/fencing fields. Existing one-slot, duplicate, post-entry no-replay, durable truth, and release barriers remain.
4. `queue21_exception_v1.py` validates only this fixed pending-owner exception; it returns `release_authorized=false` and has no ignore-hold option.

## Validation

`VALIDATION_RESULTS_V1.json` records 85 passed and 42 subtests passed across six no-solver test files, plus the live read-only hold smoke. Production DB SHA was unchanged by the smoke. The exact source and runtime evidence hashes are listed in `SHA256_INVENTORY_V1.json`.

## Resume conditions

Do not resume solver work until the designated global hold owner is identified and supplies authenticated approval of the disposition, exact hold ID and current generation. Then a trusted operator must verify the signed authority and use the official release API; re-read control state immediately beforehand. Do not call the API from this task, edit SQLite directly, or reuse generation-25 authority.

After hold release, separately register at most one solver entry for `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001`; refresh case authorization, FSP/manifest/load proof, GPU/process snapshot and full `FINAL_LAUNCH_REVALIDATION`. Stop without entry if any gate fails. Post-entry failure permits only zero-solver recovery, never automatic replay. Do not restart queue21, create its attempt_002, or launch any of the 160 V2 data cases.

## Exact records

- `EXCEPTION_DISPOSITION_V1.json`
- `QUARANTINE_MANIFEST_V1.json`
- `CURRENT_EXECUTION_STATE_V1.json`
- `OWNER_DECISION_REQUEST.md`
- `HANDOFF_TO_COUPLING.md`
- `VALIDATION_RESULTS_V1.json`
- Runtime DB snapshot: `D:\apcd_runtime\gpu_production_runner_v1\recovery\queue21_unrecoverable_lineage_20261004T113204Z`
