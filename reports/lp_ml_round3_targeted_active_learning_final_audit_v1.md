# LP ML Round-3 targeted active learning final audit v1

## Status

`LP_ML_ROUND3_SIX_BIN_PARTIAL_COVERAGE_ROUND4_RECOMMENDED`

## Physics accounting

64 planned geometries; 128 planned x/y subruns; 127 solver-entered records, 126 unique attempt IDs, one duplicate entered accounting, 121 accepted subruns, 6 isolated failed/quarantined cases, 58 complete geometries, and 522 accepted spectral rows. No retry or replacement was performed.

## Clean materialization

Clean-v3 contains 377 geometries / 3393 rows (319 clean-v2 + 58 complete Round-3 geometries). Six Round-3 geometries remain a deterministic coverage gap; geometry 054 is absent and model-filled rows are zero.

## C5 and validation-only selection

C5 used five random seeds from scratch on the RTX 3080. Validation-only selection chose `OLD_C5_BLEND_0.95` with score 0.315115799; frozen tests were evaluated afterward on Round-1, Round-2, and Round-3 domains.

## Six-bin surrogate search

The repeated offline search returned `LP_ML_SIX_BIN_INVERSE_PARTIAL_COVERAGE_ROUND3_RECOMMENDED` with 508 candidates, 103 tuple-front entries, and per-bin counts {'0': 59, '1': 263, '2': 55, '3': 45, '4': 46, '5': 40}. Planning weights are C0=0.9025, C1=0.0475, C5=0.05. Solver calls in this search: 0.

## Route

Do not authorize inverse-FDTD yet. Repair or diagnostically close the six missing Round-3 geometries first; then rerun the same validation/audit gates. No Round-4, K6, inverse design, or new degree of freedom was generated.

## Protected evidence

Protected report hashes were rechecked and unchanged. Historical physics and geometry054 evidence were not rewritten.
