# APCD GPU platform V2 offline MVP

This independent implementation is confined to `platform_v2`. It imports no V1 Runner, Controller, Scheduler, recovery implementation or mutable production state. The worktree shares the repository's base commit only. Production execution is intentionally unavailable; fixture completion is `DONE_OFFLINE`, never scientific truth validity.

Remote worktree: `D:\project\worktrees\blue_apcd_gpu_platform_v2_cleanroom_v1`.
Interpreter: `N:\anaconda_envs\RCP_LCP\python.exe` (3.10.20).
No package installation, Scheduler modification, WinSW service, native API session or scientific solver was performed for this MVP.

## Execution and ownership

Strict Pydantic configuration validates one explicit JSON document. Duplicate JSON keys, extra fields, conflicting GPU environment values and any V2 environment override are rejected. The ledger binds one config SHA. Only `OFFLINE_* / attempt_001 / OFFLINE_FIXTURE` requests and source files beginning `OFFLINE_` are admitted; production runtime roots are excluded.

SQLite uses `BEGIN IMMEDIATE`, WAL and `synchronous=FULL`. A unique case/attempt and request SHA cannot be registered twice. One fenced slot holds a structured process identity (PID, creation time, executable, command line, parent and user). The durable entry transaction sets `entered=1` and `ENTRY_UNCERTAIN` before calling even the fake backend. A crash conservatively consumes that fixture entry. Live, unknown or reused PID evidence cannot authorize an automatic scientific replay.

`REGISTERED -> CLAIMED -> ENTRY_UNCERTAIN -> DONE_OFFLINE` is the successful fixture path. A verified pre-entry failure becomes terminal `FAILED_PREENTRY`. Post-entry failure retains the slot; dead-owner reconciliation gives `NEEDS_REVIEW_NO_REPLAY` and retains it because descendants may still be alive. There is no force-release or replay CLI. Explicit audited cutover/recovery functionality remains a future safety gate.

The pair validator preserves the FSP basename and the whole same-stem sidecar tree, verifies SHA and stable file identity/size, checks finite complete HDF5 E/H fields, compares source and archive, fsyncs new copies, and publishes a directory after its receipt is written. Interrupted `.partial.*` directories are evidence and are never treated as completed archives. No existing destination is overwritten. LOAD-only verifies hashes in a `finally` block even if a reader fails. Native FSP semantic readability still requires future authorized native LOAD-only qualification.

## Modules

| Module | Sole authority |
|---|---|
| `config.py` | strict config, request identity, contract SHA, offline safety scope |
| `ledger.py` | entry budget, task transitions, single slot, fencing, events |
| `processes.py` | process identity and read-only census |
| `worker.py` | fake backend orchestration only |
| `artifacts.py` | native pair inventory, archive, read-only reader guard |
| `native.py` | nondispatched official launch specification and LOAD-only reader |
| `coupling.py` | shape, complex labels, P_scale, hash-pinned consumer comparison |
| `__main__.py` | fixture execution and independent audit CLI |

## Offline verification

From this directory on the remote host:

```powershell
$env:APCD_TEST_COUPLING_ROOT = 'D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1'
& 'N:\anaconda_envs\RCP_LCP\python.exe' -m pytest -q --junitxml=reports/offline_junit.xml
& 'N:\anaconda_envs\RCP_LCP\python.exe' -m ruff check apcd_gpu_v2 tests
& 'N:\anaconda_envs\RCP_LCP\python.exe' -m apcd_gpu_v2 audit --config 'D:\apcd_runtime\gpu_platform_v2_offline_20261009_v1\offline_config.json'
```

The already completed CLI acceptance request cannot be rerun. A fresh fixture requires a new OFFLINE identity and matching request/config/source SHA. `NativeBackend.run()` always refuses. Never enable scientific execution by modifying offline constants; qualification and explicit authorization must precede any production implementation.

Read `docs/GPU_PLATFORM_AGENT_CONTEXT_V1.md`, then `docs/CONFLICT_AUDIT_AND_DECISION.md` and `reports/acceptance_summary.json`. All reports are evidence snapshots, not launch authority.

Native acceptance follow-up: see `docs/NATIVE_ACCEPTANCE_DECISION_V1.md` and `reports/native_acceptance_v1`. Real LOAD/importer/systemcheck are now verified; production cutover remains BLOCKED. Historical MVP reports above retain their original offline scope.

Latest owner closure: `docs/UNKNOWN_PROCESS_CLOSURE_DECISION_V1.md`, `reports/unknown_closure_v1`. Qualification remains BLOCKED_WITH_IDENTIFIED_OWNER_RISK; the cutover transaction is prepared but not executed.
