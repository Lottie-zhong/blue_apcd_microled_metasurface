# LP ML Round-2 Clean Recompetition v2

## Status

`LP_ML_ROUND2_RECOMPETITION_PASS_INVERSE_PLANNING_READY`

## 054 authoritative boundary

`LPML_R1_GLOBAL_SOBOL_054` remains `QUARANTINED_INCOMPLETE_NO_COMPLETE_JONES_V1`. Its original identity/hash, orphan x checkpoint and two failed y entered records are retained as read-only evidence. It contributed zero admitted physics rows. No 054 solver was run and no source physics checkpoint was changed. Any old postprocess rows that claimed acceptance are classified `POSTPROCESS_PROVENANCE_CONFLICT`, diagnostic-only and superseded.

## Merge root cause

The old Round-2 postprocess loaded staging Jones rows without applying the plan/quarantine admission contract and wrote `geometry_054_excluded=False` on Round-2 rows. This was a stale status/path admission problem, not a physics repair. Clean v2 admits only exact hash, accepted x and y, checkpoint provenance, matching attempt/case ledger, complete nine-wavelength grid, frozen weighted-G0/reference/normalization and non-quarantine identity. Geometry ID alone is not a join key.

## Clean rematerialization

| view | geometries | rows | wavelengths/geometry | 054 rows | model-filled | duplicates |
|---|---:|---:|---:|---:|---:|---:|
| Round-1 clean | 255 | 2295 | 9 | 0 | 0 | 0 |
| Round-2 accepted clean | 64 | 576 | 9 | 0 | 0 | 0 |
| merged clean v2 | 319 | 2871 | 9 | 0 | 0 | 0 |

Dataset SHA256: `ca2fd154eed8e9b2f41b92c2f2aaa95f77d451c7047e4056f84a430c56e67336`
Split SHA256: `2a4223f802204e870cc7d28d956f5c705f9442ccdbad2ad9bd10fecab07ce661`
Normalization SHA256: `13c7855b48d8c34e674ea67cb343df9414306cf43a943efdec6bba001f864167`

## Superseded artifacts

The prior merged/staging-derived Round-2 models, predictions, metrics and promotion records are retained but ledgered as `CONTAMINATED_BY_054_POSTPROCESS_PROVENANCE_CONFLICT`, `DIAGNOSTIC_ONLY`, `NOT_PROMOTABLE`, and `SUPERSEDED_BY_CLEAN_REMATERIALIZATION_V2`. The Round-1 champion remains current because its input hash is the clean Round-1 dataset hash.

## Clean splits

Geometry-level splits are clean: Round-1 train/validation/test = 179/38/38 geometries; Round-2 train/validation/test = 48/8/8. All wavelengths stay with their geometry, no canonical/symmetry leakage was observed, and normalization uses clean training geometries only. Round-2 external test remains the frozen 8 geometries.

## Candidate models

C0 is the frozen Round-1 champion. C1, C2, C3 and C4 were trained from random initialization with seeds 11/22/33/44/55, CUDA (`RTX 3080` runtime), no warm start, and no solver. C2 is replay-balanced, C3 domain/stratum balanced, and C4 uses reduced auxiliary losses.

## Validation-only selection

| model | validation score | gate |
|---|---:|---|
| C1 | 0.657466 | PASS |
| C2 | 6.714427 | FAIL |
| C3 | 3.069027 | FAIL |
| C4 | 0.807386 | FAIL |

C1 was the best new model. The selected validation-only blend is C0/C1 with `alpha=0.95`; no frozen-test value was read for model selection.

## Frozen-test comparison

| model | R1 test Frobenius mean | R2 test Frobenius mean | R1 phase MAE (deg) | R2 phase MAE (deg) |
|---|---:|---:|---:|---:|
| C0 | 0.045941 | 0.123696 | 0.8528 | 2.4809 |
| C1 | 0.050758 | 0.098784 | 1.0344 | 2.3589 |
| selected blend | 0.050280 | 0.099621 | 1.0224 | 2.3643 |

The selected blend improves the frozen Round-2 external Frobenius mean by 19.5% relative to C0 while staying within the frozen Round-1 preservation gate. Paired geometry bootstrap and uncertainty/calibration are recorded in the analysis artifacts.

## Promotion decision

`LP_ML_ROUND2_RECOMPETITION_PASS_INVERSE_PLANNING_READY`. This authorizes only the already-scoped inverse-planning discussion; it does not authorize solver, inverse FDTD, Round-3, K6 or new geometry.

## Champion status

The original Round-1 champion remains `CURRENT_CHAMPION`; the clean-v2 C0/C1 blend is the selected Round-2 candidate pending any separately authorized promotion action. No contaminated artifact is promotable.

## Tests and hard gates

The targeted clean/recompetition and prior recovery tests passed `15/15`; the LP-ML related shard passed `80/80`. `solver_calls=0`, no inverse/Round-3/K6, no protected report edits, no raw physics edits, no model-filled rows, and no geometry 054 rows.

## Outputs

Clean data/manifests are under `outputs/lp_ml_dataset_v1/clean_v2/`. Recompetition analysis is under `outputs/lp_ml_dataset_v1/analysis/` with training, validation selection, blend, final tests, bootstrap, promotion and checksum JSONs. The execution script is `scripts/lp_ml_round2_clean_recompetition_v2.py`.
