# V3-C final full-development completion report

- Status: `MDC_HF_SURROGATE_V3_C_FINAL_5SEED_FULL_DEVELOPMENT_MODEL_FROZEN`
- Model: `MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1` / V3-C
- Membership: 200 geometries / 1200 cases / exactly 6 cases per geometry
- Shared preprocessing: PCA32 fit count 1; input scaler fit count 1; shared by all five seeds
- Final fits: seeds 20260813–20260817, exactly 117 epochs each; no validation, early stopping, checkpoint selection, or seed pruning
- Ensemble: equal arithmetic mean of five decoded normalized profiles; disagreement diagnostic only
- Fresh-load replay: two independent processes, individual and ensemble hashes identical
- V3-Test40: sealed, labels/truth not generated/read; HF15/R12 not read
- Solver calls: 0 in this task; neural fits: 5; PCA/scaler fits: 1/1
- Scope: ranking/screening-only; inherited KNOWN_FAILURE_LEVEL_STRATUM_WARNING
