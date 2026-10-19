# Checkpoint Provenance Report

## Check performed

Checkpoint files were loaded individually from the existing 272G analysis folders and checked against the 272G `FOLDS.json` and `COMPLEX_DATASET.npz`; no checkpoint was written or retrained. See `CHECKPOINT_CHECKS.csv` for each file and `CV_SPLIT_IDENTITY_CHECK.csv` for full fold identities.

### Results

- 52/52 serialized model checkpoints passed identity and train-only preprocessing checks: 24 ExtraTrees (Balanced and Leaf1, 4 folds × 3 seeds), 8 NN29 (4 × seeds 17/29), 4 Joint29 (4 × seed 43), 12 PSNet (4 × seeds 17/29/43), and 4 Ridge.
- Each checkpoint’s saved `train_ids` exactly matched the assigned fold; MLP and ET random states matched the manifest seed; MLPs had `warm_start=False`, `early_stopping=False`, and 300 iterations.
- Feature scaler means/variances matched independently calculated fold-train features to <1e-10. NN target-scaler means/variances matched fold-train labels to <1e-10. ExtraTrees Balanced scaling vectors matched the documented fold-train target statistics to <1e-12. Ridge feature transform was separately checked against its training-only transformed design matrix.
- No checkpoint from another fold was inherited. Each fit path constructs a new estimator in the fold loop; same-fold reuse is documented below and is not a cross-fold transfer.

## Reuse map

1. `FORWARD/Balanced_fold*_seed*.joblib` and `Leaf1_fold*_seed*.joblib`: 24 fit records. Later tree-aggregation and P_scale evaluations reuse saved same-fold Leaf1 predictions/checkpoints as a comparator.
2. `COMPLEX_ENSEMBLE_SHRINKAGE_V1/NN_fold*_seed(17, 29).joblib`: 8 fresh fold models; both are reused unchanged in `PSCALE_DECOUPLING_V1` to keep the NN2 candidate fixed.
3. `PSCALE_DECOUPLING_V1/Joint29_fold*_seed43.joblib`, `PSNet_fold*_seed*.joblib`, and `Ridge_fold*_seed0.joblib`: 20 new fixed fold fits. Metadata confirms train-only labels and scalers.
4. `609D_COMPLEX_FORWARD_DIAGNOSTIC_V1/PREPARE_AND_TRAIN.py` runs fresh estimators within each architecture/fold/seed loop (40 fit-ledger rows); it persists prediction arrays rather than reusing another fold’s fitted estimator. `ANALYZE.py` projects only the assigned fold’s original heldout124 identities.
5. `AL50_V2_FINAL_CLOSEOUT/MATCHED_156_FIT_LEDGER.json` contains 32 new family-purged reference fits with a fixed factory and same validation IDs. The closeout states this was for a comparable 156 reference, not tuning.

## OOF prediction provenance for the published NN2 values

`NN2_Joint_OOF.npz` has 124 unique case IDs. For each fold, two independently loaded NN29 checkpoints (seeds17 and29) were run on only the fold’s 21 wavelength rows per validation geometry. The resulting `C_hat` and `P_scale` matched saved seed predictions and matched the OOF artifact after seed averaging within 1e-12. Every validation ID is absent from the assigned checkpoint’s train IDs. Recomputed frozen-H2 results are P(+1) MAE=0.021560397887, 450 nm Spearman=0.679698402265; these agree with the reported pair.

## Training/convergence selection

The exact fitted targets in current 29D NN paths are Cartesian complex channels plus log(P_scale). The NN models use fixed 300 epochs and no early stopping; validation labels are not fed to the fit call or used to select an epoch. Validation/model comparisons do exist after fitting, which is covered separately in `VALIDATION_REUSE_RISK_REPORT.md`.
