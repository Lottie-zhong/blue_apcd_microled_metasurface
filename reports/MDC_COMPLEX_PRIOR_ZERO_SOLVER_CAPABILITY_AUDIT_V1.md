# MDC_COMPLEX_PRIOR_ZERO_SOLVER_CAPABILITY_AUDIT_V1

**Status:** PASS — zero-solver, read-only capability audit complete. No FDTD, TMM, RCWA, NP or training execution was started by this audit.

## Frozen authority and audit boundary

- Worktree: `D:\project\worktrees\blue_apcd_mdc_hf_surrogate_v2`
- Branch: `work/mdc-hf-surrogate-v2`
- Audited pre-report HEAD: `8d1380355ae2c5548d7f0c66a783b413982c8a7c` (the supplied authority literal is 39 characters and is therefore malformed; the repository's verified 40-character commit is used).
- DOE96 authority: 96 geometries × 6 source cases = 576 accepted 2D-FDTD cases.
- Current V3-C authority: `MDC_HF_SURROGATE_V3_C_FINAL_5SEED_PROFILE_ONLY_V1`; normalized spectral-angular profile only.
- FSP access was LOAD-only. No `run`, `runanalysis`, `runsetup`, `mesh`, `save`, or property mutation was issued.

## FSP monitor inventory

The retained capability audit records 102 historical retained FSPs. A representative 14-file post-FSP sample was loaded successfully in Lumerical 8.33.3999. The sample covers `off_center_defect`, `symmetric_periodic`, `grouped_chirped`, and `dual_defect`, with top/centroid/bottom × x/z dipole cases where present.

The representative object tree contains:

| object | observed read-only metadata |
|---|---|
| active source | `DipoleSource`; source-specific x/z orientation and top/centroid/bottom identity are supplied by the frozen case index; wavelength limits 420–480 nm, center 450 nm |
| `emit_box_12nm_top`, `emit_box_12nm_bottom` | `DFTMonitor`, Linear X, 301 frequency points, 24 nm x-span |
| `emit_box_12nm_right`, `emit_box_12nm_left` | `DFTMonitor`, Linear Y, 301 frequency points, 24 nm y-span |
| `upward_monitor` | `DFTMonitor`, Linear X, 301 frequency points, 6 µm x-span, y = 1 µm |

The DFT result namespace exposes `E`, `Ex`, `Ey`, `Ez`, `H`, `Hx`, `Hy`, `Hz`, `P`, `T`, `power`, `farfield`, coordinate axes and frequency. The FDTD object advertises `always use complex fields`; this is a native monitor capability observation, not an assertion that a plane-wave scattering operator was archived.

The frozen exported DOE96 NPZ archive contains only `wavelength_nm`, `angle_deg`, `joint_raw`, `spectral_marginal_raw`, `angular_marginal_raw`, `p_up_raw`, and `p_box_raw`; `joint_raw` is `[301, 2000]`, `float64`, and no E/H, complex t/r or phase arrays are exported. Inventory search found 1,154 FSP files, zero H5/HDF5 files and 577 NPZ files under the DOE96 database tree; these are inventory counts only.

## Complex E/H availability

Two levels must be kept separate:

1. **Native retained FSP capability:** **B — `COMPLEX_EH_PARTIALLY_AVAILABLE`**. Native DFT monitors expose field-result channels and complex-field mode, but the retained contract does not establish a complete incident/reference-plane/de-embedded channel pair for a plane-wave scattering matrix.
2. **Canonical DOE96 exported response:** **C — `INTENSITY_POWER_ONLY`**. The frozen NPZ response is real intensity/power and marginal data only.

This is not class A: no retained artifact proves a complete, channel-resolved, normalized complex E/H operator across the DOE96 response grid.

## Dipole versus plane-wave semantics

The FSPs are dipole-emission simulations. Any complex E/H recovered from those monitors is a `DIPOLE_EMISSION_COMPLEX_STATE` (source orientation, position, monitor surface and phase convention included). It must not be relabeled as a `PLANE_WAVE_COMPLEX_TRANSFER_OPERATOR`, nor as plane-wave `t`/`r`. The 2D monitor contract reports direct Poynting/field channels and source-dependent angular emission; it does not supply an incident plane-wave normalization.

## Zero-solver recoverable complex features

Without a new solver call, the existing artifacts can support:

- FSP object/source/monitor/grid metadata and monitor result-key inventory;
- if explicitly authorized in a later LOAD-only extraction, dipole-monitor complex E/H samples, field phase and Poynting-derived emission channels;
- existing NPZ spectral marginal, angular marginal, joint intensity profile and relative upward-power descriptors;
- pure-Python layered-stack complex amplitudes, phase, R/T and angle/polarization conditioning from the existing frozen TMM code.

They cannot support a validated plane-wave complex transfer matrix from the DOE96 dipole NPZ archive, absolute extraction efficiency, LEE, Purcell/LDOS, or a 3D vector operator.

## TMM complex transfer capability

The frozen source contains two relevant layers of capability:

- `scripts/mdc_tmm_core.py` computes complex internal reflection/transmission amplitudes but its public `tmm_complex` return is the scalar `R`, `T`, and `R_plus_T` descriptor.
- `scripts/mdc_tmm_complex_incident_power_v1.py` explicitly returns complex E-field-basis `r` and `t`, phase-preserving power bookkeeping, normal and oblique TE/TM branches, passive `kz` selection, and native-material loss handling.
- `scripts/mdc_dipole_tmm.py` returns complex `r`/`t` for the layered plane-wave channel used by its reciprocal relative dipole proxy, while explicitly labelling that proxy as not a total-power, LEE, LDOS or Purcell calculation.

Thus a deterministic, code-level **plane-wave layered-stack complex prior exists** without FDTD. Existing archived tables are predominantly scalar T/R, peak/FWHM and angular descriptors; a canonical complex t/r table is not claimed to already exist.

## TMM / 2D-FDTD consistency

The available comparison is only qualitative because source physics, geometry, normalization and grids differ. For example, historical 2D-FDTD records give `ZL1_N3_M3_L78_H46_450_XDIPOLE` an angular FWHM of 25.14° and a spectral peak near 447.75 nm; the historical normal-incidence layered TMM control reports a peak near 450.3 nm and a 3.3 nm FWHM. The 2D-FDTD broadband comparison similarly reports peaks near 447.75 nm for the two historical candidates. These are not an apples-to-apples complex-transfer validation and are marked **NOT DIRECTLY COMPARABLE**. They support only the use of TMM as a cavity/stack prior, not substitution for dipole HF truth.

## Recommended MDC prior type

**Preferred:** `MDC_HYBRID_TMM_PLUS_PROFILE_PRIOR`.

Rationale: use the existing plane-wave TMM complex `r(λ,θ,pol)`, `t(λ,θ,pol)`, phase and stack/cavity descriptors as the physically interpretable prior, and retain V3-C's normalized spectral-angular profile as the dipole-emission shape prior. Keep the two semantics explicit; do not convert dipole E/H into plane-wave t/r. This is the lowest-cost route that adds phase/cavity conditioning without new solver calls.

## Current fixed-MDC role

For the current fixed-MDC 20-geometry coupling line, the prior may condition wavelength, angle/polarization, phase reference, spectral/cavity structure and relative shape. It cannot explain K6 geometry-to-geometry variation, absolute power, LEE, Level-1 coupling truth or an integrated device response. V3-C remains Level-0 normalized-profile screening only.

## Future variable-MDC role

The future provider interface may be:

`(geometry, wavelength, angle, polarization) -> {complex_tmm_state, profile_state, provenance}`

where `complex_tmm_state` contains plane-wave `r/t`, R/T and phase under the frozen material/reference convention, and `profile_state` contains the V3 normalized dipole profile descriptors. Geometry-dependent HF data are still required for quantitative Level-1/provider validation; this audit generated none.

## 3D FDTD necessity

3D FDTD is **not necessary for the cheapest valid prior** and is not authorized here. It becomes necessary only if the target explicitly requires effects that the layered TMM plus retained profile cannot represent (finite-area 3D scattering, out-of-plane/vector coupling, non-separable polarization or near-field interactions), and only after a separate solver authorization. Current evidence does not justify starting production 3D FDTD merely to obtain complex t/r.

## GIT and next

This report is the only intended lightweight change. No large arrays, FSPs, checkpoints, credentials or runtime logs are included. Next action is deliberately not executed: if Chart later authorizes implementation, expose the existing TMM complex state through a versioned provider contract and validate it against explicitly matched plane-wave semantics; keep dipole FSP fields as a separate state.
