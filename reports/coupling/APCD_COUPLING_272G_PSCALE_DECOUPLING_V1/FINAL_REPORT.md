# APCD_COUPLING_272G_PSCALE_DECOUPLING_V1

## 正式裁决

**零求解研究任务完成PASS；前向代理H1继续HOLD。** 原两种子结果精确复现，补齐三种子后神经网络的模态与目标功率收益仍成立。P_scale误差是独立瓶颈；整链路存在抵消，不能仅按P(+1) MAE选P模型。分离树P显著改善P自身误差，但当前证据不足以证明整链路稳定升级。

## 冻结评价合同与新增训练

合法FAST272G，主评价为原124个几何，四折32/31/30/31；训练折分别216/217/208/217。原old32为train-only，原局部家族connected components保留purge，所有21波长归属同一几何折。所有输入/输出StandardScaler仅拟合训练折，无验证标签作为模型输入。未访问sealed confirmation。

原29D网络为7→64→64→29、tanh、Adam、300epochs、batch256；原17/29两种子八个模型完整复用，本轮仅为每折补seed43。独立PNet为7→32→32→1，目标lnP，三个种子、300epochs；Ridge(alpha1)使用六维几何、中心化波长及其平方，回归lnP；Mean为各波长训练几何的物理P均值。另复用原ET leaf3与Leaf1三个种子P预测。共4个联合NN+12个PNet+4个Ridge轻量fit，无树模型重训、无CVAE训练、无超参搜索。

所有模型为Geometry+λ输入；28Cartesian+lnP组成29D，21λ通过显式Cartesian588+lnP21重组609D。复数态使用Cartesian种子均值，P使用每种子逆log后的物理算术均值。独立P组合共用同一NN3复数态，故复数NRMSE、相位、TM幅度、η完全相同；区别仅来自P。

复数NRMSE为124G pooled SSE/真值能量；MAE为124G×21λ平均；450nm Spearman与Top20为四折均值，Top20每折ceil(20%×n)且延续既有argsort tie口径。相对相位使用同一训练折参考通道、圆周角差和|C_true|²权重；真值振幅低于逐case/λ最大值0.001倍排除，相位近零保护不变。七阶-3…+3、TE/TM、POSTNP1722nm及统一incident phase gauge不变。X/P_XLIKE单入射不构成完整Jones/偏振选择性验证。

误差条为114个原connected局部家族/单例的配对cluster bootstrap，2000次；只描述固定OOF模型条件下的不确定性，不包含重训/选模不确定性。数据获取为自适应开发流程，不是独立外部test。所有候选均列报；根据本轮验证挑选的模型不得称未见数据无偏认证。

## 完整同口径模型对照

|模型|复数NRMSE|TM幅度MAE|Routing MAE|相对相位°|P_scale MAE|P(+1) MAE|450nmρ|Top20召回|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|Leaf1_Joint|0.754712|0.223137|0.115907|49.219550|0.053121|0.028486|0.499227|0.482143|
|ET3_Joint|0.768557|0.232131|0.126928|49.708285|0.053431|0.029191|0.469040|0.517857|
|NN2_Joint|0.574201|0.122936|0.068135|42.694430|0.061272|0.021560|0.679698|0.660714|
|NN3_Joint|0.561037|0.121012|0.066819|40.886741|0.060016|0.020600|0.711677|0.738095|
|NN3_PSNet|0.561037|0.121012|0.066819|40.886741|0.062097|0.020322|0.715916|0.702381|
|NN3_ET3|0.561037|0.121012|0.066819|40.886741|0.053431|0.020316|0.716394|0.702381|
|NN3_Leaf1|0.561037|0.121012|0.066819|40.886741|0.053121|0.020276|0.719181|0.702381|
|NN3_Ridge|0.561037|0.121012|0.066819|40.886741|0.069390|0.021162|0.720253|0.702381|
|NN3_PMean|0.561037|0.121012|0.066819|40.886741|0.053435|0.020644|0.722255|0.702381|

表格中NN2是原17/29seed复核，NN3是补齐43后的新ensemble，明确不混作同一旧结果。Leaf1为前轮0.02849基线，ET3为正式旧leaf3对照。NN3所有分离组合保持同一28D复态，没有真实验证标签作为输入。

## 三种子稳定性

|Seed|基线|NN P MAE|基线 P MAE|NN ρ|基线ρ|NN胜出折数|
|---|---|---:|---:|---:|---:|---:|
|17|Leaf1|0.024652|0.029185|0.58714|0.43761|4/4|
|17|ET3|0.024652|0.029429|0.58714|0.39330|4/4|
|29|Leaf1|0.023013|0.028744|0.68669|0.49642|4/4|
|29|ET3|0.023013|0.029288|0.68669|0.46438|4/4|
|43|Leaf1|0.022476|0.028746|0.71469|0.52698|4/4|
|43|ET3|0.022476|0.029428|0.71469|0.49902|4/4|

每个种子均复用相同折，不能把12个相关折/种子当成12次独立外部实验。三种子NN相对Leaf1功率MAE差-0.007886，114家族bootstrap95%[-0.012027,-0.004432]，四折均改善；相对原ET3同样四折改善。Top20及相位、复数误差见MODEL_FOLD_METRICS.csv，未做best-seed筛选。

## H2解耦与P_scale关键证据

NN3仅模态预测Oracle功率MAE0.01905，只有P预测Oracle0.00840，完整0.02060。Leaf1对应0.02738/0.00743/0.02849，说明NN的收益在消除P误差后仍成立。

逐点误差可抵消：NN3约51.08%的模态/P误差异号；完整误差是两项加乘积，不应简单把B+C的MAE相加。CANCELLATION_POOLED.json保存精确分解、MSE交叉项；H2_ORACLE_DECOUPLING_REPORT.md完整列出A/B/C/D谱形与排序，B/C不是正式模型指标。

分离Leaf1 P把P MAE0.06002→0.05312；组合功率0.02060→0.02028、ρ0.7117→0.7192，但功率增益CI跨0、Top20 0.7381→0.7024。独立PNet把P MAE变为0.06210，不是稳定改善。原冻结H2及609D均不变。

## 冻结H1

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

## 文件与图表

- MODEL_COMPARISON.csv、MODEL_FOLD_METRICS.csv：所有ensemble及seed同口径完整指标。
- H2_ORACLE_DECOUPLING_REPORT.md、ORACLE_COMPARISON.csv、ORACLE_FOLD_METRICS.csv、CANCELLATION_POOLED.json：Oracle和精确误差分解。
- PSCALE_DIAGNOSTIC_REPORT.md、PSCALE_POOLED_DIAGNOSTIC.csv、PSCALE_WAVELENGTH_POOLED.csv、PSCALE_GEOMETRY_DIAGNOSTIC.csv：波长、几何、峰值、方差、系统偏差。
- H1_GAP_AND_NEXT_STAGE.md、H1_NUMERIC_GAPS.csv：科学裁决和下一批建议。
- FIGURES/PSCALE_DECOUPLING_OVERVIEW、PSCALE_AND_POWER_SPECTRA：PDF/SVG/PNG及逐图来源和QA。谱例为联合P误差最低/中位/最高几何，不是选择有利案例。
- PREREGISTRATION、WORKER、FIT_LEDGER、全部训练checkpoint与OOF预测：可复现记录；大模型留远端，不混入Git。
- BOUNDARY_AUDIT、INDEPENDENT_RECONSTRUCTION_AUDIT、GIT_BEFORE/AFTER：边界和对账证据。原生FSP/H5/609D未改，Runner未改，sealed未访问。

## 边界与Git

FAST272，NEW_FDTD0，NEXT_BATCH_AUTHORIZED0；DIAG2=1/2,A2HOLD,DOE56HOLD；CVAE与逆向暂停。canonical117条Solver Entry不变，历史科学账本及原4项staged文件按原字节保留。

branch work/mdc-np-coupling-ml-v1，HEAD2cc687020e90ec4397e6cd4ed31efed59aaaf386，ahead/behind0/0，保留原dirty；未commit/push。完整报告位于正式Coupling worktree reports/coupling/APCD_COUPLING_272G_PSCALE_DECOUPLING_V1。

## 固定训练预算的限制

所有本轮MLP按预注册300轮到达max_iter，sklearn报告ConvergenceWarning；未宣称优化已收敛，未为改善指标额外续训。这是固定轻量预算的模型对照，不能据此断言架构容量上限或充分优化性能。TRAINING_CONVERGENCE_DIAGNOSTIC.json保留各checkpoint末尾loss及迭代数。

## 峰位误差补充

|模型|峰位MAE(nm)|±1nm内比例|最大偏移(nm)|
|---|---:|---:|---:|
|Joint|0.4274|0.9516|4|
|PSNet|0.3629|0.9677|4|
|ET3|0.2823|0.9677|4|
|Leaf1|0.2984|0.9677|4|
|Ridge|0.2823|0.9677|4|
|PMean|0.2823|0.9677|4|

21个已保存波长点直接取argmax，无插值或亚纳米分辨率声称。峰位错配与公共谱形回归失配有证据，但未唯一归因于模型结构或FAST数值标签。
