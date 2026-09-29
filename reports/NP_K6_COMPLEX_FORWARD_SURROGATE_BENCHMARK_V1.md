# NP_K6_COMPLEX_FORWARD_SURROGATE_BENCHMARK_V1

**Status:** `COMPLETE_ZERO_SOLVER`  
**Learnability verdict:** `COMPLEX_FORWARD_LEARNABILITY_PARTIAL`

## Source complex truth

- Dataset: `NP_K6_HF22_COMPLEX_SCATTERING_STATE_V1` from extraction commit `4f343b6`.
- 22 geometries × P/S × 11 wavelengths (445–455 nm); 44 logical cases, 8,712 complex state rows.
- Ordered geometry input `[D1,D2,D3,D4,D5,D6]`; transmission orders m=-3…+3; reflection orders m=-5…+5.
- Phase is raw monitor-plane phase; no arbitrary alignment or de-embedding. `FULL_2x2_JONES_MATRIX_NOT_AVAILABLE` (one incident column per P/S).
- Truth SHA256: `5937a30e9407bf71e45599883b888069c1f2894e29c49018e169ff5f2233294a`.

## RUN3C-P 448 nm forensic

- Classification: `RAW_POYNTING_CROSSCHECK_LOCAL_OUTLIER_COMPLEX_STATE_VALID`.
- Formal T = 0.5017703283; raw E/H signed-flux cross-check = 0.5320700792 (absolute discrepancy 0.0302997509).
- Complex modal sum = 0.5017703283; modal closure residual = -2.22e-16; sourcepower and monitor contract are finite and consistent.
- Same-geometry S branch at 448 nm raw cross-check error = 2.22e-15; row retained with explicit flag, no correction/removal.

## Frozen representation audit

- Phase significance threshold (frozen before model comparison): `0.000124632217633` absolute efficiency, `max(1e-8, 1st percentile of positive truth |c|²)`.
- PCA ranks (joint state, 90/95/99/99.9%): `{'0.9': 14, '0.95': 20, '0.99': 32, '0.999': 40}`.
- Transmission joint rank: `{'0.9': 7, '0.95': 9, '0.99': 18, '0.999': 30}`; reflection joint rank: `{'0.9': 17, '0.95': 22, '0.99': 32, '0.999': 40}`.
- Geometry/state-distance Spearman: P `0.3438`, S `0.4223`.

## Split and model contract

- Outer CV: 22-fold Leave-One-Geometry-Out; both P/S and all 11 wavelengths held out together.
- M0 Ridge, M1 RBF KernelRidge, M2 compact MLP; M3 order-local spectral latent (fold-fitted PCA + Ridge). No full-data fit.
- Every scaler/PCA/latent transform was fitted inside the training geometries only.

## OOF comparison

| formulation/model | complex RMSE | norm median | norm q95 | phase MAE | T MAE | R MAE | eta(+1) RMSE | rank P / S |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| row_wise__M0_Ridge | 0.2383 | 1.0022 | 1.1599 | 1.5014 | 0.7395 | 0.2013 | 0.4687 | -0.4286 / -0.2151 |
| row_wise__M1_RBF_KernelRidge | 0.2237 | 0.9267 | 1.1967 | 1.3221 | 0.6621 | 0.1466 | 0.1842 | 0.9289 / 0.8995 |
| row_wise__M2_compact_MLP | 0.2642 | 1.0726 | 1.4839 | 1.5489 | 0.6749 | 0.1777 | 0.4163 | 0.0943 / 0.0570 |
| spectral__M0_Ridge | 0.2725 | 0.9585 | 2.1944 | 1.3390 | 0.5267 | 0.1580 | 0.4336 | -0.2129 / -0.0051 |
| spectral__M1_RBF_KernelRidge | 0.1740 | 0.6849 | 1.0458 | 1.0399 | 0.1895 | 0.0906 | 0.1891 | 0.9097 / 0.8871 |
| spectral__M2_compact_MLP | 0.2279 | 0.8832 | 1.2525 | 1.3686 | 0.5798 | 0.1742 | 0.3578 | 0.4884 / 0.4274 |
| spectral__M3_order_local_spectral_latent | 0.2724 | 0.9578 | 2.1936 | 1.3376 | 0.5269 | 0.1590 | 0.4340 | -0.2242 / -0.0051 |

### Interpretation

- `spectral__M1_RBF_KernelRidge` is the strongest complex-state benchmark: lowest complex RMSE, normalized q95, T/R and routing errors among tested models.
- `row_wise__M1_RBF_KernelRidge` gives the stronger broadband eta(+1) ranking (P/S Spearman 0.9289/0.8995 versus 0.9097/0.8871 for spectral M1). This is a ranking trade-off, not a reason to optimize the complex model against the historical scalar objective.
- P and S were always explicit; no averaging or equivalence assumption was used. Spectral M1 complex RMSE is P 0.1734 / S 0.1747; transmission 0.2085 / reflection 0.1480.
- Decoded powers remain non-negative by construction; decoded energy residual and worst-geometry errors are recorded in `benchmark_manifest.json`.

## Historical scalar comparison

- Historical scalar evidence (not directly equivalent): spectral OOF MAE ≈ 0.03960; ranking Spearman ≈ 0.96160. The complex benchmark is not claimed as a percentage improvement over those metrics.

## Coupling interface readiness

- Defined only, not executed: NP complex normal-incidence state + MDC TMM complex transfer + spacer propagation → `C_component`.
- Current HF22 truth is one incident modal column per P/S; arbitrary returning-order re-scattering and a full Jones operator are not available. Those effects remain outside this provider or require a future multi-order operator dataset.

## Governance

- New solver calls: **0**; new data acquisition: **0**; Coupling H1 errors/candidate labels read: **0**; sealed HF targets read: **0**; deployment provider: **not created**; Active Learning: **not started**.
- No solver/training contract or source truth was modified.

## Artifacts

- Preregistration: `outputs/np_k6_complex_forward_surrogate_benchmark_v1/preregistration.json` (SHA256 `4b846fa88b1b75dc43a6398a604222af53345590634f1245d0f4c473d3b834cc`).
- Forensic: `outputs/np_k6_complex_forward_surrogate_benchmark_v1/run3c_p_448_forensic.json`.
- Representation audit: `outputs/np_k6_complex_forward_surrogate_benchmark_v1/representation_audit.json`.
- OOF predictions: `outputs/np_k6_complex_forward_surrogate_benchmark_v1/oof_*.npz`.
- Machine-readable manifest: `outputs/np_k6_complex_forward_surrogate_benchmark_v1/benchmark_manifest.json`.

## Next gate

`CHART_REVIEW_NP_COMPLEX_PROVIDER_AND_COUPLING_RESIDUAL_POC` — review only; not executed by this task.
