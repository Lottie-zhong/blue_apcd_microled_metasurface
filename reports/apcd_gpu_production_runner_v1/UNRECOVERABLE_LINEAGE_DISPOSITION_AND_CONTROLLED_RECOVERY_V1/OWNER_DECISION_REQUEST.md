# Owner decision request: queue21 unrecoverable lineage

**Status:** Awaiting the authenticated owner. This is a request, not an approval or release authority.

## Fixed incident

- Traditional case: `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`.
- Entry rows: 1499 and 1506, same lease-token hash and fencing generation 14; both have empty metadata.
- Physical solver-entry count: **UNKNOWN**. No event-linked process lineage or durable truth path/hash was recovered.
- Exception disposition: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\UNRECOVERABLE_LINEAGE_DISPOSITION_AND_CONTROLLED_RECOVERY_V1\EXCEPTION_DISPOSITION_V1.json` (SHA256 `5e2ba9d6de8c94e2f4fe0af89ba9fc7b5a523763d35b863e083888f3f06c5065`).
- Quarantine manifest: `D:\project\worktrees\blue_apcd_gpu_production_runner_v1\reports\apcd_gpu_production_runner_v1\UNRECOVERABLE_LINEAGE_DISPOSITION_AND_CONTROLLED_RECOVERY_V1\QUARANTINE_MANIFEST_V1.json` (SHA256 `f5c058bea0a38c8e900d8019b6fb33e4a34d450411980765598007bc1b9d6cbf`).
- Applicable hold: `hold-4a6eab94af3b4a6d8510ba2fe32a5b66`, GLOBAL, ACTIVE, generation 26; live DB SHA256 `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`.

## Evidence and authority boundary

The prior release authority SHA `b511106445fbba220779824d8f19fa4472ce6f9ff43067916a11e8fc1c77d865` was scoped to S35/S39 attempt_001 and is not reusable for this hold. The inspected permission matrix `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\shared_infra\APCD_GLOBAL_FDTD_PRODUCTION_PLATFORM_V1\OWNER_PERMISSION_MATRIX.md` (SHA256 `ed5ebf416804eb1209a759ac18be4e7a06db22135d15378c3d461508c722b3da`) authorizes lease owners to release/quarantine/reconcile only with their token and generation; it does not identify a named global hold owner. The active hold row names a containment call, not a human signer. The server OS account `DESKTOP-NNE313K\DELL` is not proof of release authority.

The checked official API source is `D:\project\worktrees\blue_apcd_shared_v3_gpu_reliability_v1\scripts\shared_fdtd\control_v3\db.py` (SHA256 `372a33ee95337960a62ee9f81f4ad3eacf361ea5f4bbcb7bf159bc73b6f3bd2c`), method `ControlDB.release_hold(...)`. It requires non-empty `released_by` and `release_authority_hash`, but the implementation does not authenticate the identity behind those strings. A signed owner authority must therefore be verified independently before an operator invokes it. The read-only Runner gate is a snapshot, not a distributed lease; the owner must serialize the release decision and dispatch window. No API call or DB write was made.

## Requested owner decision

The designated owner should provide an authenticated, signed record containing all of the following:

1. Owner identity, role, and the authoritative permission source (path/reference and SHA256).
2. Explicit acceptance of `C_EVIDENCE_INSUFFICIENT_LINEAGE_NOT_RECOVERABLE`, retaining physical entry count `UNKNOWN`; do not clear or waive the historical duplicate metric.
3. Explicit acceptance of the identity/provenance quarantine in the referenced manifest: exclude from training, ranking, scientific conclusions, and truth handoff; preserve all original events and artifacts; do not restart this attempt or create a replacement attempt.
4. A decision for the exact active hold ID and the generation observed at approval time. If release is authorized, name the official `ControlDB.release_hold` operation and supply the signed authority artifact/hash. Re-read current generation immediately before release; if it is no longer 26, obtain a fresh review. Do not reuse generation-25 authority.
5. If the independent two-plane diagnostic is to run after hold release, separately authorize only `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001`, maximum one entry, zero automatic replay; the currently pinned Runner authority still says `solver_entry_authorized=false` and `max_solver_entries_after_handoff=0`.

The current diagnostic solver authorization remains **false / 0**. The 160 V2 dataset cases remain **0 solver-authorized**. No solver should be launched from this draft.
