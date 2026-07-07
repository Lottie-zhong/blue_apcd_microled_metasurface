# FMM2C-FREEZE FMMAX dipole feasibility no-run synthesis

## 中文报告

1. 本阶段是 no-run synthesis，没有新仿真、没有新 FMMAX run，只读取 FMM2C1/FMM2C2/FMM2C3 已提交的轻量 CSV/JSON/MD 结果。
2. FMM2C1 证明：`py -3.12` 可用，`fmmax v1.7.1`、`jax 0.10.2`、`jaxlib 0.10.2` 可 import，device=`cpu:0`，`dirac_delta_source`、`gaussian_source`、`brillouin_zone_in_plane_wavevector` 可调用，decision=`fmmax_dipole_bz_smoke_pass`。
3. FMM2C2 证明：最小 FMMAX optical-metric chain 可跑通，即 `basis -> fmm.eigensolve_isotropic_media -> scattering.stack_s_matrix -> sources.amplitudes_for_source -> fields.directional_poynting_flux`，并从 homogeneous air / dielectric slab tiny cases 提取到 true Poynting-flux-like scalar。
4. FMM2C3 证明：同一链路可扩展到 tiny DBR/slab extraction table；DBR-like stacks 明显把 localized-source flux 推向 top side，decision=`fmmax_dbr_slab_dipole_table_pass`。
5. 完整方法链：localized source / Gaussian source -> BZ / in-plane wavevector -> eigensolve -> scattering matrix -> source amplitudes -> directional_poynting_flux -> DBR/slab top-bottom flux table。

## FMM2C3 top/bottom flux table

| stage | case | top_flux | bottom_flux | total | top_fraction |
|---|---|---:|---:|---:|---:|
| FMM2C2 | homogeneous_air_gaussian_source | 0.125 | 0.125 | 0.25 | 0.5 |
| FMM2C2 | dielectric_slab_mid_gaussian_source | 0.06402400881052017 | 0.06402400881052017 | 0.12804801762104034 | 0.5 |
| FMM2C3 | homogeneous_air_reference | 0.125 | 0.125 | 0.25 | 0.5 |
| FMM2C3 | single_dielectric_slab_reference | 0.06402400881052017 | 0.06402400881052017 | 0.12804801762104034 | 0.5 |
| FMM2C3 | TiO2_SiO2_2pair_DBR_tiny | 0.2082606554031372 | 0.035500410944223404 | 0.2437610663473606 | 0.8543639003710496 |
| FMM2C3 | TiO2_SiO2_4pair_DBR_tiny | 0.2738541066646576 | 0.0047081452794373035 | 0.2785622519440949 | 0.9830984088957531 |
| FMM2C3 | TiO2_SiO2_10pair_DBR_H1J4_like_tiny | 0.28316009044647217 | 4.889697720500408e-06 | 0.28316498014419267 | 0.9999827319828956 |

## 冻结结论

FMMAX/FMM 可以用于偶极源/局域源仿真的可行性证明已经完成。证据链覆盖 localized-source API、BZ/in-plane wavevector、layer eigensolve、scattering stack、source amplitude injection、directional Poynting-flux scalar，以及 DBR/slab top-bottom flux extraction table。

## 边界和不能过度声明的内容

- 还不能说已经替代 H1J4 FDTD。
- 还不能说已经生成 ML dataset。
- 还不能说已经完成真实 RCLED-MDC candidate validation。
- 还不能说已经与 FDTD 做绝对物理标定。
- 还不能说已经验证 finite mesa、sidewall、off-center dipole 或 APCD coupling。

## 组会可用一句话

“We verified a FMMAX/JAX localized-source workflow that links Gaussian-source excitation, Brillouin-zone/in-plane-wavevector handling, layer eigensolve, scattering matrix construction, source amplitude injection, and directional Poynting-flux extraction. The DBR/slab tiny table further shows that DBR-like stacks can redirect localized-source flux toward the top side, demonstrating the feasibility of FMM-based dipole-source simulation for future RCLED/Micro-LED dataset acceleration.”

## 后续若以后重启

- FMM2C4 = source-position/orientation incoherent averaging。
- FMM2C5 = source-weight prototype `w(lambda, theta, phi, pol)`。
- ML dataset generation = only after calibration and validation。
- 本轮停止 FMM2C feasibility track，不继续扩展。

## 明确限制

没有 FDTD；没有打开或修改 H1J4 FSP；没有 Lumerical RCWA；没有新 FMMAX run；没有 broadband；没有 optimization；没有 ML dataset；没有 push。
