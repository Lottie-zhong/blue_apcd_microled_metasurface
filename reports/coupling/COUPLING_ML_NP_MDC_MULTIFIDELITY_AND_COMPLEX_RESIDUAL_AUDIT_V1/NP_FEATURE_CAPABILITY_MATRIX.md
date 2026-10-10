# NP_FEATURE_CAPABILITY_MATRIX

| 能力 | 正式证据与范围 | 可用于 Coupling 的内容 |
|---|---|---|
| 输入 | 有序 D1…D6；100–230 nm、5 nm 网格；pitch=290 nm，周期跨界也检查非重叠；不排序 | runtime支持27^6个有序向量；不等于未知几何精度验证 |
| 可执行特征 | 27直径×11波长的冻结 x 单柱 txx，经有序六位置 DFT，生成7个归一化阶 fraction + T_proxy | 每几何88维，辅助 physics-informed features |
| 功率语义 | T_proxy仅为归一化 tracked m=-1,0,+1 的和；R不可用 | 不等于绝对透射，不能提供 integrated P_scale |
| 已有精度 | 历史 scalar spectral OOF MAE≈0.03960、ranking Spearman≈0.96160，属于筛选口径；HF22未通过全部量化准入 gates | 不可与 integrated C_hat 指标直接等价。runtime parity最大1.78813934e-7只证明实现一致 |
| 复数归档 | 22几何×P/S×11波长；透射m=-3…3，反射m=-5…5；系数sqrt(formal power)×gratingvector | 保存了复数 order proxy，但不是散射归一化 t/r |
| 原始 E/H | 历史44/44 retained FSP LOAD-only审计暴露两monitor的6个复数分量 | 有恢复能力证据；本轮未LOAD，也未声称新核验完整场dump |
| 相位与参考 | raw monitor phase；后续正式two-port合同明确FAIL：scattering normalization和incident complex phase reference | 禁止据此级联或构造伪复数 residual |
| 角度与偏振 | HF22 normal u_x=ky=0，P/S分别记录；V2可执行特征仅P/XLIKE | 不做P/S平均或替代，不宣称任意角度 |
| 稀疏角度 | M11 ALT1/B仅+0.224137931(S)、±0.378689400(P/S)，55行；CONTROL0决策未证实，-0.482759 stress-only | 不是未知K6几何、多输入返回阶算子 |
| 波段 | 445–455 nm integer grid；440–444及456–460不支持 | 可用88维中波段几何描述符，但不能外推NP响应 |
| 复数预测基准 | 最强spectral RBF normalized error median/q95=0.6849/1.0458，complex RMSE=0.1740，phase MAE=1.0399 rad；T/R MAE=0.1895/0.0906 | 尚非部署provider，提升精度不自动解决phase/normalization |
| 支持域 | 没有geometry fit；HF22经验支持22点，冻结32G exact overlap=0/32、runtime valid=32/32 | OOD/support仅诊断，不进入训练输入 |

代码核查：np_k6_coupling_forward_feature_interface_v2.py 的102–143行冻结输入，328–373行实施有序DFT/功率输出；np_k6_hf22_complex_scattering_state_extractor_v1.py 第143行明确sqrt(abs(total))*component，没有除以入射复数幅值。

正式报告包括 NP_K6_COUPLING_FORWARD_RUNTIME_COVERAGE_V2、NP_K6_COMPLEX_FORWARD_SURROGATE_BENCHMARK_V1、NP_K6_HF22_COMPLEX_SCATTERING_STATE_EXTRACTION_V1，以及其后的 NP_K6_COMPLEX_TWO_PORT_REFERENCE_PLANE_CONTRACT_V1。完整路径与SHA见EVIDENCE_INDEX.json。

早期 extraction PASS是可用性及功率账本闭合；后续不可组合结论是复数物理语义限制，两者不能混写。D180历史pre-FSP linkage警告保留，本轮未重开forensic。
