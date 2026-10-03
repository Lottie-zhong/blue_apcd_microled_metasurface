# COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1

Read this file first, then protocol.json, checkpoint.json, seed_progress.json, results.json, and audit.json before resuming.

Remote host DESKTOP-NNE313K, user dell. Prefer LAN SSH 192.168.1.107 when available; otherwise NetBird 100.81.105.58. Canonical project root D:\project\blue_apcd_microled_metasurface. Formal worktree D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1, branch work/mdc-np-coupling-ml-v1. Frozen start HEAD a9257143025969f800f04b1761a5dabf1811defa.

Authority: reports/coupling/COUPLING_ML_32G_COMPLEX_STATE_REPRESENTATION_DIAGNOSTIC_V1 and its continuation/protocol/checkpoint/results/audit; 32G Stage-1 truth/H1 package; V2 existing folds; frozen M5 module; H1 gate and H2 decoder. Exact hashes are in protocol.json.

Current scientific line remains fixed-MDC reliable K6 forward first. This task authorizes exactly C0 Cartesian control and C1 amplitude plus circular absolute-phase CPU offline fits. ZERO SOLVER: no FDTD, GPU Runner, new HF, reserve, inverse search or Runner development. Keep D1..D6 ordered. No extra configurations/seeds/tuning.

Recover: use scripts/coupling_ml/coupling_ml_32g_amplitude_circular_phase_forward_poc_v1.py. It verifies frozen hashes, loads predictions_partial.npz and seed_progress.json, skips completed config/fold/seed fits and writes each completed seed atomically. Do not reset if HEAD advances; inspect new authority. Historical S35 FAILED_POSTENTRY and its separate LOAD-only recovery stay intact.


## Execution status after the amplitude/circular-phase POC

All 192 preregistered C0/C1 outer-fold and seed fits completed. No solver, GPU Runner, new HF, reserve case, inverse search or Runner development was run. RCP_LCP was used with CUDA masked (`CUDA_VISIBLE_DEVICES=-1`); training tensors and models stayed on CPU.

C0 reproduced historical FULL H1 summaries within 1e-12 and its mean complex prediction differed by at most 1.31e-8. C1 lowered amplitude, routing and absolute-order errors but worsened relative-phase and aggregate state error. Both candidates remain H1 FAIL; the shared frozen P_scale branch also fails its original gate. No follow-on configuration or sample was run.

Recovery: read this document, protocol.json, checkpoint.json, results.json, audit.json, seed_progress.json and artifact_hashes.json. The 192 completed fold/seed fits and predictions are in predictions_partial.npz and oof_predictions.npz; the exact saved script skips completed fits if resumed. The human-readable results are in COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1.md. Stop at science review; do not extend this training budget.


## Commit-format audit

Before commit, one extra blank CRLF at EOF was removed from the training script and its test file to satisfy `git diff --check`. No executable statements changed. `audit.json` records both the exact frozen training/test hashes and final committed hashes; appending one CRLF to each final file reconstructs its frozen bytes.
