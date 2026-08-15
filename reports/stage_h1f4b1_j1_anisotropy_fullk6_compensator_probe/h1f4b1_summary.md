# H1F-4B1 J1 anisotropy full-K6 compensator Jacobian probe

- H1F4B0 path anomaly was a stale final-summary path; committed evidence is in the LP worktree.
- Primary seed: `K6_L1_C_POS_PLUS10`; hash `a8606d8f44a4675db08493c3dd95c8ea43f30882d3a9bbb18a65b59c2ba45198`.
- J1 mode: `J1_length=J1_side+delta_nm`, `J1_width=J1_side-delta_nm`, preserving mean dimension at all six sites and the frozen local-axis convention; delta is +/-2 nm.
- 4/4 FDTD cases accepted; replay=0. Baseline was recovered from the authoritative H1F3B artifact and was not rerun.
- J1 central difference is `(M(+2)-M(-2))/4 nm`; even residual is `(M(+2)+M(-2))/2-M(0)`.
- `d eta_y,+1/dJ1` mean is `+2.7271403e-3/nm`; `d eta_x,+1/dJ1` mean is `-2.6817358e-3/nm`.
- Frozen grouped-D directional derivatives are available for eta_x,+1, eta_y,+1, eta_x,0 and eta_x,-1 from the existing H1F4A full-wave order artifact; no grouped-D solver was rerun.
- `r_cancel=-0.09287375`; per-wavelength values are recorded in `h1f4b1_cancellation.csv`.

## CONCURRENCY_3_OBSERVATION

- Peak simultaneous real FDTD jobs: 3; concurrent RCWA jobs: 1.
- LP MPI: 4 processes, 1 thread. Throughput and CPU/RAM telemetry: unavailable.
- No license denial or peer solver failure; one scheduler heartbeat registry write returned WinError 5.

## VERDICT

`J1_ANISOTROPY_FULLK6_COMPENSATOR_LEVER_PARTIAL`; no combined geometry was run or auto-promoted.
