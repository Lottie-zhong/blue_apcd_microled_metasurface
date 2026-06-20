# Stage10 CP Route B4-3 fabrication tolerance periodic plane-wave screen

## English

- Route B4-3; CP-APCD J1/J2 dimer branch only.
- Finite-patch dipole FDTD: not run. No source-position cases were run.
- Tolerance screening follows the integer freeze because quantized coordinates do not guarantee robustness to placement, rotation, or critical-dimension errors. Periodic plane-wave screening limits the later finite-patch tolerance workload.
- Nominal reused from B4-1: DoCP=-0.993259629255, L_fraction=0.996629814627, IL_Rin=0.952912148973, R-input IL/IR ratio=295.719583476.
- Tolerance cases tested: 14; pass=13, fail=1.
- Included: +/-2 nm individual J1/J2 x/y offsets, +/-1 deg individual rotations, and optional uniform +/-2 nm size tolerance.
- CP chain: periodic zeroth-order complex J_xy from x/y inputs, converted to calibrated +z R/L basis; T_output,input.

### Worst three tolerance cases

| rank | case | type | DoCP | L fraction | IL/nominal | target/opposite | x-bias nm | pass |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | TOL_SIZE_ALL_P2 | uniform_size | -0.964393079751 | 0.982196539876 | 0.2547 | 55.1688566725 | 0 | no |
| 2 | TOL_SIZE_ALL_M2 | uniform_size | -0.980736140028 | 0.990368070014 | 1.01587 | 102.821352674 | 0 | yes |
| 3 | TOL_J1_YP2 | relative_y_offset | -0.991950055932 | 0.995975027966 | 1.00028 | 247.448931221 | 0 | yes |

- +/-2 nm position errors preserve strong plane-wave CP: yes.
- +/-1 deg rotation errors preserve strong plane-wave CP: yes.
- Uniform size tolerance was included. Worst size case `TOL_SIZE_ALL_P2` pass=no; its low IL_Rin ratio makes it the first B4-4 risk case.
- Route B4-4 recommendation: reuse nominal B4-2, then finite-patch minimal x-line for `TOL_SIZE_ALL_P2` (critical size case), `TOL_J1_YP2` (worst position case), and `TOL_J1_ROT_M1` (worst rotation case). Do not run B4-4 here.

## 中文

- 本任务是 Route B4-3，只处理 CP-APCD J1/J2 dimer 支线。
- 没有运行 finite-patch dipole FDTD，也没有运行源位置 case。
- 整数冻结不等于对放置、旋转和 CD 误差鲁棒，因此需要先做周期平面波容差筛选，以限制后续 finite-patch 容差工作量。
- nominal 复用 B4-1：DoCP=-0.993259629255，L_fraction=0.996629814627，IL_Rin=0.952912148973，R-input IL/IR ratio=295.719583476。
- 共测试 14 个容差 case；通过=13，失败=1。
- 已包含：J1/J2 单独 x/y +/-2 nm 偏移、单独旋转 +/-1 deg，以及可选的整体尺寸 +/-2 nm 容差。
- +/-2 nm 位置误差是否保持强平面波 CP：是。
- +/-1 deg 旋转误差是否保持强平面波 CP：是。
- 已包含整体尺寸容差。最危险 size case `TOL_SIZE_ALL_P2` 通过状态=no；其 IL_Rin 保留率低，因此是 B4-4 首要风险 case。
- Route B4-4 推荐：复用 nominal B4-2，对 `TOL_SIZE_ALL_P2`（关键尺寸）、`TOL_J1_YP2`（最危险位置）和 `TOL_J1_ROT_M1`（最危险旋转）运行最小 x-line。本任务不运行 B4-4。
