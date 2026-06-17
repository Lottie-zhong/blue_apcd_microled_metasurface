# Stage10 CP Route B1 d/theta periodic plane-wave scout

## English

- Route: B1, local d/theta scout around the frozen J1/J2 dimer.
- Finite-patch dipole FDTD: not run. No x_plus_qp/x_minus_qp finite-patch cases were run.
- Periodic plane-wave screening: x/y linear inputs were run or reused and converted to the calibrated +z CP basis, R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).
- Candidate count: 12 d/theta candidates; successful/reused periodic linear FDTD files: 24 of 24.
- Why d/theta first: increasing theta toward 90 deg reduces the x projection of J1/J2 separation, which should reduce +q/-q source preference for different Jones-response roles.
- L_fraction relation: L_fraction=(1-DoCP_RminusL)/2. More negative DoCP_RminusL means stronger L-output dominance.
- Baseline plane-wave reference: DoCP_RminusL_for_Rin=-0.9948633822044406, L_fraction_for_Rin=0.9974316911022203, IL_Rin=0.9338176821657366, target/opposite ratio=388.3612644742646.
- Baseline geometry x_bias_abs_nm=62.418676.

### Top candidates

| rank | candidate_id | d | theta | DoCP_RminusL_for_Rin | L_fraction_for_Rin | target L output | target/opposite ratio | x_bias_abs_nm | reason |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | RB1_J1J2_D195_T90_PSI97p5_H525 | 195 | 90 | -0.99255133 | 0.996275665 | 0.929634238 | 267.504297 | 1.19403063e-14 | strong R_in->L_out and reduced x-bias |
| 2 | RB1_J1J2_D182p5_T85_PSI97p5_H525 | 182.5 | 85 | -0.993265751 | 0.996632875 | 1.08222634 | 295.989296 | 15.9059231 | strong R_in->L_out and reduced x-bias |
| 3 | RB1_J1J2_D195_T85_PSI97p5_H525 | 195 | 85 | -0.981537229 | 0.990768614 | 1.10896797 | 107.326099 | 16.9953698 | strong R_in->L_out and reduced x-bias |

- Theta near 90 deg preserving plane-wave function: yes.
- Recommended Route B2 finite-patch test: RB1_J1J2_D195_T90_PSI97p5_H525 with x_plus_qp_x and x_plus_qp_y only; optionally RB1_J1J2_D182p5_T85_PSI97p5_H525 if one backup is desired. Do not run them in B1.

## 中文

- 路线：B1，围绕 frozen J1/J2 dimer 的局部 d/theta scout。
- 有限阵列偶极 FDTD：没有运行。本任务没有运行新的 x_plus_qp/x_minus_qp 有限阵列偶极 case。
- 周期平面波筛选：运行或复用 x/y 线偏振入射，再转换到校准后的 +z CP 基底 R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)。
- 候选数量：12 个 d/theta 候选；成功/复用的周期线偏振 FDTD 文件：24 / 24。
- 为什么先扫 d/theta：theta 靠近 90 deg 会减小 J1/J2 分离向量的 x 投影，预计降低 +q/-q 对不同 Jones 响应柱的偏置激发。
- L_fraction 关系：L_fraction=(1-DoCP_RminusL)/2。DoCP_RminusL 越负，L 输出占优越强。
- baseline 平面波参考：DoCP_RminusL_for_Rin=-0.9948633822044406, L_fraction_for_Rin=0.9974316911022203, IL_Rin=0.9338176821657366, target/opposite ratio=388.3612644742646。
- baseline 几何 x_bias_abs_nm=62.418676。

### Top 候选

| rank | candidate_id | d | theta | DoCP_RminusL_for_Rin | L_fraction_for_Rin | target L output | target/opposite ratio | x_bias_abs_nm | reason |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | RB1_J1J2_D195_T90_PSI97p5_H525 | 195 | 90 | -0.99255133 | 0.996275665 | 0.929634238 | 267.504297 | 1.19403063e-14 | strong R_in->L_out and reduced x-bias |
| 2 | RB1_J1J2_D182p5_T85_PSI97p5_H525 | 182.5 | 85 | -0.993265751 | 0.996632875 | 1.08222634 | 295.989296 | 15.9059231 | strong R_in->L_out and reduced x-bias |
| 3 | RB1_J1J2_D195_T85_PSI97p5_H525 | 195 | 85 | -0.981537229 | 0.990768614 | 1.10896797 | 107.326099 | 16.9953698 | strong R_in->L_out and reduced x-bias |

- theta 接近 90 deg 是否保持平面波 CP 功能：是。
- 推荐 Route B2 有限阵列测试：优先 RB1_J1J2_D195_T90_PSI97p5_H525，只跑 x_plus_qp_x 和 x_plus_qp_y；如需备选，再考虑 RB1_J1J2_D182p5_T85_PSI97p5_H525。B1 本轮不运行它们。
