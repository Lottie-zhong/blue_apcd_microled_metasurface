# Stage10 CP Route B3 D195/T90 minimal x-line validation

## English

- Route: B3. Candidate tested: RB1_J1J2_D195_T90_PSI97p5_H525 only.
- Newly run/reused finite-patch cases: center_x/y and x_minus_qp_x/y. Existing x_plus_qp_x/y is reused from Route B2 and was not rerun.
- No x_plus rerun, no x_plus_2qp/x_minus_2qp, no y-offset, no 41-position sweep, no bare reference, no DBR/RCLED, no K=6, no steering.
- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); negative DoCP_RminusL means L-output dominant.
- x/y dipole averages are incoherent power sums only.

### Position averages

- center: +/-5 deg DoCP=-0.582223, L_fraction=0.791111, P=6.91661e-12; +/-10 deg DoCP=-0.580613, L_fraction=0.790307, P=2.84069e-11; +/-20 deg DoCP=-0.504043, L_fraction=0.752021, P=1.11085e-10.
- x_plus_qp: +/-5 deg DoCP=-0.684866, L_fraction=0.842433, P=3.17571e-12; +/-10 deg DoCP=-0.627807, L_fraction=0.813903, P=1.47727e-11; +/-20 deg DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11.
- x_minus_qp: +/-5 deg DoCP=-0.604914, L_fraction=0.802457, P=3.7692e-12; +/-10 deg DoCP=-0.475826, L_fraction=0.737913, P=1.63939e-11; +/-20 deg DoCP=-0.438505, L_fraction=0.719253, P=6.04762e-11.

### Baseline comparison at +/-20 deg

- center: baseline DoCP=-0.471676, L_fraction=0.735838, P=1.05872e-10; D195/T90 DoCP=-0.504043, L_fraction=0.752021, P=1.11085e-10, power ratio=1.0492382343105555.
- x_plus_qp: baseline DoCP=0.0318954, L_fraction=0.484052, P=7.44342e-11; D195/T90 DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11, power ratio=0.7697073005809433.
- x_minus_qp: baseline DoCP=-0.380125, L_fraction=0.690063, P=7.05843e-11; D195/T90 DoCP=-0.438505, L_fraction=0.719253, P=6.04762e-11, power ratio=0.856793972107349.
- Minimal x-line robustness at +/-20 deg: pass; min L_fraction=0.697063.
- If pass: pause CP finite-patch expansion and prepare a concise stage closeout; test backup D182p5_T85 only if needed. If fail: test backup D182p5_T85 x_plus_qp_x/y.

## 中文

- 路线：B3。只测试候选 RB1_J1J2_D195_T90_PSI97p5_H525。
- 本轮新运行/复用的有限阵列 case：center_x/y 和 x_minus_qp_x/y；x_plus_qp_x/y 复用 Route B2 已有结果，没有重跑。
- 没有重跑 x_plus，没有 x_plus_2qp/x_minus_2qp，没有 y-offset，没有 41-position sweep，没有 bare reference，没有 DBR/RCLED，没有 K=6，没有 steering。
- CP 约定：R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)；DoCP_RminusL 为负表示 L 输出占优。
- x/y 偶极平均只做强度非相干相加。

### 位置平均

- center: +/-5 deg DoCP=-0.582223, L_fraction=0.791111, P=6.91661e-12；+/-10 deg DoCP=-0.580613, L_fraction=0.790307, P=2.84069e-11；+/-20 deg DoCP=-0.504043, L_fraction=0.752021, P=1.11085e-10。
- x_plus_qp: +/-5 deg DoCP=-0.684866, L_fraction=0.842433, P=3.17571e-12；+/-10 deg DoCP=-0.627807, L_fraction=0.813903, P=1.47727e-11；+/-20 deg DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11。
- x_minus_qp: +/-5 deg DoCP=-0.604914, L_fraction=0.802457, P=3.7692e-12；+/-10 deg DoCP=-0.475826, L_fraction=0.737913, P=1.63939e-11；+/-20 deg DoCP=-0.438505, L_fraction=0.719253, P=6.04762e-11。

### +/-20 deg baseline 对比

- center: baseline DoCP=-0.471676, L_fraction=0.735838, P=1.05872e-10；D195/T90 DoCP=-0.504043, L_fraction=0.752021, P=1.11085e-10, power ratio=1.0492382343105555。
- x_plus_qp: baseline DoCP=0.0318954, L_fraction=0.484052, P=7.44342e-11；D195/T90 DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11, power ratio=0.7697073005809433。
- x_minus_qp: baseline DoCP=-0.380125, L_fraction=0.690063, P=7.05843e-11；D195/T90 DoCP=-0.438505, L_fraction=0.719253, P=6.04762e-11, power ratio=0.856793972107349。
- +/-20 deg 最小 x-line 鲁棒性：通过；min L_fraction=0.697063。
- 如果通过：建议暂停 CP 有限阵列扩展，准备简洁阶段 closeout；只有必要时再测试备选 D182p5_T85。如果失败：建议测试备选 D182p5_T85 的 x_plus_qp_x/y。
