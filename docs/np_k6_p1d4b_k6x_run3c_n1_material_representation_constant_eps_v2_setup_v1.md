# NP K6-x constant-epsilon v2 setup-only

Status: `READY_FOR_RUN3C_N1_MATERIAL_REPRESENTATION_CONSTANT_EPS_V2_DIAGNOSTIC_AUTHORIZATION`

This directory is independent of the consumed invalid control evidence. The old control is explicitly superseded as `MATERIAL_REPRESENTATION_CONTROL_INVALID_WRONG_REPRESENTATION`; no physics conclusion is retained.

The new setup changes only the seven geometry-object material references to scalar Lumerical `Dielectric` materials whose permittivity is taken from the canonical Native-M1 loader at exactly 449 nm. It does not claim actual solver-grid equality. `entered=false`, `run_invocation_count=0`, no engine/controller/scheduler was started.

Setup SHA256 is recorded in `setup_checksum.json`; independent reload proves no sampled-data or frequency-table property, constant 445/449/455 readback, and n^2=epsilon.
