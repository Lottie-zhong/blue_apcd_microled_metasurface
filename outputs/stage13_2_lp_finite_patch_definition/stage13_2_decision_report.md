# Stage13-2 LP Finite-Patch Definition And q/source-z Decision Report

## Scope boundary

- Decision/configuration package only; no FDTD was run.
- No `.fsp` file was created, opened, or modified.
- The frozen Stage12 H500 LP-APCD K=6 periodic supercell is read-only.
- Coordinate convention is x-y metasurface, z height, source below, +z emission/monitor, x gradient, x-LP target.
- K=6 means six dimers (12 nanopillars) per supercell.

## Discovered frozen-supercell evidence

- Candidate: `H500_LP_APCD_K6_XGRAD_FROZEN_STAGE12`.
- Source files: `["outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv", "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_geometry_audit.csv", "outputs/stage12_6_h500_lp_k6_official_result_package/stage12_6_key_metrics.csv", "outputs/stage13_0_lp_dipole_geometry_audit/geometry_audit.csv", "src/metasurface/stage12_k6_layout.py", "src/metasurface/stage12_k6_fdtd.py"]`.
- Supercell period x: `2591.446716` nm.
- Supercell/y pitch: `432.0` nm.
- Phase-bin pitch x = Lambda_x/6: `431.907786` nm.
- Raw footprint x: `-1239.769465` to `1224.769465` nm.
- Raw footprint y: `-112.5` to `77.5` nm.
- Six dimer centers and all J1/J2 centers were parsed into the JSON candidate package.

## Patch decision

- Recommended geometry for the first later FDTD: `A_small`.
- Size: `3 x 19` whole-supercell/y-row tiles.
- Estimated geometry: `342 dimers; 684 nanopillars`.
- Reason: it preserves the frozen phase ramp and optical origin without forcing a center dimer or rounding coordinates.
- This is a recommendation pending manual approval, not authorization to run FDTD.

### Candidate summary

| option | Nx | Ny | true center dimer | phase ramp preserved | x edge error (nm) | y edge error (nm) | first-FDTD recommendation |
| --- | ---: | ---: | --- | --- | ---: | ---: | --- |
| A_small | 3 | 19 | False | True | 15.0 | 35.0 | True |
| A_medium | 5 | 31 | False | True | 15.0 | 35.0 | False |
| B_dimer_centered_small | 3 | 19 | True | True | 416.907786 | 35.0 | False |
| C_integer_fabrication_small | 3 | 19 | False | False | 15.0 | 35.0 | False |

- Option C maximum 2D center perturbation after integer rounding: `0.702050219` nm.
- Option C conservative minimum gap after rounding: `19.0` nm versus the frozen `20.0 nm` minimum.
- Therefore Option C is not gap-safe by the existing 20 nm rule and requires redesign/tolerance validation.

## q decision

- Recommended candidate: `q_candidate_1`.
- q = `107.9769465` nm, independently derived from the frozen LP phase-bin pitch.
- q was safely inferred for case preparation, but still requires explicit manual approval before FDTD.
- The numerical match to the historical CP q is incidental; no CP q value was reused.

| q candidate | q (nm) | safe for minimal x-line | recommended |
| --- | ---: | --- | --- |
| q_candidate_1 | 107.9769465 | True | True |
| q_candidate_2 | 107.9769465 | True | False |
| q_candidate_3 | None | False | False |

## source-z decision

- No LP MQW plane or approved vertical-stack source position was found.
- `source_z_nm` remains `null`; status is `requires_manual_definition`.
- CP-branch `-200 nm` evidence is not transferable to this LP patch and was not selected.

| z candidate | source z (nm) | safe |
| --- | ---: | --- |
| z_candidate_1 | None | False |
| z_candidate_2 | None | False |
| z_candidate_3 | None | False |

## FDTD blocking items

1. Manually approve one finite-patch option (recommended: A_small).
2. Manually approve q_candidate_1 or supply another LP-specific q.
3. Define and approve LP source_z_nm from a vertical stack/MQW decision.

Until all three are resolved, every case remains `prepared_not_run` and `run_fdtd=false`.
