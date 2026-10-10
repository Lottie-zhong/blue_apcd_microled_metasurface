# MDC_COMPLEX_RESPONSE_MATRIX

| 项目 | 已验证能力 | 限制 |
|---|---|---|
| 蓝光Traditional | 冻结P1_ZL1_ALTERNATIVE_G3_A3；12层975 nm；另加237 nm SiO2 spacer；Native-M1 | 不引用红/绿champion代替蓝光 |
| 双向复数prior | 440–460 nm的21行r_L、t_LR、r_R、t_RL，E-field幅值；左GaN、右SiO2 | 不是空气右端口，也不是NP衍射算子 |
| 反向实现 | _response_for_direction交换media并反转层序 | r_L与r_R不能擅自等同 |
| 角度/TE-TM | 底层helper具oblique TE/TM/passive kz；冻结prior evaluate_row拒绝非零角度；normal TE/TM差为0 | 每个返回衍射阶的oblique表尚未冻结 |
| 参考面 | 左0 nm、右975 nm；exp(-iωt)，+z为exp(+ikz z)；extra spacer未包含 | 237 nm传播只乘一次；不能因此修复NP入射phase |
| 功率 | admittance修正；lossy GaN下R+T为0.9601–1.0444，不强制等于1；power_entering-T-A_stack闭合0；reciprocity残差7.45e-16 | 内部代数检查，不是integrated HF独立验证；不能只用|t|² |
| MDC网络 | V3-C final5seed，200 development geometries×6 dipole条件；normalized spectral-angular profile、Level0筛选 | 无合法PW复数r/t，无load-bearing power准入，无LEE/Purcell能力 |
| 固定MDC | 已有解析/归档复数TMM，无需重训网络 | 对不同K6几何相同，不能解释几何差异 |
| 未来自由度 | 既有families包括层厚、defect厚度/位置、chirp/asymmetry、topology及source条件 | 联合优化具体变量与范围需另行冻结，当前没有授权改变 |

MDC artifact SHA=b8e856fed0c7859b6ce3d1aa7d40549f40720b0c317b6f3dbf362e62c7e37a38；
source SHA=a7d618b697a71ed59bf8b56d9d5239b570f0cb03f9f650497fa49ce37a5a6a00。
均与Coupling正式handoff及当前bytes一致。MDC HEAD=7f34bd767adee8ed37c2d907ac0546d47430631e。

当前模型是D→完整609谱输出。固定MDC谱向量在不同geometry间是常数；train-centering后为0，stationary RBF距离不变，MLP常数输入可吸收到bias。不能把简单拼接称为新增物理信息。物理输出条件化可能改变归纳偏置，但需单独冻结与验证。本轮不为C/D常数输入重复拟合。
