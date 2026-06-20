# Stage13-0/1 LP Dipole Preparation

This package is configuration and geometry-audit metadata only. It does not run FDTD and does not modify the frozen H500 LP-APCD K=6 x-gradient design.

## Coordinate convention

- Metasurface plane: x-y; nanopillar height: z.
- Dipole/MicroLED source: below the metasurface.
- Target emission and far-field monitor: +z.
- Structure/source x-y origin: (0, 0).
- The frozen periodic K=6 source supercell has no true center dimer. A finite-patch definition is still missing.

## Source and polarization rules

- Prepare x- and y-oriented in-plane electric dipoles as separate cases.
- Never coherently add Ex/Ey fields from different dipole orientations.
- Unpolarized response is the incoherent power sum: `I_unpol = I_xdip + I_ydip`.
- q is not copied from the CP branch. Here `q_nm` is null with `requires_manual_definition` because no frozen LP finite-patch source-position rule was found.

## LP metrics

- `target_LP_power`: x-LP projected far-field power.
- `leakage_LP_power`: y-LP projected far-field power.
- `LP_fraction = target_LP_power / (target_LP_power + leakage_LP_power)`.
- `target_to_leakage_ratio = target_LP_power / leakage_LP_power`.
- DoCP is not a main metric for this LP branch.

## Required later extraction

Later extraction must use the complex vector far field (`Ex`, `Ey`, `Ez`) from `farfieldvector3d` or an equivalent API. `farfield3d` intensity alone is insufficient for LP projection.

## Run boundary

- `run_fdtd = false`.
- Six cases are prepared but not run: center/x-plus-q/x-minus-q, each with x/y dipole orientation.
- Cone statistics are configured for 5, 10, and 20 degrees; 30 degrees is disabled.
- Resolve every item in `blocking_issues_before_fdtd` before any FDTD task.
