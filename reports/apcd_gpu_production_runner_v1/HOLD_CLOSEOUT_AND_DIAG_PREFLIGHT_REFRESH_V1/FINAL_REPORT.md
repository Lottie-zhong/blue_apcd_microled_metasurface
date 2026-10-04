# APCD GPU Runner hold closeout and diagnostic preflight refresh

## STATUS

**PARTIAL.** The independent diagnostic is freshly admitted at setup level. Queue21 has a durable evidence-insufficient disposition; its physical entry count cannot be determined, so the generation-26 global hold remains active and no release authority can be issued.

## QUEUE21 DISPOSITION / HOLD

Events `1499` and `1506` for `K6_5X3_SP237_X_CENTER_ORIGIN_PLUS1 / attempt_001` share the same lease token and fencing generation `14`, but neither carries process identity. The available record cannot distinguish one physical solver with duplicate event recording from two launches. Event-linked process/engine/GPU lineage, FSP/H5 archive identity, durable truth hashes, completion and fresh-LOAD proof are missing. The existing durable disposition remains `C_EVIDENCE_INSUFFICIENT_LINEAGE_NOT_RECOVERABLE`; raw events and truth were not changed.

The live control DB snapshot is SHA256 `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`. Hold `hold-4a6eab94af3b4a6d8510ba2fe32a5b66` is `ACTIVE`, global generation `26`, reason `SHARED_V3_DUPLICATE_ENTRY_METRIC_CONTAINMENT`, with no release principal or authority hash. The hold links the unresolved queue21 incident. Although the pinned Runner V1 route is filesystem-authoritative and has no direct Shared V3 DB dependency, no formal migration authority permits bypass. No release API, direct DB change, ledger rebuild, or owner/fence edit was performed.

Existing offline prevention evidence is 59 passed and 38 subtests passed. No Runner runtime code changed in this closeout. Those offline tests do not resolve the historical physical entry count.

## DIAGNOSTIC CURRENT PREFLIGHT

`K6V1_EXT02_TWO_AIR_PLANES_DIAG / attempt_001` remains a distinct diagnostic identity linked to historical `K6V1_EXT02 / attempt_001`. Historical event `1680` and its single-plane truth SHA256 `a75a081c75d1fa3ed5e483fe8dccfd5906fb1e7b2e065fc6810aea1580a87ded` remain unchanged. The diagnostic identity has no historical entry.

The current official route is `APCD_GPU_RUNNER_VERSIONED_CONTROLLED_ADMISSION_V1`; adapter SHA256 `43fcc070e70510d45026f0dd7242ac38e65b7ea9967149649a4b1c09b848b3bb`, policy `b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45`, authority `d2b35c1b376e3ca5e1c7b38650861be2fb33ebc713e86772f8d82a9ebb634f56`.

- Independent contract SHA256: `58ac1ac81fc4a0da61784d62bf80c48fc21d6e119ee96e5941fc1139b5954e68`; semantic SHA256: `b049c2d7f5f4418abd526599157d5973a942a22f080a7a77a974403a03b320e6`.
- Setup fingerprint: `441020e420c609dffb6ffa28fbe8df6648385bdee9ca2373550252d7ce170262`.
- Source manifest: `471b34053c2048174d9bbd8cffe5b210684c822924e4446aa9a46e384c52d7eb`.
- Source and staged FSP: both `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`.
- Fresh setup LOAD-only proof: `0567ed5c0fb298817e4c4d166b5000e63eedb57301f8449352babee70eb5c8b1`.
- Formal setup preflight: **PASS**, result SHA256 `ed30226995b96f83b80f3f72fbcc36e49f092652698a05d4c7fe6a8c6d16a500`; envelope SHA256 `b352899bc0f343d77feecd4db2d550c2851a523eee4a4146c6c544a18d878a73`.

The setup preserves `MON_POSTNP` and adds only `EXT02_POSTNP_DIAG_Z2000`. Actual sampled z, solved mesh and PML inner edge remain pending a future authorized solver run. This is setup-admission proof only, not truth recovery or two-plane scientific validation. Authorization still says setup preflight allowed, solver entry not authorized, current entry budget 0, proposed future budget 1, automatic replay 0, and training eligibility false.

## V2 160-CASE PROOF COMPATIBILITY

The existing 160-case enrollment/preflight package remains pinned to route authority `d2b35c1b376e3ca5e1c7b38650861be2fb33ebc713e86772f8d82a9ebb634f56`, matching the current authority. The recorded full artifact rehash covered all 160 formal results, source manifests, setup proofs, source/staged FSPs and found 160 checked / 0 mismatch. No FDTD LOAD was repeated. Counts remain 160 enrolled, 160 canonical/staged ready, 160 fresh LOAD PASS, 160 formal preflight PASS, 160 solver unauthorized with budget 0; confirmation responses remain unread and training-ineligible. These setup proofs remain conditional on their bound artifacts and do not replace mandatory start-time revalidation or grant solver authorization.

## EXECUTION COUNTS

Solver entries `0`; FDTD run calls `0`; replay `0`; no run-one invocation. The fresh diagnostic setup LOAD-only proof and no-slot formal preflight were completed. No historical event, truth, attempt, global hold, or control generation was mutated.

## UNRESOLVED

1. Recover authoritative queue21 process/engine/GPU and artifact lineage, or retain the evidence-insufficient disposition and active hold.
2. No authorized owner/release authority for the active generation-26 hold is recorded.
3. Diagnostic solver entry remains unauthorized; do not start until hold/release conditions and a separate one-entry case authorization are formally satisfied.
4. Actual two-plane sampled coordinates and solved mesh/PML readback are pending the authorized diagnostic run.

## NEXT — DO NOT EXECUTE

Obtain the queue21 event-linked lineage from the formally authorized owner. Do not dispatch a case or bypass the active hold while that evidence and release authority remain unresolved.
