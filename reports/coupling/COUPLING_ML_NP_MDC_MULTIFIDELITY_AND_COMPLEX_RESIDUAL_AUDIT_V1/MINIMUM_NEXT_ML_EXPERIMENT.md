# 最小下一轮 ML 实验提案 — 本轮不执行

建议一个 A/B 成对 KRR development 对照：恰好2个 joint state/P_scale fits，0新HF、0确认响应读取。不得新增 MLP/GNN/polar/hybrid/residual 候选；需后续明确训练授权。

## 固定数据与配置

沿用已有65G的52训练/13验证分组，split seed3208。21个波长随完整 geometry 分组。两臂固定 alpha=0.01、gamma=1/3，来自已有65G配置，不搜索。输出原21×7×2复数 Cartesian state（588个实数）及独立21个 log P_scale，无 PCA。训练组拟合全部输入、目标尺度和 log 统计量；非正 truth、非有限或 exp 溢出显式失败，不加 epsilon、不 clipping、不使用 oracle。

A：6个有序直径。
B：相同直径 + 88个冻结 NP 输出（445…455 nm，每点7个阶 fraction及T_proxy）。固定 source SHA，仅从 geometry 得到；support/OOD 不作输入。

建议预注册 kernel 输入为 zD 与 sqrt(6/88)*zF 的拼接，常数特征列居中为0。该固定分块尺度避免仅因88维数量放大距离；不得依据验证误差改变它。它是后续提案的明确修改，并非声称已有协议已包含此规则。

两臂都预测 full-band 609输出。88个中波段描述符可以作为 geometry 特征，但不能宣称 NP 在440–444或456–460提供响应；不插值、不外推、不补值。保存输入、配置、预处理、预测及实现 SHA。

## 评价与停止

主评价仍为原 full-band H2 与全部 conjunctive H1。另列445–455 nm 的幅值、固定 truth 权重相位、跨阶相对相位及功率归因；不能凭子波段通过宣称原 H1 PASS。

逐 geometry 保留结果，分旧8/局部1/全域4，报告 median/q95/worst、paired win/loss、state与routing、训练/验证落差。小组均值不能证明泛化，单 KRR 不证明 MLP seed stability。

使用2 fits而不直接拿历史A作匹配，是为统一新输入预处理、实现与输出协议；历史A仍保留。该预算是未来独立诊断提案，不计入或改动正式V2的281 fits。

若无完整state/phase收益则停止，不自动追加常数MDC的C/D fits或E residual。若有价值，先冻结候选与协议，再依原封存规则进行独立确认评审。旧开发验证已有历史暴露，不能当独立确认。所有生产依赖和数值重复性缺口继续保留。
