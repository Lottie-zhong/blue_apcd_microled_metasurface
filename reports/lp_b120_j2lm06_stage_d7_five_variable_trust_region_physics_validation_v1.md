# LP B120 J2LM06 Stage D7 five-variable trust-region physics validation v1

- Status: **PASS**; solver invocations 16/16; accepted 16/16; complete Jones 8/8.
- Frozen plan SHA256: `440a443c1604219e52f5671cb08945b835ffeb62dad9a36b460a3fa8e36d0124`; schema `LP_ML_SCHEMA_V1.23`; wavelength 450 nm only.
- CASE_A five-variable projector tangent: **SUPPORTED by this validation set** (all actual phase drops positive; projector residual is reported per candidate).
- Best combined phase/projector candidate: `D7_TRV_PROP_693ec7d86d7c23e2`; actual phase `83.390903°`; drop `3.210176°`; sigma2/sigma1 `0.322457`; Txx `0.976875`; Tyy `0.101574`.

## Candidate results

|rank|candidate|phase drop deg|prediction error deg|Txx|Tyy|sigma2/sigma1|cross power|
|---:|---|---:|---:|---:|---:|---:|---:|
|1|D7_TRV_PROP_ac2e5d6ca24e9987|4.570895|-0.245738|0.978029|0.111002|0.336891|3.877e-06|
|2|D7_TRV_PROP_00098aaf5db983b9|4.462954|-0.250092|0.980168|0.111222|0.336857|5.712e-17|
|3|D7_TRV_PROP_f5fdd16c144945e5|4.264471|-0.350246|0.981390|0.111010|0.336326|2.991e-06|
|4|D7_TRV_PROP_27a9f273b1daf877|3.831409|-0.460541|0.984392|0.106390|0.328750|9.166e-07|
|5|D7_TRV_PROP_89eb19e02e4961be|3.699436|-0.490082|0.982367|0.106698|0.329565|3.810e-17|
|6|D7_TRV_PROP_5faf242ac18ec85b|3.587187|-0.505148|0.979310|0.106377|0.329583|3.516e-07|
|7|D7_TRV_PROP_693ec7d86d7c23e2|3.210176|-0.560249|0.976875|0.101574|0.322457|4.314e-07|
|8|D7_TRV_PROP_56364757e6cc98ca|3.216831|-0.452320|0.974461|0.101920|0.323405|5.602e-17|

## Constraint audit

- Exactly 8 frozen geometries and 16 x/y subruns; no retry, replacement, extra wavelength, spectrum, tolerance, anchor/D5/D6/reference rerun, training, canonical merge, or D8.
- Formal observable: transmission-side coordinate-weighted periodic G0, endpoint handling, sqrt(T)/norm normalization, field monitor z=1000 nm.
- Prediction fields remain `MODEL_PREDICTION_NOT_PHYSICS_LABEL`; physics fields are accepted FDTD weighted-G0 measurements.
- Existing D6 staging, canonical v1.21 and protected reports were read-only inputs.

Execution package: `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\execution_packages\b120_j2lm06_stage_d7_trust_region_validation_execution_package_v1`
Physics staging: `D:\project\worktrees\blue_apcd_lp_stage11_4\outputs\lp_ml_dataset_v1\staging\b120_j2lm06_stage_d7_five_variable_trust_region_validation_v1`
