# Native-M1 ZL-1 alternative tolerance comparison

Pure-film TMM only; no FDTD/Lumerical. Local basin uses ΔH/ΔL/Δcenter = −3…+3 nm integer offsets; MC seed 20260711.

## Nominal three core metrics

| candidate | peak | FWHM | T448 | T450 | T453 | 450 angle | angular FWHM | I0/Imax | strict | near |
|---|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| ZL1_N3_M3_L78_H46 | 450.300 | 3.366 | 0.3399 | 0.9605 | 0.2849 | -3 | 17.726 | 0.9696 | False | True |
| ZL1_N3_M3_L79_H44_C316 | 449.700 | 3.329 | 0.4814 | 0.9606 | 0.2092 | +0 | 14.921 | 1.0000 | True | True |

## Local basin pass rates

| candidate | radius | spectral | angular | combined | peak mean±std | FWHM mean±std | angle mean±std | angular FWHM mean±std |
|---|---|---:|---:|---:|---|---|---|---|
| ZL1_N3_M3_L78_H46 | local_basin_pm1nm | 0.444 | 0.556 | 0.333 | 450.315±2.057 | 3.372±0.063 | -4.481±4.590 | 13.324±4.587 |
| ZL1_N3_M3_L78_H46 | local_basin_pm2nm | 0.256 | 0.536 | 0.192 | 450.320±3.565 | 3.381±0.106 | -5.568±5.974 | 12.914±5.791 |
| ZL1_N3_M3_L78_H46 | local_basin_pm3nm | 0.175 | 0.466 | 0.134 | 450.331±5.043 | 3.393±0.150 | -10.114±14.460 | 12.302±6.446 |
| ZL1_N3_M3_L78_H46 | local_basin_full_pm3nm | 0.175 | 0.466 | 0.134 | 450.331±5.043 | 3.393±0.150 | -10.114±14.460 | 12.302±6.446 |
| ZL1_N3_M3_L79_H44_C316 | local_basin_pm1nm | 0.444 | 0.667 | 0.333 | 449.697±2.050 | 3.336±0.047 | -3.370±4.120 | 14.381±4.266 |
| ZL1_N3_M3_L79_H44_C316 | local_basin_pm2nm | 0.256 | 0.576 | 0.200 | 449.701±3.554 | 3.345±0.078 | -6.120±10.104 | 13.351±5.590 |
| ZL1_N3_M3_L79_H44_C316 | local_basin_pm3nm | 0.175 | 0.452 | 0.140 | 449.705±5.029 | 3.357±0.111 | -12.872±18.491 | 12.290±6.260 |
| ZL1_N3_M3_L79_H44_C316 | local_basin_full_pm3nm | 0.175 | 0.452 | 0.140 | 449.705±5.029 | 3.357±0.111 | -12.872±18.491 | 12.290±6.260 |

## Independent layer errors

- ZL1_N3_M3_L78_H46 independent_layer_1nm: spectral 0.697, angular 0.633, combined 0.523; peak 450.262±1.301 nm; FWHM 3.371±0.033 nm; angle -3.573±3.643°; angular FWHM 15.802±4.178°.
- ZL1_N3_M3_L78_H46 independent_layer_3nm: spectral 0.330, angular 0.550, combined 0.270; peak 450.473±2.977 nm; FWHM 3.415±0.074 nm; angle -5.150±5.515°; angular FWHM 13.483±5.612°.
- ZL1_N3_M3_L78_H46 independent_layer_5nm: spectral 0.230, angular 0.517, combined 0.183; peak 450.258±4.474 nm; FWHM 3.480±0.118 nm; angle -7.597±11.225°; angular FWHM 12.933±6.166°.
- ZL1_N3_M3_L79_H44_C316 independent_layer_1nm: spectral 0.687, angular 0.830, combined 0.590; peak 449.649±1.242 nm; FWHM 3.337±0.029 nm; angle -2.183±2.933°; angular FWHM 15.940±3.026°.
- ZL1_N3_M3_L79_H44_C316 independent_layer_3nm: spectral 0.337, angular 0.657, combined 0.287; peak 449.575±3.172 nm; FWHM 3.371±0.073 nm; angle -4.377±6.902°; angular FWHM 14.283±5.162°.
- ZL1_N3_M3_L79_H44_C316 independent_layer_5nm: spectral 0.210, angular 0.497, combined 0.160; peak 450.055±4.768 nm; FWHM 3.445±0.115 nm; angle -9.567±14.619°; angular FWHM 12.811±6.258°.

## Decision

- Alternative is compared using identical Native-M1 materials, 12-layer compiled geometry, gates, FWHM interpolation, and angle definitions.
- Maximum-transmission angle is plane-wave TMM selection, not dipole far-field.
- Boundary-clipped widths remain blank; no NaN/inf tokens are emitted.
