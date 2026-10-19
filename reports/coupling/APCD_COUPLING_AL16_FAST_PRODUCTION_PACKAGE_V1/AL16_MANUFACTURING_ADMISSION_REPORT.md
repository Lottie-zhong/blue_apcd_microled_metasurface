# AL16_MANUFACTURING_ADMISSION_REPORT

**AL16_FAST_PRODUCTION_READY — 仅理想几何FAST仿真生产包；真实求解未授权。**

## 准入范围与权威

用户本轮明确回复：“本轮批准理想几何FAST仿真准入，实际制造资格仍UNRESOLVED”。据此16案可作为理想几何仿真候选，不宣称实际可制造。该裁决不授权任何Solver Entry。原历史候选域仅证明观察到的100–230nm/5nm步长、有序D1…D6、290nm节距、500nm柱高；原文件明确制造限值未建立，且旧扩展限制于冻结候选池。本次批准仅适用于当前16提案理想仿真包，不将整个27^6空间追认为工艺合法。

已检索正式worktree的configs/docs/相关科学脚本、PW_K6_GEOMETRY_DOMAIN_AUTHORITY_V1、冻结NP/monitor/temporal合同、历史合法几何与已核验制造审计；并查找可识别GDS/工艺文件名。未找到独立柱间隙/深宽比/侧壁工艺规范。材料配置Native-M1是电磁材料合同，不是沉积/刻蚀资格证明；不以历史合法仿真等同实物工艺验证。

## 16案逐案检查

|Case|D1,D2,D3,D4,D5,D6 nm|min X gap|min Y gap|min halfcell|H/D range|准入|
|---|---|---:|---:|---:|---|---|
|K6AL_FAST_R01_G001|230,100,135,210,100,170|90|60|30|2.174–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G002|225,100,120,100,230,200|75|60|30|2.174–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G003|100,100,100,100,145,225|105|65|32.5|2.222–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G004|100,200,200,230,195,200|75|60|30|2.174–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G005|220,100,165,195,160,100|110|70|35|2.273–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G006|225,145,115,100,160,230|62.5|60|30|2.174–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G007|100,230,150,105,230,140|100|60|30|2.174–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G008|225,225,230,115,165,115|62.5|60|30|2.174–4.348|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G009|105,125,145,115,100,155|155|135|67.5|3.226–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G010|225,225,110,205,130,225|65|65|32.5|2.222–4.545|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G011|220,170,195,120,180,180|90|70|35|2.273–4.167|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G012|165,205,100,200,170,150|105|85|42.5|2.439–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G013|185,140,105,180,150,145|125|105|52.5|2.703–4.762|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G014|200,165,100,205,170,105|102.5|85|42.5|2.439–5.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G015|180,150,160,125,185,200|97.5|90|45|2.500–4.000|理想仿真PASS / 制造UNRESOLVED|
|K6AL_FAST_R01_G016|185,200,220,125,210,175|80|70|35|2.273–4.000|理想仿真PASS / 制造UNRESOLVED|

列值均为几何测量，不是新发明的工艺门槛。X gap包含D6→下一周期D1；Y gap为290−Di；halfcell=(290−Di)/2。六柱中心固定x=[−725,−435,−145,145,435,725]nm，y=0；不排序、不交换。1740×290nm周期，固定975nm MDC、237nm SiO2 spacer、500nm理想垂直TiO2圆柱。最小周期X gap62.5nm，Y gap60nm，halfcell30nm；整批最小直径100nm，对应最大H/D=5。所有直径满足既有观察域/5nm离散网格，所有几何非重叠、全周期网格覆盖通过。

**实际制造仍UNRESOLVED**：允许最小柱间隙、实际最小边界余量、最大H/D、最小可刻蚀直径、柱高公差、TiO2沉积/刻蚀与侧壁锥度/粗糙度/圆度限制。用户以后若要求实际制造资格，需提供这些参数或正式工艺规范；本轮依据理想仿真裁决不将它们作为虚构硬阈值。

## 保留与替代

原16案全部保留，替换0。没有已证实违反本轮理想几何准入的候选；不因缺少工艺规则就随意换几何。8192候选池不重建，8coverage+4disagreement+4stratified-random不改变，不使用预测最高效率作为唯一选样依据。

## 去重与科学身份

刷新全部先前已核验保护几何元数据、历史已计算/已入场/失败注册、DOE56全56保护、DIAG2保留几何、sealed仅几何元数据，以及已知runtime source/queue/batch manifests和canonical V31 jobs/entries。当前16内部唯一、已知保护几何冲突0；详见DEDUPLICATION_AUDIT.json。未读取sealed响应，未将DOE56诊断数据合并训练。未注册的手工外部任务不在可证明集合内，因此正式授权submit前仍要刷新同一registry与队列快照，不能宣称不存在未知执行器。

Case ID为K6AL_FAST_R01_G001…G016，attempt_001；ExternalExecutionID为coupling:<case_id>/attempt_001。均未提交生产Runner、未创建生产Job/Entry。16次是独立AL预算提案，当前授权0；不消费DIAG2剩余1次，不改变旧科学Ledger。

## FSP/科学合同

16个独立pre.fsp已生成并逐案重新LOAD核验。模板为已认证6ps setup-only输入，校验原SHA后只恢复最大物理时间3ps、修改有序柱半径；保留其余已审计源/材料/monitor/mesh/MDC/spacer。模板两个冻结X-forward源对象原样保留，没有新增或关闭源。源标签P_XLIKE不被解释为随意重建单源。完整有限字段readback与逐案差分在checks目录。

物理字段继续使用原32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5，其原哈希范围仅冻结六字段physics，不能声称该SHA本身编码所有时间/网格参数。另以FAST_NUMERICAL_CONTRACT、实际FSP SHA和fresh-load readback绑定5nm/3ps、auto-shutoff1e-6。没有新的canonical规则或替换expected SHA。

逐案FSP绝对路径及完整SHA见AL16_FAST_PRODUCTION_MANIFEST.json、SHA_INVENTORY.json；原FSP/H5均未覆盖。新输入在本任务inputs/<case>/attempt_001/pre.fsp。所有science_outputs是预期路径，当前不伪造任何新标签或truth。

## 测试与结论

直接使用已安装Runner的submit解析器，在本任务隔离fixture SQLite中注册16案，未调用real或fake run。16输入/schema接受，跨batch重复ExternalExecutionID拒绝、错误SHA拒绝、fixture entries=0；Extractor import/无solver API静态检查通过。生产SQLite与原Ledger只读/未改。原11+8及A1原生FSP/H5/609D证据复用，不重跑历史提取或模型。

新16案尚无物理输出；接口PASS不等于新truth/labels有效。实际执行后必须完成独立GPU日志、停止状态、nativeH5/复杂场、冻结后处理、标签及Ledger验收，再入训练库。
