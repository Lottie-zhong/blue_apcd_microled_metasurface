# APCD GPU Runner V3.1 使用手册

## 提交批次
```bash
python minimal_batch_runner_v3.1_final.py submit 批次名 --manifest 清单.json
```

## 运行批次
```bash
python minimal_batch_runner_v3.1_final.py run 批次名
```

## 查询状态
```bash
python minimal_batch_runner_v3.1_final.py status 批次名
```

## 输出位置
- FSP: `outputs/batch_N/job_M_output.fsp`
- 数据库: `runner.db`

## SHA256校验
9d380e62f265cb7ca3d4398a9831dd8358362223d09fc5476a436b4f2582be33

版本: 3.1.0 Final
日期: 2026-10-17
