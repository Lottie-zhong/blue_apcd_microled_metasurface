# NP K6 M8 20G forward retraining and promotion review v1

Final state: `MORE_TARGETED_DEVELOPMENT_HF_REQUIRED`

## Authority and frozen method

- Preregistration `NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1`; SHA256 `fc05bc4d99cb54fa48558cda3605da53aa3fbda3f84c995a5493dfb820131ef9`.
- M7A preregistration SHA256: `bd221dfe8d15475cb5c0f9d5959a6595fed2238ff58f7ca1befbdc421bf65951`.
- Formal HF20 authority: 440 rows = 20 geometries × 2 polarizations × 11 exact wavelengths (445–455 nm); 20 geometry hashes; 40 paired P/S cases; G01 quarantine absent; duplicate/conflicting provenance 0.
- M7A contribution: 88 rows / 4 geometries; pre-M7A HF16: 352 rows. LF20: 440/440 keys matched with no missing baseline.
- Ordered physical `[D1,D2,D3,D4,D5,D6]` is preserved; no diameter sorting, pooling, or permutation-invariant encoding. Scope is `NORMAL_INCIDENCE_ONLY` (`u_x=0`, `k_y=0`). P/S remains explicit.
- Primary output is `[R, eta_m-3 … eta_m+3]`; `T` is derived from the symbolic order sum. Directionality and leakage are derived quantities. Complex labels remain `COMPLEX_ORDER_CONTRACT_NOT_YET_READY`.
- M8 uses 20-fold LOGO, fold-local normalization, 3 deterministic seeds (17, 29, 43), and 9 fixed model families.

## Model comparison

| Model | order MAE | eta(+1) MAE | R MAE | T MAE | rho | Top-3 | champion rank | worst order MAE | energy max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LF_only | 0.046238 | 0.104086 | unsupported | 0.209516 | 0.951880 | 0.333333 | 4 | 0.081879 |  |
| LF_global_bias | 0.048299 | 0.100919 | 0.10346961518875901 | 0.104833 | 0.951880 | 0.333333 | 4 | 0.079995 | 0.004914 |
| LF_affine | 0.048824 | 0.101573 | 0.10336231575987123 | 0.105630 | 0.951880 | 0.333333 | 4 | 0.077705 | 0.011561 |
| LF_ridge_residual | 0.042516 | 0.082800 | 0.0683804426502917 | 0.072849 | 0.953383 | 0.666667 | 4 | 0.102465 | 0.106248 |
| LF_paired_shared_contrast | 0.044420 | 0.094435 | 0.06838044265029156 | 0.065777 | 0.953383 | 0.666667 | 4 | 0.102752 | 0.271837 |
| corrected_residual_mlp | 0.047085 | 0.089833 | 0.06065505436286495 | 0.080662 | 0.942857 | 0.666667 | 6 | 0.108623 | 0.210010 |
| direct_mlp | 0.071427 | 0.147215 | 0.05922856250731803 | 0.182714 | 0.864662 | 0.333333 | 5 | 0.174147 | 0.510470 |
| resmlp | 0.055300 | 0.109287 | 0.060106491197202495 | 0.093804 | 0.903759 | 0.333333 | 4 | 0.120541 | 0.246661 |
| circular_cnn | 0.047797 | 0.079635 | 0.06611742695733383 | 0.171506 | 0.933835 | 0.333333 | 5 | 0.138530 | 0.412877 |

- Best order-profile trainable result: `LF_ridge_residual` (0.042516). Lowest η(+1) MAE is `circular_cnn` (0.079635), but its T/energy/worst-case gates fail. No model passes every frozen development gate.
- Raw and constrained metric files are both retained; constrained projection is not used as a substitute for raw physics validity.

## Ranking, physics, and P/S

- LF-ridge and paired correction reach ρ≈0.9534 and Top-3 recall 2/3, but both predict the true champion at rank 4. Thus high global rho does not close champion-neighborhood reliability.
- Best P/S contrast MAE is ResMLP 0.087505, but its other numerical/physics gates fail. P/S averaging is not used.
- Physics bookkeeping `T=sum(eta_m)` is exact in the OOF schema; raw energy and negative-power violations remain nonzero for multiple learned models.

| Model | P/S contrast MAE | negative-power violation | energy max |
|---|---:|---:|---:|
| LF_only | 0.093667 | 0.000000 | None |
| LF_global_bias | 0.093667 | 0.372078 | 0.004914 |
| LF_affine | 0.096101 | 0.345455 | 0.011561 |
| LF_ridge_residual | 0.096101 | 0.106494 | 0.106248 |
| LF_paired_shared_contrast | 0.130821 | 0.136039 | 0.271837 |
| corrected_residual_mlp | 0.124541 | 0.115260 | 0.210010 |
| direct_mlp | 0.101296 | 0.000000 | 0.510470 |
| resmlp | 0.087505 | 0.000000 | 0.246661 |
| circular_cnn | 0.101093 | 0.000000 | 0.412877 |

## HF20 P/S truth distribution

| Scope | metric | n | mean | median | P90 | max |
|---|---|---:|---:|---:|---:|---:|
| HF16 | eta_plus1 | 352 | 0.379689 | 0.290267 | 0.840354 | 0.944240 |
| M7A_new4 | eta_plus1 | 88 | 0.327557 | 0.105440 | 0.842405 | 0.928699 |
| HF20 | eta_plus1 | 440 | 0.369263 | 0.278740 | 0.840921 | 0.944240 |
| HF16 | eta_0 | 352 | 0.254732 | 0.196623 | 0.660649 | 0.826355 |
| M7A_new4 | eta_0 | 88 | 0.306337 | 0.257340 | 0.671009 | 0.715268 |
| HF20 | eta_0 | 440 | 0.265053 | 0.196623 | 0.667650 | 0.826355 |
| HF16 | eta_minus1 | 352 | 0.039872 | 0.014721 | 0.117917 | 0.291557 |
| M7A_new4 | eta_minus1 | 88 | 0.026105 | 0.017640 | 0.055969 | 0.124339 |
| HF20 | eta_minus1 | 440 | 0.037118 | 0.014955 | 0.099594 | 0.291557 |
| HF16 | R | 352 | 0.218569 | 0.199471 | 0.424901 | 0.733822 |
| M7A_new4 | R | 88 | 0.196515 | 0.159574 | 0.365415 | 0.485361 |
| HF20 | R | 440 | 0.214158 | 0.190080 | 0.402264 | 0.733822 |
| HF16 | T | 352 | 0.781177 | 0.800480 | 0.932451 | 0.974884 |
| M7A_new4 | T | 88 | 0.803250 | 0.839686 | 0.926936 | 0.947492 |
| HF20 | T | 440 | 0.785592 | 0.809698 | 0.928367 | 0.974884 |
| HF16 | PS_abs_eta_plus1 | 176 | 0.087624 | 0.061431 | 0.209312 | 0.501273 |
| M7A_new4 | PS_abs_eta_plus1 | 44 | 0.117839 | 0.037865 | 0.312153 | 0.484915 |
| HF20 | PS_abs_eta_plus1 | 220 | 0.093667 | 0.052405 | 0.233628 | 0.501273 |
| HF16 | PS_abs_eta_0 | 176 | 0.085800 | 0.028117 | 0.251835 | 0.549935 |
| M7A_new4 | PS_abs_eta_0 | 44 | 0.049462 | 0.037881 | 0.096159 | 0.171248 |
| HF20 | PS_abs_eta_0 | 220 | 0.078532 | 0.035601 | 0.236476 | 0.549935 |
| HF16 | PS_abs_eta_minus1 | 176 | 0.015473 | 0.008180 | 0.039355 | 0.084580 |
| M7A_new4 | PS_abs_eta_minus1 | 44 | 0.018940 | 0.011702 | 0.035246 | 0.093497 |
| HF20 | PS_abs_eta_minus1 | 220 | 0.016166 | 0.009061 | 0.039263 | 0.093497 |

The HF20 P/S contrast remains materially nonzero; polarization must remain an explicit condition.

## Common-HF16 learning value

| Model | order improved/degraded | eta(+1) improved/degraded | M8 R mean | M8 T mean | M8 P/S mean |
|---|---:|---:|---:|---:|---:|
| LF_affine | 10/6 | 5/11 | 0.104415 | 0.103884 | 0.090307 |
| LF_global_bias | 9/7 | 6/9 | 0.105318 | 0.104961 | 0.087624 |
| LF_only | 0/0 | 0/0 | nan | 0.218823 | 0.087624 |
| LF_paired_shared_contrast | 9/7 | 6/10 | 0.071097 | 0.069826 | 0.133056 |
| LF_ridge_residual | 9/7 | 7/9 | 0.071097 | 0.075220 | 0.090307 |
| circular_cnn | 12/4 | 11/5 | 0.069809 | 0.164532 | 0.096390 |
| corrected_residual_mlp | 9/7 | 10/6 | 0.063899 | 0.080073 | 0.121922 |
| direct_mlp | 14/2 | 11/5 | 0.062739 | 0.174648 | 0.105578 |
| resmlp | 14/2 | 9/7 | 0.061902 | 0.102635 | 0.091287 |

The geometry-level paired deltas are mixed. Direct MLP/ResMLP improve many common geometries but remain poor globally; LF-ridge has 9 improved / 7 degraded and a small negative median order delta. This is targeted learning value, not uniform generalization improvement.

## M7A new4 held-out difficulty

| Model | worst order MAE | worst eta(+1) MAE | worst R MAE | worst T MAE | worst P/S MAE |
|---|---:|---:|---:|---:|---:|
| LF_affine | 0.072441 | 0.260934 | 0.120009 | 0.125042 | 0.252338 |
| LF_global_bias | 0.071861 | 0.264700 | 0.126529 | 0.130266 | 0.281309 |
| LF_only | 0.073799 | 0.324684 | nan | 0.327351 | 0.281309 |
| LF_paired_shared_contrast | 0.071585 | 0.177024 | 0.073703 | 0.050707 | 0.228473 |
| LF_ridge_residual | 0.070647 | 0.181877 | 0.073703 | 0.068941 | 0.252339 |
| circular_cnn | 0.076339 | 0.147511 | 0.072673 | 0.380820 | 0.260418 |
| corrected_residual_mlp | 0.061758 | 0.210793 | 0.064253 | 0.147965 | 0.301196 |
| direct_mlp | 0.174147 | 0.424799 | 0.062670 | 0.369427 | 0.212249 |
| resmlp | 0.118827 | 0.114894 | 0.067157 | 0.133772 | 0.176852 |

G01 `RESIDUAL-TAIL` remains the clearest difficult regime; G02/G03 show useful targeted information, but the new4 tail is not removed.

## M7A prospective-like acquisition audit

- The audit compares frozen M7 selection-time fields against M7A truth only; it does not use M8 predictions and is not an external test.

| Role | geometry | selection-time evidence |
|---|---|---|
| COVERAGE-CONTROL | K6X_D100_D105_D110_D115_D190_D230 | LF_only err=0.232406; LF_global_bias err=0.447388; LF_ridge_residual err=0.036992; corrected_residual_mlp err=0.020545; circular_cnn err=0.166090
| POLARIZATION-STRESS | K6X_D100_D105_D115_D165_D225_D230 | LF_only err=0.331601; LF_global_bias err=0.369794; LF_ridge_residual err=0.025206; corrected_residual_mlp err=0.000784; circular_cnn err=0.052508
| RANKING-CHAMPION-STRESS | K6X_D110_D125_D135_D150_D175_D195 | LF_only err=0.378812; LF_global_bias err=0.000579; LF_ridge_residual err=0.004947; corrected_residual_mlp err=0.007829; circular_cnn err=0.012964
| RESIDUAL-TAIL | K6X_D135_D155_D190_D220_D225_D230 | LF_only err=0.010798; LF_global_bias err=0.050840; LF_ridge_residual err=0.165765; corrected_residual_mlp err=0.165575; circular_cnn err=0.119409

Residual-tail and polarization/ranking stress roles were genuine informative acquisition choices; this supports targeted development but not external promotion.

## Residual structure and disagreement

- `residual_structure_by_geometry.csv`, `residual_structure_oof_by_geometry.csv`, and `hf_minus_lf_residual_summary.csv` retain per-geometry, P/S, wavelength/order residual evidence for LF, global-bias, affine and ridge baselines.
- Model disagreement is informative but not calibrated probability: high-disagreement η(+1) bucket error 0.087264 vs low 0.041426; high order-profile bucket 0.046785 vs low 0.023997.

## Promotion and governance

- Final decision: `MORE_TARGETED_DEVELOPMENT_HF_REQUIRED` — new4 retains a measurable error tail and no model passed all frozen gates.
- External set `NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1` remains metadata-only: 12 geometries / 24 future P/S logical cases. No target was read and no external solver ran.
- Concurrency governance remains `CONCURRENCY3_FUNCTIONAL_STABILITY_EVIDENCE_PRESENT`; max active FDTD 3 with 4 MPI × 1 thread, but CPU/RAM telemetry was unavailable, so throughput optimality is not claimed.
- No new HF, FDTD, LumAPI run, inverse design, angular extension, or external test was started.
- The surrogate remains a development candidate; it is not labeled `FORWARD_SURROGATE_FROZEN`.

## Validation and reproducibility

- Requirement audit: PASS; residual reconstruction max error 5.55e-17; symbolic order schema and T/order closure PASS; selection-time manifest fields preserved exactly; no inverse artifacts in M8 output.
- Regression suite: 26 passed across M5, M5B, M7, M7A and M8 focused tests. Standalone M8 validator: PASS. `git diff --check`: PASS.
- Training fit completed before a post-processing selection-schema mismatch was discovered; recovery was post-processing-only and did not rerun fit or solver.

Evidence directory: `outputs\np_k6_m8_20g_forward_retraining_v1\`.
