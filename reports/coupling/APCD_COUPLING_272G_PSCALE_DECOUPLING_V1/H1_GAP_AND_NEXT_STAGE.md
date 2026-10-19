# H1与下一阶段科学决策

## 六项回答

1. **NN是否稳定优于ExtraTrees？** 在本次固定开发验证口径下，P(+1)、复数态、TM幅度、Routing与排序有一致改善：三个种子各4/4折功率MAE优于对应ET/Leaf1，共12/12。三种子ensemble功率MAE0.02060 vsLeaf1 0.02849；家族配对CI完全低于0。但P_scale自身更差，未达到全指标优势，也不是未知全空间独立认证。
2. **P_scale误差来源？** 已验证公共波长趋势占主导、几何响应压缩、高P区域低估、log→exp曲率偏差及训练/验证差距。共享多任务竞争、覆盖不足、输入表征是否为唯一主因尚未证实。独立PNet无稳定改善反驳“只要拆头就能解决”的强说法。
3. **功率改善是否部分依赖抵消？** 存在点级抵消与交互；但真P的模态Oracle仍显著更好，且真实P比预测P的最终误差更低，所以主要模态收益真实可见，不能简化成仅靠抵消。所有Oracle单列。
4. **分离P是否稳定获益？** ET/Leaf1使P MAE下降有稳定证据，整链路P+MAE仅再降约1.4–1.6%、家族CI跨0，Top20由0.738降为0.702；不作为正式全面升级。PNet微小功率收益同时P误差更坏、CI跨0，不推荐替代。保留联合NN3作为研究主对照，分离ET作为P误差受控对照；本轮无生产模型安装。
5. **H1还差什么？** 见下方原阈值数值，state、Routing、thresholded absolute order、total-power仍FAIL；absolute order与seed stability PASS。状态门槛为逐几何相对RMSE，不等同于pooled复数NRMSE；不能混口径宣布通过。
6. **下批50G如何采样？** 只建议、不建Job/Entry：24G六维稀疏联合覆盖，10G有功率TM/Routing局部误差与模型分歧（不按最高效率），10G P_scale公共谱形残差/高P极值附近的独立模型分歧与欠覆盖几何，6G分层随机。可在24G中组织约4–6个局部补全案例，优先已有锚点；不得越过总50或虚构现有真值。训练数据上的高P/残差用于理解风险，未计算候选只能用训练模型、覆盖距离与可验证分歧评分，不能用不可获得真值选样。先零求解检查P分歧是否对OOF真误差有信息，若无校准就将其配额回拨几何覆盖/随机。防止P均值收缩模型以低不确定性漏掉峰值区域。

下一优先动作是冻结几何/波长共同趋势与几何残差的轻量P基线，利用现有数据检验（不在本轮另起大型模型工程）；继续以609D+FrozenH2为主，禁止η或P(+1)直接回归取代主线。新50预算必须单独授权。

## 冻结H1数值缺口

|模型/门禁|median / 上限|q95 / 上限|Pearson / 下限|裁决|
|---|---:|---:|---:|---|
|NN3_Joint/state|0.54817 / 0.50000|0.68823 / 0.80000|N/A / N/A|FAIL|
|NN3_Joint/routing|0.09200 / 0.05000|0.12223 / 0.10000|0.80639 / 0.95000|FAIL|
|NN3_Joint/absolute_order|0.03445 / 0.05000|0.05687 / 0.10000|N/A / N/A|PASS|
|NN3_Joint/thresholded_absolute_order|0.52328 / 0.30000|0.71671 / 0.75000|N/A / N/A|FAIL|
|NN3_Joint/total_power|0.26041 / 0.15000|0.76894 / 0.30000|0.91656 / 0.95000|FAIL|
|NN3_Joint/seed_stability|0.00097 / 0.03000|N/A / N/A|N/A / N/A|PASS|
|NN3_Leaf1/state|0.54817 / 0.50000|0.68823 / 0.80000|N/A / N/A|FAIL|
|NN3_Leaf1/routing|0.09200 / 0.05000|0.12223 / 0.10000|0.80639 / 0.95000|FAIL|
|NN3_Leaf1/absolute_order|0.03348 / 0.05000|0.05391 / 0.10000|N/A / N/A|PASS|
|NN3_Leaf1/thresholded_absolute_order|0.51877 / 0.30000|0.73667 / 0.75000|N/A / N/A|FAIL|
|NN3_Leaf1/total_power|0.23295 / 0.15000|0.66706 / 0.30000|0.93312 / 0.95000|FAIL|
|NN3_Leaf1/seed_stability|0.00097 / 0.03000|N/A / N/A|N/A / N/A|PASS|

表格为原H1 authority逐geometry median/q95/Pearson及种子稳定性；没有放宽阈值。即使以后retrospective通过，生产资格仍需原prospective验证条件，不可用本开发OOF自动替代。

DIAG2=1/2,A2HOLD,DOE56HOLD；NEW_FDTD0,NEXT_BATCH_AUTHORIZED0；CVAE与逆向设计继续暂停。
