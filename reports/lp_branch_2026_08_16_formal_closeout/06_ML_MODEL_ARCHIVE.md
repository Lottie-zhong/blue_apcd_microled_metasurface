# LP-ML model archive

All model artifacts below are historical and archived. No model was trained in this closeout (`ml_training_delta=0`).

- Round-1: five-seed residual MLP, 7 inputs to 8 raw Jones Re/Im outputs; four residual SiLU/LayerNorm/dropout blocks; AdamW; geometry-level split. Clean v1: 255 geometries / 2295 rows. Report: `reports/lp_ml_dataset_v1_round1_complete_255_audit_v1.md`.
- Round-2: clean-v2 recompetition; C0/C1 validation-only blend alpha=0.95, no warm start, no solver. Clean-v2: 319 geometries / 2871 rows. Report: `reports/lp_ml_round2_clean_recompetition_v2.md`.
- Round-2 active learning: 60,000 legal candidate pool; fresh five-seed residual-MLP; selected forward-surrogate archive. Report: `reports/lp_ml_round2_active_learning_and_readiness_v1.md`.
- Round-3: clean-v3 377 geometries / 3393 rows; 58 complete R3 geometries; six deterministic coverage gaps. Selected `OLD_C5_BLEND_0.95`; global calibration did not satisfy the stronger dispersion target. Report: `reports/lp_ml_round3_targeted_active_learning_final_audit_v1.md`.
- Surrogate-only six-bin search: 508 candidates, 103 tuple-front entries; all six selected candidates were high model-disagreement risk. Report: `reports/lp_ml_round3_six_bin_inverse_search_v1.md`.
- Inverse Stage-I: raw tuple space 38,880; phase-grid RMS 94.3273 deg; `LP_ML_INVERSE_STAGE1_FIVED_SPACE_INSUFFICIENT_EVIDENCE`. Report: `reports/lp_ml_inverse_stage1_physics_closure_v2.md`.

Limitations: local-dimer data and full-K6 data are not interchangeable; surrogate predictions are not physics rows; geometry 054 is exact-hash quarantined with zero admitted rows; no stable broadband coupled K6 manifold was established.
