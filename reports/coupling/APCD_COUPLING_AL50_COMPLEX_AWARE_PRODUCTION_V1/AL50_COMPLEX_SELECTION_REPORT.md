# AL50 Complex-Aware Selection Report

状态：50案固定；真实入场由PRODUCTION_HARD_GATES与独立授权共同控制。

正式路线：Geometry → C_hat复数Floquet + P_scale → Frozen H2。目标布局588 Cartesian+21 logP，B29按原609D顺序重组。

## 轻量诊断

仅复用既有124个几何OOF，未重跑旧折。种子分歧与TM MSE Spearman=0.41858693941778125；A/B分歧=0.179405192761605。仅统计关联，非校准不确定性。

TM幅度收缩、几何间方差及各阶Routing见LIGHTWEIGHT_ERROR_DIAGNOSTIC.json。冻结H2中相位不直接改变正交模态功率，但必须保留复数609D主线。TE近零相位不作为高权重优化目标。

## 选样

28覆盖＋10功率加权TM复数/阶分配分歧＋6分层随机＋6局部补充。不按预测高效率选样。新做6次全222G模型拟合仅用于8192池采集分歧，不替代OOF，不重复既有训练；参数与先前ET相同。

全池平均最近距离：0.34785475565476565 → 0.3320909891316174，后者仅为新增50均有效的前瞻覆盖。距离单位为有序六径/130nm欧氏距离。

局部6点从两个既有old32训练专用锚点构成D2-D3及D6-D1完整四角设计；三缺角各补3点。锚点及其家族不进入原124验证。不把训练内局部拟合称为独立泛化。

## 全部有序几何

|Case|Role|D1…D6 / nm|Pool index|
|---|---|---|---|
|K6AL_COMPLEX_R03_G001|coverage|200, 230, 105, 220, 230, 160|6359|
|K6AL_COMPLEX_R03_G002|coverage|105, 225, 220, 140, 125, 175|594|
|K6AL_COMPLEX_R03_G003|coverage|170, 230, 230, 100, 230, 125|4550|
|K6AL_COMPLEX_R03_G004|coverage|145, 175, 110, 105, 110, 150|2901|
|K6AL_COMPLEX_R03_G005|coverage|220, 180, 170, 225, 225, 110|7469|
|K6AL_COMPLEX_R03_G006|coverage|100, 220, 175, 160, 145, 115|275|
|K6AL_COMPLEX_R03_G007|coverage|220, 225, 170, 105, 175, 220|7569|
|K6AL_COMPLEX_R03_G008|coverage|105, 175, 105, 165, 185, 160|474|
|K6AL_COMPLEX_R03_G009|coverage|230, 220, 160, 100, 100, 225|8164|
|K6AL_COMPLEX_R03_G010|coverage|105, 190, 100, 230, 105, 220|506|
|K6AL_COMPLEX_R03_G011|coverage|120, 135, 190, 100, 220, 105|1302|
|K6AL_COMPLEX_R03_G012|coverage|230, 100, 155, 125, 175, 230|7893|
|K6AL_COMPLEX_R03_G013|coverage|120, 140, 185, 225, 165, 110|1312|
|K6AL_COMPLEX_R03_G014|coverage|145, 220, 105, 100, 190, 140|3000|
|K6AL_COMPLEX_R03_G015|coverage|195, 145, 175, 215, 100, 160|5873|
|K6AL_COMPLEX_R03_G016|coverage|210, 130, 160, 155, 225, 145|6748|
|K6AL_COMPLEX_R03_G017|coverage|130, 185, 160, 230, 175, 150|2018|
|K6AL_COMPLEX_R03_G018|coverage|230, 165, 230, 180, 220, 105|8044|
|K6AL_COMPLEX_R03_G019|coverage|105, 155, 125, 175, 100, 165|429|
|K6AL_COMPLEX_R03_G020|coverage|120, 195, 165, 185, 225, 185|1434|
|K6AL_COMPLEX_R03_G021|coverage|110, 180, 230, 100, 130, 230|798|
|K6AL_COMPLEX_R03_G022|coverage|115, 150, 200, 225, 225, 230|1031|
|K6AL_COMPLEX_R03_G023|coverage|230, 220, 200, 145, 115, 110|8167|
|K6AL_COMPLEX_R03_G024|coverage|105, 100, 130, 150, 180, 220|304|
|K6AL_COMPLEX_R03_G025|coverage|100, 215, 185, 165, 155, 215|265|
|K6AL_COMPLEX_R03_G026|coverage|220, 175, 110, 135, 165, 110|7451|
|K6AL_COMPLEX_R03_G027|coverage|150, 105, 220, 185, 165, 105|3055|
|K6AL_COMPLEX_R03_G028|coverage|180, 105, 170, 100, 225, 200|4872|
|K6AL_COMPLEX_R03_G029|complex_disagreement|130, 225, 165, 135, 230, 145|2106|
|K6AL_COMPLEX_R03_G030|complex_disagreement|130, 230, 135, 125, 185, 140|2117|
|K6AL_COMPLEX_R03_G031|complex_disagreement|150, 100, 135, 165, 155, 135|3037|
|K6AL_COMPLEX_R03_G032|complex_disagreement|230, 205, 135, 140, 220, 140|8126|
|K6AL_COMPLEX_R03_G033|complex_disagreement|170, 130, 145, 170, 125, 190|4318|
|K6AL_COMPLEX_R03_G034|complex_disagreement|130, 220, 155, 210, 165, 185|2093|
|K6AL_COMPLEX_R03_G035|complex_disagreement|140, 165, 160, 130, 190, 140|2577|
|K6AL_COMPLEX_R03_G036|complex_disagreement|135, 230, 155, 190, 140, 155|2419|
|K6AL_COMPLEX_R03_G037|complex_disagreement|145, 100, 230, 100, 170, 155|2741|
|K6AL_COMPLEX_R03_G038|complex_disagreement|130, 225, 170, 125, 205, 115|2108|
|K6AL_COMPLEX_R03_G039|stratified_random|120, 155, 115, 215, 130, 110|1340|
|K6AL_COMPLEX_R03_G040|stratified_random|125, 135, 155, 110, 185, 220|1596|
|K6AL_COMPLEX_R03_G041|stratified_random|175, 190, 130, 125, 180, 170|4756|
|K6AL_COMPLEX_R03_G042|stratified_random|200, 125, 185, 155, 175, 175|6132|
|K6AL_COMPLEX_R03_G043|stratified_random|175, 195, 210, 100, 160, 230|4773|
|K6AL_COMPLEX_R03_G044|stratified_random|150, 135, 220, 225, 205, 175|3120|
|K6AL_COMPLEX_R03_G045|local_interaction|215, 110, 215, 230, 105, 130|None|
|K6AL_COMPLEX_R03_G046|local_interaction|215, 105, 220, 230, 105, 130|None|
|K6AL_COMPLEX_R03_G047|local_interaction|215, 110, 220, 230, 105, 130|None|
|K6AL_COMPLEX_R03_G048|local_interaction|205, 215, 105, 225, 180, 105|None|
|K6AL_COMPLEX_R03_G049|local_interaction|210, 215, 105, 225, 180, 100|None|
|K6AL_COMPLEX_R03_G050|local_interaction|210, 215, 105, 225, 180, 105|None|

## 合同与边界

100–230nm/5nm步长，有序六柱，柱心距290nm，柱高500nm；237nm spacer、顶部MDC、材料和参考面保持冻结；440–460nm/1nm，X/P_XLIKE，5nm/3ps。仅理想几何准入，实际制造UNRESOLVED。

全历史去重包括222合法几何、注册失败/已入场身份、保护几何元数据、V1移出案例和已知队列；不读取sealed响应。具体来源及生产SQLite只读快照见DEDUPLICATION_AUDIT.json。未知未注册手工工作不被虚称已穷尽。

独立新预算最多50，一案一次真实entry；失败消耗、不Replay、不替换。DIAG2 1/2、A2 HOLD、DOE56 HOLD。此批后无下一轮授权。

验证固定原124，训练专用old32及相连家族严格隔离；16/32/50有效新增样本阶段比较222G基线。主模型A609、B29、KRR/ET及Mean，冻结H1/H2。功率常数Mean仅额外评估参考，绝非直接功率代理替代。
