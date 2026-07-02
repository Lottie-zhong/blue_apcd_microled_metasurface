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
- 5 deg L_fraction vs wavelength: 440nm=0.786625, 442nm=0.775709, 444nm=0.769339, 446nm=0.769170, 453nm=0.810506, 455nm=0.822960, 456nm=0.827769, 458nm=0.839407, 460nm=0.849406
- 10 deg L_fraction vs wavelength: 440nm=0.784135, 442nm=0.777943, 444nm=0.774026, 446nm=0.775693, 453nm=0.803786, 455nm=0.812074, 456nm=0.815487, 458nm=0.822987, 460nm=0.829469
- 20 deg L_fraction vs wavelength: 440nm=0.756610, 442nm=0.754661, 444nm=0.750926, 446nm=0.750981, 453nm=0.759234, 455nm=0.761842, 456nm=0.763261, 458nm=0.765744, 460nm=0.768006
- Worst 20 deg L_fraction: 444 nm, 0.750926, source=new_spectral_run.
- L_out dominant at all 20 deg scanned/reference wavelengths: yes.

## Interpretation
- 447-448 nm notch risk should be judged by PSI99 vs PSI97 20 deg L_fraction and total cone power in the combined CSV.
- PSI99 worst 20 deg row: 444 nm L_fraction=0.750926.
- PSI97 worst 20 deg row: 453 nm L_fraction=0.755995.
