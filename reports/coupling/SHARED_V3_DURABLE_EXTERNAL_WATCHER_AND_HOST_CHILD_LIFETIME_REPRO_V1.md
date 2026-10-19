# SHARED_V3_DURABLE_EXTERNAL_WATCHER_AND_HOST_CHILD_LIFETIME_REPRO_V1

## STATUS

PASS_WITH_REAL_CANARY_GATE

The zero-solver external watcher and the A-J host/child lifetime
reproduction matrix are complete. The evidence supports exactly one future
instrumented real GPU canary after Chart review. No real canary is launched by
this task.

## HISTORICAL EVENT EVIDENCE

Read-only Windows evidence was collected on `DESKTOP-NNE313K` for local time
`2026-09-24 18:20:00` through `21:10:00`, covering the S12 window
(`20:10-20:11`) and S13 window (`20:54-20:56`). The query covered:

- Application and System
- `Microsoft-Windows-TaskScheduler/Operational`
- `Microsoft-Windows-WER-Diag/Operational`
- `Microsoft-Windows-DxgKrnl/Operational`
- `Microsoft-Windows-Display/Operational`
- WER, dump, LiveKernelReports, Minidump, and NVIDIA artifact locations

Observed: 10 Windows events and 0 crash artifacts.

- 9 Application events were unrelated VSTO 4.0 event 4096 entries from the
  optiSLang Excel add-in signed-manifest path, at approximately 20:39-20:48.
- 1 System event was unrelated DistributedCOM event 10010 at 19:58:11.
- No event matched `fdtd-solutions.exe`, `fdtd-engine-msmpi.exe`,
  `mpiexec.exe`, `smpd.exe`, the V3 host/controller, NVIDIA, `nvlddmkm`, a
  display/GPU reset, or an APCD Task Scheduler task.
- Task Scheduler history contained no matching S12/S13 APCD execution record.

Conclusion: the Windows evidence supplies no causal OS, WER, display-driver,
GPU-reset, or scheduler evidence for either early exit. The unrelated events
must not be used as a cause.

## WATCHER DESIGN

Implemented:

- `scripts/shared_fdtd/tools/external_process_watcher.py`
- `scripts/shared_fdtd/tests/run_external_process_watcher_zero_solver_tests.py`

The watcher is a generic manifest-driven external process. A future manifest
can match `fdtd-solutions.exe`, `fdtd-engine-msmpi.exe`, `mpiexec.exe`,
`smpd.exe`, and selected launcher/host/observer/controller names or seed PIDs.
Each durable JSONL event records the watcher identity and lifetime, timestamp,
PID, PPID, process name, command line, creation time, parent relationship,
disappearance, and exit-code availability when exposed.

It writes append-only JSONL with flush plus `fsync` for every event and an
atomic heartbeat JSON file containing active rows and active PIDs. It runs as
an independent process, has no V3 SQLite writes, does not call a solver, does
not install a permanent service, and does not alter the launcher/controller,
slot allocator, registry, Traditional branch, or admission policy. It is
intentionally not wired into the production launcher in this task; the
external watcher must be started before a separately authorized future canary.

## ZERO-SOLVER REPRO MATRIX

The dummy topology used the same Windows subprocess creation mode intended for
production observation (`CREATE_NO_WINDOW`) and a temporary control database.

| Case | Reproduction | Result |
|---|---|---|
| A | normal host completion | PASS |
| B | host unexpected exit; child survives | PASS |
| C | force-terminated host; child survives | PASS |
| D | observer disappears; host and child remain | PASS |
| E | controller disappears; dummy child remains active | PASS |
| F | watcher survives controller/host disappearance | PASS |
| G | parent-close/detached lifetime path; child survives | PASS |
| H | cleanup/finally path | PASS |
| I | reconciler preserves live entry, then closes on process loss | PASS |
| J | heartbeat/lease transitions with no science | PASS |

The watcher test passed 17/17 checks, including durable `PROCESS_CREATED`,
`PROCESS_DISAPPEARED`, watcher heartbeat/start/stop, return code, and flushed
record checks. The test reported `solver_invocations=0`.

## ROOT CAUSE / REMAINING HYPOTHESES

No shared lifecycle defect was proven. The source audit found no direct
`TerminateProcess`/`taskkill` path and no explicit Job Object assignment that
would explain the historical exits. The A-J reproduction shows that an
external observer can remain alive and preserve child lifetime evidence across
host, observer, and controller disappearance, but it cannot retroactively
identify why S12/S13 disappeared because those runs had no independent
watcher.

The remaining root-cause set is therefore narrowed to FDTD/launcher/runtime
or Windows process-disappearance behavior, with the exact branch unresolved.
The historical evidence does not justify claiming an NVIDIA reset, WER crash,
Task Scheduler kill, controller kill, or child cleanup as the cause.

No scientific physics, mesh, solver setting, or comparator was changed.

## CHANGED FILES

- `scripts/shared_fdtd/tools/external_process_watcher.py`
- `scripts/shared_fdtd/tests/run_external_process_watcher_zero_solver_tests.py`
- `reports/coupling/SHARED_V3_DURABLE_EXTERNAL_WATCHER_AND_HOST_CHILD_LIFETIME_REPRO_V1.md`

No FSP, H5, raw/HF payload, runtime database, queue/slot registry, Traditional
artifact, or temporary recovery tree was changed or committed.

## TEST RESULTS

- Global zero-solver: 20/20 PASS
- Branch zero-solver: 20/20 PASS
- Chaos zero-solver: 12/12 PASS
- GPU engine-exit observability: 11/11 PASS
- Backend mutex: 7/7 PASS
- GPU native bundle: 11/11 PASS
- Post-entry runtime supervision: 12/12 PASS
- External watcher A-J: 17/17 PASS
- Postsolver persistence: PASS
- Production integration: 12/12 PASS
- Scientific solver invocations: 0

## SAFETY AUDIT

At final read-only verification:

- `new_entry_hold=1`
- `temporary_runtime_cap=1`
- `health_status=PASS`
- `control_generation=9`
- `GLOBAL_SLOT_1/2/3=FREE`
- S12/S13 remain existing `POSTENTRY_NO_TRUTH`
- S14/S15/S16 remain `WAIT_RESOURCE_CAPACITY`
- no S12/S13 replay and no attempt_002 created by this task
- no autofill was enabled
- no Traditional mutation
- foreign mutation count: 0

## NEXT

Evidence justifies **YES: exactly one instrumented real GPU canary after Chart
review**, not now. The future canary must start the independent watcher first,
use a manifest plus seed PIDs for the complete launcher/host/MPI/engine
lineage, preserve the current new-entry hold/autofill policy until explicit
authorization, run one case only, and retain the watcher JSONL and heartbeat
beside the attempt ledger. S12/S13 must remain unreplayed and no attempt_002
may be created from this task.

## END FLAGS

```text
scientific solver invocations=0
new GPU_ENGINE_ENTRY_CONFIRMED=0
S12 replay=0
S13 replay=0
attempt_002 created=NO
foreign mutation=0
new_entry_hold TRUE
autofill disabled
```
