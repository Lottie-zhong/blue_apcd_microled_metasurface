# COUPLING_ML_COUPLING_REPOSITORY_ADAPTATION_REVIEW_V1

审查日期：2026-10-03。审查对象是三个固定 commit 的只读源码与公开论文；未执行第三方代码、训练、仿真或数据集下载。结论用于研究适配评审，不构成模型或生产准入。

## STATUS

源码适配审查完成。GNN 源码展示了“局部几何图→近场复数场”的实现；Meta_SCMT 展示了单层、单向传播的局部模耦合近似；mutual-coupling 项目仓库没有可审查训练代码或可直接获取的数据。三者都不能直接替换当前 integrated C_PW/H2 路径，也没有证据证明可以消除当前 H1 失败。

## AUTHORITY / GIT

主 worktree 为 D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1，分支 work/mdc-np-coupling-ml-v1，审查起始 HEAD 46ac79c8edcf684352d3f98a7558d1109a85a882，与指定 HEAD 一致，upstream ahead/behind 为 0/0。正式 authority 与此前 continuation/HYBRID audit 在报告索引中逐文件列出。审查期间第三方源代码位于 worktree 外部隔离缓存，项目提交仅含本目录的八个审查记录文件。

## ZERO-SOLVER / ZERO-TRAINING

本任务没有启动 FDTD、GPU Runner、HF、reserve、逆向搜索或第三方 solver；没有执行模型 fit、训练或任何第三方仓库代码；没有下载第三方数据集。只对已有预测、truth schema、已保存的 H2/H1 审计结果作只读复核。

## REPOSITORY SHAs / LICENSES

- GNN-for-Metasurfaces：commit 6c1d0d1e4aef5b99d24a95ca52c9060fcd2f0b55，获取日期 2026-10-03。审查时 Git tree 未发现 LICENSE/COPYING，代码可读但不得据此推定可复制或改编。匹配论文 Khoram et al., ACS Photonics 10(4), 892–899 (2023), DOI 10.1021/acsphotonics.2c01019。仓库标题/README 描述和论文标题不完全相同；本审查把论文作为机制解释来源、固定 commit 源码作为实现证据。
- Meta_SCMT：commit 01dafb45534835b004f1b009fa4a6280dec181e7，获取日期 2026-10-03，仓库含 MIT license。论文 Wu et al., “Inverse design of dielectric metasurface by spatial coupled mode theory,” arXiv:2304.00603。源码可在 MIT 条款范围内评估复用，仍须保留许可文本和检查具体依赖许可。
- Metasurface-mutual-coupling：commit 92864f297a5e95d4548bcc4aff002d29a695214c，获取日期 2026-10-03。未发现仓库 LICENSE/COPYING，不能默认复制。论文 An et al., Advanced Optical Materials 10, 2102113 (2022), DOI 10.1002/adom.202102113。公开 Git tree 只有 README、dataset README 与图片；没有可审查训练源码或 dataset 数组。

完整文件级源码 SHA-256 在 evidence_index.json 和外部缓存的 source_snapshot_manifest.json。没有星数或 README 宣称被用作实现证明。

## SOURCE-VERIFIED COMPUTATION PATHS

### GNN-for-Metasurfaces

**README/论文宣称：** 用 GNN 建模散射单元间耦合并处理 varying-size metasurface；论文解释了局部图网络与近场重建的思路。**固定 commit 实现：** dataset/data_maker.ipynb 中的目标是平面波激发下的复数电场面数据；输入包括 TiO2 柱几何和边界上下文。training/pol3_code.py 将柱作为图节点，节点含 R、H、dx、dy、boundary 等特征；按半径/邻域上限生成局部邻接，并取固定尺寸局部窗口。training/model_p3.py 将节点隐变量经 DGL message passing 更新，消息含节点状态和位置；聚合使用距离权重，之后把图输出映射为网格特征并由 CNN 重建场面。预测量是六个分量的实/虚场网格面，不是 diffraction-order TE/TM complex modal coordinate、单元 S 矩阵或 C_hat/P_scale。loss 是近场实/虚场误差；训练脚本还包含按 field panel 文件和 patch 随机划分。inverse_design/inverse_design.py 将预测近场作传播/强度评估并优化几何。源码实际有图层对节点数/邻域作一定泛化，但固定网格窗口、CNN 输出尺寸和边界特征限制“任意 varying size”范围；它不是对任意尺寸都已验证的物理保证。

**适配推断：** 可借鉴消息传递表达几何相互作用，但必须重写 APCD 的输入/读出、周期拓扑、相位参考及 LOGO 划分。图节点置换等变性只保证一致重编号下的函数性质；不能丢弃 D1…D6 身份、物理位置或输出坐标顺序。

### Meta_SCMT

**README/论文解释：** 局部本征模与空间耦合模传播，之后自由空间传播并优化焦点/强度。**固定 commit 实现：** simulator.py/simulator_lam.py 调用 Tidy3D 对孤立有限横向盒中的 waveguide 单元求本征模，modes2D.py 提取场与有效折射率；fitting_neffs.py、fitting_E_field_2D.py、fitting_C_matrix_2D.py 和 fitting_K_matrix_2D.py 构造/缓存 Neff、模场与 pairwise coupling 的拟合器。C 来自横向模场 E/H overlap，K 来自介电扰动 overlap。SCMT_2D.py/SCMT_model_2D.py 按输入单元生成模态入射幅度 U0、Neff/C/K，再用矩阵传播，核心形式为 U(z)=exp(i C^-1(k Neff C+K)z)U0（代码亦有 Euler 选项），从局部模态重建复近场。2D 实现限制为单模，耦合邻域数在实现中固定；邻接在有限边界裁剪而非周期 wrap。free-space 输出路径可以返回强度，因而丢失远场复相位。逆向接口对单层宽度作梯度优化。

**缺失能力：** 未见两侧入/出端口反射与透射 block 的联合网络方程；没有反向传播的闭环求解、MDC-spacer-NP 多次反射、当前 3D periodic FDTD 真值的同参考面归一化对照，也未覆盖 APCD 的七阶双极化 C_PW。论文中的 coupled-mode 解释不等于这些能力已实现。若后续引入 SCMT，须先取得本征模、pairwise coupling 和多端口复数校准标签，并验证其与 integrated C_PW 同参考面。

### Metasurface-mutual-coupling

**README/论文宣称：** 通过邻近单元影响改进单元响应预测。**实际公开仓库：** 只有文档、图和 dataset README；无可检查训练脚本/网络定义，也没有仓库内标签数组。论文方法描述目标单元加 x 向左右邻居窗口（每侧四邻居），以 CST 局部等效源/周期辅助求解与远场探针定义 local complex transmission，再由 CNN 从截面几何像素预测 t 的实部/虚部。该表述是论文证据，仓库无法复核 exact ordering、归一化实现及数据文件。论文采集几何所述折射率与仓库 README 的矩形材料描述存在冲突（README 1.67，论文数据描述 3.67）；不能把其中任一当成 APCD 参数。其一维邻域标签不是完整 3D、七阶、多极化多端口 operator。

## INPUT / OUTPUT / LABEL DEFINITIONS

当前正式 truth authority 的 dataset_truth_32g.npz SHA-256 为 fefc09bbd06d0da06664105540c4f5e0659a51b68b06a07df8c44ed413891d28，包含 32×21×7×2 complex128 C_hat、32×21 P_scale、每阶 power/eta/modal weights，以及 ordered_D_nm/case_id。物理状态为 post-NP、+z、y=0、七个 Floquet orders、TE/TM。这个正式包不含 local E/H 网格、single-pillar eigenmodes、pairwise C/K coupling、两侧多端口复反射/透射 blocks。报告只对正式包作此断言；不推断其他归档是否有可复用监视器数据。

因此：GNN 局部场监督需要场面标签；SCMT 需要孤立柱本征模及 pairwise overlap/coupling；mutual coupling 需要明确参考面和归一化的 local complex response；多层反射网络需要完整的多端口 complex S blocks 和 spacer 传播相位；现成 APCD truth 支持直接监督集成 C_hat 与独立 P_scale，但它只是指定入射状态，不等于完整多端口 operator。Raw E/H 的存在本身也不能授权任意局部标签提取：新增抽取需要固定 monitor/reference plane、入射归一化、模态正交约定、去嵌/背景定义，并通过能量与复数 round-trip 验证。

## POSITION / ORDER / PERIODICITY AUDIT

GNN 源码中的局部坐标/边界编码服务于其 patch 和近场任务；不是 D1…D6 物理槽位或 APCD phase origin。SCMT 的单元位置有序且传播路径依赖位置，但当前邻接是有限边界，不是 K6 torus。节点重编号等变性不允许对物理单元排序或丢弃绝对位置。适配 K6 必须由 authority 提供位置和方向，显式保留 D1…D6 identity、cell origin/cyclic registration 与带 image shift 的跨周期边；读出必须逆映射回同一 physical order。x/y 周期和 z PML 是 solver truth 的边界合同，网络图边不能替代 solver 边界定义。K4/K9 与不同角度要求新输入/标签域，当前源码不提供自动泛化证据。

严格 split 的独立单位为 32 个 geometry group。禁止 wavelength、node、local patch 随机分割；所有波长和节点来自同一 geometry 时必须整体留在同一 outer LOGO fold。GNN 论文/仓库随机 panel/patch split 和 SCMT 设计任务没有当前 32G 的 strict geometry LOGO 协议，不能照搬其 validation 作为 APCD 泛化估计。

## MDC–NP FEEDBACK CAPABILITY

三种被审查方法均未实现 GaN + fixed top MDC + 237nm spacer + ordered K6 NP 的完整双向反馈。GNN 学近场映射没有两层反射端口方程；Meta_SCMT 当前是单层向前传播，不解上下行多次反射；mutual-coupling 只有论文描述的局部复透射标签。Standalone NP 的归一化 eta/T proxy 不是 complex Jones/S operator，不能与 MDC 复数级联。要建立可验证层间反馈 baseline，至少需每层在统一两侧参考面上的复数端口块、偏振/衍射通道归一化、spacer propagation phase 与界面方向约定，并用完整 integrated C_PW 对级联闭环作独立验证。当前资料没有合法的该 baseline，因此 physics-conditioned residual 方案标记为“尚不可实施”。

## 32G ADAPTATION MATRIX

详见 adaptation_matrix.md。整体判断：输入位置和 ordered output、周期邻接、TE/TM 阶坐标及 H2/H1 封装均需要 APCD 专用改写；已有 integrated C_hat/P_scale 可用于有限 geometry-only 的监督研究。分离层级网络或 SCMT 参数不能从当前 truth 直接识别，需新增物理标签。

## SEED-MEAN / METRIC-WEIGHT CLARIFICATION

仅复用 HYBRID audit 已保存的同 fold/seed OOF 预测，没有重新训练、重新选权重或 recompute H1。逐 seed 和 complex seed-mean 指标完整列于 seed_metric_clarification.csv。seed-mean 先平均复预测再算角度，因复数平均和 atan2 非线性而不等于逐 seed 指标平均，也不是额外独立样本。

C0 seed-mean 的 truth-amplitude weighted absolute phase RMSE 为 1.3303 rad，prediction-amplitude weighted 为 0.5144 rad；truth-weighted relative phase 为 1.0891 rad、prediction-weighted relative phase 0.6826 rad。C1 对应 1.4087、1.1529、1.2028、1.1971 rad；HYBRID 为 1.3238、1.1202、1.1040、1.0924 rad。HYBRID 每个单独 seed 的 truth-weighted phase / truth-weighted relative phase 保持 C0 值，因为相位来自 C0；prediction-weighted 指标变动来自 hybrid 振幅权重及 complex seed mean，不能解释为逐坐标相位模型改善。不同权重指标的差异本身说明强弱振幅坐标所占权重不同；phase error 在近零幅值处不能按等权角度解释。

HYBRID audit 的 C0/FULL、C1、HYBRID 仍未通过原始 conjunctive H1：state、routing/eta、absolute-order、thresholded-relative、P_scale/total power 及 seed stability 由原报告逐项保存；P_scale OOF 分支在三方案间相同，不能由 HYBRID 修复。历史 audit 是 post-hoc development comparison，不是独立确认或 production admission。精确逐 fold、seed、几何级证据见报告索引所列 HYBRID 文件。

## MINIMAL RECOMMENDED ADAPTATION

### 低成本、现有标签方案（建议评审，不在本任务执行）

只提出一个 APCD-native、小容量的 ordered-periodic graph baseline：六个图节点严格绑定 D1…D6 authority identity/位置/方向，边用 authority 坐标和周期 image shift 显式编码；保留物理原点与输出 inverse mapping；仅以已有 C_hat 作为完整复数监督目标，P_scale 继续冻结使用原 OOF 分支；网络输出尺寸固定为 [order, TE/TM, wavelength, real/imag]，过原 reconstruction/H2/H1。复用既有 C0/C1 的几何 loader、outer LOGO folds/seeds、训练预算、检查点规则和评价器；容量不超过 C0，不能 random wavelength/node split。GNN 原 repo 仅提供结构概念，不复制无 license 代码。

最小 smoke check（若未来获准）：合成几何验证节点恒为六个且标签 order map round-trip；跨 x/y 边 seam 与 image shift 正确；对节点输入一致置换后 inverse-mapped C_hat 一致；相位原点平移的预期变换显式校验；梯度可到所有输出头；同一 geometry 全波长只进入一个 LOGO fold；一条已有 OOF 样本通过原 H2 重建 parity。通过只证明接口/数值连通，不证明准确性或物理有效。小样本风险仍很高：只有32个独立 geometry group，增加 message passing 容量可能过拟合，单一 candidate 不得搜索超参数。训练/solver budget：0 solver；如果 Chat 后续单独授权，至多一个容量封顶方案×既有3 seeds与固定 LOGO，使用现有数据，不申请新 HF。

### 需要新增物理数据的后续方案（更晚阶段）

在预算审批后为 NP 与 MDC 两个层分别建立统一参考面、入射/出射归一化一致的双侧复数多端口 S blocks，通道覆盖需要的 diffraction orders 和 TE/TM，并记录隔离层的反射/透射相位；补充 spacer 厚度/传播相位和界面模态匹配，构造包含反射迭代的网络级联，再和集成 C_PW 对照。SCMT 的 Neff/mode fields/pairwise C/K 可作为层内近似的候选来源，但需新增标签、检查材料/模式基底及多模/边界假设。只有完整 operator 与集成 truth 在相同参考面、归一化及边界下闭合，才可考虑 residual 或级联。当前 NP proxy、局部场假设与单一入射 C_PW 均不足。该方案需要新 solver/HF/data budget，因此这里只提交评审建议。

## CHECKS / LIMITATIONS

- 只读固定 commit 源码、论文与冻结 APCD artifacts；外部源快照保存在 worktree 外，未放入提交。
- 校验 21 个摘录源文件哈希与 manifest；第三方完整仓库、训练、仿真、安装和大数据集均未执行/获取。
- truth schema 的维度和复数类型由冻结 NPZ 检查；既有 HYBRID seed 数字来自保存的 predictions/results，仅做汇总解释。
- 不把 correlated fold×wavelength×seed 当独立统计样本，不根据相关性声称因果，不把模型机制称为 gate 达标。
- source absence only means absent from the examined pinned Git tree; it does not establish the absence of private files outside that tree.
- 不生成接口原型：源码路径审查已足以确认当前输出/标签不兼容，新增原型不会回答新的适配问题。

## ARTIFACTS / HASHES / COMMIT / PUSH

本目录内的报告、矩阵、缺口清单、推荐、指标 CSV、证据索引、continuation 和 hash 清单由 artifact_hashes.json 逐文件列出 SHA-256。冻结输入路径与 hash 见 evidence_index.json。第三方源快照位置为 D:\project\external_review_cache\COUPLING_ML_COUPLING_REPOSITORY_ADAPTATION_REVIEW_V1\source_snapshots，不属于项目提交。提交/推送结果在本轮终端 final verification 和最终回复记录。

## NEXT — DO NOT EXECUTE

等待 Chat 选择是否批准单一 ordered-periodic graph geometry-to-C_hat 离线 candidate。physics-conditioned residual/层间级联先因多端口复数标签缺失而不可实施。需要层间反馈研究时，先单独评审数据与 solver budget。审查结束后停止。
