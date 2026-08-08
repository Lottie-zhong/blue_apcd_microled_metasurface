# Test40 selection scope

- No pre-training Test40 selection rule existed.
- The final M1 model was locked first at commit `489b54e43bbf2c08ce030a945b9d4b70ee7550f2`.
- Competing Chart draft selection rules existed afterward and were explicitly resolved before any test geometry set, prediction, FDTD label, or metric was materialized.
- `STRATIFIED_DETERMINISTIC_HASH_RANDOM_V1` is the sole authoritative current contract.
- The Gower-maximin draft was superseded with zero selected/test rows.
- Test40 is an outcome-blind post-model-lock external holdout within frozen DOE96 metadata support.
- It is not a preregistered pre-training test and is not an IID deployment-distribution sample.
