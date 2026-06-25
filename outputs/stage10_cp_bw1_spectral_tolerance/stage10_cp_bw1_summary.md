# Stage10-CP-BW1 narrow-band plane-wave validation

## English

- Candidate: `B4INT_J1J2_D194_T90_PSI97_H525`.
- Scope: CP-APCD metasurface-only periodic plane-wave validation; no DBR, RCLED, MQW, dipole source, finite patch, +/-q cases, tolerance geometry, or optimization.
- Base: B4 integer periodic plane-wave setup logic reused, with only wavelength changed.
- Method: 7 wavelength points, each reconstructed from x/y linear plane-wave runs (14 small periodic FDTD runs unless reused).
- CP convention: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2).
- Physical target: for the current frozen B4INT candidate in the existing Stage10 +z scripts, the calibrated target channel is RCP input -> LCP output, i.e. R_in -> L_out. Therefore BW1 treats R_in_to_L_out as the target channel.  Do not use the older L_in -> R_out wording unless an inspected script proves the opposite convention; here it is reported only as an optional reverse channel.

| wavelength nm | target_cp_power = R_in_to_L_out | same-spin_leakage_power = R_in_to_R_out | conversion_to_leakage_ratio | L_fraction under R_in | DoCP_RminusL | status |
|---:|---:|---:|---:|---:|---:|---|
| 447 | 0.742510027913 | 0.032496678205 | 22.8487977519 | 0.958069165146 | -0.916138330292 | PASS |
| 448 | 0.267805154613 | 0.0294288860722 | 9.10007786078 | 0.90099086227 | -0.80198172454 | BORDERLINE |
| 449 | 0.930748584293 | 0.00632747527474 | 147.096360536 | 0.993247639602 | -0.986495279204 | PASS |
| 450 | 0.952912154469 | 0.00322235011076 | 295.719621306 | 0.996629815057 | -0.993259630114 | PASS |
| 451 | 0.983776288919 | 0.00515829738699 | 190.717249339 | 0.994783985252 | -0.989567970504 | PASS |
| 452 | 1.01332146131 | 0.00880427827538 | 115.094210975 | 0.991386306073 | -0.982772612147 | PASS |
| 453 | 0.925963984022 | 0.0124135309697 | 74.5931182904 | 0.98677128259 | -0.97354256518 | PASS |

### FWHM=6 nm weighted result

- weighted target power: 0.845857543707
- weighted same-spin leakage power: 0.0121034174599
- weighted target/same-spin leakage ratio: 69.8858439369
- weighted L fraction: 0.98589281097
- weighted DoCP_RminusL: -0.971785621939
- worst wavelength: 448 nm (lowest target/same-spin leakage ratio over sampled wavelengths)
- edge ratios 447/450/453 nm: 22.8488 / 295.72 / 74.5931
- CP dominance flips: False
- generated plots: stage10_cp_bw1_target_leakage_power.png, stage10_cp_bw1_ratio.png, stage10_cp_bw1_cp_fraction.png, stage10_cp_bw1_gaussian_weights.png
- Interpretation: if all rows remain PASS, the 447-453 nm metasurface-only response is acceptable for later RCLED FWHM around 6 nm. Narrower 2-3 nm RCLED is not required by BW1 alone; cavity work remains separate.

## Chinese

- 候选：`B4INT_J1J2_D194_T90_PSI97_H525`。
- 范围：只做 CP-APCD metasurface-only 周期平面波验证；没有 DBR、RCLED、MQW、dipole、finite patch、+/-q、容差几何或优化。
- 基础：复用 B4 整数候选周期平面波建模/提取逻辑，只改变波长。
- 方法：7 个波长点，每个波长用 x/y 线偏振重构 CP Jones（若无缓存则共 14 个小周期 FDTD）。
- CP 约定：R=(Ex-iEy)/sqrt(2)，L=(Ex+iEy)/sqrt(2)。
- 物理目标：对当前冻结 B4INT 候选，在现有 Stage10 +z 脚本中校准目标是 RCP input -> LCP output，即 R_in -> L_out。因此 BW1 将 R_in_to_L_out 作为目标通道；旧的 L_in -> R_out 只作为 optional reverse channel。
- FWHM=6 nm 加权 target/same-spin leakage ratio = 69.8858439369，加权 L_fraction = 0.98589281097。
- 最差波长：448 nm；边缘 447/450/453 nm ratio = 22.8488 / 295.72 / 74.5931。
- 若全部为 PASS，则 447-453 nm 对后续 FWHM≈6 nm RCLED 是可接受的；本 metasurface-only 结果本身不要求先收窄到 2-3 nm。
