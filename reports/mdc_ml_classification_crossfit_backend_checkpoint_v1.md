# MDC-ML classification crossfit backend checkpoint v1

Parent backend checkpoint: `b083ab3a5368eedd14ecfbb16e2a593915014a0f`.

Remote-first implementation adds a synthetic-only classification crossfit backend. The formal metadata interface reads registry and frozen assignment metadata without reading target arrays. It validates the frozen target order, 150-feature signature, 128 Round1 rows and frozen four-fold assignment.

Each synthetic fold uses only original train plus the other three Round1 folds for fitting the frozen `extra_trees_1` baseline. The scaler is train-only and restores material-token indices. Calibration uses original calibration with Shared v1 sigmoid/isotonic selection; thresholds use original validation and Shared v1 97-quantile, balanced-accuracy/F1/0.5 tie logic. Held-out labels are used only in final synthetic OOF records.

Atomic fold artifacts, deterministic CSV/JSONL OOF, manifest validation, and fixture audit are produced only below system TEMP. The synthetic fixture uses actual ExtraTrees/scaler/calibrator/threshold operations and validates exact-once coverage plus artifact reload.

Formal classification OOF was not started. Regression, MLP, conformal, bootstrap, promotion, routing, proposal, TMM, FDTD and Lumerical were not invoked. Sealed test targets/predictions and official merge/retrain outputs remain unused.

`CLASSIFICATION_CROSSFIT_BACKEND_FROZEN=true`

`FORMAL_CLASSIFICATION_OOF_STARTED=false`

`FULL_TRAINER_IMPLEMENTATION_FROZEN=false`

`FORMAL_TRAINING_STARTED=false`

Next module: `MDC_ML_REGRESSION_THREE_SEED_CROSSFIT_CONFORMAL_BACKEND_V1`.
