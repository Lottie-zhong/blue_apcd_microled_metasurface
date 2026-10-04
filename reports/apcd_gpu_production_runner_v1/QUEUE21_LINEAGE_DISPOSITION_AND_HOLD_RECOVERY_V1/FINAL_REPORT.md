# Queue21 lineage disposition and hold recovery V1

**Status:** `PARTIAL_HOLD_REMAINS_ACTIVE`
**Classification:** `LINEAGE_NOT_RECOVERABLE` (C: evidence insufficient)

## Finding

Traditional queue21 is `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1` / `attempt_001`. The durable ledger contains **two** `SCIENTIFIC_SOLVER_ENTERED` records (events 1499 and 1506), both under the same lease-token hash and fencing generation 14. Both entry `metadata_json` objects are empty. The physical number of solver launches therefore remains **unknown**: neither a duplicate event write nor two separate launches can be ruled out. The `SCIENTIFIC_VALID` terminal and `RELEASED` row have no truth paths or hashes in the queue payload.

Fresh read-only audit of the current database found SHA256 `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202` (1,478,656 bytes). It reconfirmed the queue row and the five case events (1498, 1499, 1506, 1507, 1508). The earlier forensic report `12cff822935ca852daeebb3b06073fbbeedb9a5fbc2d39ab67e04a617b2375eb` used the older DB snapshot SHA256 `48c227694c67da29185884808c7b405c16a7d04684c1ec27f4ce3a9a32c212a0`; its C classification remains consistent with the refreshed rows. The full extracted rows and hold lifecycle are in `QUEUE21_LINEAGE_DISPOSITION_V1.json`.

## Hold and Runner boundary

The Shared V3 hold `hold-4a6eab94af3b4a6d8510ba2fe32a5b66` remains **ACTIVE**, generation `26`, reason `SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`. It was set after S35 pre-entry denial due to the unresolved queue21 duplicate-entry metric. No `released_by` or `release_authority_hash` exists for this hold. The earlier generation-25 release was scoped to S35/S39 and is not authority for generation 26. No hold API was called and the production DB was not written.

The current Runner V1 code/doc path uses `D:\apcd_runtime\gpu_production_runner_v1`, an exclusive filesystem root and registry; no direct Shared V3 DB/queue dependency was found. However, V1 authority `migration_authority`, `control_plane_migration`, `control_database`, and `hold_policy` are null. This proves technical separation in the inspected V1 path, but does not provide a formal migration or release authority to close the historical V3 hold. Preserve that hold as historical containment; do not claim it was released or silently bypassed.

Runner V1 runtime has 12 registered runs, queue21 absent, no active-run marker and no lock file. Its status counts and hashes are in the JSON evidence. Current read-only resource snapshot found eight `fdtd-solutions.exe -server -hide` API processes owned by `DESKTOP-NNE313K\DELL`, each with 15.7–17.0 MB working set and Python parents running prior-FSP inventory/result-metadata scripts or stdin contexts. No `fdtd-engine-msmpi.exe` was present; RTX 3080 utilization was 0%, with 8007 MiB free and no FDTD process in the GPU compute-app list. No process was killed or adopted. This live snapshot does not establish queue21's historical launch count.

## Prevention and remaining gap

Current Runner V1 has a root-wide exclusive lock/active marker, duplicate run-ID and manifest checks, a durable-entry guard, post-entry replay prohibition, and adapter process-lineage checks. Focused offline regression: **59 passed, 38 subtests passed**. This supports current V1 single-slot protection; it does not repair or explain the older V3 duplicate records. The trigger path for events 1499/1506 is not recoverable from current evidence.

The production hold and raw events remain unchanged. No code change or ledger rebuild is justified without evidence and formal owner authority. Physical launch count: **unknown**.

## Execution and next action

Solver entries: **0**; FDTD runs: **0**; replays: **0**; production database mutations: **0**; truth mutations: **0**.

Next, a formally authorized owner must retrieve original launcher/controller/process-start and solver artifacts for both timestamps, match process creation identity and FSP/H5/truth hashes, and then either adjudicate with evidence or preserve C. If the source records no longer exist, keep the containment hold; do not replay or delete events.
