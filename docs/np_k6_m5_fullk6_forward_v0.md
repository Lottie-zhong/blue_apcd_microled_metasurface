# NP K6 M5 Full-K6 Coupling-Aware Forward V0

## Status

`NP_K6_M5_FULLK6_FORWARD_V0_COMPLETE_EXTERNAL_HF_AUTHORIZATION_READY`

This is a development forward-model assessment. It is not `FORWARD_SURROGATE_FROZEN`; no external or prospective HF truth was read or run.

## Authority and preregistration

- Preregistration: `outputs\np_k6_m5_fullk6_forward_v0\NP_K6_FULLK6_FORWARD_V0_PREREG_V1.json`, SHA256 `3cb63dd1100768f13f982db8ddeab9dde623c4e60ea9d3ec2e971edd06c5c09e`; fit timestamp is strictly later.
- Dataset: 286 rows = 13 ordered geometries × 2 polarizations × 11 exact wavelengths; incident `u_x=0` only (`NORMAL_INCIDENCE_ONLY`).
- The immutable raw merged view contained 132 historical false training labels; M5 uses the immutable M3 promoted 198-row view plus 88 accepted Batch2 rows, with reconciliation recorded in `authority_audit.json`.
- 26 paired P/S logical cases, duplicate/conflicting provenance 0, quality gate true, diagnostic-only false, sealed target reads 0.
- Primary outputs: `R, eta_m(-3..+3)`; `T_hat=sum(eta_m)`; order schema confirmed from actual detailed files, 77 rows/case, max order-sum mismatch 3.33e-16.

## Model comparison (13-fold geometry LOGO, seeds 17/29/43)

| model | order MAE | eta(+1) MAE | R MAE | T MAE | rank Spearman | champion rank | worst geometry MAE | energy residual MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| lf_only | 0.042909 | 0.106214 | NA | 0.199493 | 0.829670 | 1 | 0.078591 | NA |
| direct_mlp | 0.084763 | 0.251411 | 0.081783 | 0.146759 | 0.153846 | 13 | 0.221271 | 0.128786 |
| resmlp | 0.083089 | 0.263392 | 0.094546 | 0.101046 | 0.384615 | 13 | 0.240859 | 0.089545 |
| residual_mlp | 0.164743 | 0.497511 | 0.080376 | 0.979103 | -0.741758 | 12 | 0.287790 | 1.001190 |
| circular_cnn | 0.061686 | 0.133458 | 0.080620 | 0.221433 | 0.472527 | 11 | 0.136993 | 0.220682 |

LF-only is the numerical/ranking/worst-case incumbent in this small grouped OOF. Direct MLP, ResMLP and CNN are retained as comparisons; residual MLP is not promoted because its unconstrained correction produced 46.59% negative-power violations and energy residual MAE 1.00119.

## LF-to-HF coupling audit

LF legally supplies seven order proxies and `T_proxy`, but no R baseline and is polarization-blind. The residual audit is in `lf_to_hf_residual_audit.csv`; its main systematic biases are eta(-3) -0.018036, eta(-2) -0.009364, eta(-1) -0.005301, eta(0) -0.043869, eta(+1) and other orders are reported there. P/S remains explicit; `ps_delta_audit.csv` reports true-versus-predicted P-S deltas for every model, geometry and wavelength. The observed HF P/S discrepancy therefore remains a coupling signal, not an equivalence assumption.

## Physics and uncertainty

- All tracked order identities, wavelength identities and P/S identities are complete. T/order bookkeeping is exact by construction for predictions (`T_hat=sum eta`); actual energy residuals are reported rather than hidden.
- Direct/ResMLP/CNN outputs are non-negative by sigmoid parameterization; residual MLP negative-power rate and energy residual are explicitly retained in `physics_consistency_metrics.json`.
- Multi-seed disagreement versus absolute error is in `ensemble_disagreement_audit.csv`; disagreement is not presented as calibrated probability.

## External and prospective governance

- `NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1` is ready as a metadata-only frozen external registry with 12 geometries, P/S pairing, 445–455 nm, `u_x=0`, and future HF budget 24 logical cases. No sealed target values were read; no registry geometry intersects development.
- Prospective validation remains separate: freeze surrogate assessment, choose a previously unrun development candidate, freeze prediction, then request one authorized HF comparison. Do not retrain before reporting that prospective comparison.

## Answers to the M5 questions

- A: yes, the reconciled 286-row development authority is complete and provenance-clean; the immutable raw/normalized distinction is documented.
- B: LF residuals are output-, geometry-, wavelength- and polarization-dependent; LF is not exact full-K6 truth.
- C: yes, residual structure is present, but the current residual MLP parameterization is not numerically/physically reliable.
- D–G: LF-only is best on current numerical OOF, ranking and worst-case; ResMLP has the lowest non-LF energy residual but does not win the primary metrics.
- H: no; residual MLP is not better than direct-HF here.
- I: yes; P/S is retained explicitly and P/S deltas remain substantial coupling evidence.
- J: this remains a development forward assessment, not a frozen surrogate.
- K: yes, metadata-only external readiness is frozen without HF target access.
- L: recommend external HF test as the next gate, subject to explicit solver authorization; do not execute it automatically.

## Zero-solver evidence

`solver_zero_audit.json`: FDTD run 0, LumAPI solver run 0, new HF 0, sealed target reads 0, inverse artifacts 0.

## Evidence

See `authority_audit.json`, `order_schema_audit.json`, `oof_predictions.csv`, `per_group_metrics.csv`, `numerical_metrics.json`, `ranking_metrics.csv`, `physics_consistency_metrics.json`, `lf_to_hf_residual_audit.csv`, `ps_delta_audit.csv`, `ensemble_disagreement_audit.csv`, `external_set_registry.json`, `solver_zero_audit.json`, and `validator_report.json`.
