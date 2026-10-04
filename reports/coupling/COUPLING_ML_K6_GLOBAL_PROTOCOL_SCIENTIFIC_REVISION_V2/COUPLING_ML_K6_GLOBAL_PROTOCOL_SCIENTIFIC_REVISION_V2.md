# COUPLING_ML_K6_GLOBAL_PROTOCOL_SCIENTIFIC_REVISION_V2

## 状态与执行边界

状态：READY_FOR_CHAT_REVIEW。完成了 V1 边界偏置复核、V2 Amendment 01 冻结、全域几何点集重生成、分层覆盖审计及几何/划分验证。这个交付是数据设计与未来评估协议，不是 HF 数据、训练结果或生产准入。

本轮计数：solver entry 0；training fit 0；P_scale-only fit 0；新 FSP 0；Runner invocation 0；reserve launch 0。没有打开任何响应数组或确认响应。生成脚本只从 32G NPZ 读取 case_id 与 ordered_D_nm，并使用几何 authority、local DOE、候选池及排除清单。

## Authority 与 V1 → V2 修订

固定 MDC、237 nm spacer、有序 D1…D6 和现有 K6 plane-wave 合同保持不变。正式候选域为每坐标 100–230 nm、5 nm 离散，共 27 个水平；数值检查对全域网格点均通过，周期相邻净间隙下限为 60 nm，半单元横向余量下限为 30 nm。制造约束 authority 仍未找到，因此这些仅是数值可行性检查，不代表制造批准。

V1 的精确面比例和近边界比例来自响应盲的 32,768 点 Sobol 原始池：12,133/32,768 精确触边，25,527/32,768 距任一面不超过 10 nm；数值约束过滤拒绝 0 点。它们接近离散均匀期望。之后的 maximin 选择却把 V1 全域 144 点推到 112 个精确触边、138 个落在 10 nm 内；开发 116 点为 89/111，确认 28 点为 23/27。由于约束没有拒绝候选，这种富集来自不分边界层的高维 maximin 选择，不能归因于物理过滤。

基础 V2 已把 exact-face 作为显式配额，但首轮几何结果仍有 142/144 点落在 10 nm 边界带；其中 exact-face 为 56。故在生成最终点集前，冻结了独立的 Amendment 01，增加 deep-interior 与 near-boundary nonexact 两层。该改动仅依据几何覆盖审计，没有按响应、误差、效率或预测结果选点。V1 报告、V1→V2 基础差异文件、V2 基础协议及 Amendment 01 前首轮输出均保留原哈希。

离散均匀网格的期望是：任一精确边界面的几何占 36.983%，任一 10 nm 边界带占 77.862%。这作为覆盖参照，不把 maximin 点集伪装成概率抽样或可直接估计域平均风险的随机样本。

## 分层覆盖审计

精确边界指任一 D 坐标为 100 或 230 nm；10 nm 边界带指任一坐标落在 100–110 或 220–230 nm。二维覆盖统计 15 个有序坐标对的离散单元数；粗覆盖统计把每轴切成 3 个等宽区间后占据的 3×3 格数。NN 为坐标欧氏距离除以 130 nm，报告组内最近邻分布。所有旧点和局部点均单独统计。

| 子集 | n | 精确触边 | 10 nm 内 | 15 对唯一单元 min/中位/max | 3×3 格 min/中位/max |
|---|---:|---:|---:|---:|---:|
| 既有 32G | 32 | 25 | 32 | 29 / 31 / 32 | 7 / 9 / 9 |
| 冻结局部轴向开发点 | 12 | 0 | 11 | 5 / 5 / 5 | 1 / 1 / 2 |
| 冻结局部组合确认点 | 4 | 0 | 2 | 2 / 4 / 4 | 1 / 1 / 2 |
| V1 全域开发 | 116 | 89 | 111 | 96 / 102 / 107 | 9 / 9 / 9 |
| V1 全域确认 | 28 | 23 | 27 | 24 / 27 / 28 | 7 / 9 / 9 |
| 基础 V2 首轮开发（修订前） | 116 | 45 | 114 | 96 / 101 / 107 | 9 / 9 / 9 |
| 基础 V2 首轮确认（修订前） | 28 | 11 | 28 | 25 / 27 / 28 | 8 / 9 / 9 |
| Amendment 01 全域开发 | 116 | 45 | 90 | 98 / 104 / 110 | 9 / 9 / 9 |
| Amendment 01 确认核心 | 27 | 10 | 21 | 25 / 26 / 27 | 7 / 9 / 9 |
| 单独边界 stress | 1 | 1 | 1 | 单点，不定义组内 NN | 1 / 1 / 1 |
| Amendment 01 全域确认（含 stress） | 28 | 11 | 22 | 26 / 27 / 28 | 8 / 9 / 9 |
| 全域 deep-interior 层 | 32 | 0 | 0 | 27 / 31 / 32 | 8 / 9 / 9 |
| 全域 near-boundary nonexact 层 | 56 | 0 | 56 | 42 / 48 / 53 | 8 / 9 / 9 |
| 全域 exact-boundary 层 | 56 | 56 | 56 | 49 / 52 / 56 | 9 / 9 / 9 |

V2 最终全域开发点按 D1…D6 的 distinct levels 分别为 27、25、26、25、25、26；全域确认点为 16、18、18、17、15、18。两组每个坐标均覆盖 100–230 nm 全域。全域开发每个坐标对占据 9/9 粗格；确认核心的各投影至少占 7/9 粗格，含 stress 的确认集至少占 8/9。最终 deep 层各轴实际范围为 D1 120–215 nm、D2 115–215、D3 115–215、D4 115–215、D5 115–215、D6 115–215；near 层各轴覆盖 105–225 nm 的边界带内水平；exact 层六轴均包含 100 与 230 nm 面。

各组每轴 distinct levels（D1…D6）：
- 既有 32G：14,18,16,16,15,18。
- 局部轴向 12：3,3,3,3,3,3；局部组合 4：2,2,2,2,2,2。
- V1 开发：24,24,26,25,26,25；V1 确认：17,15,15,15,17,16。
- 基础 V2 首轮开发：26,25,27,27,22,27；首轮确认：14,17,17,16,18,17。
- 最终 V2 开发：27,25,26,25,25,26；最终全域确认：16,18,18,17,15,18。

V2 开发 116 点分层为 deep-interior 26、near-boundary nonexact 45、exact-boundary 45。确认核心 27 点为 deep 6、near nonexact 11、single-face 8、two-face 2；其精确触边 10/27、10 nm 内 21/27，接近离散均匀参照。另有一个三面触边 stress 点独立报告，不并入确认核心域平均解读。全域确认 28 点合计 11 个精确触边、22 个位于 10 nm 内。

候选池是 seed 20261006 的 2^20 个 scrambled Sobol 栅格点，去重后 1,048,453；约束过滤拒绝 0，旧 32G、local16、reserve6、protected25、source-pool48 与 V1 global144 的身份重叠均为 0。点集按 strata 分层 maximin，先纳入 deep，再 near nonexact，再精确单面/交面/stress；并列时按 Sobol 首次出现顺序。与参考点和新点的归一化 maximin 以确定性贪心更新，面组合种子与选择顺序均写入 Amendment 01 与生成脚本。

独立 32,768 点 coverage probe 的归一化最近样本距离中位数/q95：既有32G 为 0.559/0.728；既有32G+新增开发128 为 0.379/0.503；既有32G+全部新增160（仅几何覆盖审计）为 0.363/0.479。全域确认28对全域开发116的归一化距离 min/q05/median/q95/max 为 0.430/0.476/0.510/0.563/0.569。该高维覆盖仍有限； maximin 和分层配额不构成全域泛化或统计代表性证明。

## 模型、划分与学习曲线协议

仅保留两个全域候选：RBF KRR 与 Cartesian MLP。输入是有序六直径，均值/标准差仅由当前训练组拟合；所有 21 个波长响应跟随整组几何划分，不按波长、节点或 patch 随机拆分。

每个几何输出 609 个实数：完整 588 维 Cartesian C_hat（21×7×2）与 21 个 log(P_scale) 目标。完整复数 state 不强制 rank-2 压缩。P_scale truth 必须有限且严格为正；log 统计量仅从训练组得到，反变换为 exp，不加 epsilon、不裁剪。非正标签及非有限、溢出或下溢预测均为失败。损失为按训练组尺度标准化后的 state MSE 与 log(P_scale) MSE 等权。

KRR 仅测试 RBF gamma {1/6,1/3,2/3} 与 ridge {1e-4,1e-2,1} 的 9 种组合。MLP 为 6→32 GELU→32 GELU，两个输出头分别为 32→588 和 32→21，共 21,377 个可训练参数（224+1,056+20,097）；AdamW 学习率 1e-3，weight decay {1e-5,1e-4,1e-3}，seeds 0/1/2，最多 1,000 次 full-geometry 更新，inner patience 50、min_delta 1e-5。超参数只由 outer-train 内几何分组 3-fold inner CV 选择；确认响应不得用于选择。

四个 outer fold 只切分新增 128 个开发几何，每折验证 32 个（3 个局部轴向点、29 个全域点）；既有 32G 永远只作训练。每折训练池为既有32+新增开发96=128 个几何，inner folds 为 43/43/42。学习曲线规模明确表示训练几何数且共享同一 outer validation：
- 32：既有 32G。
- 64：既有32+3 个局部轴向+7 deep+11 near nonexact+11 exact，全为当前 outer-train 内几何；嵌套选择。
- 128：既有32+当前 outer-train 全部新增96（9 local+87 global）。
各 fold 的 preprocessing 只对当次训练子集拟合。每个几何的 21 波长始终保持成组。

冻结 fit 预算 proposal：inner KRR 108 + MLP 108=216；学习曲线 KRR 12 + MLP 36=48；全 160 开发点 final KRR1 + MLP3=4；local affine 的 12 leave-one-axial-out + final1=13；all-in 281 fits，284 ceiling 内剩 3。没有这些拟合在本轮执行。每个全域 fit 同时预测 C_hat 和 P_scale，不单独训练 P_scale。

确认响应读取规则：28 个全域确认点的两个候选及所有 seeds/预测、配置、训练内预处理、评估器、H2 输出文件必须先完整保存并 hash，再一次性打开响应。报告所有 28，分层报告核心27与 stress1，两个候选均应用原始 H1 conjunction；若仅一个达所有适用 gates，只报告数值 attainment，不给予生产准入。看过确认结果后不改模型、loss、阈值、超参数或预测。确认响应若转作开发，必须记录转换并另设新的 sealed set。4 个局部组合点只评估局部 affine，不支持全域结论。

## 物理/运行依赖与限制

旧 32G 曾被多轮研究反复查看，只属开发数据，不计入新增预算，也不进入确认集。12 个轴向点用于 local leave-one-out；4 个组合响应仅在 local affine 冻结后打开。现有 ±5 nm 响应尚无已验证的数值重复性误差供比较；没有数据时不能声称该尺度的响应已可分辨。

正式 Runner 仍是 committed READY、单槽串行、禁止 replay、仅 12 个 Stage-1 IDs。V2 几何未获 owner-authority enrollment，当前 V2 approved=0、canonical FSP=0、case manifest=0。Runner worktree 中未提交的 controlled-admission 改动不是正式准入 authority，本任务未写入该 worktree。每个未来 case 仍需 owner-approved 精确 ID/source manifest、canonical FSP/hash、fresh LOAD-only 与 source/staged parity、不可变 Runner envelope，以及另行明确的 HF 执行授权。LOAD-only setup 证明不等于 Runner 准入，也不等于 solver 后 truth 恢复证明。

EXT02 双空气面仍是 launch dependency，当前为 BLOCKED_PREENTRY，因为 committed Runner 不支持诊断 monitor overlay/第二 POSTNP 平面；这不是数值验证失败。本轮保留生产 POSTNP monitor，不改合同，也未重跑 solver。制造 authority 仍 unresolved。局部 ±5 nm 信号与数值误差的可分辨性仍未知。

V1 既有估算基于 11 个已完成 case tree：中位 668.129 s/case，160 case 串行约 29.7 h，存储约 55 GiB。此处仅沿用 V1 估计，本轮未重新读取日志、测量恢复开销或承诺墙钟时间；实际 launch 要复核 Runner 许可与最近完成日志。

## 交付物与关键 SHA-256

- 基础 V2 preregistration：4a041dfc9b9fd8bbc79edfd792d698d0240163de157144029ad51a41c104f44a
- 冻结 Amendment 01：124f6a0ddd65a65b0b4499a6dbfd98f2105d40ee273bfaeba04b28a6591f8f8a
- Amendment 01 全域/局部点集：596bcc8fd7011cb5ec0c2fc93b9dfe26653ef74720d1bcd4872d3b22e18727c4
- Outer folds：309556978921717151716f20bbb80faf38e9d94bbbf52e27e6ff0a61d44a15ee
- Inner folds：ab8d7d1cf1dc1909b03d15cc43fda7d9a036c50fd66039eed66c6e1495936441
- Nested learning-curve membership：2ad2282e6551520e32644e3335d167f2706dd6a3e250ac75d7358c47fb5706de
- Coverage audit：2af526e487504a3d9485de30f6a7316c0e80bb0517e37d4b1ed9e6ef25437a8e
- Amended generator：4172072e2feabf66d9585cf6f7e36e279ed42cdf8b23284a0126674aaa52c5ef
- Independent validator：ea1f78b92a9ca35eddbb3baf96167964801ce03f60087479b043ad174df7b992
- 首轮 V2 pre-amendment archive inventory：a8f0fcb2246ca8c40c26206e3f12ecab55eeb5465bc6cf2cdbb59f552ae00db4

完整任务目录文件 SHA-256 见 SHA256_INVENTORY_V2.json。恢复入口为本目录 CONTINUATION.md。
