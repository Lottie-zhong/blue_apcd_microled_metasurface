# Stage10 CP BW2A PSI99 Center Spectral Power Audit

## English Summary

This audit reads existing CSV outputs only. No FDTD was run, and no FSP/LDF/runtime files were opened, moved, deleted, or modified.

### Strongest Total Cone Power
- 5 deg: 420 nm: total=7.03663e-12, L_fraction=0.913665, usable_L=6.42913e-12
- 10 deg: 420 nm: total=2.99779e-11, L_fraction=0.874956, usable_L=2.62293e-11
- 20 deg: 424 nm: total=1.1298e-10, L_fraction=0.810338, usable_L=9.15523e-11

### Strongest Usable L_out Power
- 5 deg: 420 nm: total=7.03663e-12, L_fraction=0.913665, usable_L=6.42913e-12
- 10 deg: 420 nm: total=2.99779e-11, L_fraction=0.874956, usable_L=2.62293e-11
- 20 deg: 422 nm: total=1.12656e-10, L_fraction=0.814921, usable_L=9.18054e-11

### Strongest Spectral Windows by Average Usable L_out Power
- 5 deg, 4 nm window: 420-424 nm, avg usable L=6.38282e-12, avg total=6.98378e-12, avg L_fraction=0.913949
- 5 deg, 6 nm window: 420-426 nm, avg usable L=6.30543e-12, avg total=6.91413e-12, avg L_fraction=0.9119
- 5 deg, 8 nm window: 420-428 nm, avg usable L=6.20996e-12, avg total=6.84388e-12, avg L_fraction=0.907126
- 5 deg, 10 nm window: 420-430 nm, avg usable L=6.11302e-12, avg total=6.78165e-12, avg L_fraction=0.900914
- 10 deg, 4 nm window: 420-424 nm, avg usable L=2.6086e-11, avg total=2.98472e-11, avg L_fraction=0.873979
- 10 deg, 6 nm window: 420-426 nm, avg usable L=2.58493e-11, avg total=2.96436e-11, avg L_fraction=0.871957
- 10 deg, 8 nm window: 420-428 nm, avg usable L=2.55667e-11, avg total=2.94439e-11, avg L_fraction=0.868181
- 10 deg, 10 nm window: 420-430 nm, avg usable L=2.52735e-11, avg total=2.92568e-11, avg L_fraction=0.863585
- 20 deg, 4 nm window: 420-424 nm, avg usable L=9.1594e-11, avg total=1.1248e-10, avg L_fraction=0.814328
- 20 deg, 6 nm window: 420-426 nm, avg usable L=9.12985e-11, avg total=1.12471e-10, avg L_fraction=0.81176
- 20 deg, 8 nm window: 420-428 nm, avg usable L=9.09747e-11, avg total=1.12547e-10, avg L_fraction=0.808342
- 20 deg, 10 nm window: 420-430 nm, avg usable L=9.06054e-11, avg total=1.12598e-10, avg L_fraction=0.804701

### Interpretation
- At 20 deg, total-power maximum is 424 nm: total=1.1298e-10, L_fraction=0.810338, usable_L=9.15523e-11.
- At 20 deg, usable-L maximum is 422 nm: total=1.12656e-10, L_fraction=0.814921, usable_L=9.18054e-11.
- At 20 deg, CP-selectivity maximum is 420 nm: total=1.11803e-10, L_fraction=0.817724, usable_L=9.14242e-11.
- The power maximum is not aligned with the CP-selectivity maximum.
- The red side mainly loses total cone power; L_fraction remains high and does not indicate a CP-selectivity collapse.
- Best 20 deg window: 420-424 nm by average usable L_out power.
- Missing expected rows: 0.

### Recommended Off-center Validation Wavelengths
- Power maximum wavelength: 422 nm
- Project-center wavelength: 453 nm
- Blue edge wavelength: 420 nm
- Red edge wavelength: 480 nm

## 中文判断

本审计只读取已有 CSV，没有运行 FDTD，也没有打开、移动、删除或修改 FSP/LDF/runtime 文件。

20 deg 下，总 cone power 最强点为 424 nm: total=1.1298e-10, L_fraction=0.810338, usable_L=9.15523e-11。
20 deg 下，可用 L_out power 最强点为 422 nm: total=1.12656e-10, L_fraction=0.814921, usable_L=9.18054e-11。
20 deg 下，CP 选择性最高点为 420 nm: total=1.11803e-10, L_fraction=0.817724, usable_L=9.14242e-11。
功率峰值与 CP 选择性峰值不完全重合。红侧主要是 total cone power 下降，L_fraction 仍保持较高，不是 CP 选择性塌陷。
建议后续 off-center 检查波长：功率峰值 422 nm、项目中心 453 nm、蓝边 420 nm、红边 480 nm。
