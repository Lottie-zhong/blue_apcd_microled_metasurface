# Stage13-3 Manual Approval Record

## Scope

- Configuration and approval record only; no FDTD was run.
- No `.fsp` file was created, opened, or modified.
- The frozen Stage12 H500 LP-APCD K=6 x-gradient supercell remains unchanged.

## Approved finite patch

- `patch_option_id`: `A_small`
- Replication: `3 x 19` tiles
- Estimated geometry: `342 dimers / 684 nanopillars`
- Approval status: `manually_approved_for_first_no_dbr_diagnostic`
- Reason: preserves the frozen K=6 phase ramp and optical origin without forcing a center dimer.

## Approved q

- `q_nm`: `107.9769465`
- Definition: `LP phase-bin pitch / 4`
- Evidence: `Lambda_x / 6 / 4 = 2591.446716 / 6 / 4`
- Approval status: `manually_approved_for_first_no_dbr_diagnostic`
- Boundary: q was independently derived from the LP phase-bin pitch. Its numerical match to historical CP q is incidental; CP q was not reused.

## Approved diagnostic source z

- `source_z_nm`: `-200.0`
- Status: `diagnostic_manual_placeholder`
- Reference plane: Stage12 metasurface/pillar base plane z=0 nm; source_z=-200 nm is 200 nm below that plane.
- Approval status: `manually_approved_for_first_no_dbr_diagnostic`
- Usage boundary: borrowed only as a first no-DBR diagnostic depth inspired by CP-branch dipole debugging. It is not a final MicroLED MQW position and must not be used as a final DBR/RCLED device-stack value.

## Coordinate and polarization boundary

- Metasurface: x-y; nanopillar height: z; source below; emission/monitor: +z.
- Gradient axis: x; target LP: x; leakage LP: y.
- K=6 means six dimers per supercell.
- x/y dipoles are separate simulations. Never coherently add their fields.
- Later unpolarized response: `I_unpol = I_xdip + I_ydip`.
