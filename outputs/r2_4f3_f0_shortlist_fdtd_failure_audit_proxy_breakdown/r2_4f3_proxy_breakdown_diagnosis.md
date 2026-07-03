# R2-4F3 Proxy Breakdown Diagnosis

The full F0 relaxed-target shortlist failed tri-point x-dipole FDTD guard.

Current proxy breakdown:
- The Python-only 1D stack/MDC proxy estimates angular transmission/reflection, but it does not model finite MQW dipole emission coupling.
- It lacks Green-function / LDOS / dipole-to-farfield angular coupling, so it can miss leaky or guided-like high-angle channels.
- Source-position stability cannot be inferred from the current stack-only proxy.
- Spectral narrowing proxy does not guarantee angular narrowing.
- High top mirror or MDC layers can trap or redirect energy into high-angle channels instead of producing near-normal extraction.

Measured route failures:
- F0_0781: stable off-normal around 26 deg plus broad 40-60 deg channel.
- F0_0204: severe far-offaxis 46-67 deg, broad FWHM, and source-position mismatch.

Conclusion: do not keep blindly sweeping 1D stack parameters for normal RCLED source selection.
