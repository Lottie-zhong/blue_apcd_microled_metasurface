# SHARED_V3_INSTRUMENTED_REAL_GPU_CANARY_S14_V1

## STATUS

`BLOCKED_PREENTRY`

The single authorized S14 gate was attempted once. No new real scientific solver entry occurred. The gate reached `HOST_PROCESS_STARTED`, but the host process disappeared before `HOST_STARTED`, `SOLVER_ENTRY_INTENT`, `GPU_ENGINE_ENTRY_CONFIRMED`, or `SCIENTIFIC_SOLVER_ENTERED`.

## PREENTRY GATES

- Remote identity: `DESKTOP-NNE313K` / `desktop-nne313k\\dell`.
- Branch: `work/mdc-np-coupling-ml-v1`.
- HEAD before and after the gate: `7d844158e2318a56b7d34eb01c26d3da45b98822`.
- Control before gate: `new_entry_hold=1`, `temporary_runtime_cap=1`, `health_status=PASS`, `control_generation=9`.
- S14 pre-entry manifest: `solver_entered=false`, `solver_invocations=0`, `replay_count=0`; pre-FSP SHA256 `4b355a9b736020e4ea0c4a9bf8efbd6bd1e1369f19f748745c12da415aa1bb4f`.
- S12/S13 were already `POSTENTRY_NO_TRUTH`; they were not replayed.
- S15/S16 had zero scientific entries and remained non-entered.
- Foreign mutation count: `0`.
- Duplicate scientific entry count: `0`.

The corrected breakaway watcher/telemetry pair was started before the gate. Its heartbeat advanced, then both observers were stopped by the exact stop flag after the failure evidence was captured.

## ENTRY / GENERATION

- Admission was opened once through the shared control API at `2026-09-24T14:23:38Z`, generation `10`, hold `false`.
- The gate restored the hold at generation `11`.
- S14 lease/slot: `K6V1_S14 / attempt_001 / GLOBAL_SLOT_2 / fencing_generation=44`.
- S14 queue state after the event: `HOST_STARTED`.
- S14 event count: `2`:
  - `HOST_START_INTENT`
  - `HOST_PROCESS_STARTED`, host PID `21060`
- `S14_SCIENTIFIC_SOLVER_ENTRY_COUNT=0`.
- `S14_GPU_ENGINE_ENTRY_CONFIRMED_COUNT=0`.
- `S14_ATTEMPT_002_COUNT=0`.

## SOLVER LIFECYCLE

Observed lifecycle:

```text
HOST_START_INTENT -> HOST_PROCESS_STARTED(pid=21060) -> host disappeared
```

No `HOST_STARTED`, `SOLVER_ENTRY_INTENT`, `GPU_ENGINE_ENTRY_CONFIRMED`, or `SCIENTIFIC_SOLVER_ENTERED` event was written. No S14 solver process, MPI process, native FSP, H5, raw spectrum, archive, or terminal truth exists.

Historical safety counts remain unchanged:

| Case | Existing scientific entries | New entries in this task | Replay / new attempt |
|---|---:|---:|---:|
| S12 | 1 | 0 | 0 |
| S13 | 1 | 0 | 0 |
| S14 | 0 | 0 | 0 |
| S15 | 0 | 0 | 0 |
| S16 | 0 | 0 | 0 |

## WATCHER / GPU TELEMETRY

- The first observer launch was discarded before the gate because its detached processes did not survive the SSH session.
- The corrected observer pair used `CREATE_NO_WINDOW | DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB` and survived the SSH session.
- Watcher heartbeat reached `2026-09-24T14:25:39.855066Z` before stop.
- The watcher saw baseline `fdtd-solutions.exe -server -hide` processes only; no S14 FDTD engine, `mpiexec`, or `smpd` lineage appeared.
- GPU telemetry stayed at approximately 1–2% utilization, about 1037 MB / 10240 MB VRAM, approximately 100 W and 60 C; no solver workload signature appeared.
- Windows event delta: `event_count=0`, `artifact_count=0` for the captured window.

## TRUTH BUNDLE

Absent for S14. Preserved evidence is limited to:

- `pre_entry_manifest.json`
- `pre_canary_evidence_manifest.json`
- setup-only `setup/runtime.fsp`
- runtime `events.jsonl`
- external watcher JSONL/heartbeat/telemetry
- `s14_failure_evidence_snapshot.json`
- `windows_event_delta.json`

The setup-only FSP is not scientific truth.

## ROOT-CAUSE EVIDENCE

The shared dispatcher launches the host with `CreateProcessW` and previously supplied only `CREATE_NO_WINDOW` (`0x08000000`). The dispatcher/gate returns immediately after `HOST_PROCESS_STARTED`; the child therefore had no explicit breakaway from a Windows job/process boundary. The host disappeared before its first durable host event. This is the strongest available infrastructure explanation for the pre-entry loss.

The exact Windows termination record is unavailable: the captured Application/System/TaskScheduler/WER/DxgKrnl/Display/NVIDIA window contained no matching event, and the 0.5 s watcher interval did not observe PID `21060` after creation. Therefore this is classified as an evidence-backed infrastructure cause class, not a solver or physics conclusion.

Minimal source correction applied after the failed gate, without rerunning the canary:

- `scripts/shared_fdtd/tools/v3_dispatcher_service.py`: add `CREATE_BREAKAWAY_FROM_JOB` to the existing `CreateProcessW` flags.
- `scripts/shared_fdtd/tests/run_v3_dispatcher_detach_zero_solver_tests.py`: zero-solver regression proving the child survives launcher exit.
- Dispatcher detach regression: `PASS`.
- Existing zero-solver regression: global `20/20`, branch `20/20`, chaos `12/12` `PASS`.

## CONTROL SAFETY

- Final admission: `new_entry_hold=1`.
- Final `temporary_runtime_cap=1`.
- Final `health_status=PASS`.
- Final `control_generation=11`.
- `GLOBAL_SLOT_1=FREE`, `GLOBAL_SLOT_3=FREE`.
- `GLOBAL_SLOT_2=RESERVED` by `coupling_ml / K6V1_S14 / attempt_001`, with `solver_entered_at=null`.
- S15 and S16 remain `WAIT_RESOURCE_CAPACITY`; no autofill occurred.
- S12/S13 remain untouched and are not replayable.
- Traditional was not touched.
- No direct SQLite mutation, no solver rerun, no S14 attempt_002, and no S15/S16 entry occurred.

The S14 RESERVED owner is intentionally preserved as stale evidence. Releasing or recovering it requires a separate shared-control/chart-reviewed action; it was not silently forced here.

## GIT / CHANGED FILES

- Branch: `work/mdc-np-coupling-ml-v1`.
- HEAD unchanged: `7d844158e2318a56b7d34eb01c26d3da45b98822`.
- Worktree remains dirty from pre-existing Coupling-ML changes plus the dispatcher correction, zero-solver regression, and this report.
- No commit and no push.
- Dispatcher source SHA256 after correction: `CDF556F041B91595AF76CE95BF4469ACDB2F056A5996CA920FD66D1D351CA299`.

## NEXT

Chart review the dispatcher breakaway correction and a shared-API stale-owner recovery procedure; do not run another S14 scientific entry in this task.

## SAFETY COUNTS

```text
ACTUAL_SOLVER_ENTRY_COUNT_THIS_TASK=0
GPU_ENGINE_ENTRY_CONFIRMED_COUNT_THIS_TASK=0
S14_ENTRY_COUNT_THIS_TASK=0
S14_ATTEMPT_002_COUNT=0
S12_REPLAY_COUNT=0
S13_REPLAY_COUNT=0
S15_ENTRY_COUNT=0
S16_ENTRY_COUNT=0
DUPLICATE_SCIENTIFIC_ENTRY_COUNT=0
FOREIGN_MUTATION_COUNT=0
```
