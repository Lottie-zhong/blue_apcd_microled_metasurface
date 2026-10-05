# CONTINUATION — COUPLING K6 V2 128 Development Queue

Read this file first after context loss. Then read the immutable Runner handoff and this directory latest progress supplement and SHA inventory. Keep all queue execution on the remote Windows host.

## Workspace and authority

- Host/user: DESKTOP-NNE313K / dell; verified account desktop-nne313k\dell.
- Coupling worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1; branch work/mdc-np-coupling-ml-v1; observed HEAD 3c9c3b540c6b88d5c964245f37b5017397e68bea, upstream 0/0.
- Runner worktree: D:\project\worktrees\blue_apcd_gpu_production_runner_v1; branch codex/apcd-gpu-production-runner-v1; observed HEAD 02ad6b4b5f47b247f384fc132af329cc05612327, clean, upstream 0/0.
- Runner handoff: docs/APCD_GPU_PRODUCTION_RUNNER_V1_HANDOFF.md.
- Current route authority a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35; policy b89924544fe506f8775058730d6f491bca4206c1f5f55f7d247e338f9d04dd45; K6 V2 development budget overlay e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c.
- Frozen budget: 128 unique development IDs, attempt_001, maximum one entry per case, one slot serial, zero post-entry automatic replay. Confirmation IDs/responses remain denied.
- Use remote N:\anaconda_envs\RCP_LCP\python.exe; SSH via NetBird 100.81.105.58. Never output credentials.
- Coupling worktree had 204 unrelated dirty/staged/untracked paths at checkpoint; preserve all. Runner worktree was clean. Do not stage broadly.

## Scientific/execution boundaries

Fixed MDC, fixed spacer, ordered K6, frozen 440–460 nm contract, same truth/H2/H1. No training, P_scale fits, confirmation, reserve, extra HF, contract/monitor/mesh/Runner changes, or replay. Per-case entry requires the official Runner V1 path and live gates. Do not touch foreign processes.

## Completed entries at this checkpoint

Three of 128 development identities have one entry each and durable valid truth: historical pilot K6LDA1_DEV_D1_M05, K6LDA1_DEV_D1_P05, and K6LDA1_DEV_D2_M05. No confirmations, training, P_scale fits, or automatic replay. The first two are documented in PROGRESS_SUPPLEMENT_D1_P05_V1.md and prior task continuation.

K6LDA1_DEV_D2_M05 / attempt_001, ordered D [220,190,210,150,140,210] nm, completed once as K6V2_D2M05_20261005T143145Z_68c91452; Runner status DONE, one solver invocation, no replay, fresh LOAD and scientific validation PASS. Native truth H5 SHA 888c01cca9050a3ce4b664f6b2b9434e7f861b2bd41bd321e0a3e52df53b31fd; solved FSP SHA ac1d56f7c98c27540883add675cbc2ecbcaabefd1b232caed4bec3a733b86515; Runner state SHA 11fa8f1852f2f5aab6e5f1ba24ab8a0fe74125ce07c2a069e772c3618a46a829; raw fields SHA d819d55ff53d358e05d99c1be6762fdeb34da58101061c52fcbbd51a7d1e70c1; orders SHA 71fd997336ee0f14e0340656a981edff48a7bcd6daa410c46c6171e5f0de81a8. Frozen Coupling importer passed: C_hat (21,7,2), P_scale (21,), eta/absolute order (21,7), power residual 1.1102230246251565e-16. Ingested NPZ SHA 13cd84d25e0d19db5e6db727927115d0dd68d0022eee29d3dc773cf2aa52d0c6; ingest-result JSON SHA 3efc98a562e515758359955bc3b47b787b95e812821df27d974cacc2f1ca1a15. This is development truth only, not model admission.

## Workflow steering and next action

The user clarified that all remaining cases should be prepared before sequential queue execution. The prior per-case pattern had setup/preflight, one run, post-entry checks/import, and only then preparation of the next case. The completed D2 entry is retained; no entry has been started after the clarification.

The formal handoff documents adapter.py run-one <immutable-case-manifest.json>, GPU-only, serial, single-slot, no-replay; no native multi-case submission CLI was found. The intended adjusted workflow is therefore: batch-refresh each remaining case official current-route LOAD proof and formal setup preflight for all 125 cases, save and verify the frozen ordered queue, then invoke the existing official run-one interface sequentially in that order. Each run-one still performs its required live pre-entry/owner/GPU gate; this is not bypassed. Stop queue on any failed pre-entry or ambiguous post-entry state. Do not create or modify Runner source or an independent launcher.

Next identity by frozen budget order is sequence 4 K6LDA1_DEV_D2_P05 / attempt_001. Before any further entry, finish the batch preparation for all remaining IDs, including route-bound source manifest/proof, official preflight, setup hash checks, and a frozen queue status/hash. Existing setup packages are under outputs/coupling_ml/APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1/<case_id>/attempt_001/; their current manifests/proofs bind the older route and require official current-route refresh. Preserve old route evidence before replacing case-local files.

After batch preparation passes, perform only the per-case live final revalidation and official run-one calls serially. Runner truth is durable at each DONE; import/append development records without reading confirmation/diagnostic responses. Persist progress and hashes frequently so a connection loss never causes replay.

## 2026-10-06 workflow correction: serial batch queue

- User clarified the required batch order: prepare the complete case/setup list first, then run cases one at a time through the single Runner slot; after each case, require DONE, durable truth, released slot, and successful development-label ingest before advancing.
- The official GPU Runner interface remains one-case `adapter.py run-one`; a Coupling-only serial queue controller was added at `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\k6_v2_pipeline\serial_queue.py`. It does not change Runner code or launch outside the official entry.
- Zero-solver validation: local and remote `py_compile` passed; controller `--dry-run` passed with 3 previously completed/ingested cases, 125 queue cases remaining, and next case `K6LDA1_DEV_D2_P05` at sequence 4. Training fits, P_scale fits, confirmation access, and dry-run solver entries all equal 0.
- At this checkpoint 23 case route/preflight proofs are PASS; the remaining case-specific current-route checks are performed just before each case reaches the queue head, per the latest Chat steering. All setup packages were staged earlier.
- Current first-case preflight result SHA-256 `3a8b5049c98537d94bae84033fb61ace46da75265a58129770a5d98a3f39b98d`; queue-manifest canonical SHA-256 `ecbb9b32105f5a26adf051d614bef68fcf793e0f089eae391510e6b86a138e32`; controller SHA-256 `65e85ff5a1bba8f9ff54bec2e28196aea1dfc38a9c336f9e81ce28e7aaa4c906`. See `SERIAL_BATCH_QUEUE_WORKFLOW_V1.md` and `SHA256_INVENTORY_V3.json`.

## 2026-10-06 first live queue cycle

- First queued case `K6LDA1_DEV_D2_P05` completed through official Runner V1 as `K6V2_D2P05_20261005T170314Z_d24728f8`: solver_invocations=1, replay_count=0, DONE, validation PASS, durable truth and development ingest PASS. Total owner-budget rows now entered/truth-valid/labeled = 5/4/4; remaining unentered=123.
- Only after D2_P05 truth was ingested and the slot released did the queue begin `K6LDA1_DEV_D3_M05`. At this checkpoint its controller phase is `RUN_ONE_IN_PROGRESS`; current-run status is in `QUEUE_LIVE_CHECKPOINT_V1.json`.
- The controller persists the per-case ledger and never automatically replays a case after solver entry. If interrupted, reconcile Runner registry/status/truth/validation and queue ledger before continuing.

## 2026-10-06 second live queue cycle

- Second queued case `K6LDA1_DEV_D3_M05` completed through official Runner V1 as `K6V2_D3M05_20261005T171524Z_76271eae`: solver_invocations=1, replay_count=0, DONE, validation PASS, durable truth and development ingest PASS. Total owner-budget rows now entered/truth-valid/labeled = 6/5/5; remaining unentered=122.
- Only after D3_M05 truth was ingested and the slot released did the queue begin `K6LDA1_DEV_D3_P05`. At this checkpoint its controller phase is `RUN_ONE_IN_PROGRESS`; current-run status is in `QUEUE_LIVE_CHECKPOINT_V2.json`.
- The controller persists the per-case ledger and never automatically replays a case after solver entry. If interrupted, reconcile Runner registry/status/truth/validation and queue ledger before continuing.

## Queue checkpoint V2 is historical; live recovery authority

- `QUEUE_LIVE_CHECKPOINT_V2.json` is an immutable historical snapshot from `2026-10-05T17:29:18.381254+00:00` (6 entered / 5 truth-valid / 5 labels-valid; D3_P05 in progress). It is not the restart cursor.
- Recovery must reconcile `QUEUE_EXECUTION_LEDGER_V1.json` with Runner `registry.json`, matching run `status.json`, and durable truth/validation/hash artifacts. Do not replay any entered case.
- Read-only reconciliation at `2026-10-05T17:44:13.495624+00:00` found ledger time `2026-10-05T17:43:57.355977+00:00`, counts 7/6/6, remaining 121, failures/isolations 0; current `K6LDA1_DEV_D4_M05` / `attempt_001` / `K6V2_D4M05_20261005T173925Z_abe99c6d` was `RUN_ONE_IN_PROGRESS`, Runner state `SOLVER_ENTERED`, one entry, zero replay. The solver and slot were not touched. Details: `QUEUE_RECOVERY_AUTHORITY_NOTE_V1.md`.
