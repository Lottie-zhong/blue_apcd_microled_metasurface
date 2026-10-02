# COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2

STATUS: COMPLETE_ZERO_SOLVER_CPU_ONLY

Frozen V2 contract SHA256: 3c6b0bb9d498982811910a4be2da87e13ad82eba2a3bc493140bdd6834688081. Solver invocations: 0; GPU/Runner invocations: 0; additional HF: 0.
Dataset: 32 frozen ordered geometries; paired P/XLIKE 445-455 nm at 1 nm; 352 geometry-wavelength rows / 2464 order rows.
NP V2: 220 cached queries exact runtime parity plus 132 new-geometry deterministic runtime queries; HF22 exact overlap 0/32; runtime-domain valid 32/32.
Truth-state parity to archived 20G labels max absolute difference: 2.78e-16; modal-to-routing closure max: 0.000336545.

## Confirmatory questions

Q1 routing: A0 median/q95 0.212318/0.32283; A1 0.195806/0.277463; A1-A0 paired wins/ties/losses 20/0/12; Pearson A0/A1 0.783203/0.812909.
Q1 absolute order source-normalized: A0 median/q95 0.1036/0.168439; A1 0.100666/0.144665. Thresholded relative median/q95 A0 0.900498/0.963115; A1 0.850679/0.928898.
Q2 complex state: A0 median/q95/worst 0.805084/1.17442/1.26394; A1 0.79453/1.15998/1.16697.
Q3 20G-to-32G feature-effect classification: REVERSES (routing and source-normalized absolute-order paired geometry median deltas; see comparison JSON).
Q4 production H1 unchanged: frozen 32G baseline H1 FAIL; confirmatory retrospective gates A0/A1 FAIL/FAIL; production remains NOT_ADMITTED because prospective six-geometry gate was not run.

## 20G vs 32G paired feature effects

| Metric | 20G median(A1-A0) | 32G median(A1-A0) | 20G wins/ties/losses | 32G wins/ties/losses |
|---|---:|---:|---:|---:|
| State | -0.00341699 | -0.0154919 | 11/0/9 | 21/0/11 |
| Routing | -0.00231053 | -0.00206892 | 12/0/8 | 20/0/12 |
| Absolute order | -0.00132699 | 0.00142495 | 12/0/8 | 15/0/17 |
| Thresholded absolute | -0.0193615 | -0.0253572 | 12/0/8 | 24/0/8 |
| P_scale | -2.67224e-07 | -0.00661459 | 10/0/10 | 19/0/13 |

Feature value verdict: COUPLING_ML_NP_FORWARD_FEATURES_PARTIAL. 32G preregistered supported gate: {"absolute_and_pscale_median_q95_no_worse": false, "both_medians_5pct_and_20_wins": false, "nearest_far_sign_mixed": false, "q95_10pct": true, "seed_stable": true, "worst_25pct": true}.
20G feature verdict was COUPLING_ML_NP_FORWARD_FEATURES_PARTIAL; 32G feature-effect replication status is REVERSES.
20G and 32G H1 are independent frozen production authorities; baseline conclusion remains DATA_COVERAGE_NOT_PRIMARY_BOTTLENECK. No production H1 admission was changed.
OOD/support strata are diagnostic only and were never passed to either predictor. NP LF features are auxiliary proxies, not integrated truth, a scattering operator, Jones matrix, or MDCxNP cascade.
A2/A3 remain unavailable. No new model family, HF, prospective gate, inverse design, solver, or GPU work was run.

## OOD support strata

- nearest n=11: median state delta=-0.0346041 (wins 8), routing delta=-0.012017 (wins 8).
- middle n=11: median state delta=-0.00741714 (wins 8), routing delta=-0.000321749 (wins 6).
- farthest n=10: median state delta=-0.00252858 (wins 5), routing delta=-0.00106449 (wins 6).

## H1 metrics

| Arm | State median/q95 | Routing median/q95/Pearson | Absolute median/q95 | Thresholded median/q95 | P_scale median/q95/Pearson | Seed std | H1 |
|---|---|---|---|---|---|---:|---|
| A0 | 0.805084/1.17442 | 0.212318/0.32283/0.783203 | 0.1036/0.168439 | 0.900498/0.963115 | 0.167196/0.524672/0.850142 | 0.0153699 | FAIL |
| A1 | 0.79453/1.15998 | 0.195806/0.277463/0.812909 | 0.100666/0.144665 | 0.850679/0.928898 | 0.118075/0.551717/0.871896 | 0.0112545 | FAIL |

NEXT: CHART_REVIEW_32G_H1_AND_NP_FEATURE_CONFIRMATORY_RESULT (not executed).
