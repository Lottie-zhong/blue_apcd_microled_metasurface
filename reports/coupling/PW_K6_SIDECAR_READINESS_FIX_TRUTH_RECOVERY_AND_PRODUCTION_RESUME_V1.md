# PW_K6 sidecar readiness fix, truth recovery and production resume

Generated UTC: 2026-09-25T21:56:09.510053+00:00

## Pre-solver authority

- This report is a pre-solver freeze. No scientific solver was launched, replayed, or created by this task phase.
- EXT01 and EXT02 remain original `attempt_001`, `FAILED_AFTER_ENTRY`, consumed, with no replay.
- EXT03-EXT14 remain `WAIT_RESOURCE_CAPACITY` and have zero scientific entries.

## Sidecar readiness fix

- `gpu_bundle.py` now waits for a non-empty sidecar layout whose size/mtime signature is stable.
- The readiness barrier invokes the normal production fresh-load validator before persistence promotion when the host supplies one.
- Bounded failures raise `NATIVE_SIDECAR_READINESS_TIMEOUT`, distinct from `MON_IN` schema failure.
- Physics, geometry, wavelength, MDC, NP, solver settings, admission caps, and fencing semantics are unchanged.

## Zero-solver evidence

- Targeted GPU bundle readiness: PASS; solver invocations=0; replay=0.
- Global regression: 20/20 PASS.
- Branch regression: 20/20 PASS.
- Chaos regression: 12/12 PASS.
- Monitor contract, PW launcher, K6 manifest, persistence, GPU truth schema, and related zero-solver tests: PASS.

## Recovery gate

- The next permitted operation is read-only completeness validation of the existing EXT01/EXT02 FSP/H5 bundles.
- Only bundles passing every scientific completeness gate may enter zero-solver post-processing recovery.
- 8G sanity is required before the single authorized real validation case EXT03.
- EXT04+ remain blocked until EXT03 cleanly validates the real post-fix path.

## Linked evidence

- `reports/coupling/PW_K6_MON_IN_EXTRACT_FAILURE_FORENSIC_V1.json`
- `reports/coupling/PW_K6_MON_IN_EXTRACT_FAILURE_FORENSIC_V1.md`
- `MONITOR_CONTRACT_HASH=6c0c434f680302664ff752b8dfa9d6ec7669909c42c8f66f1cab2b2c2bd86e28`
