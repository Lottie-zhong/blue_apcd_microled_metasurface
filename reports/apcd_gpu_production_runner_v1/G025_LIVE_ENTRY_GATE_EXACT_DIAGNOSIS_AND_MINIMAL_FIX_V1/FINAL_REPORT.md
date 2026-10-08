# G025 LIVE_ENTRY_GATE diagnosis and minimal fix

Status: PASS for the zero-solver owner-gate repair and current live-gate check. The Coupling queue remains stopped; this report does not authorize or perform a controller start, case launch, or solver run.

## Root cause

The committed Runner owner probe returned busy for the exact historical case K6GDP2_DEV_G024 / attempt_001 / K6V2_G024_20261007T123943Z_713590ad. Its status is FAILED_POSTENTRY, has one recorded solver invocation, and lacks solver_process_lineage. The generic fail-closed branch treated this terminal record as an active owner even though its formal closeout says CLOSED / FAILED_POSTENTRY_NO_TRUTH, one entry, zero replay, and runner slot closed.

The original controller exception was not saved. The on-disk interruption evidence has exact_original_exception=null. Replaying the committed pre-fix serial_queue.entry_gate as a pure function under the pinned Python 3.10.20 environment reproduced StopQueue:RUNNER_SLOT_OR_LOCK_NOT_FREE at the owner check. The saved generation-2 interruption evidence records last_persisted_phase=LIVE_ENTRY_GATE; the operator-reported phase was LIVE_ENTRY_GATE. The original exception remains unknown.

## Repair and verification

The Runner now recognizes only the exact G024 case, attempt, run ID, status SHA, closeout receipt SHA, verification SHA, terminal result, zero-replay/resource-release evidence, and matching registry row. It does not add lineage, edit the old status/registry, or weaken handling for other missing-lineage or active owners.

Four focused tests passed under N:/anaconda_envs/RCP_LCP/python.exe 3.10.20, including valid G024 closeout, failed slot-release evidence, active lock, and generic missing/ambiguous lineage. Python compilation passed.

The current Coupling serial_queue.entry_gate returned PASS at 2026-10-08 13:39:12 UTC: owner busy=false, active-run absent, lock absent, control generation 27 with hold=0, and GPU free memory 8076 MiB against a 1369 MiB minimum. The current engine-process filter found no fdtd-engine-msmpi.exe. Solver entries, FDTD runs, and automatic replays in this task were all zero.

## Coupling handoff and version binding

The Coupling controller remains STOPPED_RECONCILED for request bb93248ca2dff9605d7885554a319394; it has no runner request IDs or unresolved requests. Queue counts remain 36 entered / 33 truth-valid / 33 labels-valid / 92 unentered.

The controller manifest binds the Coupling controller script and queue manifest, not adapter.py. G025's existing setup-preflight result records adapter SHA 8860254b701fe2461def30644158117bf211b826f1d3adf3e5919c02c48c550a, which was the committed pre-fix file. This patch changes only owner-probe classification; setup contract and validator code did not change. A future Runner request will capture the current adapter SHA 7f28045aa8e0178ce22e44c4377d02515431f4577fb8f1dbd578f58149b50173 at request creation and use the current start-time revalidation. No Coupling binding or queue file was changed in this task.

## Evidence

Structured diagnosis and gate evidence: DIAGNOSTIC_EVIDENCE_V1.json (SHA256 d7362fa427924d2a4c306fc0f78e02d21d814e4d2e4f807d6868cdc17c45667a).

Base Runner HEAD: dc38d0bc7efebabbfbf1a321becd06c9345d3772 on branch codex/apcd-gpu-production-runner-v1. Solver execution was not performed.
