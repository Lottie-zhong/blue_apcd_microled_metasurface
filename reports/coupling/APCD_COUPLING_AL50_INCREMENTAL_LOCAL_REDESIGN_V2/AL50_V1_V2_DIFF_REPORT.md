# AL50_V1_V2_DIFF_REPORT

## 最终裁决

**AL50_LOCAL_GLOBAL_V2_PRODUCTION_READY**，理想几何FAST准备态。NEW_FDTD=0、NEW_ENTRY=0、NEW_FITS=0、AL50_AUTHORIZED=0。保留原40案，仅替换10案，不增加原50entry候选上限。

|角色|V1|V2|
|---|---:|---:|
|全局覆盖|30|30|
|模型分歧|10|8|
|分层随机|10|2|
|单柱局部|0|8|
|双柱交互补充|0|2|
|合计|50|50|

原30coverage、所有D2=130/185补充案例均保留；分歧组保留前8，随机组强制保留D2=185的G050，再用全池覆盖损失最小原则选另1案。实际保留随机案为K6AL_FAST_R02_G044与K6AL_FAST_R02_G050。

## 1. 先审计既有局部信息

对历史172G与V1固定50案逐几何枚举单轴恰5nm邻边和六维任意双轴四角，不排序柱径。172G有11条原已labels-valid单柱配对，围绕K6V1_S31；V1计划50案没有新增这种邻边，原172+50中完整四角设计0。11条历史配对全部保留并优先利用，不为它们再求解。

标签溯源在LOCAL_GEOMETRY_NODE_INDEX.json、AL50_LOCAL_PAIR_GRAPH.csv：包含有序几何、Case ID、原生/输入FSP、SHA及标签/缓存Case键。历史609D仍指向原inventory/标签，新点标记NOT_RUN；旧32共享标签容器通过Case键区分。EXISTING_VALID_PAIR_DIFFERENCES.json保存11条已有配对的21λ P(+1)/eta/P_scale真实差分，仅描述既有全波响应，不冒充模型验证。

当前有效配对仍为11；新增12条是设计/混合边，必须等待新标签，不能称23条已有效。完整四角**设计2组、真值完整0组**。

## 2. 局部设计及新10案

D3=170nm唯一历史合法锚点K6GDP2_DEV_G059=[115,110,170,105,225,225]。对六柱各+5nm，再对D2/D3各−5nm，形成8个单柱新点；加D2+D3各+5nm交互角。另复用K6V1_S31=[220,195,210,150,140,210]及其已有D1+5/D6+5标签，只补D6+D1各+5nm角。

|新Case|有序D1…D6 nm|角色/原因|
|---|---|---|
|K6AL_FAST_R02V2_L001|120,110,170,105,225,225|K6GDP2_DEV_G059 D1 +5nm; D3sparseanchor|
|K6AL_FAST_R02V2_L002|115,115,170,105,225,225|K6GDP2_DEV_G059 D2 +5nm; D3sparseanchor|
|K6AL_FAST_R02V2_L003|115,110,175,105,225,225|K6GDP2_DEV_G059 D3 +5nm; D3sparseanchor|
|K6AL_FAST_R02V2_L004|115,110,170,110,225,225|K6GDP2_DEV_G059 D4 +5nm; D3sparseanchor|
|K6AL_FAST_R02V2_L005|115,110,170,105,230,225|K6GDP2_DEV_G059 D5 +5nm; D3sparseanchor|
|K6AL_FAST_R02V2_L006|115,110,170,105,225,230|K6GDP2_DEV_G059 D6 +5nm; D3sparseanchor|
|K6AL_FAST_R02V2_L007|115,105,170,105,225,225|K6GDP2_DEV_G059 D2 -5nm; D3sparseanchor|
|K6AL_FAST_R02V2_L008|115,110,165,105,225,225|K6GDP2_DEV_G059 D3 -5nm; D3sparseanchor|
|K6AL_FAST_R02V2_I001|115,115,175,105,225,225|K6GDP2_DEV_G059 interactionD2-D3 +5nm/+5nm|
|K6AL_FAST_R02V2_I002|225,195,210,150,140,215|K6V1_S31 interactionD6-D1 +5nm/+5nm|

|组|锚点|柱对|既有有效角|待求解角|当前状态|
|---|---|---|---:|---:|---|
|INTERACTION_01|K6GDP2_DEV_G059|D2-D3|1|3|设计完整，真值未完整|
|INTERACTION_02|K6V1_S31|D6-D1|3|1|设计完整，真值未完整|

两个不同锚点、两个不同柱对，包括D2与周期边界D6-D1。S31复用3角、G059复用1角，不重复消耗历史预算。新增8单柱点与2双柱角都采用完整集成MDC+K6 3DFDTD FAST，未使用孤立柱叠加，也不把交互索引写入/修改正式609D目标。本文仅实施用户明确的局部四角设计，不外推未提供论文的机理结论。

## 3. 覆盖取舍与信息收益边界

相同剩余原8192池上最近数据点距离均值：V1 0.346094→V2 0.350137，增加1.17%（覆盖损失）；最坏距离均为0.530156，未恶化。若全50有效，D2=130/185各仍2例，D3=170从V1的1例增至V2的7例；六轴各27档保持。

局部组故意相距5nm，不再适用V1全局采样最小距离0.4；这是实验角色改变，非几何非法或制造门槛放宽。原30覆盖未动，只用10非覆盖槽换取12条新待验局部边及2个四角设计。新增局部点由用户明确5nm扰动规则派生，可能不属于原8192离散抽样行，但均在100–230/5nm合法理想域；来源不伪装成原池选中。

预计信息收益是同锚点差分、符号和非加性交互可以被观察；并未证明代理MAE、排序或全空间泛化会改善。有效四角依赖所有必要角labels-valid，若失败不补额、不把缺角组标为完整。

## 4. V1归档、身份与预算

V1原目录及50个FSP/manifest原样保留，V1_ARCHIVE_REFERENCE记录归档引用。40保留案复用完全相同的FSP路径/字节SHA、Case ID、Attempt、ExternalExecutionID与单案Runner manifest；输出目录也沿原映射。10被移出案在本轮声明SUPERSEDED_ZERO_ENTRY，原文件不删除、不改写，futureconsumer不得再把这些案算作V2候选。

10新案使用K6AL_FAST_R02V2_L001…L008及I001/I002，独立输入路径/SHA/ExecutionID；没有把旧ExecutionID绑定到新FSP。V1与V2是同一50-entry候选预算的互斥版本，当前只能审阅V2，不允许两版分别授权后叠加100entry。没有生产submit/Entry；fixture注册只在隔离SQLite，Entry0。全历史保护/失败/DOE56/DIAG2/sealed仅几何元数据、172已计算、全部V1保留及移出几何、已知runtimequeue与canonicalDB已刷新去重；新10与保护集合冲突0，V2内部50唯一。

## 5. 精度与接口不变

原5nm/最大3ps、auto-shutoff1e-6、21λ440–460nm、Native-M1、固定975nm顶部MDC与237nmSpacer、500nm柱高、290nm心距、两冻结X/P_XLIKE源、monitor/reference/TE-TM/Floquet/H1/H2/609D均不变。10新FSP仅修改有序半径及恢复3ps，与模板其余审计属性一致；40旧FSP无重建。实际制造资格仍UNRESOLVED，理想几何仿真准入；训练级不是最终收敛级。

独立新consumer仅将原只读提取器指向V2manifest，保留案及新案均按case-record输出，不改冻结后处理。Runner冻结源码SHA5778eefb…cb7不变，无部署或平台开发。输入、预算映射和单案V3.1 manifests见AL50_FAST_PRODUCTION_MANIFEST_V2.json / SHA_INVENTORY_V2.json。

## 6. 家族防泄漏与评估

原124heldout几何身份与指标口径保留。发现历史S31锚点属old32，而其11扰动分布在原四折验证中，因此不能把旧几何分组成绩冒称局部家族独立泛化。

双轨报告：原协议继续作为legacy对比，不宣称family-independent；额外严格轨保持相同124heldout IDs，对任何触及验证的局部连通家族，清除其所有训练成员。被purge的old32不移入验证。未来172G baseline与V2 after必须采用相同purge重算后再比，不能拿未purge旧指标与purge新指标混比。本轮只做索引验证，不训练。

G059及9个新家族成员统一归原锚点第3折，整个家族同时留出。S31旧32锚点不作测试样本；其完整四角可在truth闭合后报告真实物理非加性交互，但不宣称该family模型out-of-sample局部能力。严格局部模型指标只有一个可测锚点家族，样本范围有限；两个设计组不等于两个独立的heldout泛化家族。

指标：局部差分MAE=mean|ΔYhat−ΔY|，局部方向sign一致率（精确tie单列），家族内局部排序/成对次序一致率；非加性I=Yij−Yi−Yj+YD及|Ihat−I|（仅整个组符合heldout资格时）。Y使用同冻结21λ H2P(+1)、eta、P_scale。绝对差/原参考量并列，近零分母不虚构稳定相对量；5nm FAST差分仍带数值风险，不宣称制程导数或最终精度。无孤立柱近似。

继续新增有效16/32/50的零求解模型评估计划，固定Mean/KRR/ExtraTrees/小MLP与训练折预处理；模型不改善不改冻结科学合同。局部组不完整时留缺失状态，不伪造交互数值。

## 7. 验收与预计成本

V2完整55项输入/接口/旧OOF复核全部PASS，新增10项身份复用、归档保护、D2/coverage保留、新SHA/ExecutionID、23边差分/溯源、2四角/穷举、family泄漏purge及预算检查全部PASS；合计65PASS/0FAIL。隔离fixture50schemaJob/0Entry，real/fake run均0。复用验证器最后的终端打印路径已修正，没有重跑已通过55项，也没有科学改动。

总候选仍50，预计求解调用8.02h、科学服务9.76h、同门禁节奏墙钟10.13h；没有额外局部求解预算。仅10新setup，40重用。估计非保证，失败不Replay或自动补角。北京时间21:00–次日10:00为优先窗口，可跨夜和资源安全时白天运行，不强制截断。

最终：AL50_AUTHORIZED=0，NEW_FDTD=0，DIAG2=1/2，A2 HOLD，DOE56 HOLD。下一步仅等待对此V2固定50案的独立真实求解授权及启动前实时资源/registry复核。

执行顺序候选：先原G001/G002两案D2补洞输入，再10个新局部/交互案，然后其余38个保留案；便于新增16有效几何的首个检查点已含局部信息。总50集合、身份与预算不变，本轮不执行。
