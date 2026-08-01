# POST_D8_REVISED_QUADRATIC_MAP_EVIDENCE_CLOSURE_AND_ROUTE_DECISION_V2

## Status
`REVISED_QUADRATIC_MODEL_PHASE_VALID_PROJECTOR_PARTIAL`

## Evidence closure
- Coordinates/baseline/aliases/new/unique: 27/9/5/13/22
- New physics: 26 planned subruns; actual checkpoint records 26; accepted 26; recovered 0; failed 0; missing 0.
- New complete Jones: 13/13; unique complete Jones: 22/22.
- Reuse: 5/5 trusted formal mappings, no alias reweighting.

## Quadratic replay
- Rank 10/10; condition number 6.10534.
- Gradient [0.12780655857798653, -0.058180142248077674, -0.011487106166991407].
- Hessian eigenvalues [-0.1806998763462342, 0.8600209779282927, 1.2258688003442042].
- Phase LOO mean/max 0.532323/1.87722 degree.
- Central-gradient reference [0.538505, -0.150746, -0.027266] differs from fitted gradient because the fit uses actual quantized 22-row geometry and curvature.

## Projector/Jones closure
Continuous Jones/projector metrics were replayed from formal complex fields. Independent family/source holdout contracts were not present, so the result is `PHASE_VALID_PROJECTOR_PARTIAL`; no projector PASS threshold was invented.

## Route
Offline decision only. No D9 authorization, no new geometry, no solver/lumapi/FDTD, no canonical mutation. Future work requires explicit user authorization.

## Pareto summary

The 10 unique-only Pareto candidates and their phase/Txx/Tyy/leakage/sigma2-ratio/projector alignment are recorded in `outputs/lp_ml_dataset_v1/analysis/b120_j2lm06_post_d8_revised_pareto_v2.json`. Lowest phase, strongest projector, and best trade-off are explicitly identified there.
