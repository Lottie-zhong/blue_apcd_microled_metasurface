# NP K6 P0 runtime launcher recovery setup v1

- stage: `NP_K6_P0_RUNTIME_LAUNCHER_RECOVERY_SETUP_V1`
- state: `READY_FOR_NP_K6_P0_SIMTIME_2PS_RECOVERY_V2_AUTHORIZATION`
- solver run / entered: **0 / 0**
- setup-only: true; solver_authorized: false; training_label: false; provisional_hf_label: true

## Abort audit

The prior consumed `RUN3C_P_PILOT_HF_SIMTIME_2PS_CONTROL_V1/attempt_001` remains immutable: entered=1, run_invocation_count=1, no engine/controller/post-save, scheduler result `0xC000013A` at 27.203%, no post-FSP. The scheduler was interactive-token, battery/idle stop enabled, and no task-history or explicit taskkill/shutdown evidence was recovered. Therefore the only defensible classification is `ROOT_CAUSE_UNRESOLVED`; the old attempt is not reinterpreted or retried.

The reported plane-wave path was absent. The authoritative copy is in the NP worktree; its setup FSP SHA is `76d23a8961267fb6a720ad875ba016b56aed5c65e8c7379ce09b0cea6029ef1f`. No artifacts were moved or deleted.

## Launcher persistence

The launcher uses an explicit remote Python executable and detached child with `CREATE_BREAKAWAY_FROM_JOB`, a PID file, heartbeat, stdout/stderr, completion record, and read-only status/recovery modes. It refuses duplicate starts while a PID is alive, quarantines stale PID metadata, has no automatic retry, no FDTD calls, and no interactive-session dependency.

The hardened dummy-only dry run ran for 65 seconds. The caller returned before completion; heartbeat reached 65 seconds, completion exit code was 0, PID was cleaned, and `entered=false`, `run_invocation_count=0`, `solver_calls=0` throughout. See `outputs/np_k6_p0_runtime_launcher_recovery_setup_v1/dummy_persistence_dry_run.json`.

## Recovery-v2 setup

New independent case: `RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2`, `attempt_001` (not attempt_002), source setup SHA `76d23a8961267fb6a720ad875ba016b56aed5c65e8c7379ce09b0cea6029ef1f`, simulation time `2e-12 s`, auto-shutoff `1e-05`. The setup is byte-identical to the frozen 2 ps control input; unexpected physical differences are empty. Actual solver-grid equality is intentionally unproven until a future authorized run.

The new ledger is setup-only with `entered=false`, `run_invocation_count=0`, `engine/controller/post-save=0/0/0`, `solver_authorized=false`, `training_label=false`, and `provisional_hf_label=true`. No FDTD result, T/R label, checkpoint, or training artifact was produced.

## Evidence

- `outputs/np_k6_p0_runtime_launcher_recovery_setup_v1/`
- `outputs/np_k6_p0_simtime_2ps_recovery_v2_setup/`
