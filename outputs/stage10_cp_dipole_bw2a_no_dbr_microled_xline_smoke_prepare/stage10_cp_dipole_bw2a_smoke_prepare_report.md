# Stage10-CP-DIPOLE-BW2A smoke prepare

## English
- No FDTD was run.
- No .fsp, .ldf, raw monitor data, DBR, RCLED, MQW, top DBR, bottom mirror, spacer scan, +/-q positions, 450 nm case, or full 36-case run was created.
- This helper was copied from the old mixed worktree single helper and narrowed to smoke scope inside the clean CP worktree.
- Smoke scope: 2 candidates x 1 wavelength x 1 center source position x 2 dipole axes = 4 planned cases.
- Candidates: BW2_J1J2_D194_T90_PSI99_H525 and BW2_J1J2_D194_T90_PSI97_H525.
- Wavelength: 453 nm only.
- Source position: center only, x=0 nm, y=0 nm, source_z=-200 nm.
- Dipoles: x and y, to be combined later by incoherent power summation only.
- CP basis for future extraction: R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); target is L-output dominance.
- Setup-only FSP count: 0. Waiting for user approval before actual 4-case FDTD smoke run.

## 中文
- 没有运行 FDTD。
- 没有创建 .fsp、.ldf、raw monitor 数据，也没有加入 DBR、RCLED、MQW、顶 DBR、底镜、spacer scan、+/-q、450 nm 或完整 36-case run。
- 本 helper 从旧 mixed worktree 的单个 helper 复制而来，并在 clean CP worktree 中收窄为 smoke 范围。
- Smoke 范围：2 个候选 x 1 个波长 x 1 个中心源位置 x 2 个偶极方向 = 4 个计划 case。
- 候选：BW2_J1J2_D194_T90_PSI99_H525 和 BW2_J1J2_D194_T90_PSI97_H525。
- 波长：仅 453 nm。
- 源位置：仅 center，x=0 nm，y=0 nm，source_z=-200 nm。
- 偶极：x 与 y，后续只能做功率非相干相加。
- 后续提取 CP 基底：R=(Ex-iEy)/sqrt(2), L=(Ex+iEy)/sqrt(2); target is L-output dominance。
- setup-only FSP 数量：0。等待用户确认后再运行实际 4-case FDTD smoke。
