# CP +z Center-Dipole Sanity and Convergence Summary

## English

- +z coordinate setup correct: True. Static checks confirm metasurface plane x-y, pillar height z, pillar rotation axis z, finite patch in x/y, sources below the metasurface at z=-200 nm, and Z-normal monitors above at z=1000 nm.
- Ex/Ey are the correct transverse basis for +z far-field extraction. This report uses R=(Ex-iEy)/sqrt(2) and L=(Ex+iEy)/sqrt(2).
- Negative DoCP_RminusL means the L component is stronger under the current +z convention. Final handedness labeling still needs source-side / reciprocity plane-wave control.
- No 5-position or 41-position sweep was run. No DBR, no K=6 phase gradient, no +10 degree steering, and no frozen-dimer geometry change.

### T100 Grid And Cone Convergence, Incoherent x+y

| time_fs | grid_n | cone_deg | DoCP_RminusL | total_cone_power |
|---:|---:|---:|---:|---:|
| 100 | 31 | 10.0 | -0.5946867520677929 | 2.3184141411064416e-12 |
| 100 | 31 | 15.0 | -0.5386445234196409 | 5.198736536612639e-12 |
| 100 | 31 | 20.0 | -0.4651024958247185 | 1.0105433060848525e-11 |
| 100 | 31 | 25.0 | -0.42306422906126245 | 1.3817919247563911e-11 |
| 100 | 31 | 30.0 | -0.39246465630351224 | 1.7432747496413433e-11 |
| 100 | 61 | 10.0 | -0.5922285309497042 | 9.849865564928069e-12 |
| 100 | 61 | 15.0 | -0.5384812129127888 | 2.1291238426940955e-11 |
| 100 | 61 | 20.0 | -0.47284037708652993 | 3.8055586448370104e-11 |
| 100 | 61 | 25.0 | -0.42531346460568253 | 5.4360677891244455e-11 |
| 100 | 61 | 30.0 | -0.3950861796445315 | 6.905548646688021e-11 |
| 100 | 101 | 10.0 | -0.5923463051135907 | 2.6725571555034168e-11 |
| 100 | 101 | 15.0 | -0.5374019597467412 | 5.953753099365216e-11 |
| 100 | 101 | 20.0 | -0.47167557990093073 | 1.0587216332040106e-10 |
| 100 | 101 | 25.0 | -0.4252735756107699 | 1.5117002484098085e-10 |
| 100 | 101 | 30.0 | -0.3938584794995934 | 1.9190883325111976e-10 |

Grid convergence is stable. At +/-20 deg, incoherent x+y DoCP_RminusL is -0.465102, -0.472840, and -0.471676 for 31, 61, and 101 grids. The sign is unchanged and the 61/101 values agree closely.
Cone-angle dependence is reasonable: widening the cone from +/-10 to +/-30 deg keeps the sign negative while reducing |DoCP| as more off-axis power is included.

### Time Convergence At +/-20 deg, Grid 101

| row_type | case_id | orientation | time_fs | DoCP_RminusL | total_cone_power | status |
|---|---|---|---:|---:|---:|---|
| case | CP_ZPROP_CENTER_X_T100FS | x | 100 | -0.5506352809359792 | 7.126122809302345e-11 | ok |
| case | CP_ZPROP_CENTER_Y_T100FS | y | 100 | -0.3091036866928933 | 3.461093522737762e-11 | ok |
| incoherent_xy | INCOHERENT_XY | x+y | 100 | -0.47167557990093073 | 1.0587216332040106e-10 | ok |
| case | CP_ZPROP_CENTER_X_T150FS | x | 150 | -0.5512368372717531 | 7.138751320324045e-11 | ok |
| case | CP_ZPROP_CENTER_Y_T150FS | y | 150 | -0.30921561458307073 | 3.4546148340550386e-11 | ok |
| incoherent_xy | INCOHERENT_XY | x+y | 150 | -0.47231101767182937 | 1.0593366154379084e-10 | ok |
| case | CP_ZPROP_CENTER_X_T200FS | x | 200 | -0.5515470247916266 | 7.139195390060691e-11 | ok |
| case | CP_ZPROP_CENTER_Y_T200FS | y | 200 | -0.30928166734092055 | 3.453252688075689e-11 | ok |
| incoherent_xy | INCOHERENT_XY | x+y | 200 | -0.4725658968528376 | 1.0592448078136381e-10 | ok |

T150/T200 were run: yes. Four new center-only simulations were run: x/y at T150 fs and x/y at T200 fs.
The x+y averaged DoCP remains meaningfully nonzero and very stable: grid101 +/-20 deg gives -0.471676, -0.472311, and -0.472566 for T100, T150, and T200.
Best current robust estimate for center x+y averaged DoCP: about -0.472 at +/-20 deg using grid101, with |DoCP| about 0.47.

Next recommended step: run a +z plane-wave control / reciprocity convention check before assigning final RCP/LCP handedness. If that passes, the next finite-patch dipole step should be a small 5-position x/y sweep, not the full 41-position sweep yet.

## 中文

- +z 坐标设置是否正确：True。静态检查确认超表面平面为 x-y，柱高为 z，柱子旋转轴为 z，有限阵列沿 x/y 展开，source 位于超表面下方 z=-200 nm，Z-normal monitor 位于上方 z=1000 nm。
- 对 +z 远场提取，Ex/Ey 是正确横向基底。本报告使用 R=(Ex-iEy)/sqrt(2)，L=(Ex+iEy)/sqrt(2)。
- 负的 DoCP_RminusL 表示在当前 +z 约定下 L 分量更强。最终 RCP/LCP 手性标签仍需要源侧 / 互易 plane-wave control 校验。
- 未运行 5-position 或 41-position 扫描；未加 DBR；未做 K=6 相位梯度；未做 +10 度 steering；未改变 frozen dimer 几何。

### T100 网格与 cone 收敛，x+y 非相干平均

| time_fs | grid_n | cone_deg | DoCP_RminusL | total_cone_power |
|---:|---:|---:|---:|---:|
| 100 | 31 | 10.0 | -0.5946867520677929 | 2.3184141411064416e-12 |
| 100 | 31 | 15.0 | -0.5386445234196409 | 5.198736536612639e-12 |
| 100 | 31 | 20.0 | -0.4651024958247185 | 1.0105433060848525e-11 |
| 100 | 31 | 25.0 | -0.42306422906126245 | 1.3817919247563911e-11 |
| 100 | 31 | 30.0 | -0.39246465630351224 | 1.7432747496413433e-11 |
| 100 | 61 | 10.0 | -0.5922285309497042 | 9.849865564928069e-12 |
| 100 | 61 | 15.0 | -0.5384812129127888 | 2.1291238426940955e-11 |
| 100 | 61 | 20.0 | -0.47284037708652993 | 3.8055586448370104e-11 |
| 100 | 61 | 25.0 | -0.42531346460568253 | 5.4360677891244455e-11 |
| 100 | 61 | 30.0 | -0.3950861796445315 | 6.905548646688021e-11 |
| 100 | 101 | 10.0 | -0.5923463051135907 | 2.6725571555034168e-11 |
| 100 | 101 | 15.0 | -0.5374019597467412 | 5.953753099365216e-11 |
| 100 | 101 | 20.0 | -0.47167557990093073 | 1.0587216332040106e-10 |
| 100 | 101 | 25.0 | -0.4252735756107699 | 1.5117002484098085e-10 |
| 100 | 101 | 30.0 | -0.3938584794995934 | 1.9190883325111976e-10 |

远场网格收敛稳定。+/-20 度下，x+y 非相干平均 DoCP_RminusL 在 31、61、101 网格分别为 -0.465102、-0.472840、-0.471676；符号不变，61/101 非常接近。
cone 角度依赖合理：从 +/-10 度扩展到 +/-30 度时，DoCP 符号保持为负，同时 |DoCP| 随纳入更多离轴功率而降低。

### +/-20 度、grid101 时间收敛

| row_type | case_id | orientation | time_fs | DoCP_RminusL | total_cone_power | status |
|---|---|---|---:|---:|---:|---|
| case | CP_ZPROP_CENTER_X_T100FS | x | 100 | -0.5506352809359792 | 7.126122809302345e-11 | ok |
| case | CP_ZPROP_CENTER_Y_T100FS | y | 100 | -0.3091036866928933 | 3.461093522737762e-11 | ok |
| incoherent_xy | INCOHERENT_XY | x+y | 100 | -0.47167557990093073 | 1.0587216332040106e-10 | ok |
| case | CP_ZPROP_CENTER_X_T150FS | x | 150 | -0.5512368372717531 | 7.138751320324045e-11 | ok |
| case | CP_ZPROP_CENTER_Y_T150FS | y | 150 | -0.30921561458307073 | 3.4546148340550386e-11 | ok |
| incoherent_xy | INCOHERENT_XY | x+y | 150 | -0.47231101767182937 | 1.0593366154379084e-10 | ok |
| case | CP_ZPROP_CENTER_X_T200FS | x | 200 | -0.5515470247916266 | 7.139195390060691e-11 | ok |
| case | CP_ZPROP_CENTER_Y_T200FS | y | 200 | -0.30928166734092055 | 3.453252688075689e-11 | ok |
| incoherent_xy | INCOHERENT_XY | x+y | 200 | -0.4725658968528376 | 1.0592448078136381e-10 | ok |

是否运行 T150/T200：是。实际新增运行 4 个 center-only 仿真：T150 的 x/y，以及 T200 的 x/y。
x+y 平均 DoCP 仍明显非零且非常稳定：grid101、+/-20 度下，T100/T150/T200 分别为 -0.471676、-0.472311、-0.472566。
当前最稳健的中心 x+y 平均 DoCP 估计：约 -0.472，取 grid101、+/-20 度，|DoCP| 约 0.47。

下一步建议：先做 +z plane-wave control / reciprocity convention check，再最终标注 RCP/LCP 手性。如果通过，再进入小规模 5-position x/y 扫描，不要直接跑完整 41-position。
