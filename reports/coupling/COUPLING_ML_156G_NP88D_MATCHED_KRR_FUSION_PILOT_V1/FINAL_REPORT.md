# COUPLING_ML_156G_NP88D_MATCHED_KRR_FUSION_PILOT_V1

STATUS PASS; scientific verdict NP_FUSION_NO_CLEAR_GAIN. Four joint state/log-P CPU KRR fits (eight internal output-head solve calls), zero baseline refits, zero solver/replay/confirmation responses. Old65G pair authorization superseded.

|Metric|A median/q95|B median/q95|wins/losses|paired median delta|
|---|---|---|---|---|
|state_relative_rmse|0.872970/1.086444|0.903966/1.116615|54/70|0.015934|
|routing_eta_rmse|0.182086/0.297147|0.195308/0.308885|49/75|0.008112|
|absolute_order_source_normalized_rmse|0.064621/0.115201|0.069143/0.108209|62/62|0.000021|
|thresholded_absolute_order_relative_median|0.801501/0.937560|0.798356/0.926634|63/61|-0.000951|
|total_power_relative_rmse|0.248064/0.757838|0.261788/0.811482|53/71|0.009306|
|p_scale_relative_rmse|0.248064/0.757838|0.261788/0.811482|53/71|0.009306|

A models and all124G heldout predictions are exact original baseline parity. Ordered input sixD and88NP power features. Same124train per fold and fixed heldouts32/31/30/31; old32 train-only historical exposure. Same target normalizer, label contract, gamma/alpha, float64, H1/H2. No new model selection or kernel-scale search.

NP frozen single-pillar-DFT source supports ordered100..230/5nm and445..455/P/XLIKE; descriptors predict fullHF440..460 but do not validate NP outside band. Neither reflection/Jones nor same-reference complexLF exists; no residual. Support distance/HF22 membership diagnostic only. D180 historical setup-link warnings preserved; validated post-FSP and library result source remain bound.

H1 A {'state': False, 'routing': False, 'absolute_order': False, 'thresholded_absolute_order': False, 'total_power': False, 'seed_stability': None}; B {'state': False, 'routing': False, 'absolute_order': False, 'thresholded_absolute_order': False, 'total_power': False, 'seed_stability': None}. No independent confirmation/production admission. P_scale/total equal by H2 definition, not two independent validations.

State norm ratio median A 0.507299, B 0.456028; truth-weight phase median A 1.220526, B 1.339729; relativephase A 1.721010, B 1.779797. No alignment/rescaling/clipping.

Geometry paired bootstrap10000 seed8815601 descriptiveCI, no wavelength pseudo-replication/significance claims; nested/history-correlated folds limit inference. Full pergeometry, spectral bands, orders/TE/TM, +1/othernonzero, severe tails retained in JSON. Kernel audited train-only; equal block weighting fixed beforefits. Any benefit conflates additional physical nonlinear descriptors with altered metric, not causal proof of coupling physics.

NEXT DO NOT EXECUTE: Chat review of matched pilot, prioritize state/phase representation and modal structure if fullstate gain fails; no automatic widerMLP, newHF, residual or confirmation.

## Fold paired results (B minus A)

|Metric|Fold|Median delta|Wins/losses|
|---|---:|---:|---:|
|state_relative_rmse|1|0.037856|11/21|
|state_relative_rmse|2|0.026567|13/18|
|state_relative_rmse|3|0.010593|12/18|
|state_relative_rmse|4|-0.010991|18/13|
|routing_eta_rmse|1|-0.003255|17/15|
|routing_eta_rmse|2|0.012263|8/23|
|routing_eta_rmse|3|0.008261|13/17|
|routing_eta_rmse|4|0.022381|11/20|
|total_power_relative_rmse|1|0.009514|12/20|
|total_power_relative_rmse|2|0.003641|15/16|
|total_power_relative_rmse|3|0.000963|15/15|
|total_power_relative_rmse|4|0.017655|11/20|

## Spectral strata (diagnostic, no gate substitution)

|Band|State A/B median|Routing A/B median|P_scale/total A/B median|
|---|---:|---:|---:|
|full|0.872970/0.903966|0.182086/0.195308|0.248064/0.261788|
|NP_supported|0.863500/0.888951|0.172885/0.190726|0.188038/0.208103|
|outside_low|0.877316/0.899732|0.179155/0.191884|0.232560/0.232215|
|outside_high|0.881649/0.911994|0.180336/0.183856|0.241888/0.255819|

## Geometry bootstrap uncertainty (descriptive)

|Metric|Mean delta95%CI|Median delta95%CI|
|---|---|---|
|state_relative_rmse|[-0.002184044669921521, 0.02829755929028146]|[-0.004381801122985141, 0.03536940413936962]|
|routing_eta_rmse|[-0.0004193675077504646, 0.014055872224409096]|[0.0009345597919470233, 0.014039626972522921]|
|absolute_order_source_normalized_rmse|[-0.004268557377552748, 0.002476905489504419]|[-0.0030369881679110427, 0.0028341010128162393]|
|total_power_relative_rmse|[-0.0021913085893472276, 0.036064020300856765]|[-0.0034603989998120976, 0.016826032365077764]|

## Phase, norm and limits

A: amplitude error median/q95 0.672675/0.797020; truthweighted absolutephase 1.220526/1.768362rad; relativephase 1.721010/1.961726rad; normratio 0.507299/0.733121.

B: amplitude error median/q95 0.680092/0.815351; truthweighted absolutephase 1.339729/2.051115rad; relativephase 1.779797/1.987028rad; normratio 0.456028/0.792186.

The fixed NP88 fusion has no clear state/routing gain and does not merit automatic expansion into a larger fusion network. Some absolute-order tail and thresholded-relative metrics improve, but core state/routing/P_scale medians worsen and norm collapse deepens. This negative result applies to this provider, block metric, frozen gamma/alpha and dataset; it does not prove all physics fusion is ineffective. Next scientific review should examine complex/modal/phase learnability and lawful LF/HF alignment before any residual. No scale retuning/MLP/confirmation launched.

Kernel unregularized condition~3.4e3..1.1e4, regularized24.3..25.3; no constant NP columns, all156 runtime-supported. NP contributes~48..49% median trainpair squared distance. HF22 empirical support is distinct from legal singlepillar runtime support; OOD is not a training feature. Kernel metric changes are a confound for mechanistic attribution.

## Source-verified information limits
NP88 contains correlated power descriptors: each wavelength sevenfractions sum1, T_proxy=sumthreefractions, m=-3/+3 alias on sixsiteDFT. All156geometry inference verifies cyclicdiameter shift power invariance within frozen float32parity tolerance. Thus these features do not directly carry complexDFTphase or physicalphaseorigin; raworderedD input still distinguishes shifted geometries. This supplies a plausible limitation for phaselearning, not causal proof of the observed negative gain. Full details: NP_FEATURE_INFORMATION_LIMITS.json.
