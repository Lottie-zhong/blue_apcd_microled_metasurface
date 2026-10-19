# Figure QA

PASS：4组图全部逐面板及整图目视验收，4/4PDF字号审查通过，最小7pt，实际宽度183mm；可编辑PDF/SVG与600dpiPNG。源检查19PASS/1WARN/0FAIL，唯一WARN未导出TIFF，本轮不是期刊正式提交。

前向5模型比较包括Mean/KRR/冻结leaf3及2预注册对照，4折范围非CI；单位norm投影变差与收缩未解决如实保留。树平均仅标fold1/seed17/32G，不外推全空间。CVAE训练曲线完整400epoch和8runs，不作heldout早停；posterior重建明确encoder看见geometry，非prior生成。代理与已知库真值分开标注，不能交叉比较“真实目标达成”；CVAE8runs不是8独立数据集，生成合法率由投影保证。仅对NA标签边距定向重绘一图，无模型重训或全量回归。
