# APCD_COUPLING_SIMPLE_FORWARD_SURROGATE_S0_S2_V1

Status: COMPLETE / EXPLORATORY_TASK_LEARNABILITY_ONLY.

5 nm / 3 ps HF numerical reliability remains unresolved. This study measures predictability of the current legal dataset and cannot certify final physics or production H1.

## Data and validation

156 unique legal development geometries:113 global+11 local-axis+32 old. Reused the approved identity-gated 156 loader and frozen H2. Old32 always train-only due prior exposure; fixed outer folds hold out32/31/30/31 new geometries,124 total. Three inner geometry folds select the small grids; all scalers fit training only. Every wavelength of one geometry stays together. Confirmation32 and DOE56 responses were not read.

S0:450nm eta(+1),P_scale,P(+1)_H2 directly predicted as3 outputs. S2:exact6-32-32-42 MLP or multioutput KRR predicts eta(+1)[21]+P_scale[21]; derived P(+1)=predicted eta*predicted P_scale is compared with frozen H2 truth. This is not a new H2 decoder or a609D state predictor. Existing609D/H1/H2 files and old fit ledger have zero Git diff.

Native eta*P_scale vs H2 P(+1) maximum discrepancy=0.000162034. This small extraction distinction is retained.

## 450nm results

Top-k ties use fractional cutoff inclusion; a constant predictor has the random selection expectation. The initial tie-report bug was corrected from cached predictions with zero new fits and preserved originals. Pooled OOF error is descriptive; ranking below uses mean of four within-fold Spearman/recall values. Constant Mean has undefined within-fold rho. Top20% random-reference recall is about0.2; finite folds use ceil(20%*n).

|Target/model|eta MAE|eta fold rho|Pscale MAE|P+1 MAE|P+1 fold rho|P+1 top20 recall|
|---|---:|---:|---:|---:|---:|---:|
|scalar/Mean|0.0954|N/A|0.0850|0.0656|N/A|0.2176|
|scalar/kNN|0.0996|-0.1196|0.0817|0.0676|-0.1103|0.1071|
|scalar/KRR|0.0984|-0.0692|0.0781|0.0666|-0.0572|0.2202|
|scalar/GPR|0.1049|-0.0616|0.0879|0.0721|-0.0922|0.2143|
|scalar/MLP|0.0956|-0.0631|0.0801|0.0653|0.0007|0.2917|
|scalar/MLP_Adam_recovery|0.1206|-0.0833|0.1116|0.0807|-0.0435|0.2917|
|spectral/Mean|0.0954|N/A|0.0850|0.0657|N/A|0.2176|
|spectral/kNN|0.0996|-0.1196|0.0817|0.0677|-0.1010|0.1071|
|spectral/KRR|0.0984|-0.0692|0.0781|0.0664|-0.0147|0.1845|
|spectral/MLP|0.0999|-0.1185|0.0768|0.0674|-0.0966|0.0714|
|spectral/MLP_Adam_recovery|0.1324|-0.0235|0.1244|0.0869|0.0094|0.3333|

## 440–460nm spectra

|Model|eta MAE/RMSE|Pscale MAE/RMSE|H2 P+1 MAE/RMSE|
|---|---:|---:|---:|
|Mean|0.0987/0.1280|0.0533/0.0730|0.0313/0.0487|
|kNN|0.1013/0.1312|0.0515/0.0730|0.0322/0.0502|
|KRR|0.1000/0.1301|0.0488/0.0688|0.0315/0.0493|
|MLP|0.1009/0.1315|0.0509/0.0715|0.0319/0.0499|
|MLP_Adam_recovery|0.1333/0.1725|0.0719/0.1010|0.0413/0.0623|

Per-wavelength errors, fold metrics, unclipped physical-range violations and seed results are retained in RESULTS.json. METRICS_450NM.csv includes geometry-bootstrap paired MAE gains; PER_GEOMETRY_ERRORS.csv includes role, nearest training distance and error. Local11/global113 strata are descriptive, not independent folds.

## Stability and CPU cost

|Target/model|Estimator fits|Fit seconds|Warning fits|Abnormal fits|
|---|---:|---:|---:|---:|
|scalar/Mean|5|0.015|0|0|
|scalar/kNN|41|0.146|0|0|
|scalar/KRR|113|0.420|0|0|
|scalar/GPR|53|0.246|0|0|
|scalar/MLP|39|10.325|22|18|
|spectral/Mean|5|0.012|0|0|
|spectral/kNN|41|0.099|0|0|
|spectral/KRR|113|0.331|0|0|
|spectral/MLP|39|2.593|39|39|
|scalar/MLP_Adam_recovery|15|16.427|15|0|
|spectral/MLP_Adam_recovery|15|17.954|15|0|

Initial449 estimator fits are retained. LBFGS abnormal termination motivated a preregistered fixed Adam recovery:30 fits, same architecture/folds,1500 full-batch epochs,lr0.003,alpha0.001,seeds17/29/43,no outer early-stop or grid. Recovery is a post-failure exploratory extension, not independent confirmation. Adam max-iteration warnings reflect the fixed budget, not a convergence certificate. Both optimizer results are reported; no clipping or outer-guided retuning.

Final all156 models are persisted; final hyperparameters use modal inner selections, with all three MLP seeds. Reload predictions are exact. ERROR_AND_RANKING_ANALYSIS.json includes per156-batch inference times; no claim of calibrated uncertainty or reliable extrapolation is made.

## MLP seed stability

|Target/optimizer|Training RMSE mean|Ensemble OOF RMSE|Seed OOF RMSE min–max|Mean prediction SD|
|---|---:|---:|---:|---:|
|scalar/MLP|0.09962|0.10954|0.10945–0.10960|0.00044|
|scalar/MLP_Adam_recovery|0.00351|0.13950|0.14350–0.16820|0.05702|
|spectral/MLP|0.09471|0.10584|0.10597–0.10617|0.00554|
|spectral/MLP_Adam_recovery|0.01864|0.14136|0.16741–0.17297|0.07344|

The Adam recovery lowers training error while increasing heldout error and seed dispersion. Thus its poor validation cannot be explained solely by the LBFGS abnormal-exit issue. This is evidence of failed generalization under the tested training setup, not proof that no model can learn the physics.

Total estimator fit time: 48.568 seconds of summed wall-clock fit time on CPU (two threads) for479 fits, excluding loading, reporting, serialization and SSH latency.

## Scientific interpretation

A. 450nm eta(+1) and P(+1): current grouped validation does not demonstrate useful learnability; P_scale has limited error reduction. Tiny best P(+1) gain overlaps zero in the paired geometry bootstrap.

B. Full42D: P_scale spectra contain some learnable structure, but eta/P(+1) do not show stable mean-baseline gains; the joint42D task is not established as useful.

C. KRR is a low-cost reproducible reference with modest P_scale improvement. Fixed-grid GPR does not improve the main targets. LBFGS MLP has optimizer failures; fixed Adam removes abnormal exits but does not yield robust generalization. No universally effective model is demonstrated.

D. Unknown K6 ranking is not reliable: fold Spearman is near zero or negative, and top20 recall is variable. A positive top-k hit rate alone does not override poor full ranking. No sealed confirmation or extrapolation test supports production ranking.

E. Prioritize numerical credibility and lawful coverage/data-quality review before surrogate-driven optimization. This experiment gives no basis for jumping directly to a larger ML or more complex physics model. Any new data or solver work remains separately unauthorized.

## Boundaries and reproducibility

FDTD0;RCWA/FMM0;replay0;confirmation response access0;DOE56 diagnostic rows0;GPU Runner edits0;inverse production0. No scientific solver budget was enlarged. Input orderingD1…D6, wavelengths440…460, H2 reference/decoder and H1 thresholds are unchanged. The reduced target model cannot be used to claim full complex609D/H1 certification.

Source: scripts/coupling_ml/simple_forward_surrogate_s0_s2_v1.py, corresponding recovery_v1.py, analysis_v1.py and reporting_fix_v1.py. PREREGISTRATION.json, OPTIMIZER_RECOVERY_PREREGISTRATION.json, FOLDS.json, DATA_AUDIT.json, both fit ledgers and model manifests reproduce the bounded experiment. PCA-KRR was optional and omitted.

One attempted SSH background launch exited before preregistration or fit entry; INITIAL_BACKGROUND_LAUNCH.json preserves this. The SSH foreground run completed; recorded estimator fits were not replayed.

Git:work/mdc-np-coupling-ml-v1;HEAD2cc687020e90ec4397e6cd4ed31efed59aaaf386;ahead/behind0	0. Worktree remains dirty; original four staged files preserved. No commit/push was performed for this task.
