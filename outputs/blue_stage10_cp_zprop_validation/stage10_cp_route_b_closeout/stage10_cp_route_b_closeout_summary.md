# Stage10 CP Route-B Closeout

## English

### Closeout decision

`RB1_J1J2_D195_T90_PSI97p5_H525` is frozen as the current Stage10 CP robust finite-patch x-line candidate. It preserves strong calibrated +z periodic plane-wave CP conversion and passes the minimal finite-patch x-axis centerline robustness test. No FDTD or other simulation was run for this closeout package.

### Problem and diagnosis

The original frozen dimer had excellent periodic plane-wave `R_in -> L_out` conversion, but its localized finite-patch response was source-position sensitive. At a +/-20 degree collection cone, the baseline `x_plus_qp` result collapsed to near CP balance (`DoCP_RminusL=+0.031895`, `L_fraction=0.484052`) even though center and `x_minus_qp` remained L-output dominant.

The J1/J2 audit found that the baseline central dimer was not role-preserving mirror symmetric. J1 (230 x 100 nm) was centered at `(31.209338, 85.746952) nm`, while J2 (180 x 90 nm) was centered at `(-31.209338, -85.746952) nm`. The center source was equidistant, `+q` was nearer J1, and `-q` was nearer J2. The observed asymmetry was therefore most consistent with localized J1/J2 excitation-weight sensitivity, rather than a handedness-convention error.

Theta was moved toward 90 degrees because this removes the x projection of the J1/J2 separation vector. The Route-B1 scout showed that D195_T90 reduced `x_bias_abs_nm` to numerical zero while retaining strong periodic plane-wave CP function.

### D195_T90 evidence

For calibrated +z propagation, `R=(Ex-iEy)/sqrt(2)` and `L=(Ex+iEy)/sqrt(2)`. Negative `DoCP_RminusL` means L-output dominance.

Periodic plane-wave `R_in` screening gave:

- `DoCP_RminusL=-0.992551`
- `L_fraction=0.996276`
- `IL_Rin=0.929634`
- dominant/opposite ratio `267.50`
- `x_bias_abs_nm` approximately zero

Finite-patch x/y-incoherent averages at +/-20 degrees were:

| Position | DoCP_RminusL | L_fraction | Total cone power |
|---|---:|---:|---:|
| center | -0.504043 | 0.752021 | 1.11085e-10 |
| x_plus_qp | -0.394126 | 0.697063 | 5.72926e-11 |
| x_minus_qp | -0.438505 | 0.719253 | 6.04762e-11 |

All three positions remain L-output dominant. The minimum L fraction is `0.697063`, above the `0.60` minimal robustness threshold. D195_T90 therefore **passes** the Stage10 minimal x-line robustness test.

Relative to the baseline, center improved slightly with a cone-power ratio of `1.049`; `x_plus_qp` was rescued from CP balance to L-output dominance while retaining `0.770` of baseline cone power; and `x_minus_qp` improved in L fraction while retaining `0.857` of baseline cone power. The principal gain is CP purity and positional robustness, with an acceptable cone-power tradeoff.

### Boundaries and limitations

- Only center, `x_plus_qp`, and `x_minus_qp` on the x-axis centerline were tested.
- No full x-y source-position plane sweep was performed.
- No DBR/RCLED or spacer was included.
- Cone-power and LEE-style values are API-normalized extraction metrics, not independently validated absolute LEE.
- No K=6 or steering is part of this CP closeout.

The CP finite-patch expansion should now pause. D195_T90 is the base candidate for any later DBR/RCLED or spacer integration. The D182p5_T85 backup should be tested only if an independent backup is needed.

## 中文

### 收尾决策

冻结 `RB1_J1J2_D195_T90_PSI97p5_H525`，作为当前 Stage10 CP 鲁棒有限阵列 x 轴中心线候选。它既保持了已校准 +z 周期平面波的强 CP 转换，也通过了最小有限阵列 x 轴中心线鲁棒性测试。本次收尾包没有运行 FDTD 或任何新仿真。

### 原始问题与诊断

原 frozen dimer 的周期平面波 `R_in -> L_out` 转换很强，但局域有限阵列响应对源位置敏感。在 +/-20 度收集 cone 下，baseline 的 `x_plus_qp` 塌到接近 CP 平衡（`DoCP_RminusL=+0.031895`，`L_fraction=0.484052`），而 center 和 `x_minus_qp` 仍为 L 输出占优。

J1/J2 审计显示，baseline 中心 dimer 在保持功能角色的前提下不具备 x 镜面对称性。J1（230 x 100 nm）中心为 `(31.209338, 85.746952) nm`，J2（180 x 90 nm）中心为 `(-31.209338, -85.746952) nm`。center 源到两柱等距，`+q` 更靠近 J1，`-q` 更靠近 J2。因此，观察到的非对称最符合局域照明下 J1/J2 激发权重敏感性，而不是手性约定错误。

将 theta 推向 90 度，是为了消除 J1/J2 分离向量的 x 分量。Route-B1 scout 证明 D195_T90 将 `x_bias_abs_nm` 降到数值零附近，同时保留强周期平面波 CP 功能。

### D195_T90 证据

已校准 +z 传播约定为 `R=(Ex-iEy)/sqrt(2)`、`L=(Ex+iEy)/sqrt(2)`；负 `DoCP_RminusL` 表示 L 输出占优。

周期平面波 `R_in` 筛选得到 `DoCP_RminusL=-0.992551`、`L_fraction=0.996276`、`IL_Rin=0.929634`、主导/反向比 `267.50`，且 `x_bias_abs_nm` 约为零。

在 +/-20 度下，有限阵列 x/y 非相干平均为：center `DoCP=-0.504043`、`L_fraction=0.752021`；`x_plus_qp` `DoCP=-0.394126`、`L_fraction=0.697063`；`x_minus_qp` `DoCP=-0.438505`、`L_fraction=0.719253`。

三个位置全部保持 L 输出占优，最小 `L_fraction=0.697063`，高于 `0.60` 的最小鲁棒性阈值。因此 D195_T90 **通过** Stage10 最小 x-line 鲁棒性测试。

与 baseline 相比，center 略有改善且 cone power 比为 `1.049`；`x_plus_qp` 从 CP 平衡被救回 L 输出占优，同时保留 baseline cone power 的 `0.770`；`x_minus_qp` 的 L 占比改善，同时保留 `0.857` 的 baseline cone power。主要收益是 CP 纯度与位置鲁棒性，cone power 代价可接受。

### 边界与限制

- 只测试了 x 轴中心线的 center、`x_plus_qp`、`x_minus_qp`。
- 没有做完整 x-y 源位置平面扫描。
- 没有加入 DBR/RCLED 或 spacer。
- cone power 与 LEE 类数值是 API-normalized extraction metrics，不是独立验证的绝对 LEE。
- 本 CP closeout 不包含 K=6 或 steering。

当前应暂停 CP 有限阵列扩展。后续 DBR/RCLED 或 spacer 集成应以 D195_T90 为 base；只有需要独立备选时，才测试 D182p5_T85。
