# NP K6 M6 error-region acquisition design-only v1

## Status

`NP_K6_M6_ERROR_REGION_ACQUISITION_DESIGN_READY_FOR_SOLVER_AUTHORIZATION`

This is a zero-solver development design artifact. No FDTD/LumAPI solver run, external HF target read, sealed target read, or inverse-design artifact was created.

## Frozen preregistration

- ID: `NP_K6_M6_ERROR_REGION_ACQUISITION_PREREG_V1`
- SHA256: `9f7e578d2b54c571206d8537a1fb6aa72b16e37f85f9c179097c94e6c81794e8`
- Created: `2026-08-11T17:32:59.960471+00:00`
- The preregistration was written before final Primary4/backups identities.

## Authority and candidate universe

- M4 effective development pool: **39**
- Current HF development geometries excluded: **4**; post-exclusion overlap: `[]`
- External frozen registry: **12** metadata-only geometries; candidate overlap: `[]`
- Final eligible development candidates: **35**
- Duplicate geometry hashes: `False`; physical-order violations: `[]`
- Candidate scores use frozen M4 predicted profiles and HF13 LF residual bias only as heuristic acquisition proxies; they are not HF truth or calibrated probabilities.

## Primary4 and expansion

| Rank | Role | Geometry | Geometry hash |
|---:|---|---|---|
| 1 | ERROR-1 | `K6X_D110_D125_D130_D135_D140_D175` | `714b47fc14f3ebf1b6ebfe7d011e9924fa714cc1c261035eb4ad86c2fc7aabdf` |
| 2 | POLARIZATION-STRESS | `K6X_D110_D190_D210_D215_D220_D225` | `02a7beacb7a5e503de03a7aae4857727444d893b2052182e874bb2b2f32680e7` |
| 3 | COVERAGE-EXTRAPOLATION-CONTROL | `K6X_D150_D205_D215_D220_D225_D230` | `1378d30bbda23695267aae4a889c45ff266766efe10cbac3e7ee6cb40fb7be18` |
| 4 | PERFORMANCE+ERROR | `K6X_D105_D120_D125_D130_D165_D190` | `4191675fbcc4312feb77afe9a40a7c767fc01e54e6775d3a2439de9cc47fdf7b` |

Backups (ranked):
1. `K6X_D160_D165_D170_D175_D180_D220`
2. `K6X_D105_D110_D115_D120_D135_D200`
3. `K6X_D100_D110_D120_D125_D130_D205`
4. `K6X_D100_D160_D165_D170_D175_D185`
5. `K6X_D135_D155_D190_D220_D225_D230`
6. `K6X_D125_D135_D145_D150_D155_D160`
7. `K6X_D105_D125_D135_D155_D160_D165`
8. `K6X_D105_D110_D165_D200_D215_D220`

- First6: `K6X_D110_D125_D130_D135_D140_D175, K6X_D110_D190_D210_D215_D220_D225, K6X_D150_D205_D215_D220_D225_D230, K6X_D105_D120_D125_D130_D165_D190, K6X_D160_D165_D170_D175_D180_D220, K6X_D105_D110_D115_D120_D135_D200`
- First8: `K6X_D110_D125_D130_D135_D140_D175, K6X_D110_D190_D210_D215_D220_D225, K6X_D150_D205_D215_D220_D225_D230, K6X_D105_D120_D125_D130_D165_D190, K6X_D160_D165_D170_D175_D180_D220, K6X_D105_D110_D115_D120_D135_D200, K6X_D100_D110_D120_D125_D130_D205, K6X_D100_D160_D165_D170_D175_D185`
- Primary4 role quota: satisfied exactly once for ERROR-1, POLARIZATION-STRESS, COVERAGE-EXTRAPOLATION-CONTROL, and PERFORMANCE+ERROR.

## Baseline comparison and coverage

| Set | Size | Mean nearest distance after | P90 after | Max after | Top-quartile eta residual covered | Top-quartile P/S risk covered |
|---|---:|---:|---:|---:|---:|---:|
| proposed_primary4 | 4 | 2.02536 | 3.41924 | 4.0871 | 0.25 | 0.25 |
| random4_seed_20260812 | 4 | 1.89367 | 3.49539 | 4.14263 | 0.375 | 0.125 |
| performance_only_top4 | 4 | 2.24242 | 3.51317 | 4.24553 | 0 | 0 |
| coverage_only_top4 | 4 | 1.80693 | 3.12572 | 3.49539 | 0 | 0.375 |
| proposed_first6 | 6 | 1.79181 | 3.41924 | 4.0871 | 0.5 | 0.25 |
| proposed_first8 | 8 | 1.59135 | 3.15613 | 4.0871 | 0.625 | 0.375 |

- Primary4→first6 mean-distance change: `-0.233545`
- First6→first8 mean-distance change: `-0.200463`
- Baseline rows are descriptive comparisons over the identical 35-candidate universe; they do not establish prospective superiority.

## Empirical cost package

- Clean completed-ledger sample count: **24**
- Median / P90 / max case runtime: **0.922982 / 3.80035 / 4.48604 h**
- Infrastructure-loss note: `1` case(s) tracked separately; no fixed three-hour assumption used.

| Batch | Logical P/S cases | Median total h | P90 total h | Max total h |
|---|---:|---:|---:|---:|
| Primary4 | 8 | 7.38386 | 30.4028 | 35.8883 |
| first6 | 12 | 11.0758 | 45.6042 | 53.8324 |
| first8 | 16 | 14.7677 | 60.8056 | 71.7766 |

These are planning estimates only; no solver was launched in M6.

## Governance and next gate

- External registry `NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1` remains metadata-only, with `0` sealed target reads and no training intersection.
- External HF budget remains future-only: 12 geometries × P/S = 24 logical cases.
- Prospective validation is distinct from external test and active-learning training; predictions must be frozen before any future authorized HF run.
- Recommended next action: request explicit authorization for the M6 Primary4 HF acquisition (8 logical P/S cases) only after this design is reviewed. This document itself authorizes no solver.

## Zero-solver evidence

- FDTD run calls: `0`
- LumAPI solver run calls: `0`
- External HF calls: `0`
- Sealed HF target reads: `0`
- Inverse-design artifacts: `0`

