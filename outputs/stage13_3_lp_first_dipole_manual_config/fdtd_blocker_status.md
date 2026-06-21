# Stage13-3 FDTD Blocker Status

## Decision

`CONFIGURATION_UNBLOCKED_FOR_NEXT_FIRST_NO_DBR_DIAGNOSTIC`

The patch, q, and diagnostic source-z decisions are manually approved. All six case rows have empty `blocking_issues`. This task still has `run_fdtd=false`; execution requires a separate FDTD task.

## Cleared decisions

- Patch: `A_small`, 3 x 19 tiles.
- q: `107.9769465` nm from the LP phase-bin pitch / 4.
- source z: `-200.0` nm as `diagnostic_manual_placeholder`.
- DBR: off.
- RCLED: off.

## Mandatory first-run order

Run only these two cases in the next FDTD stage:

1. `center_x`
2. `center_y`

Do not launch the four ±q cases until the two center diagnostics are reviewed.

## Prepared for later

- `center_x`
- `center_y`
- `x_plus_qp_x`
- `x_plus_qp_y`
- `x_minus_qp_x`
- `x_minus_qp_y`

## Non-blocking but mandatory caveats

- source z is a diagnostic placeholder, not a final MQW/device-stack location.
- Use complex-vector Ex/Ey/Ez for later LP projection; intensity-only `farfield3d` is insufficient.
- Keep x/y dipole simulations separate and combine only powers/intensities incoherently.
- Do not add DBR, RCLED, a larger patch, or a full x-y source-position sweep to the first diagnostic.
