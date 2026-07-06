# R2-4H1I x-only source validation protocol

Current stage uses x-polarized 2D validation only. Do not run y-dipole or broadband in H1I.

Future FDTD validation must use at least three x-axis positions: -2500 nm, 0 nm, and +2500 nm. The final decision must use incoherent intensity/power averaging over these positions. Center-only validation is diagnostic only and must never be used as pass/fail evidence.

PlaneSource `source` must be disabled. DipoleSource `source_1` must be enabled and configured as electric x-dipole with theta=90 deg and phi=0 deg at 450 nm.
