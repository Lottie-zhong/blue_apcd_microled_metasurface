# NP K6 P0 decay-tail projection v1

- classification: `DECAY_TAIL_PROJECTION_INCONCLUSIVE`
- source case: `RUN3C_P_PILOT_HF_SIMTIME_3PS_CONTROL_V1` / `attempt_001`
- post-FSP SHA256: `c14fd3a2464e11c3ba667e4b513bd76a1828c918f80df54511fec7862e2705ca`
- runtime history samples: `100`
- time range: `0.000457578–2.99012 ps`
- final auto-shutoff: `7.43634e-05` at `2.99012 ps`

## Decay history and provenance

The history is read-only data parsed from the 3 ps engine runtime log. No solver, run, save, post-FSP modification, training, checkpoint, or sealed-test access occurred in this stage. Source-off time was not exposed by the post-FSP/runtime evidence, so the effective tail windows are explicitly reported by sample percentile rather than asserted as a source-off timestamp.

## Tail fits

All fits use log10(auto_shutoff_value) versus time_s. No samples were deleted or reweighted. Reliability gates are n>=10, slope<0, monotonic fraction>=0.8, R2>=0.95; at least two reliable windows and crossing-time agreement within 10% are required for a recommendation.

- last_10_percent: n=10, start=2.71832 ps, slope=-0.251383/ps, R2=0.0353105, monotonic fraction=0.444444, crossing=6.06969 ps, CI95=[-15.915, 28.0543] ps, reliable=False
- last_20_percent: n=20, start=2.41632 ps, slope=-0.163808/ps, R2=0.0560259, monotonic fraction=0.473684, crossing=7.76493 ps, CI95=[-6.95965, 22.4895] ps, reliable=False
- last_30_percent: n=30, start=2.11432 ps, slope=-0.180763/ps, R2=0.13013, monotonic fraction=0.482759, crossing=7.30511 ps, CI95=[0.309222, 14.301] ps, reliable=False

All three windows fail monotonicity and R2 gates. The endpoint trend is therefore insufficient for a defensible threshold-crossing time.

## Recommendation

`recommended_max_simulation_time_ps = null`; no next solver time is authorized or recommended. Expected early-stop behavior is unsupported because the 3 ps run terminated at fixed simulation time with auto-shutoff above 1e-5.

## Data gate

- formal HF labels: 0
- training labels: 0
- candidate labels: 0
- remaining five pilot cases untouched
- model training/checkpoints: 0
- sealed-test access: 0
- solver run performed in this stage: false

## Evidence

See the JSON/CSV files in `outputs/np_k6_p0_decay_tail_projection_v1/`.
