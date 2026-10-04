# APCD GPU Runner V1 — unrecoverable queue21 lineage and controlled recovery

## STATUS

`PARTIAL — EXCEPTION DISPOSITION SAVED; OWNER DECISION AND HOLD RELEASE REQUIRED`

## HISTORICAL UNKNOWN / QUARANTINE

Queue21 `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001` retains original events 1499 and 1506. Their token hash and fencing generation match, but both metadata objects are empty and neither entry is tied to a process lineage or truth artifact. Physical solver-entry count remains **UNKNOWN**. Events and truth artifacts were not modified. The fixed-case quarantine excludes this identity and unresolved linked outputs from training, ranking, scientific conclusions, and formal truth handoff; no replacement attempt is allowed. No event-linked truth path was recovered, so the physical impact scope remains unknown.

The current DB snapshot is `D:\apcd_runtime\gpu_production_runner_v1\recovery\queue21_unrecoverable_lineage_20261004T113204Z`. Main DB SHA256: `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202` (size 1478656 bytes); snapshot copy equals live source at capture. The older DB binary with reported SHA `48c227694c67da29185884808c7b405c16a7d04684c1ec27f4ce3a9a32c212a0` was not recovered; that reported hash is retained as forensic history.

## CURRENT EXECUTION STATE

At `2026-10-04T11:33:31.858440+00:00`, GPU Runner V1 had 0 active scientific cases, no `.runner.lock` or `active_run.json`, and no `fdtd-engine-msmpi.exe`, Fluent worker, or `mpiexec` process. Eight long-lived `fdtd-solutions.exe -server -hide` API contexts were owned by `DESKTOP-NNE313K\DELL`, parented by Python metadata/FSP inventory contexts, with 0.031–0.062 s CPU growth over two seconds; they were left intact. One separate interactive `ansysedt.exe` was also present. RTX 3080 read 0% utilization and 2045/10240 MiB used; the desktop/EDT processes remain visible, so low GPU use alone is not treated as proof. Shared V3's three historical slots were FREE but are not used as Runner V1 capacity evidence.

The V1 registry held 12 terminal records (11 DONE, one retained S35 FAILED_POSTENTRY record). S35 has an existing zero-solver recovery_003 with `TRUTH_VALID`, one original invocation and zero replay; it is not active. Queue21 is absent from the V1 registry. V1 has filesystem lock/marker ownership rather than lease/fencing fields.

## SINGLE-SLOT PREVENTION VALIDATION

The Runner V1 source now blocks every attempt for the exact queue21 case before run-directory creation; requires a pre-entry guard at the production root; and uses a read-only fail-closed global hold guard in the official adapter. That guard checks the active boolean, generation, active global lifecycle holds, and revalidates contract/source/staged FSP hashes at the entry boundary. It does not allocate Shared V3 slots. Legacy token/fencing fields are rejected by the exact V1 manifest schema. The read-only hold snapshot is not a distributed lease/fence; the owner must serialize any hold changes with dispatch. Existing serial lock, duplicate rejection, post-entry replay prohibition, durable truth, fresh LOAD, truth-before-DONE and release barriers remain.

Validation: **85 passed, 42 subtests passed** over six offline test files. A separate read-only check against the live DB returned `GLOBAL_NEW_ENTRY_HOLD_ACTIVE` for the exact active hold at generation 26; DB SHA remained unchanged. All tests are synthetic or injected-callback tests; no FSP load or solver was run. See `VALIDATION_RESULTS_V1.json`.

## OWNER DISPOSITION / HOLD RELEASE

The active hold is `hold-4a6eab94af3b4a6d8510ba2fe32a5b66`, GLOBAL, generation 26, reason `SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`. The hold row names a containment call, not an authenticated person. The inspected permission matrix does not name a global hold owner. The previous generation-25 release was limited to S35/S39 and cannot be reused. The checked official API requires actor and authority hash but does not authenticate the signer, so no release API call was made.

`OWNER_DECISION_REQUEST.md` is the exact approval package request. The exception validator reports `release_authorized=false`; the DB, events, metric, generation and hold remain unchanged.

## DIAGNOSTIC / V2 AUTHORIZATION

`K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001` remains `solver_entry_authorized=false`, budget 0 in the pinned authority; its proposed future limit is at most one entry with zero replay, after approval and hold release. It was not run. All 160 V2 geometries remain setup-only with solver-authorized count 0; no confirmation response was read.

Coupling's consumer exclusion registry was not modified. `HANDOFF_TO_COUPLING.md` requires the data owner to ingest and verify the exact quarantine exclusion before any possible import. Until then, linked queue21 data remains blocked.

## EXECUTION COUNTS

Solver entries: **0**. FDTD runs: **0**. Post-entry replays: **0**.

## NEXT

Obtain and verify an authenticated decision from the designated global hold owner for the exact disposition hash and current hold generation. Only after the official hold release and a separate one-entry diagnostic authorization may a fresh FINAL_LAUNCH_REVALIDATION run. Do not execute queue21 or the diagnostic from this draft.

Continuation: `CONTINUATION.md`. Coupling handoff: `HANDOFF_TO_COUPLING.md`.
