# LP-ML Six-Bin Inverse-Design Planning Contract v1

## Status

`LP_ML_INVERSE_PLANNING_CONTRACT_READY`

This is an offline planning freeze only. No candidate geometry was generated, no runnable solver package was created, and solver/FDTD calls = 0.

## Frozen inputs and model roles

Clean v2 remains 255 Round-1 geometries / 2295 rows, 64 Round-2 geometries / 576 rows, and 319 merged geometries / 2871 rows. Geometry 054 is quarantined with zero admitted rows. C0 remains the current champion/global guard; the C0/C1 alpha=0.95 blend is the primary planning challenger; C1-C4 seed ensembles provide dispersion and model-disagreement diagnostics, not confidence intervals.

## Target Jones and six-bin convention

Each target is a complete complex Jones matrix `J_target,k = complex_scalar_k * P_APCD`, with `complex_scalar_k = rho_k exp(i(phi_offset + 60 k degrees))`. The common phase offset is free and scored modulo the 60-degree equivalence. The projector shape is scalar-invariant and uses `min_c ||J-cP_APCD||_F / ||J||_F`; ambiguous legacy projection-error aliases are not used.

## Inverse objective

The objective combines circular phase error, scalar-invariant projector shape error, sigma2/sigma1, raw-Jones leakage, throughput, spectral endpoint/slope/curvature/order stability, ensemble uncertainty, C0/blend disagreement, and a hard manufacturing gate. Normalization is from clean train/validation residual distributions only; frozen tests cannot tune weights.

## Tuple and Pareto policy

Six-bin selection is Pareto-based across phase, projector, throughput, leakage, rank, spectral stability, consensus, uncertainty, manufacturing margin and geometric diversity. No bin has a single authoritative champion; high-disagreement candidates cannot be sole representatives.

## Future validation hierarchy

Surrogate-only Pareto filtering precedes C0/blend consensus, separately authorized single-dimer FDTD, assimilation, tuple selection, full-K6 full-wave validation, and finally broadband/tolerance/source-weighted integration. Constituent-additive predictions cannot substitute for K6 full-wave validation.

## Future budget proposal

Planning envelope only: 6-10 geometries per bin (36-60 total), x/y subruns if authorized (72-120 total), 450 nm only. This task authorizes none of those solver calls.

## Hard gates

Clean hashes, protected reports, model checkpoint hashes and quarantine boundary must remain unchanged before any future candidate generation. No Round-3, inverse FDTD, six-bin promotion, K6 execution, geometry 054 use, or test-guided weighting is permitted here.
