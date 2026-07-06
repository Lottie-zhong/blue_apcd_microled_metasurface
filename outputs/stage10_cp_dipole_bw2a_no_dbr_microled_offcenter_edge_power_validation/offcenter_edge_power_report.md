# Stage10 CP BW2A PSI99 Off-center Edge/Power Validation

## English Summary

Scope: PSI99 only; no-DBR ordinary MicroLED; x_plus_q/x_minus_q only; wavelengths 420/422/453/480 nm.
No DBR, no RCLED, no center-boundary expansion, no y-offsets, no full 2D sweep.
CP basis: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); DoCP_RminusL < 0 means L_out dominance.

- Reused cases: 4
- Newly run cases: 12
- All 20 deg off-center positions pass L_fraction >= 0.60: yes
- Highest off-center usable L_out power at 20 deg: 480.0 nm x_plus_q, usable_L=5.159875e-11, L_fraction=0.764016.
- Best minimum off-center retention at 20 deg: 480.0 nm, min retention=0.693860.
- Near-threshold 20 deg warnings: 2.
- Red edge 480 nm does not fail by CP selectivity.

### 20 deg off-center incoherent rows
- 420.0 nm x_minus_q: L_fraction=0.807158, DoCP=-0.614316, P=5.050766e-11, usable_L=4.076767e-11
- 420.0 nm x_plus_q: L_fraction=0.692800, DoCP=-0.385601, P=3.942826e-11, usable_L=2.731592e-11
- 422.0 nm x_minus_q: L_fraction=0.807755, DoCP=-0.615511, P=5.070960e-11, usable_L=4.096095e-11
- 422.0 nm x_plus_q: L_fraction=0.694915, DoCP=-0.389830, P=4.133742e-11, usable_L=2.872600e-11
- 453.0 nm x_minus_q: L_fraction=0.729470, DoCP=-0.458940, P=6.270693e-11, usable_L=4.574283e-11
- 453.0 nm x_plus_q: L_fraction=0.700648, DoCP=-0.401296, P=5.707814e-11, usable_L=3.999169e-11
- 480.0 nm x_minus_q: L_fraction=0.735892, DoCP=-0.471784, P=6.449845e-11, usable_L=4.746389e-11
- 480.0 nm x_plus_q: L_fraction=0.764016, DoCP=-0.528031, P=6.753625e-11, usable_L=5.159875e-11

### Reuse / run accounting
- Reused: 453:x_minus_q:x, 453:x_minus_q:y, 453:x_plus_q:x, 453:x_plus_q:y
- Newly run: BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_422NM_X_PLUS_Q_XDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_422NM_X_PLUS_Q_YDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_422NM_X_MINUS_Q_XDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_422NM_X_MINUS_Q_YDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_420NM_X_PLUS_Q_XDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_420NM_X_PLUS_Q_YDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_420NM_X_MINUS_Q_XDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_420NM_X_MINUS_Q_YDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_480NM_X_PLUS_Q_XDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_480NM_X_PLUS_Q_YDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_480NM_X_MINUS_Q_XDIP, BW2A_OFFEDGE_BW2_J1J2_D194_T90_PSI99_H525_480NM_X_MINUS_Q_YDIP

## 中文判断

本轮只验证 PSI99 no-DBR 普通 MicroLED 的 x_plus_q / x_minus_q 离轴位置，波长为 420/422/453/480 nm。没有运行 DBR/RCLED，没有做中心边界扩展，也没有做 y-offset 或 2D 扫描。
20 deg 下所有离轴位置均保持 L_out 占优并满足 L_fraction >= 0.60：是。
20 deg 下离轴可用 L_out power 最高的是 480.0 nm x_plus_q。
20 deg 下相对中心保持率最好的是 480.0 nm。
480 nm 红边没有 CP 选择性失败；若有劣化，主要看可用功率/保持率。
后续 RCLED-coupled 验证优先考虑 422 nm 和 453 nm，同时保留 420/480 nm 作为边缘压力点。
