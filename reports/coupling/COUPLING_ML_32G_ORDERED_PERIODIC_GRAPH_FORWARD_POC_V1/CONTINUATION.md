# COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1

Read this file first, then protocol.json, training_lock.json, checkpoint.json, seed_progress.json, results.json, audit.json, and artifact_hashes.json before resuming.

Remote: DESKTOP-NNE313K / dell. Formal worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`; canonical root: `D:\project\blue_apcd_microled_metasurface`; branch `work/mdc-np-coupling-ml-v1`. Start HEAD `aeae982ecb555df1b38ab08173119408486a7b10`.

Recovery script: `reports/coupling/COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1/g0_run.py`. Runtime is `N:\anaconda_envs\RCP_LCP\python.exe` with CUDA disabled. Protocol was frozen before training; the graph preflight and C0 evaluator parity are in `pretraining_tests.json`.

Scope: one offline G0 ordered periodic graph candidate, 288 grouped inner fits plus 96 outer refits maximum. C0 predictions are reused from the frozen amplitude/circular-phase POC. P_scale is the same frozen OOF RBF KRR. ZERO SOLVER, ZERO FDTD/GPU Runner/HF/reserve/inverse-search/platform work.

Current phase: MIXED_OR_TAIL_DETERIORATION. Training and held-out summaries are in `results.json`; full paired metrics, attribution, checkpoints and predictions are in CSV/NPZ/JSON artifacts. This is a development POC, not an independent geometry confirmation or production admission. Do not change width, rounds, edges, loss, rank, seeds or add candidates.

The exact payload allowlist was committed and pushed successfully. Commit: `cd4e79f42c86f04b957b765e13a28c6ed48e5300` (parent `aeae982ecb555df1b38ab08173119408486a7b10`). The verified push and clean task status are recorded in `audit.json`. Stop at science review.
