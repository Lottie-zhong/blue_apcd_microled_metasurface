# APCD_COUPLING_ML_GPU_V31_FINAL_HANDOFF_AND_DIAG2_BINDING

## 裁决
DIAG2_V31_SCIENCE_BINDING_READY。正式平台接收、安装 SHA、External Execution 绑定、科学账本对账、Native接口五项 PASS。本轮未获真实启动授权，未调用真实 run。

## 正式绑定
原 A1/A2、attempt_001、原6ps合同和原两条预算不变。通过安装态 submit/status 各登记一个单Job子批次；见 DIAG2_SCIENCE_LEDGER.json 和 PRODUCTION_SUBMIT_STATUS_RECEIPTS.json。Science Case → coupling:case/attempt_001 → canonical Batch/Job → pending Entry → 单一科学投影账本。真实 Entry 尚不存在，绝不虚构 Entry ID。

Runner canonical solver_entries 的 REAL 原子预留是唯一消费事件，科学账本绑定其科学含义；不另行执行旧 Diag2Budget 预扣。失败、断线、RUNNING仍保守消耗，不退款、不换ID。每次调用前后以只读模块对账；偏差 HOLD。V2.1 无Admission、三旧任务 Disabled，旧94条tasks无DIAG2，完整保留。此为用户接受的单一受支持入口管理边界，不能声称锁可阻止任意手工旧脚本。

## 零求解验证
安装态隔离合成fixture验证submit/Fake/status、跨Batch和attempt复用execution拒绝、错误SHA拒绝、重复Fake无新增预留。fixture有1条FAKE reservation，solver_entered=0；生产0条Entry。定向恢复检查见TARGETED_TESTS.json；科学绑定模块8项见SCIENCE_BOUND_VIEW_TESTS.json。首次路径断言误加数据库stem已按实际status修正；bundle_inventory调用签名也按既有接口修正，未改Runner。

安装文件SHA与deployment、af39ddc8和upstream一致；沿用平台33/33，不全量重跑。原16SHA、G001/G004原生609D零差异、14迁移/6resolver、156G和已训练模型均未重跑。

## Native科学边界
新路径为data/outputs/runner_v31/batch_N/job_N/output.fsp，以status实际返回为准。已将合法历史Native字节以硬链接隔离视图接至新路径，复用bundle_inventory验证FSP/H5有限E/H与SHA；冻结importer和原生basename readview及609D收据沿用已有PASS。伴随H5必须现场发现并清单记录，不能假定partial文件重命名后内部链接自动有效。COMPLETED不等于labels-valid；Fake/partial/缺H5一律不科学入库。真实6ps输出及truth均NOT_RUN。

## 资源与下一次执行
只读当前容量门禁：PASS，原因[]。资源需求来自历史同mesh/结构日志和当前GPU单进程单线程配置，采用GPU2GiB、RAM8GiB、磁盘10GiB余量；不是6ps实测。当前License提供enterprise lumerical_solve；68SM的容量按官方规则为1solve+64anshpc，API另需1GUI，详见RESOURCE_REQUIREMENTS_QUALIFIED.json及[官方License规则](https://optics.ansys.com/hc/en-us/articles/360058577794-Ansys-optics-solve-accelerator-and-Ansys-HPC-license-consumption)。资源GUI仅只读配置、未load/run/save，已关闭自己的会话；旧版本缺getlicenseestimate/islicensestandard已记录，不据此伪造返回值。

本轮不授权run。后续独立启动任务：核对固定身份及0/2 → 确认无配置变化并在canonical mutex内重新双采样资源/License → A1 run → 原生FSP/H5 freshLOAD/609D/科学有效性及6ps诊断验收 → science账本对账 → 只有A1验收有效后才处理A2。不对双Job一键连续启动。任一不一致或HOLD停止，不删除预留、不换ID；原2预算无需重申请。

## 保留状态
DIAG2_ENTRY=0/2；NEW_FDTD=0；REPLAY=0；DOE56=HOLD；AL16=NOT_AUTHORIZED；NEW_ML_FITS=0。confirmation响应未访问，609D/H1/H2和合法156G不变。模型与8192池/16提案不重做。后续科研由Coupling自主负责，Runner冻结。

## Git
分支work/mdc-np-coupling-ml-v1，HEAD 2cc687020e90ec4397e6cd4ed31efed59aaaf386，ahead/behind 0	0。工作区dirty，原4项staged保留；本轮未提交或推送。精确allowlist仅本报告目录的小型证据及新只读科学绑定模块，不含fixture/SQLite/FSP/H5。
