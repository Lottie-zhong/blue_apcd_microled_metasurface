# EXISTING_MODEL_FAILURE_ANALYSIS

已验证：历史33G目录中的dataset manifest为65G（旧32+新增33），split为52train/13validation；只读已有KRR与MLP两个fit。验证8旧、1局部、4全域。旧32聚合NPZ和新增33 label NPZ的SHA一致；13个prediction case/order/λ/component顺序按冻结schema，state相对误差复算匹配原报告≤1e-12。逐geometry、normratio、复数方向、各λ/阶/TE-TM SSE见READ_ONLY_METRICS.json。

| 指标 median/q95 | KRR | MLP |
|---|---:|---:|
| State |0.939633/1.159260 |0.936562/1.094406 |
| Routing |0.147433/0.246631 |0.171951/0.305307 |
| Absolute-order |0.065302/0.090317 |0.059330/0.111052 |
| Thresholded-relative |0.767995/0.900413 |0.746368/0.932565 |
| P_scale=total |0.463683/0.653790 |0.246375/0.486062 |

原五类数值gates全部FAIL。单seed的stability未测；保存的评估器即使对MLP也标记NOT_APPLICABLE_DETERMINISTIC_CANDIDATE，不能把此措辞理解为MLP稳定性已证实。

## 零基线、收缩与相位

state指标为 ||C_pred−C_truth||₂ / ||C_truth||₂，跨21λ×7阶×TE/TM汇总每geometry。全零baseline对每非零真值恰为1，未调用H2解码零态（零态无合法routing）。

定义r=预测/真值范数比、cosθ=实部复数内积的方向余弦，则 e²=1+r²−2r cosθ。本轮验证该恒等式，无oracle phase alignment、无预测重归一化。r中位数：KRR0.554412，MLP0.520735。支持幅值收缩，但不能仅由RMSE≈1断言所有预测恒常数；方向误差同时重要。

65G每个模型仅1seed，因此本次收缩不能归因为ensemble平均。未来complex seed-mean可能引起抵消，须继续报告平均前后范数，不能改原集成规则。P_scale每seed先exp回物理域再算术平均。

## 分组与训练/验证

| 组 | n | KRR state median | MLP state median |
|---|---:|---:|---:|
| 旧32验证 |8|0.965059|0.915063|
| 新局部轴向 |1|0.218517|0.376630|
| 新全域 |4|1.005170|1.010006|

唯一局部点D2_M05，其附近10个轴向点在训练组；r=0.956384/0.727520。这是已观察的较易邻域，不证明局部组合交互可泛化。未读取4个局部组合确认响应；±5 nm响应仍缺数值重复性误差对照。

当前旧8与此前REAL32验证8不同，不能作相同geometry的前后直接比较。没有为对照而改split或重训。

KRR train/val standardized loss=0.014596/1.423014；MLP=0.818910/1.141077，selected155、executed205 updates。KRR训练好而验证差；MLP仍有训练拟合余地，二者不能简单合并成同一根因。

旧31G轨迹审计中C0/G0在1000更新后训练latent近零，但6条inner轨迹都在15–29步达验证最低点，继续训练不恢复。PCA floor约0.37低于最终验证误差1.04–1.35。该历史结果支持泛化限制，不证明609输出65G模型也有完全相同机制。

## 幅值、相对相位与NP收益

历史32G：normalized complex SSE amplitude63.244%/phase36.756%；ORACLE common-phase只解释12.686%SSE；in-basis prediction79.997%，PCA truncation20.003%。physical C_PW的amplitude/phase为52.653%/47.347%，不同口径不能混用。仅引用历史oracle诊断，不把它用于本轮预测/gates。

NP A0/A1在445–455：state改善21/32、routing20/32、amplitude26/32、phase15/32。Routing median0.212318→0.195806；P_scale median0.167196→0.118075但q950.524672→0.551717；absolute-order15/32。全部H1 FAIL。功率DFT特征更容易提供幅值/routing线索是证据支持的推断，非因果证明；full-band NP正式ablation不存在。

KRR TE占总state SSE约1.12e-9，MLP约0.001197；误差以TM为主、order0贡献较大，但覆盖全部七阶。TE弱仍保留，不能因此删坐标或声称完整polarization operator。

H2以冻结modal weights对|C_hat|²计算order power，归一化eta，再令absolute=eta×predicted P_scale，total=predicted P_scale。P_scale与total误差相等为定义；overall C_hat scale对routing抵消，解释了功率侧改善未必代表完整复数state改善。

未验证假设：更好的合法NP几何描述符可能改善state；incident-normalized多端口相位可能改善跨阶phase；固定MDC输出条件化可能改变归纳偏置。均不自动构成H1改善、补样必要性或新的训练授权。
