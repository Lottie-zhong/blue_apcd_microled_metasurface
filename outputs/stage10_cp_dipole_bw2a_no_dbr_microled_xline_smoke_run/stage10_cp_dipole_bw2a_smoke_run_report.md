# Stage10 CP BW2A no-DBR MicroLED center dipole smoke run

## English
- FDTD smoke run scope: exactly 4 cases from the prepared manifest.
- No +/-q, no 450 nm, no 36-case run, no DBR, no RCLED, no MQW stack change, no top DBR, no bottom mirror, no spacer scan.
- CP extraction uses complex farfieldvector3d Ex/Ey and +z convention R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).
- L_out dominance means DoCP_RminusL < 0 and L_fraction > 0.5.

### 20 deg cone comparison
- PSI99 center x: L_fraction=0.80796, DoCP=-0.615921, P=6.80287e-11
- PSI99 center y: L_fraction=0.681378, DoCP=-0.362757, P=4.25761e-11
- PSI99 x/y incoherent average: L_fraction=0.759234, DoCP=-0.518468, P=1.10605e-10
- PSI97 center x: L_fraction=0.799431, DoCP=-0.598863, P=6.7973e-11
- PSI97 center y: L_fraction=0.685809, DoCP=-0.371617, P=4.20669e-11
- PSI97 x/y incoherent average: L_fraction=0.755995, DoCP=-0.51199, P=1.1004e-10
- PSI99 remains L_out dominant: yes
- PSI99 not significantly worse than PSI97 by 0.6x total-cone-power guard: yes; PSI99/PSI97 power ratio = 1.00513

## 中文
- FDTD smoke 范围：严格只运行 manifest 中 4 个 case。
- 没有 +/-q、没有 450 nm、没有 36-case run、没有 DBR、RCLED、MQW stack change、顶 DBR、底镜或 spacer scan。
- CP 提取使用 complex farfieldvector3d Ex/Ey 和 +z 约定 R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2)。
- L_out 占优表示 DoCP_RminusL < 0 且 L_fraction > 0.5。
- 20 deg cone 下 PSI99 x/y 非相干平均：L_fraction=0.759234, DoCP=-0.518468, P=1.10605e-10。
- 20 deg cone 下 PSI97 x/y 非相干平均：L_fraction=0.755995, DoCP=-0.51199, P=1.1004e-10。
- PSI99 是否保持 L_out 占优：yes。
- PSI99 是否没有显著差于 PSI97：yes；总 cone power 比值 = 1.00513。
