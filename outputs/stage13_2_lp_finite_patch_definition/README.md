# Stage13-2 LP Finite-Patch Decision Package

This directory contains lightweight definitions and manual-decision metadata only. No FDTD was run, and the frozen Stage12 K=6 periodic supercell was not modified.

## Recommendation

- Geometry: `A_small`, a 3-supercell x replication with odd symmetric y rows.
- q: `q_candidate_1 = phase_bin_pitch_x_nm / 4`, derived from the LP layout and pending manual approval.
- source z: unresolved; no LP MQW/vertical-stack position is frozen.

## Boundaries

- `run_fdtd=false`.
- No `.fsp` files belong in this package.
- x/y dipole orientations remain separate; unpolarized power is the incoherent sum.
- Later LP extraction must use complex vector far-field components, not intensity-only `farfield3d`.
- Manual approval of patch, q, and source z is required before any simulation task.
