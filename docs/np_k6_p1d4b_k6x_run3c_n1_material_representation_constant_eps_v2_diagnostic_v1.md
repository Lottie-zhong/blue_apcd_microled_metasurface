# NP K6-x constant-epsilon v2 diagnostic v1

Status: MATERIAL_REPRESENTATION_CONSTANT_EPS_V2_PARTIAL_EFFECT

This is a diagnostic-only single solver attempt. It is not a production mesh freeze, DOE result, or training label.

- Case: RUN3C_N1_MATERIAL_REPRESENTATION_CONSTANT_EPS_V2_DIAGNOSTIC / attempt_001
- Setup SHA256: 8b7551773caf482a9af8d4470572fa5f4b05aee6843f4ab521d8ff88d4bef522
- Post-FSP SHA256: 2d01ccb9daf15dd52c077bb994e3eb93f62016af6c0256bc77837f9964a9a72b
- entered/engine/controller/post-save/run_invocation: True/True/True/True/1

## Material readback

Both TiO2 and SiO2 reload as scalar `Dielectric` materials with no sampled-data or frequency table. Their 445/449/455 nm complex epsilon values are constant and match canonical Native-M1 epsilon at 449 nm within the recorded tolerance; n² readback errors are recorded in `post_run_material_audit.json`.

## Diagnostic result

- 449 nm T/R/residual: 0.6245991117111378, 0.34825246897499496, 0.027148419313867245
- 449 nm absolute closure: 0.027148419313867245
- 449 nm structure interval signed gain: -0.026064653140363103
- Full-band maximum absolute closure: 0.027148419313867245
- Order-sum mismatch maximum: 2.220446049250313e-16
- 450 nm T/R/residual: 0.6836449549409476, 0.3402610711630233, -0.023906026103970857

The constant-epsilon control reduces both baseline 449 nm anomalies by more than 25% but does not meet the 0.02 restoration gates; classification is PARTIAL_EFFECT. Coordinate-grid equality versus sampled fixed-N1 is true; index/material tensor values are expected to differ.

## Scope and next action

- diagnostic_only=true
- production_mesh_frozen=false
- candidate_performance_label=false
- k6_training_label=false
- no N2 or additional case run
- solver entered exactly once

Await explicit authorization before any further solver attempt.
