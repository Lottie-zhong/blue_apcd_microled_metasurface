# SHARED_V3_PREENTRY_STALE_OWNER_TERMINALIZATION_FIX_AND_S14_CANARY_V3

## STATUS

`BLOCKED_PREENTRY`

This task completed the shared pre-entry recovery fix and one authorized S14
canary dispatch attempt. `K6V1_S14/attempt_002` failed before scientific
solver entry because the preparation manifest used an uppercase SHA-256 while
the host ledger used the same digest in lowercase and the host check was
case-sensitive. No scientific solver was entered.

## Authority and boundary

- Remote transport: NetBird SSH to `dell@100.81.105.58`.
- Canonical worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`.
- Branch: `work/mdc-np-coupling-ml-v1`.
- HEAD at audit: `7d844158e2318a56b7d34eb01c26d3da45b98822`.
- Runtime DB: `D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3`.
- No solver rerun, replay, attempt003, S15/S16 launch, autofill, or direct
  SQLite mutation was performed.

## Shared recovery fix

The dispatcher now terminalizes stale pre-entry ownership only when all
pre-entry gates pass: owner/fencing identity, dead host/process lineage,
zero scientific entry, no native truth, no pending event, no newer attempt,
and no hold conflict. It releases ownership idempotently, clears queue
references, records the recovery boundary once, and returns
`ALREADY_TERMINAL` on repeat calls. A zero-solver `terminal_failure.json`
with `solver_entered=false`, `solver_returned=false`, `queue_state=FAILED_PREENTRY`,
and `rerun=false` is not treated as scientific truth.

Current dispatcher SHA-256:
`7EB2BF7F8FF791D1F8D2C59A092312BF3F32E167580EB90FAA46A7DE41018659`.

The detached-launch hardening source remains:
`CDF556F041B91595AF76CE95BF4469ACDB2F056A5996CA920FD66D1D351CA299`,
including `CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB`.

## Zero-solver verification

All listed suites completed without scientific solver entry:

| Suite | Result |
|---|---|
| Global zero-solver | PASS, 20/20 |
| Branch zero-solver | PASS, 20/20 |
| Chaos zero-solver | PASS, 12/12 |
| Pre-entry recovery state machine | PASS, 16/16 |
| Integration | PASS; solver_runs=0, scientific_solver_entries=0, replays=0, foreign_mutation_count=0 |
| External watcher zero-solver | PASS, 17/17 |
| GPU observability | PASS, 11/11 |
| GPU native bundle | PASS |
| Backend mutex | PASS; solver runs=0 |
| Persistence | PASS |
| Post-entry supervision | PASS, 12/12 |

The real historical `K6V1_S14/attempt_001` recovery was also coherent:
`FAILED_PREENTRY`, entry count 0, all queue references cleared, one lease
release, and recovery manifest SHA-256
`BAA7D752D1E1E4DB1DEBD3852FC607CB20FD8C80550137C5A2311000FD1368F8`.

## Authorized S14 canary

Preparation created only a setup-only FSP and pre-entry evidence at:

`outputs\coupling_ml\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_S14\attempt_002`

The setup FSP SHA-256 was
`4B355A9B736020E4EA0C4A9BF8EFBD6BD1E1369F19F748745C12DA415AA1BB4F`.
The pre-entry manifest recorded the same digest in uppercase. The attempt
ledger recorded the same digest in lowercase:
`4b355a9b736020e4ea0c4a9bf8efbd6bd1e1369f19f748745c12da415aa1bb4f`.
The host's case-sensitive comparison raised:
`RuntimeError('PRE_FSP_HASH_MISMATCH')`.

Admission and launch evidence:

- Shared one-shot gate: PASS.
- Dispatch was filtered to exactly `K6V1_S14/attempt_002`.
- Admission control generation 12 was opened only for the filtered dispatch;
  generation 13 was used when the hold was reclosed.
- `FINAL_ADMISSION_PASS`, `FINAL_LAUNCH_REVALIDATION_PASS`, and
  `CHILD_PROCESS_STARTED` were recorded.
- `FAILED_PREENTRY` followed immediately; `solver_entered=false`,
  `run_invocation_count=0`, `replay=false`.
- Scientific solver entry count: 0.
- GPU engine entry count: 0.
- Native truth, raw/H5 truth, postprocessing truth, and terminal scientific
  truth bundle: absent.

The exact failure is therefore a preparation/provenance normalization bug,
not a scientific solver failure and not evidence of physical behavior.

## Recovery and final control-plane state

The Shared `recover_failed_preentry` API was called for
`coupling_ml/K6V1_S14/attempt_002`. The result was:

```text
status=ALREADY_TERMINAL
scientific_solver_entry_count=0
replay=0
release.status=ALREADY_FREE
release.duplicate_side_effects=0
```

Final queue state:

- S14 attempt001: `FAILED_PREENTRY`, no slot/lease/fencing references.
- S14 attempt002: `FAILED_PREENTRY`, no slot/lease/fencing references.
- S15 attempt001: `WAIT_RESOURCE_CAPACITY`, no entry.
- S16 attempt001: `WAIT_RESOURCE_CAPACITY`, no entry.

Final slots: `GLOBAL_SLOT_1`, `GLOBAL_SLOT_2`, and `GLOBAL_SLOT_3` are all
`FREE`. Admission control is `new_entry_hold=1`,
`temporary_runtime_cap=1`, `health_status=PASS`, `control_generation=13`.

The attempt event log contains exactly one
`PREENTRY_RECOVERED_FOR_ZERO_SOLVER_BOUNDARY` event for attempt002. The
external watcher and GPU telemetry were stopped by the requested stop file;
the final heartbeat records `stopped=true`, `reason=STOP_FILE`.

## Safety invariants

- `ACTUAL_SCIENTIFIC_SOLVER_ENTRY_COUNT=0` for attempt002.
- Attempt001 and attempt002 each have zero scientific entry.
- GPU scientific entry count for this task: 0.
- S12/S13 replay count: 0.
- S15/S16 entry count: 0.
- attempt003 count: 0.
- duplicate scientific entry count: 0.
- foreign mutation count: 0.
- No scientific native/raw/archive truth was created.
- S12/S13 remain classified as `INSUFFICIENT_EVIDENCE`; no replay was used.

## Git

- Branch: `work/mdc-np-coupling-ml-v1`.
- HEAD: `7d844158e2318a56b7d34eb01c26d3da45b98822`.
- Worktree: dirty from pre-existing and current uncommitted changes.
- No commit and no push.

## Next route (not executed)

Chart review should first approve a minimal pre-FSP SHA normalization and
validation fix, with the canonical digest representation made consistent at
manifest/ledger/host boundaries. No new scientific attempt is authorized by
this report. In particular, do not create attempt003 or replay attempt002.
