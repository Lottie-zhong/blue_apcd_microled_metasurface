# APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1

**PASS — approved execution completed.** Scientific model verdicts: `{"RBF_KRR": "DEVELOPMENT_H1_FAIL", "CARTESIAN_MLP": "DEVELOPMENT_H1_FAIL"}`. No independent confirmation, production surrogate admission, inverse-design or dipole validation is claimed.

## Frozen scope and execution

156 unique development groups: old32 + local11 + global113. Original160G/V2 authority retained; approved version COUPLING_K6_V2_DEVELOPMENT_156G_AMENDMENT_V1 binds closure inventory SHA `9e2687d61496850bca4f79b5fb24d20f446f47b56944c7a69edb127757a38403`. Source truth/label/native FSP/H5 byte hashes rechecked before first fit. Actual legacy S16 attempt002 preserved; S35 failed and recovered provenance remain separate. Historical old32 EXT02 is legal; independent diagnostic EXT02, queue21, reserve, four failed attempts and confirmation responses excluded.

268/268 logical CPU fits complete, no failed or extra fit:108innerKRR+108innerMLP+12curveKRR+36curveMLP+1finalKRR+3finalMLP. Internal KRR state/log-P heads belong to one logical joint fit; standalone P_scale fits0. Actual MLP optimizer updates `28857`. Summed per-fit wall time 1793.9s; original worker through report-serialization exit 1831.7s. Solver0, GPU FDTD0, replay0, local0, NP0, confirmation-response accesses0; synthetic model fits0.

Interpreter N:\anaconda_envs\RCP_LCP\python.exe, Python3.10.20, torch2.5.1+cu121, numpy2.2.5, scipy1.15.3, sklearn1.7.1. CUDA hidden, execution CPU two threads. Torch/CUDA not reinstalled. Exclusive task CPU owner claim archived after exit. All268 fits succeeded; the worker subsequently exited on NumPy int64 report serialization. Original failed exit receipt and traceback are preserved. A zero-fit evaluation recovery loaded52 completed refit/final checkpoints, reproduced primary metrics byte-for-byte, and finished evaluation. The zero-error energy-share reporting edge and NumPy scalar serialization were fixed after training; all six original/fixed actual prediction diagnostics have exact numerical parity. Original execution source freeze retained, with versioned post-fit reporting fix evidence. Engine checkpoint every optimizer update; all268 fitted models independently saved/reloaded with exact prediction equality and rehashed. Full models/preprocessors/predictions/trajectories retained outside Git; SHA inventory records durable files. Original foreign working/staged states preserved.

## Validation and training sizes

Four fixed survivor outer validation groups32/31/30/31 (total124), all new development identities:113global+11local. Old32 remain outer-training-only and historically exposed; they can appear in original inner validation groups. Outer train124/125/126/125. Inner memberships unchanged except missing IDs removed. Full21-wavelength response belongs to one geometry group. Inner preprocessing fitted only corresponding inner-train; each refit preprocessing only its32/64/124 groups. Hyperparameters and fixed MLP epochs selected only using corresponding outer-train3-fold inner CV.

32/64/124 are **actual refit counts**, not total response budgets: all levels see the same124–126 outer-train groups during configuration selection. Fixed outer evaluation identity at every size; training subsets nested and response-blind frozen. Max124 curve leaves0/1/2/1 outer-train groups unused for refit; all included in applicable inner search and final156 fits. Not exactly comparable to hypothetical160G/128 or old65G's different validation IDs. Matched within-run curves are primary evidence of sample-size effect, not cross-experiment causal claims or wavelength-times-seed independent statistics.

## Original H1/H2 results

| Model | Refit G | State med/q95 | Routing med/q95 | Routing r | Absolute med/q95 | Thresholded relative med/q95 | P_scale/total med/q95 | Power r | Norm ratio med | Seed std | Gates |
|---|---:|---|---|---:|---|---|---|---:|---:|---|---|
| RBF_KRR | 32 | 0.950782/1.228374 | 0.246586/0.335596 | 0.425787 | 0.090336/0.131082 | 0.853509/0.947179 | 0.277642/0.784160 | 0.903235 | 0.596048 | N/A | state:FAIL, routing:FAIL, absolute_order:FAIL, thresholded_absolute_order:FAIL, total_power:FAIL, seed_stability:N/A |
| RBF_KRR | 64 | 0.911116/1.135174 | 0.205125/0.319431 | 0.448417 | 0.076065/0.124365 | 0.829640/0.942808 | 0.260980/0.795739 | 0.899341 | 0.527618 | N/A | state:FAIL, routing:FAIL, absolute_order:FAIL, thresholded_absolute_order:FAIL, total_power:FAIL, seed_stability:N/A |
| RBF_KRR | 124 | 0.872970/1.086444 | 0.182086/0.297147 | 0.470601 | 0.064621/0.115201 | 0.801501/0.937560 | 0.248064/0.757838 | 0.904588 | 0.507299 | N/A | state:FAIL, routing:FAIL, absolute_order:FAIL, thresholded_absolute_order:FAIL, total_power:FAIL, seed_stability:N/A |
| CARTESIAN_MLP | 32 | 0.991845/1.227410 | 0.292074/0.363337 | 0.398018 | 0.100105/0.139103 | 0.904839/0.960339 | 0.303008/0.890486 | 0.929806 | 0.601230 | 0.002618 | state:FAIL, routing:FAIL, absolute_order:FAIL, thresholded_absolute_order:FAIL, total_power:FAIL, seed_stability:PASS |
| CARTESIAN_MLP | 64 | 0.920877/1.162605 | 0.280927/0.375409 | 0.407245 | 0.098453/0.144854 | 0.913786/0.972284 | 0.259804/0.826517 | 0.928285 | 0.495618 | 0.002656 | state:FAIL, routing:FAIL, absolute_order:FAIL, thresholded_absolute_order:FAIL, total_power:FAIL, seed_stability:PASS |
| CARTESIAN_MLP | 124 | 0.923843/1.109628 | 0.274689/0.373825 | 0.416899 | 0.096554/0.142925 | 0.911368/0.972487 | 0.245158/0.778914 | 0.931426 | 0.448574 | 0.003603 | state:FAIL, routing:FAIL, absolute_order:FAIL, thresholded_absolute_order:FAIL, total_power:FAIL, seed_stability:PASS |

P_scale and total-power metrics are identical by frozen decoder definition: total_power=physical predictedP_scale; routing is normalized modal powers and absolute_order=routing*P_scale. This identity is not independent power validation. Full state errors use raw predicted C_hat without phase alignment, norm rescaling, clipping or projection. C_hat three-seed complex mean, P_scale physical arithmetic mean after per-seed log inverse/exp; original per-seed metrics and mean-norm change retained.

### RBF_KRR

124G held-out state median/q95 0.872970/1.086444; zero-prediction state baseline1. Norm ratio median 0.507299. Matched124-minus32 state median delta -0.080633: 102 geometry wins/22 losses. Fold deltas: `{"1": {"median": -0.08904717894694025, "q95": 0.06319761342611759, "worst": 0.11955859995335716, "mean": -0.11120371878296467}, "2": {"median": -0.08919819476580415, "q95": 0.10198021826242443, "worst": 0.22820737732999086, "mean": -0.09140853211876902}, "3": {"median": -0.0888520282979699, "q95": 0.015109591796477749, "worst": 0.07525293893032503, "mean": -0.10767791627876694}, "4": {"median": -0.0671463127250026, "q95": 0.03158973099253398, "worst": 0.06758517158989008, "mean": -0.09150158156676713}}`.

Worst state geometry K6GDP2_DEV_G009 (DEEP_INTERIOR), error 1.156564. Worst wavelength diagnostic `{"case_id": "K6GDP2_DEV_G078", "wavelength_nm": 457, "relative_RMSE": 1.2570282039627358}`; worst order diagnostic `{"case_id": "K6GDP2_DEV_G100", "m": 0, "relative_RMSE": 2.958835027334126}`. State-error energy fractions orders m=-3..3: `[0.13867694932048827, 0.15218247141653388, 0.1549581678528945, 0.14080573978108193, 0.15208386822154363, 0.13461394214355085, 0.1266788612639066]`; TE/TM: `[1.2052186387309983e-09, 0.99999999879478]`. Truth-weighted significant absolute-phase RMSE median 1.220526rad; relative-phase median 1.721010rad.

124G gates: `{"state": false, "routing": false, "absolute_order": false, "thresholded_absolute_order": false, "total_power": false, "seed_stability": null}`; final status DEVELOPMENT_H1_FAIL. All gates retain original numeric authority; deterministic KRR seed stability N/A.

### CARTESIAN_MLP

124G held-out state median/q95 0.923843/1.109628; zero-prediction state baseline1. Norm ratio median 0.448574. Matched124-minus32 state median delta -0.056028: 93 geometry wins/31 losses. Fold deltas: `{"1": {"median": -0.06271564202974128, "q95": 0.057666317369335696, "worst": 0.08866509023312719, "mean": -0.07610988224338924}, "2": {"median": -0.051052104036179324, "q95": 0.1646464520246299, "worst": 0.24415201856954016, "mean": -0.053842326667814494}, "3": {"median": -0.052778415344404306, "q95": 0.0596943354768326, "worst": 0.11757865648426136, "mean": -0.07108690171017988}, "4": {"median": -0.06200958713075688, "q95": 0.04255196969566555, "worst": 0.09829365028239201, "mean": -0.08057772157819838}}`.

Worst state geometry K6GDP2_DEV_G009 (DEEP_INTERIOR), error 1.239919. Worst wavelength diagnostic `{"case_id": "K6GDP2_DEV_G088", "wavelength_nm": 446, "relative_RMSE": 1.3135461047543675}`; worst order diagnostic `{"case_id": "K6GDP2_DEV_G100", "m": 0, "relative_RMSE": 3.0879838818543357}`. State-error energy fractions orders m=-3..3: `[0.12940045375738876, 0.14546247619169164, 0.17065002498662882, 0.14604842907005955, 0.15460866874548573, 0.1376195744737271, 0.11621037277501946]`; TE/TM: `[0.0001884813423846657, 0.9998115186576163]`. Truth-weighted significant absolute-phase RMSE median 1.535195rad; relative-phase median 1.819352rad.

124G gates: `{"state": false, "routing": false, "absolute_order": false, "thresholded_absolute_order": false, "total_power": false, "seed_stability": true}`; final status DEVELOPMENT_H1_FAIL. All gates retain original numeric authority; deterministic KRR seed stability N/A.

## Failure-mode interpretation and limitations

Per-geometry, wavelength, order, TE/TM, role and boundary-stratum outputs are retained. Phase diagnostics use preregistered per-wavelength truth significance>=1e-4, truth-amplitude-squared weights and separately prediction-dependent weights; weight changes do not prove phase improvement. Relative phase compares all order pairs within each polarization; no oracle common-phase alignment. Very weak TE fields can have large relative errors without dominating state-energy error. Actual observations are numerical deltas/norms/phase/routing; sparse-coverage, rapid phase variation, regularization/optimization and representation explanations are hypotheses, not causal proofs.

Training errors versus held-out results are separately in TRAIN_VS_HELDOUT_DIAGNOSTIC.json. Lower training error alone is not generalization. No architecture/width/rank/loss/seed/config expansion was performed in reaction to outer results. Existing finite RBF KRR grid and21377-parameter6->32->32GELU Cartesian MLP unchanged, full588real Cartesian coordinates plus21logP_scale, no rank2PCA. Positive finite P_scale truth required; noepsilon/clipping; train-only shared state residualRMS/log statistics and original L_C+L_P objective.

Original13 local fits remain SUSPENDED (missingD6_M05; original six-dimensional LOAO rank deficiency); localconfirmation4 unopened. All32 confirmation responses sealed. Both final global candidates fit all156 groups, and geometry-only predictions for27core+1stress were frozen with model/preprocessor/evaluator SHA. These are predictions awaiting separate confirmation HF/evaluation authority, not validated responses. NP88D paired65G twoKRR experiment remainsPENDING and is not included in268. FixedMDC not retrained; complexLF residual still unavailable until LF/HF contracts align.

## Minimal next proposal — do not execute

Review the matched124G state/phase/norm andpower evidence first. If originalH1 remains failed, consider the already frozen65G geometry-only versusNP88D twoKRR paired experiment as a limited physics-feature test; do not treat it as156G confirmation. A156G feature experiment needs its own frozen matched protocol and authorization. No extraHF merely to pad160G, no network expansion or complexLF residual here. Independent confirmation remains a separate decision after reviewing these development results.

## Recovery and artifacts

Read CONTINUATION.md, SCIENTIFIC_AUTHORIZATION.txt, DEVELOPMENT_156G_AMENDMENT_V1.json, EXECUTION_SOURCE_FREEZE.json and APPROVED_268_FIT_MANIFEST.json. FIT_EXECUTION_LEDGER.json is COMPLETE for all268; do not restart fits. Final source inventory andMODEL_ARTIFACTS_AND_SHA.json bind models and preprocessing. Report folder `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_COUPLING_ML_156G_AMENDED_GLOBAL_FORWARD_TRAINING_V1`. Git commits use exact task allowlist; FSP/H5 and model binaries not added.
