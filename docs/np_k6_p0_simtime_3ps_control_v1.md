# NP K6 P0 3 ps simulation-time convergence control v1

- case: `RUN3C_P_PILOT_HF_SIMTIME_3PS_CONTROL_V1` / `attempt_001`
- setup SHA256: `390e6164c438a1b2b24ce84a463c4bfc58d5baa6cc06339dbe1fb1412086d21e`
- post-FSP SHA256: `c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca`
- single changed property: `FDTD/simulation time`, 2 ps -> 3 ps
- solver entered/run: `1/1`
- classification: `SIMULATION_TIME_3PS_CLOSURE_PASS_DECAY_UNRESOLVED`

## Numerical evidence

- max full-band closure residual: `0.00451376761291` at `448 nm`
- 448 nm structure interval delta: `-0.00359253561667`
- final logged auto-shutoff: `7.43634e-05`; fixed-time termination is distinguished from threshold termination
- max order-sum mismatch: `2.22e-16`
- max direct-power normalization mismatch: `1.11e-16`

Formal HF labels, candidate labels, training labels, and model checkpoints remain zero; the remaining five P0 cases remain untouched. Actual solver-core grid equality is not claimed from monitor coordinate readback.
