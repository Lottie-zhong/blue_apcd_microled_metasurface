# Stage13-0 LP Dipole Geometry Audit

## Scope boundary

- Read-only audit of the frozen Stage12 H500 LP-APCD K=6 x-gradient geometry.
- No FDTD simulation was run; no `.fsp` file was created or modified.
- Coordinate system: metasurface in x-y, height along z, source below, emission and monitor toward +z.
- K=6 means six dimers, not six nanopillars.

## Geometry conclusion

- Candidate: `H500_LP_APCD_K6_XGRAD_FROZEN_STAGE12`.
- The frozen Stage12 artifact is one periodic K=6 supercell; a finite-patch Nx/Ny replication definition was not found.
- True center unit: `False`.
- True center dimer: `False`.
- Source center x/y: `0.0`, `0.0` nm.
- Source center z: `None`.
- q status: `requires_manual_definition`; q_nm: `None`.
- CP-branch q was not reused and no LP q was guessed.
- Left/right footprint edge distances: `1239.769465` / `1224.769465` nm.
- Edge symmetry error: `15.0` nm.
- Geometry audit pass: `False`.

## Manufacturability

- Integer-nm centers: `False`.
- Integer-nm dimensions: `True`.
- Integer-degree rotations: `True`.
- Minimum inferred gap: `20.0` nm.
- Sub-nm coordinates detected: `True`.
- Non-integer angles detected: `False`.
- Notes: Frozen source supercell period is 2591.446716 nm; physical dimensions and rotations are integer-valued, but centered coordinates include sub-nm values. No rounding or geometry modification was performed.

## Blocking issues before FDTD

- `frozen_stage12_artifact_is_periodic_supercell_not_finite_patch`
- `finite_patch_Nx_Ny_and_replication_rule_missing`
- `q_requires_manual_definition`
- `source_center_z_requires_manual_definition`

## Warnings

- K=6 means six dimers; centered source supercell has no true x=0 center dimer
- GUI FSP is evidence-only and was not opened or modified
- sub-nm centers belong to the frozen Stage12 layout and were not rounded

## Evidence paths

`["outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_layout_plan.csv", "outputs/stage12_1_h500_lp_k6_forward_layout/stage12_1_k6_forward_geometry_audit.csv", "outputs/stage12_6_h500_lp_k6_official_result_package/stage12_6_key_metrics.csv", "outputs/stage12_3b_h500_lp_k6_gui_inspection/stage12_3b_h500_lp_k6_forward_gui_inspection.fsp"]`
