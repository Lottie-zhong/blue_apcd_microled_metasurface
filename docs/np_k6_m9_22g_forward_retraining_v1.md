# NP K6 M9 22-geometry forward retraining v1

## Status
NP_K6_M9_22G_FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED

## Authority
- HF: 484 rows = 22 geometries x P/S x 11 exact wavelengths; u_x=0, k_y=0, NORMAL_INCIDENCE_ONLY.
- LF22 full-vector gate: PASS. A deterministic frozen D0 pipeline regenerated all 7 tracked m fields plus T_proxy for both newly acquired geometries; historical M8A linkage remains immutable.
- Solver calls: 0; sealed/external target reads: 0.
- Preregistration: NP_K6_M9_22G_FORWARD_RETRAINING_PREREG_V1; SHA256 072cf2a9b372bfbbeab98afff8301809ed00a66910906e2ff49773916644ff07.

## OOF comparison (22-fold LOGO, 3 seeds)
| model | order MAE | eta(+1) MAE | R MAE | T MAE | rank rho | top3 | champion rank | worst geometry MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LF_only | 0.04717 | 0.10282 | nan | 0.20682 | 0.9616 | 0.333 | 4 | 0.08188 |
| LF_global_bias | 0.04872 | 0.10007 | 0.09889 | 0.10008 | 0.9616 | 0.333 | 4 | 0.07946 |
| LF_affine | 0.04913 | 0.10056 | 0.09922 | 0.10093 | 0.9616 | 0.333 | 4 | 0.07755 |
| LF_ridge_residual | 0.03960 | 0.07399 | 0.06627 | 0.06893 | 0.9503 | 0.667 | 5 | 0.06189 |
| LF_paired_shared_contrast | 0.04062 | 0.07804 | 0.06627 | 0.06220 | 0.9503 | 0.667 | 5 | 0.06106 |
| corrected_residual_mlp | 0.04586 | 0.08367 | 0.06102 | 0.07621 | 0.9503 | 0.667 | 5 | 0.11002 |
| direct_mlp | 0.06059 | 0.10838 | 0.05866 | 0.19482 | 0.8950 | 0.333 | 5 | 0.13743 |
| resmlp | 0.05220 | 0.11210 | 0.05896 | 0.09622 | 0.8826 | 0.333 | 6 | 0.12335 |
| circular_cnn | 0.04468 | 0.07220 | 0.06221 | 0.16031 | 0.9390 | 0.333 | 6 | 0.12183 |

Best order-profile model: LF_ridge_residual; best eta(+1) model: circular_cnn; best ranking rho: LF_only. No model passed all frozen promotion gates: top-3/champion-rank and/or physics/worst-case failures remain.

## Coupling and residual audits
- True P/S |delta eta(+1)| across 242 geometry x wavelength pairs: mean 0.091214, max 0.501273; P/S remains an explicit condition.
- LF-to-HF residuals are reported per order, geometry, wavelength and polarization in the lightweight audit; no HF-to-LF calibration was applied.
- Common-HF20 comparison is mixed (improvements and degradations across models), so no consistent regression-free gain is established.

## External governance
- NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1 remains metadata-only: 12 geometries / 24 future P/S cases, training intersection [], target reads 0.

## Decision
NP_K6_M9_22G_FORWARD_MODEL_PLATEAU_REASSESSMENT_REQUIRED. Automatic new HF, external HF, angular extension, inverse design and M10 are not started. The next gate is a user-authorized external-HF test after frozen model-selection review.

## Evidence
- outputs\\np_k6_m9_22g_forward_retraining_v1\\lf22_full_vector_authority_gate.json
- outputs\\np_k6_m9_22g_forward_retraining_v1\\NP_K6_M9_22G_FORWARD_RETRAINING_PREREG_V1.json
- outputs\\np_k6_m9_22g_forward_retraining_v1\\model_metrics_raw.csv
- outputs\\np_k6_m9_22g_forward_retraining_v1\\ranking_metrics.csv
- outputs\\np_k6_m9_22g_forward_retraining_v1\\ps_coupling_audit_22g.json
- outputs\\np_k6_m9_22g_forward_retraining_v1\\m9_final_validator_report.json
