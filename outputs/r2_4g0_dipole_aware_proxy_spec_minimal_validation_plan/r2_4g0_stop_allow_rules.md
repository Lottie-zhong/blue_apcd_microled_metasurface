# R2-4G0 Stop / Allow Rules

Stop:
- D5_BASE_13461
- E1_0236
- F0_0781
- F0_0204

Do not:
- run FDTD immediately after G0;
- run FDTD from the current 1D proxy shortlist;
- use center-only verdicts;
- run y/z/broadband before tri-point x-dipole pass;
- claim source-position stability from Python-only proxy.

Allow:
- G1 Python-only negative dataset and feature table;
- reviewed G2 minimal calibration only after G1;
- retain relaxed target: spectral FWHM <=10 nm and angular FWHM <=20 deg;
- accept 25-30 deg only as literature-aligned intermediate baseline, not final pass.
