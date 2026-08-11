# NP K6 M5A Forward Development / Promotion Diagnostic v1

## Frozen scope

- Preregistration: `NP_K6_M5A_FORWARD_DIAGNOSTIC_PREREG_V1`
- Preregistration SHA256: `30644e7a2cef9a9a6d6d471e3baa2b0edd91ccf755876fa605daf1b0f87532cb`
- Scope: zero-solver forensic diagnosis and development-only model screening.
- FDTD/LumAPI runs: `0`; external HF calls: `0`; sealed HF target reads: `0`.
- The frozen M5 evidence under `outputs/np_k6_m5_fullk6_forward_v0/` was read-only and was not modified.

## Authority audit

The normalized development view contains exactly 286 rows, 13 geometry identities, 26 paired P/S cases, and 11 exact wavelengths. All rows have `m5_training_label=true`, `quality_gate_pass=true`, and `diagnostic_only=false`; no duplicate/conflicting provenance was found. The current capability remains normal incidence only (`u_x=0`, `k_y=0`). The formal transmitted-order vector is `[-3,-2,-1,0,+1,+2,+3]`, with full response represented as `[R, eta_-3, eta_-2, eta_-1, eta_0, eta_+1, eta_+2, eta_+3]`.

The existing `NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1` registry remains metadata-only with 12 geometries and zero sealed-target reads. Its future budget is 24 logical P/S cases; no case was launched.

## M3 to M5 forensic comparison

On the common nine-geometry membership, the descriptive OOF comparison was:

| model / evidence | order-profile MAE | eta(+1) MAE | T MAE | ranking Spearman |
|---|---:|---:|---:|---:|
| M3 CNN, HF9 | 0.07288 | 0.08261 | 0.08733 | 0.9000 |
| M5 CNN, same HF9 membership | 0.06837 | 0.15146 | 0.26081 | 0.6167 |
| M5 direct MLP, same HF9 membership | 0.09066 | 0.27618 | 0.16732 | 0.2167 |

These are not an improvement percentage claim: folds, preprocessing and model contracts differ. The controlled 2x2 ablation also shows a data/contract interaction: HF13 was materially easier than HF9 for both styles, while the M5-style output contract reduced R error but did not solve eta(+1) generalization.

## Confirmed implementation/formulation findings

1. **Frozen M5 residual reconstruction bug.** The frozen residual MLP stored `delta_hat` as eta output instead of reconstructing `eta_hat = LF_eta + delta_hat`. The audit is recorded in `m5_residual_reconstruction_audit.json`; historical M5 evidence remains unchanged. A corrected shallow residual fit is numerically legal (negative-power rate 0, bookkeeping max 0) but does not pass the frozen promotion gate.
2. **Frozen ranking index mix-up.** In the frozen source, `a[ix,4]` selects eta(0) in the full vector, while eta(+1) is index 5. `m5_ranking_contract_audit.json` records the complete vector, the source literal, and the corrected M5A ranking calculation. No frozen M5 file was edited.

## LF-to-HF coupling audit

The LF baseline is not a global correction: `residual_is_global_bias=false`. For eta(+1), LF residual mean bias is `-0.08446`, MAE `0.10621`, P90 absolute residual `0.22488`, and maximum absolute residual `0.58189`; eta(0) has mean bias `-0.04387` and MAE `0.06972`. The residual varies by geometry, wavelength and P/S. The highest-priority error regions are `K6X_D125_D135_D150_D175_D190_D210`, `K6X_D110_D125_D135_D150_D175_D190`, `K6X_D100_D130_D135_D155_D160_D225`, and `K6X_D130_D145_D155_D180_D195_D230`. These are development-HF targets only; the sealed set is untouched.

The measured P/S difference remains material (authority mean approximately `0.15839`, maximum approximately `0.50127` for eta(+1)); P/S cannot be averaged or removed. The paired correction candidate preserves explicit P/S, but its P/S delta error is `0.15457` and it fails the promotion gate.

## M5A model competition (13-geometry geometry-LOGO OOF)

| candidate | order MAE | eta(+1) MAE | R MAE | T MAE | ranking | worst geometry MAE | promotion |
|---|---:|---:|---:|---:|---:|---:|---|
| LF-only frozen | 0.04291 | 0.10621 | unavailable | 0.19949 | 0.9341 | 0.07859 | no (reference)
| LF global bias | **0.03692** | **0.08412** | 0.09733 | 0.09983 | 0.9326 | **0.07398** | no (P/S)
| LF wavelength/P affine | 0.04716 | 0.08592 | 0.07337 | 0.08733 | **0.9505** | 0.10104 | no
| LF ridge residual | 0.04163 | 0.08593 | 0.07337 | 0.08799 | 0.9341 | 0.08314 | no
| paired shared correction | 0.04132 | 0.08954 | 0.06750 | **0.07739** | 0.9341 | 0.08092 | no (P/S)
| corrected shallow residual MLP | 0.04920 | 0.11837 | 0.07390 | 0.10649 | 0.8462 | 0.10975 | no
| M5 direct MLP frozen | 0.08476 | 0.25141 | 0.08178 | 0.14676 | 0.5110 | 0.22127 | no
| M5 ResMLP frozen | 0.08309 | 0.26339 | 0.09455 | 0.10105 | 0.4615 | 0.24086 | no
| M5 CircularCNN frozen | 0.06169 | 0.13346 | 0.08062 | 0.22143 | 0.7582 | 0.13699 | no

All candidates had zero negative-power violations. The physics bookkeeping audit is legal for the corrected candidates, but the frozen promotion rule requires simultaneous order, eta(+1), ranking, worst-geometry, energy and P/S gates. No learned candidate satisfies all gates; external authorization therefore remains false.

## Decision

**`MODEL_FORMULATION_REQUIRES_REVISION`**

The main blocker is not a lack of solver data or sealed access: two frozen implementation contracts were objectively wrong (residual reconstruction and ranking index), and the corrected low-capacity candidates still do not pass the strict promotion rule. The result is a development diagnostic, not a frozen surrogate and not an HF promotion.

## Completion supplement

The remaining diagnostics were frozen in `NP_K6_M5A_FORWARD_DIAGNOSTIC_SUPPLEMENT_V1` before the supplement audit fit/post-processing. Its SHA256 is `30b94bacf65545a27de40cce24e244ee24c6245c5dab2b783b617c16fa8fbc72`. It adds the explicit ranking tie-break, geometry-level bootstrap, disagreement buckets, and a simple non-negative energy projection; it does not modify the parent M5A preregistration or any M5 frozen evidence.

The complete ranking audit gives LF-only `rho=0.9341`, top-3 recall `0.667`, top-5 recall `1.0`, and champion rank `3`. The best LF-corrected candidates have the same top-3/top-5 recall but do not improve champion retrieval consistently; direct MLP, ResMLP and CNN have champion ranks `8`, `7`, and `6`, respectively. Frozen-seed ranking stability is high for the CNN (`mean rho=0.9835`) but this does not imply accuracy.

Geometry-paired bootstrap (10,000 resamples, geometry unit) shows global-bias mean eta(+1) error delta `-0.02210` versus LF (95% CI `[-0.04576, 0.00489]`, improvement probability `0.9469`, 9/13 geometries), Ridge delta `-0.02029` (CI `[-0.05625, 0.01293]`, probability `0.8803`, 9/13), and paired P/S delta `-0.01668` (CI `[-0.05828, 0.02471]`, probability `0.7804`, 8/13). Learned direct/ResMLP/CNN deltas are positive (`+0.1452`, `+0.1572`, `+0.0272`), so none is promotion-ready.

The constrained-output experiment is a deterministic projection, not a new architecture: clip `[R, eta]` at zero and scale when the total exceeds one. It drives negative-power and energy-violation rates to zero. For example, ResMLP energy-residual MAE falls from `0.08955` to `0.02600`, but eta(+1), ranking, worst-case and P/S gates still fail; physics legality alone does not justify promotion.

Disagreement is informative but not calibrated probability. For direct MLP eta(+1), high-disagreement rows have MAE `0.4768` versus `0.1441` in the low bucket; for ResMLP the values are `0.2571` versus `0.2046`; CNN is `0.1024` versus `0.0805`. LF eta(+1) residual MAE correlates with LF eta(+1) magnitude (`rho=0.8901`), with mean-gap correlation `0.4231` and mean-diameter correlation `-0.4286`, supporting a coupling-regime error cluster rather than a single global bias.

## Evidence and validation

Evidence directory: `outputs/np_k6_m5a_forward_development_promotion_diagnostic_v1/`

Key files include the preregistration/hash, common-subset and Batch2 audits, 2x2 ablation, residual physics tables, corrected reconstruction audit, ranking contract audit, candidate gate, promotion decision, solver-zero audit, and `m5a_validator_report.json`. The standalone validator confirms 286 rows, 13 geometries, 26 paired cases, 11 wavelengths, unchanged M5 hashes, zero solver/sealed reads, and no external authorization.

Supplement files additionally include `ranking_audit_full.csv`, `geometry_paired_bootstrap_audit.csv`, `lf_residual_spectrum_polarization.csv`, `model_disagreement_audit.csv`, `physics_consistent_output_metrics.csv`, `m5a_model_provenance_audit.json`, and `m5a_supplement_run_manifest.json`.

## Next gate

Revise and re-validate the forward output/reconstruction/ranking implementation on the same development authority; do not run external HF, Batch3, angular extensions, or inverse design until a corrected development candidate passes the frozen promotion gates.
