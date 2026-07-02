# R2-4D4 Focused Cavity-Phase Sweep

No FDTD, Lumerical, FSP, LDF, MAT/H5, or raw monitor data were created. This is a Python-only transfer-matrix reflection-phase diagnosis.

## Scope

- Representative candidates: 7
- Wavelength grid: 445-461 nm, 0.25 nm step
- Angle grid: 0-70 deg, 1 deg step
- Angle convention: internal GaN/cavity angle
- Polarizations: TE and TM
- Cavity spacer sweep: 160-430 nm, 2 nm step
- Layer convention: top and bottom stacks are evaluated from the GaN cavity side toward air; manifest layers are reused where available, otherwise regenerated from committed candidate parameters.

## Key Result

- Normal 453 nm phase reachability within 15 deg phase error: `True`
- Normal phase beating best 20-60 deg off-axis competitor: `True`
- Recommended route: `A`

## Best Phase-Guided Spacer

| candidate | pol | spacer nm | normal error deg | off-axis angle deg | off-axis error deg | margin deg |
|---|---:|---:|---:|---:|---:|---:|
| R2_4B_OPT_06176 | TE | 178.0 | 3.570 | 42.0 | 23.033 | 19.463 |

## Interpretation

The representative stacks can be phase-aligned near normal only if their 20-60 degree competitors are tracked. The next proxy must include explicit angle-dependent reflection phase and a phase-margin term, not just reflectance or a normal/off-axis intensity proxy.
