# CVAE探索试验裁决

## 结论

**可保留轻量探索分支；可靠逆向设计尚未证明，不能进入正式逆向生产。** 不扩大网络，不将CVAE作为下一批主选样器。

## 模型与训练

Encoder：有序D1…D6归一化＋4个光学条件，10→64SiLU→32SiLU→μ3/logvar3。Decoder：(4条件＋z3)→32SiLU→64SiLU→6sigmoid。条件为FrozenH2得到的450nm η+、P_scale及各自21λ均值；P+由两者决定，不再重复加入。低维条件不唯一确定原609D完整状态或唯一几何。

4折×2seed，8次训练，各400epoch；batch64，AdamW lr0.001、weight_decay0.0001，KL系数0.005、80epoch warmup，无heldout早停或超参数选优。所有运算CPU2线程，另4个预先固定原ET-leaf3 B29 checker仅用各训练折拟合，不因前向试验事后换checker。

同原124个验证几何、原四折与完整局部家族purge，old32保持train-only；λ行不跨几何折；预处理只拟合训练折。四折heldout为32/31/30/31。主MAE按124几何聚合，450nmSpearman按既定折均值。CVAE先按几何数加权再平均两个seed；248条query-seed不是248个独立几何。数据采集曾使用已有开发标签，因此本轮是开发集OOF诊断，不是独立外部测试。

## 生成与基线

|方法|best-of-16代理条件误差|条件内几何多样性 /nm|与272G精确重合|
|---|---:|---:|---:|
|CVAE|0.600637|42.854|0.0%|
|均匀随机|0.642443|53.481|0.0%|
|训练库检索|0.279798|61.412|100.0%|

CVAE对随机的代理best16误差降低6.51%，8个fold-seed中7个更好；但库检索明显更强。**以上全部是相同代理的离线筛选分数**，不是新结构FDTD条件误差。库几何属于checker训练点，享有域内优势；其已知真值另列，不能据代理差距断言未求解CVAE几何的真实物理优劣。

CVAE共3968个候选，全局唯一3968、与272G重合0。100–230nm、5nm投影及周期正间隙合法率100%，最小周期间隙60nm；均由边界/网格构造保证，随机亦100%，不代表实际制造资格。六径未排序。候选CSV仅EXPLORATORY_ONLY，无新科学或执行身份。

Posterior重建MAE26.3026nm（train17.9940nm，heldout离散重建26.2668nm）。这是encoder看见几何后的重建，不能当作prior逆向生成性能。KL均值3.3605、8/8训练均3个latent活跃，未见整体塌缩；latent活跃阈值var(μ)>0.01只是诊断约定，不是冻结科学门槛。各模型aggregate posterior均值/协方差与N(0,I)对照见CVAE_LATENT_DISTRIBUTION_AUDIT；不混合不同模型不可识别的潜坐标，也不据两个矩宣称完整Gaussian校准。

相同z打乱条件后，几何平均变化16.38nm，best16代理误差0.60064→0.66559，8/8变差，支持网络使用了条件；仍非真实物理条件满足证明。

## 已知库的代理排序风险

已知真值条件最近邻误差0.216755；在同16个库候选中改由checker挑选，真实误差升至0.326566（约+50.7%）。真值NN按定义在该库条件距离下最优，此实验量化的是checker误排序的实际损失，不是惊讶的物理因果发现。新CVAE/随机结构没有真值，不能把这一差值直接外推为其真实误差。

详细架构、loss、latent、候选、逐折数据与启动恢复记录在CVAE/CVAE_PILOT_REPORT.md及对应FIT_LEDGER、LOSS.csv、EVALUATION.npz。一次SSH子进程启动被回收发生于0fit之前，改用既有WMI独立worker后完成；无已完成fit重训，无Solver调用。

## 科学与执行边界

FAST272G，ML_TRAINING_GRADE，严格数值收敛NOT_CERTIFIED。NEW_FDTD=0；NEXT_BATCH_AUTHORIZED=0；DIAG2=1/2；A2HOLD；DOE56HOLD。无Runner调用或修改、无原生FSP/H5覆盖、无sealed响应访问、无新科学Case/Job/Entry身份。既有Git dirty/staged保留。
