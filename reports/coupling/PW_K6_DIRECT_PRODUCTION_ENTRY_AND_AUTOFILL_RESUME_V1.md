# PW_K6_DIRECT_PRODUCTION_ENTRY_AND_AUTOFILL_RESUME_V1

## STATUS

**PASS — DIRECT_PRODUCTION_ENTRY_VALIDATED; AUTOFILL_READY_IDLE**

S16 completed through the clean direct-authoritative path. Coupling-ML production control was resumed after terminal truth and release checks. No pending K6 queue item remained, so the direct autofill tick launched no successor and did not create or replay a case.

## NEW PRODUCTION HEAD

- branch: `work/mdc-np-coupling-ml-v1`
- HEAD: `3a4cf14b4ceda2e3e5930cbd3833e71b7809ac8d`
- safety-fix commit: `fix: reject unsafe scheduled-task scientific launch context`
- push: `NOT_PUSHED`

## SCHEDULED TASK POLICY

- `\APCD_V3_COUPLING_DISPATCHER`: **DISABLED** after direct authority was validated.
- Scheduled Task scientific entry: **DISABLED / FAIL_CLOSED**.
- The Scheduled Task was not used for S16 scientific entry and cannot start a scientific host in the restrictive Job context.
- No service, broker, daemon, privileged helper, or alternative Scheduled Task escape mechanism was created.

## DIRECT ENTRY AUTHORITY

- authoritative path: NetBird SSH direct dispatcher context on `DESKTOP-NNE313K`, `dell`.
- path: Shared V3 admission -> owner/fencing -> resource reservation -> final launch revalidation -> direct host -> controller/dispatcher -> GPU solver.
- S16 used one exact one-shot permit, `authorization_generation=19`, consumed at final launch revalidation.
- final production control generation after resume: `20`.

## ZERO-SOLVER DIRECT REPRO

**PASS**.

- direct parent Job: `BREAKAWAY_OK | KILL_ON_JOB_CLOSE`, flags `10240`.
- production creation flags: `CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB`.
- harmless detached child survived launcher exit; independent watcher heartbeat/timeline survived and stopped through its stop flag.
- `solver_invocations=0`; `scientific_solver_entries=0`; `scheduled_task_entry_used=false`.
- direct zero-solver regression suites and the previously frozen Shared V3 suites remained PASS.

## S16 ATTEMPT_002

- case: `K6V1_S16 / attempt_002`
- pre-FSP SHA256: `641d0fdb57b6c5ecf1267841a41d6edbfd0ca13e38f068fc1611ae1a18b7ac08`
- physical-contract SHA256: `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`
- one initial pre-entry host start was blocked by the restored global hold before solver entry: `solver_entered=false`, `run_invocation_count=0`, no truth, no replay.
- same attempt was safely continued with the exact permit; this was not a scientific replay and no `attempt_003` was created.
- `SCIENTIFIC_SOLVER_ENTERED=1`; `GPU_ENGINE_ENTRY_CONFIRMED=1`; `run_invocation_count=1`; `replay=false`.
- GPU/MPI lineage: `fdtd-engine-msmpi.exe -gpu -t 1`, `mpiexec -n 1`, 12-engine scientific lineage.
- solver log: completed successfully; wall time `519.840000 s`; peak memory `1.389421 GiB`.
- native FSP SHA256: `177e8274f34335356412fe5916c2f38d28a1a6b567584b3158150c4bd3d67b91`.
- sibling H5: `76,603,189 bytes`, SHA256 `e78f55a3bd8adb9a0fa8cf35afea6dffbece21202f83c50be2568093bbf69645`.
- fresh native LOAD-only validation: `PASS`.
- raw SHA256: `c838c5ec692eb00dcb8e7fc85b01f7dc487e2594914509a2b42c73dd5ec6faa8`.
- 21-wavelength projection, orders, complex fields/state and HF archive: present.
- terminal: `SCIENTIFIC_VALID`; release: `RELEASED`; slot: `GLOBAL_SLOT_2`.

## NORMAL PATH VERDICT

`DIRECT_SHARED_V3_NORMAL_POSTFIX_PRODUCTION_PATH_VALIDATED = YES`

The stale watcher generated a conservative `TRUTH_FINALIZATION_PENDING` observation while still tied to the first pre-entry host PID. It never released or killed the live S16 owner. The watcher was stopped using its manifest stop flag; the authoritative host then completed native truth, postprocessing, raw/projection, HF archive, and release normally.

## AUTOFILL STATE

- Coupling-ML: cap `2`, enabled `1`.
- Global cap: `3`.
- GPU physical cap: `3`.
- `new_entry_hold=0`, `temporary_runtime_cap=NULL`, `health_status=PASS`, generation `20`.
- one direct dispatcher tick was executed after resume: `launched=[]`.
- no `WAIT_RESOURCE_CAPACITY` K6 item was present; no successor was enqueued, replayed, or fabricated.
- autofill is **direct-authoritative and ready/idle**, pending an explicitly queued future production geometry.

## ACTIVE/COMPLETED CASES

- active cases: none; all three global slots FREE; no active reservation or GPU lease.
- valid K6 data: `S02`, `S03`, `S04`, `S05`, `S15`, `S16` — 6 `SCIENTIFIC_VALID` cases.
- `S14/attempt_004`: `RECOVERED_ADOPTED` / post-entry-no-truth authority; not counted as new native scientific truth.
- `S01`, `S06`–`S13`: historical failed/pre-entry or post-entry-no-truth states; not replayed.
- `S16/attempt_001`: historical `FAILED_PREENTRY`; `attempt_002` is the sole scientific S16 entry.

## DATA QUALITY

S15 and S16 carry the frozen integrated 3D periodic PW contract: native M1 materials, 5 nm GPU setup, X/P_XLIKE, 440–460 nm at 21 points, fixed MDC/spacer, monitor/reference-plane contract, raw complex fields, projection/order payloads, canonical state and durable native FSP plus sibling H5.

## 8G STATUS

`NOT_REACHED`: 6 valid K6 geometries are authoritative; the eighth valid geometry has not been produced.

## 12G STATUS

`NOT_REACHED`: no 12-geometry Ridge/GP/shallow-MLP baseline was run.

## CONTROL SAFETY

- `FOREIGN_MUTATION_COUNT=0`.
- `DUPLICATE_SCIENTIFIC_ENTRY_COUNT=0`.
- no nonzero health metric observed.
- Traditional: cap `1`, disabled.
- no solver kill, replay, attempt_003, attempt_004 creation for S16, queue rewrite, or registry mutation.
- Scheduled Task was disabled; its action and production physics were not changed.
- no automation was created.

## GIT

- branch: `work/mdc-np-coupling-ml-v1`
- HEAD: `3a4cf14b4ceda2e3e5930cbd3833e71b7809ac8d`
- upstream: `NO_UPSTREAM`
- worktree: `DIRTY` from pre-existing runtime/report/output/recovery artifacts; this report is an additional uncommitted report artifact.
- push: `NOT_PUSHED`.

## NEXT

Keep the direct production authority ready. The next production action is to queue or authorize the next uncompleted K6 geometry; do not replay S01/S06–S13 or reinterpret S14 adoption as fresh native truth.
