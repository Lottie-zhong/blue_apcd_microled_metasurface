# LP_ML_DATASET_V1 Round-2 Targeted Active Learning

## Provenance exception

- Accepted exception: UNRECOVERABLE_DERIVED_REPORT_BYTE_IDENTITY_EXCEPTION_ACCEPTED.
- Protected report was not modified by this task. Task-start SHA256 was 171033e0d2c73865d0f8610e81d5a33de56d7deb79d8d38aa2f925f7e17e8321; final audit observed 9E46A7BD1927D65ADC3A9CF9192040E7D239B839ED516ADCD96870BF64BFCD02. This unresolved post-start drift was not overwritten.
- This is a governance exception, not a physics/data exception.

## Frozen pool and plan

- Feasible pool: 60,000 legal candidates generated from the frozen Round-1 five-seed ensemble.
- Frozen Round-2 plan: exactly 64 geometries, quotas HIGH_UNCERTAINTY=20, LOW_PHASE_AND_SIX_BIN_COVERAGE=16, PROJECTOR_FAVORABLE_TRADEOFF=12, BOUNDARY_AND_HIGH_GRADIENT=8, DIVERSITY_CONTROLS=8.
- Existing formal geometries and geometry 054 were excluded; no replacements or retries.

## Solver accounting

- Planned/entered/accepted: 64 geometries / 128 x-y subruns / 128 / 128.
- Spectral rows: 576 at 450.0鈥?54.0 nm, 0.5 nm spacing (9 wavelengths).
- Failed/quarantined/duplicate: 0/0/0. Geometry 054 generated/retried: no/no.
- No solver was run after the completed 128-subrun execution.

## Formal observable

Native-M1 weighted-G0 Jones contract remained unchanged: transmission-side field monitor at z=1000 nm, full-period coordinate-weighted complex-field G0, periodic endpoint deduplication/reclosure, and sqrt(T)/norm(weighted Ex,Ey) normalization.

## Prospective frozen Round-1 evaluation

Evaluation was completed before merged-data retraining, with bounded geometry 054 excluded:
- rows=576; element MAE=0.04004816; element RMSE=0.07635568; element max=1.00629570;
- Frobenius MAE=0.17927091; Frobenius max=1.02351501; phase MAE=2.41621581 deg;
- ensemble uncertainty mean/P95=0.03697617/0.05969892.

## Merge and composite-loss retraining

- Merged complete dataset: 319 geometries / 2871 rows.
- Round-1 split was retained; Round-2 was grouped as 48 train / 8 validation / 8 permanent external test geometries.
- HGB, ExtraTrees, SimpleMLP, and five residual-MLP seeds were trained from scratch; warm_start=false.
- Residual-MLP architecture: 7鈫?56, four residual SiLU/LayerNorm blocks, dropout=0.03, output=8.
- Loss/config frozen from Round-1: raw SmoothL1 + 0.25 relative-Jones + 0.10 power + 0.05 rank + 0.05 projection + 0.05 circular-phase; AdamW lr=3e-4, weight_decay=1e-4, batch=64, max_epochs=500, patience=50, gradient_clip=1.0.
- Fresh 5-seed ensemble combined test (414 rows): element MAE=0.01459611, RMSE=0.02634404, max=0.22381583; Frobenius MAE=0.06453597, max=0.23239295; phase MAE=1.36557681 deg.
- Round-1 test subset (342 rows): element MAE=0.01251213, RMSE=0.02291597, max=0.22381583; Frobenius MAE=0.05620735, max=0.23239295; phase MAE=1.10384838 deg.
- Round-2 external test subset (72 rows): element MAE=0.02449497, RMSE=0.03867978, max=0.16805831; Frobenius MAE=0.10409692, max=0.21032190; phase MAE=2.60878682 deg.
- Tree/simple models remain recorded in the machine-readable metrics JSON; the residual 5-seed ensemble is the selected forward surrogate.

## Readiness and constraints

- Outcome: LP_ML_ROUND2_FORWARD_SURROGATE_READY_FOR_INVERSE_DESIGN_PLANNING.
- This is forward-surrogate readiness only. No inverse-design FDTD, Round-3, six-bin promotion, K6, D9, Batch B, or old Batch2 was executed.
- Geometry 054 remains excluded with zero admitted rows and no retry.
- Quality audit confirms complete Jones, duplicate geometry hashes/rows=0, model_filled_rows=0, wavelengths valid, and no later solver authorization.

## Tests

- Targeted Round-2 contract tests: 2 passed.
- Full repository pytest: 389 passed, 14 failed, 1 skipped. The failures are unrelated pre-existing protected-report hash/fixture failures; no Round-2 targeted test failed.

## Outputs

- Plan/contract: outputs/lp_ml_dataset_v1/plans/lp_ml_dataset_v1_round2_64_candidate_plan_v1.csv/.json and lp_ml_dataset_v1_round2_execution_contract_v1.json.
- Physics staging: outputs/lp_ml_dataset_v1/staging/lp_ml_dataset_v1_round2_active_learning_attempt1_v1/.
- Merge/metrics: outputs/lp_ml_dataset_v1/lp_ml_dataset_v1_round2_complete_319_geometry_2871_rows.csv and outputs/lp_ml_dataset_v1/analysis/lp_ml_round2_*.
- Report: reports/lp_ml_round2_active_learning_and_readiness_v1.md.

