# COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_20G_V2

STATUS: COMPLETE_ZERO_SOLVER_OFFLINE_ML
Frozen contract SHA256: 3c6b0bb9d498982811910a4be2da87e13ad82eba2a3bc493140bdd6834688081. Solver invocations: 0. CPU only.
Dataset: 20 valid integrated 3D PW geometries; paired P/XLIKE 445-455 nm, 1 nm; 220 sample rows / 1540 order rows.
NP cache/runtime: 220/220; representative exact runtime parity 15/15; HF22 overlap 0/20; all OOD.

| Metric | A0 median | A0 q95 | A1 median | A1 q95 |
|---|---:|---:|---:|---:|
| State relative RMSE | 0.749614 | 1.00496 | 0.746904 | 1.12361 |
| Routing eta RMSE | 0.17487 | 0.293987 | 0.171762 | 0.238216 |
| Abs-order source-normalized RMSE | 0.0914416 | 0.158274 | 0.0914029 | 0.124397 |
| Thresholded abs-order relative | 0.857088 | 0.95775 | 0.849706 | 0.905182 |
| P_scale relative RMSE | 0.140073 | 0.401246 | 0.135937 | 0.405679 |

Feature verdict: COUPLING_ML_NP_FORWARD_FEATURES_PARTIAL. Median improvements A1 vs A0: state 0.362%; routing 1.777%.
State wins/ties/losses: {'losses': 9, 'ties': 0, 'wins': 11}; routing: {'losses': 8, 'ties': 0, 'wins': 12}.
Worst held-out state geometry: A0 K6V1_EXT08 (1.11881); A1 K6V1_EXT06 (1.18721).
Worst held-out routing geometry: A0 K6V1_EXT08 (0.357004); A1 K6V1_EXT08 (0.281257).
Routing Pearson A0/A1: 0.81774/0.854378; P_scale Pearson: 0.882221/0.875876.
Seed state-median std A0/A1: 0.00475649/0.0170119.

OOD-stratified paired A1-A0 median deltas (negative favors A1):
- nearest (n=7): state -0.0328138; routing -0.00217029; state/routing wins 6/5.
- middle (n=7): state 8.33915e-05; routing -0.005488; state/routing wins 3/4.
- farthest (n=6): state 0.014277; routing -0.00391351; state/routing wins 2/3.

Retrospective H1 gates: A0 FAIL {'absolute': False, 'pscale': False, 'routing': False, 'seed': True, 'state': False, 'threshold': False}; A1 FAIL {'absolute': False, 'pscale': False, 'routing': False, 'seed': True, 'state': False, 'threshold': False}.
Production H1: NOT_ADMITTED; prospective six-geometry prediction-before-truth gate not run. Prospective six-geometry prediction-before-truth gate not run.
The 20G result supports only partial incremental NP LF feature value: median improvements are below the preregistered 5% joint criterion; paired wins are 11/20 state and 12/20 routing; the OOD effect is mixed and state q95 worsens.
Qualitative no-material-degradation for key absolute-order and P_scale metrics was conservatively operationalized as no worsening of median or q95; no threshold added.
NP features are low-fidelity single-pillar proxies, not standalone truth for Coupling geometries, integrated MDC-NP truth, C_component, a complex scattering operator, Jones response, or MDC-TMM phase.
Truth route decoder closure median/q95/max abs eta error: 2.85852e-05/0.000175411/0.000330951.
OOD strata identities/distances and per-geometry deltas are in ood_support_analysis_v2.json; D180 provenance warnings and S16 sidecar exception are preserved.
Packaging recovery: all outer-fold logs, OOF predictions, paired metrics and leakage audit were persisted before a post-fit OOD-summary key mismatch interrupted packaging. Remaining diagnostics/report/hash were generated from saved outputs; no refit occurred.
NEXT: COUPLING_ML_NP_FORWARD_FEATURE_ABLATION_32G_CONFIRMATORY_V2 only after a valid 32G authority; not executed.
