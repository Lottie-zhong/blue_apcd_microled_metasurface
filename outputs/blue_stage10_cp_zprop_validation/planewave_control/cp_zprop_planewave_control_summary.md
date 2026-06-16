# +z Plane-Wave CP Handedness Control

## English

- Empty-cell handedness check passed: True.
- R input remains R-dominant without metasurface: True (DoCP_RminusL=1.0).
- L input remains L-dominant without metasurface: True (DoCP_RminusL=-1.0).
- Therefore the current +z extraction convention does not flip handedness in free propagation.

### Frozen Dimer CP Power Table

| input | IR_out | IL_out | DoCP_RminusL | dominant output | dominant/opposite ratio |
|---|---:|---:|---:|---|---:|
| R | 0.0024045077807383066 | 0.9338176821657366 | -0.9948633822044406 | L | 388.3612644742646 |
| L | 0.0013348342342546361 | 0.001902055980869281 | -0.1752366342127949 | L | 1.4249379676206597 |

- Complex amplitudes use T_output,input notation: T_RR=0.048264032052-0.008665505803j, T_LR=-0.502884284866-0.825181845535j, T_RL=0.024996828792-0.026645689794j, T_LL=0.043493072426-0.003226241128j.
- Frozen dimer strongest channel under current +z convention: R input -> L output, power=0.9338176821657366, dominant/opposite ratio=388.3612644742646.
- This is opposite to the earlier plane-wave target wording LCP_in -> RCP_out, so a handedness label flip is present between the earlier convention/geometry naming and the current +z convention.
- The finite-patch dipole result should currently be labeled L-output dominant under the calibrated +z convention, not final device-level RCP/LCP success.
- This is not a diffraction-order APCD steering claim. It is a zero-order periodic unit-cell plane-wave convention control using the complex transmitted field monitor.
- Next step: use this calibrated +z label mapping in the finite-patch dipole analysis; if accepted, run a small 5-position x/y dipole sweep before any full 41-position sweep.

## 中文

- 空单元手性检查是否通过：True。
- 无超表面时 R 输入是否保持 R 占优：True（DoCP_RminusL=1.0）。
- 无超表面时 L 输入是否保持 L 占优：True（DoCP_RminusL=-1.0）。
- 因此当前 +z 提取约定在自由传播中没有翻转手性标签。

### Frozen dimer CP 功率表

| input | IR_out | IL_out | DoCP_RminusL | dominant output | dominant/opposite ratio |
|---|---:|---:|---:|---|---:|
| R | 0.0024045077807383066 | 0.9338176821657366 | -0.9948633822044406 | L | 388.3612644742646 |
| L | 0.0013348342342546361 | 0.001902055980869281 | -0.1752366342127949 | L | 1.4249379676206597 |

- 复数振幅使用 T_output,input 记号：T_RR=0.048264032052-0.008665505803j，T_LR=-0.502884284866-0.825181845535j，T_RL=0.024996828792-0.026645689794j，T_LL=0.043493072426-0.003226241128j。
- 当前 +z 约定下 frozen dimer 最强通道：R 输入 -> L 输出，功率=0.9338176821657366，主导/相反通道比=388.3612644742646。
- 这与此前 LCP_in -> RCP_out 的平面波目标文字相反，说明早期约定/几何命名与当前 +z 约定之间存在手性标签翻转。
- 有限阵列偶极结果目前应标注为：在校准后的 +z 约定下 L 输出占优，而不是最终器件级 RCP/LCP 成功。
- 这不是衍射级次 APCD steering 结论；这里只是基于复数透射场 monitor 的零级周期单元平面波约定校准。
- 下一步建议：把这个 +z 标签映射用于 finite-patch dipole 分析；若接受该约定，再做小规模 5-position x/y 偶极扫描，不要直接跑完整 41-position。
