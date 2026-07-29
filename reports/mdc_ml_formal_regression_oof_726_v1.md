# Formal Regression OOF 726 v1

Status: PASS. This report records the single authorized canonical, non-synthetic official Regression OOF and does not compare, promote, or select models.

## Run identity

- run ID/root: `regression_oof-20260729T055956Z-3109d794627e` / `C:\Users\DELL\AppData\Local\Temp\mdc-formal-regression-oof-726-20260729T055955Z\regression_oof-20260729T055956Z-3109d794627e`
- execution-code commit: `3109d794627e5d79cb23d2568b77036bb13b2960`
- canonical/config/view/run/manifest fingerprints: `7769c95d8062a73133490463c330120ad9eb7e19d57b9a15bfea6b9eb3afe054` / `531fdff3dfb57d7233915c103a0e118369633a3e619eeb45092edef1f03b350d` / `dd4c85829bfc0d2b4b54c5e06b4362f8c4ccb2971084b8725177cf1b4ea0122c` / `4ba215d7d6584eca22de0cba4dfcfc3f7ebf797ce1950aeb27250f791ad4dbac` / `9d091f9b1548ea391edfda248154d7ec2bf23f25e6228ce1fc0f1cac4657da9e`
- development contract SHA256: `e4459941dc3b09ad57a31a09190e27f204a3fe6df2cd76fcf46440d88c05142b`

## Completion and boundaries

- 4 folds; train/validation/calibration/held-out counts `[519,521,509,523]` / `[111,111,111,111]` / `[72,72,72,72]` / `[24,22,34,20]`.
- 12 independent seed models, 4 ensembles, 4 target-wise calibration-only conformal fits; exact-once rows 100 sample / 400 target / 1,200 seed-target / 400 interval.
- 28 ineligible identities were registry-only and had zero predictions. Completed-run rerun was a strict no-op; fresh-process reload/replay passed.
- Original rejected run `regression_oof-20260728T131110Z-1c865c984fde` was not reused. Classification formal inventory added/removed/modified = 0.
- Sealed target reads/predictions = 0/0; sealed evaluation count remained 1. TMM/FDTD/Lumerical and final-model calls = 0.

## OOF metrics and conformal

| Target | MAE | RMSE | empirical coverage | mean interval width |
| --- | ---: | ---: | ---: | ---: |
| spectral_fwhm_normal_nm | 2.227742 | 4.183299 | 0.91 | 14.979141 |
| angular_fwhm_450_deg | 7.841950 | 10.809938 | 0.95 | 47.267502 |
| cone5_integral_proxy | 0.027312 | 0.035422 | 0.93 | 0.143934 |
| normal_band_transmission_proxy | 0.156635 | 0.203544 | 0.94 | 0.843956 |

Conformal coverage was 0.90 with `higher` quantiles. Fold 0/1/2/3 quantiles respectively were `[7.167443,22.100594,0.071012,0.416622]`, `[7.961740,23.703237,0.073012,0.421347]`, `[7.136562,24.877866,0.072340,0.427542]`, and `[7.956853,23.282109,0.071330,0.419641]`.

Early stopping produced 12 checkpoints; best epochs ranged 98–162, with best validation losses 0.131191–0.141196.
