# APCD LP D7 physics assimilation and D8 offline plan v1

## D7 actual absorption

- Formal accepted subruns: 16/16; complete Jones: 8/8; wavelength: 450 nm only.
- Actual Pareto front (all objectives jointly): D7_TRV_PROP_ac2e5d6ca24e9987, D7_TRV_PROP_00098aaf5db983b9, D7_TRV_PROP_f5fdd16c144945e5, D7_TRV_PROP_27a9f273b1daf877, D7_TRV_PROP_89eb19e02e4961be, D7_TRV_PROP_5faf242ac18ec85b, D7_TRV_PROP_693ec7d86d7c23e2, D7_TRV_PROP_56364757e6cc98ca.
- Lowest phase candidate: `D7_TRV_PROP_ac2e5d6ca24e9987`.
- Best trade-off and selected D8 anchor: `D7_TRV_PROP_693ec7d86d7c23e2`; phase 83.390903 deg; phase drop 3.210176 deg; Txx 0.976875; Tyy 0.101574; sigma2/sigma1 0.322457.

|rank|candidate|phase|drop|Txx|Tyy|sigma2/sigma1|cross power|phase residual|
|---:|---|---:|---:|---:|---:|---:|---:|---:|
|1|D7_TRV_PROP_ac2e5d6ca24e9987|82.030184|4.570895|0.978029|0.111002|0.336891|3.877e-06|-0.245738|
|2|D7_TRV_PROP_00098aaf5db983b9|82.138125|4.462954|0.980168|0.111222|0.336857|5.712e-17|-0.250092|
|3|D7_TRV_PROP_f5fdd16c144945e5|82.336608|4.264471|0.981390|0.111010|0.336326|2.991e-06|-0.350246|
|4|D7_TRV_PROP_27a9f273b1daf877|82.769670|3.831409|0.984392|0.106390|0.328750|9.166e-07|-0.460541|
|5|D7_TRV_PROP_89eb19e02e4961be|82.901643|3.699436|0.982367|0.106698|0.329565|3.810e-17|-0.490082|
|6|D7_TRV_PROP_5faf242ac18ec85b|83.013891|3.587187|0.979310|0.106377|0.329583|3.516e-07|-0.505148|
|7|D7_TRV_PROP_693ec7d86d7c23e2|83.390903|3.210176|0.976875|0.101574|0.322457|4.314e-07|-0.560249|
|8|D7_TRV_PROP_56364757e6cc98ca|83.384248|3.216831|0.974461|0.101920|0.323405|5.602e-17|-0.452320|

## Local-model adequacy

- Five-variable raw design rank: 4/5; centered variation rank: 3.
- J1-side and J2-length were not independently excited; a complete five-variable Jacobian is not identifiable.
- Normalized active W2/D/Psi condition number: 1.3507; phase residual MAE: 0.037630 deg; max absolute residual: 0.093638 deg.
- Model frozen as constrained active-subspace, residual-corrected local surrogate. It is not a full Jacobian and is valid only near D7 H500/450 nm geometry.

## D8 planned-only freeze

- Anchor is the actual multi-objective trade-off, not the lowest-phase candidate.
- D8 uses one bounded local branch with eight planned candidates; J1 remains fixed because its derivative is unidentifiable.
- Every D8 row is `MODEL_PREDICTION_NOT_PHYSICS_LABEL` with `physics_fields=ABSENT_NOT_SIMULATED`; no D8 staging exists.

|rank|candidate|role|J2 L|J2 W|D|Psi|pred drop|pred Txx|pred Tyy|pred sigma2/sigma1|
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
|1|D8_TRV_PLAN_d6f4911593b64495|PRIMARY_PHASE_STEP|106|100|200.5025|0.2858|3.2163|0.9780|0.1016|0.3224|
|2|D8_TRV_PLAN_3f9495af463cc07b|PRIMARY_PHASE_CONTROL|106|100|200.5000|0.0000|3.1385|0.9772|0.1019|0.3230|
|3|D8_TRV_PLAN_c011ef1be0120947|PRIMARY_PHASE_SIGN_DIAGNOSTIC|106|100|200.5025|-0.2858|2.9440|0.9777|0.1017|0.3225|
|4|D8_TRV_PLAN_2709798bc19d7b76|PARETO_LEAKAGE_BALANCE|106|99|200.5025|0.2858|3.8708|0.9798|0.1063|0.3294|
|5|D8_TRV_PLAN_2c6c4edac3638079|D_CONTROL|106|99|200.5000|0.0000|3.7931|0.9790|0.1066|0.3299|
|6|D8_TRV_PLAN_9cf1d115c3f947b9|L_CONTROL|107|100|200.5025|0.2858|3.2163|0.9780|0.1016|0.3224|
|7|D8_TRV_PLAN_28f33b5793175bc4|BOUNDARY_DIAGNOSTIC|106|98|200.5000|0.0000|4.4476|0.9808|0.1113|0.3369|
|8|D8_TRV_PLAN_b90dc117dcee89fd|LOCAL_NEUTRAL_CONTROL|107|99|200.5000|0.0000|3.7931|0.9790|0.1066|0.3299|

## Test regression evidence

- Initial traceback: `explicit_from_csv_json()` called `.get()` on a non-dict JSON row while scanning repository metadata.
- Minimal repair: skip non-dict JSON rows; frozen physics inputs were not changed.
- Target test after repair: 4 passed.
- D7 commit diff confirms the failing LP-ML1A2 script was not changed by the D7 physics commit.
- Full pytest reached 93 passed before the pre-existing D6 package test failed because it requires D6 staging to be absent.
- Excluding that D6 test reached 106 passed before the pre-existing Stage11-3B1 test failed on missing legacy six-bin geometry rows.

## No-solver and provenance audit

- This task made zero Lumerical/lumapi/FDTD calls and created no D8 physics staging.
- D7 physics staging, D7 execution package, canonical v1.21, D6 staging and protected reports are read-only inputs.
- D8 future budget is exactly 8 geometries / 16 x/y subruns / 450 nm only.

D8 plan: `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\plans\b120_j2lm06_bounded_local_validation_stage_d8_v1.json`
D8 execution contract: `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\plans\b120_j2lm06_stage_d8_execution_contract_v1.json`
D8 ML-label contract: `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\plans\b120_j2lm06_stage_d8_ml_label_contract_v1.json`
D8 validation contract: `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\plans\b120_j2lm06_stage_d8_validation_metric_contract_v1.json`
