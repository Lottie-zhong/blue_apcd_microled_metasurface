# Test40 selection conflict resolution and manifest freeze

Status: `MDC_HF_SURROGATE_V2_TEST40_POST_MODEL_LOCK_OUTCOME_BLIND_MANIFEST_FROZEN_READY_TO_RESUME_EXTERNAL_EVALUATION`

The sole authoritative contract is `MDC_HF_SURROGATE_V2_TEST40_POST_MODEL_LOCK_SELECTION_V1` using `STRATIFIED_DETERMINISTIC_HASH_RANDOM_V1` with seed `20260808`, applied post-model-lock and before labels or predictions. The prior Gower-maximin draft is explicitly deprecated and superseded before test-set materialization with zero selected geometries and zero generated cases.

The canonical 8,675-row geometry master yielded 2,688 frozen-support candidates and 2,674 eligible candidates after the hash-only formal-FDTD exclusion union. Fixed quotas selected 40 unique geometries (Explicit 10+4, ZL1 9+4, ZL2 9+4), materialized as 240 deterministic case UIDs.

Two independent fresh Python processes reproduced support membership, forbidden set, boundary classes, selection order, human IDs, all case UIDs, geometry-manifest SHA, and case-matrix SHA exactly. HF15 formal-label reads, diagnostics reads, Test40 labels/predictions, sealed-test reads, solver calls, FDTD/TMM/RCWA calls, and model fitting were all zero. External evaluation was not started; return to Chart for the next authorized step.
