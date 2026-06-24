# RCLED / DBR-only 3D far-field postprocess

## Scope

- No new FDTD solve was launched. Only completed `.fsp` monitor data were loaded and postprocessed.
- Propagation axis: `+z` (`prop_axis = 3`).
- Monitor: `top_field_monitor_zprop` (Z-normal).
- Data source: direct `farfield3d`, not `getsweepresult`.
- DBR-only input FSPs:
  - `GAN_DBR_ONLY_CENTER_X_T100FS.fsp`
  - `GAN_DBR_ONLY_CENTER_Y_T100FS.fsp`
- Reference FSPs: completed planar no-DBR GaN center x/y results from Stage10 DBR-0.
- x/y dipole far-field intensities were summed incoherently before the main comparison.

## DBR-only x/y incoherent result

| Metric | Result |
|---|---:|
| eta_5deg | 0.0183773 (1.8377%) |
| eta_10deg | 0.0902028 (9.0203%) |
| eta_20deg | 0.173906 (17.3906%) |
| eta_30deg | 0.269084 (26.9084%) |
| x-cut peak | -1.15368 deg |
| x-cut FWHM | 13.1027 deg |
| y-cut peak | 7.32612 deg |
| y-cut FWHM | 50.0254 deg |
| total solid-angle power proxy | 1.69747e-13 |

## Comparison with no-DBR planar GaN reference

| Metric | DBR only | No DBR | DBR / reference or change |
|---|---:|---:|---:|
| eta_5deg | 0.0183773 | 0.00967811 | 1.89885x |
| eta_10deg | 0.0902028 | 0.0403460 | 2.23573x |
| eta_20deg | 0.173906 | 0.152836 | 1.13786x |
| eta_30deg | 0.269084 | 0.332885 | 0.808339x |
| x-cut FWHM | 13.1027 deg | 91.7991 deg | -78.6964 deg |
| y-cut FWHM | 50.0254 deg | 91.7991 deg | -41.7737 deg |
| total solid-angle power proxy | 1.69747e-13 | 4.08429e-13 | 0.415605x |

The DBR-only / RCLED stack **does narrow the far-field divergence** relative to the available no-DBR planar GaN reference: both central-cut FWHMs decrease and the fractions inside 5, 10, and 20 degrees increase. The narrowing is anisotropic; the y-cut remains much broader than the x-cut. This is not a net extraction-power enhancement: the integrated far-field power proxy falls to about `0.416x` the reference, and the absolute +/-20 degree cone-power proxy is about `0.473x` the reference. These values are API-normalized far-field proxies, not absolute LEE.

## Script adaptations and warnings

- The original `outputs/3d_farfield_source.lsf` was not overwritten.
- Per-case copies changed `data_mode=2`, `monitor_name="top_field_monitor_zprop"`, `prop_axis=3`, and `export_prefix`.
- Ansys 2025 R1 interpreted `run("script.lsf")` as a solver command, so wrappers use `feval("script.lsf")`.
- The supplied script's `while (...) {}` block produced a syntax error at line 108 in this installation. Direct-monitor data are already 2D, so copied scripts use a single conditional trailing-dimension reduction.
- The copied LSF still did not complete reliably through lumapi. Final metrics and figures were therefore generated with the project Python/lumapi fallback using the same `farfield3d`, solid-angle correction, cone masks, cuts, peak, and first-to-last half-maximum FWHM definitions.
- The first-to-last half-maximum FWHM definition can span separated lobes; interpret broad or multi-lobed cuts together with the exported images.

## 中文结论

本轮没有启动新的 FDTD，只读取已经完成的 monitor 数据。与已有无 DBR 平面 GaN 参考相比，DBR-only / RCLED 的 x、y 中心切线 FWHM 均减小，且 +/-5、+/-10、+/-20 度 cone 内的功率占比提高，因此可以判断远场发散角得到收窄。不过这种收窄明显各向异性，y-cut 仍比 x-cut 宽；同时总远场功率代理降至参考的约 `0.416x`，绝对 +/-20 度 cone 功率代理约为参考的 `0.473x`。因此当前结果是“角谱收窄，但提取功率下降”，不能宣称绝对 LEE 得到提升。
