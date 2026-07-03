# R2-4E0 D9 No-Pass Route Reset

D9 returned no-pass: the old candidate pool did not satisfy the D8-derived conservative guards. Therefore no old candidate should be hard-picked for more FDTD.

## Why old-candidate FDTD is blocked
- D7 proved D5_BASE_13461 fails the x-line x-dipole scout at 453 nm.
- D8 diagnosed the failure mode: center-only near-normal emission does not represent the x-line source-position ensemble.
- Off-center source positions can revive the 30-40 deg off-axis lobe.
- D9 applied these guards to the old pool and found no justified shortlist.

Continuing old candidates would repeat the center-only false-positive pattern instead of testing a corrected design hypothesis.
