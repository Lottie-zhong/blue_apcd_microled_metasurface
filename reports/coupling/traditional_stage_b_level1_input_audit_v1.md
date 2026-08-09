# Traditional Stage-B Level-1 Input Audit

Status: TRADITIONAL_STAGE_B_LEVEL1_HANDOFF_BLOCKED_LEVEL1_POLARIZATION_MAPPING_INPUT_INSUFFICIENT

## Frozen Stage-A baseline

- Closure HEAD: 25e78936afca7387f71bda244545efed64cbe702
- MDC: P1_ZL1_ALTERNATIVE_G3_A3, 975 nm, top SiO2 79 nm
- Extra spacer: 237 nm; continuous SiO2 separation: 316 nm
- NP: NP_K6X_125_135_150_175_190_210
- Integrated matrix: 445-455 nm exact 1 nm, 5 angles, P/S branches, 110 rows
- Matrix SHA256: d400c51cfa557aeffdefb09567dbe20705c50d915bc9a5ddd570281535265bf6

## MDC Level-1 provider

Decision: REQUIRES_DIRECT_SOLVER.

The only ZL1 dipole package found is legacy diagnostic data with source y=-400 nm, five x-offset positions (-1000, -500, 0, 500, 1000 nm), x/z dipoles, and 448-452 nm at 0.1 nm spacing. It is not the formal top/centroid/bottom z contract. A separate native-M1 ZL1 result is x-dipole only and uses a 978 nm stack. DOE96 contains 301x2000 joint tensors, but for 96 new DOE geometries and no frozen ZL1 geometry hash match.

Required formal MDC input: six real 2D FDTD cases at z=-171.5/-276.0/-380.5 nm, x/z dipoles, raw upward power, exact source/grid identity, and normalized W/P semantics.

## NP Level-1 provider

Decision: PARTIAL_EXISTING_ASSET.

Existing formal scope is standalone SiO2 substrate -> Native-M1 TiO2 K6 -> Air, exact 445-455 nm, u_x=0, x-pol only. It does not support y/S, oblique u_x, finite-SiO2 termination transfer, or the final MDC-NP stack. The Stage-A integrated 110-row matrix is excluded as an eta provider.

## Interface / mapping

- MDC conceptual output plane: z=975 nm, upward into Native-M1 SiO2.
- NP input plane: pillar bottom z=1212 nm, incident/reference medium Native-M1 SiO2.
- Primary variable: conserved u_x=kx/k0; theta_air is derived only.
- Raw-first aggregation: 0.5 x + 0.5 z per position, then top/centroid/bottom geometry average, then normalization.
- Polarization mapping is a hard gate: MDC x/z source channels are not NP P/S branches. No x->P or z->S mapping is permitted.
- Quadrature weight semantics remain unresolved until formal MDC profile metadata is supplied.

## Solver budget planning

No solver was run. Conditional minimum planning is 6 MDC formal FDTD cases plus 9 missing NP (u_x, polarization) broadband response states for the full Stage-A 5-angle/P-S target. These are planning numbers only and are not authorization.

## Safety

FDTD/TMM/RCWA/FEM/training/ML/integrated Level-1 numerical entries this turn: all zero. Source worktrees received no writes; their pre-existing dirty/untracked states were preserved.
