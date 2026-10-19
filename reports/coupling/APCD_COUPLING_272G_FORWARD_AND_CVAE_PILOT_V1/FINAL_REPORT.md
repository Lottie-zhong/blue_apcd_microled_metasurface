# APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1

## 状态

离线试验完成PASS；前向正式H1资格HOLD；CVAE为探索可行、可靠逆向未证明。

## 1. TM收缩诊断

原始目标根方差约69%TM、31%logP，TE不主导损失。单个32G折／种子中每树norm≈1，跨树复数平均后≈0.457，收缩有直接模型证据；不把它简单归结为目标尺度或叶内平均。单位norm投影不能改善H2Routing。详见TM_AMPLITUDE_SHRINKAGE_DIAGNOSTIC_REPORT.md。

## 2. 复数前向改进

原B29ET→Leaf1：complexNRMSE0.76856→0.75471，TM模长RMSE0.27478→0.26568，RoutingMAE0.12693→0.11591，P+MAE0.029191→0.028486，ρ450：0.4690→0.4992；Top20召回0.5179→0.4821。收缩仍严重（TM方差仅真值14.18%），全部H1主精度门FAIL；不能宣称模型达到逆向设计精度。

## 3–5. CVAE训练、合法性与条件基线

小64/32网络、latent3、4折2seed、8×400epoch，CPU-only。Posterior重建26.30nm，非prior生成误差；KL3.36、8/8三个latent活跃。3968个CVAE候选唯一且与272G不重复，合法率100%由投影保证。固定16候选同checker：CVAE代理条件误差0.60064，随机0.64244，库检索0.27980。条件打乱8/8更差，支持条件依赖但无新几何真值。详见CVAE_PILOT_VERDICT.md及CVAE完整训练报告。

## 6. 是否继续CVAE

仅保留低成本探索，暂不增加复杂度、不作为主选样器。已知库中按真值检索误差0.21676，代理再选变成0.32657，说明checker尚不足以认证生成结构。正式主线依然Geometry+λ→ComplexFloquet+P_scale→FrozenH2，不是直接η回归，也不是可靠逆向生产。

## 7. 下一批数据

建议先零求解修复幅度／相位学习及平均问题；未来另授权50G时以28覆盖＋10响应分歧＋6随机＋6小规模局部组为参考，CVAE主导生产数当前建议0。没有新生产Manifest、科学身份或预算申请。

## 证据与评价口径

同原124个验证几何、原四折与完整局部家族purge，old32保持train-only；λ行不跨几何折；预处理只拟合训练折。四折heldout为32/31/30/31。主MAE按124几何聚合，450nmSpearman按既定折均值。CVAE先按几何数加权再平均两个seed；248条query-seed不是248个独立几何。数据采集曾使用已有开发标签，因此本轮是开发集OOF诊断，不是独立外部测试。

Root独立复算：5模型complexNRMSE、3968/方法的生成合法性、标准化代理条件误差及已知库真值最近邻/代理重排误差全部一致；609D重组与H2解码一致。各报告、24项前向fit ledger、8项CVAE fit ledger和4个固定checker保存在本目录；无需下载远端大型ET joblib。图表仅实际数据，最终QA记录另附。

## 科学与执行边界

FAST272G，ML_TRAINING_GRADE，严格数值收敛NOT_CERTIFIED。NEW_FDTD=0；NEXT_BATCH_AUTHORIZED=0；DIAG2=1/2；A2HOLD；DOE56HOLD。无Runner调用或修改、无原生FSP/H5覆盖、无sealed响应访问、无新科学Case/Job/Entry身份。既有Git dirty/staged保留。


## 最终审计与图表

四组图已完成目视QA，4/4PDF通过、最小7pt；见FIGURE_QA_REPORT.md。117条既有Solver Entry记录逐条一致，NEW_FDTD=0；24前向ET＋4固定checker＋8CVAE训练均CPU，无旧模型重训。原4项staged保留，HEAD不变、ahead/behind0/0，未提交或推送。
