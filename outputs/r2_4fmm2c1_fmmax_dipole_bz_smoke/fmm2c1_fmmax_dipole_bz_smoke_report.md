# FMM2C1 FMMAX localized-dipole / BZ smoke

## 中文报告

1. 本阶段做了 Python-only FMMAX/JAX 环境检查、fmmax 包 API inventory、关键词扫描，以及一个最小 localized-source/BZ API smoke。
2. FMMAX/JAX 当前环境是否可用：`True`；fmmax version=`v1.7.1`；JAX devices=`["cpu:0"]`。
3. 是否找到 dipole/localized source/Brillouin-zone API 或 example 路径：`True`。关键模块包括 `fmmax.sources`, `fmmax.basis`, `fmmax.fields`, `fmmax.scattering`。
4. 是否跑了 tiny smoke test：`True`。
5. tiny 结果：runtime=2.610381199978292 s, dirac_source_norm=1.0, gaussian_source_norm=1.0, bz_wavevector_norm=0.0。该 smoke 只验证 source/BZ API 和轻量标量，不是完整辐射功率求解。
6. 若未完整 power/flux：原因是当前只调用 pip package 中最小 source/BZ API；radiated/extracted power 需要下一步构造 layer solve + scattering/source amplitude 链路。
7. 对 ML dataset 加速判断：`FMM2C2 tiny single-dipole slab metric`。
8. 明确限制：没有 FDTD；没有 H1J4 FSP；没有 Lumerical RCWA；没有 optimization；没有 ML dataset；没有 push。
9. decision = `fmmax_dipole_bz_smoke_pass`。

## Matched files preview

- `fmmax/__init__.py`
- `fmmax/_fields.py`
- `fmmax/basis.py`
- `fmmax/beams.py`
- `fmmax/farfield.py`
- `fmmax/fields.py`
- `fmmax/fmm.py`
- `fmmax/fmm_matrices.py`
- `fmmax/sources.py`
- `fmmax/vector.py`
