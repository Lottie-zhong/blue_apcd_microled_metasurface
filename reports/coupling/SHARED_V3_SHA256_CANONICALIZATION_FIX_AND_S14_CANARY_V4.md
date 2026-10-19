# SHARED_V3_SHA256_CANONICALIZATION_FIX_AND_S14_CANARY_V4

## STATUS

`BLOCKED_PREENTRY`

The SHA256 canonicalization fix and all zero-solver gates passed. The single authorized S14 attempt003 did not reach scientific solver entry. It was blocked at final launch revalidation after the one-shot gate was reclosed. No attempt004 was created and no replay occurred.

## SHA ROOT CAUSE

`K6V1_S14/attempt_002` failed before solver entry because the manifest stored the correct SHA256 digest in uppercase while the ledger stored the same digest in lowercase, and the old pre-FSP guard compared raw strings case-sensitively. The two strings represented the same 256-bit digest.

## SHA FIX

Added the strict SHA256-specific path in `scripts/shared_fdtd/engine/persistence.py`:

- exactly 64 hexadecimal characters;
- case-insensitive hexadecimal semantics with lowercase canonical comparison;
- rejection of missing, null, wrong-length, non-hex, prefixed/suffixed, and whitespace-padded values;
- original raw strings remain unchanged in provenance and stored artifacts.

Shared validation now uses the helper in persistence, GPU native-bundle validation, and V3 host FSP/archive comparisons. Scientific payloads and historical hashes were not rewritten.

The later async-host stale-reference fix in `scripts/shared_fdtd/tools/v3_g2_host.py` makes `WAIT_RESOURCE_CAPACITY` clear queue slot/lease/fencing references after the allocator has released the provisional owner. A regression test was added; the existing attempt003 runtime row was not mutated.

## ZERO-SOLVER TESTS

All listed suites passed with zero solver invocations and zero scientific solver entries:

- global: 20/20 PASS;
- branch: 20/20 PASS;
- chaos: 12/12 PASS;
- production integration: PASS, including `async_host_wait_clears_released_refs`;
- admission gate: 32/32 PASS;
- SHA canonicalization A-M: PASS;
- preentry recovery: 16/16 PASS;
- backend mutex: 7/7 PASS;
- GPU engine observability: 11/11 PASS;
- GPU native bundle: all checks PASS;
- persistence: PASS;
- external watcher: PASS;
- GPU concurrency/autofill, resource resolution, truth schema, completion barrier, launcher, PW complex-state, K6 manifest, monitor/reference roles, runtime supervision, and resource-aware suites: PASS.

Aggregate evidence: `solver_invocations=0`, `scientific_solver_entries=0`, `replays=0` in the executed zero-solver paths.

## ATTEMPT_002 AUDIT

`K6V1_S14/attempt_002` remains `FAILED_PREENTRY` with:

- solver entry: 0;
- GPU engine entry confirmation: 0;
- run invocation count: 0;
- replay: false;
- no native FSP, H5, raw truth, archive, or terminal truth;
- owner/lease/slot released;
- one unique zero-solver recovery event; repeated recovery is idempotent.

It was not reopened or modified.

## ATTEMPT_003 PREENTRY

Fresh `K6V1_S14/attempt_003` was created from the frozen setup and admitted only through the Shared V3 path. Dispatch selected exactly `K6V1_S14`; S15/S16 were not admitted.

Observed sequence:

1. `LEASE_ACQUIRED`;
2. `FINAL_ADMISSION_PASS`;
3. `FINAL_LAUNCH_REVALIDATION_PASS`;
4. `CHILD_PROCESS_STARTED`;
5. `SOLVER_ENTRY_INTENT`;
6. gate reclose caused `FINAL_LAUNCH_REVALIDATION_BLOCKED` with `NEW_ENTRY_HOLD` and `OWNER_FENCING_OR_RESERVATION_INVALID`;
7. no scientific invocation occurred.

Current evidence:

- queue state: `WAIT_RESOURCE_CAPACITY`;
- actual slot state: `GLOBAL_SLOT_2 = FREE`;
- current queue row still contains stale slot/lease/fencing references;
- `recover_failed_preentry` returns `NOT_ELIGIBLE` because the queue state is already `WAIT_RESOURCE_CAPACITY`;
- no attempt004 was created;
- no replay was performed.

## REAL SOLVER LIFECYCLE

No real solver lifecycle occurred for attempt003:

- `GPU_ENGINE_ENTRY_CONFIRMED=0`;
- `SCIENTIFIC_SOLVER_ENTERED=0`;
- `SCIENTIFIC_SOLVER_RUNNING=0`;
- `SOLVER_RETURNED=0`;
- no solver process lineage or scientific truth bundle was produced.

## WATCHER / GPU EVIDENCE

The durable watcher and GPU telemetry were alive and heartbeats advanced before the one-shot gate. Recorded source/manifest hashes:

- watcher source: `37D83CDFEA971F09D9601E2B61FF5A2828146DEB8D4329DE2CF544D1999F9AB9`;
- telemetry source: `FD1B918EC6C1F5AA3C5522287CDE083281729DA93F444F8BB60307F809B79BEB`;
- watcher manifest: `9A26E50D9054CF432029AE068BCD91BEC4EF1E0219DAF6545F8E27D924B0079B9`.

Both observers were stopped using the exact stop flag after the preentry block. No solver-entry signature was observed.

## TRUTH BUNDLE

Absent for attempt003: no runtime FSP, native FSP, H5, raw result, HF archive, terminal truth, or fresh LOAD-only validation.

## CONTROL SAFETY

| Item | Count / state |
|---|---:|
| attempt001 scientific entries | 0 |
| attempt002 scientific entries | 0 |
| attempt003 scientific entries | 0 |
| new GPU engine entry confirmations | 0 |
| S12 replay | 0 |
| S13 replay | 0 |
| S15 entries | 0 |
| S16 entries | 0 |
| attempt004 count | 0 |
| S14 duplicate scientific-entry count | 0 |
| foreign mutation count | 0 |
| `new_entry_hold` | TRUE |
| autofill | DISABLED |

A read-only global history query shows one older duplicate scientific-entry group on the untouched Traditional case `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1/attempt_001`; this is outside the S14 canary scope and was not modified.

## GIT / CHANGED FILES

- branch: `work/mdc-np-coupling-ml-v1`;
- HEAD: `7d844158e2318a56b7d34eb01c26d3da45b98822`;
- working tree: dirty with pre-existing and current shared-V3 changes;
- no commit;
- no push.

Relevant current changes are in `scripts/shared_fdtd/engine/persistence.py`, `scripts/shared_fdtd/engine/gpu_bundle.py`, `scripts/shared_fdtd/tools/v3_g2_host.py`, `scripts/shared_fdtd/tests/run_sha256_canonicalization_zero_solver_tests.py`, and `scripts/shared_fdtd/tests/run_coupling_ml_integration_zero_solver_tests.py`. Existing unrelated dirty/untracked files were preserved. `git diff --check` reports only an existing blank-line-at-EOF warning in `scripts/shared_fdtd/engine/host_lifecycle.py`.

## NEXT

Do not execute: chart review of a fenced Shared recovery/reconcile API for a `WAIT_RESOURCE_CAPACITY` row whose owner is already free, followed by a separately authorized canary decision. No attempt004, replay, S15/S16 launch, or autofill is authorized by this report.
