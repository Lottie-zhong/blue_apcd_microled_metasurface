# APCD Coupling-ML 272G Data Leakage Audit

## Scope and authority

Independent read-only audit of the 272G development dataset, four fold manifests, 23 local-pair edges, two interaction squares, model fit scripts, serialized model checkpoints, training/fit ledgers, saved OOF outputs, and the 0.02156 / 0.680 summary. No FDTD, RCWA/FMM, refit, sealed-confirmation access, truth rewrite, or GPU Runner change occurred. The audit generated only this report package.

Dataset: `reports\coupling\APCD_COUPLING_AL50_COMPLEX_AWARE_PRODUCTION_V1\STAGE_50\COMPLEX_DATASET.npz`; 272 unique ordered geometries, 21 wavelengths (440–460 nm inclusive), `target29=(272,21,29)`, `C_hat=(272,21,7,2)`, `P_scale=(272,21)`. The 124 primary validation geometries are each present exactly once in OOF output.

Git at audit: branch `work/mdc-np-coupling-ml-v1`, HEAD `2cc687020e90ec4397e6cd4ed31efed59aaaf386`, ahead/behind `0	0`. Existing staged paths unchanged=True; pre-existing worktree status unchanged outside this audit folder=True. No commit or push.

## Fold and wavelength identity

The primary 124 are the original 32/31/30/31 grouped geometries. Per-fold validation identity matches exactly across the 156G `S0_S2/FOLDS.json`, AL16/172G `ML_UPDATE/FOLDS.json` (`heldout_old_ids`), VFIN matched-156/222G `MATCHED_156_FOLDS.json`, and 272G `STAGE_50/FOLDS.json`. Fold identities were recomputed from the lists, not accepted from `family_overlap` prose alone. All 272 geometries partition into train / heldout / purged sets for each 272 fold, and train vs heldout geometry intersections are zero.

The B29 pipeline expands a training geometry into 21 rows only after the geometry-level train indices are chosen (`repeat(D_train,21)` and `tile(wavelengths)`); it never splits wavelength rows independently. All 21 wavelengths for every geometry therefore follow the same role. The CSV exports every geometry and family role for every fold. Its summary rows include complete train IDs, primary validation IDs, all model-heldout IDs, purged IDs, and corresponding family-ID lists.

- Fold 1: train 216 geometries / 201 family IDs; primary validation 32 geometries / 30 family IDs; other heldout 14; purged 10; local family intersections 0. Full IDs are in the fold-summary rows and case rows of `CV_SPLIT_IDENTITY_CHECK.csv`.
- Fold 2: train 217 geometries / 202 family IDs; primary validation 31 geometries / 29 family IDs; other heldout 14; purged 10; local family intersections 0. Full IDs are in the fold-summary rows and case rows of `CV_SPLIT_IDENTITY_CHECK.csv`.
- Fold 3: train 208 geometries / 202 family IDs; primary validation 30 geometries / 29 family IDs; other heldout 23; purged 11; local family intersections 0. Full IDs are in the fold-summary rows and case rows of `CV_SPLIT_IDENTITY_CHECK.csv`.
- Fold 4: train 217 geometries / 202 family IDs; primary validation 31 geometries / 29 family IDs; other heldout 14; purged 10; local family intersections 0. Full IDs are in the fold-summary rows and case rows of `CV_SPLIT_IDENTITY_CHECK.csv`.

## Local-family audit

The current 272G manifest contains four connected components in `LOCAL_FAMILY_COMPONENTS.json`; all 23 local graph edges and both four-corner groups have their constituent identities present in the dataset. For every fold, every connected local component was independently checked for train∩heldout overlap: zero. When a local member is held out, the connected peers are either held out in that same fold or purged from training; none of the component’s labels cross into the fitting split. The two double-pillar groups are treated as four-case families, not as four independent geometries.

- INTERACTION_01 (K6GDP2_DEV_G059, LOCAL_FAMILY_04:K6GDP2_DEV_G059): all four corners present=True; saved 609D analysis says complete truth=True; fold roles={"1": ["TRAIN", "TRAIN", "TRAIN", "TRAIN"], "2": ["TRAIN", "TRAIN", "TRAIN", "TRAIN"], "3": ["PRIMARY_VALIDATION", "OTHER_HELDOUT", "OTHER_HELDOUT", "OTHER_HELDOUT"], "4": ["TRAIN", "TRAIN", "TRAIN", "TRAIN"]}. Cross-split family leakage=NO.
- INTERACTION_02 (K6V1_S31, LOCAL_FAMILY_03:K6V1_S31): all four corners present=True; saved 609D analysis says complete truth=True; fold roles={"1": ["PURGED", "PURGED", "PURGED", "PURGED"], "2": ["PURGED", "PURGED", "PRIMARY_VALIDATION", "PURGED"], "3": ["PURGED", "PURGED", "PURGED", "PURGED"], "4": ["PURGED", "PRIMARY_VALIDATION", "PURGED", "PURGED"]}. Cross-split family leakage=NO.

This protects ordinary unknown-geometry validation from a nearby local perturbation’s labels. Unknown-local-family generalization is a stricter question: the 23 edge measurements reduce to **two connected local families**, and the historical closeout identifies only **one eligible fully held-out predictive family** (G059). The S31 anchor is outside the primary124 validation (old32 train-role) and is purged in folds where related members are held out, so that quartet is not a complete independent family holdout. Thus group protection passes, but the local-family test sample is too small to support a broad claim.

## Preprocessing, fitting, and prediction audit

The current fit code constructs each model inside the fold/seed loop. The persisted checkpoints were loaded one at a time and checked against the fold’s full `train_ids`. Across **52 serialized checkpoints** (24 ET, 8 NN29, 4 Joint29, 12 PSNet, 4 Ridge), all checkpoint train IDs matched the assigned fold; model input and output scalers matched independently recomputed training-fold statistics; the 24 ET target reweighting vectors matched only the corresponding fold-training targets. All 52 checks passed. Fold validation IDs were disjoint from those training IDs.

MLP checkpoints have fixed 300 epochs, `early_stopping=False`, and `warm_start=False`; output scaling uses only fold training targets. `StandardScaler` inputs use only fold training features. ExtraTrees target scaling, where applied, is computed from fold training labels. There is no PCA, label-driven feature selection, or heldout-loss checkpoint selection in these 272G fit paths. KRR/Mean/ET/MLP specifications are preregistered rather than searched by an inner optimizer in the 40-fit 609D diagnostic. No validation target enters the model `.fit()` calls.

The 124 saved `NN2_Joint_OOF` predictions were reconstructed from the serialized fold/seed17+29 NN29 checkpoints. For every validation geometry, saved complex state and P_scale matched fresh checkpoint inference (maximum absolute discrepancy <1e-12); OOF ensemble arrays also matched the first-two-seed fold prediction artifacts (<1e-12). Each identity was scored once by its assigned fold and absent from that fold’s train IDs. The 0.02156 metric was recomputed through the frozen H2 decoder from those OOF C and P_scale arrays: **P(+1) MAE=0.021560397887** (saved 0.021560397887); **450 nm within-fold Spearman=0.679698402265** (saved 0.679698402265). This rules out train-prediction rows being mixed into these two reported values.

`PREDICTIONS_A/B.npz` contains predictions for all 272 rows per fold, including train rows. That is an intermediate prediction cache, not the OOF scoring set: the analysis projection selects only the matching fold’s `heldout_old_ids`. The standalone `NN2_Joint_OOF.npz` contains only the 124 validation IDs. Downstream consumers must use that OOF projection or its explicit fold case IDs, not score the full per-fold arrays.

## Historical reuse and final verdict

The 124 identities are fixed across 156G, 172G, 222G, and 272G. Repeated estimates on this same holdout are legitimate fold-wise OOF computations, but repeated inspection and model/aggregation comparison makes it a development validation set, not a final untouched test. Fit ledgers show repeated variants: 156G reduced-target exploration (449 initial fits plus 30 recovery fits); AL16/172G update 40 fits; 272G forward comparison 24 fits; 609D A/B diagnostic 40 fits; 272G ensemble 8 new NN fits; P_scale ablation 20 new fits; and a 32-fit matched-156 reference comparison. Checkpoint reuse occurs for same-fold baselines and the seed17/29 MLPs in later P_scale diagnostics; it is not cross-fold weight carryover.

There is also a concrete **adaptive validation-feedback path**: AL16 update code refits final estimators on all 172 geometries, which include the original 124, then computes candidate-pool predictions/disagreement from those final models. The next AL16/AL50 proposal code reuses that disagreement. Thus the old124 labels helped determine the later training-geometry acquisition distribution. This is not a direct same-case label in its own fold’s OOF fit, but it makes subsequent same124 performance estimates adaptively reused and potentially optimistic for untouched future cases.

### Requested verdicts

| Question | Verdict | Evidence-based meaning |
|---|---|---|
| A. Traditional leakage | **No direct fold leakage detected; adaptive feedback present** | No geometry overlap, no validation-label fit/scaler/early-stop path in the audited 272 models, and OOF predictions are checkpoint-reproducible. However, validation labels fed full-data models used for subsequent active-learning selection. |
| B. Local-family cross-contamination | **No train/heldout family overlap detected** | All four connected components were protected. Local-family generalization evidence remains narrow: one eligible full family holdout. |
| C. Repeated validation tuning bias | **Yes, material development-set selection risk** | Same124 repeatedly scored across stages and model/aggregation comparisons; the later acquisition pool was selected using models trained with those labels. This is not corrected by fold groupings. |
| D. 0.02156 / 0.680 as legal CV metrics | **Yes, qualified retrospective OOF metrics** | Both reproduce from checkpoint-backed, family-grouped predictions. Retain as historical development OOF scores only; do not present them as unbiased final generalization or a locked test. |
| E. New independent final evaluation | **Required** | Keep the old124 for development/continuity. Freeze model, preprocessing, selection policy, and predictions on previously untouched geometries before acquiring/revealing their truth. Score once under the existing frozen H1 contract; after reveal, that cohort becomes development data. No new truth was requested or generated in this audit. |

New solver runs=0; next batch authorization=0; sealed response access=0.
