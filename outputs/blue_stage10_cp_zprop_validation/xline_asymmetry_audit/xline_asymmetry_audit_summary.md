# Stage10 CP +z x-line J1/J2 asymmetry audit

## English

- FDTD run status: no FDTD was run by this audit. The script is read-only with respect to simulation state and does not import or call lumapi.
- Sweep definition: this is an x-axis centerline-only source-position diagnostic. Source y is fixed at 0 nm; source z is -200.0 nm.
- Frozen dimer: DIMER_PAIRA_MAPBA_ROBUST_D182p5_T70_PSI97p5_H525, wavelength 450.0 nm, H=525.0 nm, n=2.6, d=182.5 nm, theta=70.0 deg, psi=97.5 deg.

### J1/J2 definition

- J1: 230 x 100 nm pillar, rotation -7.5 deg about z, center (x,y)=(31.209338, 85.746952) nm. This is the larger Jones-response pillar role / literature element-1 role in the frozen mapping.
- J2: 180 x 90 nm pillar, rotation +37.5 deg about z, center (x,y)=(-31.209338, -85.746952) nm. This is the smaller Jones-response pillar role / literature element-2 role in the frozen mapping.
- Delta from J1 to J2: dx=-62.418676 nm, dy=-171.493903 nm.
- Mirror check: the single dimer is not role-preserving mirror-symmetric under x -> -x. Because J1 and J2 have different Jones-response roles, mirrored source positions can preferentially excite different roles.

### Source positions and distances

- q = 107.976946 nm.
- center source: (0, 0, -200.0) nm.
- +q source: (107.976946, 0, -200.0) nm.
- -q source: (-107.976946, 0, -200.0) nm.
- Geometry estimate: +q is nearer J1; -q is nearer J2; center is equidistant from J1 and J2.

### Patch symmetry

- Patch layout: 7 dimers along x and 3 dimers along y, with a true center dimer at ix=0, iy=0.
- The dimer-center lattice is symmetric, but the repeated non-mirrored J1/J2 motif offsets the physical pillar bounding box slightly from x=0.
- Edge-distance audit: the dimer-center lattice is symmetric, but +q to +x physical edge and -q to -x physical edge differ by about 21.7 nm. This is smaller than the source-to-J1/J2 distance swap, so it is a secondary geometry factor.

### Existing CP results used for context

- center, +/-20 deg: DoCP_RminusL=-0.47167557990093073, L_fraction=0.7358377899504653
- x_plus_qp, +/-20 deg: DoCP_RminusL=0.03189539221049794, L_fraction=0.484052303894751
- x_minus_qp, +/-20 deg: DoCP_RminusL=-0.3801250939389637, L_fraction=0.6900625469694819
- center, +/-5 deg: DoCP_RminusL=-0.6126280083111246, L_fraction=0.8063140041555623
- x_plus_qp, +/-5 deg: DoCP_RminusL=0.055557640429547105, L_fraction=0.47222117978522643
- x_minus_qp, +/-5 deg: DoCP_RminusL=-0.45600354433368234, L_fraction=0.7280017721668411

### Likely explanation

The observed +q/-q CP asymmetry is most consistent with J1/J2 excitation-weight asymmetry. A finite patch physical-edge asymmetry exists because the same non-mirrored motif is repeated, but its x-edge distance difference is modest compared with the direct source-to-J1/J2 distance swap. A source-coordinate bug is unlikely from this static audit because y=0 is fixed and the +/-q source coordinates are symmetric.

### Recommendation

Before DBR/RCLED or wider source maps, the next minimal diagnostic should focus on J1/J2 excitation-weight sensitivity. A low-cost next FDTD option, if needed, is a one-case continuation along the x centerline such as x_plus_2qp_x or a controlled mirrored-role/frozen-dimer diagnostic, but not y-offset or full-plane sweeps.

## 中文

- FDTD 状态：本审计没有运行 FDTD。脚本只读已有脚本/CSV/JSON，并且不导入或调用 lumapi。
- 扫描定义：这是 x 轴中心线源位置诊断。source y 固定为 0 nm，source z = -200.0 nm。
- frozen dimer：DIMER_PAIRA_MAPBA_ROBUST_D182p5_T70_PSI97p5_H525，波长 450.0 nm，H=525.0 nm，n=2.6，d=182.5 nm，theta=70.0 deg，psi=97.5 deg。

### J1/J2 定义

- J1：230 x 100 nm 功能柱，绕 z 轴旋转 -7.5 deg，中心坐标 (x,y)=(31.209338, 85.746952) nm。它是当前 frozen mapping 中较大的 Jones 响应功能柱 / 文献 element-1 角色。
- J2：180 x 90 nm 功能柱，绕 z 轴旋转 +37.5 deg，中心坐标 (x,y)=(-31.209338, -85.746952) nm。它是当前 frozen mapping 中较小的 Jones 响应功能柱 / 文献 element-2 角色。
- 从 J1 到 J2 的位移：dx=-62.418676 nm，dy=-171.493903 nm。
- 镜像检查：单个 dimer 在 x -> -x 下不是保持 J1/J2 角色不变的镜面对称结构。由于 J1/J2 是不同 Jones 响应角色，镜像源位置可能更强激发不同功能柱。

### 源位置和距离

- q = 107.976946 nm。
- center source：(0, 0, -200.0) nm。
- +q source：(107.976946, 0, -200.0) nm。
- -q source：(-107.976946, 0, -200.0) nm。
- 几何估计：+q 更靠近 J1；-q 更靠近 J2；center 到 J1/J2 等距。

### patch 对称性

- patch：x 方向 7 个 dimer，y 方向 3 个 dimer，在 ix=0, iy=0 有真实中心 dimer。
- dimer 中心格点是对称的，但由于重复使用未镜像的 J1/J2 motif，物理柱整体 bbox 相对 x=0 有轻微偏移。
- 边界距离审计：dimer 中心格点是对称的，但 +q 到 +x 物理边界与 -q 到 -x 物理边界相差约 21.7 nm。这个差异小于 source 到 J1/J2 距离互换的量级，因此是次要几何因素。

### 已有 CP 结果背景

- center, +/-20 deg：DoCP_RminusL=-0.47167557990093073, L_fraction=0.7358377899504653
- x_plus_qp, +/-20 deg：DoCP_RminusL=0.03189539221049794, L_fraction=0.484052303894751
- x_minus_qp, +/-20 deg：DoCP_RminusL=-0.3801250939389637, L_fraction=0.6900625469694819
- center, +/-5 deg：DoCP_RminusL=-0.6126280083111246, L_fraction=0.8063140041555623
- x_plus_qp, +/-5 deg：DoCP_RminusL=0.055557640429547105, L_fraction=0.47222117978522643
- x_minus_qp, +/-5 deg：DoCP_RminusL=-0.45600354433368234, L_fraction=0.7280017721668411

### 可能原因

当前 +q/-q CP 非对称最符合 J1/J2 激发权重非对称。由于重复未镜像 motif，有限 patch 的物理边界确实有轻微 x 偏心，但它的边界距离差小于 source 到 J1/J2 距离互换的量级。静态审计下源坐标 bug 不太可能，因为 y=0 固定且 +/-q 坐标对称。注意这只是几何估计，不是新的 FDTD 结果。

### 下一步建议

在进入 DBR/RCLED 或更大源位置图之前，建议先围绕 J1/J2 激发权重敏感性做最小验证。如果还需要一个低成本 FDTD，建议仍沿 x 中心线一次只补一个 case，例如 x_plus_2qp_x，或者做受控的镜像角色/frozen-dimer 诊断；不要进入 y-offset 或 full-plane sweep。
