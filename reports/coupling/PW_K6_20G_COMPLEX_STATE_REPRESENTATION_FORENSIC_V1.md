# PW_K6_20G_COMPLEX_STATE_REPRESENTATION_FORENSIC_V1

Status: ZERO_SOLVER_COMPLETE; forensic PASS with scientific gates retained.

## 1. Scope and authority

This report is a retrospective CPU-only audit of the frozen PW_K6 20G truth. No FDTD solver, GPU entry, replay, new attempt, geometry, queue, manifest, FSP, H5, raw truth, archive, or frozen comparator was modified.

- Frozen snapshots: 8G=8, 12G=12, 20G=20 geometries.
- Grid: 21 wavelengths, 440–460 nm; planes IN/PRENP/POSTNP; C_PW shape [3, 21, 81, 2, 2] = 324 complex coefficients per sample.
- solver_invocations=0; gpu_used=false; all source artefacts were read-only.
- Case-artifact SHA256 index: `4935ef3618a8dca741a7284559d2924359b28da8b39ab2e6a5c9362630466a36`.

Authoritative source hashes:

| artifact | SHA256 |
|---|---|
| `PW_K6_20G_DATASET_FREEZE_MANIFEST_V1.json` | `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c` |
| `PW_K6_20G_SOURCE_PROVENANCE_MANIFEST_V1.json` | `e32d72cd0898d17dad0f0fb7cf2879e514139cafe1d2b5328f1fbbe229f20d5d` |
| `PW_K6_20G_CPU_LEARNABILITY_ANALYSIS_V1.json` | `0445376551cec413fb0ea0a3fcd4593cc362ec916b66599b43e2bf69202f768a` |
| `PW_K6_20G_FRESH_LOAD_ONLY_VALIDATION_V1.json` | `f28ab2022b92e2cae6181139da0a5061e59bbc99e000fee0ba3d120306adad7a` |

## 2. Retrospective 8G sanity

**8G_SANITY_PASS**. This is a structural/numerical sanity result, not a production-fidelity admission.

| check | result | evidence |
|---|---|---|
| geometry_unique | PASS | 8 unique geometry hashes; min pair distance 128.55 nm |
| axis_and_shape | PASS | all 8 cases: (3,21,81,2,2), matching wavelength/order axes |
| finite_and_spectral_smoothness | PASS | finite; second-difference q95 magnitude=0.230683, phase=2.1455 rad |
| phase_gauge_reference | PASS | max incident-reference phase residual=1.106e-16 rad |
| geometry_separation | PASS | min pair distance=128.55 nm |
| per_plane_variation | PASS | non-zero cross-geometry variation in IN, PRENP, POSTNP |
| rt_accounting | PASS | max closure=1.11e-16 |
| order_topology_consistent | PASS | same post order topology across the 8 cases |
| no_state_collapse | PASS | normalized pairwise C_PW distance min/median=0.128335/1.28802 |
| no_duplicate_geometry_hash | PASS | 8/8 unique |

C_PW magnitude spread (all 8G channels):

| plane | all-channel median / q95 / max | propagating median / q95 | evanescent median / q95 |
|---|---:|---:|---:|
| IN | 0.000727616 / 0.217135 / 17.6622 | 0.000727616 / 0.217135 | NA / NA |
| PRENP | 0.00488062 / 1.8513 / 22.1391 | 0.00567332 / 4.42971 | 0.00488062 / 0.996021 |
| POSTNP | 0.000641038 / 1.44404 / 22.8466 | 0.000880173 / 7.47264 | 0.000583843 / 0.939702 |

The 8G result is PASS because the frozen state is finite, axis-consistent, non-collapsed, spectrally finite, geometry-separated, and energy-accounted. It does not imply that geometry-to-C_PW learning is production-ready.

## 3. Direct C_PW → routing decoder

The deterministic decoder used here is the modal/Floquet power map already implied by the frozen source implementation:

`P_hat(m,n,d) = sum_pol abs(Re(power_z_per_abs_e2(m,n,d,pol))) * abs(C_norm(m,n,d,pol))^2` for propagating orders; `route_hat = P_hat / sum(P_hat)`.

`power_z_per_abs_e2` was reconstructed from the saved passive `kz` and the frozen TE/TM basis. No fitted scale, solver call, or truth mutation was used.

| direction / plane | absolute order RMSE / corr (median per case) | normalized route RMSE / corr | centroid RMSE / corr | positive-x fraction RMSE / corr |
|---|---:|---:|---:|---:|
| POSTNP +z | 0.0458396 / 0.992606 | 7.69201e-05 / 1 | 5.10219e-05 / 1 | 0.000107781 / 1 |
| IN -z | 0.0352003 / 0.999422 | 0.068301 / 0.979224 | 0.0253711 / 0.839739 | 0.0937255 / 0.811952 |

Interpretation:

- POSTNP +z route topology is reproduced essentially exactly after within-spectrum normalization: median route RMSE `7.692e-05`, median correlation `0.99999993`, centroid RMSE `5.102e-05`.
- Absolute source-normalized power is not consistent with the saved order truth: the median of per-case POSTNP predicted/true total ratios is `2.625` (range `1.409–5.932`). This is an evidence conflict between the modal-state normalization and the separately saved launcher/grating source-power scalar, not something to hide with a fitted scale.
- IN -z reflection routing is only partial: normalized route median RMSE `0.06830`, correlation `0.97922`, and positive-x fraction median RMSE `0.09373`.

**H2 verdict: H2_PARTIALLY_SUPPORTED.** True C_PW is sufficient for POSTNP propagating route proportions and directional centroid, but the current frozen archive does not support a certified absolute source-power decoder across both planes/directions.

## 4. Phase-gauge and stability forensic

- The canonical state is already incident-referenced: `single_global_phase_per_wavelength_from_IN_REF_+z_(0,0)_TM`, reused across planes/channels; saved `zero_denominator_count=0`.
- In 8G the incident-reference phase residual is at most `1.106e-16 rad`; this rules out an arbitrary per-case global phase as the main cause of the learned-state failure.
- A diagnostic per-sample global phase alignment on 20G POSTNP R0 Ridge changes relative median error only from `1.01204` to `0.988978`; median alignment angle is `0.530381` rad. This is not an admission metric and uses truth only for diagnosis.
- The frozen comparator’s magnitude denominator floor can inflate relative error on weak channels, but propagating channels, dominant channels, and the post-state as a whole remain poor; this is a secondary aggregation pathology, not proof that the comparator is mathematically invalid.

Root-cause classification: A (genuine learned modal-state difference) is present; B denominator-near-zero is not present in the canonical normalization; C evanescent exponential amplification is not sufficient to explain the propagating error; D passive kz branch/sign has no failure evidence; E axis/order permutation is ruled out by the 8G audit; F local-medium mismatch is not supported by the saved kz/mask consistency; G weak-channel relative aggregation is secondary; H the exact additional issue is the absolute-power normalization mismatch between C_PW decoding and saved grating-order truth.

No comparator V2 change is proposed in this task.

## 5. Representation ablations (same geometry-grouped LOGO folds)

R0 is the frozen complex target represented as real/imaginary; R1 is the explicit Re/Im encoding and is numerically identical. R2 is magnitude/sin/cos phase. R3 divides out the incident reference unit phase; R4 applies the equivalent global incident-phase alignment. Since the frozen state is already gauge-fixed, R0/R1/R3/R4 are equal to machine precision on these folds.

| snapshot / POSTNP Ridge | relative median | magnitude RMSE | phase MAE (deg) |
|---|---:|---:|---:|
| 8G R0_raw_complex | 1.13315 | 1.99438 | 85.603 |
| 8G R1_re_im | 1.13315 | 1.99438 | 85.603 |
| 8G R2_mag_sin_cos | 1.30272 | 2.72646 | 85.164 |
| 8G R3_incident_phase | 1.13315 | 1.99438 | 85.603 |
| 8G R4_global_phase_aligned | 1.13315 | 1.99438 | 85.603 |
| 12G R0_raw_complex | 1.04483 | 2.23707 | 84.608 |
| 12G R1_re_im | 1.04483 | 2.23707 | 84.608 |
| 12G R2_mag_sin_cos | 1.44749 | 1.85353 | 85.053 |
| 12G R3_incident_phase | 1.04483 | 2.23707 | 84.608 |
| 12G R4_global_phase_aligned | 1.04483 | 2.23707 | 84.608 |
| 20G R0_raw_complex | 1.01204 | 2.31376 | 83.027 |
| 20G R1_re_im | 1.01204 | 2.31376 | 83.027 |
| 20G R2_mag_sin_cos | 1.48988 | 1.67478 | 83.859 |
| 20G R3_incident_phase | 1.01204 | 2.31376 | 83.027 |
| 20G R4_global_phase_aligned | 1.01204 | 2.31376 | 83.027 |

20G POSTNP shallow-MLP: R0 relative median `1.09523`, magnitude RMSE `2.03434`, phase MAE `80.29°`; R2 relative median `1.32411`, magnitude RMSE `1.77005`, phase MAE `81.51°`. R2 reduces absolute magnitude RMSE but worsens relative-state accuracy and does not solve phase.

## 6. Plane / subspace / order / wavelength decomposition

20G R0 Ridge decomposition; weak/dominant thresholds are pooled true-magnitude q25/q75 per plane, not tuned admission thresholds:

| plane | subspace | relative median | relative p95 | magnitude RMSE | phase MAE (deg) |
|---|---|---:|---:|---:|---:|
| IN | propagating | 1.0016 | 1.54939 | 0.237071 | 84.82 |
| IN | evanescent | NA | NA | NA | NA |
| IN | weak q25 | 1.00933 | 1.63494 | 1.09211e-05 | 88.921 |
| IN | dominant q75 | 0.986589 | 1.21169 | 0.474135 | 75.509 |
| PRENP | propagating | 1.00822 | 1.74647 | 1.85938 | 85.68 |
| PRENP | evanescent | 1.01425 | 2.1687 | 0.553893 | 84.429 |
| PRENP | weak q25 | 1.01423 | 1.88549 | 1.45627e-05 | 85.821 |
| PRENP | dominant q75 | 0.998095 | 1.61439 | 1.62074 | 82.26 |
| POSTNP | propagating | 1.01204 | 2.02278 | 2.31376 | 83.027 |
| POSTNP | evanescent | 0.992698 | 1.87465 | 0.629502 | 83.488 |
| POSTNP | weak q25 | 0.938661 | 1.81325 | 1.48168e-07 | 85.287 |
| POSTNP | dominant q75 | 0.999285 | 1.74901 | 1.8162 | 81.156 |

The phase error is broad rather than confined to weak channels: POSTNP dominant-channel phase MAE is still `81.16°`, while weak-channel phase MAE is `85.29°`. Thus weak-channel denominator instability is real but not the primary H1 blocker.

POSTNP worst relative orders in the 20G R0 Ridge diagnostic are `(2,0)`, `(1,0)`, `(-1,0)`, `(-2,0)`, `(3,0)`; the worst wavelengths are 440, 460, 441, 459, and 443 nm. The error is edge-of-band weighted but not a single-order-only failure.

## 7. H1, NP prior, learning curve, and AL gate

**H1: geometry + wavelength → C_PW: H1_NOT_SUPPORTED_CURRENT_REPRESENTATION.** 20G POSTNP R0 Ridge remains at relative median `1.01204` and phase MAE `83.03°`; the incident-gauge ablations are identical and magnitude/sin/cos does not improve the state target. The direct geometry-to-routing baseline remains RMSE `0.0404628`, correlation `0.6387342`, but it does not establish C_PW learnability.

NP prior diagnosis from the frozen CPU analysis: PRENP prior improves all 20 matched geometries (median relative improvement `0.607466`, magnitude `1.34793`, phase `52.4217°`); POSTNP is inconsistent (median relative change `-0.187081`, improved `5/15`; magnitude change `0.414391`, improved `15/5`; phase change `14.6387°`, improved `19/1`). This supports a useful PRENP upstream prior but not a stable POSTNP prior bridge.

Learning curve: routing MLP 12G→20G improves RMSE `0.0459599→0.0404628` and correlation `0.590168→0.638734`; scalar MLP changes `0.0961759→0.106757` RMSE and `0.857600→0.848511` correlation. Dataset growth helps routing but does not establish monotonic full-state learning.

**ACTIVE_LEARNING_NOT_READY.** H1 is not supported and H2 is only partial; no production AL, variable MDC, K4/K9, dipole FDTD, or deep model was started.

## 8. Scientific interpretation and next route

- Physically meaningful propagating routing: the true POSTNP C_PW contains enough information to recover route proportions, centroid, and positive-x directionality with near-zero normalized error.
- Evanescent/local near-field fidelity: the retained evanescent state is non-collapsed and structurally present, but geometry-to-state prediction remains poor; POSTNP evanescent relative median is `0.99270` and phase MAE `83.49°`.
- Comparator numerical stability: the saved gauge, axes, order topology, passive branch, finite denominators, and 8G structural sanity pass. No frozen-comparator invalidity is proven.
- Cavity/reflection sensitivity: the separately saved source-normalized order scalar is not numerically commensurate with the modal-state absolute-power reconstruction; this blocks absolute H2 certification even though route proportions agree.

**Exactly one next route (not executed): B — design one targeted representation/normalization refinement candidate.** The candidate should preserve the frozen truth and test a propagation-only POSTNP route head plus an explicitly reconciled absolute-power contract; it should be CPU-only and must not launch a solver until Chart review accepts the contract. Do not execute this route in the present task.

## 9. Evidence boundary

The results above are offline diagnostics over saved 20G truth. They do not change MEDIUM/5 nm admission, do not promote the current C_PW learner to production, do not authorize replay/EXT03–EXT14/new attempts, and do not alter any frozen artifact.
