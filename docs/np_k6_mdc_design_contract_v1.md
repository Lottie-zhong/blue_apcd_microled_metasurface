# NP-K6-MDC-V1 Lightweight Design Contract

## Identity and scope

- **branch_id:** `NP-K6-MDC-V1`
- **branch_function:** 450 nm non-polarized, polarization-insensitive specified-angle directional emission.
- **metasurface:** TiO2 solid circular cylindrical nanopillars.
- **wavelength_nm:** 450
- **target_angle_air_deg:** 15
- **K:** 6 nanopillars per supercell.
- **gradient_direction:** x
- **propagation_direction:** GaN/MDC -> Air
- **angle_convention:** `air_side_far_field_conserved_real_kx_v1`

## Frozen lattice and coordinates

- **local_pitch_x_nm:** 290
- **period_y_nm:** 290
- **supercell_period_x_nm:** 1740
- **phase_seed_deg:** [0, 60, 120, 180, 240, 300]
- Fixed pillar centers, **x_nm:** [-725, -435, -145, 145, 435, 725]
- All pillar centers, **y_nm:** 0
- Every formal candidate geometry dimension is an integer number of nanometres.

## Geometry and fabrication gate

The V1 design variables are `[H_nm, D1_nm, D2_nm, D3_nm, D4_nm, D5_nm, D6_nm]`.

- 100 <= Di <= 230 nm
- 300 <= H <= 700 nm
- minimum edge-to-edge gap >= 60 nm
- H / min(Di) <= 5.5

No independent SiO2 spacer is added in V1. TiO2 cylinders sit directly on the outermost SiO2 termination layer of the MDC.

A single-cylinder phase library is only a warm-start. The formal optimization object is the complete K=6 periodic supercell containing D1...D6.

## Materials contract

Use only Native-M1 measured project materials, with no constant-index fallback, extrapolation, or branch-private material model.

| Canonical ID | Original material | Use |
| --- | --- | --- |
| `APCD_TIO2_NATIVE_M1` | `tio22` | TiO2 nanopillars |
| `APCD_SIO2_NATIVE_M1` | `sio222` | MDC outer termination layer |
| `APCD_GAN_NATIVE_M1` | project Native-M1 GaN | propagation-side material |

- Read-only source: `F:\wc_312\MDC_blue_oujizi_m\m_1.fsp`
- Unified configuration reference: `configs\material_reference_apcd_blue.yaml`

## Dataset and evaluation freeze

The future ML database must use `datasets\np_k6_mdc_v1\schema.json`. Evaluation records retain the fixed geometry, material provenance, input polarization, boundaries and monitors, complex amplitudes and powers for every propagating diffraction order, R/T/energy residuals, target-order efficiency, leakage, x/y consistency, main-lobe angle, FWHM, manufacturing flags, hashes, code commit, failure mechanism, and provenance.

This contract defines setup and provenance only. It does not authorize or record FDTD/RCWA execution.
