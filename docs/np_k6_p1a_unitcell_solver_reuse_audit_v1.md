# NP-K6-MDC P1-A Unitcell Solver Reuse Audit V1

## Executive conclusion

**FDTD_PRIMARY_NO_RCWA_AVAILABLE**

Periodic 3D FDTD is the P1-B primary backend. Static evidence confirms lumapi.FDTD, periodic x/y plus z-PML setup, plane-wave sources, monitors, Native-M1 registration, and order-resolved grating-vector scaffolding. No solver was started.

## Status and environment

- NP: work/np-k6-mdc-v1 at 5bd69e01151ae501ba41e6f3fe9536affff40da2; clean before this report.
- Native-M1 YAML, JSON, policy, helper, and sampled CSV exist.
- RCP Python and DELL Python exist.
- Lumerical v251 API static import passed: FDTD=True, MODE=True, RCWA class=False.
- No addrcwa implementation was found; license remains a later setup-only/smoke gate.

## Reusable code and backend audit

- src/metasurface/apcd_diffraction.py:71-177,417-462: tracked Jones/order schema and extract_fdtd_grating_orders; it reads gratingn/m/u, grating power, total transmission, and optional gratingvector complex vectors. Reuse the extraction contract, not its solved-result assumptions.
- src/metasurface/apcd_dimer.py:413-476: periodic 3D FDTD template with periodic x/y, z-PML, substrate, plane wave, and T/T_fields monitors. It contains lumapi.FDTD and run paths, so reuse only the model-pattern logic in a new isolated builder.
- apcd_dimer.py:479-503,588-661 supports polygon ellipse but no exact circular-cylinder token; P1-B needs a direct addcircle TiO2 cylinder.
- scripts/apcd_native_materials.py:18-162 provides policy/CSV loading and register_lumerical_sampled_material; use the latter only inside a future authorized FDTD setup.
- Requested legacy scripts 14/17/18/19 and archive apcd_metagrating.py do not exist in D:\project\blue_plane_wave_metasurface.

RCWA is not selected: no reusable addrcwa code, no lumapi.RCWA class, and no license test evidence. Periodic FDTD is suitable but its runtime license/API capability is still unverified. Cost is moderate-to-high for 3D H/D, 3 wavelengths, 2 LP inputs, and matched blanks.

## Frozen warm-start extraction convention

Geometry: SiO2 substrate -> TiO2 circular nanopillar -> Air; px=py=290 nm; propagation +z; x-LP and y-LP; 448/450/453 nm. The pillar is directly on SiO2 with no independent spacer. H=300..700 nm integer and D=100..230 nm integer; recommended coarse steps are H=10 nm and D=5 nm.

For each LP incidence and zero order save raw complex Cartesian amplitude, raw zero-order power, total R, total T, and energy residual 1-R-T. Use matched candidate and blank builders with identical px/py, substrate, source, wavelengths, and monitor/reference planes; the blank removes only the pillar. Define t_rel=t0_candidate/t0_blank and phase_rel=arg(t_rel). Save Re/Im/abs/phase of raw and relative amplitudes; never save phase alone.

Jones plan: x input gives txx and tyx; y input gives txy and tyy. Store T0_x, T0_y, cross-pol power, x/y phase mismatch, and x/y amplitude mismatch. For the single-cell library use direct solver-returned zero-order complex amplitude, not weighted_G0: the direct order field preserves normalization, phase, and cross-polarization. weighted_G0 is a historical LP convenience and is not physically interchangeable with order-resolved complex transmission.

The single-cylinder library is warm start only. Final K=6 evaluation must directly solve the 1740 x 290 nm supercell and retain every propagating diffraction order/Jones column; grating power alone cannot establish a Jones result.

## P1-B minimum implementation plan

- configs/np_k6_unitcell_library_v1.yaml: fixed contract and integer grid.
- scripts/build_np_k6_unitcell_setup_v1.py: new direct-circle periodic FDTD builder; candidate/blank selected by one flag.
- scripts/extract_np_k6_unitcell_complex_t_v1.py: new result-only extractor using the apcd_diffraction order/Jones pattern.
- tests/test_np_k6_unitcell_contract_v1.py: static contract/path/geometry checks.
- outputs/np_k6_unitcell_library_v1/: future authorized results only.

Keep setup builder and extractor separate. Native-M1 helper connects in the builder after an authorized FDTD object exists. Use the same builder for blank and candidate.

## Risks and exact next allowed task

Risks: FDTD license/API capability, gratingvector zero-order phase convention, blank reference-plane equivalence, and mesh/convergence remain unsolved. No RCWA license conclusion is justified without an authorized setup-only or smoke test.

Exact next allowed task: create the P1-B configuration/builder/extractor/test files and perform one D/H candidate plus matched blank setup-only gate. Do not run a solver until separately authorized.

No FDTD, RCWA, lumapi solver, FSP open/save, or other optical simulation was run in P1-A.
