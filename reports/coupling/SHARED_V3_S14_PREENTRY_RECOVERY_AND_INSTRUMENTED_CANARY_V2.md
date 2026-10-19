# SHARED_V3_S14_PREENTRY_RECOVERY_AND_INSTRUMENTED_CANARY_V2

## STATUS

`BLOCKED_RECOVERY`

Phase A could not be completed safely through the currently implemented Shared V3 recovery path. Phase B was not entered. No S14 `attempt_002` was created and no new scientific solver entry occurred.

## ATTEMPT_001 RECOVERY

Preserved evidence:

- S14 attempt root: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_S14\attempt_001`
- Runtime root: `D:\apcd_runtime\global_fdtd_control_v3\cases\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_S14\attempt_001`
- Recovery evidence manifest: `preentry_recovery_evidence_manifest.json`
- Manifest SHA256: `BAA7D752D1E1E4DB1DEBD3852FC607CB20FD8C80550137C5A2311000FD1368F8`
- Original runtime events preserved: `HOST_START_INTENT`, `HOST_PROCESS_STARTED(host_pid=21060)`.
- PID `21060`: no longer alive; no descendants alive.
- `SCIENTIFIC_SOLVER_ENTERED=0`.
- `GPU_ENGINE_ENTRY_CONFIRMED=0`.
- FDTD engine entry count: `0`.
- `attempt_002` existence: `false`.
- No native FSP, H5, raw spectrum, archive, or terminal scientific truth exists for S14 attempt_001.

The existing authoritative call was executed without a direct database write:

```text
recover_failed_preentry(
  coupling_ml, K6V1_S14, attempt_001
)
=> NOT_ELIGIBLE / state=HOST_STARTED
```

The before/after probe showed no control-plane mutation:

- queue remained `HOST_STARTED`, queue id `44`, `GLOBAL_SLOT_2`, fencing generation `44`;
- slot remained `RESERVED` by `coupling_ml / K6V1_S14 / attempt_001`;
- lease `SCIENTIFIC_SOLVER_ENTERED` count remained `0`;
- admission remained `new_entry_hold=1`, `temporary_runtime_cap=1`, `health_status=PASS`, generation `11`.

The current recovery API accepts `FAILED_PREENTRY`, `AMBIGUOUS_QUARANTINED`, `HOST_START_INTENT`, and `SOLVER_ENTRY_INTENT`, but not `HOST_STARTED`. Its existing recovery result is `WAIT_RESOURCE_CAPACITY`, which is not a safe terminal state for this task because it could permit reuse/replay of attempt_001. Therefore no release or queue mutation was forced.

## DISPATCHER FIX

Already-present minimal correction:

- File: `scripts/shared_fdtd/tools/v3_dispatcher_service.py`
- Before `CreateProcessW` flags: `0x08000000` (`CREATE_NO_WINDOW`).
- After flags: `CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB` (`0x08000000 | 0x01000000`).
- After-correction SHA256: `CDF556F041B91595AF76CE95BF4469ACDB2F056A5996CA920FD66D1D351CA299`.
- Existing error handling remains: failed `CreateProcessW` raises `ctypes.WinError(ctypes.get_last_error())`.
- Returned child PID remains `PROCESS_INFORMATION.dwProcessId`; process and thread handles are closed after creation.

Zero-solver checks:

- `run_v3_dispatcher_detach_zero_solver_tests.py`: `PASS`; dummy child survived launcher exit.
- Existing global zero-solver tests: `20/20 PASS`.
- Existing branch zero-solver tests: `20/20 PASS`.
- Existing chaos zero-solver tests: `12/12 PASS`.

No real attempt_002 launch was permitted, so real host/child Windows Job membership and full live controller/reconciler fencing behavior remain unverified. The zero-solver survival result does not by itself prove the original PID-21060 termination mechanism.

## S05/S12/S13 CORRELATION

`INSUFFICIENT_EVIDENCE`

Saved S12/S13 records show prior scientific entries, but the preserved per-attempt evidence does not contain a direct dispatcher source fingerprint or Windows Job-membership record sufficient to prove that S05, S12, and S13 all used the same `CreateProcessW` containment path. The breakaway hypothesis is therefore not promoted to their root cause.

## ATTEMPT_002 PREENTRY

Not created. The required Phase-A gates did not pass because the stale owner could not be terminalized through the existing recovery API without changing its semantics or directly mutating SQLite.

Current safety state:

- `new_entry_hold=TRUE`
- `autofill=disabled`
- `GLOBAL_SLOT_1=FREE`
- `GLOBAL_SLOT_2=RESERVED` by S14 attempt_001, `solver_entered_at=NULL`
- `GLOBAL_SLOT_3=FREE`
- S15/S16 remain `WAIT_RESOURCE_CAPACITY`
- no pending S14 attempt_002 truth or recovery action

## REAL SOLVER LIFECYCLE

Not started in V2. The only S14 lifecycle remains:

```text
HOST_START_INTENT -> HOST_PROCESS_STARTED(pid=21060) -> host disappeared
```

No `HOST_STARTED`, `SOLVER_ENTRY_INTENT`, `GPU_ENGINE_ENTRY_CONFIRMED`, or `SCIENTIFIC_SOLVER_ENTERED` event exists for attempt_001.

## WATCHER/GPU EVIDENCE

- Durable watcher v2 heartbeat advanced before the V1 gate and was stopped using its exact stop flag after evidence capture.
- The watcher observed baseline `fdtd-solutions.exe -server -hide` processes only; no S14 FDTD engine, `mpiexec`, or `smpd` lineage appeared.
- GPU telemetry showed approximately 1–2% utilization, about 1037 MB / 10240 MB VRAM, approximately 100 W and 60 C; no solver workload signature appeared.
- Windows event delta contained `0` matching events and `0` matching artifacts.

## TRUTH BUNDLE

No scientific truth bundle exists for S14 attempt_001 or attempt_002. Preserved non-scientific evidence includes:

- setup-only `runtime.fsp`;
- pre-entry and pre-canary manifests;
- runtime `events.jsonl`;
- watcher heartbeat, process events, telemetry, failure snapshot, and Windows event delta;
- `preentry_recovery_evidence_manifest.json`.

## CONTROL SAFETY

```text
S14_ATTEMPT_001_SCIENTIFIC_ENTRIES=0
S14_ATTEMPT_002_SCIENTIFIC_ENTRIES=0
TOTAL_NEW_GPU_ENGINE_ENTRY_CONFIRMED=0
S12_REPLAY_COUNT=0
S13_REPLAY_COUNT=0
S15_ENTRY_COUNT=0
S16_ENTRY_COUNT=0
ATTEMPT_003_CREATED=0
DUPLICATE_SCIENTIFIC_ENTRY_COUNT=0
FOREIGN_MUTATION_COUNT=0
NEW_ENTRY_HOLD=TRUE
AUTOFILL=DISABLED
```

No solver was rerun, no S12/S13 replay occurred, no S15/S16 entry occurred, no direct SQLite mutation occurred, and Traditional was not touched.

## GIT / CHANGED FILES

- Branch: `work/mdc-np-coupling-ml-v1`.
- HEAD unchanged: `7d844158e2318a56b7d34eb01c26d3da45b98822`.
- Worktree remains dirty with pre-existing Coupling-ML changes, the previously validated dispatcher correction/test, this V2 report, and the preserved recovery evidence.
- No commit and no push.
- No scientific FDTD settings were changed.

## NEXT

Chart review a Shared V3 terminalization path for the stale `HOST_STARTED` preentry owner that cannot replay `attempt_001`; do not create `attempt_002` until that path is implemented and zero-solver validated.
