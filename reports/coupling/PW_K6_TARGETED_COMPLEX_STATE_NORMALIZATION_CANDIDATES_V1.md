# PW_K6 targeted complex-state normalization candidates forensic

## STATUS

**PARTIAL — zero-solver audit complete; no representation or comparator is admitted.**

Scope: frozen PW_K6 20G artifacts, 20 geometries, 21 wavelengths (440–460 nm), and IN/PRENP/POSTNP saved states. `solver_invocations=0`, `gpu_used=false`, and `frozen_truth_unchanged=true`. No FDTD entry, replay, new geometry, attempt, AL, MDC rebuild, or frozen-file modification was performed.

## 1. Frozen identity and hash audit

The saved raw JSON, complex state NPZ, projection JSON, and order JSON were reloaded for all 20 cases. The declared raw-complex E/H payload hash was retained. The full per-case table is in the companion analysis JSON.

- case hash index SHA256: `dd8fc73c6618ffba7719758238e9c5096013c30c6114ff9ba36deff466600c2d`
- fetched analysis JSON SHA256: `7e0055bb8bf38b8f23aac036d66f90bb80ff1031e5d830e4105766313d686594`

| frozen authority | SHA256 |
|---|---|
| `reports/coupling/PW_K6_20G_DATASET_FREEZE_MANIFEST_V1.json` | `e17a22cc34b7f0390fb272ded5245a61b52edbfff215d7ba83799e25a7c8570c` |
| `reports/coupling/PW_K6_20G_SOURCE_PROVENANCE_MANIFEST_V1.json` | `e32d72cd0898d17dad0f0fb7cf2879e514139cafe1d2b5328f1fbbe229f20d5d` |
| `reports/coupling/PW_K6_20G_FRESH_LOAD_ONLY_VALIDATION_V1.json` | `f28ab2022b92e2cae6181139da0a5061e59bbc99e000fee0ba3d120306adad7a` |
| `scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py` | `b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15` |
| `scripts/shared_fdtd/tools/pw_scientific_launcher.py` | `48d3c332fde679a9d8dc991a5ba8cd75aecdcb54750d7ec1774f732203ef08be` |

## 2. POWER EQUATION AUDIT

### 2.1 Frozen projection and modal equations

The audited implementation is `scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py`.

1. Projection is an actual-coordinate trapezoidal NUDFT: `sampled = sum(wx*wy*field*exp(-i*(2*pi*m*x/Px + 2*pi*n*y/Py)))/(Px*Py)`. The period-area division is explicit; no second supercell-area factor was inserted.
2. The local-medium basis uses `kz = passive_sqrt((n*k0)^2-kx^2-ky^2)` and `H=(n/ETA0)*(k_hat cross E_hat)`, followed by the saved 6-component least-squares modal solve.
3. Reference-plane de-embedding is `C <- C*exp((+i for +z, -i for -z)*kz*(z_ref-z_sample))`; the passive branch and direction sign are explicit.
4. Incident normalization is `P_inc=power_z_per_abs_e2(0,0,+z,TM)*abs(incident)^2`, followed by `C_norm=C_raw/sqrt(P_inc)*conj(incident)/abs(incident)`. The saved metadata says the global incident phase gauge is already applied at every plane.
5. Modal diagnostic power is `P_mode=0.5*Re((E_mode cross conj(H_mode))_z)*abs(C_norm)^2`; propagating modes use positive forward flux and absolute backward flux for reflected power.

### 2.2 Independent grating-truth path

The audited implementation is `scripts/shared_fdtd/tools/pw_scientific_launcher.py`. It reconstructs `in_plus=0.5*(E+Z0*H/n)` and `in_minus=0.5*(E-Z0*H/n)`, then computes `R=Re(n_gan)|in_minus|^2/(Re(n_gan)|in_plus|^2)` and `T=|post_plus|^2/(Re(n_gan)|in_plus|^2)`. Order truth is persisted from `abs(total_power)*real(grating_fraction)`. The launcher path has no additional explicit time-average factor; the modal path contains the `0.5` Poynting factor.

Fourier area, phasor handling, modal 0.5 factor, local-medium admittance, passive kz branch, direction sign, TE/TM basis, propagating mask, de-embedding order, and monitor-specific grating normalization were all traced. This proves that the two paths are different estimators with explicit conventions; it does not prove that one estimator is mathematically wrong.

Coverage limitation: some saved IN order truth contains orders outside the canonical C_PW `m,n=-4..4` envelope. IN order diagnostics report only the intersection with the canonical state envelope; no outside order was fabricated or folded into C_PW.

## 3. ABSOLUTE-POWER MISMATCH CLASSIFICATION

`Q=P_CPW/P_grating_truth`; POSTNP uses +z versus `T_FDTD`, IN uses -z versus `R_FDTD`. PRENP has no independent grating-order truth and is only a derived modal-flux diagnostic.

| plane / direction | Q min | Q05 | median | Q95 | max | geometry/Q correlation |
|---|---:|---:|---:|---:|---:|---|
| POSTNP +z / T_FDTD | 1.1720 | 1.3806 | 2.1980 | 6.1110 | 127.64 | D1=0.1266; D-distance=-0.6638 |
| IN -z / R_FDTD | 1.2654 | 1.2778 | 1.3242 | 2.4652 | 11.019 | D1=0.1115; D-distance=-0.0286 |

POSTNP per-m order Q medians are 2.1973–2.2013. This argues against channel-order permutation, a single wrong polarization, or an m-dependent Fourier indexing error. The factor is not global: POSTNP geometry medians span about 1.4088–5.9315, while wavelength medians vary strongly and the largest Q values occur in the 450–454 nm region. All 20×21 geometry/wavelength values are preserved in `mismatch.POSTNP_PLUSZ.geometry` and `.wavelength` in the companion analysis JSON.

Representative POSTNP geometry medians: S02 2.0788, S03 1.9694, S04 1.6778, S05 2.2405, S15 3.9752, S16 1.7465, EXT01 1.4583, EXT02 3.1418, EXT06 4.8679, EXT08 5.9315, EXT09 4.8335, EXT14 1.4088. The remaining geometry medians are in the companion JSON.

Representative wavelength medians (POSTNP): 440 nm 2.4353, 445 nm 2.0054, 446 nm 2.0790, 449 nm 2.2377, 450 nm 2.2935, 451 nm 2.2143, 452 nm 2.1157, 453 nm 2.1059, 454 nm 2.0765, 455 nm 2.0362, 460 nm 2.4442. The extreme row maxima occur near the same resonance/low-truth region.

**Classification:** `MIXED_CROSS_ESTIMATOR_NORMALIZATION_MISMATCH_PLUS_LOW-POWER_DENOMINATOR_AMPLIFICATION`. The fixed order-to-order factor indicates a common normalization difference; wavelength/geometry drift and extreme maxima indicate denominator/aggregation sensitivity when independently saved R/T truth is small. The saved evidence does not isolate a unique missing factor, kz sign error, local-medium error, or deterministic decoder defect. No derived decoder was promoted and the frozen comparator was not changed.

## 4. N0–N4 candidate representations

| candidate | definition | status |
|---|---|---|
| N0_CURRENT | Frozen complex C_PW | Historical authority; retained |
| N1_INCIDENT_NORMALIZED | Reapply incident flux/phase normalization | Algebraically identical to N0 under frozen metadata |
| N2_PROP_POWER_SEPARATED | `C_hat=C/sqrt(sum|C|^2)` over target propagating direction; separate saved R/T scale | Diagnostic only |
| N3_POWER_METRIC_UNIT | `C_hat=C/sqrt(sum(P_mode*|C|^2))`; separate saved R/T scale | Diagnostic only |
| N4_POWER_METRIC_PHASE_GAUGE | N3 plus incident physical phase gauge | Numerically identical to N3 because frozen gauge is already applied |

### 4.1 LOGO normalized-state regression

Geometry-held-out Ridge metrics over the valid propagating mask:

| plane | candidate | relative median | relative p95 | magnitude RMSE | phase MAE |
|---|---|---:|---:|---:|---:|
| IN | N0/N1 | 1.0051 | 1.5621 | 1.0624 | 88.2143° |
| IN | N2 | 1.0109 | 1.8961 | 0.1026 | 86.9844° |
| IN | N3/N4 | 1.0126 | 1.9427 | 1.8286 | 86.9902° |
| PRENP | N0/N1 | 1.0070 | 1.7668 | 2.2836 | 86.4803° |
| PRENP | N2 | 1.0124 | 1.7410 | 0.1185 | 87.2950° |
| PRENP | N3/N4 | 1.0125 | 1.7426 | 2.7413 | 87.3031° |
| POSTNP | N0/N1 | 1.0089 | 1.9478 | 2.5084 | 83.3524° |
| POSTNP | N2 | 1.0058 | 1.7417 | 0.1319 | 83.3358° |
| POSTNP | N3/N4 | 1.0065 | 1.7498 | 3.8206 | 83.4096° |

POSTNP MLP cross-check: N0/N1 `rel_med=1.09849, mag_RMSE=2.24403, phase_MAE=80.829°`; N2 `1.09566, 0.11556, 81.753°`; N3/N4 `1.09416, 3.34055, 81.475°`. Lower N2 magnitude RMSE is a coordinate-scale change, not evidence of accurate complex phase or end-to-end power.

### 4.2 Absolute-scale regression

Geometry-held-out Ridge scale metrics are shown as `relative median / RMSE / corr`; the best transform is selected by relative median only. A sqrtP result near relative median 1.0 is a degenerate near-zero predictor and is not a pass.

| plane | P | logP | sqrtP | diagnostic |
|---|---|---|---|---|
| IN | 0.9987 / 0.3766 / 0.0991 | 1.6962 / 0.6984 / 0.0306 | 1.0000 / 0.3770 / 0.2169 | P |
| PRENP | 1.0049 / 0.5365 / 0.1108 | 1.5863 / 0.6306 / 0.1025 | 1.0000 / 0.5349 / -0.0518 | sqrtP degenerate |
| POSTNP | 0.9674 / 0.2172 / -0.1642 | 7.1897 / 0.9228 / -0.1563 | 0.9997 / 0.2063 / -0.0828 | P, not reliable |

For POSTNP MLP, P scale has RMSE 0.22860 and relative median 1.25075; logP has relative median 5.09065; sqrtP collapses toward zero (relative median 1.0, corr 0.31032). The separate scale head therefore did not learn a reliable absolute scale.

### 4.3 End-to-end predicted state + scale → deterministic decoder

These are geometry-held-out Ridge metrics, with order truth restricted to the canonical envelope where necessary. They are learned end-to-end metrics, not the direct frozen-state decoder metrics from the prior forensic report.

| plane/candidate | route RMSE / corr | absolute order RMSE / corr | total-power RMSE / corr |
|---|---|---|---|
| IN / N0/N1 | 0.07637 / 0.97003 | 0.08974 / 0.91548 | 0.26904 / 0.85594 |
| IN / N2 | 0.23934 / 0.67139 | 0.12568 / 0.58475 | 0.37704 / 0.50189 |
| IN / N3/N4 | 0.23941 / 0.67113 | 0.12436 / 0.58466 | 0.37307 / 0.50177 |
| POSTNP / N0/N1 | 0.17737 / 0.69386 | 0.05635 / 0.13562 | 0.19309 / -0.65209 |
| POSTNP / N2 | 0.21793 / 0.48071 | 0.05618 / 0.06500 | 0.20677 / -0.33491 |
| POSTNP / N3/N4 | 0.21762 / 0.48008 | 0.05584 / 0.06518 | 0.20535 / -0.33494 |

N3/N4 are only marginally better in POSTNP absolute-order RMSE, while routing worsens and total-power correlation remains negative. They are not production-ready.

## 5. NP and MDC prior audits

### NP

`NP_PRIOR_FEATURE_DEFINITION.json` SHA256: `494a058f2e1a20859e5530ea999a44efe5addb2962a73e9141967cf7895eacf9`. Its contract requires exact lookup across all six pillars and wavelength. The declared provider library `D:\project\blue_apcd_np_k6_mdc_v1\outputs\np_k6_p1d2_broadband_library_27point_v1\library_long.csv` is absent on the connected host. Strict-support NP ablation is therefore **NOT EVALUABLE / NOT RUN**; no interpolation, extrapolation, old upstream prior, or unsupported feature was used. Historical summary SHA `291a64388f2ccb2c2ab0ba112b50969b1d590136fd8cbe0c886f41c0a5909516` was not treated as current 20G truth.

### MDC

No exact current 20G zero-cost standalone MDC prior was available. MDC was not rebuilt or injected. Existing upstream state observations are not a valid substitute. GP was not run for the high-dimensional 20G state/scale LOGO problem; existing 8G/12G GP R/T artifacts do not answer this audit.

## 6. H1/H2 and bottleneck verdict

- **H1 — full complex POSTNP state is learnable from current geometry+wavelength input:** **NOT SUPPORTED**. N2–N4 do not materially reduce relative state error or phase error; phase remains about 81–83°.
- **H2 — relative routing can be learned independently of absolute scale:** **PARTIALLY SUPPORTED only for the direct frozen-state decoder**, consistent with the prior direct POSTNP route result (RMSE `7.692e-05`, corr `0.99999993`). It is not supported as a learned end-to-end geometry-only representation: N2–N4 route errors are about `0.212–0.218`.

Current bottleneck is **mixed**: (i) cross-estimator normalization/scale mismatch between modal C_PW power and monitor/grating R/T truth, amplified at low truth denominators; and (ii) insufficient learnability of the high-dimensional complex state from the current input. Evidence is insufficient to declare the frozen comparator invalid.

## 7. Recommended representation and next route

**Recommended representation:** retain N0 as the historical/frozen authority; do not promote N1–N4. Any future candidate should preserve complex Re/Im and carry an explicit separate physical scale only after the scale contract is reconciled against the independent grating estimator.

**Exactly one recommended route: D — zero-solver cross-estimator normalization reconciliation.** Freeze current truth, construct a unit-testable modal-to-grating power bridge from saved raw E/H and projection artifacts, and resolve common-factor versus low-denominator amplification before any representation promotion or scientific solver allocation. This route is recommended, not executed here.

## 8. Git and execution safety

- Branch: `work/mdc-np-coupling-ml-v1`
- HEAD at task start: `eefda35d53eb6953fb5819da25b659dbfc4fd4df`; no commit or push performed.
- Worktree: dirty with pre-existing user changes; no reset, restore, clean, merge, rebase, amend, stage, or push performed.
- Scientific solver: **not invoked**; no scientific entry consumed.

## RETURN

- STATUS: `PARTIAL`
- POWER EQUATION AUDIT: completed; source paths and frozen hashes recorded
- ABSOLUTE-POWER MISMATCH CLASSIFICATION: mixed cross-estimator normalization mismatch plus low-power denominator amplification; unique deterministic decoder bug not proven
- N0–N4: defined and evaluated offline; none admitted
- normalized-state: no candidate materially resolves complex-state learnability
- absolute-scale: no reliable P/logP/sqrtP scale predictor under current LOGO geometry split
- NP: strict-support ablation blocked because provider library is absent
- MDC: not rebuilt; no exact current zero-cost prior available
- end-to-end: N0 remains better than N2–N4 for learned POSTNP routing; absolute power remains unresolved
- H1/H2: H1 not supported; H2 partially supported only for direct frozen routing
- next route: D, zero-solver normalization reconciliation; not executed
