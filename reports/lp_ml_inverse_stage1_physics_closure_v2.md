# LP ML inverse Stage-I physics closure v2

## Tuple-gate root cause

The previous `all(planned_candidates_complete_per_bin` predicate was an `OVERSTRICT_BATCH_COMPLETION_GATE`. Tuple admission requires at least one complete physics candidate per bin; B2 has 5 complete candidates, so the physical tuple space is valid. The quarantined B2 y case remains excluded and unchanged.

## Physics integrity

35 complete prospective single-dimer 450-nm weighted-G0 Jones candidates are used. Counts are B0/B1/B2/B3/B4/B5 = 6/6/5/6/6/6. No model-filled or historical rows are included.

## Tuple enumeration

Raw combinations: 38,880 (`6 x 6 x 5 x 6 x 6 x 6`). Each tuple contains one candidate from every bin. A common phi offset is fitted by circular least squares against 60-degree steps. Physics-only tuple front and six role-specific champions are in `lp_ml_inverse_stage1_physics_tuple_front_v1.json`. Evidence label: `SINGLE_DIMER_PHYSICS_TUPLE_ONLY`; this is not K6 full-wave validation.

Balanced tuple: `LPML_INV_B0_GRA_590ad651d09c|LPML_INV_B1_GRA_464431e7fc00|LPML_INV_B2_DER_1c4c70e363d7|LPML_INV_B3_DER_e74126c376f7|LPML_INV_B4_DER_6603cd5211b7|LPML_INV_B5_GRA_14f392011ec0`

## Closure decision

`LP_ML_INVERSE_STAGE1_PHYSICS_TUPLE_READY_FOR_BROADBAND_PLANNING` is supported by the single-dimer physics tuple evidence. This only authorizes an offline planning proposal; no broadband solver is run or authorized here.

## Surrogate audit

See `lp_ml_inverse_stage1_surrogate_vs_physics_ranking_audit_v1.json` for per-bin rank correlations, risk stratification, and worst errors. Frozen C0/C1/C5/blend roles were not changed.

## Constraints

Solver calls in this task: 0. No B2 rerun, geometry replacement, model retraining, Round-4, broadband FDTD, K6, geometry054, or protected-report modification.
