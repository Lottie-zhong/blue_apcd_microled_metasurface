# Auto-refill runtime and PW pre-entry boundary

## STATUS

AUTO_REFILL_RUNTIME_READY

## Verdict

PW_REAL_CANARY_READY_FOR_CHART_REVIEW

Zero-solver validation only. No solver was launched, no scientific solver entry occurred, no replay occurred, no attempt_003 was created, and Traditional was not modified.

## Canonical identity

- branch: work/mdc-np-coupling-ml-v1
- case: PW_PLANAR_STACK_REAL_CANARY
- attempt: attempt_002
- canonical queue rows: 1
- current queue: WAIT_RESOURCE_CAPACITY with null slot, lease token, and fencing generation
- reservation: one row, RELEASED, GLOBAL_SLOT_2

## Root cause fixed

The old scheduler/wrapper path was stuck under Task Scheduler and depended on an unavailable N: mapping. Nested per-case schtasks launch, the Windows task command-length limit, same-attempt reservation insertion, child process census, and stale-boundary acceptance were additional blockers.

The runtime now uses a one-minute transient pythonw dispatcher tick, native Windows process census, native CreateProcessW for the host shim, released-reservation reuse, WAIT-state cleanup, zero-solver recovery guards, and fresh fencing/mtime-validated pre-entry boundary evidence.

## Tests

- global: 20/20 PASS
- branch: 20/20 PASS
- chaos: 12/12 PASS
- coupling-ML integration: 9/9 PASS
- resource-aware: 9/9 PASS
- persistence: PASS
- PW launcher A-L: PASS
- medium PW pre-entry: 8/8 PASS
- durable post-solver finisher: 20/20 PASS
- entered-exception isolation: 16/16 PASS
- Python compile: PASS
- solver runs / scientific entries / replays: 0 / 0 / 0
- foreign mutation count: 0

## Real production runtime proof

The formal APCD_V3_COUPLING_DISPATCHER scheduled-task action was invoked once as a controlled validation tick. It ran the production dispatcher service, passed resource admission, reacquired the canonical attempt_002, started the native host process, and reached:

- PREENTRY_BOUNDARY_REACHED
- solver_entered=false
- scientific_solver_entry_count=0
- run_invocation_count=0
- fencing generation 20
- slot GLOBAL_SLOT_2

The lease was released as FAILED_PREENTRY, the queue returned to WAIT_RESOURCE_CAPACITY, and all global slots were free. The task returned 0; no generated per-case task remained. The scheduled tasks were disabled after proof because the zero-solver hard gate remains active.

## Answers

1. Auto-refill previously failed because the old scheduled wrapper did not progress reliably and carried the mapping, child-launch, command-length, reservation, census, and stale-boundary defects.
2. A one-minute APCD_V3_COUPLING_DISPATCHER task now wakes the transient pythonw dispatcher service; each tick rechecks WAIT cases.
3. Controller restart: PASS; the same attempt survives DB reopen with no duplicate scientific entry.
4. One freed slot: PASS; multislot_autorefill admits the next waiting case.
5. The sole current canonical attempt is attempt_002; no attempt_003 exists.
6. Yes: the formal production scheduled-task path reached the real pre-entry boundary automatically, without a manual per-case launch and without solver invocation.
7. AUTO_REFILL_RUNTIME_READY is justified for chart review of the zero-solver runtime gate. Scientific solver entry is still blocked and needs separate authorization.

## Git

- source parent: f037cabbae6df9a9365dd75ed9bef247ff4af97d
- source commit: 280aff2792b4dbbc351fc0e810a3e0dc787899ec
- push: NOT_PUSHED
- the unrelated pre-existing dirty scripts/shared_fdtd/engine/host_lifecycle.py and other pre-existing untracked artifacts were preserved and not staged.
