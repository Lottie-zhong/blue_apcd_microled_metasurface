# COUPLING_ML_NP_MDC_MULTIFIDELITY_AND_COMPLEX_RESIDUAL_AUDIT_V1

状态：PASS（零 solver 审计完成）；复数 residual 的实施条件尚不具备。未授予模型生产准入。

## 已验证结果

- NP V2 可接受未知的有序 D1…D6，在 100–230 nm、5 nm 网格与 445–455 nm 上生成 88 个辅助功率特征。它不是完整复数散射算子，也不提供合法的 integrated P_scale。
- NP HF22 确实保留复数阶系数和历史 E/H 可恢复性证据。然而，后续正式 two-port 审计明确判定：散射归一化不成立、入射复数相位参考不可恢复。不能因早期 extraction PASS 而忽略后续物理语义限制。
- 固定 MDC 已有冻结的 440–460 nm 双向复数 TMM prior，端口为 GaN / SiO2，975 nm MDC 与额外 237 nm spacer 明确分开。实测文件 SHA 与正式交接一致。MDC V3-C 网络预测的是归一化 dipole 谱角形状，不是 plane-wave r/t。
- “33G”诊断目录实际包含旧32G加新增33G：52训练 / 13验证，验证为旧8、局部1、全域4。只读取已有两个 fit 的结果，旧32G聚合NPZ及新增33份标签NPZ SHA 已核对。

| 65G 已存诊断：median / q95 | KRR | MLP |
|---|---:|---:|
| state relative RMSE | 0.939633 / 1.159260 | 0.936562 / 1.094406 |
| routing RMSE | 0.147433 / 0.246631 | 0.171951 / 0.305307 |
| absolute-order RMSE | 0.065302 / 0.090317 | 0.059330 / 0.111052 |
| thresholded-relative | 0.767995 / 0.900413 | 0.746368 / 0.932565 |
| P_scale / total relative RMSE | 0.463683 / 0.653790 | 0.246375 / 0.486062 |

原五类数值 H1 gates 均 FAIL；单 seed 不证明 seed stability。state 指标复算误差在 1e-12 内。全零预测 state 基线为1；预测/真值范数比中位数为 KRR 0.554412、MLP 0.520735。原 H2 定义 total = predicted P_scale，因此两者误差相同是代数定义，不是独立能量验证。逐 geometry、波长、阶次、TE/TM 结果保存在 READ_ONLY_METRICS.json。

历史 NP A0/A1 在 445–455 nm 的幅值改善 26/32、routing 改善20/32、相位改善15/32，仍全部 H1 FAIL。唯一局部验证点较好，不足以证明整个局部域可泛化。

## 证据支持的推断

目前更有依据采用 NP 辅助特征融合。幅值收缩及训练/验证落差同时存在，不能将其单独归因为数据、优化或架构。固定 MDC 的完整谱向量对所有 K6 几何相同；对完整谱输出的普通拼接，train-centering 后不增加 KRR 几何信息，MLP 可将常数吸收到 bias。C/D 作为常数输入对照不值得重复消耗 fit。

## 尚未验证的假设

合法 NP 特征可能改善完整 state，但相位收益未证实。真正 incident-normalized 的 NP 多端口算子配合 MDC/spacer 多次反射，未来可能形成有效 residual baseline；现有资料不能实施。固定 MDC 的物理输出条件化可能改善归纳偏置，但属于另行冻结的参数化修改，不能冒充新增几何信息。

## 四个直接答案

1. 是否先提升 NP/MDC 独立模型精度？特征融合不需要先重训。固定 MDC 直接用 TMM；NP 复数路线应先解决 observable / phase / normalization 合同，再讨论准确率。
2. 是否已有复数 LF baseline 的必要数据？没有。缺 NP 入射参考与散射归一化、返回阶输入矩阵、完整21点波段覆盖。
3. 优先特征融合还是 residual？先特征融合；E residual 保持禁止实施。
4. 最小下一轮实验：固定65G 52/13 split，两个匹配 KRR A/B fits，预测完整 Cartesian state 与实际 P_scale，仅 B 加88个冻结 NP 特征；无搜索、无新 HF、无确认响应。细节见 MINIMUM_NEXT_ML_EXPERIMENT.md，仅提案，未执行。

## 边界与交付

本轮 FDTD=0、new training fits=0、P_scale fits=0、replay=0、confirmation response access=0、FSP LOAD=0。未修改 Runner、GPU request/release、生产合同、DOE、truth、H1/H2 或现有训练代码。只写本审计目录。

全部七项科学输出、FINAL_REPORT、CONTINUATION、SHA_INVENTORY、EVIDENCE_INDEX、READ_ONLY_METRICS 与独立只读脚本已保存。完整输入路径和 SHA 见 EVIDENCE_INDEX.json，产物 SHA 见 SHA_INVENTORY.json。历史开发数据已多次查看；局部 ±5 nm 尚缺重复性误差比较；已有 modal/TMM 代数闭合不能替代独立物理标签验证。

下一步：提交 Chat 科学评审两个匹配 KRR 的特征融合提案；不执行训练或 solver。
