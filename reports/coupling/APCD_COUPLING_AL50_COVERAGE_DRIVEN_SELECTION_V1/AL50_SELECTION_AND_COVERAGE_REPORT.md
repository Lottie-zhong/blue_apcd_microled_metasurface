# AL50_SELECTION_AND_COVERAGE_REPORT

## 状态与AL16正式收尾

**AL50_FAST_PRODUCTION_READY**，仅理想几何FAST生产包准备。NEW_FDTD=0，NEW_ENTRY=0，NEW_ML_FITS=0，AL50_AUTHORIZED=0。

172G合法开发集完整，AL16为16REALentries/16labelsvalid/0Replay，16案FSP/原生H5/scienceH5/609D路径均存在且原验收/独立对账保留。原156与新增16具有同冻结physics、21lambda/7order/TE-TM/reference/H1/H2定义及5nm3ps训练级合同，实际制造资格未建立、严格收敛未闭合。sealedresponse未访问，DOE56/DIAG2不入训练。

基于已保存OOF零拟合重算同124heldout几何，逐目标MAE与原报告误差<1e-12，450nmmeanfoldrho同样一致；旧32保持train-only，原new124分折未改。历史before指标复用原保存结果，未伪造已丢失的旧pooledOOF/Topk。见AL16_MODEL_METRIC_RECHECK_ZERO_FIT.json。ExtraTreesP+谱MAE0.0315207→0.0313934，rho−0.04649→−0.04455；仍无可靠排名，不能以预测最高功率作为选样依据。

## 六维覆盖与稀疏诊断

172G轴覆盖[D1..D6]=[27,25,27,27,27,27]。D2=130/185nm各0，AL16并未补到。其余五轴虽都有27档，样本数不均匀，不能当作覆盖充分。

|轴|172G缺失档位|172G样本数<=2的档位nm|归一化边际熵172→候选222|候选222最小档位样本数|
|---|---|---|---|---:|
|D1|无|[130, 135, 140, 190, 205]|0.9263→0.9448|2|
|D2|[130, 185]|[130, 185, 205]|0.9450→0.9616|2|
|D3|无|[170]|0.9526→0.9437|1|
|D4|无|[130, 165, 190, 215]|0.9331→0.9427|2|
|D5|无|[205]|0.9520→0.9597|3|
|D6|无|[140, 150, 170, 185]|0.9502→0.9669|3|

若全部50有效：总开发集222G、六轴均27档，D2=130/185各增至2例。其余未选原池上最近样本距离均值0.369385→0.346094（预计下降6.31%）；全池距离中位数0.374877→0.350401。候选间最小归一化距离0.405217，距离为Euclidean(D/130nm)。这是前瞻几何指标，没有新的物理数据或学习增益。

D3=170nm仍只有1例，部分边界档位较多；边际熵可能略降，不隐瞒。联合maximin为主、六轴稀疏bonus为辅，不声称50案使边际分布完全均匀。应在未来16/32/50阶段复查这些稀疏区与实际误差。D2仅2个强制补洞名额，不占用整个覆盖组；50案来自原8192有序池，不重新生成或扩域。

## 选样规则与完整50案

30coverage(60%)+10rawdisagreement(20%)+10stratifiedrandom(20%)。前两coverage分别在D2=130/185中选六维最远点；另外28coverage按联合最近距离乘温和六轴占用补偿得分，已在生成前记录算法。10disagreement直接复用172G模型已保存的未校准分歧，要求多样性目标距离>=0.4；不是置信区间、更不是最高预测效率。随机组seed20261018，在均值柱径十个分位层各选1案，保持有序维度。

|Case|D1,D2,D3,D4,D5,D6 nm|组别|原池索引|
|---|---|---|---:|
|K6AL_FAST_R02_G001|230,130,100,125,185,155|coverage|7954|
|K6AL_FAST_R02_G002|135,185,100,145,230,105|coverage|2316|
|K6AL_FAST_R02_G003|130,220,160,140,170,165|coverage|2094|
|K6AL_FAST_R02_G004|155,220,210,230,215,155|coverage|3619|
|K6AL_FAST_R02_G005|225,170,230,225,165,200|coverage|7753|
|K6AL_FAST_R02_G006|220,165,160,230,100,100|coverage|7432|
|K6AL_FAST_R02_G007|230,105,230,170,160,170|coverage|7909|
|K6AL_FAST_R02_G008|170,105,100,130,165,195|coverage|4260|
|K6AL_FAST_R02_G009|170,125,225,100,225,170|coverage|4314|
|K6AL_FAST_R02_G010|115,135,160,100,170,180|coverage|994|
|K6AL_FAST_R02_G011|175,150,100,100,160,125|coverage|4664|
|K6AL_FAST_R02_G012|175,160,225,225,155,110|coverage|4695|
|K6AL_FAST_R02_G013|165,220,100,160,185,220|coverage|4216|
|K6AL_FAST_R02_G014|225,190,100,110,110,140|coverage|7787|
|K6AL_FAST_R02_G015|100,145,130,160,100,100|coverage|102|
|K6AL_FAST_R02_G016|205,170,225,110,120,130|coverage|6536|
|K6AL_FAST_R02_G017|220,120,230,100,185,215|coverage|7336|
|K6AL_FAST_R02_G018|145,115,100,205,230,110|coverage|2766|
|K6AL_FAST_R02_G019|160,100,210,165,125,160|coverage|3650|
|K6AL_FAST_R02_G020|205,110,150,185,160,185|coverage|6396|
|K6AL_FAST_R02_G021|195,225,100,145,230,140|coverage|6046|
|K6AL_FAST_R02_G022|105,210,105,190,125,165|coverage|551|
|K6AL_FAST_R02_G023|180,225,225,230,220,220|coverage|5145|
|K6AL_FAST_R02_G024|160,175,120,170,225,170|coverage|3812|
|K6AL_FAST_R02_G025|225,100,215,105,120,180|coverage|7596|
|K6AL_FAST_R02_G026|150,170,200,225,155,215|coverage|3199|
|K6AL_FAST_R02_G027|105,110,130,155,105,225|coverage|327|
|K6AL_FAST_R02_G028|220,220,135,170,180,130|coverage|7555|
|K6AL_FAST_R02_G029|225,105,100,140,110,110|coverage|7597|
|K6AL_FAST_R02_G030|170,140,145,230,100,220|coverage|4342|
|K6AL_FAST_R02_G031|180,125,165,230,230,110|disagreement|4915|
|K6AL_FAST_R02_G032|215,220,100,145,170,230|disagreement|7248|
|K6AL_FAST_R02_G033|175,170,230,195,125,160|disagreement|4717|
|K6AL_FAST_R02_G034|190,155,225,155,105,115|disagreement|5596|
|K6AL_FAST_R02_G035|215,110,190,190,140,220|disagreement|7009|
|K6AL_FAST_R02_G036|100,175,205,210,220,105|disagreement|175|
|K6AL_FAST_R02_G037|120,165,175,180,100,230|disagreement|1366|
|K6AL_FAST_R02_G038|190,130,205,230,195,110|disagreement|5536|
|K6AL_FAST_R02_G039|195,115,165,210,175,230|disagreement|5803|
|K6AL_FAST_R02_G040|190,110,230,150,160,215|disagreement|5493|
|K6AL_FAST_R02_G041|150,115,175,100,115,175|stratified_random|3073|
|K6AL_FAST_R02_G042|195,125,160,150,140,125|stratified_random|5827|
|K6AL_FAST_R02_G043|185,160,100,140,155,180|stratified_random|5294|
|K6AL_FAST_R02_G044|135,125,185,135,200,165|stratified_random|2187|
|K6AL_FAST_R02_G045|175,105,195,125,180,185|stratified_random|4568|
|K6AL_FAST_R02_G046|100,200,155,160,200,190|stratified_random|229|
|K6AL_FAST_R02_G047|200,170,145,180,170,150|stratified_random|6230|
|K6AL_FAST_R02_G048|205,160,115,210,200,160|stratified_random|6504|
|K6AL_FAST_R02_G049|105,230,230,135,175,220|stratified_random|606|
|K6AL_FAST_R02_G050|225,185,185,210,205,200|stratified_random|7783|

每案具体理由、原池位置、到172G及已选集距离、原始分歧值见AL50_SELECTED_GEOMETRIES.csv；完整六轴计数见COVERAGE_AND_SPARSE_DIMENSIONS.json。没有坐标排序或置换，没有新模型训练/预测来改变选样结论。

## 合法性、去重及科学身份

理想TiO2六柱：D100–230nm/5nm步长，中心x=[−725,−435,−145,145,435,725]nm、y0，节距290、柱高500、固定975nm MDC与237nmSiO2Spacer；周期1740×290nm。逐案检查相邻及周期D6→D1间隙、Y周期间隙、halfcell余量和H/D；全50非重叠且满足原mesh覆盖。实际工艺最小间隙/侧壁/最大深宽比未获得独立规范，保留UNRESOLVED，不以几何测量发明制程硬门槛。

刷新全部先前已核验保护几何、已计算172G、失败/历史Entry、DOE56全56预留、DIAG2两身份、sealed仅几何元数据、已知runtime queue/source/batch manifests及正式V31jobs/entries。50案内部唯一，对全部已核验保护集合交集0。DEDUPLICATION_AUDIT列明完整来源和canonical快照；未登记的外部手动任务无法穷尽，正式授权前需刷新同一已知registry，不宣称全服务器未知任务绝无冲突。

Case为K6AL_FAST_R02_G001…G050，attempt_001，ExecutionID=coupling:<case>/attempt_001。科学预算候选AL50_FAST_R02_BUDGET_PROPOSAL_V1请求最多50entry，每案1，当前授权0；所有Job/Entry映射null，未生产submit，不复用AL16或DIAG2身份/预算。隔离接口fixture含50schema注册记录、0Entry，不是生产登记。

## FSP、SHA和正式接口

50独立setupFSP已保存并重新LOAD核验。复用已认证setup-only模板，只恢复最大3ps及修改各案有序半径；其余已审计材料、源、MDC、Spacer、monitor、boundary、网格与reference不变；两个既有冻结X-forward源对象保持原样，不自行重建源。5nm/3ps/auto-shutoff1e-6，440–460nm21点，3D/P_XLIKE；FDTD物理时长与平台排程分开。

原physics SHA32e60a…dea5的哈希范围沿用原六字段规则，完整时间/mesh由FAST_NUMERICAL_CONTRACT、FSP SHA及实际readback绑定，不伪称physics SHA独自编码全部setup。逐案输入路径、完整SHA、ExternalExecutionID、输出目录、checks与预算候选都在AL50_FAST_PRODUCTION_MANIFEST.json/SHA_INVENTORY。没有覆盖任何历史FSP/H5。

科学总包是wrapper；正式Runner输入为runner_manifests/每案单Job JSON，以submit/run/status执行，保持truth-before-next。已安装冻结Runner解析器在隔离SQLite接受50输入，跨batch重复身份和错误SHA均被拒；含提取脚本import/无solver静态检查及旧模型指标复核，共55PASS/0FAIL，real/fake run均0。安装RunnerSHA5778eefb…cb7不变，无部署/调度平台开发。

提取脚本复用AL16已实证的只读FSP→复杂EH→原生H5检查→冻结post/H1/H2→609D及21eta/P_scale/H2P+；只改新包路径/案例角色，不改科学公式。前瞻50案尚无truth/labels，离线PASS不等于物理有效。labels-valid receipt且Entry独立对账后才可进入FAST，所有失败原生证据保留、禁止solverReplay。science_entry_authorized=false不是Runner强制安全锁，Coupling必须依据未来明确人类授权与科学预算控制入场。

## 预算、成本与调度

沿用AL16实测9.6232min/Runner调用、11.7091min/至科学验收服务：50次规划求解调用约8.02h、服务约9.76h；若案间门禁节奏相同，墙钟约10.13h。均非保证，不含未来几何差异/资源等待和阶段性模型评估延迟。
50entry在100%/90%/80%有效率情景下分别新增50/45/40有效几何，即222/217/212G；90/80%为规划情景，不是已测新批次成功率。失败消耗entry，不自动补足50、不借DIAG2预算；无报价依据不报货币成本。

北京时间21:00–次日10:00仅PREFERRED_GPU_WINDOW，可跨夜；白天实际资源安全且获得授权时可运行，10:00不截断既有FDTD。允许他人CPUFDTD/EDT/GUI，只有实际GPU/CPU/RAM/许可证/磁盘或未知资源门禁冲突延后新entry。正式入场必须实时检查，准备态不对未来资源背书。

## 16/32/50阶段科学与学习验收计划

未来若获完整授权，逐案串行入场、native保存、科学receipt与Entry原子对账。新增有效几何到16/32/50时，暂停新增entry做零求解模型评估（可用CPU），总开发规模188/204/222。若50entry结束仅有较少有效标签，则按实际数做最终评估，不自动新建case补额。

保留172G基线的old32train-only与既有140个heldoutID/四折；新增50按冻结case顺序mod4分折，同几何不跨折，预处理仅训练折。相同140heldout给出before/after，旧124另列长期可比表，新50cohort独立OOF，避免主动选样偏倚伪装随机总体测试。采用原固定Mean/KRR/ExtraTrees/小MLP及种子，不新建复杂网络。

每阶段报告谱P+/eta/Pscale MAE/RMSE、450nmmeanfoldSpearman及独立pooled、Top20%ceil(n*.2)recall/regret及固定IDties规则、invalid预测、六轴与联合覆盖、有效几何/GPUh、失败成本。OOF先持久化再reload；已有172OOF可零拟合给出同140基线，历史缺失OOF不伪造。模型暂不改善不授权修改冻结物理合同；只有系统性科学合同/数据/安全异常暂停新entry，不因时间窗口kill solver。

## 最终边界

准备态理想几何科学输入与接口准入READY，实际可制造性UNRESOLVED，真实生产需用户单独授权及启动前实时资源/registry复核。本轮NEW_FDTD=0，AL50_AUTHORIZED=0，DIAG2=1/2，A2 HOLD，DOE56 HOLD。原科学Ledger和172G/模型资产保留。
