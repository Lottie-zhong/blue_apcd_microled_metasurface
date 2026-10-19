# 272G复数前向模型轻量改进

同原124个验证几何、原四折与完整局部家族purge，old32保持train-only；λ行不跨几何折；预处理只拟合训练折。四折heldout为32/31/30/31。主MAE按124几何聚合，450nmSpearman按既定折均值。CVAE先按几何数加权再平均两个seed；248条query-seed不是248个独立几何。数据采集曾使用已有开发标签，因此本轮是开发集OOF诊断，不是独立外部测试。

正式主线保持Geometry+λ→29D后组装原609D→FrozenH2。目标588复数实虚数＋21logP_scale不变。Mean/KRR/原ET预测复用；仅增加Balanced与Leaf1两项预注册对照，4折×3seed=24fit，无大型搜索。Balanced对训练TM目标做可逆方差平衡，TE不放大，logP权重下降；Leaf1只改min_samples_leaf3→1，隔离目标尺度与平均效应。

|模型|复数NRMSE|TM幅度RMSE|Routing MAE|相对相位MAE /°|P_scale MAE|η+ MAE|P+ MAE|ρ450|Top20召回|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|Mean|0.942921|0.340356|0.198134|91.042326|0.053090|0.140261|0.043378|NA|NA|
|KRR|0.862413|0.226042|0.109577|63.850078|0.072626|0.121915|0.038966|0.043553|0.297619|
|ExtraTrees|0.768557|0.274781|0.126928|49.708285|0.053431|0.092175|0.029191|0.469040|0.517857|
|Balanced|0.765704|0.272779|0.119042|49.384634|0.058941|0.091038|0.029277|0.407184|0.517857|
|Leaf1|0.754712|0.265680|0.115907|49.219550|0.053121|0.089674|0.028486|0.499227|0.482143|

Leaf1为本轮较好的探索候选，复态NRMSE下降约1.80%，P+MAE下降约2.42%，rho提高至0.4992；但Top20召回由0.5179降到0.4821。因此不替换冻结正式版本、不宣布全面优势。Balanced略改复态但P_scale变差、rho下降，不能把困难全部归因目标尺度。所有5项H1主精度门仍FAIL，三个ET候选seed stability PASS；正式模型资格保持HOLD。

相位主指标沿用既有|C_hat|²权重和近零幅度掩码；另附cosθ|C_hat|²真实模态通量权重的独立补充：baseline48.6679°、Balanced48.3612°、Leaf1 48.2044°。不能将两种权重口径交叉比较。近零TE相位在主掩码下无有效分量，标NA而非声称学会。全部实虚目标仍保留TE。

证据：FORWARD/METRICS_FIXED124.json、24项FIT_LEDGER.json、H1_GATE_SUMMARY.json、逐阶及逐几何CSV；独立重算INDEPENDENT_MODEL_AND_GENERATION_AUDIT.json。大模型检查点保存在远端，不纳入普通Git提交或本地交付下载。

## 科学与执行边界

FAST272G，ML_TRAINING_GRADE，严格数值收敛NOT_CERTIFIED。NEW_FDTD=0；NEXT_BATCH_AUTHORIZED=0；DIAG2=1/2；A2HOLD；DOE56HOLD。无Runner调用或修改、无原生FSP/H5覆盖、无sealed响应访问、无新科学Case/Job/Entry身份。既有Git dirty/staged保留。
