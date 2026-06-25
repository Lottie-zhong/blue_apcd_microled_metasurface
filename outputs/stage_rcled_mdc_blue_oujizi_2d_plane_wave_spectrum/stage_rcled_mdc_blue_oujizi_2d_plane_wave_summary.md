# MDC_blue_oujizi 2D Plane-Wave Spectrum

- Source 3D FSP: `D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_dbr_only\rcled_mdc_blue_oujizi_dbr_only_no_metasurface.fsp`
- 2D FSP: `D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_2d_plane_wave_spectrum\rcled_mdc_blue_oujizi_2d_plane_wave_spectrum.fsp`
- Scope: 2D x-z plane-wave only; no dipoles, no APCD/B4INT/metasurface, no finite patch.
- Source: normal incidence from GaN/source side toward physical +z DBR/output side; Lumerical 2D uses simulation +y as physical +z.
- Wavelength range: 438-468 nm; requested sampling step 0.5 nm.
- Boundaries: x periodic, simulation y PML (physical z PML).
- Monitors: `T_up_monitor` above DBR, `R_down_monitor` below/source side.
- Mesh accuracy: 3.

## Layer stack

GaN source-side region, then `[sio222 100 nm -> tio22 52 nm] x 8 -> terminal sio222 100 nm`, then air output side.

## Spectral summary

| mode | peak nm | FWHM nm | bounded | T447 | T450 | T453 | avg 447-453 | FWHM6 weighted |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| pol0_angle0 | 453.003 | 10.510 | True | 0.5287 | 0.7501 | 0.9999 | 0.7454 | 0.7505 |
| pol90_angle90 | 452.503 | 10.547 | True | 0.5487 | 0.7851 | 0.9988 | 0.7727 | 0.7789 |

## Judgement

1. Spectral peak near 450 nm: False.
2. FWHM: 10.509908697312483.
3. 447-453 nm remains in a high-response region: False.
4. A later RCLED/MicroLED FWHM鈮? nm spectrum is not clearly acceptable from this normal-incidence plane-wave proxy.
5. Recommended next step: 2D dipole spectral-angle simulation, because this result is only a normal-incidence spectral proxy and cannot replace 2D/3D dipole angular emission validation.

## Figures

- `D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_2d_plane_wave_spectrum\figures\T_norm_vs_wavelength.png`
- `D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_2d_plane_wave_spectrum\figures\T_R_loss_proxy_vs_wavelength.png`
- `D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_2d_plane_wave_spectrum\figures\gaussian_fwhm6_weights_447_453.png`
- `D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_2d_plane_wave_spectrum\figures\polarization_mode_comparison.png`

