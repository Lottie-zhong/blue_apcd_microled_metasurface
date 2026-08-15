# NP K6 M7A targeted development HF acquisition design v1

**Status:** `NP_K6_M7A_TARGETED_DEVELOPMENT_ACQUISITION_READY_FOR_SOLVER_AUTHORIZATION`

## Scope and governance

Zero-solver design-only stage. No FDTD/LumAPI run, external target read, sealed target read, inverse artifact, or training promotion was performed. u_x remains 0 and ordered physical D1...D6 is preserved. G01 (`K6X_D110_D125_D130_D135_D140_D175`) is permanently excluded and is not a supplemental or replacement geometry.

Preregistration SHA256: `bd221dfe8d15475cb5c0f9d5959a6595fed2238ff58f7ca1befbdc421bf65951`. Candidate source count was 35; eligible development universe after formal-HF/external/G01 exclusions is 31. Formal-HF overlap after exclusion is zero; external overlap is zero.

## Primary4 and backups

| tier | geometry | role | ranking ambiguity | residual-tail | P/S risk | nearest-HF distance |
|---|---|---|---:|---:|---:|---:|
| Primary4 | K6X_D135_D155_D190_D220_D225_D230 | RESIDUAL-TAIL | 0.2923 | 0.7960 | 0.7342 | 2.1470 |
| Primary4 | K6X_D110_D125_D135_D150_D175_D195 | RANKING-CHAMPION-STRESS | 0.3704 | 0.2786 | 0.2386 | 0.4234 |
| Primary4 | K6X_D100_D105_D115_D165_D225_D230 | POLARIZATION-STRESS | 0.1308 | 0.4827 | 0.8198 | 3.4954 |
| Primary4 | K6X_D100_D105_D110_D115_D190_D230 | COVERAGE-CONTROL | 0.2563 | 0.6300 | 0.6597 | 4.2455 |
| backup | K6X_D105_D110_D165_D200_D215_D220 | backup | 0.2039 | 0.6213 | 0.4071 | 3.1561 |
| backup | K6X_D100_D140_D165_D190_D225_D230 | backup | 0.2019 | 0.4983 | 0.4932 | 3.2252 |
| backup | K6X_D160_D165_D170_D175_D180_D220 | backup | 0.2995 | 0.3576 | 0.6087 | 2.4976 |
| backup | K6X_D135_D160_D165_D205_D210_D215 | backup | 0.2228 | 0.3857 | 0.6103 | 2.6277 |
| backup | K6X_D105_D110_D115_D125_D165_D230 | backup | 0.3551 | 0.3630 | 0.2752 | 3.3135 |
| backup | K6X_D105_D110_D115_D120_D135_D200 | backup | 0.3342 | 0.4034 | 0.2752 | 2.7749 |
| backup | K6X_D100_D110_D120_D125_D130_D205 | backup | 0.3541 | 0.3819 | 0.2439 | 3.1257 |
| backup | K6X_D100_D115_D135_D165_D220_D230 | backup | 0.1816 | 0.3018 | 0.4448 | 2.5227 |

first6 = K6X_D135_D155_D190_D220_D225_D230, K6X_D110_D125_D135_D150_D175_D195, K6X_D100_D105_D115_D165_D225_D230, K6X_D100_D105_D110_D115_D190_D230, K6X_D105_D110_D165_D200_D215_D220, K6X_D100_D140_D165_D190_D225_D230
first8 = K6X_D135_D155_D190_D220_D225_D230, K6X_D110_D125_D135_D150_D175_D195, K6X_D100_D105_D115_D165_D225_D230, K6X_D100_D105_D110_D115_D190_D230, K6X_D105_D110_D165_D200_D215_D220, K6X_D100_D140_D165_D190_D225_D230, K6X_D160_D165_D170_D175_D180_D220, K6X_D135_D160_D165_D205_D210_D215

Candidate predictions are design-time full-development M7 fits and LF/M6 frozen proxies; they are not HF truth or calibrated uncertainty. Detailed wavelength/P/S values are in `candidate_predictions_long.csv`.

## Baseline comparison

| baseline | role coverage | residual coverage | ranking coverage | P/S coverage | geometry diversity | LF-response diversity | redundancy |
|---|---:|---:|---:|---:|---:|---:|---:|
| proposed | 4 | 0.7495 | 0.2625 | 0.6338 | 38.6564 | 0.0504 | 0.6214 |
| performance-only | 1 | 0.5709 | 0.3732 | 0.1276 | 6.2784 | 0.0033 | 0.5364 |
| residual-only | 2 | 0.8768 | 0.2717 | 0.5033 | 45.8414 | 0.0769 | 0.5236 |
| coverage-only | 2 | 0.7470 | 0.1982 | 0.6264 | 29.6385 | 0.0500 | 0.4656 |
| random4 | 1 | 0.4253 | 0.1739 | 0.5346 | 45.6187 | 0.0569 | 0.5773 |

The proposed Primary4 is selected for expected information value and four-role coverage only; it is not declared superior by unseen HF performance. The marginal 4→6→8 audit is in `marginal_4_6_8_audit.csv`.

## Solver budget proposal (not executed)

| batch | logical P/S cases | median h | P90 h | max h |
|---|---:|---:|---:|---:|
| Primary4 | 8 | 7.384 | 30.403 | 35.888 |
| first6 | 12 | 11.076 | 45.604 | 53.832 |
| first8 | 16 | 14.768 | 60.806 | 71.777 |

Runtime authority is 4 MPI processes × 1 thread with verified concurrency=2. This stage only proposes cost; it does not create scheduler tasks or run cases.

## Decision

Authorize at most Primary4 for the next development HF gate if desired. first6/first8 are expansion proposals, not automatic execution. External HF remains unauthorized and the frozen 12-geometry metadata-only registry is unchanged.
