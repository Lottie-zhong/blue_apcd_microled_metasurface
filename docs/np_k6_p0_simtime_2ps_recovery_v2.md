# NP K6 P0 2 ps recovery-v2 evidence

## Classification

`SIMULATION_TIME_EXTENSION_CLOSURE_PASS_DECAY_CONVERGENCE_UNRESOLVED`

The single authorized `RUN3C_P_PILOT_HF_SIMTIME_2PS_RECOVERY_V2/attempt_001` completed all 209,800 iterations at 1.999997e-12 s. The controller exited before post-save; the completed run copy was independently reloaded and binary-copied to the post-FSP path without a second solver call.

## Execution

- Source pre-FSP SHA256: `76d23a8961267fb6a720ad875ba016b56aed5c65e8c7379ce09b0cea6029ef1f`
- Post-FSP SHA256: `f0119e256cf64e4875d82c0c5cca3dbc854936fc429aca4643577d7b2b1005d7`
- `entered=1`, `run_invocation_count=1`, `engine_completed=1`, `post_saved=1`, `controller_returned=0`, `controller_recovery_completed=1`
- Runtime: 10829.526229 s; fixed simulation-time completion; last periodic auto-shutoff sample 1.50024e-4 (threshold 1e-5 was not the termination reason).

## Numerical result

- 11 exact wavelengths 445--455 nm; all finite.
- Maximum absolute closure residual: `0.02059962733651377` at 448 nm (gate 0.02, fail by 5.9963e-4).
- 448 nm: `T=0.5053457166872318`, `R=0.4740546559762544`, residual `+0.02059962733651377`.
- 449 nm: `T=0.6644653378812949`, `R=0.33942522401330766`, residual `-0.0038905618946025733`.
- 450 nm: `T=0.7395719671897157`, `R=0.26067433158527137`, `eta(+1)=0.6216787417275325`.
- 448 nm structure-interval flux jump: `-0.019825876414615418`; lower/upper transition jumps are `-1.57027e-05` and `-9.71118e-06`.
- Maximum transmitted-order sum mismatch: `2.220446049250313e-16`; no order-normalization failure.

## Comparison with 1 ps

- Closure improved from `0.0812666246641951` to `0.02059962733651377` (absolute improvement `0.06066699732768133`, relative `74.66%`).
- 448 nm structure anomaly magnitude improved from `0.08020762156035277` to `0.019825876414615418` (relative `75.28%`).
- Observed periodic auto-shutoff sample improved from `2.61435e-4` to `1.50024e-4`; termination remained fixed-time.
- Runtime multiplier versus the 1 ps formal run: `2.3729376762765413`.

## Data gate

This is provisional observation evidence only. Formal HF labels, candidate labels, training labels, model checkpoints, sealed tests, and the remaining five P0 cases remain untouched.

Evidence: `outputs/np_k6_p0_simtime_2ps_recovery_v2/`.

Next action: wait for explicit authorization before any remaining P0 anchor case.
