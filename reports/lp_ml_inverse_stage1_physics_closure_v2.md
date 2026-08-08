# LP ML inverse Stage-I physics closure v2

## Tuple-gate root cause

The previous `all(planned_candidates_complete_per_bin)` predicate was an `OVERSTRICT_BATCH_COMPLETION_GATE`. Tuple enumeration correctly used one complete candidate from each bin, excluding the quarantined B2 y case.

## Physics integrity

35 complete prospective single-dimer 450-nm weighted-G0 Jones candidates were independently recomputed. Counts are B0/B1/B2/B3/B4/B5 = 6/6/5/6/6/6.

## Tuple result

The raw tuple space is 38,880 (`6 x 6 x 5 x 6 x 6 x 6`). A common phi offset was fit for every tuple. A formal tuple front exists, but the best balanced tuple has a 60-degree phase-grid RMS of 94.3273 degrees. All bin phases remain concentrated near 73-94 degrees, so the inverse six-bin objective is not physically closed.

## Closure decision

`LP_ML_INVERSE_STAGE1_FIVED_SPACE_INSUFFICIENT_EVIDENCE`. A tuple exists combinatorially, but no reasonable six-bin phase closure was demonstrated. No broadband proposal was generated.

## Constraints

Solver calls in this task: 0. No B2 rerun, replacement, new geometry, broadband FDTD, K6, Round-4, geometry054, model retraining, or protected-report modification.
