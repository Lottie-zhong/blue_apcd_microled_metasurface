# R2-4D5A Shortlist TE/TM Off-Axis Risk Review

No FDTD, Lumerical, lumapi, setup-only FSP, LDF, MAT/H5, or raw monitor data were created.

## Reviewed Candidates

D5_BASE_13461, D5_BASE_13481, D5_BASE_13881, D5_BASE_14322, D5_BASE_08955

## Primary TM 30-40 Risk

D5_BASE_13461 TM 30-40 minimum phase error is 6.524 deg at 34.50 deg. Widths inside 30-40 deg: <10 deg = 0.75 deg, <15 deg = 1.50 deg, <20 deg = 1.50 deg. Interpretation: `narrow_localized`.

## Setup-Only Readiness

| candidate | ready | TM risk | width <10 | width <15 |
|---|---:|---|---:|---:|
| D5_BASE_13461 | True | narrow_localized | 0.75 | 1.50 |
| D5_BASE_13481 | True | narrow_localized | 0.75 | 1.25 |
| D5_BASE_13881 | True | narrow_localized | 0.50 | 1.00 |
| D5_BASE_14322 | True | narrow_localized | 0.75 | 1.00 |
| D5_BASE_08955 | True | narrow_localized | 0.50 | 0.75 |

## Decision

`A_only_D5_BASE_13461`

Keep only D5_BASE_13461 for R2-4D6. Its TM 30-40 risk is classified as localized enough by the fine scan, and no backup improves the risk enough to justify extra setup files.

This remains a TMM phase risk review. Physical validation still requires x-line x-dipole FDTD after setup-only geometry inspection.
