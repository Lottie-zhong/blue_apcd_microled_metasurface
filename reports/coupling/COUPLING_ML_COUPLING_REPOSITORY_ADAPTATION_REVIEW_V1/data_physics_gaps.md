# 数据与物理能力缺口

## 已有监督

冻结 truth 包 dataset_truth_32g.npz 包含 32 个 geometry、21 个 wavelength、7 个 transmitted orders、2 个 polarization 的 complex C_hat，以及独立 P_scale、absolute-order power、eta/modal weights、ordered_D_nm 和 case_id。状态是指定 P_XLIKE 单一入射下的 post-NP +z 输出。它支持 geometry→integrated state 的有限监督，不是完整多端口 scattering operator。

正式 NP feature manifest 暴露 445–455nm 域的 7 个归一化 eta_m_proxy 与 T_proxy。其自身明确不是 complex Jones、多端口、integrated truth 或 MDC×NP 级联标签。它不提供各阶 complex phase。

## 三种路线的必要标签和现有性

| 路线 | 真正需要的标签 | 正式 32G truth NPZ 是否具备 | 判定 |
|---|---|---|---|
| GNN 近场映射 | 固定面/单位下复数局部 E/H 网格，几何与场逐样本配对 | 否 | 需独立确认归档是否有可合法用的原始 monitor；不得由 C_hat 猜局部场 |
| 单柱/局部 SCMT | 各形状 isolated eigenmodes、复 mode fields、neff、模式归一化 | 否 | 新求解/标签；现成 truth 无法识别 Neff 和模态基底 |
| pairwise SCMT C/K | 有序 pair 的 overlap、complex coupling、边界及距离参数 | 否 | 新标签/校准；不能从全局 C_hat 唯一反演局部 C/K |
| local mutual response | 参考面定义的复 local transmission/reflection，背景去嵌、入射归一化 | 否 | 论文中有方法，固定 repo tree 无训练数据可核验 |
| 多层反馈/cascade | 每层双侧复数 S blocks，通道、功率归一化、spacer propagation phase、界面方向 | 否 | 需要新物理数据与预算；当前没有合法 baseline |
| Integrated truth | 同合同的完整 C_PW 与 P_scale | 是 | 现有 geometry-only supervised task 的唯一直接真值 |

## 数据提取边界

存在 raw E/H 不等于可直接获得局部标签。每种抽取需登记物理面位置、法向、模态基/正交归一化、入射振幅、背景参考与去嵌、x/y 周期和 z PML，验证功率守恒、方向符号、复数 round-trip 与对 integrated C_PW 的一致性。若想从一次 integrated solve 抽取 local response，还要证明该定义对相邻结构/边界不变；否则它不是可迁移的单元标签。

要研究 MDC–spacer–NP 反馈，至少测/算两层各自入射与出射方向的复反射/透射矩阵；仅 transmission t 或 standalone NP eta/T proxy 不够。对七阶双极化通道，端口基础必须覆盖需要传播的阶与偏振，必要时记录倏逝模对近场耦合的作用。只在多个块的同一参考面、同归一化和同材料边界下级联，才能与集成 C_PW 比较。

## 当前 baseline 可实施性

Physics-conditioned residual 需要一个已验证的物理 baseline B(x, λ)，其输出须与 C_PW 同 reference plane/normalization、通道顺序及 complex phase convention 一致，并定义 residual C_PW−B。当前没有这样的 B：standalone NP proxies 不是 complex operator，SCMT 仓库没有两侧反馈，mutual repo 没有可审源码/数据。因此标记为“尚不可实施”，不能用该名称代替接口与标签。
