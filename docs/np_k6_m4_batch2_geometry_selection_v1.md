# NP K6 M4 Batch2 geometry selection v1

## 状态

`NP_K6_M4_BATCH2_GEOMETRY_SELECTION_READY_FOR_SOLVER_AUTHORIZATION`

本阶段是严格的 selection-only evidence：`FDTD=0`、`LumAPI run=0`、
`sealed_target_reads=0`。没有启动 Batch2 solver，也没有把任何预测值写成
HF 标签。

## Authority 与排除

选择只使用当前仓库中的冻结 M3 198-row development HF view、M3 六模型
CNN/MLP ensemble、M2 冻结 LF acquisition features 以及 48 点 development
geometry manifest。development universe 为 48 个 geometry；sealed universe
为 12 个；M2 candidate source 为 45 个。M3 已接受的 9 个 HF geometries
从候选池排除，故 M4 有效候选为 39 个。sealed overlap、HF overlap 和重复
geometry hash 均为 0。没有读取 sealed target，也没有读取未来 HF 标签。

M3 ensemble checkpoint 只做 CPU inference；模型 ID、checkpoint hash、训练
view hash 和 split manifest hash 都记录在 `m4_selection_policy.json` 与
`m4_authority_audit.json` 中。

## 冻结 policy

policy 在产生任何 Batch2 identity 前先写入并哈希：

`policy_hash = a0f46c2da1f653c8a3798ee97bc70e4e3da7598dda5bc9392b76fc4a2128d5d7`

policy ID 为 `NP_K6_M4_POLICY_PHYSICS_ROBUST_ROLE_BALANCED_V1`。primary
performance 使用 445--455 nm、P/S 分开预测后的 robust mean/min eta(+1)、
robust T、robust directionality 和 non-target leakage；E2 增加与 E1 的
物理特征距离；coverage 使用 D0--D5、相邻跳变、complement gap、span/mean/
std/alternating proxy 的显式 feature space；stress 使用 p/s eta 差异、
CNN--MLP 差异及 CNN--LF 差异。ensemble disagreement 只作相对 acquisition
heuristic，不能解释为校准概率、置信区间或 uncertainty calibration。

## Primary 4

| role | geometry | hash | 选择信息 |
|---|---|---|---|
| exploitation_1 | `K6X_D110_D125_D135_D150_D175_D190` | `e599c908c3befb142dacc503b37f1aefc68655082078b987ae553e49f60ec84f` | performance 0.93158；robust eta mean/min 0.81859/0.76555；T min 0.83463；directionality min 0.91544 |
| exploitation_2 | `K6X_D120_D125_D180_D185_D190_D195` | `50ad4213fdfa1bf1b1a353c55769ade406e6fdebf5a82de63c4bd7e0c7fc3e7c` | performance 0.74342；robust eta mean/min 0.78977/0.67367；T min 0.76149；与 E1 保持 feature-space 分离 |
| coverage_exploration | `K6X_D120_D145_D200_D215_D220_D230` | `269b86c19099935a4fe83452d0a05faf6296e1ec0d4b4f38325d07863d571033` | coverage 0.95263；覆盖远离 HF9 的 development 区域 |
| model_conflict_physics_stress | `K6X_D140_D160_D165_D170_D180_D190` | `0ac97060e42705949d81140172fb178bb0fee693903982773db4697ba86e5d0d` | conflict 0.66711；同时满足 performance/T/directionality floor，不是低性能异常点 |

P/S 始终分开计算；本表不宣称 P/S 等价。每个 geometry 若获得授权，
后续必须执行 paired P/S、`u_x=0`、445--455 nm exact broadband 和冻结
NP 3D HF generator。

## Backups 与扩展顺序

ranked backups 为：

1. `K6X_D125_D135_D145_D150_D155_D160`
2. `K6X_D105_D125_D135_D155_D160_D165`
3. `K6X_D115_D125_D135_D155_D180_D195`
4. `K6X_D160_D165_D170_D175_D180_D220`
5. `K6X_D100_D105_D130_D145_D175_D220`
6. `K6X_D105_D110_D115_D120_D135_D200`
7. `K6X_D105_D120_D125_D130_D165_D190`
8. `K6X_D110_D125_D130_D135_D140_D175`

若扩展至 6，新增 backup 1--2；若扩展至 8，再新增 backup 3--4。顺序已
冻结在 `m4_selection_manifest.json`，无需重新运行 acquisition。

## Coverage audit

当前 HF9 的 nearest-HF distance mean / P90 / max 为
`2.20531 / 3.99752 / 4.96608`。加入 primary4 后为
`1.70954 / 3.44209 / 4.24553`，mean 改善 `0.49577`；first6 后 mean
为 `1.60442`，改善 `0.60089`；first8 后 mean 为 `1.53031`，改善
`0.67499`。P90 和 max 在 primary4、first6、first8 间没有继续下降，
因此不能把小 batch 描述为覆盖整个 design space。primary4/first6/first8
均无超过 0.25 阈值的 pairwise redundant pair，且候选都在 48 点
development feature bounds 内，没有明显 extrapolation candidate。

## Solver cost package

根据冻结 M3 Batch1 runtime audit，不使用固定“3 小时”估计：

| package | logical geometries | paired P/S cases | clean physical solver count | wall median | wall P90 |
|---|---:|---:|---:|---:|---:|
| primary4 | 4 | 8 | 8 | 9.2545 h | 32.2350 h |
| first6 | 6 | 12 | 12 | 13.8818 h | 48.3526 h |
| first8 | 8 | 16 | 16 | 18.5090 h | 64.4701 h |

历史 Batch1 有 1 次基础设施丢失和 1 次受控 replacement；它们不计入正常
clean demand，但在成本风险中保留。

## Recommendation

当前继续 geometry acquisition 仍有价值，因为有效 development 候选尚未
覆盖完整 feature space，且 primary4 分别覆盖性能、差异化 coverage 和
model-conflict falsification。当前不采用 pure uncertainty acquisition，
因为 M3 uncertainty 尚未证明为 calibrated confidence；本 policy 把它限制
在相对冲突/风险上下文中。与随机 4 点相比，primary4 的 role coverage
更可审计，且 primary4→first6 的额外 mean-distance 改善为 `0.10465`，
first6→first8 为 `0.07411`，应由 Chart 按 solver cost 决定是否扩大。

推荐 Chart 下一步只授权 `primary4`，即 8 个 paired P/S HF cases；不要
自动启动。first6/first8 仅作为已冻结扩展包，等资源决定后再授权。

## Evidence and validation

证据目录：

`outputs\\np_k6_m4_batch2_geometry_selection_v1\\`

其中包含 authority、policy、selection、profile、coverage、cost、zero
solver、provenance、checksum 和 validator artifacts。独立 validator：

`scripts\\validate_np_k6_m4_batch2_geometry_selection_v1.py`

stage-specific pytest：

`tests\\test_np_k6_m4_batch2_geometry_selection_v1.py`

历史 G04 validator 的旧 frozen-ledger assertion 没有被修改或放宽。
