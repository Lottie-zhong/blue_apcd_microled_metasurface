# APCD MDC-ML Regression Three-Seed Crossfit Backend Freeze

Status: `FROZEN_SYNTHETIC_REGRESSION_BACKEND_V1`

`REGRESSION_THREE_SEED_CROSSFIT_BACKEND_FROZEN=true`

`FORMAL_CLASSIFICATION_OOF_STARTED=false`

`FORMAL_REGRESSION_OOF_STARTED=false`

`FORMAL_TRAINING_STARTED=false`

`FULL_TRAINER_IMPLEMENTATION_FROZEN=false`

This checkpoint freezes a synthetic-only regression backend. It does not claim that formal Round1 regression OOF, final v2 regression training, sealed-test evaluation, model promotion, Round2, FDTD shortlisting, or any solver execution has run. Classification Stage B remains frozen and unchanged.

## Frozen backend contract

- Targets, in order: `spectral_fwhm_normal_nm`, `angular_fwhm_450_deg`, `cone5_integral_proxy`, `normal_band_transmission_proxy`.
- Candidate: `multitask_mlp_3seed`; 150 input features; MLP `150 -> 256 -> 128 -> 4`, ReLU and dropout 0.1.
- Seeds: `20260720`, `20260721`, `20260722`; independent initialization, optimizer, checkpoint, best epoch, and validation trace for every fold/seed unit.
- Optimizer/loss: AdamW (`lr=0.0007`, `weight_decay=1e-5`, betas `(0.9, 0.999)`, eps `1e-8`) and SmoothL1Loss(beta=1.0).
- Feature and four-target scalers are fit only from the current fold training rows. Original validation is early-stopping-only; original calibration is conformal-only; held-out rows and sealed test are excluded.

## Metadata and output contract

- Round1 rows: 128; regression eligible/ineligible: 100/28; overlap: 0.
- Eligible fold sizes from metadata: `[24, 22, 34, 20]`; exact-once held-out total: 100.
- Synthetic fixture outputs: 100 sample OOF rows, 400 ensemble sample-target rows, 1,200 per-seed sample-target rows, and a 28-row ineligible registry. Ineligible prediction count is zero.
- Each target receives calibration-only absolute-residual nonconformity, a target-wise higher-quantile, and held-out lower/upper intervals. The frozen formal contract has no coverage/alpha value, so the fixture-only coverage is 0.90 and `FORMAL_CONFORMAL_COVERAGE_PARAMETER_PENDING_CONTRACT=true`.
- Artifact set includes OOF sample/target/seed tables, intervals, calibration nonconformity, quantiles, ineligible registry, fold plan, seed/scaler/checkpoint/OOF manifests, and the atomic artifact manifest.

## Synthetic execution evidence

The pre-commit fixture `regression-precommit-v1` passed with 12 real MLP fits (4 folds x 3 seeds), zero formal fits/OFF calls/output writes, zero sealed-test accesses, and zero TMM/FDTD/Lumerical calls. The fixture injects failure before `fold1_seed20260722`, observes a `FAILED` state, resumes without refitting completed seeds, preserves their SHA-256 and mtime, rejects an artifact-drift resume, and finishes with `REGRESSION_OOF=COMPLETE` and top-level `PARTIAL`.

Fresh-process evidence used a distinct child PID, reloaded persisted seed checkpoints, rebuilt per-seed predictions, ensemble mean, conformal intervals, and eligible/ineligible signatures, and returned zero. Fixture audit SHA-256: `f20e40536fa51bcde4c9c5855d39175da0ec54da10e34e157e8835de3fdc9c6d`.

## Tests and non-mutation audit

- Regression backend pytest: 2 passed.
- Existing merge-retrain backend, Classification Stage B backend, and active-learning merge-retrain suites were executed after the shared-state change with a zero exit code.
- Regression metadata-only CLI audit passed: 128 rows, 100/28 partition, fold sizes `[24, 22, 34, 20]`, all formal/sealed/solver counters zero.
- Official output trees were fingerprinted before the final fixture and compared afterward; no official output writes occur in this backend. The formal tree baseline remains 10 files and 18,082,726 bytes.

## Retained MDC interface and next module

MDC-side labels retain full complex scattering-matrix, port/basis, wavelength/angle, structure/provenance, derived-target, quality, and failure-mode contracts for future MDC-NP coupling; no NP database is copied or reconstructed here.

Next authorized phase: `FORMAL_MERGE_RETRAIN_OOF_EXECUTION_AND_DEVELOPMENT_TRAINING_V2`.
