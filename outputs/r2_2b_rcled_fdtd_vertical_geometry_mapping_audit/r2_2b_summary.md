# R2-2B Vertical Geometry Mapping Audit

This is a prepare-only audit for mapping R2 TMM/STACK candidates into later 2D FDTD dipole validation geometry.

No FDTD was run. Lumerical was not launched. No `.fsp`, `.ldf`, or raw monitor files were created.

## Mapping decision

Selected for first smoke validation: **Option A, literal spacer mapping**.

`cavity_span_nm` should be used directly as the physical GaN cavity / effective spacer thickness for the first smoke model. This is not claimed to be the final calibrated physical thickness; it is the most reproducible first test before adding optical-phase correction.

## First smoke candidate

Selected: **R2_1_00223**.

Reason: true two-mirror cavity, top=6, bottom=6, cavity=280 nm, no termination, low extraction risk, and slightly narrower high-resolution TMM spectral FWHM than R2_1_00227.

## Geometry risks still open

- TMM `cavity_span_nm` may include effective DBR penetration and reflection phase.
- MQW source must be placed at the cavity center and audited away from DBR interfaces.
- Monitor/PML placement must be checked in the later FDTD setup before solving.
- R2_1_04067 is useful as a different-family check but has medium top-mirror extraction risk.
