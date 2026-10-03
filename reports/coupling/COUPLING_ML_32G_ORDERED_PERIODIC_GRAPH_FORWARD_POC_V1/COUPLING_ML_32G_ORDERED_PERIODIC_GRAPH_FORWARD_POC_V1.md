# COUPLING_ML_32G_ORDERED_PERIODIC_GRAPH_FORWARD_POC_V1 — 有序周期图前向 POC 结果

状态：`MIXED_OR_TAIL_DETERIORATION`。这是 development POC，不是独立几何确认或生产准入。

## 冻结方案与实现检查

- G0 仅训练一个新候选；C0 与历史 FULL 均复用落盘 OOF。数据为 32 个 geometry LOGO 折 × 21 个波长，seeds 0/1/2，3 个 geometry-grouped inner folds。最终完成 288 inner + 96 final fits，共 384 fits、20786 个 optimizer steps；上限 122,880。CPU only。
- 每个节点为有序 D1…D6 的直径及固定 x/Λx 位置，phase origin=(0,0) nm，x/y 周期分别 1740/290 nm。左右有向环边带 signed dx/Λx 与 image shift；3 轮共享消息更新，按物理槽位 flatten，接 rank-2/order-local PCA heads 和原 cross-order fusion。
- 参数：graph encoder 1040 + heads 462 + fusion 942 = 2444；C0=2684。h=4 仅由参数上限选择，h=5 超限。
- 训练前检查：PASS；重编号后物理槽读出最大预测差通过 allclose；循环移动直径不被强制不变；左右路径、跨边界 image shift 均影响输出；六个直径均有梯度。Cartesian PCA/H2 接口检查通过。无 solver、无 C0/P_scale refit。

## 原 H1 指标

| 模型 | state med/q95/worst | routing med/q95/worst | absolute order med/q95/worst | thresholded relative med/q95/worst | P_scale med/q95/worst | H1 |
|---|---:|---:|---:|---:|---:|---|
| G0 图编码 | 0.822821 / 1.1198 / 1.25333 | 0.206695 / 0.318168 / 0.343641 | 0.0799943 / 0.12623 / 0.134351 | 0.926867 / 0.971795 / 0.979233 | 0.204122 / 0.574895 / 0.718727 | FAIL |
| 冻结 C0 | 0.818979 / 1.12391 / 1.26898 | 0.202821 / 0.319415 / 0.343753 | 0.0793698 / 0.125476 / 0.135187 | 0.921277 / 0.977745 / 0.985474 | 0.204122 / 0.574895 / 0.718727 | FAIL |
| 历史 FULL | 0.818979 / 1.12391 / 1.26898 | 0.202821 / 0.319415 / 0.343753 | 0.0793698 / 0.125476 / 0.135187 | 0.921277 / 0.977745 / 0.985474 | 0.204122 / 0.574895 / 0.718727 | FAIL |

C0 重用预测经当前冻结 evaluator 复算与保存汇总完全一致（最大绝对差 0）。G0/C0/FULL 原始 conjunctive gates：state、routing、absolute-order、thresholded-relative、P_scale/total 均 FAIL；seed stability PASS。P_scale 完全相同，Pearson=0.943177，未重新拟合。

## 复数状态、相位与配对差

G0 vs C0 每个差值按同一 geometry 配对。下表是 G0−C0 的 median / q95 / worst delta 及 geometry win/loss：

| 指标 | median / q95 / worst Δ | wins / losses |
|---|---:|---:|
| state | -0.00293978 / 0.0109859 / 0.0253184 | 19 / 13 |
| amplitude | 0.0076039 / 0.0346737 / 0.0370537 | 11 / 21 |
| 绝对相位，truth-amplitude² 权重 | 0.00100682 / 0.207897 / 0.254451 | 16 / 16 |
| 绝对相位，prediction-amplitude² 权重 | -0.0233948 / 0.0263438 / 0.0576823 | 24 / 8 |
| 跨阶相对相位，truth 权重 | 0.0330301 / 0.237595 / 0.315434 | 12 / 20 |
| routing | 0.00257382 / 0.00704531 / 0.00880443 | 9 / 23 |
| absolute order | 0.00122196 / 0.00224407 / 0.00392809 | 5 / 27 |
| thresholded-relative | 0.00334709 / 0.0594761 / 0.0693626 | 13 / 19 |

G0 的 state median 为 0.822821（C0 0.818979），q95 为 1.11980（C0 1.12391）；paired state wins 19:13，median 有小幅改善但 q95 与最差几何恶化。Routing median 为 0.206695（C0 0.202821），paired wins 9:23；不支持一致改善。G0 amplitude median 0.652229（C0 0.644584），truth-weighted absolute phase 1.33861 rad（C0 1.33029），truth-weighted relative phase 1.16464 rad（C0 1.08912），均变差。Prediction-weighted absolute phase从 0.514418 到 0.487627 rad，但振幅分布也变了，不能当成独立相位提升。Oracle common-phase 仅作诊断，不进入 H1。

每个 seed（state/routing/truth-weighted relative phase median）：

- G0 图编码 seed 0: 0.818605 / 0.206446 / 1.16539；P_scale median 0.204122。
- G0 图编码 seed 1: 0.82927 / 0.205305 / 1.1385；P_scale median 0.204122。
- G0 图编码 seed 2: 0.824017 / 0.207189 / 1.17121；P_scale median 0.204122。
- 冻结 C0 seed 0: 0.821195 / 0.196802 / 1.18774；P_scale median 0.204122。
- 冻结 C0 seed 1: 0.807801 / 0.197425 / 1.09623；P_scale median 0.204122。
- 冻结 C0 seed 2: 0.843237 / 0.198552 / 1.17489；P_scale median 0.204122。
- 历史 FULL seed 0: 0.821195 / 0.196802 / 1.18774；P_scale median 0.204122。
- 历史 FULL seed 1: 0.807801 / 0.197425 / 1.09623；P_scale median 0.204122。
- 历史 FULL seed 2: 0.843237 / 0.198552 / 1.17489；P_scale median 0.204122。

## Tail 与训练/held-out

- K6V1_EXT08: G0/C0 state 1.02574/1.03297；amplitude 0.830202/0.840648；truth-weighted abs phase 1.93253/1.99256 rad；relative phase 1.35445/1.32016 rad；routing 0.325837/0.328472；absolute order 0.134351/0.135187。
- K6V1_S31: G0/C0 state 1.2061/1.20153；amplitude 0.852918/0.85148；truth-weighted abs phase 2.31591/2.40554 rad；relative phase 1.10846/0.965789 rad；routing 0.343641/0.343753；absolute order 0.129595/0.129335。
- K6V1_S33: G0/C0 state 1.25333/1.26898；amplitude 0.712361/0.716705；truth-weighted abs phase 1.76633/1.93172 rad；relative phase 1.59786/1.44332 rad；routing 0.264077/0.263197；absolute order 0.0959373/0.0955402。
- 新最差 state geometry 是 K6V1_S33，state=1.25333；新最差 truth-weighted relative-phase geometry 是 K6V1_EXT12，1.612 rad。G0 的最差 order 诊断为 K6V1_S31 / m=0，最差 wavelength 诊断为 K6V1_S33 / 459 nm。完整谱线分解见 per_wavelength.csv 与 per_order.csv。
- G0 in-sample state median/q95/worst: 0.795391 / 1.15103 / 1.25762；OOF complex seed-mean: 0.822821 / 1.1198 / 1.25333。训练几何在多个 outer fits 中重复，样本数 2976 不能视为独立。此 POC 没有 C0 in-sample refit，不能比较训练拟合差。

## H2、泄漏与结论

- H1 modal_weights 是 m=0 归一化的功率比，H2 power_z_per_abs_e2 是绝对系数。按每个波长 m=0 TE 系数归一后，两者最大差 7.77156e-16；原系数约 0.00132721–0.00132721。H2 由 C_hat 与同一 predicted P_scale 重建，各 seed/complex seed-mean 的总功率闭合最大差 7.77156e-16，routing 相对 H1 最大差 4.44089e-16。H2 只用分偏振 |C|² 功率和，不含 TE/TM 复相位交叉项。
- 外层整组 geometry LOGO，wavelength 不跨组；inner folds、scaler、PCA 均按 geometry 仅在当前训练组拟合。没有节点/窗口随机切分。32 个 geometry 是配对统计单位。
- 结果为 MIXED_OR_TAIL_DETERIORATION：periodic graph 没有带来一致 state/routing/phase 改善，且 S31 与新的 relative-phase worst 显示退化。P_scale gate 仍独立失败。该证据不否定图编码或更多几何数据，只说明此冻结 G0 配置未显示稳定收益。停止在科学评审边界，不追加宽度、层数、loss、seed 或样本。

下一步建议（不执行）：由 Chat 评审是否停止图路线或设计新的独立几何确认；本开发 OOF 比较不能作为确认验证。


## Supplement: seed, oracle, tail and training diagnostics

Values below are generated only from persisted results.json, seed_metrics, h2_reconstruction.csv and pretraining_tests.json; no metrics were recomputed and no model or solver was run.

| Arm | seed-state median std | routing Pearson | P_scale Pearson | oracle-aligned state median | oracle common-phase SSE share median |
|---|---:|---:|---:|---:|---:|
| G0 | 0.00435408 | 0.772821 | 0.943177 | 0.754813 | 0.0520059 |
| C0 | 0.0146094 | 0.771308 | 0.943177 | 0.74752 | 0.0494356 |
| HISTORICAL_FULL | 0.0146094 | 0.771308 | 0.943177 | 0.74752 | 0.0494356 |

Per-seed medians (state / routing / truth-weighted absolute phase / truth-weighted relative phase):

- G0 seed 0: 0.818605 / 0.206446 / 1.35952 rad / 1.16539 rad.
- G0 seed 1: 0.82927 / 0.205305 / 1.31678 rad / 1.1385 rad.
- G0 seed 2: 0.824017 / 0.207189 / 1.34936 rad / 1.17121 rad.
- C0 seed 0: 0.821195 / 0.196802 / 1.34594 rad / 1.18774 rad.
- C0 seed 1: 0.807801 / 0.197425 / 1.28887 rad / 1.09623 rad.
- C0 seed 2: 0.843237 / 0.198552 / 1.36042 rad / 1.17489 rad.
- HISTORICAL_FULL seed 0: 0.821195 / 0.196802 / 1.34594 rad / 1.18774 rad.
- HISTORICAL_FULL seed 1: 0.807801 / 0.197425 / 1.28887 rad / 1.09623 rad.
- HISTORICAL_FULL seed 2: 0.843237 / 0.198552 / 1.36042 rad / 1.17489 rad.

Focused tail P_scale and thresholded-relative medians (values are per geometry over the complete 21-wavelength spectrum):

- K6V1_EXT08: P_scale G0/C0 0.30983/0.30983; thresholded-relative 0.947399/0.956017; routing 0.325837/0.328472.
- K6V1_S31: P_scale G0/C0 0.718727/0.718727; thresholded-relative 0.930427/0.922184; routing 0.343641/0.343753.
- K6V1_S33: P_scale G0/C0 0.234901/0.234901; thresholded-relative 0.979233/0.985474; routing 0.264077/0.263197.
- Final-fit standardized latent MSE median/q95/worst: 0.997874/1.00417/1.01499. G0 in-sample state entries repeat across outer fits and are descriptive only.

The three message rounds define the model receptive field; they do not assert that physical coupling is limited to immediate neighbors. The oracle common-phase values use held-out truth and remain diagnostic only. Prediction-dependent phase weighting also changes when amplitudes change.
