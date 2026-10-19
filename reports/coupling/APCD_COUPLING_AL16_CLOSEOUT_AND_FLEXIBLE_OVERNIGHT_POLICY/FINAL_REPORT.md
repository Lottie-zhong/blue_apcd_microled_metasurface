# AL16 CLOSEOUT AND FLEXIBLE OVERNIGHT POLICY

## 状态

PASS。AL16已闭环，无未入场余额，不重复启动。只读复核canonical16个COMPLETED Job/16 REAL Entry、16有效标签及所有FSP/H5/609D路径，与科学Ledger一致。复用已完成科学验收、独立对账与40次模型拟合，不重提取/重训/全量hash。

AL16 valid16/invalid0/replay0，FAST172G。原模型前后比较与学习曲线见上一轮FINAL_REPORT及ML_UPDATE；ExtraTrees P+谱MAE0.0315207→0.0313934，450nmmeanfoldrho−0.04649→−0.04455，排序仍不可靠。覆盖距离均值约下降2.40%，不宣称设计精度通过。

## 夜间优先、弹性调度

Asia/Shanghai21:00–次日10:00是PREFERRED_GPU_WINDOW，仅优先级，不是强制启动/停止条件。已经进入FDTD的case正常完成；不因10:00终止，不改变FDTD物理最大时长。白天若真实共享资源安全，可继续仍获授权且未入场的case；冲突或未知资源状态延后新entry。CPU FDTD/EDT/GUI本身不是阻塞，不终止他人任务。

沿用正式RunnerV3.1资源门禁/串行接口，不改Runner，不安装Scheduler、cron、heartbeat或新的调度平台。该文件是科研操作政策，不冒充已部署自动时钟控制器。任何时间窗口都不增加预算、允许replay或放开DOE56/DIAG2。

## 后续约50G规划

常规批次目标约50G，按GPU时间、有效率、覆盖、学习曲线与空闲动态调整，可以跨多个夜间窗口。不要求每夜完成50，也不要求凑满50。

按AL16实测服务时间11.7091min/有效几何，50次在同样100%有效率下服务约9.76h；与13h偏好窗口相比有规划余量，但不保证同样成本、有效率或无冲突。若50attempt有效率90%/80%，预计45/40有效几何；不能自动增加entry补足50。队列、冲突与未来耗时不确定性另列。

旧下一轮16提案仅作选样种子，后续AL50须独立选样/去重/身份/FSP/Manifest/有界预算和正式求解授权；本轮未生成AL50 Case/FSP/Job，授权0。下一包继续覆盖优先，考虑D2=130/185稀疏值，不按不可靠的最高预测P+直接选最优。

## 边界与交付

本轮NEW_FDTD=0、NEW_ENTRY=0、NEW_FIT=0。AL16预算16/16已耗尽；DIAG2=1/2，A2 HOLD，DOE56 HOLD。旧科学数据/Ledger及Runner不改。FLEXIBLE_OVERNIGHT_POLICY.json为正式持久化政策；AL50_PLANNING_NOT_AUTHORIZED.json仅规划。上一轮完整产物保持原路径。
