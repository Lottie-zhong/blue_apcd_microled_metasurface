# Stage10 CP Route B4-1 fabrication-integer periodic plane-wave screen

## English

- Route B4-1; CP-APCD J1/J2 dimer branch only.
- Finite-patch dipole FDTD: not run. No source-position cases were run.
- D195_T90_PSI97p5 remains the physical robust reference, but is not fabrication-integer-ready because its centers are y=+/-97.5 nm and its J1/J2 rotations are -7.5/+37.5 deg.
- D194/D196 make the theta=90 deg centers exactly +/-97 or +/-98 nm; PSI97/PSI98 make both actual pillar rotations integer degrees.
- Integer candidates screened: 4; fabrication_integer_ready: B4INT_J1J2_D194_T90_PSI97_H525, B4INT_J1J2_D194_T90_PSI98_H525, B4INT_J1J2_D196_T90_PSI97_H525, B4INT_J1J2_D196_T90_PSI98_H525.
- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); negative DoCP_RminusL means L-output dominant.

| rank | candidate | J1 center | J2 center | rotations J1/J2 | DoCP R-in | L fraction | IL_Rin | R-input IL/IR ratio | x-bias | soft pass |
|---:|---|---|---|---|---:|---:|---:|---:|---:|---|
| 1 | B4INT_J1J2_D194_T90_PSI97_H525 | (0, 97) | (0, -97) | -7/38 | -0.993259629255 | 0.996629814627 | 0.952912148973 | 295.719583476 | 1.18790739517e-14 | yes |
| 2 | B4INT_J1J2_D196_T90_PSI97_H525 | (0, 98) | (0, -98) | -7/38 | -0.99237497847 | 0.996187489235 | 0.966137641537 | 261.294341368 | 1.20015386316e-14 | yes |
| 3 | B4INT_J1J2_D194_T90_PSI98_H525 | (0, 97) | (0, -97) | -8/37 | -0.993265789591 | 0.996632894796 | 0.917162547218 | 295.991017293 | 1.18790739517e-14 | yes |
| 4 | B4INT_J1J2_D196_T90_PSI98_H525 | (0, 98) | (0, -98) | -8/37 | -0.992397623246 | 0.996198811623 | 0.934801703753 | 262.075622881 | 1.20015386316e-14 | yes |

Reference D195_T90_PSI97p5: DoCP=-0.99255133, L_fraction=0.996275665, IL_Rin=0.929634238, R-input IL/IR ratio=267.504297; reference only, not rerun.

Ratio note: the soft threshold uses IL_Rin/IR_Rin for reconstructed R input. The stricter IL_Rin/(IR_Rin+IR_Lin+IL_Lin) is reported separately as target_to_all_other_ratio.

Recommended Route B4-2 candidate: `B4INT_J1J2_D194_T90_PSI97_H525`. Next, and not in this task, run only center_x/y, x_plus_qp_x/y, and x_minus_qp_x/y for that candidate.

## 中文

- 本任务是 Route B4-1，只处理 CP-APCD J1/J2 dimer 支线。
- 没有运行 finite-patch dipole FDTD，也没有运行任何源位置 case。
- D195_T90_PSI97p5 仍是物理鲁棒 reference，但其中心为 y=+/-97.5 nm、J1/J2 旋转为 -7.5/+37.5 deg，因此不是整数加工就绪设计。
- D194/D196 在 theta=90 deg 时分别给出精确 +/-97 nm 和 +/-98 nm 中心；PSI97/PSI98 使两根柱的实际旋转角均为整数度。
- 共筛选 4 个整数候选；fabrication_integer_ready：B4INT_J1J2_D194_T90_PSI97_H525, B4INT_J1J2_D194_T90_PSI98_H525, B4INT_J1J2_D196_T90_PSI97_H525, B4INT_J1J2_D196_T90_PSI98_H525。
- CP 约定：R=(Ex-iEy)/sqrt(2)，L=(Ex+iEy)/sqrt(2)；负 DoCP_RminusL 表示 L 输出占优。
- 推荐进入 Route B4-2 的候选：`B4INT_J1J2_D194_T90_PSI97_H525`。下一阶段只对该候选运行 center_x/y、x_plus_qp_x/y、x_minus_qp_x/y，本任务不运行。
