# R2-FMM2B minimal calculation plan

No FDTD in FMM2B. The first FMM/RCWA calculation should be tiny and periodic.

Candidate structure: start with MDC-only Wan baseline if the solver API can represent it cleanly; otherwise use a simplified RCLED-MDC periodic stack.

Coarse grids first:

- wavelength: 445-461 nm or 443-463 nm
- angle: -60 to +60 deg coarse samples
- polarization: x-polarized only at this branch stage
- source averaging: approximate MQW source-plane emission by weighted angular spectrum, not a single normal-incidence plane wave only

Outputs: spectral FWHM, angular FWHM/DA, eta10/eta20, normal/offaxis ratio, and peak-shift proxy.

Stop condition: if the solver cannot reproduce the qualitative H1H MDC-only trend, do not use FMM as a ranking layer.
