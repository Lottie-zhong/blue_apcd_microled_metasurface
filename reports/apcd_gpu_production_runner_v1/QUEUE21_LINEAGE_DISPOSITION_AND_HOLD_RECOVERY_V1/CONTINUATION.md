# CONTINUATION — queue21 lineage and hold recovery

- Queue21 disposition: `LINEAGE_NOT_RECOVERABLE` (C); report JSON SHA256 `97527da4693056941cc1019a026ce4c1485400535227ff00b9c3e470f925fcef`.
- Refreshed read-only Shared V3 DB SHA256: `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`; raw events remain untouched.
- Active hold: `hold-4a6eab94af3b4a6d8510ba2fe32a5b66`, generation `26`; no release authority.
- Runner V1 code path is filesystem-authoritative and shows no direct Shared V3 DB dependency. No formal migration authority is present in the V1 authority JSON. Do not claim the old hold is released.
- Prevention suite: 59 passed, 38 subtests passed; offline only.
- No solver entry, FDTD run, replay, DB mutation, or truth mutation.
- Next minimal step: a formally authorized owner retrieves original process-start/launcher/engine and FSP/H5/truth/fresh-LOAD lineage for events 1499 and 1506. If unavailable, retain C and the hold.
- No V1 code change, Shared V3 ledger rebuild, owner/fence edit, attempt reset, or process termination was performed.


## 2026-10-04 closeout refresh — APCD_GPU_RUNNER_HOLD_CLOSEOUT_AND_DIAG_PREFLIGHT_REFRESH_V1

- Re-read live queue21 evidence and the production control snapshot. Events `1499` and `1506` remain two `SCIENTIFIC_SOLVER_ENTERED` records for `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`, with fencing generation `14`, the same lease token, empty process metadata, and timestamps `2026-09-23T00:39:11.269437+00:00` / `2026-09-23T02:38:41.983302+00:00`. The physical launch count remains **undetermined**: no event-linked process creation/engine/GPU lineage or paired FSP/H5/truth/fresh-LOAD evidence was recovered. Preserve disposition `C_EVIDENCE_INSUFFICIENT_LINEAGE_NOT_RECOVERABLE`; do not rebuild or edit counts.
- Current DB SHA256 remains `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`; hold `hold-4a6eab94af3b4a6d8510ba2fe32a5b66` remains `ACTIVE`, global generation `26`, reason `SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`, with no `released_by`, release timestamp, or release authority hash. No current-generation release owner/authority is present. The V1 filesystem-authoritative route has no direct Shared V3 DB read in its pinned code, but the hold explicitly links the unresolved queue21 incident; absent formal migration/release authority, this does not authorize bypass. No release API or DB write was performed.
- Existing offline prevention evidence remains `59 passed` plus `38 subtests passed`; this closeout made no Runner runtime-code change. Physical entry count cannot be concluded from those tests.
- Remaining minimum evidence: authorized owner must locate original launcher/controller/process-start/engine/GPU evidence and map it to each event, or locate event-linked archived FSP/H5, durable truth hashes, completion and fresh-LOAD proof. If the original lineage is unavailable, keep disposition C and hold active; do not use a new run to infer the old count.
- This closeout run: solver entries `0`, FDTD runs `0`, replays `0`; no DB, event, owner/fence, attempt, or truth mutation.
