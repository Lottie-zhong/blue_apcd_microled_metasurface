# MDC-ML merge/retrain training execution contract refreeze v2

## Status

- Previous training thread stopped safely before fitting because execution semantics were not frozen.
- This revision freezes execution semantics before first training; `first_training_started=false`.
- No classifier/regressor fit, OOF, calibration, conformal, solver, TMM, FDTD, Lumerical, proposal generation, or sealed-test prediction was run.

## Provenance

- Superseded pretraining freeze: `afbd9eb526bf0003a693fdab6d1dbd1d9103c0cb`.
- Shared Surrogate v1 source commit: `182b0c284959120b612d218f7dddb2b56903231d`.
- V1 config SHA-256: `3325bca7a236df40fc9044b4c95cdba62f44f1753fa567ff30217f503c0e5b38`.
- V1 trainer SHA-256: `3ef3193c8339a7fc8eba08f7fece259037b1772f3a69b8952f3e1f7c53a1eafe`.
- V1 dataset-builder SHA-256: `18a08757b53996de05bff92dd4729953075ee2d5c0ffb404ef7c83134e40c296`.
- Promotion contract SHA-256 (preserved): `71b43c40035bb49a0a9647734b8aa4b42f7a089aa9c354de0b2a90f0c93def52`.
- Training execution contract SHA-256: `4cc187dc18f2e18bae32dc659d1ffad6f2baf0fa411c7214fa98db02645ce886`.
- Full merge/retrain config SHA-256: `76e51a802f598e458264c31db5b6024ade4a0e0a65f3ba2cc3c4587fcd74ade6`.

## Frozen execution semantics

- Candidate allowlists resolve every v1 classification and regression candidate; bounded recompetition equals those frozen sets.
- Baselines: `extra_trees_1` classifier and `multitask_mlp_3seed` regressor.
- Features: canonical 150 physics-only features; regression targets retain the canonical 4D order.
- Seeds: classifier/final seed `20260720`; MLP ensemble `[20260720, 20260721, 20260722]`; fold rule is explicit.
- Calibration uses original calibration only; threshold/model selection use original validation only; conformal uses original calibration eligible rows only.
- MLP early stopping is deterministic and excludes calibration, sealed test, and its held-out adaptive fold.
- Route precedence gives data-contract review exclusive priority; FDTD shortlist readiness never runs FDTD; Round 2 always requires a separate task.

## Resolved values and references

- `model_candidate_allowlist`: source `configs/mdc_ml_shared_surrogate_v1.yaml` plus `scripts/train_mdc_ml_shared_surrogate_v1.py`; classification candidates are `dummy_prevalence`, `dummy_stratified`, `linear_C_0.1`, `linear_C_1.0`, `linear_C_10.0`, `extra_trees_0`, `extra_trees_1`, `hgb_0`, `hgb_1`, and `multitask_mlp_3seed`; regression candidates are `dummy_mean`, `dummy_median`, `ridge_0.1`, `ridge_1.0`, `ridge_10.0`, `extra_trees_0`, `extra_trees_1`, `hgb_0`, `hgb_1`, and `multitask_mlp_3seed`. Full constructor parameters and per-candidate resolved-value SHA are in the config.
- `fixed_v1_architecture_retrain`: classifier `extra_trees_1` (384 trees, min leaf 2, max features 1.0, balanced classes) and regression `multitask_mlp_3seed` (hidden `[256,128]`, ReLU, dropout 0.1, AdamW, learning rate 0.0007, weight decay 1e-5, batch 128, maximum 240 epochs).
- `target_transforms`: ordered targets are spectral FWHM in nm, angular FWHM in deg, Cone-5 proxy, and normal-band-transmission proxy; 150 feature inputs use train-only StandardScaler with material tokens restored; eligible-target standardization is fit on training eligible rows only.
- `training_seeds`: classifier/final seed 20260720; regression seeds 20260720, 20260721, 20260722; fold and per-target seed derivations are explicit.
- `early_stopping`: strict validation-loss improvement by 1e-7, patience 35, maximum 240 epochs, restore best weights; calibration, sealed test, and the held-out adaptive fold are excluded.
- `route_rules`: data-contract review has exclusive precedence; retain/inconclusive maps proposal use to v1; shortlist readiness is capped at 12 and does not run FDTD; Round 2 remains separately authorized.

## Assurance

- Builder `--validate-only` validates source SHA/resolved-value SHA, candidate closure, targets, seeds, early stopping, route precedence, promotion invariance, and pretraining-zero-artifact state without writing outputs.
- The next authorized entry point is `MDC_ML_MERGE_RETRAIN_OOF_AND_DEVELOPMENT_TRAINING_V2`.
