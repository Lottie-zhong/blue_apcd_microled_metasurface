# Cyclic equivalence and validation leakage audit

## Data and cyclic equivalence

The source is the existing `STAGE_50/COMPLEX_DATASET.npz`, backed by its `FAST_DATASET_MANIFEST.json`: 222G historical FAST data plus 50 labels-valid AL50 cases, total 272 distinct case IDs; validation124 and old 222G training identities are recorded unchanged, and the manifest states no sealed access. All 272 ordered six-diameter vectors are unique. Canonicalization by the lexicographically minimum of the six cyclic rolls yields 272 orbit classes, each containing one observed case. Therefore there are **zero real-data rotated duplicate pairs** to compare phase-aligned complex labels against; native-response parity for a matched rotated pair is NOT MEASURED. The exact transformation is tested algebraically and against the production projector separately.

## Fixed four-fold identity audit

The audit reuses the established family-guarded 124-development geometry split. Full row-level identities, ordered diameters, family IDs, all-21-wavelength grouping, canonical cyclic key, and fold-role overlaps are in `CYCLIC_FOLD_IDENTITY_AUDIT.csv`. Role counts below come from the prior frozen `CV_SPLIT_IDENTITY_CHECK.csv` geometry rows.

| Fold | Train | Primary validation | Purged | Other held out | Train/validation family overlap | Train/validation cyclic-orbit overlap |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 216 | 32 | 10 | 14 | 0 | 0 |
| 2 | 217 | 31 | 10 | 14 | 0 | 0 |
| 3 | 208 | 30 | 11 | 23 | 0 | 0 |
| 4 | 217 | 31 | 10 | 14 | 0 | 0 |

For every fold, case IDs are disjoint between train and primary validation; family overlap is zero; cyclic-orbit overlap is zero; every geometry carries all 21 wavelengths in a single role. No cyclic leakage was found, so the validation manifest was not regenerated. Counts marked `PURGED` and `OTHER_HELDOUT` preserve the existing audit roles rather than being reclassified.

## Limits

No validation geometry or family was moved. The 124 geometries have been repeatedly used in development/model selection, so all new metrics remain **DEVELOPMENT EVIDENCE**, not final generalization certification. The separate sealed confirmation remains untouched. Synthetic augmented rotations are generated only from training labels inside each fold; validation rotations are used only for inference diagnostics.
