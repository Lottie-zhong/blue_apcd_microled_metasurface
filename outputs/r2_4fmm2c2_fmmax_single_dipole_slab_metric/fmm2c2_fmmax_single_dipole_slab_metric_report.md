# FMM2C2 FMMAX tiny single-dipole slab metric

## 中文报告

1. 本阶段做了 Python-only FMMAX tiny single-dipole/slab optical-metric feasibility test：先映射 FMMAX API，再运行一个 homogeneous air source case 和一个 dielectric slab mid-source case。
2. FMM2C1 已证明：FMMAX/JAX 可 import，CPU backend 可用，`fmmax.sources.dirac_delta_source`、`gaussian_source` 与 `basis.brillouin_zone_in_plane_wavevector` 可用；但 FMM2C1 还缺 layer solve、scattering、farfield、radiated power 或 flux extraction。
3. 本阶段使用的关键 FMMAX API：`basis.LatticeVectors`、`basis.generate_expansion`、`fmm.eigensolve_isotropic_media`、`scattering.stack_s_matrix`、`sources.amplitudes_for_source`、`fields.directional_poynting_flux`。
4. 是否完成 tiny source/slab solve：`True`。
5. 是否提取到 true flux/power/radiated-power-like scalar：`True`。提取路径是 FMMAX 文档中的 `fields.directional_poynting_flux`，这里报告的是 top/bottom exterior layer 的 outward directional Poynting flux magnitude；raw signed flux 也保存在 CSV 中。
6. amplitude/norm 字段只是 proxy，用来辅助 debug，不被称为真实功率。
7. 对机器学习数据集加速的判断：`ready_for_FMM2C3_tiny_DBR_slab_dipole_extraction_table`。当前可以进入 FMM2C3 的小型 DBR/slab dipole extraction table，但还不是 ML dataset generation。
8. 下一步建议：`FMM2C3 tiny DBR/slab dipole extraction table`。
9. 明确限制：没有 FDTD；没有打开或修改 H1J4 FSP；没有 Lumerical RCWA；没有 broadband；没有 optimization；没有 ML dataset；没有 push。
10. decision = `fmmax_single_dipole_metric_pass`。

## Tiny metric table

| case | status | true flux? | top flux abs | bottom flux abs | total flux abs | amplitude proxy |
|---|---:|---:|---:|---:|---:|---:|
| homogeneous_air_gaussian_source | ok | True | 0.125 | 0.125 | 0.25 | 1.0 |
| dielectric_slab_mid_gaussian_source | ok | True | 0.06402400881052017 | 0.06402400881052017 | 0.12804801762104034 | 0.715675950050354 |

## Notes

- `directional_poynting_flux` 返回带符号的方向 flux 分量；top/backward escaping channel 在本约定下为负号，因此 summary scalar 使用其绝对值作为 outward flux magnitude。
- 当前只用 minimal Fourier expansion 和单一 wavelength-like point 0.453 um；这不是 convergence study。
