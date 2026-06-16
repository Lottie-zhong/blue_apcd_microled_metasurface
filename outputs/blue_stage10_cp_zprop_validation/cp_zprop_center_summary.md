# Blue Stage10 CP +z Propagation Center Dipole Validation
## English
- Adapted old scripts: `scripts/stage10_cp_microled_center_dipole_time_convergence.py`, `scripts/stage10_cp_microled_uniform_patch_setup_only.py`, and `scripts/stage10_cp_microled_simplified_gan_clean_setup_only.py`.
- Coordinate change: old +y model used x-z metasurface plane and y pillar height; this +z model uses x-y metasurface plane and z pillar height. Old local/array z coordinates are remapped to y, and pillar rotation axis is changed from y to z.
- Metasurface plane: x-y. Height axis: z. Collection direction: +z.
- Sources: center x-oriented and y-oriented electric dipoles at (x,y,z)=(0,0,-200) nm.
- Monitor: 2D Z-normal top field/power monitors at z=1000 nm.
- New FSP files generated/used: ['outputs\\blue_stage10_cp_zprop_validation\\_saved_fsp\\CP_ZPROP_CENTER_X_T100FS.fsp', 'outputs\\blue_stage10_cp_zprop_validation\\_saved_fsp\\CP_ZPROP_CENTER_Y_T100FS.fsp'].
- farfieldvector3d worked: True.
- x dipole +/-20 deg DoCP_RminusL: -0.5501033081230786. IR=1.5177792521237232e-12, IL=5.229455299842903e-12.
- y dipole +/-20 deg DoCP_RminusL: -0.29432032908625594. IR=1.1849062093054021e-12, IL=2.1732922995764965e-12.
- Incoherent x+y +/-20 deg DoCP_RminusL: -0.4651024958247185. IR=2.7026854614291253e-12, IL=7.4027475994194e-12.
- Next recommended step: inspect the +z outputs and, if the far-field method is stable, repeat only a short time-convergence check before any larger dipole-position sweep.

## 中文
- 改造来源脚本：`scripts/stage10_cp_microled_center_dipole_time_convergence.py`、`scripts/stage10_cp_microled_uniform_patch_setup_only.py`、`scripts/stage10_cp_microled_simplified_gan_clean_setup_only.py`。
- 坐标变化：旧 +y 模型使用 x-z 超表面平面和 y 方向柱高；新 +z 模型使用 x-y 超表面平面和 z 方向柱高。旧局部/阵列 z 坐标映射为 y，柱子旋转轴从 y 改为 z。
- 超表面平面为 x-y，柱高方向为 z，出射/提取方向为 +z。
- 光源：中心 x 取向和 y 取向电偶极子，坐标 (x,y,z)=(0,0,-200) nm。
- Monitor：顶部 2D Z-normal field/power monitor，z=1000 nm。
- 已生成/使用的新 FSP 文件：['outputs\\blue_stage10_cp_zprop_validation\\_saved_fsp\\CP_ZPROP_CENTER_X_T100FS.fsp', 'outputs\\blue_stage10_cp_zprop_validation\\_saved_fsp\\CP_ZPROP_CENTER_Y_T100FS.fsp']。
- farfieldvector3d 是否成功：True。
- x 偶极子的 +/-20 度 DoCP_RminusL：-0.5501033081230786。IR=1.5177792521237232e-12，IL=5.229455299842903e-12。
- y 偶极子的 +/-20 度 DoCP_RminusL：-0.29432032908625594。IR=1.1849062093054021e-12，IL=2.1732922995764965e-12。
- x+y 非相干平均 +/-20 度 DoCP_RminusL：-0.4651024958247185。IR=2.7026854614291253e-12，IL=7.4027475994194e-12。
- 下一步建议：先检查 +z 输出与远场提取是否稳定；若稳定，再做短时间收敛复核，不要直接进入更大位置扫描。
