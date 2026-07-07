# FMM2B2Q RCWA-vs-TMM quantitative calibration

## 中文报告

1. 本阶段做了 tiny RCWA-vs-TMM quantitative diagnostic：4 个固定 1D stack case，3 个显式 RCWA variant；没有 sweep、没有 angle audit、没有 candidate ranking。

2. FMM2B2R 仍不足以进入 grating_power/angle audit：它只证明 interface/material inclusion 有定性恢复，但 10-pair RCWA R_avg 仍远低于 TMM oracle 的高反射。

## TMM oracle

| case | TMM R | TMM T |
|---|---:|---:|
| air_reference | 0.0 | 1.0 |
| single_SiO2_79nm | 0.1160629034346602 | 0.8839370965653396 |
| single_TiO2_45nm | 0.5338667610779264 | 0.4661332389220735 |
| TiO2_SiO2_10pair_QWinteger453_proxy | 0.9999597100342625 | 4.028996573727591e-05 |

## RCWA variant results

| variant | case | Rs | Ts | Rp | Tp | R_avg | ratio_R | status |
|---|---|---:|---:|---:|---:|---:|---:|---|
| axis_x_absolute_interfaces | air_reference | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | -0.0 | missing | ok |
| axis_x_absolute_interfaces | single_SiO2_79nm | 0.0014925087550915531 | 0.9985074912449089 | 0.0009451595981624684 | 0.9990548404018381 | 0.0012188341766270108 | 0.010501496520920453 | ok |
| axis_x_absolute_interfaces | single_TiO2_45nm | 0.004817798682236295 | 0.9951822013177635 | 0.0033280553702840438 | 0.996671944629715 | 0.00407292702626017 | 0.007629107716008678 | ok |
| axis_x_absolute_interfaces | TiO2_SiO2_10pair_QWinteger453_proxy | 0.0651899148779494 | 0.9348100851220558 | 0.06314751998984194 | 0.9368524800101549 | 0.06416871743389567 | 0.06417130289349057 | ok |
| axis_z_absolute_interfaces | air_reference | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | -0.0 | missing | ok |
| axis_z_absolute_interfaces | single_SiO2_79nm | 0.11606290343465953 | 0.8839370965653335 | 0.11606290343465953 | 0.8839370965653335 | 0.11606290343465953 | 0.9999999999999941 | ok |
| axis_z_absolute_interfaces | single_TiO2_45nm | 0.5338667610779256 | 0.4661332389220726 | 0.5338667610779256 | 0.4661332389220726 | 0.5338667610779256 | 0.9999999999999986 | ok |
| axis_z_absolute_interfaces | TiO2_SiO2_10pair_QWinteger453_proxy | 0.9999597100342542 | 4.02899657372751e-05 | 0.9999597100342542 | 4.02899657372751e-05 | 0.9999597100342542 | 0.9999999999999917 | ok |
| index_grid_or_explicit_material_variant | air_reference | -0.0 | 1.0000000000000002 | -0.0 | 1.0000000000000002 | -0.0 | missing | ok |
| index_grid_or_explicit_material_variant | single_SiO2_79nm | 0.0006175296947267458 | 0.9993824703052744 | 0.0005131042802191679 | 0.9994868957197807 | 0.0005653169874729569 | 0.004870781022561724 | ok |
| index_grid_or_explicit_material_variant | single_TiO2_45nm | 0.0022298247384602435 | 0.9977701752615402 | 0.0018809505541936419 | 0.9981190494458072 | 0.0020553876463269426 | 0.0038500011541773545 | ok |
| index_grid_or_explicit_material_variant | TiO2_SiO2_10pair_QWinteger453_proxy | 0.05885791156128729 | 0.9411420884387189 | 0.05789337295136375 | 0.9421066270486358 | 0.05837564225632552 | 0.05837799430371584 | ok |

## Decision

- 最接近 TMM 的 variant（按 DBR R 最大）：`axis_z_absolute_interfaces`，10-pair R_avg=`0.9999597100342542`，ratio=`0.9999999999999917`。
- 是否找到 10-pair 高反射 >0.8：`True`。
- 若仍不接近，当前失败更像 RCWA object/command 或 region/layer-interpretation 限制，而不是 total_energy schema 缺失；axis_z 未成为定量解。
- decision = `rcwa_tmm_quantitative_pass`。
- 明确限制：没有 FDTD；没有打开/修改 H1J4 FSP；没有 sweep；没有 broadband；没有 APCD coupling；没有 push。
