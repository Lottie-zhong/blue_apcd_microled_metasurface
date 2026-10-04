# Continuation — EXT02 independent two-air-plane diagnostic identity

Last verified: 2026-10-04, remote `DESKTOP-NNE313K` as `desktop-nne313k\dell`.

## Current state

- Historical production identity: `K6V1_EXT02 / attempt_001`, one preserved solver entry (event 1680), terminal truth SHA `a75a081c75d1fa3ed5e483fe8dccfd5906fb1e7b2e065fc6810aea1580a87ded`. Never replay or overwrite it.
- New diagnostic identity: `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001`. Registered in the pinned controlled-admission authority for setup preflight only, linked to the historical source, excluded from training, and old overlay future-start authorization revoked.
- Current solver permission: **false**. Authority `max_solver_entries_after_handoff=0`. The one-entry / zero-replay figure is a future proposal only; it is not entry permission. No `attempt_002`.
- Fresh formal preflight: PASS, source/staged FSP SHA `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`, contract SHA `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68`, proof SHA `245d4cfc34ad7c0069c7b831d3fc4df862694d4fee4687268ea6310b522aee37`, result SHA `697ceebdeb82ebdddfe026f72e7f558ad7f28c7ed3185222240b2f208727530f`. Solver/run/replay counters: `0/0/0`.
- Global controller hold: active `hold-4a6eab94af3b4a6d8510ba2fe32a5b66`, generation `26`, DB SHA `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`. Cause: queue21 events 1499/1506 unresolved. No release owner/hash is recorded on the active hold. Hold remains active; no DB write or release call was made.

## Files and evidence

Full report: `FINAL_REPORT.md`. Machine-readable audit snapshot: `IDENTITY_AND_HOLD_EVIDENCE.json`. Versioned copies of identity/provenance, contract, source manifest, setup proof, preflight result and inventory are under `evidence/`. Source/staged FSP remain in the Coupling output directory recorded by the inventory and are intentionally excluded from Git.

## Resume only after explicit authorization

1. Have the Shared V3 authority owner resolve or rebuild the duplicate-lineage incident through the official durable process and issue an applicable release authority; verify live generation and hold state without editing SQLite directly.
2. Obtain a separate explicit one-entry grant for `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001`. Do not infer it from the prior budget proposal, this setup preflight, an idle GPU, or the old attempt's release.
3. Recheck entry history, current generation/hold, owner/fence/quota, route/policy/authority, identity, contract, manifests, source/staged FSP and fresh setup LOAD proof at launch time. Use only the formal Runner; never `run-one` before successful `FINAL_LAUNCH_REVALIDATION`.
4. If authorized and run, require one complete GPU-lineage entry, durable FSP/H5, fresh LOAD, `SCIENTIFIC_VALID` and official release. Extract both planes from the immutable archive and verify actual coordinates/mesh/PML. Use the frozen Coupling de-embedding protocol without phase-oracle alignment. Do not train on this diagnostic.
5. Stop after any post-entry failure or ambiguous lineage. Zero automatic replay; no new attempt under this authorization.

This continuation supersedes the earlier old-ID setup handoff for future overlay startup. Historic reports and the old production case remain unchanged.
