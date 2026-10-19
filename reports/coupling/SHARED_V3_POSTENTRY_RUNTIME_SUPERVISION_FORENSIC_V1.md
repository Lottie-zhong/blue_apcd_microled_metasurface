# SHARED_V3_POSTENTRY_RUNTIME_SUPERVISION_FORENSIC_V1

## Status

`BLOCKED / UNRESOLVED_POSTENTRY_EARLY_EXIT_ROOT_CAUSE`

This report is zero-solver only. No replay, attempt creation, S14/S15/S16 entry, registry edit, hold release, or solver launch occurred.

Frozen project facts remain:

- `REAL_GPU_RUNTIME_EARLY_EXIT_REPEAT=YES`
- S12 and S13: `POSTENTRY_NO_TRUTH`, one scientific entry each, no durable native/H5/raw truth
- `SHARED_V3_POSTENTRY_RUNTIME_SUPERVISION_STABLE=NO`
- `REAL_PRODUCTION_GPU_TRUTH_PERSISTENCE_STABLE=YES`
- `FINAL_LAUNCH_REVALIDATION_ZERO_SOLVER_VALIDATED=YES`
- `PW_K6_SEED_DB_V1_RESUME_AUTOFILL=NO`
- `TRADITIONAL_GPU_ADOPTION_READY=NO`

## S05 / S12 / S13 timeline

All timestamps below are UTC from attempt ledgers, runtime events, p0 logs, and the canonical SQLite event/queue records.

| Case | Entry evidence | Solver/mesh evidence | Truth/terminal evidence |
|---|---|---|---|
| S05 | host 10:34:02; scientific entry 10:34:39; GPU engine and MPI lineage recorded | p0 log reaches `Simulation completed successfully` at 10:43:20; native durable 10:43:53 | `SOLVER_RETURNED` 10:44:08; `SCIENTIFIC_VALID` and release 10:46:20 |
| S12 | host 12:10:01; engine confirmed 12:10:17.967; entry 12:10:20.374 | p0 reaches initial `Starting meshing`; no iteration/progress/return/native truth | reconciler closeout 12:11:07.196; terminal 12:11:07.516; release after quarantine |
| S13 | host 12:54:39/40; engine confirmed 12:55:02.647; entry 12:55:02.776 | p0 completes two mesh passes, then stops at a third `Starting meshing`; no iteration/progress/return/native truth | reconciler closeout 12:56:06.833; terminal 12:56:07.157; release after quarantine |

S12 and S13 therefore share the same post-entry/no-truth signature, but their saved evidence does not prove whether the engine exited first, the host exited first, or an external Windows lifecycle mechanism removed the tree.

## Supervision and terminalization audit

The shared reconciler path is:

1. require exactly one `SCIENTIFIC_SOLVER_ENTERED` and no durable truth;
2. call the supplied `process_probe`;
3. preserve with `SOLVER_STILL_RUNNING` when any matching process is returned;
4. only when the probe returns an empty list, write `POSTENTRY_NO_TRUTH`, quarantine, release the slot, and set `replay=0`.

The V3 service probe uses `psutil` snapshot data and requires both the case and attempt text in the command line. It has no elapsed-time threshold, heartbeat TTL, stale grace timer, or solver-kill operation. The V3 Task Scheduler reconciler/dispatcher tasks are one-minute `--once` tasks with `IgnoreNew`; task XML showed no short execution limit. No matching Task Scheduler operational-history records were returned for S12/S13.

The weakness is not a proven false-positive terminalization. The weakness is an in-process observation boundary: the host owns the child wait loop and the observer finalizer. If the host/observer disappears before child return, `process_exit_provenance.json` and `final_log_tail.json` are never written. The next reconciler then has only a current process probe and no durable historical exit record.

## Process-kill / Job Object audit

Source search of the shared V3 engine, dispatcher, reconciler, host lifecycle, process identity, and GPU launcher found no `TerminateProcess`, `taskkill`, `Stop-Process`, `psutil.kill`, `psutil.terminate`, `CreateJobObject`, `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, `BREAKAWAY`, or CTRL-break/CTRL-C cleanup path. `CloseHandle` is used only to close the handles returned by `CreateProcessW`.

The V3 host is launched with `CreateProcessW(..., CREATE_NO_WINDOW)`; the GPU child is launched with `subprocess.Popen(..., CREATE_NO_WINDOW)`. No Job Object is created or configured by this code. Historical Job Object membership cannot be recovered after the S12/S13 processes have disappeared, so Windows Job Object involvement remains unproven.

The generic durable-canary helper contains a separate `schtasks /End` utility, but that path is not the S12/S13 V3 GPU launch path and there is no matching S12/S13 invocation evidence.

## Parent-host and observer lifetime

S13 durable timeline evidence contains:

- child `fdtd-solutions.exe` PID 18040 with parent host PID 32316;
- MPI/engine PIDs 13416/13000 after engine entry;
- durable observer rows through 12:55:02.478 while the engine was visible;
- p0 log mtime 12:55:02.867;
- no final observer row, `process_exit_provenance.json`, or `final_log_tail.json`.

This proves the observer could write polling evidence and then failed to reach its finalizer. It does not prove the cause of the host/engine disappearance. S12 has the same missing-finalizer/no-truth pattern but no equivalent persisted timeline.

## Meshing and run-call comparison

- S05: normal mesh/initialization followed by iterations and successful completion.
- S12: initial GPU initialization and mesh start only; no completed science iteration.
- S13: two completed mesh passes followed by a third mesh start; no science iteration.
- The actual S12 and S13 `run_gpu.lsf` each contain exactly one `run("FDTD","GPU",...)` call, followed by three monitor `getdata` calls and `save`.

Therefore duplicate scientific invocation and multiple `run` calls are not supported by the saved evidence.

## Root-cause verdict

**Proven:** repeated post-entry early-exit/no-truth plus an observability gap: final exit provenance is not externalized before the host/observer can disappear, and reconciler closeout is based on a later point-in-time exact process match.

**Not proven:** A controller timeout, heartbeat timeout, lease TTL, cleanup action, Job Object kill, Task Scheduler kill, callback regression, licensing failure, or specific FDTD engine defect as the direct cause of the S12/S13 process disappearance.

No shared infrastructure patch was applied because the task requires a specific proven cause before changing runtime lifecycle behavior.

## Zero-solver failure-injection A-L

`scripts/shared_fdtd/tests/run_postentry_runtime_supervision_zero_solver_tests.py`: **12/12 PASS; solver_invocations=0**.

- A entered child alive past reconcile: PASS, no terminalization
- B long meshing: PASS, no terminalization
- C delayed heartbeat with engine alive: PASS, no kill/terminalization
- D lease TTL boundary with engine alive: PASS, preserve
- E controller exits while detached child survives: PASS
- F scheduled wrapper exits while child survives: PASS
- G hold becomes true after entry: PASS, child state preserved
- H branch disabled after entry: PASS, child state preserved
- I observer failure: PASS, no slot release
- J no truth before solver return: PASS, wait/preserve
- K process disappears: PASS, quarantine/closeout with replay 0
- L zero solver: PASS

Other zero-solver regressions:

- shared global/branch/chaos: 20/20, 20/20, 12/12 PASS
- GPU engine-exit observability: 11/11 PASS
- backend mutex: 7/7 PASS
- GPU native bundle: 11/11 PASS
- postsolver persistence: PASS
- postsolver production integration: 12/12 PASS

## Current control state

- `new_entry_hold=TRUE`, temporary runtime cap `1`, health `PASS`, generation `9`
- coupling-ML branch remains enabled with formal cap `2`
- `GLOBAL_SLOT_1/2/3`: all `FREE`
- S14/S15/S16: `WAIT_RESOURCE_CAPACITY`, scientific entry count `0`
- S12/S13: `POSTENTRY_NO_TRUTH`, no replay, no attempt_002
- no new scientific solver entry in this task

## Required next route

Do not select a new scientific experiment. Chart review should first decide whether to implement an external durable watcher/exit-evidence design and a controlled zero-solver reproduction of the host/child disappearance. Until that is proven stable, keep the production hold and do not resume autofill.
