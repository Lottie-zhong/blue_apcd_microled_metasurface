# Stage10 CP BW2A center spectral dipole run

- Scope: center-only no-DBR ordinary MicroLED dipole wavelength scan.
- New FDTD cases: 16 exactly. No +/-q, no 453 rerun, no 36-case run, no DBR/RCLED/MQW/mirrors/spacer.
- CP basis: +z transverse Ex/Ey, R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2). L_out dominance means DoCP_RminusL < 0.

## BW2_J1J2_D194_T90_PSI97_H525
- 5 deg L_fraction vs wavelength: 453nm=0.812652
- 10 deg L_fraction vs wavelength: 453nm=0.803952
- 20 deg L_fraction vs wavelength: 453nm=0.755995
- Worst 20 deg L_fraction: 453 nm, 0.755995, source=reused_existing_453_data.
- L_out dominant at all 20 deg scanned/reference wavelengths: yes.

## BW2_J1J2_D194_T90_PSI99_H525
- 5 deg L_fraction vs wavelength: 436nm=0.811048, 438nm=0.794270, 453nm=0.810506, 462nm=0.855905, 464nm=0.859746
- 10 deg L_fraction vs wavelength: 436nm=0.800035, 438nm=0.788887, 453nm=0.803786, 462nm=0.833514, 464nm=0.835817
- 20 deg L_fraction vs wavelength: 436nm=0.763480, 438nm=0.758408, 453nm=0.759234, 462nm=0.768860, 464nm=0.769236
- Worst 20 deg L_fraction: 438 nm, 0.758408, source=new_spectral_run.
- L_out dominant at all 20 deg scanned/reference wavelengths: yes.

## Interpretation
- 447-448 nm notch risk should be judged by PSI99 vs PSI97 20 deg L_fraction and total cone power in the combined CSV.
- PSI99 worst 20 deg row: 438 nm L_fraction=0.758408.
- PSI97 worst 20 deg row: 453 nm L_fraction=0.755995.
