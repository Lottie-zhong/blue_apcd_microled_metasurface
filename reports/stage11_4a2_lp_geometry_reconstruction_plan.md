# Stage11-4A2 LP Fixed-Height Geometry Reconstruction Plan

Planning only: no FDTD, no Lumerical, no K=6, no finite patch, no dipole, no DBR/RCLED, no H500 rescue.

## Why H600 First

Stage11-4A1 showed H600 is the least-bad fixed-height scout: H600 B300 kept high selectivity (ratio about 9.148, Tx about 0.957) but failed phase, while H600 B240 failed ratio/matrix/phase. H650 was worse overall, so H650 is only an escape hatch.

## Why K=6 Remains Blocked

No H600/H650/H700 height-scaled template produced strict or loose bins over 451/452/453 nm. K=6 remains blocked until a fixed-height six-bin LP projection-phase library exists.

## Future A2 Run Groups

| group | height | bins | cases | purpose |
|---|---:|---|---:|---|
| S11_4A2_H600_B240_ROLE_RECOMBINE | 600 | 240 | 24 | repair B240 first because A1 H600 B240 failed ratio, matrix, and phase |
| S11_4A2_H600_B300_PHASE_PULL | 600 | 300 | 18 | use H600 B300 high selectivity as phase-only repair seed |
| S11_4A2_H600_COVERAGE_0_60_120_180 | 600 | 0;60;120;180 | 36 | only cover remaining bins after 240/300 show viable fixed-height behavior |
| S11_4A2_H650_ESCAPE_HATCH_240_300 | 650 | 240;300 | 18 | test H650 only if H600 lacks enough phase diversity after bottleneck repair attempts |

Total planned future extraction cases: 96 / 96.

## Early Stop Rules

- S11_4A2_H600_B240_ROLE_RECOMBINE: stop this group after any candidate is strict at 451/452/453, else keep best leakage and matrix near-miss
- S11_4A2_H600_B300_PHASE_PULL: stop after strict B300 or if phase error cannot be pulled below loose threshold in first half of variants
- S11_4A2_H600_COVERAGE_0_60_120_180: stop coverage once four bins have strict or loose candidates over 451/452/453
- S11_4A2_H650_ESCAPE_HATCH_240_300: stop immediately if H650 also fails loose gates for both 240 and 300

## Thresholds Reused From Stage11-4A1

- strict: ratio >= 6, Tx >= 0.45, matrix_error <= 0.50, phase_error <= 25 deg
- loose: ratio >= 3, Tx >= 0.10, matrix_error <= 1.00, phase_error <= 35 deg

## Recommendation

Use H600-only reconstruction first. Enable the H650 240/300 escape-hatch group only if H600 cannot produce loose 240/300 candidates. Do not start K=6 until fixed-height robust six-bin candidates exist.
