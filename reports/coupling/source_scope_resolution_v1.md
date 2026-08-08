# APCD MDC-NP Coupling V1 scope lock and Stage-A readiness

Task: APCD_MDC_NP_COUPLING_V1_RETURN_TO_SCOPE_LOCK_AND_STAGE_A_READINESS
Formal status: APCD_MDC_NP_COUPLING_V1_EXPLORATORY_DIRECT_STAGE_A_READY_AWAITING_SOLVER_AUTHORIZATION
Joint normalized scope: EXPLORATORY_ONLY
Offline joint screening: NOT AUTHORIZED
Next route: DIRECT_STAGE_A_FULLWAVE_VALIDATION, pending explicit solver authorization

## Source locks

- MDC: `489b54e43bbf2c08ce030a945b9d4b70ee7550f2`, model `MDC_HF_M1_GEOMETRY_CONDITIONED_DIRECT_FINAL_5SEED_V1`, model SHA256 `8153fcb0846d5bb644c1eef0aa04db46f447e05d00addd704fa050d1a334351a`; scope artifact SHA256 `ecb7d1bc7668c849799d11bf6d62ae535743718786a2ad6459512788dbeb1b52` remains `CLOSED_QUANTITATIVE_HF_PROMOTION_REJECTED` and `EXPLORATORY_NP_COUPLING_ONLY`.
- NP: authoritative freeze `7a8588f6b5a1c96d88813f60406d418b488135fd` on `work/np-k6-mdc-v1`; embedded source snapshot `9128dfb85a268398d1fee56fcb7543982b075d84`; package locked commit `6493fae1f9acc636722ae1705c58b208c5cbdbe6`; package `NP_K6_P1D4_K6X_V1` with SHA256 `0b7b45e838a0d73b92d63f8a45459bc46206677a91821fa474dacf4bd9028eaa`.
- NP formal scope SHA256: `f034240634365f2c81a78feb0c8df4bc2ecc17db074734236d48c13deaffc7de`.
- NP coupling handoff SHA256: `4fcf8b5cbefb37ba8153ffadbf7bb4a141d6cbbb4fb296fe9fd2211e44226934`.
- NP source tree remains externally dirty; authoritative overlap is none and no source-worktree write was made by this task.

## Frozen Stage-A contract

Bottom to top: `APCD_GAN_NATIVE_M1 continuous GaN -> ZL-1 alternative MDC -> MDC final 79nm SiO2 -> no extra spacer -> RUN3A TiO2 K6 pillars -> Air`.

- `t_extra=0 nm` baseline; future candidates `0/79/158/237 nm` are not run.
- `+z`: GaN -> MDC -> K6 -> Air; `+x`: RUN3A phase-gradient; `m=+1`: physical `+x`.
- `z=0`: GaN/MDC first interface; reference plane: NP pillar bottom.
- First shot: `450 nm`, x-pol, normal incidence, `u_x=0`, `ky/k0=0`.
- Outputs: total R/T, all open transmitted/reflected orders, `eta_t(+1/0/-1)`, physical +1 angle, directionality, closure, and provenance-aware comparison to standalone RUN3A 450 nm x-pol.
- Comparison groups B0-B3 are preserved; B3 joint and B1 RUN3A reference are first priority, with no run in this freeze.

## Scope boundaries

The NP formal source response is quantitative only within its standalone scope: exact 445-455 nm points at 1 nm spacing, normal incidence, `u_x=0`, x-pol, and `SiO2 substrate -> Native-M1 TiO2 K6 -> Air`. y-pol, x/y averaging, oblique incidence, finite-SiO2 transfer, final MDC-NP transfer, Micro-LED dipole integration, quantitative joint-power prediction, surrogate/offline ranking, and interpolation/extrapolation remain excluded.

## Safety and verification

No solver, training, joint screening, sealed-test read, or Test40 read was performed. Contract validator: PASS. Coupling tests: 17 passed. No solver, training, joint screening, sealed-test, or Test40 action was performed.
