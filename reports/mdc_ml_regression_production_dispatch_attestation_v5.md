# MDC-ML regression production-dispatch attestation v5

`PRODUCTION_DISPATCH_ATTESTATION_COMPLETE=true`

- implementation commit: `491bc534d6dc8ad711837ec7036894d8279a3e57`
- authorization scope / run kind: `REGRESSION_PRODUCTION_DISPATCH_ATTESTATION_ONLY` / `regression_dispatch_attestation`
- official formal run: `false`; formal Regression OOF calls: `0`.
- recovered legacy root (read-only): `C:\Users\DELL\AppData\Local\Temp\mdc-regression-production-dispatch-durability-v1-20260728T101307Z`
- v5 evidence root: `C:\Users\DELL\AppData\Local\Temp\mdc-regression-production-dispatch-v5-20260728T122408Z\regression_dispatch_attestation-20260728T122409Z-491bc534d6dc`
- canonical input/config/run fingerprints: `3f023b72975552db56a8164ce0ee33d736850991df91b29bc5b692d986a8fa1a`, `812f69a3645f0e085aee0c7ae9c5a4ee7ee3eafa37903450fdd9400590d02693`, `44ec6adef3d5038884dd84496573b4406899751e762bdd9c4913bed5f53e966a`.
- actual output manifest SHA-256: `2c7bafe1f1cae89bb8f669fc0b76ab102c6b7d24c67a9dfa71f3dc9f2eb0fa1c`.

## Evidence

Failure injection at `fold=1, seed=20260721` failed as expected. Resume completed four folds and 12 unique seed fits; completed seed retraining was zero and preserved checkpoint SHA-256 and mtime. Exact-once output was 100 sample rows, 400 target rows, 1,200 seed-target rows, 400 intervals, and 28 ineligible rows with zero ineligible predictions and no missing/duplicate/unexpected/NaN/Inf rows.

Input-snapshot drift was rejected before a fit (`REGRESSION_DISPATCH_INPUT_DRIFT_GUARD`, zero new fits); the completed dispatcher rerun was a strict no-op. A distinct fresh Python process replayed disk artifacts successfully. The formal Classification OOF root remained immutable: 47 files before/after, zero additions, removals, SHA mutations, and mtime mutations; its frozen manifest and fingerprint were not altered.

Focused relevant suite: `10 passed in 142.73s`. Safety counters remained zero: sealed-test target/prediction reads, solver calls, formal Regression OOF calls, and final model calls. Evaluation count remained 1. `FORMAL_REGRESSION_OOF_COMPLETE=false`.
