# Shared V3 launch-generation revalidation

## Status

`SHARED_V3_LAUNCH_GENERATION_REVALIDATION_FIX_V1=IMPLEMENTED`

`SHARED_V3_ADMISSION_CONTROL_STABLE=NO`

The control-plane fix and zero-solver certification passed, but the single
real canary did not produce durable scientific truth. No further solver entry
is authorized from this state.

## Root cause and fix

The previous failure was a launch-boundary TOCTOU: an admission token could be
consumed after the authoritative control generation changed. The shared
allocator now performs the final revalidation inside the launch transaction,
immediately before the child-start callback. It requires branch enablement,
hold state, current generation equality, effective caps, owner fencing,
resource health, pre-entry attempt identity, and duplicate-entry exclusion.
Generation mismatch or any veto releases only the provisional reservation and
returns the case to WAIT; it never increments solver entry or replays an old
token. Admission and final-launch provenance are persisted for every accepted
launch.

The callback adapter was also corrected so both host-process and standalone
GPU-child entry paths accept the final-gate provenance boundary without
changing the child-start signature.

## Zero-solver evidence

`run_admission_gate_zero_solver_tests.py`: PASS, A--AF, 32/32,
`solver_invocations=0`, `scientific_solver_entries=0`, `replay=0`,
`direct_sqlite_mutations=0`.

The targeted launcher, GPU concurrency/autofill, and Coupling-ML integration
zero-solver suites also passed with zero solver invocations and zero scientific
entries. The final-launch gate is shared by dispatcher, autofill, wait-resource
wake, manual dispatch, and restart paths.

## Real canary evidence

The first control-script attempt touched S06--S11 only at the pre-entry
boundary. Each ended `FAILED_PREENTRY` with `solver_entered=false` because the
new callback adapter had the positional-argument defect recorded in its event
ledger. No scientific engine entered in those attempts.

The one real scientific canary was `K6V1_S12/attempt_001`:

- admission generation 6 = final launch generation 6;
- host child start `2026-09-24T12:10:12.836336Z`;
- `GPU_ENGINE_ENTRY_CONFIRMED` exactly once at
  `2026-09-24T12:10:20.224805Z`;
- one `fdtd-engine-msmpi.exe -gpu` process was observed on the RTX 3080;
- the solver log reached initialization and `Starting meshing`, then the
  process tree disappeared before return;
- no native FSP, H5, raw result, projection, or archive truth was produced;
- terminal state was `POSTENTRY_NO_TRUTH`, release was idempotent, and
  `replay=0`;
- hold was reasserted immediately after entry (`control_generation=7`), and
  S13--S16 remained `WAIT_RESOURCE_CAPACITY`.

The early solver exit is proven, but its deeper cause is not established by
the saved evidence; it must not be guessed as a license or physics failure.

## Authority boundary

S05 remains the previously validated scientific truth. S12 is quarantined and
must not be replayed. `attempt_005` is forbidden. Traditional was not touched;
`traditional_solver_entries=0` and `foreign_mutation_count=0` remain required.

Current flags:

- `REAL_PRODUCTION_GPU_TRUTH_PERSISTENCE_STABLE=YES` (prior S05 authority);
- `SHARED_V3_ADMISSION_CONTROL_STABLE=NO` (real canary not durable);
- `PW_K6_SEED_DB_V1_RESUME_AUTOFILL=NO`;
- `TRADITIONAL_GPU_ADOPTION_READY=NO`.

Evidence roots:

- `D:\apcd_runtime\global_fdtd_control_v3\cases\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_S12\attempt_001`
- `outputs/coupling_ml/PW_K6_SEED_DB_V1_PRODUCTION_V1/K6V1_S12/attempt_001`
