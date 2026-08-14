# Stage H1B-0 - Fixed-H Ranking and Targeted Manifold Reconnaissance

- Status: COMPLETE_OFFLINE_ZERO_SOLVER
- New FDTD / RCWA / physics solver entered: 0; scheduler invoked: False.
- Inputs: committed H1A accepted tables and H0 exact-anchor manifest only; no synthetic fixture admitted.

| H | full-Jones | raw span | compatible | compatible span | max pair | sector gap | C(H) | RMS | max residual |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 400 | 6 | 39.312615 | 3 | 14.118944 | 14.118944 | 45.881056 | 342.502392 | 2.727327 | 4.625644 |
| 450 | 6 | 39.147748 | 3 | 12.916021 | 12.916021 | 47.083979 | 352.279425 | 2.558512 | 4.643494 |
| 500 | 6 | 44.844206 | 3 | 17.564728 | 17.564728 | 42.435272 | 0.000000 | 0.000000 | 0.000000 |
| 550 | 6 | 41.738882 | 3 | 30.096722 | 30.096722 | 29.903278 | 0.169375 | 8.610432 | 15.288115 |
| 600 | 6 | 26.239342 | 3 | 5.505242 | 5.505242 | 54.494758 | 347.854299 | 17.152480 | 35.451890 |

## Ranking
- PRIMARY_H_CANDIDATE: 550 nm.
- SECONDARY_H_CANDIDATE: 400 nm, 450 nm.
- CONTROL_H: 500 nm.
- Pareto core front: 400 nm, 450 nm, 500 nm, 550 nm.
- Leave-one-anchor-out: H_RANKING_REASONABLY_STABLE_WITHIN_H1A_SAMPLE; primary survives all six removals: True.
- Most H-sensitive anchor: LPML_R2_HIGH_UNCERTAINTY_007; least: LPML_R1_GLOBAL_SOBOL_126.

## Gate and route

- Recomputed FLAG_60_SECTOR: False; frozen H1A flag: False.
- FLAG_120_ML_RESTART remains False.
- Recommended route: TARGETED_FULL_DIMER_EXPANSION.
- Proposed-only budget: 5 full-dimer geometry cases / 10 formal x+y subruns.
- Not authorized, not frozen, and not executed.

## Hypotheses

- All lateral-variable conclusions are HYPOTHESIS_GENERATING_ONLY with N=6.
- D/Psi are candidate directions for net H=600 versus H=400 phase-shift sign.
- J1_side is a candidate direction for H-dependent projector-quality variation.
- J2 anisotropy remains unresolved; no causal claim is admitted.

## Artifacts

- h1b0_fixed_h_ranking.csv
- h1b0_anchor_response.csv
- h1b0_sector_gap.json
- h1b0_leave_one_anchor_out.json
- h1b0_lateral_hypotheses.json
- h1b0_route_comparison.json
- h1b0_proposed_next_probe.json
