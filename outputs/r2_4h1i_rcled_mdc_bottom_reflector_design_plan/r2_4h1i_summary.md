# R2-4H1I summary

Decision: `direction_b_rcled_mdc_bottom_reflector_plan_frozen`.

Direction B is frozen as the next planning route: build an RCLED-MDC source module by adding a bottom reflector / bottom DBR below the existing Wan MDC baseline, while using the existing MDC as the top filtering/output mirror.

Primary bottom reflector candidate: `DBR_QW_exact_450_10pair`.

Secondary bottom reflector candidate: `DBR_Huang_like_10pair`.

Quarter-wave exact 450 nm layer thicknesses:

| material | n at 450 nm | thickness |
|---|---:|---:|
| TiO2/tio22 | 2.5356 | 44.368 nm |
| SiO2/sio222 | 1.4261 | 78.886 nm |

H1I does not create a derived FSP and does not allow immediate FDTD. It preserves x-only three-position validation and defers y-dipole and broadband validation.
