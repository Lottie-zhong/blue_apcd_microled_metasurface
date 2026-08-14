# NP K6 M7 16G full-K6 coupling-aware forward retraining v1

**Status:** `NP_K6_M7_16G_FORWARD_RETRAINING_COMPLETE_MORE_DEVELOPMENT_HF_REQUIRED`

## Authority and scope

Formal development authority: 352 rows = 16 geometries × 2 polarizations × 11 wavelengths (445–455 nm), u_x=0, exact order-resolved powers. M6 G01-P/S primary4 cases remain quarantined and are excluded from formal training. Duplicate/conflicting provenance is zero. Capability is normal-incidence development only; this is not a production surrogate freeze.

M7 preregistration SHA256: `7286d97b52e9aab17e6e13a1b6af8639befd5a3fa5e9298b7f93ce32d721005a`. Fit followed preregistration. Solver calls: FDTD=0, LumAPI=0, new HF=0, external=0, sealed target reads=0.

## Frozen input/output contract

Input is ordered physical [D1,D2,D3,D4,D5,D6] plus [wavelength_nm,u_x,polarization]; no diameter sorting or permutation-invariant encoding. Capability is NORMAL_INCIDENCE_ONLY (u_x=0). Primary outputs are R and eta_m-3 ... eta_m+3; T is derived as their sum. Complex labels remain COMPLEX_ORDER_CONTRACT_NOT_YET_READY.

## Model comparison

| model | order MAE | Spearman | worst geometry | energy residual MAE |
|---|---:|---:|---:|---:|
| LF_only | 0.045825 | 0.955882 | 0.081879 | n/a |
| LF_global_bias | 0.048009 | 0.955882 | 0.079823 | 0.005892 |
| LF_affine | 0.048714 | 0.955882 | 0.077906 | 0.006448 |
| LF_ridge_residual | 0.041159 | 0.935294 | 0.076096 | 0.041852 |
| LF_paired_shared_contrast | 0.054775 | 0.935294 | 0.190231 | 0.070740 |
| corrected_residual_mlp | 0.046649 | 0.908824 | 0.107215 | 0.047180 |
| direct_mlp | 0.079091 | 0.611765 | 0.229330 | 0.160848 |
| resmlp | 0.069002 | 0.688235 | 0.218798 | 0.072790 |
| circular_cnn | 0.060493 | 0.844118 | 0.151827 | 0.175425 |

Evidence is Pareto-like rather than a unique winner: LF/Ridge are strongest on numerical error, LF-only has the highest ranking correlation, and affine/global bias have lower energy residuals than learned residual models. No model is promoted automatically.

## Learning value and P/S

Common-HF13 comparison is reported without an uncontrolled percentage claim because M5B and M7 memberships/folds differ. New-M6 held-out analysis is separate. The full HF16 P/S audit is retained in combined_hf16_ps_summary.csv; polarization remains explicit and P/S averaging is not used.

## External governance

NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1 remains metadata-only: 12 geometries and 24 future paired cases. No sealed target or external FDTD was accessed. External/prospective HF, angular extension, supplemental acquisitions, inverse design and training promotion remain unauthorized.

## Decision

M7 is complete as a zero-solver development assessment, but more development HF is required before any external-HF promotion claim. The next action is a user decision on external HF versus additional development HF; neither starts automatically.
