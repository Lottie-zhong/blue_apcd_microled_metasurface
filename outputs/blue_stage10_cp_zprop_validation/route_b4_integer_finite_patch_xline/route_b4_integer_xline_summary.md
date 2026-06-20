# Stage10 CP Route B4-2 integer finite-patch minimal x-line validation

## English

- Route B4-2; CP-APCD J1/J2 branch only. Candidate: `B4INT_J1J2_D194_T90_PSI97_H525` only.
- Exactly six finite-patch cases were requested and completed/reused: 6/6: center_x/y, x_plus_qp_x/y, x_minus_qp_x/y.
- No y-offset, no 41-position or full-plane sweep, no bare reference, no x_plus/minus_2qp.
- Geometry: J1 center=(0,97) nm, rotation=-7 deg; J2 center=(0,-97) nm, rotation=38 deg; fabrication_integer_ready=true.
- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); negative DoCP_RminusL means L-output dominant. x/y dipoles are combined by incoherent power sums only.

### Position averages

- center: +/-5 deg DoCP=-0.578086, L_fraction=0.789043, P=6.93696e-12; +/-10 deg DoCP=-0.576592, L_fraction=0.788296, P=2.84645e-11; +/-20 deg DoCP=-0.501405, L_fraction=0.750703, P=1.11145e-10.
- x_plus_qp: +/-5 deg DoCP=-0.670297, L_fraction=0.835148, P=3.17496e-12; +/-10 deg DoCP=-0.618141, L_fraction=0.809071, P=1.48122e-11; +/-20 deg DoCP=-0.390625, L_fraction=0.695313, P=5.7447e-11.
- x_minus_qp: +/-5 deg DoCP=-0.606181, L_fraction=0.803091, P=3.78666e-12; +/-10 deg DoCP=-0.475546, L_fraction=0.737773, P=1.64692e-11; +/-20 deg DoCP=-0.436845, L_fraction=0.718423, P=6.0706e-11.

### D195 physical-reference comparison at +/-20 deg

- center: reference DoCP=-0.504043, L_fraction=0.752021, P=1.11085e-10; integer DoCP=-0.501405, L_fraction=0.750703, P=1.11145e-10; power ratio=1.00054.
- x_plus_qp: reference DoCP=-0.394126, L_fraction=0.697063, P=5.72926e-11; integer DoCP=-0.390625, L_fraction=0.695313, P=5.7447e-11; power ratio=1.0027.
- x_minus_qp: reference DoCP=-0.438505, L_fraction=0.719253, P=6.04762e-11; integer DoCP=-0.436845, L_fraction=0.718423, P=6.0706e-11; power ratio=1.0038.
- Route B4-2 minimal x-line result at +/-20 deg: PASS; min L_fraction=0.695313.
- Decision: freeze D194_T90_PSI97 as the fabrication-aware CP candidate and move to tolerance tests, not more ideal optimization.
- Cone powers are API-normalized extraction metrics, not independently validated absolute LEE.

## 中文

- 本任务是 Route B4-2，只处理 CP-APCD J1/J2 支线，只测试 `B4INT_J1J2_D194_T90_PSI97_H525`。
- 严格请求并完成/复用 6 个有限阵列 case：6/6，即 center_x/y、x_plus_qp_x/y、x_minus_qp_x/y。
- 没有 y-offset、41 点或完整平面扫描、bare reference、x_plus/minus_2qp。
- 整数几何：J1 中心=(0,97) nm、旋转=-7 deg；J2 中心=(0,-97) nm、旋转=38 deg；fabrication_integer_ready=true。
- x/y 偶极只做功率非相干相加。负 DoCP_RminusL 表示 L 输出占优。

### 位置平均

- center: +/-5 deg DoCP=-0.578086, L_fraction=0.789043, P=6.93696e-12；+/-10 deg DoCP=-0.576592, L_fraction=0.788296, P=2.84645e-11；+/-20 deg DoCP=-0.501405, L_fraction=0.750703, P=1.11145e-10。
- x_plus_qp: +/-5 deg DoCP=-0.670297, L_fraction=0.835148, P=3.17496e-12；+/-10 deg DoCP=-0.618141, L_fraction=0.809071, P=1.48122e-11；+/-20 deg DoCP=-0.390625, L_fraction=0.695313, P=5.7447e-11。
- x_minus_qp: +/-5 deg DoCP=-0.606181, L_fraction=0.803091, P=3.78666e-12；+/-10 deg DoCP=-0.475546, L_fraction=0.737773, P=1.64692e-11；+/-20 deg DoCP=-0.436845, L_fraction=0.718423, P=6.0706e-11。
- +/-20 deg 最小 x-line 鲁棒性：通过；min L_fraction=0.695313。
- 决策：冻结 D194_T90_PSI97 为加工友好 CP 候选，下一步进入容差测试，不继续理想参数优化。
- cone power 是 API-normalized extraction metric，不是独立验证的绝对 LEE。
