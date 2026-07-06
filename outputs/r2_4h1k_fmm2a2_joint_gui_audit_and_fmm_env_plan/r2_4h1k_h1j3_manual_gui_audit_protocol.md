# R2-4H1K H1J3 Manual GUI Audit Protocol

Target runtime FSP, not committed:

`D:\project\worktrees\blue_apcd_rcled_mdc\runtime\r2_4h1j3_rcled_mdc_corrected_derived_fsp_DO_NOT_COMMIT\MDC_blue_oujizi_RCLED_QWexact453_10pair_H1J3.fsp`

This protocol records what the user must confirm manually in the Lumerical GUI before any H1L FDTD validation is planned. H1K itself performs no simulation, does not open or modify the FSP, and does not use lumapi.

Required GUI confirmations:

1. Bottom DBR group `H1J3_bottom_DBR_QWexact453_10pair` exists, contains 20 layers, and is ordered from the cavity side downward as TiO2 then SiO2 repeated 10 times.
2. TiO2 layers are about 44.7 nm, SiO2 layers are about 79.4 nm, and the bottom DBR y range is about -2191 nm to -950 nm.
3. The bottom DBR may overlap the large GaN rectangle, but every bottom DBR layer must have object-level mesh order override enabled and mesh order = 1. No FDTD is allowed if this is not visually confirmed.
4. `source_1` is an electric x-dipole at x = 0 nm, y = -800 nm, wavelength = 453 nm, theta = 90 deg, phi = 0 deg, and enabled. `PlaneSource` must be disabled.
5. FDTD y min/y max are about -2800 nm / 1400 nm, and the bottom DBR, source, and top MDC are inside the region with reasonable PML margin.
6. The DFT monitor remains about y = 1100 nm and is visually on the output side of the top MDC, not inside TiO2/SiO2, and not too close to the upper PML.
7. Far-field settings match the checklist exactly.
8. No FDTD run is performed during this GUI audit and the derived runtime FSP is not accidentally overwritten.

Decision: pass only if every required item is confirmed. If monitor, source, far-field, or mesh-order status is ambiguous, H1K fails into the corresponding fix stage rather than FDTD.
