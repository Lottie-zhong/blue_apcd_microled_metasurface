# CONTINUATION — COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2

## 恢复规则

后续恢复本任务时，先读本文件，再读同目录下的最终报告、活动 preregistration amendment、差异清单、SHA inventory 和独立 validator。不要依赖聊天历史推断协议或点集。现场 Git HEAD 可能已因本任务提交向前移动，必须先读取实时 git status、branch、HEAD 与 upstream；不得 reset 或清理既存工作区状态。

## Git 与连接检查点

- Host: DESKTOP-NNE313K
- User: dell
- Canonical project root: D:\project\blue_apcd_microled_metasurface
- Worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1
- Branch: work/mdc-np-coupling-ml-v1
- 本轮起始 HEAD: 2f543d7aef1ae6fbadcfe082379400be8be0cdc2
- 起始 upstream 差异: 0 ahead / 0 behind
- 起始工作区有 165 项既存状态；保留无关 dirty/untracked，仅本目录属于本任务提交 allowlist。
- LAN 不可用时本轮通过 NetBird SSH 恢复；不在 continuation 保存凭据。
- 完成后应从 git log 查询本任务提交 SHA；不要假定起始 HEAD 仍是当前 HEAD。

## Authority 与当前科学路线

- 先读 AGENTS.md（项目交接路径若有），本目录最终报告及活动 Amendment 01。
- 几何 authority：reports/coupling/PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1.json，SHA-256 93915ffad1159517895f28e8258d3c2341e371cfab1d139a7872f287b919a31f。
- 32G dataset authority: reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json，SHA-256 0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e。
- Original H1 numeric gate authority SHA-256 8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd。
- Local DOE manifest SHA-256 66fef2027885ac5c479072da3af78b6a5f975b53ef1dc1f6894751c96ee73cd4。
- 保持固定 MDC、237 nm spacer、ordered K6、21 wavelengths、full Cartesian C_hat、独立正值 P_scale、冻结 H2 与原始 conjunctive H1。制造约束 authority 未解决；数值 feasibility 不等于制造批准。
- Official Runner worktree: D:\project\worktrees\blue_apcd_gpu_production_runner_v1; committed HEAD 2a6f515a1d28002bca3c4e30094dbf66e463fb17; READY / one serial slot / no replay / 12 Stage-1 IDs. V2 approvals remain 0. Dirty controlled-admission prototype is not authority; do not write its worktree.
- EXT02 remains BLOCKED_PREENTRY because the official route has no monitor-overlay/second POSTNP plane. This is not a numerical validation failure. Keep current production POSTNP monitor.

## 本任务冻结状态

- Active protocol: REVISED_PREREGISTERED_PROTOCOL_V2_AMENDMENT_01.json, SHA-256 124f6a0ddd65a65b0b4499a6dbfd98f2105d40ee273bfaeba04b28a6591f8f8a。
- Base V2 protocol remains immutable at SHA-256 4a041dfc9b9fd8bbc79edfd792d698d0240163de157144029ad51a41c104f44a。
- Pre-amendment first V2 point set and its protocol, code, manifests and audit are preserved under PREAMENDMENT_01; archive index SHA-256 a8f0fcb2246ca8c40c26206e3f12ecab55eeb5465bc6cf2cdbb59f552ae00db4。
- Final global strata: deep 32, near-boundary nonexact 56, exact boundary 56. Development global 116 has exact 45 / within10 90. Confirmation core27 has exact10 / within10 21; one triple-face stress is separate; all global confirmation28 has exact11 / within10 22.
- New budget is still 128 development +32 confirmation, incorporating frozen local12 +4. Existing32 remains train-only.
- Four geometry-grouped outer folds, each holds 3 local axial +29 global points; inner folds 43/43/42; nested training sizes mean actual geometry counts 32/64/128.
- Only proposed models are RBF KRR and 6-32-32 Cartesian MLP, predicting full 588-coordinate C_hat plus 21 positive P_scale outputs. Total proposed fit budget 281; no fits were run.
- Independent validator passes; response-blind sampler rerun produced identical generated hashes.
- Task counts: solver 0, training 0, P_scale-only 0, new FSP 0, Runner 0, reserve 0. No new geometry enrolled into Runner authority.

## 恢复入口与下一步

Read, in order:
1. COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2.md
2. REVISED_PREREGISTERED_PROTOCOL_V2_AMENDMENT_01.json
3. V2_AMENDMENT_01_DIFF.json
4. GLOBAL_DATASET_CANDIDATES_V2.csv, development/inner/learning-curve manifests, COVERAGE_AUDIT_V2.json
5. validate_global_dataset_design_v2_amendment_01.py
6. SHA256_INVENTORY_V2.json

本任务产物供 Chat 科学评审。不得自动开始 HF、训练、P_scale 拟合、Runner admission 或 monitor 修改；任何求解仍需独立的新授权并先解决 owner enrollment 和 EXT02 monitor dependency。