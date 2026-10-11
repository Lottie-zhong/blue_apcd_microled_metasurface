# COUPLING_ML_FULL_RANK_AMPLITUDE_CIRCULAR_PHASE_KRR_PILOT_V1
STATUS PASS — experiment completed within budget. Scientific verdict: **STRUCTURED_AMPLITUDE_ONLY_GAIN**. Full model remains **DEVELOPMENT_H1_FAIL**.

## Frozen scope and actual execution
DESKTOP-NNE313K/dell, N:\anaconda_envs\RCP_LCP\python.exe, branch work/mdc-np-coupling-ml-v1. Source HEAD674b36df4bd0f3317590c3402c4f5468c0d13a72.156G science-valid development identity and complete previous artifact inventories were checked before fit. The same original four n124 train subsets and heldouts32/31/30/31 were used, with no baseline fit or hyperparameter selection. Geometry standardization, RBF gamma1/6 and alpha1 are the frozen same-fold values. All21 wavelengths follow geometry groups; reference1722nm, seven ordered m=-3..+3, TE/TM, full294complex/588real state and21physicalP_scale remain unchanged.

4 logical candidates, **8 CPU state-head fits** (fourAmplitude, fourPhase); no P_scale fits, baseline refits, MLP, NP/MDC retraining, FDTD, replay or confirmation response access. Eight per-head invocations were ledgered before each .fit and saved once complete. All8 completed; no reruns. Zero-fit preflight and6synthetic tests passed before fitting. Model saves/reloads reproduce predictions elementwise exactly.

## One preregistered representation
Amplitude targets sqrt(abs(C_hat)) are standardized by training coordinate means and one global RMS per head, predicted and inverse-scaled, then squared for nonnegative A. No clipping; zero negative sqrt predictions occurred. Phase targets are294absolute[cos,sin] pairs, standardized independently with training means/globalRMS. Training coordinates with fraction<1e-4 or A=0 use deterministic[1,0], never treated as reliable phase. Inverse-scaled predicted vectors are unit-normalized; norm<=64float64eps would use unit mean of reliable training phasors (no reliable/zero mean ->unit1). Actual fallback count0. No reference switching, test-truth mask, oracle alignment or full-state renormalization enters B prediction.

About50.02..50.03% training coordinates were weak (all TE and very fewTM); their truth energy was only1.88e-7..3.28e-7. The raw polar representation is fully invertible, tested through zero/tiny/wrap cases; weak-phase target canonicalization deliberately discards unreliable supervision and is not asserted to roundtrip those phases. All294 amplitudes and bothchannels remain in output. H2 roundtrip test meets1e-12; raw complex roundtrip tolerance2e-15. Protected sources and original268/NP88/zero-fit audit predictions were preserved.

## Matched original evaluator
|Metric|Cartesian A median/q95|Structured B median/q95|Improved/worsened|
|---|---:|---:|---:|
|amplitude_relative_rmse|0.672675/0.797020|0.430317/0.601391|121/3|
|phase_component_relative_rmse|0.555445/0.780624|0.933017/1.205615|0/124|
|absolute_phase_rmse|1.220526/1.768362|1.281598/1.862608|51/73|
|relative_phase_rmse|1.721010/1.961726|1.750114/1.963318|58/66|
|state_relative_rmse|0.872970/1.086444|1.039131/1.318987|12/112|
|routing_eta_rmse|0.182086/0.297147|0.122364/0.207292|106/18|
|absolute_order_source_normalized_rmse|0.064621/0.115201|0.048482/0.085943|101/23|
|thresholded_absolute_order_relative_median|0.801501/0.937560|0.647095/1.192286|98/26|
|total_power_relative_rmse|0.248064/0.757838|0.248064/0.757838|0/0|
|p_scale_relative_rmse|0.248064/0.757838|0.248064/0.757838|0/0|
|nonzero_state_rmse|0.973604/1.129514|1.162706/1.677441|13/111|

Norm ratio A 0.507299/0.733121 versus B 0.875557/0.921973 (median/q95). Restored norm alone does not mean restored complex state. P_scale A/B is elementwise identical in every fold and mergedOOF. Absolute-order changes come from routing only; H2 total=P_scale, so total/scale errors coincide by definition. Frozen A aggregate and all original gates match the original n124 result exactly.

|Original gate|A|B|
|---|---|---|
|state|False|False|
|routing|False|False|
|absolute_order|False|True|
|thresholded_absolute_order|False|False|
|total_power|False|False|
|seed_stability|None|None|

Routing Pearson A=0.47060067366405717, B=0.43925728268161945; total-power Pearson A=0.9045878624767147, B=0.9045878624767147. Deterministic one-seed KRR has seed stability N/A, not an inventedPASS. B attains the original absolute-order gate, but state/routing/thresholded-relative/total gates fail. No independent confirmation or production admission.

## Amplitude learned; absolute/relative phase not improved
Amplitude relative RMSE0.672675/0.797020 ->0.430317/0.601391;121/124 geometries improve, allfour fold median deltas negative. Amplitude pooled SSE1290.43 ->596.36 (53.8% reduction). Yet phase pooled SSE959.62 ->2596.14 (2.71x); phase now81.32% of B complex SSE versus42.65% in A. Phase direction median/q95 itself worsens1.220526/1.768362 ->1.281598/1.862608rad; relative phase1.721010/1.961726 ->1.750114/1.963318rad. Absolute phase51wins/73losses; phase-component RMSE worsens in all124. This is not an amplitude-and-phase joint gain.

Raw phase-vector norms require a strong/weak distinction: strong truth-mask norm median0.359144, q950.824084; 69.27% below0.5 and 5.46% below0.1. The all-coordinate median1 is largely weak-TE fixed[1,0], not proof of confident physical phases. Unit-circle projection restores length but cannot improve direction; with0fallbacks it preserves the predicted phase angle. Larger learned amplitude magnifies still-wrong directions through2*A_pred*A_true*(1-cosdelta), explaining the observed SSE tradeoff algebraically. It does not establish that another phase representation will generalize.

## Nonzero, zero and +1 orders
Nonzero state0.973604/1.129514 ->1.162706/1.677441;13wins/111losses. Nonzero norm0.343782 ->0.842894 recovers while complex correctness worsens. m0 state0.550113/1.872078 ->0.584045/2.197658, with itsnorm0.812537 ->1.011012. +1 state0.921086/1.337575 ->1.096359/2.468508: severe target-order tail deterioration. +1routing median0.089712 ->0.101143 worsens even though q95improves; do not generalize overall routing gain to every order. +1absolute median0.032824 ->0.033185 also slightly worsens. Full per-order TE/TM/state/power diagnostics retained.

B nonzero contribution88.25% of total complex SSE. TE contributes~1.28e-9 to B SSE; the error remains TM/nonzero phase dominated, not weak-channel phase noise. Strong and weak bins retain absolute SSE quantities to avoid misleading percentages from tiny denominators. Wavelength bands440..444,445..455,456..460 and fullband are reported independently; none selected model rules.

## Paired geometry and tails
|Fold|State wins/losses|State median delta|Routing wins/losses|Routing median delta|
|---|---:|---:|---:|---:|
|1|3/29|0.157179|29/3|-0.044834|
|2|4/27|0.203506|24/7|-0.064373|
|3|2/28|0.168008|25/5|-0.069440|
|4|3/28|0.161459|28/3|-0.066630|

Amplitude gains121/3; routing106/18; absolute-order101/23. State12/112, with pairedmedian+0.163908 and descriptive geometry-bootstrap95% medianCI[0.133515,0.203176]. Routing pairedmedian-0.063964, CI[-0.072127,-0.046431]. No wavelength pseudo-replication or statistical independence claim; folds/history are correlated and heldouts repeatedly examined.

Largest state delta: G0110.902081->1.244564 (+0.342483), G0091.156564->1.486358 (+0.329794), G0510.953989->1.279414 (+0.325424). Overall worst state A=1.156564, B=1.486358; preregistered research tail rule passes=False. Significant routing regressions includeG1110.061714->0.181633 andG0420.072071->0.183430. No NaN, overflow, negative A, replay or numerical projection exception occurred; these are predictive failures. Every geometry delta and top10worsenings permetric are saved, not only favorable averages.

## Train versus heldout and evidence limits
Per-fold training state medians: [0.553319, 0.560924, 0.551343, 0.542482]; training amplitude medians: [0.314357, 0.303662, 0.311691, 0.31244]. Full trainingphase diagnostics retained. Single matched frozenkernel/head scheme proves neither phase fundamentally unlearnable nor every structured model ineffective. Current evidence supports useful amplitude/power prediction, continued phase uncertainty, and harmful recovery of large wrong-phase vectors. No oracle result enters official H1.

## Next — DO NOT EXECUTE
Retain the evidence of amplitude/routing gain for scientific review; do not promote B or replace baseline/confirmation predictions. Priority is an order-resolved phase-structure experiment that retains absolute/common and relative phases and tests train-defined local geometry conditioning, with explicit invertible reconstruction and matched KRR controls. A concrete new protocol/budget requires Chat review; do not append another candidate, wider MLP or kernel-scale trial now. Full-rank amplitude-only recovery or global-phase-only compensation is insufficient. Existing156G can support a further developmental test; independent confirmation and numerical repeatability remain separate obligations.

## Artifacts, hashes and isolation
STRUCTURED_MODEL_FROZEN_SPEC and FOUR_FOLD_MATCHING_AND_SHA freeze code, identities, input dependencies, transforms and model choices before fits. FIT_LEDGER proves8invocations. MODEL_ARTIFACTS_AND_SHA references allhead/model/prediction binaries retained durably on thisserver; only scoped source/report/test/provenance text is committed. SHA_INVENTORY contains full hashes. FINAL_ISOLATION_CHECK re-verifies originals, no confirmation access and unchanged P_scale. Local13 continues SUSPENDED, original32confirmation roles/responses sealed and28input-side predictions unchanged. Foreign dirty/staged preserved. DELIVERY_RECEIPT contains finalGit/push snapshot and is outside its own committed inventory.
