# PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1

Date: 2026-09-29

## STATUS

`PRODUCTION_FIX_PROVENANCE_NOT_DURABLE`

No new scientific solver entry has occurred in this execution session. The
existing global `NEW_ENTRY_HOLD` remains active. The authorized continuation of
the 12 approved Stage-1 geometries is not dispatched pending production-code
provenance and hold-scope gates.

## AUTHORITY

- original Stage-1 budget: exactly 12 unique geometries
- approved IDs, in manifest order:
  `K6V1_S35`, `K6V1_S39`, `K6V1_S21`, `K6V1_S42`, `K6V1_S36`, `K6V1_S31`,
  `K6V1_S45`, `K6V1_S32`, `K6V1_S47`, `K6V1_S33`, `K6V1_S37`, `K6V1_S48`
- S35/S39 continue as `attempt_001`; no `attempt_002`
- frozen physical contract hash:
  `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`
- hold decision and detailed provenance audit:
  `reports/coupling/SHARED_V3_NEW_ENTRY_HOLD_RELEASE_AND_12G_RESUME_V1.md`

## CASE STATUS

| Case | Attempt | Queue state | Scientific entry | Slot/lease |
|---|---|---|---:|---|
| K6V1_S35 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S39 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S21 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S42 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S36 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S31 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S45 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S32 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S47 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S33 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S37 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |
| K6V1_S48 | attempt_001 | WAIT_RESOURCE_CAPACITY | 0 | none |

## EXECUTION ACCOUNTING

- solver invocations in this turn: 0
- new scientific entries: 0
- new GPU entries: 0
- replay: 0
- duplicate entries: 0
- reserve entries: 0
- slots and leases: all released/free
- 12G scientific truth validation: not started
- 32G dataset authority: not built
- 20G versus 32G comparison: not run
- H1 gate: not evaluated for 32G
- NP feature interface: untouched and unused

## CONTROL PLANE

- `NEW_ENTRY_HOLD=TRUE`; release event not recorded
- global cap: 3 slots
- Coupling-ML cap: 2, enabled
- Traditional cap: 1, disabled; no change made
- GPU physical cap: 3
- all three global slots are currently FREE
- reserve cases `S22`, `S40`, `S24`, `S43`, `S44`, `S46` have no queue rows

## PROVENANCE

The runtime campaign controller is at
`D:\apcd_runtime\global_fdtd_control_v3\PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1_controller.py`
with SHA256 `186fceb5b8fb361aad99d72e0ef23b3614d2756df9975df9aafad4792237fc42`.
It imports Shared V3 modules from the canonical Coupling worktree. A separate
pre-existing edit in `scripts/shared_fdtd/engine/gpu_bundle.py` remains
uncommitted and is used during GPU bundle persistence; it was not staged as it
is outside the authorized liveness/schema fix allowlist.

Relevant source SHA256 values:

- dispatcher: `1628e1524be6001e8dac117cd8bf1520e73c70441eafe6219e83d4a22c58f297`
- host launcher service: `3c2e13127ecb3e71aba59d7effbf02459453e17e28875191b53103556424be4a`
- host runtime: `60c8921393e4513683f25c62bbead64d592130b52e7d23202b445b94f26065fc`
- PW scientific launcher:
  `2ac608b5dcd8528846ca9d15964c035a03c919e6c52bcdfd31bb23bb32757ce5`
- out-of-scope GPU bundle diff:
  `4dc467624bd4e987701034a3ff3ded1492a45693cea7511a416d16e8593f5c91`

## NEXT

Complete provenance disposition for the GPU bundle staging-path edit and
confirm the unresolved historical post-entry truth cases do not independently
require the global hold. Then re-run the exact S35/S39 pre-entry assertions and
resume through the official Shared V3 controller if the gates pass.
