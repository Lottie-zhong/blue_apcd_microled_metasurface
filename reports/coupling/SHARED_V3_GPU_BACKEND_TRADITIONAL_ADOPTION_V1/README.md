# SHARED_V3_GPU_BACKEND_TRADITIONAL_ADOPTION_V1

Read-only adoption package for the validated shared GPU backend.

## Scope

This package documents the reusable path for Traditional adoption. It does
not mutate Traditional code, queue, registry, scientific state, or scheduler,
and it does not run a Traditional scientific solver.

The logical contract is `GLOBAL_CAP=3`, `TRADITIONAL_CAP=1`, and
`COUPLING_ML_CAP=2`. The physical GPU semaphore is independent of logical
slot identity. Physical cap 3 is only a measured candidate and remains
`PENDING_CHART_REVIEW` for production.

## Adoption boundary

Traditional may use the shared resolver and GPU capacity lease only after a
separate technical-lead review. The branch must supply its own branch, case,
attempt, slot, fencing generation, and lease token. Owner-scoped heartbeat,
release, post-solver persistence, durable-truth completion, and idempotent
release are mandatory. A foreign branch must receive an ownership error and
must not mutate the lease.

The current adoption state is `BLOCKED_REAL_CANARY_NO_DURABLE_TRUTH`. The
shared V3 launch path now requires final launch-generation revalidation, but
the current real K6 canary ended `POSTENTRY_NO_TRUTH`; Traditional remains
not production-ready. No Traditional solver entry was made by this task.

## Included authority

- `scripts/shared_fdtd/control_v3/gpu_capacity.py`
- `scripts/shared_fdtd/control_v3/allocator.py`
- `scripts/shared_fdtd/control_v3/resources.py`
- `scripts/shared_fdtd/control_v3/schema.sql`
- `scripts/shared_fdtd/engine/dispatcher.py`
- `scripts/shared_fdtd/tests/run_gpu_concurrency_autofill_zero_solver_tests.py`
- `scripts/shared_fdtd/tests/run_gpu_autofill_sandbox_zero_solver.py`

The exact SHA256 values are in `SOURCE_MANIFEST.json` beside this document.

## Do not do

- Do not bind logical slot numbers to GPU device numbers.
- Do not write the other branch's queue, registry, or scientific outputs.
- Do not infer solver entry from launch intent alone.
- Do not release a token before native truth, H5, archive, and terminal
  evidence are durable.
- Do not enqueue PW_K6 remaining geometries from this package.
