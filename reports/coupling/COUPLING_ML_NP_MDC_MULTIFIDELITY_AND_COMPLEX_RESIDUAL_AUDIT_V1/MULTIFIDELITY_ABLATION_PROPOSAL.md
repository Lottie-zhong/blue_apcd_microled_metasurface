# MULTIFIDELITY_ABLATION_PROPOSAL — 未执行

| 候选 | 定义 | 当前可行性 |
|---|---|---|
| A | Ordered geometry-only，完整Cartesian state+独立log P_scale | 合法开发基准；现有KRR/MLP families |
| B | A+冻结88个NP功率/路由描述符 | 合法feature fusion提案，无operator声明，无OOD输入 |
| C | A+MDC双向r/t与spacer Re/Im | 当前完整谱输入为geometry间常数，简单拼接为解析null control，不额外fit |
| D | B+相同MDC特征 | train-centered stationary KRR下与B相同；若引入physical output conditioning须另冻接口 |
| E | 同构C_LF+learned HF complex residual | BLOCKED：NP gauge/normalization、返回输入通道及full-band缺失 |

所有候选保留原H2/H1、完整geometry split、train-only预处理、确认封存。C_hat和正值P_scale均实际预测；不用oracle phase/scale或truth-dependent selection。常数列明确处理为居中0，不人为制造特征差异。

当前最小建议仅A/B两次匹配KRR，见MINIMUM_NEXT_ML_EXPERIMENT。full-band H1与445–455 nm机制归因分别报告。中波段88维向量可作geometry描述符预测完整谱，但不能假装NP提供其他10个波长的响应。

如两者H1均FAIL，只能评价state/routing和tails是否有研究收益，不能设置综合分数新gate。旧开发数据已反复暴露；未来positive result须经冻结预测在独立确认集检验，本轮不访问任何confirmation响应。

E需先满足：incident complex reference、同port/同normalization、passive branch、multi-input channels、deterministic deembedding parity及所声明波段覆盖。建议在physical C_PW上定义residual，再按原factorization得到C_hat/P_scale，不能在未定义的gauge上学习差值。
