# Stage10 CP Route B2 D195/T90 finite-patch x_plus_qp rescue test

## English

- Route: B2. Candidate tested: RB1_J1J2_D195_T90_PSI97p5_H525 only.
- Finite-patch cases run/reused: x_plus_qp_x and x_plus_qp_y only. No center, no x_minus_qp, no broad sweep, no y-offset, no DBR/RCLED, no K=6, no steering.
- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); negative DoCP_RminusL means L-output dominant.
- Powers are farfieldvector3d cone metrics. x/y dipole averaging is incoherent power addition only.

### Single-case results

- +/-5 deg: x-orientation DoCP=-0.669829, L_fraction=0.834915, P=1.06645e-12; y-orientation DoCP=-0.692469, L_fraction=0.846234, P=2.10926e-12.
- +/-10 deg: x-orientation DoCP=-0.749354, L_fraction=0.874677, P=5.90707e-12; y-orientation DoCP=-0.546821, L_fraction=0.773411, P=8.86568e-12.
- +/-20 deg: x-orientation DoCP=-0.63654, L_fraction=0.81827, P=2.62871e-11; y-orientation DoCP=-0.188602, L_fraction=0.594301, P=3.10055e-11.

### x_plus_qp x/y incoherent average

- +/-5 deg: DoCP=-0.684866, L_fraction=0.842433, P=3.17571e-12.
- +/-10 deg: DoCP=-0.627807, L_fraction=0.813903, P=1.47727e-11.
- +/-20 deg: DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11.

### Baseline comparison

- +/-20 deg baseline: DoCP=0.0318954, L_fraction=0.484052, P=7.44342e-11.
- +/-20 deg Route B2: DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11.
- Total cone power ratio Route/Baseline at +/-20 deg: 0.7697073005809433.
- Rescue verdict at +/-20 deg: rescued / promising.
- If rescued: next step is D195/T90 center_x/y and x_minus_qp_x/y. If failed: test backup D182p5_T85 x_plus_qp_x/y.

## 中文

- 路线：B2。只测试候选 RB1_J1J2_D195_T90_PSI97p5_H525。
- 有限阵列 case：只运行/复用 x_plus_qp_x 和 x_plus_qp_y。没有 center，没有 x_minus_qp，没有大扫，没有 y-offset，没有 DBR/RCLED，没有 K=6，没有 steering。
- CP 约定：R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)；DoCP_RminusL 为负表示 L 输出占优。
- 这里的功率是 farfieldvector3d cone 指标；x/y 偶极平均只做强度非相干相加。

### 单 case 结果

- +/-5 deg：x 取向 DoCP=-0.669829, L_fraction=0.834915, P=1.06645e-12；y 取向 DoCP=-0.692469, L_fraction=0.846234, P=2.10926e-12。
- +/-10 deg：x 取向 DoCP=-0.749354, L_fraction=0.874677, P=5.90707e-12；y 取向 DoCP=-0.546821, L_fraction=0.773411, P=8.86568e-12。
- +/-20 deg：x 取向 DoCP=-0.63654, L_fraction=0.81827, P=2.62871e-11；y 取向 DoCP=-0.188602, L_fraction=0.594301, P=3.10055e-11。

### x_plus_qp 的 x/y 非相干平均

- +/-5 deg：DoCP=-0.684866, L_fraction=0.842433, P=3.17571e-12。
- +/-10 deg：DoCP=-0.627807, L_fraction=0.813903, P=1.47727e-11。
- +/-20 deg：DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11。

### baseline 对比

- +/-20 deg baseline：DoCP=0.0318954, L_fraction=0.484052, P=7.44342e-11。
- +/-20 deg Route B2：DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11。
- +/-20 deg 总 cone power 比值 Route/Baseline：0.7697073005809433。
- +/-20 deg 救援判断：救回 / promising。
- 如果救回，下一步测试 D195/T90 的 center_x/y 和 x_minus_qp_x/y；如果失败，下一步测试备选 D182p5_T85 的 x_plus_qp_x/y。
