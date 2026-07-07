# FMM2C3 FMMAX tiny DBR/slab dipole extraction table

## 中文报告

1. 本阶段做了 Python-only FMMAX tiny DBR/slab dipole extraction table：固定 453 nm-like wavelength、单个 Gaussian localized source proxy、minimal Fourier expansion，只跑 5 个 tiny fixed cases。
2. 沿用了 FMM2C2 validated API chain：`basis` -> `fmm.eigensolve_isotropic_media` -> `scattering.stack_s_matrix` -> `sources.amplitudes_for_source` -> `fields.directional_poynting_flux`。
3. 跑的 tiny stack cases：homogeneous air、single dielectric slab、TiO2/SiO2 2-pair DBR、4-pair DBR、10-pair H1J4-like tiny DBR。
4. `directional_poynting_flux` 输出被标记为 FMMAX Poynting-flux-like scalar；这里不声称绝对物理校准，也没有做 convergence study。
5. DBR-like stack 是否改变通量分配：DBR-like cases changed top fraction from slab reference 0.5000 to max 1.0000.
6. 是否具备 ML label 雏形：`yes_tiny_scalar_label_embryo_not_dataset`。它只是 tiny scalar-label prototype，还不是 ML dataset generation。
7. 下一步建议：`FMM2C4 tiny source-position/orientation averaging`。
8. 明确限制：没有 FDTD；没有打开或修改 H1J4 FSP；没有 Lumerical RCWA；没有 broadband；没有 optimization；没有 ML dataset；没有 push。
9. decision = `fmmax_dbr_slab_dipole_table_pass`。

## Top/bottom flux table

| case | status | top_flux | bottom_flux | total_outward_flux | top_fraction | top/bottom | runtime_s |
|---|---:|---:|---:|---:|---:|---:|---:|
| homogeneous_air_reference | ok | 0.125 | 0.125 | 0.25 | 0.5 | 1.0 | 9.256536000408232 |
| single_dielectric_slab_reference | ok | 0.06402400881052017 | 0.06402400881052017 | 0.12804801762104034 | 0.5 | 1.0 | 0.0807480001822114 |
| TiO2_SiO2_2pair_DBR_tiny | ok | 0.2082606554031372 | 0.035500410944223404 | 0.2437610663473606 | 0.8543639003710496 | 5.866429426136691 | 1.4612344997003675 |
| TiO2_SiO2_4pair_DBR_tiny | ok | 0.2738541066646576 | 0.0047081452794373035 | 0.2785622519440949 | 0.9830984088957531 | 58.16602725933458 | 1.4194697001948953 |
| TiO2_SiO2_10pair_DBR_H1J4_like_tiny | ok | 0.28316009044647217 | 4.889697720500408e-06 | 0.28316498014419267 | 0.9999827319828956 | 57909.52869321619 | 1.3551850002259016 |

## Source placement convention

- In-plane Gaussian source proxy location is normalized unit-cell `(0.5, 0.5)`.
- z placement is represented by the source interface between the top half and bottom half of the source slab stack.
- DBR cases place TiO2/SiO2 pairs below the central source slab, so the table tests whether a simple bottom DBR proxy redirects FMMAX directional Poynting flux upward.
