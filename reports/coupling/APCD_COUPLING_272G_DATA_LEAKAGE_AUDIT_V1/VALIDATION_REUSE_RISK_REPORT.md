# Validation Reuse Risk Report

## Fixed validation identities

The same 124 ordered geometries, partitioned 32/31/30/31, are used in the 156G, 172G, matched 222G, and 272G evaluations. Fold membership matches by identity across the original S0/S2 folds, AL16 heldout-old manifest, VFIN matched-156 folds, and current 272G source folds. This gives strong longitudinal comparability but not a fresh test.

| Data stage / evidence | Model work and use of the same124 | Risk |
|---|---|---|
| 156G | 449 initial reduced-target fits plus 30 fixed recovery fits; modal inner selections were used for later final-model choices. Outer results were reported on the same124. | Earlier exploration increases repeated-look risk; not the source of current NN2 parameter weights. |
| 172G / AL16 update | 40 fixed-model fold fits; old124 OOF was compared before/after. Then separate models were refit on all172 (including old124) to generate full-pool disagreement for candidate selection. | Direct adaptive validation-feedback path into subsequent acquisition design. |
| 222G | Same124 retained for learning-curve / matched baseline comparisons; local family protection retained. `MATCHED_156_FIT_LEDGER.json` records32 fixed-factory fits. | Repeated score inspection; not an independent confirmatory set. |
| 272G | `FORWARD` 24 candidate fits, `609D` 40 fits, `COMPLEX_ENSEMBLE` 8 fresh NN fits, `PSCALE` 20 fresh fits (plus same-fold reused models); all use same124. | Candidate/aggregation selection on reused CV evidence; explicit `PSCALE` preregistration says heldout choice is development evidence, not nested test. |

## Direct leakage versus adaptive reuse

### Direct fold leakage: not found in audited 272 paths

- Exact geometry labels are partitioned before adding wavelength rows.
- All 21 wavelength rows remain in one geometry fold.
- Four local-family components have zero train/heldout intersections in every fold.
- Fit methods use fold training IDs only; input/output scalers and ET target scaling were numerically matched to training-only statistics in 52 serialized models.
- The NN2 OOF predictions are checkpoint-reproducible; the 124 validation labels do not occur in their assigned models’ train IDs. No training prediction is included in the scored OOF artifact.

### Adaptive validation-feedback / repeated-look risk: present

`AL16_ML_UPDATE_SOURCE.py` lines 43–53 constructs fold OOF predictions, while lines 63–72 then fit final candidate-selection models on `np.arange(172)` and use those full-data model predictions to calculate candidate disagreement. The first 156 entries include the original 124 validation geometries. `AL50_SELECTION_AND_SETUP_SOURCE.py` lines 41–55 reuses the saved disagreement to choose AL50 cases. Therefore the old124 labels helped shape the next training cohort. Later fixed124 OOF predictions still exclude the case’s own label from its fold fit, but their evaluation is conditioned on a sample-acquisition process informed by the holdout labels.

Across 156→172→222→272, the same split supported repeated model comparison, aggregation choices, and later OOF re-evaluations. Fixed preregistration and no inner search reduce some researcher degrees of freedom; they do not restore independence after outcomes have been inspected or used for acquisition. The resulting bias magnitude cannot be quantified reliably from the existing artifacts alone.

## Status of the two headline metrics

`P(+1) MAE=0.021560` and `450 nm Spearman=0.679698` are correctly computed grouped OOF development metrics for NN2 on 124 geometries. They remain useful for retrospective comparison on the same frozen split and for tracking changes with identical protocol. They should be labeled **reused/adaptive development CV**, not an independent test score, unbiased expected generalization, or final H1 proof.

## Zero-solver remedy

1. Keep the 124 identities and all visible historical scores as development-only; never rebrand them as final test.
2. Freeze the exact model family, preprocessing, training data inclusion rule, and selection policy before any new final truth is obtained.
3. Use the existing frozen H1 prospective protocol only if its six geometry identities are confirmed never trained on, inspected for target outcomes, used for active selection, or used for model choice. Persist model artifact and predictions before truth acquisition/reveal; no truth-based repair or retuning on that cohort.
4. If those identities have already been exposed or adaptively selected, reserve a new, independently selected cohort under a separate user-authorized solver budget. The current audit did not create or spend that budget.
5. Report per-case metrics, uncertainty interval over geometries/families (not 21 wavelengths as independent replicates), and the fact that the cohort is a prospective finite check, not a universal six-dimensional guarantee. Once scored, it becomes development data for subsequent iterations.

New solver runs=0; next batch authorization=0; sealed response access=0.
