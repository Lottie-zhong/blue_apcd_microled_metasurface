# NP K6 M8 20G forward retraining and promotion review v1

Final state: `MORE_TARGETED_DEVELOPMENT_HF_REQUIRED`

## Authority and preregistration

- M8 preregistration: `NP_K6_M8_20G_FORWARD_RETRAINING_PREREG_V1`; SHA256 `fc05bc4d99cb54fa48558cda3605da53aa3fbda3f84c995a5493dfb820131ef9`.
- Formal HF authority: 440 rows, 20 geometries, 40 paired P/S cases, exact 445–455 nm, u_x=0 and k_y=0. Ordered [D1…D6] was preserved; no sorting or permutation-invariant compression.
- LF20 authority: 440/440 HF keys matched deterministic LF rows; LF remains explicitly polarization-blind at current normal-incidence scope. G01 quarantine absent; duplicate/conflicting provenance 0.
- External registry `NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1` remains metadata-only (12 geometries / 24 future P/S cases).

## Model comparison

| Model | order MAE | eta(+1) MAE | R MAE | T MAE | rank ρ | Top-3 | champion rank | worst geometry MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LF_only | 0.046238 | 0.104086 | unsupported | 0.209516 | 0.951880 | 0.333 | 4 | 0.081879 |
| LF_global_bias | 0.048299 | 0.100919 | 0.10346961518875901 | 0.104833 | 0.951880 | 0.333 | 4 | 0.079995 |
| LF_affine | 0.048824 | 0.101573 | 0.10336231575987123 | 0.105630 | 0.951880 | 0.333 | 4 | 0.077705 |
| LF_ridge_residual | 0.042516 | 0.082800 | 0.0683804426502917 | 0.072849 | 0.953383 | 0.667 | 4 | 0.102465 |
| LF_paired_shared_contrast | 0.044420 | 0.094435 | 0.06838044265029156 | 0.065777 | 0.953383 | 0.667 | 4 | 0.102752 |
| corrected_residual_mlp | 0.047085 | 0.089833 | 0.06065505436286495 | 0.080662 | 0.942857 | 0.667 | 6 | 0.108623 |
| direct_mlp | 0.071427 | 0.147215 | 0.05922856250731803 | 0.182714 | 0.864662 | 0.333 | 5 | 0.174147 |
| resmlp | 0.055300 | 0.109287 | 0.060106491197202495 | 0.093804 | 0.903759 | 0.333 | 4 | 0.120541 |
| circular_cnn | 0.047797 | 0.079635 | 0.06611742695733383 | 0.171506 | 0.933835 | 0.333 | 5 | 0.138530 |

The strongest numerical trainable result is `LF_ridge_residual` (order MAE 0.042516; η(+1) MAE 0.082800; R MAE 0.068380; T MAE 0.072849). No trainable candidate passed every preregistered promotion gate: champion rank, worst-case, energy residual and/or other gates remain limiting.

## Ranking, physics, and P/S

- Broadband ranking remains strong for LF/ridge families, but the true champion is predicted at rank 4 by the best numerical residual model; high global ρ alone is insufficient for promotion.
- Raw physics audits are retained beside constrained projections. Non-negative-power and energy residual violations remain nonzero before projection; projection is not counted as a physics proof.
- P/S contrast remains an explicit condition. Contrast MAE: LF-only 0.093667, LF-ridge 0.096101, corrected residual MLP 0.124541, circular CNN 0.101093.

## Common-HF16 learning value

| Model | improved geometries | degraded geometries | median Δ(M8−M7) | M7 mean | M8 mean |
|---|---:|---:|---:|---:|---:|
| LF_affine | 10 | 6 | -0.000243 | 0.048714 | 0.047894 |
| LF_global_bias | 9 | 7 | -0.000390 | 0.048009 | 0.047339 |
| LF_only | 0 | 0 | 0.000000 | 0.045825 | 0.045825 |
| LF_paired_shared_contrast | 9 | 7 | -0.001012 | 0.054775 | 0.044232 |
| LF_ridge_residual | 9 | 7 | -0.001041 | 0.041159 | 0.041428 |
| circular_cnn | 12 | 4 | -0.004874 | 0.060493 | 0.046684 |
| corrected_residual_mlp | 9 | 7 | -0.000168 | 0.046649 | 0.047644 |
| direct_mlp | 14 | 2 | -0.005293 | 0.079091 | 0.069221 |
| resmlp | 14 | 2 | -0.008874 | 0.069002 | 0.055651 |

The common-HF16 comparison shows mixed but generally modest geometry-level gains; it does not support a blanket claim that adding M7A always improves legacy unseen-geometry generalization.

## M7A new4 and prospective-like audit

The new4 held-out table is split by the frozen roles RESIDUAL-TAIL, RANKING-CHAMPION-STRESS, POLARIZATION-STRESS and COVERAGE-CONTROL. G01 residual-tail remains the clearest difficult point for learned residual models, while G02/G03 show useful targeted information.

The prospective-like audit uses only frozen M7 selection-time fields (LF, calibrated LF, ridge, residual MLP, CNN) against M7A truth. It is not external validation and is not retroactively replaced by M8 predictions.

## Decision and governance

- Decision: `MORE_TARGETED_DEVELOPMENT_HF_REQUIRED`.
- Rationale: new4 retains a measurable error tail and no model passed all frozen gates.
- External HF was not run or authorized automatically. No new development HF, inverse design, angular extension, or M8 follow-on acquisition was started.
- M7A concurrency evidence remains `CONCURRENCY3_FUNCTIONAL_STABILITY_EVIDENCE_PRESENT`; max active FDTD observed was 3 with 4 MPI × 1 thread, but continuous CPU/RAM telemetry was unavailable, so throughput-optimality is not claimed.

## Reproducibility and solver budget

- 20-fold LOGO, 3 deterministic seeds (17, 29, 43), fold-local normalization, 9 fixed model families; fit completed after preregistration hash `fc05bc4d99cb54fa48558cda3605da53aa3fbda3f84c995a5493dfb820131ef9`.
- Solver calls: FDTD=0, LumAPI run=0, external HF=0, sealed target reads=0, inverse design=0.
- OOF fit completed before a post-processing schema mismatch was found in the frozen selection manifest; post-processing was recovered using only actual frozen fields, without rerunning fit or solver.

## Evidence

- `outputs\np_k6_m8_20g_forward_retraining_v1\` contains preregistration, OOF predictions, raw/constrained metrics, ranking, P/S, common-HF16, new4, residual, disagreement, promotion and zero-solver audits.
- External promotion remains pending further targeted development; this report stops before any external FDTD.
