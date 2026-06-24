# Stage RCLED MDC_blue_oujizi DBR-only far-field

## Scope and model

- Source DBR reference: `N:\zlt\DBR\MDC_blue_oujizi.fsp` (read only).
- Project base FSP: `D:\project\blue_apcd_microled_metasurface\outputs\stage10_cp_dbr_1_gan_dbr_only\_setup_fsp\gan_dbr_only_grouped_setup.fsp`.
- Final setup model: `D:\project\blue_apcd_microled_metasurface\outputs\stage_rcled_mdc_blue_oujizi_dbr_only\rcled_mdc_blue_oujizi_dbr_only_no_metasurface.fsp`.
- Only the DBR sampled-material data, layer thicknesses, count, and ordering were copied from the lab FSP. Its source, monitor, LED/device objects, propagation axis, FDTD region, and boundaries were not imported.
- DBR order along project +z: `[sio222 100 nm -> tio22 52 nm] x 8 -> terminal sio222 100 nm`, 17 layers and 1316 nm total thickness.
- GUI colors follow the source materials: `tio22` red `[0.75,0,0,1]`; `sio222` yellow `[1,1,0,1]`.
- No APCD/B4INT/metasurface object is present. Exactly two new FDTD cases were run: center_x and center_y.

## Runtime and files

| Case | Runtime | Result size |
|---|---:|---:|
| center_x | 2350.92 s (39.18 min) | 102,652,565 bytes |
| center_y | 2354.59 s (39.24 min) | 102,652,565 bytes |

Far-field data use direct `farfield3d` from the Z-normal `top_field_monitor_zprop`; `prop_axis=3`. The x/y dipole intensities were summed incoherently. Values are API-normalized proxies, not absolute LEE.

## New MDC_blue_oujizi x/y incoherent metrics

| Metric | Value |
|---|---:|
| P_total_x | 1.07570e-13 |
| P_total_y | 5.94244e-14 |
| P_total_xy_incoherent | 1.66995e-13 |
| eta_5deg | 0.0152722 (1.5272%) |
| eta_10deg | 0.0817691 (8.1769%) |
| eta_20deg | 0.208548 (20.8548%) |
| eta_30deg | 0.259737 (25.9737%) |
| x-cut peak | +1.15368 deg |
| x-cut FWHM | 11.5556 deg |
| y-cut peak | +8.10222 deg |
| y-cut FWHM | 31.9440 deg |

## Comparison

| Stack | eta5 | eta10 | eta20 | eta30 | x FWHM | y FWHM | P total proxy |
|---|---:|---:|---:|---:|---:|---:|---:|
| No DBR | 0.00967811 | 0.0403460 | 0.152836 | 0.332885 | 91.7991 deg | 91.7991 deg | 4.08429e-13 |
| Previous temporary DBR | 0.0183773 | 0.0902028 | 0.173906 | 0.269084 | 13.1027 deg | 50.0254 deg | 1.69747e-13 |
| MDC_blue_oujizi DBR | 0.0152722 | 0.0817691 | 0.208548 | 0.259737 | 11.5556 deg | 31.9440 deg | 1.66995e-13 |

## Main answer

The `MDC_blue_oujizi` DBR narrows the far-field FWHM better than the previous temporary DBR in both central cuts, with the largest improvement in the y-cut (`50.03 deg -> 31.94 deg`). The result is mixed rather than uniformly superior: eta_5deg and eta_10deg are slightly lower, eta_20deg is higher, and total far-field power proxy is about 1.6% lower than the temporary DBR. Relative to no DBR, the new stack strongly narrows both cuts but also reduces the total far-field power proxy. Therefore it is a better divergence-shaping DBR by FWHM, not a demonstrated absolute extraction-efficiency improvement.

## Postprocess note

Adapted copies of `outputs/3d_farfield_source.lsf` change only `data_mode`, `monitor_name`, `prop_axis`, and `export_prefix`; the original is untouched. Because the supplied LSF contains a syntax incompatibility with Ansys 2025 R1 at its trailing-dimension `while` block, final figures and metrics use the existing project Python/lumapi fallback with the same `farfield3d`, solid-angle integration, cone, peak, and FWHM definitions.

## 中文结论

新 `MDC_blue_oujizi` DBR 在 x、y 两个中心切线上的 FWHM 都小于旧临时 DBR，尤其 y-cut 从约 50.03 度缩小到 31.94 度，因此按发散角/FWHM 判断，新 DBR 的收窄效果更好。但它并非所有指标都更优：正负 5 度和正负 10 度 cone 占比略低，正负 20 度占比更高，总远场功率代理比旧 DBR 低约 1.6%。因此当前结论是“发散角整形更好，但尚未证明绝对提取效率提升”。
