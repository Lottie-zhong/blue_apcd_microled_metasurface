# Stage10 CP BW2A center spectral dipole run

- Scope: center-only no-DBR ordinary MicroLED dipole wavelength scan.
- New FDTD cases: 16 exactly. No +/-q, no 453 rerun, no 36-case run, no DBR/RCLED/MQW/mirrors/spacer.
- CP basis: +z transverse Ex/Ey, R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2). L_out dominance means DoCP_RminusL < 0.

## BW2_J1J2_D194_T90_PSI97_H525
- 5 deg L_fraction vs wavelength: 447nm=0.772746, 448nm=0.777512, 450nm=0.789043, 453nm=0.812652, 454nm=0.821029
- 10 deg L_fraction vs wavelength: 447nm=0.776753, 448nm=0.780363, 450nm=0.788296, 453nm=0.803952, 454nm=0.809517
- 20 deg L_fraction vs wavelength: 447nm=0.747753, 448nm=0.748717, 450nm=0.750703, 453nm=0.755995, 454nm=0.757674
- Worst 20 deg L_fraction: 447 nm, 0.747753, source=new_spectral_run.
- L_out dominant at all 20 deg scanned/reference wavelengths: yes.

## BW2_J1J2_D194_T90_PSI99_H525
- 5 deg L_fraction vs wavelength: 447nm=0.771596, 448nm=0.774502, 450nm=0.787157, 453nm=0.810506, 454nm=0.816606
- 10 deg L_fraction vs wavelength: 447nm=0.777979, 448nm=0.780548, 450nm=0.788814, 453nm=0.803786, 454nm=0.807861
- 20 deg L_fraction vs wavelength: 447nm=0.751464, 448nm=0.752449, 450nm=0.754561, 453nm=0.759234, 454nm=0.760695
- Worst 20 deg L_fraction: 447 nm, 0.751464, source=new_spectral_run.
- L_out dominant at all 20 deg scanned/reference wavelengths: yes.

## Interpretation
- 447-448 nm notch risk should be judged by PSI99 vs PSI97 20 deg L_fraction and total cone power in the combined CSV.
- PSI99 worst 20 deg row: 447 nm L_fraction=0.751464.
- PSI97 worst 20 deg row: 447 nm L_fraction=0.747753.
