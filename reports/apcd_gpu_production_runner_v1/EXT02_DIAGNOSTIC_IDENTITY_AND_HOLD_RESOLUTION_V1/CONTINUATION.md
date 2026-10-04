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


## 2026-10-04 route/proof refresh — APCD_GPU_RUNNER_HOLD_CLOSEOUT_AND_DIAG_PREFLIGHT_REFRESH_V1

- Refreshed under official route `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`; route adapter `43fcc070e70510d45026f0dd7242ac38e65b7ea9967149649a4b1c09b848b3bb`, policy `b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45`, authority `d2b35c1b376e3ca5e1c7b38650861be2fb33ebc713e86772f8d82a9ebb634f56`.
- Identity remains `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001`, separate from historical `K6V1_EXT02 / attempt_001` (one historical entry event `1680`, truth SHA256 `a75a081c75d1fa3ed5e483fe8dccfd5906fb1e7b2e065fc6810aea1580a87ded`). Diagnostic queue/event scan remains zero entries. No historical attempt was renamed, reset, or overwritten.
- Current independent contract SHA256 `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68`; semantic SHA `b049c2d7f5f4418abd526599157d5973a942a22f080a7a77a974403a03b320e6`; setup fingerprint `441020e420c609dffb6ffa28fbe8df6648385bdee9ca2373550252d7ce170262`; source manifest SHA `471b34053c2048174d9bbd8cffe5b210684c822924e4446aa9a46e384c52d7eb`; source/staged FSP SHA `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`; current fresh setup LOAD-only proof SHA `0567ed5c0fb298817e4c4d166b5000e63eedb57301f8449352babee70eb5c8b1`; official no-slot preflight result SHA `ed30226995b96f83b80f3f72fbcc36e49f092652698a05d4c7fe6a8c6d16a500`; envelope SHA `b352899bc0f343d77feecd4db2d550c2851a523eee4a4146c6c544a18d878a73`. All are current-route setup-admission evidence only.
- Preflight: `PASS`; solver invocation/entry `0`; run envelope not created. Existing `MON_POSTNP` was preserved; exactly `EXT02_POSTNP_DIAG_Z2000` was appended. Configured z/reference-plane data are recorded in the setup proof; actual sampled z, solved local field mesh, and PML inner edge remain post-solver measurements and are not asserted.
- Authorization remains `setup_preflight_authorized=true`, `solver_entry_authorized=false`, current solver budget `0`, proposed future budget `1`, automatic replay `0`, training eligibility `false`. Active global hold generation 26 remains applicable; setup preflight was permitted, solver dispatch is not. No run-one call.
- This refresh: solver entries `0`, FDTD runs `0`, replays `0`. The fresh setup LOAD proof does not stand in for post-solver durable truth or scientific validation.
