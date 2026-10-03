# Continuation — COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1

**Updated:** 2026-10-03 16:48 UTC
**State:** `READY_FOR_CHAT_REVIEW`; stop before any training or solver entry.

## Restore context first

- Worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
- Branch: `work/mdc-np-coupling-ml-v1`
- Task-start HEAD: `42748512daedfb580f77199c32cc8ff31ab508d1`, a formal successor of requested `03f4a5b737a99bb0ec5b6a0d38b64a5d51ad1a3f`.
- Read this file, then `LOCAL_LEARNABILITY_DOE_PLAN_REPORT_V1.md`, `PREREGISTERED_PROTOCOL_V1.json`, `CANDIDATE_MANIFEST_V1.json`, `COVERAGE_DIAGNOSTIC_V1.json`, and `SETUP_PREFLIGHT_AND_HASHES_V1.json` before resuming.
- Artifact hash index: `ARTIFACT_HASHES_V1.json` SHA256 `b747210916199ad256203365226211fd60eac7b6ba5800a8117d41b467d7ec28`.

## Frozen science and results

- Current geometry is ordered K6 D1…D6; fixed MDC and 237 nm spacer; base contract SHA256 `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`. Geometry authority SHA256 `93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f`; 32G dataset authority SHA256 `0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e`.
- Anchor is `K6V1_S31` with D=`[220, 195, 210, 150, 140, 210]` nm, chosen using only domain margin, cyclic clearance, centroid distance, and case ID. The local grid is anchor±5 nm per coordinate, 5 nm grid; 12 axial development candidates and four geometry-only sealed combinations.
- All 16 candidates pass formal bounds/grid, uniqueness/protected-set, cyclic non-overlap, and setup mesh checks. Minimum adjacent periodic gap is 70.0 nm. Independent manufacturability authority remains unresolved.
- Existing 32G has 32 geometry groups; no close pair below normalized distance 0.75. Pairwise correlations and caveats are in the report and coverage JSON. These data do not resolve the local ±5 nm question.
- Future minimal model is local affine Cartesian C_hat plus separately predicted P_scale. It has not been fit. Proposed future development: 12 leave-one-axial-geometry-out fits plus one final fit on anchor+12; only then open four sealed responses once. No training is authorized now.

## Setup state and dependencies

- Sixteen task-private pre-FSPs were built and freshly LOAD-only validated: see `SETUP_PREFLIGHT_AND_HASHES_V1.json` and `outputs/coupling_ml/COUPLING_ML_K6_LOCAL_LEARNABILITY_DOE_PLAN_V1_SETUP_ONLY/`.
- These FSPs are not Runner canonical, have no case authority manifests, and are not approved for `run-one`. Runner remains limited to its 12 existing identities.
- Zero solver entries and zero training in this task. No truth, H1/H2, Runner, or production mesh changed.
- POSTNP monitor remains current authority. The two-air-plane audit lacks a second independent air-plane field and remained blocked pre-entry. Do not move monitors or launch any of the 16 candidates before Chat reviews the monitor dependency and grants a new solver budget/authority.
- Existing S35 `FAILED_POSTENTRY` and its separate LOAD-only recovery remain unchanged; no automatic replay.

## Resume/stop boundary

No further scientific execution is pending in this task. Resume only for evidence/report integrity or exact allowlist Git completion. After commit/push, stop and wait for Chat review. This continuation is the durable recovery entry; do not rely on prior chat turns alone.
