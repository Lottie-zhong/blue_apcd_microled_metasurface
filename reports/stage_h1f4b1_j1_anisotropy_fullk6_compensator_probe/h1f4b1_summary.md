# H1F-4B1 J1 anisotropy full-K6 compensator Jacobian probe

- 4/4 formal cases accepted; no replay.
- J1 central difference: `(M(+2 nm)-M(-2 nm))/4 nm`; even response is unavailable because the baseline was not rerun.
- Grouped-D uses the frozen H1F4A direction rule; no new grouped-D solver.

## CONCURRENCY_3_OBSERVATION

- Peak simultaneous real FDTD jobs: 3; concurrent RCWA jobs: 1.
- LP MPI: 4 processes, 1 thread.
- Throughput and CPU/RAM telemetry: unavailable.
- License denial: none observed.
- Controller: one heartbeat registry write permission error; all four LP cases accepted and no peer solver failure observed.

Verdict: `J1_ANISOTROPY_FULLK6_COMPENSATOR_LEVER_PARTIAL` pending Chart review.
