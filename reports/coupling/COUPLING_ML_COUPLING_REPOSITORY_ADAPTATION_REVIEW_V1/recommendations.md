# 最小适配建议（仅供评审，不执行）

## 一个现有 32G 低成本离线方案

评审一个小容量 APCD-native ordered-periodic graph encoder，标签直接用 frozen C_hat，保持独立 P_scale 分支和原 H2/H1；它只测试显式局部几何消息是否让 geometry-to-state mapping 更容易，不声称复制 GNN repo 的近场物理能力。

必须重写：输入以物理 authority 定义 D1…D6 node id/坐标/方向及全局 phase origin；周期边含明确 image shift；输出按固定 order/TE-TM 坐标 inverse-map；所有预处理只在 outer train geometry 拟合。可复用的是已有 32G loader、C0 folds/seeds、冻结训练步数/检查点规则、重建、H2/H1 指标脚本；不能复制没有 license 的 GNN 源码。固定 C0 规模上限，不加候选/seed，不用 wavelength/node 随机拆分。

建议 smoke checks：synthetic permutation-equivariance with inverse mapping、D1…D6 identity preservation、origin/phase convention、周期 seam image shift、输出 shape、梯度连通、geometry LOGO group integrity、原 H2 numerical reconstruction。smoke 通过只表示接口/代数正确。小样本风险显著：独立 N=32，消息传递容量会增加高阶参数交互而可能更难泛化。若 Chat 后续单独批准，预算上限建议为 1 candidate × seeds 0/1/2 × 原 32G LOGO，不扩数据、solver=0；不确定性留在严格外层 OOF。当前不训练、不写接口原型。

## 一个需新增物理数据的后续方案

更后续再考虑 two-sided multiport scattering network：分别为 NP 层与 MDC 层建立同参考面、功率归一化且包含反射的复数通道块，标出方向、偏振、阶、evanescent 截断策略；验证 spacer propagation 和界面模式匹配，再将层间反射迭代/闭环输出与 integrated C_PW 同面校准。SCMT 的 isolated eigenmodes、neff、pairwise C/K 可以作为候选中间量，但要补模式归一化、边界/周期、方向和反射数据。minimum validation 是多个几何与波长下 operator reconstruction→cascade vs integrated C_PW complex parity、功率闭合和原 H2 一致性。需要单独 solver/data budget；不得从现有 eta/T proxy 或单一入射 C_PW 编造层算子。

## 失败模式对应关系（证据级别）

- Geometry-to-state：图消息传递把局部交互作为归纳偏置，机制上与相邻几何相关；在此 32G 上的增益是假设，三仓库未提供 APCD OOF 证据。
- Cross-order relative phase：GNN 场输出保留复数近场原则上比强度输出信息更丰富；不过其标签/相位面不同。SCMT 的复 U/E 保留层内相位，但简化传播不能保证跨七阶相位。都只是假设。
- Amplitude/routing：显式邻接可能帮助几何局域性，routing 实际需要 H2 order powers。没有 C_PW/H1 test 支持能改善 routing。
- P_scale：三个 repo 都没有 APCD P_scale factorization；保持冻结的 KRR 分支是适配边界，预期无帮助。
- Seed ensemble complex mean：相位表示不同会影响 complex averaging，但它们的输出 basis/reference 不一致；不能据此推断 H1 ensemble 改善。

当前证据：HYBRID post-hoc audit 中所有历史 FULL/C0、C1、HYBRID 都仍 FAIL 原 conjunctive H1；C1 amplitude/routing 变化未解决 state、phase tail 和 frozen P_scale。如下表只是指标权重解释，不是新 H1。
