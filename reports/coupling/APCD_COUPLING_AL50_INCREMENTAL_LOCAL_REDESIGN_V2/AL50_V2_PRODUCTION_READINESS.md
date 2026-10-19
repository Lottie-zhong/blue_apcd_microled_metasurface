# AL50_V2_PRODUCTION_READINESS

**AL50_LOCAL_GLOBAL_V2_PRODUCTION_READY**。

保留40/替换10；30coverage+8disagreement+2random+8单柱+2交互。V1整包原位归档，40案复用原Case/ExecutionID/FSP/SHA，10旧案SUPERSEDED_ZERO_ENTRY，10新案独立身份。V1/V2同一50entry候选预算，互斥而非叠加；当前授权0。

已有有效5nm局部边11，新增待求解边12，图总23；四角设计2组/2锚点，**truth完整0**。G059D2-D3待3角，S31D6-D1待1角。所有future真值必须是完整集成MDC+K6全波FDTD，609D不变。

覆盖平均距离较V1增加1.17%，最坏距离不变；原30coverage及D2补洞全保留，D3=170预计1→7。无局部必然改善代理的承诺。

原55项PASS+新增10项PASS，总65；新10FSP保存freshLOAD，40旧FSP不重建，全部active50在隔离安装Runner接口验收。无real/fake run、无生产submit/Entry、无模型fit。物理输入5nm3ps/440–46021点/MDC+237nmSpacer/有序TiO2六柱冻结，actual制造UNRESOLVED。

未来仅可基于AL50_FAST_PRODUCTION_MANIFEST_V2.json的active50授权，科学budgetcandidate授权前为0。读取单案runner_batches，逐案submit/run/status，fresh资源与全历史去重后入场，单案最多1、失败也计预算、NoReplay、truth-before-next。旧V1移出10案不得被消费者继续提交；不要运行旧V1总包。

16/32/50阶段采用LOCAL_FAMILY_EVALUATION_PLAN.json：保留124heldout身份；legacy与family-purged轨分开，matched172baseline也purge，G059全family第3折，S31old32不作为局部heldout测试；禁止锚点/扰动跨train/val。现阶段只验证路由，无新训练。

预计50次8.02h求解/9.76h科学服务；21:00–次日10:00优先非硬截止，跨夜/白天资源安全可灵活。当前AL50_AUTHORIZED=0，NEW_FDTD=0；DIAG2=1/2、A2 HOLD、DOE56 HOLD。停止于Solver入场前，等待用户单独授权V2。

执行顺序候选：先原G001/G002两案D2补洞输入，再10个新局部/交互案，然后其余38个保留案；便于新增16有效几何的首个检查点已含局部信息。总50集合、身份与预算不变，本轮不执行。
