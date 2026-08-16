# H1F-4B2 GROUPED_D_PLUS_J1_TWO_LEVER_COMBINED_LOCAL_VALIDATION

- 4/4 combined cases accepted; replay=0.
- Exact r_cancel: `-0.09287374665313898`; exact J1 delta: +/-`0.3714949866125559` nm with opposite signs for A_D +/-4 nm.
- Observed derivative is `(M(COMBINED_PLUS)-M(COMBINED_MINUS))/8 nm`; predictions were frozen before solver.
- `G_D,y=2.532797379e-04/nm`, `G_obs,y=-4.866473516e-04/nm`, mean cancellation fraction `-0.921383`; combined y response increased in magnitude and reversed sign.
- Verdict: `GROUPED_D_PLUS_J1_CANCELLATION_FAILED`.

## CONCURRENCY_3_OBSERVATION

- Peak simultaneous real FDTD jobs: 1; concurrent RCWA jobs: 0.
- LP MPI: 4 processes, 1 thread. Throughput and CPU/RAM: unavailable.
- No license denial, peer failure, or new heartbeat error observed.

## ROUTE

- `RETURN_TO_CHART`; no transfer validation, amplitude expansion, manifold expansion, or ML.
