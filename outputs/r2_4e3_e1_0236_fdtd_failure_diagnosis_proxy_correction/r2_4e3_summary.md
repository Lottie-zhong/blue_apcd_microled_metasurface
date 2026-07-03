# R2-4E3 E1_0236 FDTD Failure Diagnosis And Proxy Correction

This stage is Python-only. It did not launch Lumerical, call lumapi, run FDTD, read runtime FSP files, or generate FSP/LDF/MAT/H5 files.

## One-Line Conclusion
E1_0236 is a severe Python-proxy false positive: tri-point FDTD shows a stable 49-52 deg far-offaxis channel, so E4 must add 45-55 deg and 40-60 deg lobe guards before any further shortlist can be trusted.

## Proxy vs FDTD
- Predicted normal/offaxis: 2.583981
- Measured tri-point normal/offaxis: 0.07644500084836449
- Predicted angular FWHM: 9.078843 deg
- Measured tri-point FWHM: 107.97806225750904 deg
- Predicted 30-40 penalty: 0.277206
- Measured 30-40 fraction: 0.383124061357909
- Measured peak zone: 45-55 deg far-offaxis

## E4 Recommendation
R2-4E4_Python_only_candidate_generator_v3_faroffaxis_guard
