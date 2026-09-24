# GPU Native Truth Bundle V1

Status: **BLOCKED_MISSING_MON_REFLECTION**.

The bundle durability audit was zero-solver and found the FSP/H5 pair plus provenance files, but the required `MON_REFLECTION` data card is absent from the completed FSP. Therefore this bundle cannot be promoted as complete native truth under the current contract.

Checks completed:

- 9-file bundle inventory created with per-file SHA256.
- FSP SHA256: `025cf68135ff4c2341f611b385abf181f26e294265c9b1c9486f4d37c0b46afd`.
- H5 SHA256: `89327c22f398f5f24984007779cf12defaf764ae65e7f0ad44a5e0ac789049f9`.
- Bundle manifest SHA256: `c540c8a6027524baee5a29a2e30b81a880c680dfdad74a0f7cf027c6289fd042`.
- Fresh LOAD-only copy opened successfully.
- `MON_IN`, `MON_PRENP`, and `MON_POSTNP` fields, T, and grating data loaded successfully.
- Canonical state reconstruction succeeded: 3 planes, 21 wavelengths, 81 orders.
- Archive/restore preserved all 9 inventoried files and hashes.
- Synthetic omission test detected a missing `runtime/runtime_output.h5`.
- Solver invocation: false.

Hard failure:

- `MON_REFLECTION` is not present in the completed FSP. Its field, T, and grating queries all fail with a missing d-card/result-provider error.
- `MON_IN` is not substituted for `MON_REFLECTION`; that would change the contract and is not evidence of reflection truth.

Evidence:

- Audit: `outputs/coupling_ml/W2H_15294_5NM_GPU_HIGH_FIDELITY_CANARY_V1/attempt_001/GPU_NATIVE_TRUTH_BUNDLE_DURABILITY_AUDIT.json`
- Archive bundle: `outputs/coupling_ml/W2H_15294_5NM_GPU_HIGH_FIDELITY_CANARY_V1/attempt_001/archive/gpu_native_truth_bundle_v1/attempt_001`
- Restored bundle: `outputs/coupling_ml/W2H_15294_5NM_GPU_HIGH_FIDELITY_CANARY_V1/attempt_001/archive/gpu_native_truth_bundle_v1/restore_attempt_001`

Decision: stop before seed-DB initialization. No solver replay, no new scientific entry, and no attempt-002 is authorized by this report.

## Role-aware schema correction and V2 attempt

The technical-lead decision freezes `MON_REFLECTION` as R-only. Its `complex_fields=[]` is valid when the signed Poynting payload and normalized R are readable; E/H is required only for `MON_IN`, `MON_PRENP`, and `MON_POSTNP`.

`5NM_GPU_PRODUCTION_SETUP_V2` passed zero-solver structural diff with `+ MON_REFLECTION` only. Its sole authorized run attempt failed before an FDTD engine was observed because the LSF resource name did not match an installed resource. No V2 H5 or truth payload was produced, so the bundle remains blocked.
