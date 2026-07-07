# FMM2B1 tiny RCWA/addrcwa API smoke test

## 中文报告

1. addrcwa 是否可用：`True`
2. RCWA solver object 是否成功创建：`True`
3. tiny run 是否完成：`True` (完成)
4. 轻量结果摘要：目标波长 453 nm，x 偏振，法向入射；模型是最小周期 SiO2 薄膜 proxy，不是 H1J4 FSP。结果提取字段见 `fmm2b1_rcwa_api_smoke_results.csv`；若某个 Lumerical result 名称不可用，表中记录为 `missing`，没有伪造数值。
5. 明确限制：没有 FDTD；没有打开或修改 H1J4 FSP；没有 sweep；没有 broadband；没有 APCD coupling；没有 push。

Runtime artifacts are under `D:\project\worktrees\blue_apcd_rcled_mdc\runtime\r2_4fmm2b1_rcwa_api_smoke_test_DO_NOT_COMMIT` and are gitignored. Heavy runtime files are not staged or committed.
