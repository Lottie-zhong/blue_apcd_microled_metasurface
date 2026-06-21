# Stage10 CP Route B4-4 finite-patch tolerance validation

## Scope and convention

- Route B4-4 only; three tolerance variants: TOL_SIZE_ALL_P2, TOL_J1_YP2, TOL_J1_ROT_M1.
- Nominal B4-2 finite-patch results were reused and not rerun.
- Exactly 18 new finite-patch cases: three variants x center/+q/-q x x/y dipoles.
- The actual B4-2 +z convention is R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2). Ex/Ez would be inconsistent with +z transverse fields and was not used.
- x/y dipoles are combined incoherently by power addition only. Cone metrics below use +/-20 deg, grid101.
- No new pass/fail threshold is introduced. CP labels compare sign and magnitude with nominal. Power labels use the existing Stage10 <0.25x catastrophic-power guard.

## Nominal comparison

| variant | position | DoCP | L fraction | power ratio | CP interpretation | power interpretation | plane-wave warning reproduced |
|---|---|---:|---:|---:|---|---|---|
| TOL_SIZE_ALL_P2 | center | -0.502816 | 0.751408 | 1.01771 | preserved_or_improved | preserved_or_increased | no |
| TOL_SIZE_ALL_P2 | x_plus_q | -0.379045 | 0.689522 | 1.01076 | degraded_but_same_handedness | preserved_or_increased | no |
| TOL_SIZE_ALL_P2 | x_minus_q | -0.431778 | 0.715889 | 0.958662 | degraded_but_same_handedness | reduced | no |
| TOL_J1_YP2 | center | -0.503621 | 0.751811 | 0.992736 | preserved_or_improved | reduced | no |
| TOL_J1_YP2 | x_plus_q | -0.392876 | 0.696438 | 0.993511 | preserved_or_improved | reduced | no |
| TOL_J1_YP2 | x_minus_q | -0.431813 | 0.715907 | 0.991231 | degraded_but_same_handedness | reduced | no |
| TOL_J1_ROT_M1 | center | -0.504799 | 0.752399 | 1.00194 | preserved_or_improved | preserved_or_increased | no |
| TOL_J1_ROT_M1 | x_plus_q | -0.399076 | 0.699538 | 0.994788 | preserved_or_improved | reduced | no |
| TOL_J1_ROT_M1 | x_minus_q | -0.432844 | 0.716422 | 0.997979 | degraded_but_same_handedness | reduced | no |

## Interpretation

- DoCP_RminusL < 0 means L-output dominant; DoCP_RminusL > 0 means R-output dominant.
- TOL_SIZE_ALL_P2 is specifically checked for the B4-3 warning: CP handedness/purity may remain useful while usable cone power collapses.
- This report does not modify or rerun the frozen nominal geometry.
- Completed/reused tolerance cases: 18/18.
