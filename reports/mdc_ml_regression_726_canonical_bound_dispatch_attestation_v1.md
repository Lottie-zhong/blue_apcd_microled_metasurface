# Regression 726 canonical-bound dispatch attestation v1

Status: PASS. This is a non-synthetic, non-official attestation only; it did not start Formal Regression OOF.

## Identity

- execution code commit: `6a80b7cdabfe1f899e614df054f20aeac677f003`
- authorization scope: `REGRESSION_PRODUCTION_DISPATCH_ATTESTATION_ONLY`
- run root: `C:\Users\DELL\AppData\Local\Temp\mdc-regression-production-dispatch-attestation-726-20260729T052100Z\regression_dispatch_attestation-20260729T052101Z-6a80b7cdabfe`
- development view fingerprint: `dd4c85829bfc0d2b4b54c5e06b4362f8c4ccb2971084b8725177cf1b4ea0122c`
- development contract SHA256: `e4459941dc3b09ad57a31a09190e27f204a3fe6df2cd76fcf46440d88c05142b`
- canonical/config/run/manifest fingerprints: `2786ea4fb26d9743d330e1822c46a15510a0f7736a09515ccd2eac6b8d61e5f0` / `a46c090f81854dd743812f2ecb372f1b440779e6208fa7f09b2cd3f13b71dd8c` / `34eb9cebb9e75b02c0ecbf0efe75af9b69bb997b06351bdfdd65474d7fc0b477` / `d0689a3abf1c036352bb6de2901f16925fbcfff4327e5304c8c9408403fd5967`

## Results

- Four folds completed; train/validation/calibration/held-out counts: `[519,521,509,523]` / `[111,111,111,111]` / `[72,72,72,72]` / `[24,22,34,20]`.
- 12 independent seed fits, 4 ensembles, and 4 calibration-only target-wise conformal fits completed.
- Exact-once outputs: 100 sample OOF rows, 400 target OOF rows, 1,200 seed-target rows, 400 interval rows. The 28-item ineligible identity registry had zero predictions.
- Controlled failure at fold 1 seed 20260721, resume, SHA and mtime preservation, completed-run no-op, pre-fit drift rejection, and fresh-process replay all passed. Completed seeds retrained: 0.
- Classification formal artifact inventory: added/removed/modified = 0.

## Safety and verification

- `official_formal_run=false`; `formal_regression_oof_calls=0`.
- sealed-test target reads/prediction calls = 0/0; sealed-test evaluation count remained 1.
- TMM/FDTD/Lumerical calls and final classifier/regressor calls = 0.
- Targeted tests passed: `test_mdc_ml_regression_production_dispatch_v5.py`, `test_mdc_ml_regression_development_view_v1.py`, `test_mdc_ml_regression_crossfit_backend_v1.py`, and `test_mdc_ml_formal_execution_production_v2.py` (6 tests); `py_compile` and `git diff --check` passed before the implementation commit.
