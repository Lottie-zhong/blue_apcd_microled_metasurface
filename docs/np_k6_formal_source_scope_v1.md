# NP K6 formal source scope freeze v1

State: `NP_SOURCE_SCOPE_FROZEN_CONSERVATIVE`

This is a zero-solver provenance freeze. It does not authorize FDTD, RCWA, TMM, FEM, training, or joint MDC-NP screening.

## Source identity

- Branch: `work/np-k6-mdc-v1`
- Audited source commit: `9128dfb85a268398d1fee56fcb7543982b075d84`
- Locked package: `NP_K6_P1D4_K6X_V1`
- Package SHA256: `0b7b45e838a0d73b92d63f8a45459bc46206677a91821fa474dacf4bd9028eaa`
- Candidate: `NP_K6X_125_135_150_175_190_210`
- Canonical geometry hash: `aaaa5bfab2f727cca9c07754e4449cbadf70b91cdac90e6fbdd87f136a6e4b80`

## Frozen scope

- Exact wavelengths: 445--455 nm, 1 nm steps, 11 points; no interpolation/extrapolation.
- Incidence: normal only, `u_x=k_x/k_0=0`, `k_y/k_0=0`.
- Polarization: x-polarized standalone NP response only.
- Stack: standalone `NP_K6_INDEPENDENT_STACK_PILOT_V1` (SiO2 substrate / Native-M1 TiO2 K6 / Air).
- Response: total T/R, closure, all open transmitted/reflected orders, eta(+1)/eta(0)/eta(-1), directionality, order sign and `u_x`.
- Standalone NP values are quantitative only inside this frozen scope; MDC coupling remains `EXPLORATORY_ONLY`.

## Explicit exclusions

y-polarization, x/y equivalence or averaging, oblique kx (including +/-5 and +/-10 degrees), finite-SiO2 termination transfer, final MDC-NP integrated stack, Micro-LED dipole integration, extrapolation, and quantitative joint-power or surrogate/ranking claims are excluded.

## Evidence and safety

The scope artifact records full SHA256 values for every input. RUN3A independently confirms physical +1 to +x and `u_x>0`; no external MDC FSP or sealed test was read. All solver/training counters are zero.

## Coupling handoff

The coupling branch may read the 450 nm x-polarized normal-incidence direct geometry and order-sign records for interface registration/convention checks only. It may not use them for quantitative joint power, offline ranking, polarization averaging, oblique-angle input, or final-stack transfer.

Artifacts: `outputs/np_k6_formal_source_scope_v1/`.
