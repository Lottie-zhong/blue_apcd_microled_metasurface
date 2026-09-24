# SHARED_V3_GPU_CONCURRENCY_AND_AUTOFILL_HARDENING_V1

Date: 2026-09-24
Branch: `work/mdc-np-coupling-ml-v1`
Pre-change HEAD: `6e5e7110072557cb6a66f79bd7b4f22d1369a249`

## Decision boundary

This task separates logical V3 slots from the physical GPU backend. It does
not start PW_K6 production geometries, mutate Traditional scientific state,
train ML, or change the 5 nm scientific admission. The benchmark is a short,
non-production backend benchmark made from the admitted 5 nm setup with only
the FDTD simulation time reduced to `5e-15 s`.

## Logical and physical capacity

| Contract | Value |
|---|---:|
| GLOBAL_CAP | 3 |
| TRADITIONAL_CAP | 1 |
| COUPLING_ML_CAP | 2 |
| Physical device | 1 x RTX 3080 |
| Measured physical candidate | 3 |
| Production cap | `PENDING_CHART_REVIEW` |

The implementation keeps logical slots and GPU capacity leases separate. A
GPU lease is keyed by branch, case, attempt, slot, fencing generation, and a
hashed lease token. Admission waits when the physical semaphore is full;
release is owner-scoped and idempotent. A waiting case is rediscovered by a
dispatcher tick after a local release, without replaying a solver entry.

## Non-production GPU benchmark

Base setup: the admitted setup FSP
`outputs/coupling_ml/W2H_15294_5NM_GPU_PRODUCTION_SCHEMA_V3/attempt_001/setup/runtime.fsp`
with SHA256
`36e5011b5e5c67a41e28dba296575356e6d7cefbbb1b4dd5e20ed0bfbffc08a5`.

| Concurrent jobs | Return | Engine census | Runtime/job | Iterations/job | GPU util max | VRAM max | Power max | LOAD-only | Archive/restore | Validity |
|---:|---|---:|---:|---:|---:|---:|---:|---|---|---|
| 1 | 0 | 1 | 24.77 s | 525 | 82% | 1832 MiB | 186.34 W | PASS | PASS, 6/6 SHA equal | PASS |
| 2 | 0, 0 | 2 | 27.89–27.96 s | 525 | 98% | 2677 MiB | 247.55 W | 2/2 PASS | 2/2 PASS, 6/6 SHA equal | PASS |
| 3 | 0, 0, 0 | 3 | 32.82–32.95 s | 525 | 99% | 3534 MiB | 248.45 W | 3/3 PASS | 3/3 PASS, 6/6 SHA equal | PASS |

Every benchmark job had exactly one controller launch, one observed engine
entry, and zero replay. The 2-way and 3-way runs had simultaneous engine
census evidence. The benchmark outputs are retained on the remote host under:

`D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\GPU_CONCURRENCY_REPRESENTATIVE_BENCH_V1`

These measurements establish a stable measured candidate of 3 for Chart
review; they do not by themselves promote the production cap or alter
scientific admission.

## Autofill sandbox

The isolated zero-solver sandbox used the exact names `T_BENCH_1`,
`T_BENCH_2`, `M_BENCH_1`, `M_BENCH_2`, and `M_BENCH_3`. It passed with launch
order:

`T_BENCH_1 -> M_BENCH_1 -> M_BENCH_2 -> M_BENCH_3 -> T_BENCH_2`

This proves:

- Traditional remains capped at one;
- Coupling-ML holds two and refills its own slot after `M_BENCH_1` release;
- Traditional refills after `T_BENCH_1` release while ML remains active;
- repeated ticks do not duplicate ownership or entry;
- scientific solver entries and invocations are zero in the sandbox.

Sandbox result: `PASS`, `scientific_solver_entries=0`,
`direct_sqlite_mutations=0`.

## Zero-solver regression gates

All required gates passed after the shared capacity changes:

- GPU capacity/autofill A–R: PASS, solver invocations 0, scientific entries 0;
- GPU autofill named sandbox: PASS, solver invocations 0;
- global zero-solver: 20/20 PASS;
- branch engine zero-solver: 20/20 PASS;
- chaos zero-solver: 12/12 PASS;
- resource-aware: 9/9 PASS;
- backend mutex: 7/7 PASS;
- entered-exception isolation: 16/16 PASS;
- completion barrier: 15/15 PASS;
- GPU resource resolution: all checks PASS;
- GPU truth schema: all checks PASS;
- persistence, launcher, monitor-role, MON_IN, pre-entry, and Floquet gates: PASS.

## Production and branch safety

The admitted production seed remains unchanged:

- `PW_K6_SEED_DB_V1`: `valid_G=1`, `target_G=20`;
- `queued_scientific_entries=0`;
- `active_scientific_entries=0`;
- remaining 19 geometries were not enqueued;
- production scientific entry count for this task: 0;
- Traditional scientific solver was not run or modified.

The shared adoption package is read-only and contains the resolver, capacity
lease, allocator, dispatcher, schema, regression-test, and boundary notes for
future Traditional adoption. It does not change Traditional source or queue
state.

## Remaining gate

`GPU_PHYSICAL_CONCURRENCY_CAP=3` is measured and technically valid for this
short backend benchmark. The production value remains
`PENDING_CHART_REVIEW`; no production autofill has been enabled by this
report.
