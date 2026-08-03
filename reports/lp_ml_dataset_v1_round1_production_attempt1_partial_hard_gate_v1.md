# LP_ML_DATASET_V1 Round-1 production partial hard gate

## Outcome

`LP_ML_ROUND1_DATA_OR_MODEL_FIX_REQUIRED`

## Accounting

- Planned: 240 geometries / 480 x-y subruns
- Entered solver: 92
- Accepted: 91
- Failed: 1
- Complete production geometries: 45
- Partial Round-1 (including retained smoke): 61 geometries / 549 spectral rows

## Failure

Subrun `LPML_R1_GLOBAL_SOBOL_054_y` entered the solver and then failed during formal weighted-G0 extraction with `ValueError: math domain error`. The runner stopped; no retry was issued. A second invocation would require budget expansion and is not authorized by this task.

## Model gate

Full Round-1 assembly, split, baseline training, residual MLP ensemble, uncertainty calibration, and Round-2 proposal are **not run** because the production hard gate was not met. No model-filled physics rows were created.

## Integrity

The old five-point attempt remains excluded. The 16-geometry smoke Attempt-2 remains retained. Protected report hashes were unchanged. No D9, active-learning solver, or additional geometry was generated.
