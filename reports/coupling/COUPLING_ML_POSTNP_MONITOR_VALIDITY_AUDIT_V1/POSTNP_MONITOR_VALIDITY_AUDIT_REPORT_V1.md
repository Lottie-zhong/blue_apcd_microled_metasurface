# COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1

- 日期：2026-10-03
- 状态：PARTIAL（只读审计完成；历史产物没有第二个 NP 上方空气场面，独立跨高度验证缺失）
- 远端：DESKTOP-NNE313K / desktop-nne313k\dell
- worktree：D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1
- branch：work/mdc-np-coupling-ml-v1
- 审计输入 HEAD：ddda6b302d9282f416028386903ba8e7b39cbc50

## 范围与权威

只读加载 EXT02 setup FSP 检查对象/配置网格，读取历史 NPZ、H5、JSON、源码及报告；未调用 FDTD run、GPU Runner、训练、HF、reserve 或逆向搜索，未保存 FSP，也未移动 monitor、改 truth/contract 或覆盖历史数据。工作区原有 332 项状态保留；审计前 porcelain 清单 SHA256 为 e26c3debc7523bb4d157ac679656032d99c544ea675d770887afa7b236d964bc。

正式 authority：reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json，SHA256 0fae0577247866549cf85db88ab5d6f924795423adca4b8cf2742449736f6f2e。32 个 geometry、672 个 geometry×wavelength 行、4704 个七阶行，440–460 nm 共21点；state schema 为 POSTNP +z 七个 y=0 阶、TE/TM。EXT02 有序直径 [220,120,155,100,105,110] nm，state SHA256 bcb4d2c3d48bb6d033396cc0725eca9e1bfbe57759c5f002b0347e3ccfc61cf4。

monitor/reference authority SHA256 f49e0f9dcd07f2621cebd337854d507e284ead6e4b99ee774916a58695e6dcc9；monitor contract SHA256 a84d8526889084f2b3b09022402ca93b2947939cb744f071a4b19bc6eb09172f；EXT02 recovery manifest SHA256 3c9659818bbaebd9ea616bc5c1f2ff9f3361e9765faf49c3eddae027425393e6。逐文件来源和 hash 见 EVIDENCE_INDEX_V1.json。

当前用户附件是已粘贴文本，没有可用的独立截图文件。以下位置来自直接读取保存 setup 与 field axes。

## 实际几何与采样距离

直接读取 setup：outputs/coupling_ml/PW_K6_SEED_DB_V1_PRODUCTION_V1/K6V1_EXT02/attempt_001/setup/runtime.fsp，SHA256 99248d02495d8a3124f712bdaf2291c5a058cfd4a6a85ace129b096381b98143。六个 NP 对象均为 APCD_TIO2_NATIVE_M1 圆柱，z_min=1212 nm、z_max=1712 nm（500 nm 高）。x 中心依次 −725、−435、−145、+145、+435、+725 nm，半径依次110、60、77.5、50、52.5、55 nm；顺序与 D1…D6 authority 一致。

| 面 | z (nm) | 到 NP 顶面净距 |
|---|---:|---:|
| NP 顶面 | 1712 | 0 |
| POSTNP 名义坐标 | 1800 | +88 nm |
| 保存场实际采样坐标 | 1801.9999999999932（约1802） | **+90 nm** |
| POSTNP reference plane | 1722 | +10 nm |
| FDTD 顶边界 | 3000 | +1288 nm |

故真实柱顶到场采样面的间距约90 nm；1722 nm 是 de-embedding reference，不是 monitor 面，若用它计算会得到10 nm而非真实采样间距。实际样面与 reference 相距约80 nm。

POSTNP 为 NP 上方均匀 Air 中的 2D Z-normal monitor；setup 背景折射率1.0，contract 标记局部 Air。x/y span=1740×290 nm，等于一个周期；坐标范围分别为 −870…+870 和 −145…+145 nm，349×59 点、5 nm 均匀间距。保存21频点及 Ex/Ey/Ez/Hx/Hy/Hz 六个复场分量，每分量 shape=(349,59,1,21)，无提取阶段抽点/降采样。monitor 属性为 nearest mesh cell、uniform sample spacing；FSP downsampleX/Y/Z=1，Nx=349、Ny=59、Nz=1，spatialAveraging=1。最后一项仅按序列化设置原值记录；truth extractor 实际接收整张二维面，不把该值误称为平面平均。

配置网格距离（不是本次新求解的 runtime mesh）：
- NP_DERIVED_BASELINE_N2 的5 nm override 为 z=1112…1812 nm；1802 nm采样点距上界10 nm。
- MESH_NP_MDC_SPACER_BASELINE 的10 nm override 为 z=1087…1837 nm；采样点距上界35 nm。其外连接配置的非均匀网格。
- FDTD z=−600…3000 nm、PML layers=8。setup layout mesh 的 z[-9]≈2806.1667 nm；按最外侧8个间隔推得配置 PML 内缘，厚度约193.833 nm，NP 顶到内缘约1094.167 nm，采样面到内缘约1004.167 nm。该内缘为“层数+配置网格”的推算值，不是独立 PML 属性读数。采样面到顶边界约1198 nm。x/y boundary 为 periodic，z 为 PML。

保存的 raw NPZ SHA256 805b4f9e8e83db950f77fed0b4e29d7afa1423d02d9c679cdb00ed80c1753af1；其中 POSTNP_z 给出上述实际采样坐标。H5 SHA256 838a9809a22c206df1f7f40f5d70ff3a404a07da4a329178ea9bf41c195017b8。

## 真值提取有效性

源码 scripts/shared_fdtd/tools/pw_complex_floquet_state_v1.py，SHA256 b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15；raw 保存由 pw_scientific_launcher.py 调用，SHA256 9c103393c8fedfd8a7d5e5e769a94ca341f6a5a1c42b1a84f0511685c7f93b36。

这是完整周期二维 E/H 场的 Fourier/NDFT Floquet 投影，不是点场或空间平均：
1. read_fdtd_plane 读取实际 x/y/z/f 和六个场分量；canonicalize_plane_raw 保留整面数组。
2. _trap_weights 对实际递增坐标产生梯形权重、端点半权。逐阶以 exp[−i(kx x+ky y)] 对六分量积分并除以单元面积。
3. 每阶构造 6×4 复基，未知通道是 +z/−z × TE/TM；对六个 E/H 场作复最小二乘，rank<4 则报错。被动平方根分支给出 kz。倏逝阶复系数保留，但不分配传播功率。
4. de-embedding 使用 dz=z_reference−z_sample；+z 乘 exp(+i kz dz)，−z 乘 exp(−i kz dz)。每波长以 IN_REF 的 +z (0,0) TM 入射通道固定单一全局 gauge，并沿用到所有面/通道，保留跨阶相位。
5. order envelope 是 m,n=−4…+4 共81阶，propagating mask 按介质与波长计算。

EXT02 保存 state shape=(3 planes,21 wavelengths,81 orders,2 directions,2 polarizations)。POSTNP Air 中全波段每个波长有且只有7个传播阶：m=−3…+3、n=0；所以正式七阶覆盖440–460 nm全部空气传播阶，每阶保留TE/TM。其他 envelope 阶是倏逝阶。

端点包含在积分坐标中，以梯形端点半权计数；这避免端点被各算一个完整周期权重。但本次未单独量化首尾场值的周期闭合/aliasing。代码有合成单模、多模、传播方向和 reference-plane de-embedding regression tests；这些不是两个真实空气场面的独立传播验证。

结论：对周期边界、均匀 Air 和保存的完整二维 E/H，算法具备完整 Floquet 模态分离结构，比点场/空间平均具有明确模态语义。其真实复数相位跨高度不变性仍缺独立数据验证。

## Modal 与 native grating 对照证据

reports/coupling/PW_K6_MODAL_TO_GRATING_POWER_NORMALIZATION_RECONCILIATION_V1.md，SHA256 a32c3b043782cab4133f2193bc5f9d9d62e5bd4996a6c7d7ab0c61c7c8c55c19，覆盖20G×21λ（420样本，含EXT02），不是完整32G。

- C_PW modal power 与从同一 raw E/H 面做二维 Poynting 积分得到的 P_EH_norm 是不同的数值约化：median abs error=3.12805e−05、median relative=1.06140e−04、weighted relative=1.12838e−04、Pearson=0.9999999956；比值 median=0.9998983，范围0.9996282…1.0012995。支持同一面功率数值一致，不是独立 solver 或第二面验证。
- C_PW 与 saved native-grating T_FDTD 绝对总功率有显著差异：378/420；median relative error=1.10671186、Pearson=0.81534495、功率比 median=2.19804917。现有源码审查指出 T_FDTD 依赖对 E/H 面的平均近似零阶通量，再用 grating eta 缩放总量；不能用该绝对量独立校验 C_PW。
- 2940 order 行的 normalized eta correlation=0.99999994、median relative error=3.97963e−04、eta ratio median=1.00019881（范围0.9972663…1.0023934）。该 routing 比较仍复用同一 HF 的输出和场。
- grating order fraction 求和为 T_FDTD、以及 R/T/A 算术闭合，属于代数闭合，不是独立物理验证。
- grating 对照没有复数相位数据；C_PW 相位只有合成回归检查，无独立场面相位验证。

## POSTNP=1800 的历史依据

builder scripts/shared_fdtd/tools/build_medium_pw_setup_only_v1.py（SHA256 2b297e8ecfe203e56def9e0f10b0550b3eaa6ae09e6e2157cba6d0cc2381ac05）第107行设置 MON_POSTNP=1800 nm。Git 历史：
- 2026-09-21 commit 7c0bb4374d59017ee64e099bfcb0a63b2cd4aed 使用旧 POSTNP=2212 nm。
- 2026-09-24 commit 997efcdb97da7ed86f127ce152c191c623564e46（freeze monitor sample and reference plane authority）改为 POSTNP=1800 nm、PRENP=1150 nm，冻结 POSTNP_REF=1722 nm。

authority 文档解释 sample/reference 职责并拒绝旧坐标，但未记录选择1800的原始物理/几何推导或高度收敛研究。历史证据只能说明1800作为冻结 sample coordinate 替代旧 wiring；“Air侧、距 NP 顶约88nm名义/90nm实际”是当前几何推论，不能冒称原始选择理由。

## 独立第二面与下一步

H5 四个 z-normal 面约为 IN −100.788、PRENP 1152、POSTNP 1802、reflection −400 nm。NP底在1212 nm，PRENP 在底面以下60 nm的 spacer 内，不是第二个同一均匀空气区样面；其余面在器件下方。raw NPZ 也仅含 IN/PRENP/POSTNP 三面，POSTNP 仅一个 z。故没有可用的独立第二空气面，本次不报告双高度 de-embedding parity。把同一个场解析传播到别的 z 不独立。

最小后续建议（DO NOT EXECUTE）：另行授权1个 solver-entered EXT02 case，保持相同几何/材料/边界/源和生产POSTNP=1800 nm，增加只用于验证的完整二维 E/H 面，名义 z=2000 nm。求解后先读取真实网格采样 z，确认两面均处于同一 Air 区；分别投影，再将七个传播阶 +z TE/TM 复系数去嵌到同一1722 nm参考面，比较复振幅/相位、逐阶功率、总传播功率与面通量。预算是一个新 entered case，按项目规则预先记账；不需为解析传播另开第二次求解。保留原生产 monitor 和EXT02 attempt，不覆盖历史truth。该方案需要独立授权，本次未执行。

## 结论

POSTNP实际面约1802 nm，NP真实柱顶到采样面约90 nm；1722 nm只距柱顶10 nm。Truth extractor 是全周期二维 E/H Floquet 模态分解，七阶覆盖全波段空气传播阶。现有 power/routing 对照支持同一场面的数值一致性，但不能验证跨高度复相位；native-grating绝对总功率有已知归一化差异。1800 nm有冻结历史但无原始选值推导。独立第二个空气高度场面缺失，因此仅该项未闭环。

方法参考：Ansys monitor 插值/采样属性、mesh 坐标读取、PML 层厚依赖网格说明：
https://optics.ansys.com/hc/en-us/articles/360034902393-Frequency-domain-monitor-Simulation-object
https://optics.ansys.com/hc/en-us/articles/360034382574-Tips-for-getting-the-actual-mesh-size-in-FDTD
https://optics.ansys.com/hc/en-us/articles/360034382414-Always-extend-structures-through-PML-boundary-conditions
