# Stage10 CP BW2A No-DBR Dipole Validation Summary

## Executive Conclusion

- PSI99 (`BW2_J1J2_D194_T90_PSI99_H525`) is the current CP BW2A main candidate.
- In no-DBR ordinary MicroLED dipole validation, PSI99 shows stable `L_out` dominant CP selection.
- Center spectral robustness is validated across the tested 447-454 nm points.
- Source-position robustness is validated at 453 nm for center/+q/-q.
- Edge-wavelength off-center robustness is validated at 447/454 nm for +/-q.
- Main remaining issue is off-center cone-power reduction, especially +q, not CP handedness flipping.

## Candidate And Setup

- candidate_id: `BW2_J1J2_D194_T90_PSI99_H525`
- baseline candidate: `BW2_J1J2_D194_T90_PSI97_H525`
- no DBR, no RCLED, no MQW/cavity/mirror/spacer changes
- ordinary MicroLED finite patch, +z far-field monitor
- extraction: complex `farfieldvector3d` Ex/Ey, not intensity-only farfield3d
- CP basis: `R = (Ex - i Ey)/sqrt(2)`, `L = (Ex + i Ey)/sqrt(2)`
- x/y dipoles combined by incoherent power summation
- q_nm = `107.9769465`

## Evidence Chain

|commit|title|scope|case_count|conclusion|
|---|---|---|---|---|
|62a2397|Stage10 CP BW2A center dipole smoke validation|453 nm center, PSI99 vs PSI97, x/y dipoles|4 FDTD|PSI99 remains L_out dominant and is not worse than PSI97 at center.|
|905c716|Stage10 CP BW2A center spectral dipole scan|447/448/450/453/454 nm center, PSI99 vs PSI97|16 FDTD plus reused 453 nm rows|Center spectral robustness validated over tested 447-454 nm points.|
|8e9b652|Stage10 CP BW2A PSI99 position dipole scan|453 nm center/+q/-q, PSI99 only|6 FDTD|Source-position robustness validated at 453 nm; +q has lowest power/L_fraction.|
|9f9ae1d|Stage10 CP BW2A PSI99 edge-position dipole check|447/454 nm, +/-q, PSI99 only|8 FDTD|Edge-wavelength off-center robustness validated; no CP flip.|

## Key Metrics: 20 deg x/y Incoherent

### 453 nm Center Smoke: PSI99 vs PSI97

|candidate|L_fraction|DoCP|total_power|
|---|---|---|---|
|BW2_J1J2_D194_T90_PSI99_H525|0.759234|-0.518468|1.106e-10|
|BW2_J1J2_D194_T90_PSI97_H525|0.755995|-0.511990|1.100e-10|

### Center Spectral Scan

`BW2_J1J2_D194_T90_PSI99_H525`

|wavelength_nm|L_fraction|DoCP|total_power|
|---|---|---|---|
|447|0.751464|-0.502928|1.086e-10|
|448|0.752449|-0.504899|1.120e-10|
|450|0.754561|-0.509123|1.116e-10|
|453|0.759234|-0.518468|1.106e-10|
|454|0.760695|-0.521391|1.103e-10|

`BW2_J1J2_D194_T90_PSI97_H525`

|wavelength_nm|L_fraction|DoCP|total_power|
|---|---|---|---|
|447|0.747753|-0.495506|1.090e-10|
|448|0.748717|-0.497434|1.119e-10|
|450|0.750703|-0.501405|1.111e-10|
|453|0.755995|-0.511990|1.100e-10|
|454|0.757674|-0.515348|1.096e-10|

### PSI99 453 nm Source-Position Scan

|position|L_fraction|DoCP|total_power|
|---|---|---|---|
|center|0.759234|-0.518468|1.106e-10|
|x_plus_q|0.700648|-0.401296|5.708e-11|
|x_minus_q|0.729470|-0.458940|6.271e-11|

### PSI99 Edge-Wavelength Off-Center Check

|wavelength_nm|position|L_fraction|DoCP|total_power|
|---|---|---|---|---|
|447|x_plus_q|0.703135|-0.406270|5.578e-11|
|447|x_minus_q|0.723357|-0.446714|5.707e-11|
|454|x_plus_q|0.701878|-0.403757|5.721e-11|
|454|x_minus_q|0.731163|-0.462327|6.324e-11|

## Worst Cases

- Center spectral worst PSI99: 447 nm, L_fraction 0.751464.
- Position scan worst PSI99: x_plus_q at 453 nm, L_fraction 0.700648.
- Edge/off-center worst PSI99: 454 nm x_plus_q, L_fraction 0.701878.
- Overall observed worst: psi99_453_position, 453 nm x_plus_q, L_fraction 0.700648.
- Overall observed no-DBR PSI99 off-center worst is about 0.700-0.704 L_fraction at +q.

## Interpretation

- PSI99 does not show CP handedness flipping in the tested center, spectral, source-position, and edge/off-center cases.
- The 447-448 nm blue-side plane-wave notch collapse is not observed in the center dipole scan.
- Edge wavelengths at off-center positions remain `L_out` dominant.
- +q total cone power is about 0.52x center at 453 nm, so source-position power uniformity remains the main issue.
- This supports moving the power/angle stabilization problem to DBR/RCLED source-module integration rather than continuing to tune APCD for CP selection only.

## Recommended Next Steps

1. Do not expand the no-DBR CP sweep broadly unless a complete table is specifically needed.
2. Treat PSI99 as the current no-DBR CP dipole-safe candidate.
3. Next scientific route: integrate with the DBR/RCLED source module to improve total cone power and position uniformity.
4. Optional diagnostic only if needed: complete 448/450 nm +/-q matrix; it is not required for current risk closure.

## Chinese Conclusion

PSI99 no-DBR dipole CP selection is stable across the tested spectral and x-line position cases. The remaining bottleneck is off-center cone-power reduction, especially +q; this should be addressed by DBR/RCLED source-module integration rather than more CP-only APCD tuning.
