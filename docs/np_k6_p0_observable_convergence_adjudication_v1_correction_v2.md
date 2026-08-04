# NP K6 P0 observable-convergence adjudication v1 correction v2

## Scope

This correction is read-only adjudication evidence. No solver was called in this adjudication round. The formal 1 ps, 2 ps, and 3 ps post-FSP artifacts remain immutable.

## 10 ps attempt

`RUN3C_P_PILOT_HF_SIMTIME_10PS_FINAL_V1/attempt_001` remains `entered=true`, `run_invocation_count=1`, with no valid post-FSP and no numerical conclusion. Exact case-bound PIDs were terminated and the scheduler task was disabled. Rerun and recovery remain forbidden. See `outputs/np_k6_p0_10ps_targeted_termination_audit_v1/` and `outputs/np_k6_p0_observable_convergence_adjudication_v1_correction_v2/stopped_10ps_attempt_audit_v2.json`.

## Read-only 2 ps -> 3 ps evidence

- 3 ps maximum full-band closure residual: `0.004513767612906006` (threshold `0.01`).
- 3 ps 448 nm structure anomaly magnitude: `0.003592535616673165` (threshold `0.01`).
- 3 ps transmitted-order sum mismatch: `2.220446049250313e-16` (threshold `1e-8`).
- 3 ps raw/sourcepower normalization mismatch: `1.1102230246251565e-16` (threshold `1e-8`).
- 2 ps -> 3 ps maximum `|delta T|`: `0.0035753884125874213`.
- 2 ps -> 3 ps maximum `|delta R|`: `0.019661248136195186`.
- 2 ps -> 3 ps maximum `|delta eta(+1)|`: `0.005410407459291555`.
- 2 ps -> 3 ps RMSE `delta eta(+1)`: `0.001859662562992096`.
- 450 nm `|delta eta(+1)|`: `0.00151657866624888`.
- Maximum directionality delta: `0.0006645047270852356`.
- Maximum full-order weighted difference: `0.007306297078812449`; mean `0.0017567396990227175`.

The revalidation retained all 11 wavelengths, no clipping/renormalization, and the original 1 ps/2 ps/3 ps post-FSP SHA identities.

## Decision

`NP_K6_P0_OBSERVABLE_CONVERGENCE_ACCEPTED_3PS_GENERATOR_READY`.

Generator: `NP_K6_PILOT_FDTD_GENERATOR_FIXED_GRID_3PS_V2`; maximum simulation time `3e-12 s`; auto-shutoff is recorded as a decay diagnostic and is not the sole label gate; pilot scope is independent K6, `u_x=0`, `k_y=0`, p/s, 445--455 nm, and not bulk MDC compatible.

Formal HF labels remain `0`; no model training, checkpoint, or sealed-test access occurred. The five formal remaining anchors remain `entered=false`, `run_invocation_count=0`; they were not started in this adjudication round.

An accidental prior continuation `RUN3C_S_PILOT_HF_V1` V2 attempt was stopped before post-FSP and is explicitly excluded from adjudication and label generation.

Next action: wait for explicit user authorization to run the remaining five anchors with generator V2.
