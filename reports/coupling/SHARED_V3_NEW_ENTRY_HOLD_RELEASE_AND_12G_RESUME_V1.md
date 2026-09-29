# SHARED_V3_NEW_ENTRY_HOLD_RELEASE_AND_12G_RESUME_V1

Date: 2026-09-29

## STATUS

`PRODUCTION_FIX_PROVENANCE_NOT_DURABLE`

The canonical PW accessor and Shared V3 liveness fixes pass zero-solver
regression. The hold was not released and no scientific case was dispatched.
The exact production path still includes a pre-existing, uncommitted
`gpu_bundle.py` behavior change that is outside the authorized fix allowlist.
The global hold also covers separate Coupling cases still recorded as
`POSTENTRY_NO_TRUTH`; their relation to the hold is not described in the
control-plane provenance.

## PRODUCTION FIX PROVENANCE

The fixes are in the canonical Coupling worktree, not a separate Shared V3
repository:

- worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
- branch: `work/mdc-np-coupling-ml-v1`
- pre-task HEAD: `789ceac980368cd90d7fb812e78347f2b0059407`
- upstream delta before changes: `0 0`

The scoped liveness/accessor source and tests are listed in the eventual
provenance commit. A separate pre-existing edit remains in
`scripts/shared_fdtd/engine/gpu_bundle.py` (temporary staging directory naming;
file mtime 2026-09-25). It is executable during GPU bundle persistence, is not
part of either named fix, and was not staged. Since the running production
path imports this module from the same worktree, the exact production path is
not fully represented by the scoped commit. Do not enter a scientific solver
until that unrelated diff has an authorized provenance disposition.

The runtime host shim `D:\apcd_runtime\bin\v3g2h.py` is a two-line `runpy`
wrapper that loads the canonical worktree host. The runtime campaign controller
is `D:\apcd_runtime\global_fdtd_control_v3\PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1_controller.py`;
its SHA256 is recorded in the accompanying main execution report. No matching
source was found under `scripts/shared_fdtd` or `scripts/coupling_ml` during this
audit.

SHA256 values at audit time:

- `scripts/shared_fdtd/engine/dispatcher.py`:
  `1628e1524be6001e8dac117cd8bf1520e73c70441eafe6219e83d4a22c58f297`
- `scripts/shared_fdtd/tools/v3_dispatcher_service.py`:
  `3c2e13127ecb3e71aba59d7effbf02459453e17e28875191b53103556424be4a`
- `scripts/shared_fdtd/tools/v3_g2_host.py` (after restoring both LOAD-only
  callbacks): `60c8921393e4513683f25c62bbead64d592130b52e7d23202b445b94f26065fc`
- `scripts/shared_fdtd/tools/pw_scientific_launcher.py`:
  `2ac608b5dcd8528846ca9d15964c035a03c919e6c52bcdfd31bb23bb32757ce5`
- liveness regression:
  `d99a9673c6daaf86489e70b505eb93a3487ece47458afc1496220b986596d934`
- same-launcher regression:
  `ed4ef78c4d9d877e8e5211a6a655a1a622b3ac72775d0250a2607a585ad78ed6`
- canonical accessor regression:
  `86d4d68411cbc70c143444209f05de0c7a167ac9ac24828493e34c640401a13a`
- PW launcher regression:
  `cd2185f3581d589ddba967d09245dad0a2b5035e5004b9d83d0b5051abba4970`
- pre-existing out-of-scope `scripts/shared_fdtd/engine/gpu_bundle.py`:
  `4dc467624bd4e987701034a3ff3ded1492a45693cea7511a416d16e8593f5c91`
- runtime host shim:
  `26881dfdff86c6dbe532ccc71f4b1f7efb0d27ff0fe12c6daec9ca54b81ee31e`
- runtime 12G controller:
  `186fceb5b8fb361aad99d72e0ef23b3614d2756df9975df9aafad4792237fc42`

While checking the actual host file, its native and post bundle persistence
calls were found without their `fresh_load_validate_path(...)` callbacks.
Both callbacks were restored so the frozen LOAD-only validation remains on the
production path. This does not change the physical contract.

## ZERO-SOLVER REGRESSION

All passed on the canonical worktree on 2026-09-29:

- global: 20/20
- branch: 20/20
- chaos: 12/12
- canonical contract accessor: 6/6
- PW launcher: PASS
- stale-host liveness: PASS
- same-launcher pre-entry handshake: PASS
- Medium PW pre-entry: 8/8
- PW K6 seed manifest: PASS
- solver invocations: 0

Detailed captured output:
`D:\apcd_runtime\global_fdtd_control_v3\audits\SHARED_V3_NEW_ENTRY_HOLD_RELEASE_AND_12G_RESUME_V1\zero_solver_regression.json`

## HOLD SCOPE AND PROVENANCE

Official `ControlDB` read-only state reports:

- authoritative `admission_control.control_id=1`: `new_entry_hold=TRUE`
- this row is global; the `admission_control` schema has no setter, reason, or
  incident-reference fields
- `control_generation=23`, last `updated_at=2026-09-29T04:31:17.858902+00:00`
- legacy sidecar status: `PW_K6_PRODUCTION_NEW_ENTRY_HOLD`, branch
  `coupling_ml`, with initial active slots W2H_19451 / W2H_10588
- sidecar creation time: Unix `1790236213.3450165`; it has no actor or reason
  field
- no durable `NEW_ENTRY_HOLD_RELEASED` event exists; release was not attempted

The two cases named by the hold sidecar have since reached durable scientific
validity:

- W2H_19451: native and post LOAD-only validation, `POST_FSP_VALID`,
  `RAW_VALID`, `SCIENTIFIC_VALID`, `HF_ARCHIVED`, then `RELEASED`
- W2H_10588: same validation sequence and terminal release

There are also separate Coupling queue rows still classified
`POSTENTRY_NO_TRUTH`, including K6V1_S12, K6V1_S13, and W2H_06824 attempt_001.
They have no active slot/lease, but their solver-entered attempts have no
validated truth. The global admission record does not say whether these
separate unresolved truth cases require the hold to remain. The hold-release
condition therefore cannot be certified from current control-plane provenance.

## CAPACITY AND OWNERSHIP SNAPSHOT

Read through the official Shared V3 database interface:

- global physical slots: 3; all 3 `FREE`
- Coupling-ML cap: 2, enabled
- Traditional cap: 1, disabled; no allocation changed
- GPU physical cap: 3
- active reservations: 0
- active GPU capacity leases: 0
- reserve IDs S22/S40/S24/S43/S44/S46: no queue rows
- foreign mutation and duplicate-entry counters: 0 (stored counters)
- active controller/host/FDTD/MPI-engine process: none observed; one persistent
  `smpd` service process was present

S35/S39 and all ten remaining approved geometries remain
`WAIT_RESOURCE_CAPACITY`, with no slot or lease. Their scientific entry,
GPU-entry, and replay counts remain zero. No attempt_002 was created.

## HOLD RELEASE DECISION

`NEW_ENTRY_HOLD_RELEASED`: NO.

The authorized Chart decision was conditional. The unresolved production-path
provenance and lack of hold-reason attribution prevent the required safety gate
from passing. No setter API was called, no SQLite mutation was made, and no
control-plane release event was fabricated.

## SCIENTIFIC AND DATASET STATUS

- Stage-1 unique scientific entries: 0 of 12
- S35/S39: existing logical `attempt_001`, no scientific entry
- truth validation: not started for S35/S39
- 32G authority: not built
- 20G versus 32G analysis: not run
- frozen H1 gate: unchanged / not evaluated for 32G
- NP forward-feature interface: untouched and unused
- reserve: sealed and untouched

## GIT

No unrelated files were staged. The worktree has extensive pre-existing dirty
and untracked state. The task-scoped files may be committed and pushed, but that
does not resolve the separate `gpu_bundle.py` provenance blocker. No commit or
push status is asserted here; see the final Git state after the scoped changes.

## NEXT

Resolve the provenance of the pre-existing GPU bundle staging-path edit and
record the separate unresolved `POSTENTRY_NO_TRUTH` cases' relationship to the
global hold. Keep the hold active until both gates are explicitly satisfied.
