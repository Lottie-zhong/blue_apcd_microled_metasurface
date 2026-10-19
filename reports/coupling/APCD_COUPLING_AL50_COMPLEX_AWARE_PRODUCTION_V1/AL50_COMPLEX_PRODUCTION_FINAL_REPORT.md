# AL50 Complex-Aware Production Final Report

生产：PASS；50/50 REAL entry；50/50 labels valid；Replay=0；FAST=272G。

Solver调用累计8.010小时；entry至科学验收累计9.765小时；批次墙钟10.258小时。Solver调用包括load/run/save，不能称为纯GPU核计时。

## 七项科学回答

- A_ExtraTrees：复数NRMSE 0.79530→0.77695；P+MAE 0.033261→0.030440；ρ450 0.4679→0.4803；当前TM幅度MAE 0.239163；预测加权范数均值 0.4503（真值1）。
- B_ExtraTrees：复数NRMSE 0.78579→0.76856；P+MAE 0.031434→0.029191；ρ450 0.4410→0.4690；当前TM幅度MAE 0.232131；预测加权范数均值 0.4553（真值1）。

复数、TM幅度、Routing和收缩是否改善，以MODEL_BEFORE_AFTER、各阶段TM_ROUTING_VARIANCE_DIAGNOSTICS及ORACLE_ERROR_ATTRIBUTION的实际配对差异裁决，不用单一功率指标概括。A/B稳定性按4折、3种子及冻结H1种子门槛比较，不能宣称某结构全面优越。强功率Mean对照在STAGE_50/OUTPUT_DOMAIN_MEAN_REFERENCE.json。

局部真值共31条配对；已有2组加新增2组完整四角实验。新增两组对应old32训练专用锚点，因此不报告泄漏的训练内泛化成绩。沿用G059独立局部测试；非加性还包含归一化非线性，不唯一证明某种近场机制。FAST复数相位数值不确定性未独立闭合，A1的Pscale2.434%不是通用相位误差界。

下一轮仍以六维覆盖为基础，仅按实际误差/分歧关联和局部收益证据调整小部分采样。若H1仍未PASS，前向代理保持HOLD，不用于正式逆向优化。不得把模型未改善当作改合同或自动扩大预算的理由。

## 证据及边界

CASE_RESULTS.csv、NATIVE_ARTIFACT_INDEX.json：逐案FSP/H5/609D、日志、SHA、Job/Entry、时间和收据。Science Ledger与只读Runner记录一一对账；首两案验收先于后案入场。全部数据ML_TRAINING_GRADE；严格收敛NOT_CERTIFIED；制造UNRESOLVED。

DIAG2=1/2；A2 HOLD；DOE56 HOLD；NEXT_BATCH_AUTHORIZED=0。Runner/H1/H2/旧账本和历史原生文件未修改；sealed响应未访问。所有50预算已消耗，本批后停止新增入场。

图表已完成独立目视QA，七组全部通过，PDF最小字号7pt。Git保留原dirty/staged，不自动提交推送。


# Final independent scientific verdict

This evaluation retains formal609D/H1/H2; no directη surrogate, no changed thresholds. All improvements below are observed on the fixed124 geometry protocol, not a prospective independent external test.

## A_ExtraTrees

Complex NRMSE 0.795303 → 0.776945 (2.31% lower); H2 P+MAE 0.0332605 → 0.0304402 (8.48% lower).

TM magnitude MAE 0.237998 → 0.239163; predicted weighted norm 0.4757 → 0.4503, truth1. Magnitude between-geometry variance ratio pred/truth 0.0843 → 0.0931. These directly measure shrinkage; not a physical loss claim.

450nm mean-foldrho 0.4679 → 0.4803; Top20recall 0.5238. P+MAE relative improvement vs strong output-domain constantMean 5.92%. The constant reference is not a deployed directpower model.

Local6 addition conditional on44nonlocal observations: P+MAE delta -0.00002869, complexNRMSE delta +0.0000736. Negative favors local6addition. HeldoutG059 delta-complexNRMSE delta -0.002164. Not equal-size randomized acquisition; one heldoutlocalfamily cannot establish reproducible across-space local benefit.

FrozenH1 gates {'state': False, 'routing': False, 'absolute_order': False, 'thresholded_absolute_order': False, 'total_power': False, 'seed_stability': True}; seedstability PASS. Main gate verdict HOLD.

## B_ExtraTrees

Complex NRMSE 0.785793 → 0.768557 (2.19% lower); H2 P+MAE 0.0314343 → 0.0291914 (7.14% lower).

TM magnitude MAE 0.231769 → 0.232131; predicted weighted norm 0.4734 → 0.4553, truth1. Magnitude between-geometry variance ratio pred/truth 0.1078 → 0.1129. These directly measure shrinkage; not a physical loss claim.

450nm mean-foldrho 0.4410 → 0.4690; Top20recall 0.5179. P+MAE relative improvement vs strong output-domain constantMean 9.78%. The constant reference is not a deployed directpower model.

Local6 addition conditional on44nonlocal observations: P+MAE delta -0.00006410, complexNRMSE delta -0.0004580. Negative favors local6addition. HeldoutG059 delta-complexNRMSE delta -0.003785. Not equal-size randomized acquisition; one heldoutlocalfamily cannot establish reproducible across-space local benefit.

FrozenH1 gates {'state': False, 'routing': False, 'absolute_order': False, 'thresholded_absolute_order': False, 'total_power': False, 'seed_stability': True}; seedstability PASS. Main gate verdict HOLD.



## 最终七项明确裁决

1. **复数预测：小幅改善。** A复数NRMSE 0.79530→0.77695；B 0.78579→0.76856，约下降2.31%/2.19%。
2. **TM幅度与Routing：结论不同。** 阶分配和目标阶η改善，但TM模长MAE A 0.23800→0.23916、B 0.23177→0.23213，略恶化，不能报告TM幅度整体已学好。
3. **收缩：没有解决。** B预测加权范数0.4734→0.4553，真值为1，绝对幅度收缩反而加重；几何间模长方差仅从真值的10.78%升至11.29%，仍严重不足。H2对共同幅度缩放归一化，因此功率指标改善不等于完整复态尺度改善。
4. **结构稳定性：保留双候选。** A/B ExtraTrees种子稳定性都PASS。B的复数/目标功率略好，A相位、P_scale和最终450nm排序略好；没有全面赢家。B作为当前主候选，A保持对照。KRR虽然模长RMSE较小，但复杂态及H2功率更差，不据此取代ET。
5. **优于基线：已有描述性收益，未达到正式设计精度。** B的P+MAE为0.0291914，比强输出域功率常数Mean低9.78%；固定124几何450nm Spearman为0.4690、Top20召回0.5179，仍有明显高功率低估。四折配对差异见STRONG_MEAN_PAIRED_FOLD_CHECK；没有据此做外部全空间认证。A/B全部原H1主精度门槛FAIL，MODEL_GENERALIZATION保持HOLD。
6. **局部协同：小幅条件收益，重复性未证实。** 加入最后6个局部点后，B目标功率MAE仅额外下降0.0000641、复杂态NRMSE下降0.000458；同一G059独立家族差分NRMSE下降0.003785。它不是等样本量随机对照，只有一个独立局部验证家族。新增两组完整真值实验提供额外物理信息，但old32锚点训练专用，不能报告泄漏的训练内泛化收益。不得以此增加局部采样比例或唯一归因为近场机制。
7. **继续扩库的收益：有迹象但有限，先做零求解幅度/阶分配诊断。** 现有50案用约8.01小时Solver调用换来约2.2%复杂态和7.1%目标功率误差下降，不能线性外推下一50。优先检查相位平均与绝对模长收缩的学习表征，在609D合同内复用轻量模型；如用户另授权约50案，继续以六维覆盖＋功率TM分歧为主体，局部维持小比例并增加独立锚点证据，不只追预测高效率。下一轮当前授权0。

FAST训练级资格与严格数值收敛资格分开：本批50标签有效，不追认旧严格HOLD；不宣称整个六维空间已数值收敛。无sealed响应访问，无Runner修改，无预算转移。


## 评价边界补充

采集分歧模型使用全部222G已有标签选样；后续每折模型仍完全排除其验证几何及相连局部家族，预处理仅在训练折拟合。没有直接几何/家族训练泄漏，但这是数据自适应采集后的既定OOF分析，不是从未参与采集过程的独立外部测试。sealed confirmation未访问。强功率Mean逐折比较：A仅2/4折更低，B仅3/4折更低；平均收益不能写成各折一致获胜或统计显著性。

最终图表目视QA已完成：7/7通过，PDF最小字号7pt；详见FIGURE_QA_REPORT.md、VISUAL_QA_VERIFIED.json。
