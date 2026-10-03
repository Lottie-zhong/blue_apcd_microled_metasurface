# 32G 适配矩阵

状态定义：**直接支持**=机制与合同一致且已有接口证据；**明确修改支持**=可在当前标签基础上改造但不能复用现成实现；**新增标签/仿真**=现有监督不可识别；**假设不成立**=现有对象语义不同；**尚未核实**=固定 commit 证据不完整。

| 对接项 | GNN-for-Metasurfaces | Meta_SCMT | mutual-coupling | APCD 适配结论 |
|---|---|---|---|---|
| Ordered D1…D6 | 节点能表达单元，但无 APCD 物理槽位/目标阶读出 | 有空间单元次序，无 D identity | 论文 target/邻居窗口有次序，仓库实现缺失 | 明确修改支持：authority 槽位固定；禁止 sort/permutation-invariant 输出 |
| 固定位置与 phase origin | 局部位置用于 patch/message；未携带 APCD global origin | 网格传播位置显式，但没有 APCD Floquet reference | exact encoding 未在仓库核实 | 明确修改支持；输出需同一 phase origin/reference plane |
| cyclic registration | 未发现 APCD cyclic-registration rule | 有限阵列位置，不是 APCD registration | 未核实 | 明确修改支持：显式 cell origin 与回映射 |
| x/y periodic、z PML | notebook 设置 x/y 零 PML 层、z 十层 PML；零 PML 数值不等于 APCD torus 图边，图邻接对 patch 边界裁剪，无 K6 seam edge | solver/SCMT 邻接是有限边界裁剪 | 论文辅助求解有周期局部模型，代码不可审查 | 明确修改支持：周期 image-shift edges；PML 仍属于集成 solver 合同 |
| K6 跨边界邻居 | 无 APCD toroidal edges | 不支持周期 wrap 的 K6 邻接 | 一维 x-local 邻居定义但非 K6 3D 接口 | 明确修改支持；按 authority 几何生成，不能靠图默认边界 |
| 440–460 nm/21点 | 数据示例是其他波长/材料；无此 APCD 谱输出 | 支持另存 wavelength cache/分波长拟合，但不是 21 点 APCD 证据 | 论文标签域不同 | 明确修改支持用 C_hat 监督；模型须显式 wavelength condition |
| TE/TM complex modal coordinates | 输出复数 E 网格分量，非 TE/TM Floquet 模态 | 局部复模态传播，但当前单模/标量化配置不等于两个 APCD 通道 | local complex t，偏振/多阶块不足 | 新接口可重建现有 C_hat；SCMT operator 需新增标签 |
| 七个 transmitted orders | 无 | 无 APCD 七阶 far-field complex 输出 | 无 | 现有 C_hat 可直接作目标；三仓库输出都须改写 |
| C_hat / P_scale factorization | 近场 E 预测，无该因式分解 | U/mode field 到场，无 APCD P_scale 定义 | 复数 t，不是 C_hat/P_scale | 对任一复用路径为假设不成立；必须保留独立 P_scale 与 C_hat 语义 |
| frozen H2 | 无 | 无 | 无 | 三者均不能替代 H2；可复用 APCD evaluator only |
| strict geometry LOGO | 实际随机 panel/patch split，不是 32G LOGO | 未见当前 32G group LOGO 协议 | 无训练源码可验证 | 必须重写 split；geometry 是唯一独立 group |
| 固定 MDC + 237nm spacer | 无此 stack | 单层向前耦合模型，无 MDC/spacer 参数 | 局部单层 response | 需要新增层间端口数据/求解；不能直接支持 |
| MDC–NP 多次反射 | 不含 | 未实现两侧反向传播闭环 | 未实现可审查 operator | 物理假设不成立于现成计算路径；需完整双向复数端口块 |
| 当前 32G integrated truth | 论文/仓库数据标签不匹配 | 未与 APCD 集成 C_PW 同参考面校准 | 没有仓库内数组 | 现有冻结 C_hat/P_scale 才是监督和 gate 权威 |
| 未来 MDC 自由度 | 图输入可增加 MDC feature，但需再审协议 | 可为新局部模式建模，需新 mode/coupling 标签 | 需扩展 response data | 明确修改 + 很可能新增标签；先固定 MDC baseline |
| K4/K6/K9 | node count 有一定机制弹性，但 APCD order readout/边界未验证 | 新拓扑/邻域和模态数据 | 目标邻居定义不同 | 新任务新数据；不得声称 node-size 泛化即物理泛化 |
| 多角度入射 | 现有网络输入中未见 APCD incident-angle channels | 入射模态初态可概念扩展，输出多通道未有证据 | 未见多角度 operator | 需要增加入射通道标签；当前单一 P_XLIKE truth 不够 |

图等变性与物理顺序：重编号节点后函数输出按节点同步置换，是软件表示性质；它不授权忽略绝对位置、phase origin 或 D1…D6 order。K6 周期跨界边必须含 lattice image shift，使几何位移与相位/边界语义不歧义。split 单位始终是完整 geometry；32G×21λ 不等于672个独立几何样本。
