# COUPLING_ML_32G_PREDICTED_AMPLITUDE_PHASE_HYBRID_AUDIT_V1 Continuation

Read this file first, then `protocol.json`, `results.json`, `audit.json`, `checkpoint.json`, and `artifact_hashes.json` before recovery. Do not rely on chat history.

## Project and connection
Remote host: `DESKTOP-NNE313K`; user: `dell` (`desktop-nne313k\dell`). Canonical project root: `D:\project\blue_apcd_microled_metasurface`. Formal worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`; branch `work/mdc-np-coupling-ml-v1`; task starting HEAD `456cf707880e25283b325dad4b3fc5904aae58d1`. Prefer LAN SSH `dell@192.168.1.107`; use NetBird `dell@100.81.105.58` if LAN is unavailable. Reuse the existing key without printing or changing credentials. Python environment for existing ML work is `N:\anaconda_envs\RCP_LCP\python.exe`.

## Authority and scientific route
Read authority in this order: `reports/coupling/COUPLING_ML_32G_COMPLEX_STATE_REPRESENTATION_DIAGNOSTIC_V1/CONTINUATION.md`; `reports/coupling/COUPLING_ML_32G_AMPLITUDE_CIRCULAR_PHASE_FORWARD_POC_V1/CONTINUATION.md`, `protocol.json`, and `results.json`; frozen 32G dataset and H1 authority under `reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/`; existing LOGO fold manifest under `reports/coupling/COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2/`; `reports/coupling/PW_K6_H1_NUMERIC_GATE_AUTHORITY_V1.json`; and `scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py` (frozen H2). Exact SHA-256 values are pinned in this task's `protocol.json` and `audit.json`.

Formal HF route remains integrated 3D periodic plane-wave FDTD for GaN + fixed top MDC + 237 nm spacer + ordered K6 NP + air; no bottom DBR or patterned Meta-MDC. The research sequence remains fixed-MDC K6 forward, then MDC–NP joint forward/inverse closure, then any multi-angle extension, with sparse 3D dipole certification only for a final candidate. This task is only an offline post-hoc representation audit on the existing 32-geometry, 440–460 nm, 1 nm OOF predictions, seeds 0/1/2. It performed ZERO TRAINING and ZERO SOLVER and grants no production admission.

## Result and task boundary
Exactly one hybrid was formed from paired saved predictions: `abs(C1)` with C0 per-seed phase, using the frozen `1e-8` C0 phase threshold and saved-C1/fixed-unit fallback. The same frozen OOF RBF KRR P_scale branch and original H2/H1 path were used. All candidate, gate, seed, tail, H2, fallback and P_scale measurements are in the report and `results.json`; split/leakage and run-boundary checks are in `audit.json`. Current result is post-hoc development evidence only; no confirmatory evaluation or follow-up experiment is authorized.

## Artifacts and recovery
Primary report: `COUPLING_ML_32G_PREDICTED_AMPLITUDE_PHASE_HYBRID_AUDIT_V1.md`. Outputs: `hybrid_oof_predictions.npz`, `per_geometry.csv`, `per_wavelength.csv`, `per_order.csv`, `seed_metrics.csv`, `fallback_by_geometry.csv`, `pscale_by_geometry.csv`, `h2_reconstruction.csv`, `results.json`, `audit.json`, `protocol.json`, and `artifact_hashes.json`. Code/test: `scripts/coupling_ml/coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py` and `tests/coupling/test_coupling_ml_32g_predicted_amplitude_phase_hybrid_audit_v1.py`.

Recovery: verify hostname/user, worktree, branch, current HEAD/upstream, exact task commit/push state, and all hashes. If `results.json` exists, do not rerun metric computation or regenerate the hybrid; resume from the persisted outputs. Preserve unrelated dirty/untracked files. No solver, training, reserve, inverse search, Runner work, or production admission is authorized by this task.
