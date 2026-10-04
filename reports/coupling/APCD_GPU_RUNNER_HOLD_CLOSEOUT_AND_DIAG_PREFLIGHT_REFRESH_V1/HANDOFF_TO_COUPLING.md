# GPU Runner closeout handoff to Coupling

Date: 2026-10-04

## State

- Queue21 `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001`: physical entry count remains undetermined. Events 1499/1506 share lease/fence14 but lack process and artifact lineage. Durable disposition remains `C_EVIDENCE_INSUFFICIENT_LINEAGE_NOT_RECOVERABLE`.
- Global hold `hold-4a6eab94af3b4a6d8510ba2fe32a5b66`, generation 26, remains ACTIVE. No release authority is recorded; no API/DB release was attempted.
- Runner V1 remains single-slot, filesystem-authoritative. This architectural separation is not release authority and does not waive the incident linked to the hold.

## Independent diagnostic preflight

Identity: `K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001`; historical source: `K6V1_EXT02 / attempt_001`. Setup route: `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`. Official setup preflight PASS; no solver entry. The preserved `MON_POSTNP` plus exactly one added `EXT02_POSTNP_DIAG_Z2000` are represented by the independent contract.

- Contract SHA256: `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68`; semantic SHA: `b049c2d7f5f4418abd526599157d5973a942a22f080a7a77a974403a03b320e6`.
- Source manifest SHA: `471b34053c2048174d9bbd8cffe5b210684c822924e4446aa9a46e384c52d7eb`.
- Source/staged FSP SHA: `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`.
- Fresh setup LOAD-only proof SHA: `0567ed5c0fb298817e4c4d166b5000e63eedb57301f8449352babee70eb5c8b1`.
- Formal preflight result SHA: `ed30226995b96f83b80f3f72fbcc36e49f092652698a05d4c7fe6a8c6d16a500`; route authority SHA `d2b35c1b376e3ca5e1c7b38650861be2fb33ebc713e86772f8d82a9ebb634f56`.
- Authorization remains solver-entry false, current solver budget 0, future proposal 1, automatic replay 0; setup preflight is not solver authorization.
- Actual sampled z, solved local field mesh and PML inner-edge data are pending after an authorized solver run. No two-plane scientific comparison has passed.

## K6 V2 160-case proof compatibility

Existing 160-case proofs remain bound to the current authority hash above. Full rehash audit: 160 cases, 0 mismatches across formal results, manifests, proofs and source/staged FSPs. No new LOADs were run. Existing proofs do not grant solver authorization and do not replace start-time freshness checks. Confirmation responses remain unread; no manufacturing authority is implied.

## Execution counts and next action

This closeout: solver entries 0, FDTD runs 0, replays 0. Do not launch the diagnostic or any of the 160 cases. The next required action is owner recovery of queue21 event-linked lineage; only after a formal disposition covering the active hold and a separate one-entry diagnostic authorization may execution be reconsidered.
