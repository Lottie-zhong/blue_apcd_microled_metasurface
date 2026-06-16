# CP Stage10 +z x-line minimal robustness diagnostic

## English

This is an x-axis centerline-only diagnostic, not a full x-y plane dipole-position sweep. y is fixed at 0 nm. No y-offset cases, 41-position sweep, bare reference, DBR/RCLED, K=6, steering, or geometry changes were run.

Scientific motivation: following the Taguchi-style lesson, strong periodic plane-wave CP selection is not enough; source-position and angular-spectrum robustness must also be checked.

- center x/y average at +/-20 deg: DoCP_RminusL = -0.471676, L_fraction = 0.735838.
- x_plus_qp x/y average at +/-20 deg: DoCP_RminusL = 0.0318954, L_fraction = 0.484052.
- x_minus_qp x/y average at +/-20 deg: DoCP_RminusL = -0.380125, L_fraction = 0.690063.

### New x_minus_qp_y result

| cone | DoCP_RminusL | L_fraction | total_cone_power |
|---:|---:|---:|---:|
| +/-5 deg | -0.040291 | 0.520146 | 2.31483e-12 |
| +/-10 deg | -0.0511043 | 0.525552 | 9.28741e-12 |
| +/-20 deg | -0.0307819 | 0.515391 | 3.32086e-11 |

### Position averages

| position | cone | DoCP_RminusL | L_fraction |
|---|---:|---:|---:|
| center | +/-5 deg | -0.612628 | 0.806314 |
| center | +/-10 deg | -0.592346 | 0.796173 |
| center | +/-20 deg | -0.471676 | 0.735838 |
| x_plus_qp | +/-5 deg | 0.0555576 | 0.472221 |
| x_plus_qp | +/-10 deg | 0.0106265 | 0.494687 |
| x_plus_qp | +/-20 deg | 0.0318954 | 0.484052 |
| x_minus_qp | +/-5 deg | -0.456004 | 0.728002 |
| x_minus_qp | +/-10 deg | -0.43578 | 0.71789 |
| x_minus_qp | +/-20 deg | -0.380125 | 0.690063 |

Interpretation: x_minus_qp after x/y incoherent averaging is L-output dominant at +/-20 deg.
+q/-q asymmetry at +/-20 deg is observed: |DoCP(+q)-DoCP(-q)| = 0.41202.
x_plus_qp remains poor/nearly balanced even at +/-5 deg; this supports improving dimer/source-position robustness before relying on DBR/RCLED angular narrowing.
Next recommended step: run x_minus_2qp_x only if extending the x-line robustness map is still desired; otherwise analyze why +q and -q behave differently.

## 中文

这是只沿 x 轴中心线的最小诊断，不是完整 x-y 平面偶极位置扫描。y 固定为 0 nm。本轮没有运行 y-offset、41-position、bare reference、DBR/RCLED、K=6、steering，也没有改变 frozen dimer 几何。

科学动机：对应 Taguchi-style 启示，强周期平面波 CP 选择并不够，还必须检查源位置和角谱鲁棒性。

- center x/y 平均 +/-20°: DoCP_RminusL = -0.471676, L_fraction = 0.735838。
- x_plus_qp x/y 平均 +/-20°: DoCP_RminusL = 0.0318954, L_fraction = 0.484052。
- x_minus_qp x/y 平均 +/-20°: DoCP_RminusL = -0.380125, L_fraction = 0.690063。

### 新的 x_minus_qp_y 结果

| cone | DoCP_RminusL | L_fraction | total_cone_power |
|---:|---:|---:|---:|
| +/-5° | -0.040291 | 0.520146 | 2.31483e-12 |
| +/-10° | -0.0511043 | 0.525552 | 9.28741e-12 |
| +/-20° | -0.0307819 | 0.515391 | 3.32086e-11 |

### 位置平均

| position | cone | DoCP_RminusL | L_fraction |
|---|---:|---:|---:|
| center | +/-5° | -0.612628 | 0.806314 |
| center | +/-10° | -0.592346 | 0.796173 |
| center | +/-20° | -0.471676 | 0.735838 |
| x_plus_qp | +/-5° | 0.0555576 | 0.472221 |
| x_plus_qp | +/-10° | 0.0106265 | 0.494687 |
| x_plus_qp | +/-20° | 0.0318954 | 0.484052 |
| x_minus_qp | +/-5° | -0.456004 | 0.728002 |
| x_minus_qp | +/-10° | -0.43578 | 0.71789 |
| x_minus_qp | +/-20° | -0.380125 | 0.690063 |

判断：x_minus_qp 经过 x/y 非相干平均后在 +/-20° 下仍是 L 输出占优。
观察到 +q/-q 非对称：+/-20° 下 |DoCP(+q)-DoCP(-q)| = 0.41202。
x_plus_qp 在 +/-5° 下仍然较差/接近平衡；这支持在依赖 DBR/RCLED 角谱收窄前，先改善 dimer/source-position 鲁棒性。
下一步建议：如果还需要扩展 x-line 鲁棒性图，再只跑 x_minus_2qp_x；否则优先分析 +q 和 -q 行为差异的来源。
