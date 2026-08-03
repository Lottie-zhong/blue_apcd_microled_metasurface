# LP ML Dataset v1 — Round-1 complete 255-geometry audit

## Status
`LP_ML_ROUND1_COMPLETE_DATASET_READY_OFFLINE_ONLY`

## Geometry 054 closeout
`LPML_R1_GLOBAL_SOBOL_054` is permanently quarantined. The prior production `054_y` failure and its single authorized recovery attempt remain retained; no third retry occurred. The orphan `054_x` checkpoint is excluded. No 054 row is present in the 255-geometry assembly.

## Continuation accounting
- Planned: 194 geometries / 388 x-y subruns / 450–454 nm at 0.5 nm.
- Entered: None; accepted: None; failed: None; quarantined: 0.
- Outcome: `LP_ML_ROUND1_CONTINUATION_PASS_READY_FOR_ASSEMBLY`; no replacement, retry, or systemic failure.

## Complete dataset
- Smoke 16 + prior clean production 45 + continuation 194 = **255 geometries / 2295 rows**.
- Nine rows per geometry, 450.0–454.0 nm at 0.5 nm step; complete raw complex Jones; no model-filled rows; positive-T gate passes.
- Strata: {'BOUNDARY_FAILURE': 32, 'GLOBAL_SOBOL': 127, 'PHASE_REGION': 64, 'PROJECTOR_REGION': 32}.
- Geometry-level deterministic 70/15/15 split; normalization statistics use training geometries only.

## From-scratch models
ExtraTrees, HistGradientBoosting and simple MLP use the seven frozen features and eight raw Jones components. Metrics are in `analysis/lp_ml_round1_full_tree_and_simple_baselines_v1.json`.

Five-seed residual MLP: CUDA `NVIDIA GeForce RTX 3080`, 7→256 with four residual blocks (SiLU/LayerNorm/dropout 0.03), seeds 11/22/33/44/55, fresh initialization, no warm start. Ensemble test MAE=0.05100821014418923, RMSE=0.06791744150073521, Frobenius mean=0.18361849679119271, phase circular MAE=4.0186444624589575 deg.

## Round-2 boundary
`lp_ml_dataset_v1_round2_offline_acquisition_proposal_v1.json` is offline-only with zero candidates and `solver_authorized=false`; no active learning, inverse design, D9, K6, Batch B, old Batch2, or solver expansion was launched.
