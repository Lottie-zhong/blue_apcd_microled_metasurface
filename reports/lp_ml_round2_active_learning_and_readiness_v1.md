# LP_ML_DATASET_V1 Round-2 Targeted Active Learning

## Provenance exception

- Accepted exception attestation: UNRECOVERABLE_DERIVED_REPORT_BYTE_IDENTITY_EXCEPTION_ACCEPTED.
- The affected derived report was not modified in this task; current SHA256 remains 171033e0d2c73865d0f8610e81d5a33de56d7deb79d8d38aa2f925f7e17e8321.
- Historical expected bytes are unrecoverable; this is a governance exception, not a physics/data exception.

## Candidate-pool and frozen plan

- Feasible pool: 60,000 legal candidates (at least the authorized 50,000 minimum), selected before solver using the frozen Round-1 five-seed ensemble.
- Frozen plan: 64 geometries with quotas {"BOUNDARY_AND_HIGH_GRADIENT": 8, "DIVERSITY_CONTROLS": 8, "HIGH_UNCERTAINTY": 20, "LOW_PHASE_AND_SIX_BIN_COVERAGE": 16, "PROJECTOR_FAVORABLE_TRADEOFF": 12}.
- Existing geometries and geometry 054 were excluded; exact/canonical/symmetry duplicates are zero in the selected plan.

## Solver accounting

- Planned/entered/accepted: 64 geometries / 128 x-y subruns / 128 / 128.
- Spectral rows: 576 (450.0-454.0 nm, 0.5 nm step, 9 points). Failed/quarantined/duplicate: 0/0/0. Geometry 054 generated/retried: no/no.
- Formal observable remained Native-M1 weighted-G0 at z=1000 nm with endpoint deduplication and sqrt(T)/norm(weighted Ex,Ey).

## Prospective frozen Round-1 evaluation

- Evaluation was completed before any merged-data retraining; bounded geometry 054 was excluded.
- Metrics: {"element_mae": 0.04004816, "element_max": 1.0062957, "element_rmse": 0.0763556818087513, "frobenius_mae": 0.1792709092128549, "frobenius_max": 1.023515014042609, "phase_mae_deg": 2.4162158130158606, "rows": 576}.
- Ensemble uncertainty mean/P95: 0.0369761660695076 / 0.0596989206969738.

## Merge and retraining

- Merged complete dataset: 319 geometries / 2871 rows; Round-1 split retained and Round-2 grouped as 48 train / 8 validation / 8 permanent external test geometries.
- HGB, ExtraTrees, SimpleMLP, and five independent residual MLP seeds were trained from scratch; no warm start.
- Fresh residual MLP ensemble test (recomputed from saved checkpoints): {"element_mae": 0.0092743013417006, "element_max": 0.17769230739325498, "element_rmse": 0.018821056306473277, "frobenius_mae": 0.03832138894600955, "frobenius_max": 0.23762623649187023, "phase_mae_deg": 0.6693944068145237, "rows": 414}.
- Fresh tree/simple test metrics: {"ExtraTrees": {"test": {"element_mae": 0.01572254045906937, "element_max": 0.239650739442857, "element_rmse": 0.03454251208786517, "frobenius_mae": 0.07000986117478045, "frobenius_max": 0.2630277583492691, "phase_mae_deg": 3.197373788693038, "rows": 414}, "validation": {"element_mae": 0.008236780963961514, "element_max": 0.13586922750203834, "element_rmse": 0.015103106162214159, "frobenius_mae": 0.03666051751953862, "frobenius_max": 0.1659532732504151, "phase_mae_deg": 1.5111176218444726, "rows": 414}}, "HistGradientBoosting": {"test": {"element_mae": 0.01373252081741149, "element_max": 0.17982338227809205, "element_rmse": 0.030292969749816368, "frobenius_mae": 0.05814711765546387, "frobenius_max": 0.26434890700973174, "phase_mae_deg": 2.4449588894595906, "rows": 414}, "validation": {"element_mae": 0.006387007100362405, "element_max": 0.2013814588710587, "element_rmse": 0.012507974395794964, "frobenius_mae": 0.028799322458325737, "frobenius_max": 0.21021584658670892, "phase_mae_deg": 1.0400803786925201, "rows": 414}}, "SimpleMLP": {"test": {"element_mae": 0.020253159933162915, "element_max": 0.2401802560930576, "element_rmse": 0.03847512196979541, "frobenius_mae": 0.07388012225827721, "frobenius_max": 0.34629481787294575, "phase_mae_deg": 1.2458224484513523, "rows": 414}, "validation": {"element_mae": 0.009638672628273828, "element_max": 0.14649861011140497, "element_rmse": 0.01412712652086618, "frobenius_mae": 0.035275642866465326, "frobenius_max": 0.15190502982811138, "phase_mae_deg": 0.667814362162862, "rows": 414}}}.
- Round-1 baseline reference: {"Txx_mae": 0.01346836, "Tyy_mae": 0.02404161, "frobenius_mean": 0.04520755, "frobenius_p95": 0.09526959, "mae": 0.01025266, "phase_circular_mae_deg": 0.840166, "rmse": 0.01893506, "uncertainty_error_correlation": 0.6252}.

## Readiness and constraints

- Outcome: LP_ML_ROUND2_FORWARD_SURROGATE_READY_FOR_INVERSE_DESIGN_PLANNING.
- This is forward-surrogate readiness only; no inverse-design FDTD, Round-3, six-bin promotion, K6, D9, or old Batch2 was executed.
- Geometry 054 remains quarantined with zero admitted rows and no retry.
- Quality audit: {"complete_jones": true, "duplicate_geometry_hashes": 0, "duplicate_rows": 0, "geometry_054_generated": false, "inverse_design_fdt_authorized": false, "merged_geometry_count": 319, "merged_row_count": 2871, "model_filled_rows": 0, "prediction_before_retraining": true, "retrained_from_scratch": true, "round2_geometry_count": 64, "round2_row_count": 576, "round3_solver_authorized": false, "wavelengths_ok": true}.

## Tests

- Targeted Round-2 contract tests: 2 passed.
- Full repository pytest: 389 passed, 14 failed, 1 skipped. The 14 failures are pre-existing integrity/fixture failures: four tests still assert the superseded d0b9dc84 protected-report hash, and ten Stage12/Stage13 tests lack their unrelated fixture outputs. No Round-2 targeted test failed.

## Outputs

- Plan/contract: outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv/.json and lp_ml_dataset_v1_round2_execution_contract_v1.json.
- Physics staging: outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round2_active_learning_attempt1_v1/.
- Merge/metrics: outputs/lp_ml_dataset_v1/lp_ml_dataset_v1_round2_complete_319_geometry_2871_rows.csv and outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_*.
- Report: reports/lp_ml_round2_active_learning_and_readiness_v1.md.
