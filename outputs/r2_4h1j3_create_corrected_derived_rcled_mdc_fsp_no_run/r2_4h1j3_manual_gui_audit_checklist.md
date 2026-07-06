# R2-4H1J3 manual GUI audit checklist

Open the H1J3 derived FSP:

`D:\project\worktrees\blue_apcd_rcled_mdc\runtime\r2_4h1j3_rcled_mdc_corrected_derived_fsp_DO_NOT_COMMIT\MDC_blue_oujizi_RCLED_QWexact453_10pair_H1J3.fsp`

Confirm before any FDTD:

- bottom DBR exists as a group named `H1J3_bottom_DBR_QWexact453_10pair`
- group contains 20 layers
- material order is TiO2 then SiO2 repeated 10 times
- TiO2 layers are about 44.7 nm
- SiO2 layers are about 79.4 nm
- all bottom DBR layers use object-level mesh order override = true and mesh order = 1
- bottom DBR y range is about -2191 nm to -950 nm
- bottom DBR may overlap GaN rectangle, but mesh order makes DBR override GaN in overlap
- `source_1` default x=0 nm, y=-800 nm, z=0 nm
- `source_1` wavelength is 453 nm
- `source_1` remains x-dipole: theta=90 deg, phi=0 deg
- PlaneSource `source` is disabled
- FDTD y range is about -2800 to +1400 nm
- monitor y remains 1100 nm
- monitor is visually on the output side of the top MDC
- monitor is not inside TiO2/SiO2 layers
- monitor spacing from upper PML is reasonable
- far-field settings match:
  - projection direction = auto
  - material index = auto
  - far field filter = 1
  - 2D resolution = 1001
  - 3D resolution = 1001
  - Assume structure is periodic unchecked
  - override near field mesh unchecked
- no simulation was run
