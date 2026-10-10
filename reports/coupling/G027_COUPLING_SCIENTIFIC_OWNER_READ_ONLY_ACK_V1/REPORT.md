# G027 Coupling Scientific Owner 只读复核回执

状态：PASS（本案数据合同及部署后再提取一致性）；不授予批次launch或ML准入。

原G027 attempt_001唯一entry=1/replay=0保持。原native FSP/H5、正式truth、labels及账本hash核对；安装a09655cd577d7618d3080d35b7a5b2a4a5fc52c5的隔离fresh LOAD/importer产物与原恢复标签全部逐元素相同maxdiff=0。21波长、7阶、TE/TM，C_hat[21,7,2]+P_scale[21]，609输出、正值有限。

phase/reference/source normalization：POSTNP reference1722 nm；IN_REF +z(0,0)TM提供每波长共同gauge，所有平面/分量复用，保留relative phase；P_scale=POSTNP完整周期E/H通量除以IN_REF incident cell power。无需oracle phase alignment，不修改labels或归一化。

冻结H2实际复算：与native-grating标签routing最大差0.00021109951031966778，absolute-order最大差0.00011008577095045213，total/P_scale差0。保留这项既有modal/native诊断差异；不将原标签相等误写为H2与native完全相同，也不擅加1e-9新gate。

R/T/A闭合用A=1-R-T，不能作为独立吸收验证。reference deembedding roundtrip属代数检查；monitor E/H flux一致性不能证明mesh convergence。Planar TMM与patterned integrated的R/T/A差异仅为comparator诊断，不增加或修改冻结门槛。跨科学run重复性尚未验证。单入射state不是完整Jones/multiport operator。

交付清单曾有真实不一致：final_boundary_audit.json的bytes在draft inventory后被更新。原差异保存在PRE_CORRECTION_RECEIPT.json；GPU owner保留draft并提供revision2，当前清单全部files已核对通过。没有替换原科学truth。

账本仍39 entered /35 truth-valid /35 labels-valid /89 unentered。复核自身：0solver、0training、0replay、0confirmation response、0native LOAD。只读已有文件/CPU H2计算，无资源控制、无request/release/ledger/truth修改。源证据及完整SHA见RECEIPT.json与SHA_INVENTORY.json。

下一步：GPU owner将此只读回执作为外部来源绑定并封存交付。本回执不启动后续生产。
