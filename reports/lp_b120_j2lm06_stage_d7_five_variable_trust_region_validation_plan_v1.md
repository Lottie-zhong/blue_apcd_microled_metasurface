# APCD LP J2LM06 Stage D7 five-variable trust-region validation plan freeze v1

- Status: `PASS`
- Mode: `OFFLINE_ONLY`
- D6 physics staging: unchanged
- Candidate universe: exactly 8 existing D6 proposals, no replacement/addition/deletion
- Future budget: exactly 8 geometries / 16 x-y subruns / 450 nm only
- Route: `CASE_A_FIVE_VARIABLE_PROJECTOR_TANGENT_FOUND`; this is planning only, not execution authorization

## Unit semantics

Internal arithmetic remains radian-based. Method A is -0.322631253353 rad/rad, -18.4854091562 degree/rad, -0.322631253353 degree/degree. Method B is -0.322984743698 rad/rad, -18.505662661 degree/rad, -0.322984743698 degree/degree. Classification: `CASE_UNIT_LABEL_ONLY`; `-18.48540916` is degree/rad, never degree/degree.

## Near-null audit

Step-normalized singular values: `[0.16311965326793518, 0.005634908288933865, 0.0012371401130262518, 6.017425314477188e-09, 3.5045778512637968e-09]`; formal rank `5`, exact null dimension `0`. The last two singular directions form `NUMERICAL_NEAR_NULL_SUBSPACE_DIMENSION_2`; this does not change rank=5. Ψ remains a new orthogonal control column (D6/D5 fraction 0.6687933841), even though the single best near-null vector has negligible Ψ component.

## Frozen candidates

| rank | candidate | class | Ψ step | phase margin (deg) | projector uncertainty-aware |
|---:|---|---|---:|---:|---|
| 1 | `D7_TRV_PROP_ac2e5d6ca24e9987` | `PRIMARY_PROJECTOR_TANGENT_VALIDATION` | 0.995013 | 4.58115 | True |
| 2 | `D7_TRV_PROP_00098aaf5db983b9` | `PRIMARY_PROJECTOR_TANGENT_VALIDATION` | 0 | 4.4876 | True |
| 3 | `D7_TRV_PROP_f5fdd16c144945e5` | `PRIMARY_PROJECTOR_TANGENT_VALIDATION` | 0.995013 | 4.37924 | True |
| 4 | `D7_TRV_PROP_27a9f273b1daf877` | `SECONDARY_NEAR_NULL_DIVERSITY` | 0.995013 | 4.09967 | True |
| 5 | `D7_TRV_PROP_89eb19e02e4961be` | `SECONDARY_NEAR_NULL_DIVERSITY` | 0 | 4.00832 | True |
| 6 | `D7_TRV_PROP_5faf242ac18ec85b` | `SECONDARY_NEAR_NULL_DIVERSITY` | 0.995013 | 3.90006 | True |
| 7 | `D7_TRV_PROP_693ec7d86d7c23e2` | `BOUNDARY_OR_MODEL_STRESS_TEST` | 0.995013 | 3.60171 | True |
| 8 | `D7_TRV_PROP_56364757e6cc98ca` | `BOUNDARY_OR_MODEL_STRESS_TEST` | 0 | 3.51156 | True |

All rows retain `MODEL_PREDICTION_NOT_PHYSICS_LABEL`; no candidate is a validated Jones, library node, robust bin, or spectral survivor.
