# Calibrated +z x-line centerline dipole sweep summary

## English

This is an x-axis centerline dipole-position sweep, not a full x-y plane sweep. y is fixed at 0 nm. No DBR, no K=6, no +10 degree steering, no 41-position sweep, and no coherent x/y dipole field addition.

- offset q = 107.976946 nm, quarter local pitch convention.
- planned x-line cases: 10.
- extracted ok cases: 6.
- complete x-line positions with both x/y orientations: 3 (center, x_minus_qp, x_plus_qp).
- sourcepower API available for extracted cases: True; LEE-style values are API-normalized extraction metrics, not independently validated absolute LEE.
- calibrated label: negative DoCP_RminusL means L-output dominant.

### +/-20 degree complete-position averages

| position | DoCP_RminusL | L fraction | total cone power |
|---|---:|---:|---:|
| center | -0.471676 | 0.735838 | 1.05872e-10 |
| x_minus_qp | -0.380125 | 0.690063 | 7.05843e-11 |
| x_plus_qp | 0.0318954 | 0.484052 | 7.44342e-11 |

## 中文

这是 x 轴中心线偶极位置扫描，不是完整 x-y 平面扫描。y 固定为 0 nm。没有 DBR，没有 K=6，没有 +10° steering，没有 41-position 扫描，也没有对 x/y 偶极电场做相干叠加。

- 偏移 q = 107.976946 nm，沿用 quarter local pitch 约定。
- 当前计划中的 x-line cases：10。
- 成功提取 cases：6。
- 同时具备 x/y 取向的完整 x-line 位置：3（center, x_minus_qp, x_plus_qp）。
- 已提取 cases 的 sourcepower API 是否可用：True；LEE-style 值是 API-normalized extraction metrics，不是独立验证过的 absolute LEE。
