# FMM2B1R RCWA result-schema audit

## 中文报告

1. 本阶段做了 tiny RCWA result-schema follow-up：重新创建最小 SiO2 薄膜 RCWA proxy，453 nm，x 偏振设置，法向入射，只运行一次，不做 sweep。
2. 是否找到了 RCWA solver object 的正确结果名：`total_energy` 提取状态为 `True`；可发现结果名记录为 `['num_k', 'peak_memory', 'simulation_run_time', 'substrate', 'total_energy', 'total_threads', 'x', 'y', 'z']`。
3. total_energy 是否提取成功：成功。
4. total_energy 字段和值：`{"lambda": [4.5300000000000005e-07], "f": [661793505518763.8], "theta": [0.0], "phi": [0.0], "Rs": [-0.0], "Ts": [1.0000000000000002], "Rp": [-0.0], "Tp": [1.0000000000000002]}`。注意：不假定 x 偏振必然对应某个 s/p 通道，需结合 Lumerical 入射轴/角度约定解释 Rs/Ts/Rp/Tp。
5. substrate 可用：`True`；simulation_run_time 可用：`True`；runtime_seconds: `0.005961`。
6. result_schema_decision: `rcwa_result_schema_pass_total_energy_extracted`。
7. 明确限制：没有 FDTD；没有打开或修改 H1J4 FSP；没有 sweep；没有 broadband；没有 APCD coupling；没有 push。
