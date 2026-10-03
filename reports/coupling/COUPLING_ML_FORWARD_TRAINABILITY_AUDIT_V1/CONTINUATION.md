# COUPLING_ML_FORWARD_TRAINABILITY_AUDIT_V1 continuation

Read this file first, then protocol.json, checkpoint.json, source_audit.json, constant_baselines.json, four_geometry_pre_fit.json, fit_summary.json, reconstruction_and_training_audit.json, and artifact_hashes.json.

Remote DESKTOP-NNE313K / dell. Canonical root D:/project/blue_apcd_microled_metasurface. Formal worktree D:/project/worktrees/blue_apcd_mdc_np_coupling_ml_v1. Branch work/mdc-np-coupling-ml-v1. Runtime N:/anaconda_envs/RCP_LCP/python.exe with CUDA disabled. No AGENTS.md exists in the worktree or canonical root; user-provided project instructions govern.

Authority: committed G0 ordered-periodic POC and C0 amplitude/circular-phase POC, with frozen input hashes in protocol.json. This audit started at f0f47023af9c306590414232155c0d539c3dfa4d; the expected start HEAD was verified with no authority conflict.

Scope: trainability diagnosis only. ZERO solver, GPU Runner, new HF, reserve, inverse search, P_scale fit, full LOGO rerun, or platform work. No held-out truth was evaluated.

Fold 0 held out K6V1_S02. Four lexicographically selected outer-train cases were K6V1_EXT01, K6V1_EXT02, K6V1_EXT03, K6V1_EXT04, each with the complete 21-wavelength spectrum. Outer-train scaler/PCA were reconstructed deterministically and saved PCA parity was exact.

Exactly two fits completed once: T0 frozen C0 M5 and T1 frozen G0, seed 0, same four geometries, CPU AdamW lr 0.002 / weight_decay 0.0001 / clip 5, no validation, exactly 1,500 updates each (3,000 total). Final, minimum-loss, and resumable checkpoints plus step curves are persisted. Do not launch more fits.

Finding: saved G0 outputs are near-constant relative to the actual zero/mean baselines (median train loss 0.997874, median output/target latent variance ratio 0.000133, median coordinate correlation 0.132). Training chain passed gradient, optimizer, checkpoint, and refit-step reconciliation checks. Both tiny fits reached the nonzero rank-2 reconstruction floor by about step 300; this is train-only evidence, not generalization. The saved protocol did not fit its 31-geometry G0 outer-train set well; whether a longer/preregistered training budget improves held-out results remains untested.

Payload commit 211d0120ea3324b1a12221a750dfd91d7bc64b23 (parent f0f47023af9c306590414232155c0d539c3dfa4d) contains exactly the 32 task paths in audit.json. Exact-six-path evidence follow-up 5d49e8d59defcadf3e80f024e33a1b46d04813bb (parent 211d0120ea3324b1a12221a750dfd91d7bc64b23) records the origin verification; both pushes were verified. A final exact-allowlist closure commit records completed status and refreshed hashes. Recover the final state with `git rev-parse HEAD`, verify origin with `git ls-remote`, and consult audit.json for both verified commits and allowlists. The 332 unrelated worktree entries retain their original status hash 4d2ee81fb8d25f5c14d6513d147042b46547d0e42f22f90887ab39b9b097e893.

Recovery: no fit needs resumption. Read the final report and artifact_hashes.json. Preserve unrelated worktree entries. No follow-on fit, representation experiment, or sample expansion has been run or authorized.
