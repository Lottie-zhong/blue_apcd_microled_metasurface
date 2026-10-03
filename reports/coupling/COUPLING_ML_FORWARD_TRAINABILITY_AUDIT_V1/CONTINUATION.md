# COUPLING_ML_FORWARD_TRAINABILITY_AUDIT_V1 continuation

Read this file first, then protocol.json, checkpoint.json, source_audit.json, constant_baselines.json, four_geometry_pre_fit.json, fit_summary.json, reconstruction_and_training_audit.json, and artifact_hashes.json.

Remote DESKTOP-NNE313K / dell. Canonical root D:/project/blue_apcd_microled_metasurface. Formal worktree D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1. Branch work/mdc-np-coupling-ml-v1. Start HEAD f0f47023af9c306590414232155c0d539c3dfa4d. Runtime N:/anaconda_envs/RCP_LCP/python.exe with CUDA disabled. No AGENTS.md exists in the worktree or canonical root; follow user-provided project instructions and frozen protocol.

Authority consists of the committed G0 ordered-periodic POC and C0 amplitude/circular-phase POC, plus frozen input hashes in protocol.json. Expected HEAD was verified; no authority conflict was found.

Scope: trainability diagnosis only. ZERO solver, GPU Runner, new HF, reserve, inverse search, P_scale fit, full LOGO rerun, or platform work. No held-out truth was evaluated.

Fold 0 held out K6V1_S02. Its four selected train cases, chosen lexicographically from outer train, are K6V1_EXT01, K6V1_EXT02, K6V1_EXT03, K6V1_EXT04. The outer-train scaler/PCA were reconstructed deterministically; saved PCA parity was exact.

Exactly two fits completed once: T0 frozen C0 M5 and T1 frozen G0, seed 0, full batch, same four geometries, CPU AdamW lr 0.002 / weight_decay 0.0001 / clip 5, no validation, exactly 1,500 updates each. Total 3,000. Final, minimum-loss, and resumable checkpoints plus step curves are persisted. Do not launch more fits.

Current phase: report and audit complete; exact-allowlist commit and normal push pending. Saved G0 outputs are near-constant relative to actual zero/mean baselines. Both tiny fits reach the rank-2 train floor by about step 300. This is not held-out evidence. Review the early-stop/refit budget before a next representation or data experiment; do not execute the proposal without Chat selection.

Recovery: no fit needs resumption. Read the report and artifact_hashes.json; preserve all 332 unrelated worktree entries. Stage only exact paths recorded in audit.json, then normal push.
