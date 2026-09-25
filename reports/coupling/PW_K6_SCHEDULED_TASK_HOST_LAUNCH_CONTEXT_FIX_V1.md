# PW_K6_SCHEDULED_TASK_HOST_LAUNCH_CONTEXT_FIX_V1

## STATUS

**BLOCKED_TASK_JOB_CONTEXT**

- solver_invocations_this_task = 0
- scientific_solver_entries_this_task = 0
- S16 attempt_001 remains FAILED_PREENTRY; it has only HOST_START_INTENT.
- S16 attempt_002 was not created.
- No scientific FDTD settings, Scheduled Task production definition, queue schema, slot registry, Traditional branch, or autofill policy was changed.
- Hard-gate classification: E — BLOCKED_TASK_JOB_CONTEXT.
- Underlying mechanism A-like breakaway mismatch is proven, but the actual Scheduled Task Job has no safe breakaway flag; the policy therefore blocks rather than running a scientific host inside that Job.

## S15 VS S16 LAUNCH CONTEXT

### S15 validated direct path

- S15 was launched through the validated direct SSH dispatcher path.
- The direct-path zero-solver control probe used the same host executable family and recorded:
  - current executable: C:\Users\DELL\anaconda3\python.exe;
  - parent: N:\anaconda_envs\RCP_LCP\python.exe -;
  - IsProcessInJob = true;
  - Job flags 10240 = BREAKAWAY_OK | KILL_ON_JOB_CLOSE;
  - production flags CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB succeeded for a harmless cmd.exe, exit code 0.
- This matches the previously validated S15 direct-launch lineage. It is not evidence that the Scheduled Task shares the same Job policy.

### S16 failing Scheduled Task

- Task: \APCD_V3_COUPLING_DISPATCHER
- Principal: S-1-5-21-2958591235-2706656562-1210676212-1001, InteractiveToken, desktop-nne313k\DELL.
- Action:
  - executable: C:\Users\DELL\anaconda3\pythonw.exe
  - arguments: "D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\shared_fdtd\tools\v3_dispatcher_service.py" --once
- The exact Scheduled Task clone ran under:
  - current pythonw.exe PID 15132;
  - parent svchost.exe PID 4368, parent PID 2580;
  - whoami = desktop-nne313k\dell.
- The original S16 runtime evidence remains:
  - D:\apcd_runtime\global_fdtd_control_v3\cases\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_S16\attempt_001\events.jsonl
  - one HOST_START_INTENT at 2026-09-25T04:43:40.802632+00:00;
  - no HOST_PROCESS_STARTED, native FSP, H5, raw truth, process, or solver entry.

## CREATEPROCESS ERROR

The actual Scheduled Task-context probe called the same Win32 API and flags as production with only a harmless dummy target:

- command line: C:\Windows\System32\cmd.exe /d /c exit 0
- creation flags: 150994944 = 0x09000000 = CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB
- CreateProcessW result: FALSE
- GetLastError = 5
- formatted meaning: Access is denied
- no child PID was created.

Controls in the same Scheduled Task context:

- flags CREATE_NO_WINDOW only (134217728) succeeded;
- dummy child exited with code 0;
- the same production flags in the direct validated path succeeded.

The raw evidence is retained at:

- D:\apcd_runtime\global_fdtd_control_v3\task_launch_context_probe_v1\direct_result.json
- D:\apcd_runtime\global_fdtd_control_v3\task_launch_context_probe_v1\scheduled_result.json

The prior dispatcher used ctypes.windll.kernel32.CreateProcessW with an unconditional breakaway flag and then the dispatcher’s broad pre-entry exception path reduced the failure to FAILED_PREENTRY. The new error path preserves the error in runtime evidence as HOST_PROCESS_START_FAILED.

## WINDOWS JOB EVIDENCE

| Context | In Job | Query extended limits | Limit flags | BREAKAWAY_OK | SILENT_BREAKAWAY_OK | KILL_ON_JOB_CLOSE |
|---|---:|---:|---:|---:|---:|---:|
| S15-like direct SSH path | true | true | 10240 | true | false | true |
| S16 Scheduled Task clone | true | true | 0 | false | false | false |

Additional evidence:

- QueryInformationJobObject(NULL, JobObjectExtendedLimitInformation, ...) succeeded in both contexts.
- Scheduled Task clone process parent was svchost.exe PID 4368; the production action process was pythonw.exe.
- No nested Job-chain detail was exposed by the available current-process API query. The policy treats an observable Job with neither explicit nor silent breakaway as restrictive.
- The scheduled task XML and clone evidence are retained under:
  - D:\apcd_runtime\global_fdtd_control_v3\task_launch_context_probe_v1\dispatcher_original.xml
  - D:\apcd_runtime\global_fdtd_control_v3\task_launch_context_probe_v1\probe_task.xml

## ROOT CAUSE

Final hard-gate classification: E — BLOCKED_TASK_JOB_CONTEXT.

The unconditional CREATE_BREAKAWAY_FROM_JOB was incompatible with the Scheduled Task’s restrictive Job and produced ERROR_ACCESS_DENIED. Removing the flag allows a harmless child to run inside the Job, but the task contract explicitly forbids silently running a scientific host inside a restrictive Job with no safe breakaway. No already-validated Scheduled-Task-equivalent out-of-Job route was found; the direct SSH path is not an equivalent Scheduled Task context.

Therefore the scientific host launch remains blocked. No S16 retry is authorized by this result.

## MINIMAL FIX

D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\shared_fdtd\tools\v3_dispatcher_service.py was minimally hardened:

1. Uses IsProcessInJob and QueryInformationJobObject.
2. No Job: uses CREATE_NO_WINDOW without breakaway.
3. SILENT_BREAKAWAY_OK: uses no unnecessary explicit breakaway flag.
4. BREAKAWAY_OK: uses CREATE_BREAKAWAY_FROM_JOB.
5. Restrictive Job with no safe breakaway: raises BLOCKED_TASK_JOB_CONTEXT; it does not launch the scientific host.
6. CreateProcessW uses use_last_error=True and preserves the exact error code/message.
7. start_host appends HOST_PROCESS_START_FAILED with launch-context evidence before re-raising.

This is a safety fix and evidence fix, not a production launch-path fix. It deliberately stops at the task-context gate.

The patched direct zero-solver probe launched a harmless cmd.exe successfully. The patched Scheduled Task probe returned LaunchContextError: BLOCKED_TASK_JOB_CONTEXT with job_limit_flags=0, and launched no child.

## ZERO-SOLVER SCHEDULED-TASK REPRO

A temporary clone of the actual dispatcher task was registered with the same principal/settings and a harmless probe action. It was unregistered after the run; the production task definition was restored and remains ready.

Evidence:

- Raw CreateProcessW reproduction:
  - exact production flags fail with GetLastError=5;
  - no-breakaway dummy succeeds and exits 0.
- Patched shared-launch reproduction:
  - direct path: harmless dummy launch PASS;
  - Scheduled Task path: BLOCKED_TASK_JOB_CONTEXT, no dummy host launch.
- Actual Scheduled Task clone gate harness:
  - two repeated Start-ScheduledTask runs;
  - child survived wrapper exit on both runs;
  - watcher survived wrapper exit on both runs;
  - solver_invocations=0;
  - scientific_solver_entries=0;
  - new_entry_hold stayed 1, health_status=PASS, control_generation=17;
  - S16 queue state stayed FAILED_PREENTRY;
  - task clone was removed after validation.

Harness evidence:

D:\apcd_runtime\global_fdtd_control_v3\task_launch_context_probe_v1\scheduled_task_gate_v1\result.json

The A–J safety points are covered as follows: actual trigger/action identity and dummy process (A–B), wrapper/child survival and Job behavior (C–E), exact preserved GetLastError (F), watcher survival (G), unchanged S16/hold state (H), repeated idempotent trigger (I), and hold/no unrelated scientific entry (J).

## REGRESSION

All runs were zero-solver.

- Core global: 20/20 PASS
- Core branch: 20/20 PASS
- Core chaos: 12/12 PASS
- Dispatcher detach: PASS
- Pre-entry recovery: 16/16 PASS
- Exact permit: 14/14 PASS; solver invocations 0; entries 0
- SHA256 canonicalization: PASS; solver invocations 0; entries 0
- Post-entry truth-before-release race: 17/17 PASS; solver invocations 0; entries 0
- External process watcher: PASS; solver invocations 0
- Strict fenced orphan truth adoption: 30/30 PASS
- PW launcher: PASS; solver invocations 0
- Resource-aware control: PASS; solver runs 0; entries 0
- Entered-exception isolation: 16/16 PASS; solver runs 0

The corrected core-suite invocation supplied its required temporary output directory. No solver executable was launched by this task.

## S16 ATTEMPT_002

NOT CREATED.

Reason: the actual Scheduled Task context remains a restrictive Job with no safe breakaway, and no validated equivalent out-of-Job route exists. attempt_001 is not reused. No attempt_003 was created.

## PRODUCTION RESUME STATE

- new_entry_hold = 1
- health_status = PASS
- control_generation = 17
- temporary_runtime_cap = NULL
- coupling_ml: cap 2, enabled 1
- traditional: cap 1, enabled 0
- GLOBAL_SLOT_1/2/3: all FREE
- S15: RELEASED, previously SCIENTIFIC_VALID
- S16 attempt_001: FAILED_PREENTRY
- Coupling-ML autofill remains disabled by hold; no new queue entry was created.
- No GPU lease or resource reservation remains active for S16.
- No S16 native/post FSP, H5, raw, projection, archive, or terminal truth exists.

## CONTROL SAFETY

Final observed counters remain:

- FOREIGN_MUTATION_COUNT = 0
- DUPLICATE_SCIENTIFIC_ENTRY_COUNT = 0
- GLOBAL_CAPACITY_VIOLATION_COUNT = 0
- AUTO_REFILL_COUNT = 0
- solver_invocations_this_task = 0
- scientific_solver_entries_this_task = 0

The only modified production source is the shared dispatcher launch-context guard and failure evidence path. Scientific settings, physics contracts, FDTD setup, Traditional, registry, queue schema, slot schema, and production Scheduled Task action were not modified.

## GIT

- branch: work/mdc-np-coupling-ml-v1
- HEAD before/after task: be19c97e63034c2b5f43bc6242ad46107157c7b4
- upstream: NO_UPSTREAM
- worktree: dirty by pre-existing runtime/report/output artifacts; this task additionally modified:
  - scripts/shared_fdtd/tools/v3_dispatcher_service.py
  - reports/coupling/PW_K6_SCHEDULED_TASK_HOST_LAUNCH_CONTEXT_FIX_V1.md
- commit: not created
- push: NOT_PUSHED

## NEXT

Provide or validate an equivalent out-of-Job Scheduled Task launch path, or explicitly authorize a separate platform-owner change to the Task Scheduler context. Until that evidence exists, keep new_entry_hold=TRUE; do not create S16 attempt_002 and do not resume autofill.
