# PLATFORM-RECOVERY-G023-TSK-V1 Final Report

**Status: PARTIAL.** Runner-side single-request Task Scheduler lifecycle and the G023 post-entry closeout are complete. The required end-to-end Coupling queue-controller ownership by Task Scheduler remains unimplemented, so the platform is not qualified for an unattended multi-case queue. No real solver was started by this recovery task.

## G023 closeout

`K6GDP2_DEV_G023 / attempt_001 / K6V2_G023_20261006T144241Z_0a0cb192` was closed through the formal Runner closeout API as `FAILED_POSTENTRY_NO_TRUTH`. The Runner records one entry and one invocation, with zero replay. Durable truth was not available: the H5 held coordinate datasets only and validation/hashes were pending. The case is quarantined, `scientific_valid=false`, and training/handoff are disallowed. The original Coupling ledger snapshot is preserved and was not edited. The final closeout receipt SHA256 is `d6485fd48a875a5dadab14dd820b3ae2ad0c5819eee47197ee174d0b0faf07d3`; disposition `a529fafa81003c26f24640571388af4d195b28c17e2501a1c140bf21c0a90792`; journal `98817f534a379a196efb12bed610f24260a44c3c440b0c931754aa1182289af2`; terminal status `e81e8e2fc2445a0bf798668c177a01b7062faef47e6e0952875cbfb240f50ab4`; terminal registry `8beb6f9593d8783113f0411f3f2a478f75faf3fbc317c5ae70a0fad3d910c11b`. Archived lock and active marker match their captured original hashes.

## Scheduler lifecycle result

The V1 Task Scheduler API and production single-case worker task are installed. `submit-one`/`query-one` use immutable request identities and result receipts; the Scheduled Task executes one claimed request and does not auto-replay post-entry work. The installed task uses the DELL interactive token, `IgnoreNew`, least privilege, a 72-hour hard limit, and no scheduler restart. The empty-queue invocation returned `LastTaskResult=0`; it ran no case and left no pending request or worker lock. A separate final read-only census found eight long-lived `fdtd-solutions.exe -server -hide` API processes parented by Python metadata/API scripts, with no material CPU-time growth in a 3-second sample; there were no `fdtd-engine-msmpi.exe`, `mpiexec`, Runner, or Coupling queue worker processes (the first census match was the audit PowerShell command itself and was excluded on recheck). These API processes were not terminated. `nvidia-smi` showed 1% utilization and 2,164 MiB of 10,240 MiB in use by shared desktop applications, so this is not a GPU-availability/admission finding. Focused regression tests passed: **39 passed** across G023 closeout, D6 orphan closeout, Task Scheduler policy, and session lifecycle.

Synthetic tests registered three temporary Scheduler tasks. A simulated controller exited with code 23 after requesting a separate worker; the test observed Task Scheduler's duplicate trigger suppression. The worker/synthetic post-entry fault tests demonstrated zero automatic replay behavior. These are process-lifecycle fixtures only, not Lumerical or GPU tests. The retained durable-result JSON was later overwritten by a separate normal simulation invocation; the evidence JSON documents that limit. The production worker is `InteractiveToken`; actual desktop logoff was not tested because the console session was the only active session. The three temporary simulation tasks were unregistered after their XML and runtime evidence were captured. The production worker task remains registered.

## Exact serial rules

1. Global capacity is one active scientific case. The next case waits for the current Runner request to terminalize, required truth validation/persistence to finish, the Coupling ledger to reconcile, and the Runner slot to release.
2. A pre-entry failure consumes no solver entry, but the immutable failed `run_id` is retired. Coupling must reconcile it before any later dispatch; a new run ID is not an implicit retry authorization.
3. After `solver_entered=true`, the entry budget is consumed. No automatic or manual replay through the queue is allowed. Use zero-solver recovery; quarantine if truth cannot be recovered.
4. Queue progression and reconciliation must outlive the SSH caller. The current Scheduler task only owns one Runner request, not the complete Coupling queue controller.

## Remaining integration gap

Coupling `serial_queue.py` SHA256 `87ca459881e641ab5bf026767928bc09ec6470a4a0404d886331bddab4519966` starts its own process and loops over `adapter.py run-one` when `--execute` is used. It has no safe bounded resume/controller API; at the last audit it would reach all 93 remaining cases. No `\APCD_COUPLING_SERIAL_QUEUE_V1` task is registered. A companion P05 recovery at Runner HEAD `4c0de1c613612d9e23dd1ad9d8e17023322087c9` completed `RECOVERED_FAILED_PREENTRY` with `solver_entered=false`, invocations=0, replay=0, and 26 offline tests passing. Exercising Coupling reconciliation still stopped on `ENTERED_CASE_NEEDS_AUDIT:K6LDA1_DEV_D6_P05`; no Coupling files were changed. The Coupling owner must add a versioned pre-entry reconciliation state and a bounded durable controller action, then register Task Scheduler to launch that complete controller for its whole lifetime. Until that exact integration is tested, an SSH-launched queue controller followed by a Scheduled single-case worker does not meet the acceptance criterion.

Shared V3 dispatcher/allocator/launch authority and its 3-slot resource policy were not reused. Only the general principle that a separate Windows Scheduled Task has a lifecycle independent of its SSH caller was tested with synthetic fixtures.

## Execution counts

This recovery turn: real solver entries **0**, FDTD runs **0**, new cases **0**, automatic replay **0**. G023's historical Runner record remains **1 entry, 0 replay** and is now formally quarantined as above.

## Evidence

- Simulation manifest and hashes: `TASK_SCHEDULER_SIMULATION_EVIDENCE_V1.json`
- UTF-8-normalized copies of exported Scheduler definitions: `APCD_GPU_RUNNER_V1_SINGLE_CASE_WORKER.xml` and three captured/unregistered simulation task XML files
- Closeout evidence is retained under `D:\apcd_runtime\gpu_production_runner_v1\runs\K6GDP2_DEV_G023\attempt_001\K6V2_G023_20261006T144241Z_0a0cb192\postentry_closeout_v1`
- Final read-only process/GPU census: `FINAL_RESOURCE_CENSUS_V1.json`
- Hash inventory: `SHA256_INVENTORY_V1.json`


## Follow-up: full queue-controller ownership hard blocker

The requested Task Scheduler integration was evaluated against the current Coupling worktree without modifying it. The Coupling file `scripts/coupling_ml/k6_v2_pipeline/serial_queue.py` remains SHA256 `87ca459881e641ab5bf026767928bc09ec6470a4a0404d886331bddab4519966` at HEAD `bb4e105308cdb45e2a2df300cd08af3e01fdb920`; its worktree contains unrelated dirty/untracked work and was left unchanged. `--execute` traverses the full remaining queue (93 cases at the last authority snapshot) and synchronously starts `adapter.py run-one` (line 1337). It reconciles Runner state at startup (line 1434), but the existing `FAILED_PREENTRY` P05 fixture is rejected as `ENTERED_CASE_NEEDS_AUDIT:K6LDA1_DEV_D6_P05` (reconcile gate lines 949-951). Runner recovery evidence for P05 says `RECOVERED_FAILED_PREENTRY`, entry=false, invocations=0, replay=0, with 26 offline tests passing.

Therefore directly registering the current `--execute` entrypoint would not safely recover the current queue and could expose all 93 remaining cases when manually triggered. This turn is explicitly prohibited from changing Coupling files or starting a solver. No full-queue Scheduled Task was registered. The evidence-backed blocker is for the Coupling owner to version the P05 pre-entry state/reconciliation and expose a bounded/restartable queue-controller entrypoint. Task Scheduler can then launch that entire controller directly, while the independent Runner worker preserves an already submitted solver request and the restarted controller reconciles its immutable request.

Four new no-solver synthetic Runner lifecycle tests cover detached submit, controller exception with worker continuation and same-request stale-state reconciliation, stale pre-entry fail-closed handling, and duplicate submission. The combined focused Runner suite passes **43 tests**. These tests validate Runner request lifecycle only; they do not claim Coupling controller qualification.

## Historical Shared V3 provenance (read-only)

Historical artifacts inspected under `D:\apcd_runtime\global_fdtd_control_v3`: `PW_K6_SEED_DB_V1_controller.py` SHA256 `275ad826bb18a36cacc64d7510eee41e27c70f0e35ec9d8b136b732050c8e1af`; `close_failed_retry_no_replay_v1.py` SHA256 `5dc78ee75c0f15d9e07407be8f1e9f29c1d3721b94958dcc6a9ef5553178a028`; `reconcile_and_retry_s35_s39_v1.py` SHA256 `f416e95995de88340e1c6a094e638293044ff1fa063f6c84da0d45d4e71c7259`. The pre-canary task XMLs are disabled, use `InteractiveToken` and `IgnoreNew`, and have one-minute triggers. The zero-solver validation manifest SHA256 is `d9048e15ff4bb2486c064a3655ef643066318467f4a6fb473a57ddb842b4566`, generated `2026-09-29T04:09:29.5059117Z`, with 0 solver runs and 0 entries. Only atomic persistence and dead-process reconciliation principles are reused in V1; the V3 dispatch loop, retry/hold-release logic, triggers, allocator and multi-slot queue are not ported. Full hashes and findings are in the evidence JSON.
