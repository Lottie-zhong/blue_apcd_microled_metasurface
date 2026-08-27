# Paper A finite-3D layout and z-registration authority V1

Status: **HARD_GATE**
Verdict: **PAPER_A_FINITE_3D_LAYOUT_ZREG_AUTHORITY_HARD_GATE**

## Resolved

The single global datum is the GaN-top/MDC-bottom interface at `z=0`, adopted from `MDC_REALISTIC_MQW_SOURCE_MODULE_V1` (`source y=0`, project `+z=source +y`). The 12 primary well centers are therefore `-171.5, -190.5, -209.5, -228.5, -247.5, -266.5, -285.5, -304.5, -323.5, -342.5, -361.5, -380.5 nm`; each well is 3 nm thick with 16 nm internal barriers and equal weight `1/12`. The MDC stack interfaces are exactly `0, 44, 123, 167, 246, 290, 606, 650, 729, 773, 852, 896, 975 nm`.

The historical 237 nm layer is native SiO2 between the MDC top and NP pillar bottom in the Coupling Stage-A chain. It is **not transferable** to current MDC + I03; this does not authorize direct MDC-I03 contact.

## Finite layout finding

No authoritative physical mesa/aperture was found. A small zero-solver candidate set is recorded using full centered I03 cells at 3x3, 5x5, and 7x7. The 3 µm mesa and 20 µm domain are historical diagnostic bounds only, not a selected Paper A layout. I03 has exact 432 nm pitch and no truncation; analytic minimum periodic gap is 68.842339771280 nm, while the minimum cell-edge clearance is only 6.342339771280 nm. No frozen fabrication/grid threshold was found to label that clearance safe or unsafe.

## Spectrum finding

The 450 nm / 28 nm-FWHM Gaussian is a historical MDC benchmark: `sigma=FWHM/(2*sqrt(2*ln(2)))`, `g(lambda)=exp(-0.5*((lambda-450)/sigma)^2)`, power-domain relative weighting on the sampled grid. Existing provenance explicitly calls it a common benchmark, not measured MicroLED emission. MDC output is conditioned output and cannot substitute for `W_emit`; the physical emitter envelope remains unresolved.

## Readiness

No integrated 3D digital twin was constructed because finite mesa, I03 absolute vertical placement, and `W_emit` are unresolved. Future IC1 is defined only as planning: MDC + I03 + the top primary well at `z=-171.5 nm` with an x-oriented dipole. It is not authorized.

## Zero-solver

`FDTD=0`, `RCWA=0`, `ML=0`, `solver_run_called=false`, `solver_entered=0`, no setup-only FSP, no auto-admission, and no modifications to frozen source worktrees.
