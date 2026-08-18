# Paper A LP+CP broadband scope V1

## New scientific goal

Current-Native broadband polarization-state engineering for conditioned blue MicroLED emission.

- CP is a frozen positive reference: `CP_NATIVE_M1_BROADBAND_L_PRESERVED`, with L dominant throughout 420–480 nm and no handedness flip.
- LP is a new CP-inspired axis-free linear-state search: maximize DoLP, useful polarized power, stable linear axis `psi`, and stable dominant Jones channel over the MDC main spectrum. `psi` is not constrained to 0 degrees.

## Removed objectives

Six-phase reachability, K6 composition, beam steering, LP-K6, grouped-D, J1 rescue, phase coverage, and old historical rescue ranking are not objectives and cannot qualify a new LP candidate.

## Frozen sources

Old LP and CP worktrees are frozen read-only provenance. MDC is a frozen read-only provider. Production physics uses only Native-M1 materials and the shared global scheduler. This bootstrap ran zero FDTD, RCWA, or ML jobs.
