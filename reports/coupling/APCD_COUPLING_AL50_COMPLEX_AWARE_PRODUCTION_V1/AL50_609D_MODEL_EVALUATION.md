# 609D Model Evaluation

Formal Geometry → complex Floquet C_hat + P_scale → frozen H2. No direct η/power surrogate. Same original124 validation geometries, original folds, train-only preprocessing and complete local-family purge. Original222training subsets unchanged: validated at each stage. Old32 anchors remain train-only. ET seeds17/29/43,128trees,minleaf3; KRR alpha.1,gamma1/inputdim; Mean uses train-only complex/logP mean. Frozen aggregation averages complex state and physical Pscale across seeds. No tuning against heldout data. B wavelength rows remain grouped by geometry; nominal leaf3 rows is not a capacity-matched architecture claim.

|Model|N|Complex NRMSE|Magnitude RMSE|Rel phase °|P_scale MAE|η+ MAE|P+ MAE|ρ450|Top20 recall|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|A_Mean|222|0.944074|0.238860|89.936235|0.053160|0.141712|0.044027|NA|NA|
|A_Mean|238|0.944209|0.238450|90.680902|0.053180|0.140610|0.043610|NA|NA|
|A_Mean|254|0.942081|0.240231|90.174579|0.053201|0.140265|0.043448|NA|NA|
|A_Mean|272|0.942921|0.240668|91.042326|0.053090|0.140261|0.043378|NA|NA|
|A_KRR|222|0.901172|0.162094|72.984430|0.067049|0.122599|0.039073|0.065447|0.255952|
|A_KRR|238|0.892684|0.161558|69.638333|0.063033|0.124865|0.038999|0.066723|0.339286|
|A_KRR|254|0.886611|0.161034|69.329928|0.062405|0.122017|0.038658|0.071427|0.363095|
|A_KRR|272|0.876708|0.160983|68.195045|0.063032|0.124153|0.039622|0.063403|0.261905|
|A_ExtraTrees|222|0.795303|0.199462|53.504684|0.052520|0.106768|0.033261|0.467863|0.517857|
|A_ExtraTrees|238|0.790703|0.198510|52.646796|0.052348|0.103209|0.031969|0.493762|0.595238|
|A_ExtraTrees|254|0.781544|0.198747|50.769972|0.052197|0.101703|0.031860|0.489264|0.595238|
|A_ExtraTrees|272|0.776945|0.199141|48.886682|0.052419|0.096612|0.030440|0.480346|0.523810|
|B_Mean|222|0.944074|0.238860|89.936235|0.053160|0.141712|0.044027|NA|NA|
|B_Mean|238|0.944209|0.238450|90.680902|0.053180|0.140610|0.043610|NA|NA|
|B_Mean|254|0.942081|0.240231|90.174579|0.053201|0.140265|0.043448|NA|NA|
|B_Mean|272|0.942921|0.240668|91.042326|0.053090|0.140261|0.043378|NA|NA|
|B_KRR|222|0.897297|0.163525|70.084135|0.077022|0.121590|0.038891|0.099567|0.261905|
|B_KRR|238|0.887121|0.162384|66.667422|0.072308|0.123206|0.038808|0.043434|0.291667|
|B_KRR|254|0.876893|0.160754|65.419685|0.071750|0.120727|0.038366|0.007682|0.333333|
|B_KRR|272|0.862413|0.159836|63.850078|0.072626|0.121915|0.038966|0.043553|0.297619|
|B_ExtraTrees|222|0.785793|0.195179|53.478511|0.053499|0.100100|0.031434|0.440952|0.517857|
|B_ExtraTrees|238|0.781004|0.194398|52.395879|0.053068|0.097614|0.030564|0.484378|0.595238|
|B_ExtraTrees|254|0.774040|0.193865|51.198284|0.052851|0.096925|0.030386|0.484392|0.482143|
|B_ExtraTrees|272|0.768557|0.194299|49.708285|0.053431|0.092175|0.029191|0.469040|0.517857|

Fold ranges are descriptive, not independent-repeat confidence intervals. Strong output-domain constant Mean is evaluation-only in each STAGE_* directory. Frozen H1 gates and seed stability are fully retained in FROZEN_H1_DIAGNOSTIC.json; performance gains do not imply H1 approval. TM_ROUTING_VARIANCE_DIAGNOSTICS and ORACLE_ERROR_ATTRIBUTION distinguish amplitude allocation, normalization shrinkage and phase. H2 positive normalized output is structural, not independent energy-conservation evidence.


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
