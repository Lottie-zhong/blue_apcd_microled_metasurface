# R2-4F3 F0 Shortlist FDTD Failure Audit

Result: the full F0 shortlist failed tri-point FDTD guard.

Key evidence:
- F0_0781 proxy predicted peak_abs 2.45 deg and angular FWHM 16.13 deg, but FDTD measured peak_abs 25.895 deg and FWHM 54.998 deg.
- F0_0204 proxy predicted peak_abs 1.85 deg and angular FWHM 18.41 deg, but FDTD measured peak_abs 65.499 deg and FWHM 138.446 deg.
- Both candidates have normal/offaxis < 1 in FDTD.

One-line conclusion: relaxed stack/MDC proxy still misses dipole-coupled off-axis channels, so R2-4G should upgrade the proxy physics before any new FDTD.

Missing optional inputs recorded: none.
