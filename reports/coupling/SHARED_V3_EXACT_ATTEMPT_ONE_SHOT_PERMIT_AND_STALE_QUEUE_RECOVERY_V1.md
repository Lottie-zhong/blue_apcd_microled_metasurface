# SHARED_V3_EXACT_ATTEMPT_ONE_SHOT_PERMIT_AND_STALE_QUEUE_RECOVERY_V1

## STATUS

BLOCKED_AFTER_ENTRY_CONTROL_PLANE_CONFLICT

This task is closed without a new solver launch. The single authorized scientific entry was consumed exactly once, but the control plane terminalized and released the lease before the detached host completed. The later native truth is preserved, but the completion persistence path failed with an ownership mismatch. No production certification is issued.

## Scope and safety boundary

- Remote host: DESKTOP-NNE313K, user dell, NetBird SSH transport.
- Branch: work/mdc-np-coupling-ml-v1.
- Global new-entry hold remained TRUE.
- Temporary runtime cap remained 1; control generation 15; health PASS.
- No attempt_005, no replay, no S15/S16 launch, no autofill, no Traditional mutation.
- FOREIGN_MUTATION_COUNT=0.
- DUPLICATE_SCIENTIFIC_ENTRY_COUNT=0 for this task scope; historical Traditional records were not modified.

## Stale pre-entry recovery

K6V1_S14/attempt_003 was proven zero-solver:

- solver_entered=false
- solver_returned=false
- run_invocation_count=0
- replay=false
- no native/raw/H5/terminal truth
- the runtime FSP was setup-only and matched the declared setup SHA.

Shared API recovery returned RECOVERED_STALE_PREENTRY; the queue became FAILED_PREENTRY, references were cleared, and no solver entry or replay was created.

## Exact one-shot permit

The permit was armed and consumed through the Shared API:

- permit: R1v7kBxQW5Th6y3qDfkodVRb7AL3TI7U
- authorization/control generation: 15
- case/attempt scope: K6V1_S14/attempt_004
- hold at admission and final launch: TRUE
- final launch revalidation: PASS
- permit consumption: exactly one
- attempt ledger: solver_entered=true, solver_returned=true, run_invocation_count=1, replay=false
- S15 and S16 remained WAIT_RESOURCE_CAPACITY.

## Zero-solver verification

Final reruns completed before the real entry:

- Python compile check: PASS
- global zero-solver suite: 20/20 PASS
- branch suite: 20/20 PASS
- chaos suite: 12/12 PASS
- pre-entry recovery suite: 16/16 PASS
- Coupling-ML integration zero-solver suite: PASS; solver_runs=0, scientific entries=0, replays=0, foreign mutations=0
- exact-permit zero-solver suite: 14/14 PASS; solver_invocations=0, scientific entries=0

## Authorized real entry

K6V1_S14/attempt_004 was the only fresh scientific entry.

Evidence:

- GPU_ENGINE_ENTRY_CONFIRMED
- SCIENTIFIC_SOLVER_ENTERED
- SCIENTIFIC_SOLVER_RUNNING
- MPI process evidence recorded 12 engine lineage processes with one solver rank/thread configuration.
- entry timestamp: 2026-09-25T02:27:14.957627+00:00 UTC
- solver return event: 2026-09-25T02:36:34.315218+00:00 UTC
- solver log: simulation completed successfully
- wall time: 533.692104 s
- FDTD run time: 524.417202 s
- peak memory: 1.388089 GiB
- solver speed: 4773.115731 Mnodes/s
- observed GPU samples were approximately 80–84% utilization and 1682 MiB VRAM.

## Control-plane race

At 2026-09-25T02:28:08.553845 UTC, while the host/solver lineage was still alive, the reconciler wrote:

- terminal.json.status=POSTENTRY_NO_TRUTH
- truth_durable=false
- POSTENTRY_NO_TRUTH_RELEASED
- lease release for GLOBAL_SLOT_2
- released GPU capacity: 1.

This release occurred before solver return. The engine and MPI children later disappeared naturally, the host then returned, and postprocessing continued. The stale terminal file was not rewritten to reflect the later evidence.

## Truth artifacts produced after the premature terminalization

The following artifacts were produced and validated after solver return:

- native bundle: FSP SHA256 20bbf75e8be30bcbd06d6389f02e0294e09a7d204b9df7af194b26cef54244ee
- native H5 SHA256 ea20f121640054d3e2ecbfc43b3e95ebc97cef95b837162e6e041b7c127b8a36
- NATIVE_TRUTH_DURABLE
- NATIVE_TRUTH_LOAD_ONLY_VALIDATED
- post FSP valid, same FSP SHA
- raw JSON valid, SHA256 3e6a1ce481f01bcd7c8f67ca8368a5f94d089622b753a48145de07e14793e8ed
- SCIENTIFIC_VALID
- projection, complex fields, state and orders artifacts present
- HF_ARCHIVED
- HF_ARCHIVE_MANIFEST.json.status=PASS.

The terminal and queue states remain authoritative for control safety, not for declaring a clean production completion:

- queue: AMBIGUOUS_QUARANTINED
- slot 2: FREE, generation 47
- no attempt process remains
- S15/S16: WAIT_RESOURCE_CAPACITY.

## Failure classification

This is not evidence of a solver numerical failure. It is a control-plane ordering/fencing failure:

1. an asynchronous reconciler observed no truth yet;
2. it terminalized the post-entry attempt and released the lease while the host/solver was still alive;
3. the solver returned and produced native/post/raw/projection/archive truth;
4. completion persistence attempted to use the old owner and received OwnershipMismatch(GLOBAL_SLOT_2);
5. the queue was quarantined as AMBIGUOUS_QUARANTINED and CONTROL_PLANE_DEGRADED was emitted.

The durable scientific files are retained. They are not promoted to clean production authority because the terminal/release provenance is internally inconsistent.

## Required next route

Freeze this attempt and perform a zero-solver forensic fix of reconciler ordering and lease-release fencing. The fix must prevent post-entry POSTENTRY_NO_TRUTH release while the host/solver lineage or completion callback can still be live, and must preserve late truth without ownership ambiguity. Re-run zero-solver regression tests before any future scientific entry.

Do not create attempt_005, replay this attempt, release the quarantined queue by hand, or start S15/S16.
