# R2-FMM2A literature/project rationale

FMM/RCWA is introduced as a mid-fidelity screening layer, not as a replacement for FDTD. TMM remains useful for fast thin-film stopband and cavity proxies, while FMM/RCWA can handle periodic layered structures with angle, wavelength, and polarization sweeps. FDTD remains required for finite mesa validation and final paper figures.

RC-micro-LED literature is used as a source-preconditioning benchmark only, not as an epitaxial stack to copy. The branch keeps ordinary InGaN/GaN MQW Micro-LED source modeling and does not require staggered MQW or NP-GaN/GaN DBR.

Benchmark values to preserve: DA = 39.04 deg; peak wavelength shifts from 456.16 nm to 449.18 nm as current density changes from 1.77 A/cm^2 to 54 A/cm^2; peak blue shift = 6.98 nm; spectral FWHM from 14.56 nm to 26.31 nm. Wan TiO2/SiO2 MDC remains the experimentally realistic multilayer/MDC reference.
