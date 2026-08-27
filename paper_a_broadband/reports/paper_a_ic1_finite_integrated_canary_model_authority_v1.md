# Paper A IC1 finite integrated canary modeling authority v1

Status: PASS — `PAPER_A_IC1_INTEGRATED_CANARY_READY`

This is a setup-only architecture canary authority. It is not a fabrication or final device authority.

## Frozen canary model

- Finite square mesa: 3000 × 3000 nm, centered at (0, 0); this is a canary numerical/modeling extent, not a fabricated mesa claim.
- Exact BF04R_I03 unit cell, centered 5 × 5 replication, integer indices i,j ∈ [-2, +2], Px = Py = 432 nm.
- Array footprint: 2160 × 2160 nm with 420 nm nominal mesa margins on every side.
- Global datum: GaN-top/MDC-bottom interface at z = 0 nm.
- MDC: P1_ZL1_ALTERNATIVE_G3_A3, interfaces 0, 44, 123, 167, 246, 290, 606, 650, 729, 773, 852, 896, 975 nm.
- Direct contact: I03 bottom z = 975 nm, top z = 1500 nm; no 237 nm spacer.
- One source only: top primary well, x dipole at (0, 0, -171.5) nm. No y dipole and no 12-well solver batch.

## Numerical domain and measurements

- Finite x/y/z PML; periodic x/y is forbidden.
- Domain bounds: x,y = [-3000, 3000] nm and z = [-1600, 2600] nm. The selected 1500 nm lateral, 1218 nm bottom, and 1100 nm top clearances are canary numerical margins, not device dimensions.
- Six-face closed flux box: x,y = [-2000, 2000] nm and z = [-500, 1700] nm.
- Top near-to-far monitor at z = 1700 nm, 4000 × 4000 nm, complex Ex/Ey, 400–500 nm with 101 points, theta 0–90° and phi 0–359° at 1°.
- Independent V2 time probe at (0, 0, -100) nm records a field-energy proxy for late-time convergence/growth detection.

## QA and production boundary

Geometry-only readback passes: 12 registered MQW regions, 12 MDC layers, 25 full I03 cells, 50 distinct pillars, direct-contact gap 0 nm, no overlap, no PML collision, source inside the intended top-well/GaN host, and no periodic boundary.

The existing V2 divergence gate is retained unchanged and extended with finite emitted-power, finite closed-flux, finite far-field, and sourcepower-consistency checks. No solver-enterable FSP was created and no solver was run.

`W_emit(lambda)` remains `EMITTER_SPECTRUM_UNRESOLVED`. IC1 may report wavelength-resolved transfer and stability truth only; it may not report final emitter-weighted DoLP, device efficiency, final MDC benefit, or real-device useful LP.

Future single solver case, not run here: `IC1_MDC_I03_TOPWELL_X` with a one-entry FDTD budget.
