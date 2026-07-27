# APCD LP J2LM06 Stage D6 attested execution and five-variable finalization v2

- Status: `PASS`
- Route: `CASE_A_FIVE_VARIABLE_PROJECTOR_TANGENT_FOUND`
- Formal execution: `4 geometries / 8 x-y subruns / 450 nm`
- Accepted checkpoints: `8/8`; reconstructed Jones: `4/4`
- Tangential denominator: `0.010024978696435921 rad`
- Tangential common radial bias: `0.0025062499215948719 nm`
- Tangential raw/corrected residual: `0.00096686038858697493` / `0.00099428753331795507`
- Raw leakage singular values: `[0.24687251528648604, 0.16308053662746025, 0.005634867311863623, 6.0174253152402975e-09, 3.50457785074998e-09]`
- Step-normalized leakage singular values: `[0.16311965326793518, 0.005634908288933865, 0.0012371401130262518, 6.017425314477188e-09, 3.5045778512637968e-09]`
- Trust-region proposals: `8`; all are `MODEL_PREDICTION_NOT_PHYSICS_LABEL`
- Trust-region FDTD validation: `AUTHORIZED_PLANNING_ONLY`
- Applicable runtime regression tests: `5 passed`; the frozen pre-execution staging-absence assertion is not applicable after authorized D6 staging creation
- Spectrum/training/canonical v1.22 merge: `NOT_AUTHORIZED`
