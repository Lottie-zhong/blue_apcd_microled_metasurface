# NP K6 M5B Forward Formulation Repair and Clean Reevaluation v1

Status: `NP_K6_M5B_FORMULATION_REPAIR_COMPLETE_MORE_DEVELOPMENT_HF_REQUIRED`

## Governance

- M5B preregistration: `NP_K6_M5B_FORMULATION_REPAIR_PREREG_V1`, SHA256 `222dbc1a544a5d749c8eb7d769111101033c870e0e498d28affa903915379eac`
- Output schema registry SHA256 `ce71c3cbaa233a7e5d776cbc464ea3a814dc6c5f61777fc17180a2322625f448`; refit addendum SHA256 `80c989edbf58e18ab6b98e7413d7a2e6dc2b7a2ef702b5f5051239a1ad41dfb2`
- ZERO-SOLVER: FDTD/LumAPI run 0; external HF 0; sealed HF target reads 0; inverse design 0.
- M5 and M5A frozen evidence was not overwritten.

## Authoritative output contract

- Primary vector: `['R', 'eta_m-3', 'eta_m-2', 'eta_m-1', 'eta_m+0', 'eta_m+1', 'eta_m+2', 'eta_m+3']`
- `eta(+1)` symbolic key: `eta_m+1`; full-vector index `5`
- `T` is derived as the sum of all tracked transmitted eta orders; `R` is primary.
- Ordered physical D1...D6 retained; current capability remains `NORMAL_INCIDENCE_ONLY` (u_x=0).

## Historical implementation issues and corrected replay

1. Frozen residual OOF represented `delta=HF-LF`; M5B reconstructs `eta_hat=LF_eta+delta_hat` and keeps R as a direct head.
2. Frozen ranking used eta index 4; M5B uses the symbolic `eta_m+1` registry key (index 5). The old metrics remain retained and are marked superseded by corrected ranking.

## Corrected refit comparison (constrained projection)

| model | order MAE | eta(+1) MAE | R MAE | T MAE | rho | top-3 | top-5 | champion rank | worst geometry MAE | P/S contrast MAE | physics |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| LF_only_frozen | 0.04291 | 0.10621 | nan | 0.19949 | 0.9341 | 0.667 | 1.000 | 3 | 0.07859 | 0.09582 | FAIL |
| LF_global_bias | 0.03376 | 0.07188 | 0.09733 | 0.09980 | 0.9560 | 0.667 | 1.000 | 1 | 0.07345 | 0.09582 | PASS |
| LF_wavelength_polarization_affine | 0.04569 | 0.07404 | 0.12731 | 0.13543 | 0.9615 | 0.667 | 1.000 | 4 | 0.09365 | 0.10178 | PASS |
| LF_ridge_residual | 0.04559 | 0.07374 | 0.12731 | 0.13543 | 0.9615 | 0.667 | 1.000 | 4 | 0.09354 | 0.10174 | PASS |
| LF_paired_shared_contrast | 0.05164 | 0.08836 | 0.12523 | 0.12659 | 0.9451 | 0.667 | 1.000 | 4 | 0.10525 | 0.15664 | PASS |
| corrected_residual_mlp | 0.07012 | 0.09623 | 0.10327 | 0.10686 | 0.8901 | 0.667 | 1.000 | 5 | 0.14593 | 0.10054 | PASS |
| M5_direct_MLP_frozen | 0.08380 | 0.24466 | 0.08178 | 0.14394 | 0.5110 | 0.333 | 0.600 | 8 | 0.22127 | 0.10808 | PASS |
| M5_ResMLP_frozen | 0.08263 | 0.25536 | 0.09455 | 0.10509 | 0.3571 | 0.333 | 0.600 | 9 | 0.24020 | 0.12068 | PASS |
| M5_CircularCNN_frozen | 0.06136 | 0.12821 | 0.08062 | 0.22339 | 0.7857 | 0.333 | 0.800 | 6 | 0.13617 | 0.09972 | FAIL |
| M5B_corrected_no_refit_residual_mlp | 0.05277 | 0.12487 | 0.08038 | 0.08537 | 0.8626 | 0.667 | 1.000 | 4 | 0.14090 | 0.13675 | PASS |

## Promotion decision

- No learned full-response candidate passed all frozen gates simultaneously.
- LF global bias has the strongest constrained numerical calibration, but its P/S contrast gate fails; it is not promoted as a frozen surrogate.
- Corrected residual MLP is physically legal after projection but remains inferior on order-profile, worst-case and P/S gates.
- Final M5B status: `NP_K6_M5B_FORMULATION_REPAIR_COMPLETE_MORE_DEVELOPMENT_HF_REQUIRED`.

## P/S and coupling audit

- P/S remains an explicit condition; no averaging or equivalence assumption was introduced.
- Corrected residual MLP constrained eta(+1) MAE: P `0.10934`, S `0.08312`, P/S contrast MAE `0.10054`.
- M5B remains a power-level model; complex labels are not promoted.

## HF9 comparison

See `m5b_common_hf9_comparison.json`; membership is metadata-only and historical M3/M5 numbers are not pooled into the M5B gate.

## External HF readiness

- Registry: `NP_K6_FORWARD_EXTERNAL_FROZEN_SET_V1`.
- 12 sealed geometries, paired P/S, 445–455 nm, u_x=0; future budget 24 logical HF cases.
- This round read metadata only; sealed targets and external HF remain unread.
- Because no corrected development candidate passes all gates, external HF authorization is not activated.

## Reproducibility and safety

- Refit manifest: `outputs\np_k6_m5b_forward_formulation_repair_v1\m5b_refit_manifest.json` (refit_count=1, LOGO=13, seeds=[17, 29, 43]).
- Candidate OOF: `m5b_refit_candidate_oof.csv`; ranking: `m5b_refit_ranking_metrics.csv`; gates: `m5b_promotion_gate.csv`.
- Validator: `m5b_validator_report.json`; solver audit: `m5b_solver_zero_audit.json`.
- No FSP, checkpoint, runtime log or sealed target was created or read by M5B.

## Next gate

Recommend a zero-solver error-region acquisition design review; do not run HF, external test, angular extension or inverse design automatically.
