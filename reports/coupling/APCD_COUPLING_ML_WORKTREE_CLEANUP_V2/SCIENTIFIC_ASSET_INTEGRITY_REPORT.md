# Scientific Asset Integrity Report (V2)

## 保护方式

- V1 snapshot 和 SHA inventory 原位复用：`D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z`。
- 本轮未重新计算全量 SHA；使用已保存的 V1 SHA 行及文件路径/大小记录。没有将“有 SHA 记录”误写成“额外备份”。
- 4 个正式 `science_outputs/` 路径中的文件均留在原地；case/attempt manifest、science ledger、SHA inventory 等索引继续跟踪。

## 生产数据输出树

| 数据根 | 文件数 | 总字节 | 已跟踪索引文件 | V1 路径匹配 | V1 大小匹配 | V1 SHA 行 |
|---|---:|---:|---:|---:|---:|---:|
| AL50_COMPLEX_AWARE | 750 | 24,385,824,913 | 16 | 750/750 | 750/750 | 600/750 |
| AL50_COVERAGE_DRIVEN | 600 | 19,507,867,110 | 4 | 600/600 | 600/600 | 480/600 |
| AL16_FAST | 240 | 7,803,449,903 | 5 | 240/240 | 240/240 | 192/240 |
| AL50_LOCAL_GLOBAL_V2 | 150 | 4,876,302,184 | 5 | 150/150 | 150/150 | 120/150 |

合计 1,740 个 science output 文件，56,573,444,110 bytes（约56.7 GB）；所有 1,740 个当前路径都在 V1 inventory 中且大小匹配。V1 有 1,392 个对应 SHA 行；其余 348 个未声称已通过 V1 SHA 校验。四组 case ID 均可由已跟踪索引检出。目录规则只影响 Git 跟踪状态，未改动数据内容。

## 数组、模型与锁文件

报告树内 1,767 个 `.npz/.joblib/.pt/.lock` 文件由精确规则忽略，总计 19,915,585,672 bytes（约19.9 GB）。该数字与上表的 science_outputs 重叠，不作相加。文件仍在原位置；没有加入 Git。

两份 `PROTECTED_LEDGER_SNAPSHOTS.json` 包含 Runner credential context，已使用两个精确文件规则排除并原位保留。没有输出或复制凭据值。

## 其他保护项

- 8 个已提交 SQLite/DB 文件都位于 `offline_interface_fixture`、`identity_fixture`、`serial_plan_fixture` 或 `TEST_ONLY` 路径；只读检查确认是 fixture。四个 `SCHEMA_ONLY` fixture 的 `solver_entries=0`。无生产 SQLite 被改写。
- 3 个 G001/G004/A1 raw JSON 导出均命中 V1 精确路径、大小和 SHA 记录，作为小型只读科学收据提交。
- 180 个重复 `.partial` 副本删除前与最终同目录兄弟文件逐个字节比对相同；原始清单和对照结果保存在 V1 snapshot 目录下的 `V2_DUPLICATE_PARTIAL_CLEANUP.csv` 与 `_RESULT.json`。
- DOE56 与 K6 tracked ledgers 未覆盖、未改写、未提交；详情见 `UNRESOLVED_ITEMS.md`。
