# LP ML Dataset v1 — Round-1 complete 255-geometry audit

## Status
`LP_ML_ROUND1_FORWARD_SURROGATE_READY_FOR_ACTIVE_LEARNING` (proposal only; no active-learning solver authorized or run)

## Geometry 054 closeout
`LPML_R1_GLOBAL_SOBOL_054` is permanently quarantined. Both entered=true/accepted=false y attempts remain retained; 054_x remains orphan evidence only and contributes no training row. No third retry, replacement, or geometry substitution occurred.

## Continuation solver accounting
194 untouched geometries, 388 planned/entered/accepted x/y subruns, 0 failed, 0 quarantined, 450–454 nm at 0.5 nm spacing. Sentinel: `LP_ML_ROUND1_CONTINUATION_PASS_READY_FOR_ASSEMBLY`.

## Complete geometries and rows
255 complete geometries and 2295 rows (nine wavelengths per geometry). Strata: `{'BOUNDARY_FAILURE': 32, 'GLOBAL_SOBOL': 127, 'PHASE_REGION': 64, 'PROJECTOR_REGION': 32}`. No model-filled rows, duplicate rows, or negative admitted T values.

## Dataset QA and split
The split is geometry-level and symmetry-group aware using `symmetry_equivalence_geometry_hash_sha256`; wavelength rows cannot cross splits. Feature normalization is train-only. Features are J1_side_nm, J2_length_nm, J2_width_nm, D_nm, sin_Psi, cos_Psi, wavelength_nm; targets are eight raw Jones Re/Im components.

## GPU environment and residual MLP
CUDA device `NVIDIA GeForce RTX 3080`, AMP `True`. Architecture 7→256 plus four 256-wide SiLU/LayerNorm/dropout 0.03 residual blocks to eight outputs. AdamW 3e-4/1e-4, batch 64, warmup 10, cosine to 1e-6, max 500 epochs, patience 50, clip 1.0, five independent seeds, no warm start. Ensemble test: MAE `0.010252661305352833`, RMSE `0.018935062031146345`, Frobenius mean `0.04520755064985274`, P90 `0.08148921976837746`, phase circular MAE `0.8401661174463495` degrees. Uncertainty/error correlation `0.6252277494284436`.

## Baselines and strata metrics
Tree/simple baselines are in `analysis/lp_ml_round1_full_tree_and_simple_baselines_v1.json`; HistGradientBoosting strata, endpoints, phase-wrap and low-phase slices are in `analysis/lp_ml_round1_strata_metrics_v1.json`.

## Round-2 proposal
Offline proposal only, zero candidates, `solver_authorized=false`; no active learning, inverse design, six-bin, K6, D9, Batch B, or old Batch2.

## Tests
Targeted contract suite: 12 passed. Full repository pytest previously timed out without a failure assertion; this remains an open hygiene item.
