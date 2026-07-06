# R2-4H1J manual GUI audit checklist

Open the derived FSP manually:

`D:\project\worktrees\blue_apcd_rcled_mdc\runtime\r2_4h1j_rcled_mdc_derived_fsp_DO_NOT_COMMIT\MDC_blue_oujizi_RCLED_QWexact10pair_H1J.fsp`

Confirm before any FDTD:

- bottom DBR exists and has 20 layers
- layer prefix is `H1J_bottom_DBR_QWexact10pair`
- materials alternate `tio22` / `sio222`
- TiO2 layers are 44.37 nm
- SiO2 layers are 78.89 nm
- bottom DBR y range is about -2182.55 nm to -950 nm
- `source_1` remains at about y=-800 nm and is not inside DBR
- there is no overlap between bottom DBR and existing MDC
- FDTD y min/y max are expanded to about -2800 nm to +1400 nm
- PML margin below bottom DBR is reasonable
- PlaneSource `source` is disabled or clearly marked not to use for dipole validation
- DipoleSource `source_1` remains enabled for x-dipole validation
- monitor remains in a reasonable top-output/far-field position
- no simulation was run
