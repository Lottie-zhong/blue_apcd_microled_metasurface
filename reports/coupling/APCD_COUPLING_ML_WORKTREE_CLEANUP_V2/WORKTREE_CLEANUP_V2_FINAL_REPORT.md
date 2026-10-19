# Coupling-ML Worktree Cleanup V2

生成时间：2026-10-19T13:08:03+08:00

## 状态

**PARTIAL**。已归档可明确归属的代码、报告、索引和离线夹具；science outputs 原位保留并按精确路径忽略。未处理 K6 科学身份/账本冲突、DOE56 凭据上下文和其他支线文件，因此工作区没有强行标记为 clean。

## V1 快照复用

- Worktree：`D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
- Branch：`work/mdc-np-coupling-ml-v1`；V2 入手 HEAD：`11e9cf66c21675bf5d0b23bd55e476bc6676c80b`
- V1 快照：`D:\project\_codex_worktree_snapshots\APCD_COUPLING_ML_WORKTREE_CLEANUP_V1_20261019T041627Z`
- V2 开始状态：4 staged、10 tracked modified、6,936 untracked。没有重做 V1 全盘点。

## 分类与处理

V2 的逐文件归属和 SHA 来源沿用 V1 `FILE_CLASSIFICATION_MANIFEST.csv` 与 `BACKUP_AND_SHA256_MANIFEST.csv`。以下 current-untracked 统计只覆盖本轮结束时仍可见的 871 个未跟踪项；ignored 的科学数据另列，分类维度之间不相加。

### 当前未跟踪按来源类别

| V1 分类 | 文件数 | 字节 |
| --- | --- | --- |
| FORMAL_REPORT_METRICS_OR_PROVENANCE_CANDIDATE | 430 | 4,581,306 |
| HISTORICAL_REPORT_OR_AUDIT_EVIDENCE | 3 | 12,209 |
| OTHER_COUPLING_SUBLINE_ASSET | 171 | 2,438,545 |
| PROJECT_INSTRUCTIONS | 1 | 4,118 |
| RUNTIME_OR_EXECUTION_STATE | 10 | 167,064 |
| SCIENCE_IDENTITY_OR_PROVENANCE | 247 | 243,928 |
| UNRESOLVED_OR_OTHER_SOURCE | 9 | 41,166 |

### 当前未跟踪按目录

| 目录根 | 文件数 | 字节 |
| --- | --- | --- |
| reports/coupling/COUPLING_K6_V2_REMAINING127_STARTUP_REVALIDATION_V1 | 680 | 4,837,443 |
| M2I_LEVEL2A_RUNTIME_V1/cases | 133 | 1,704,511 |
| scripts/coupling_ml | 38 | 734,034 |
| reports/shared_v3 | 6 | 866 |
| reports/coupling/COUPLING_ML_LOCAL_SCALE_CIRCULAR_PHASE_KRR_PILOT_V1 | 3 | 4,146 |
| scripts/postentry-race-p6816tot | 3 | 139,296 |
| AGENTS.md | 1 | 4,118 |
| entered_exception_isolation_results.csv | 1 | 882 |
| reports/coupling/APCD_COUPLING_272G_FORWARD_AND_CVAE_PILOT_V1 | 1 | 424 |
| reports/coupling/COUPLING_K6_V2_G025_RECOVERED_TRUTH_INGEST_AND_G026_RESUME_V1 | 1 | 56,731 |
| reports/coupling/COUPLING_ML_FULL_RANK_AMPLITUDE_CIRCULAR_PHASE_KRR_PILOT_V1 | 1 | 1,511 |
| reports/coupling/SHARED_V3_STRICT_FENCED_ORPHAN_TRUTH_ADOPTION_V1_RUNTIME_RESULT.json | 1 | 2,547 |
| scripts/entered_exception_isolation_results.csv | 1 | 882 |
| scripts/shared_fdtd | 1 | 945 |

### 当前未跟踪按文件类型

| 扩展名 | 文件数 | 字节 |
| --- | --- | --- |
| .json | 789 | 6,241,743 |
| .py | 36 | 732,082 |
| .txt | 18 | 168,606 |
| .jsonl | 7 | 183,819 |
| .sha256 | 6 | 1,510 |
| .bin | 4 | 5,657 |
| .md | 3 | 10,962 |
| .csv | 3 | 2,709 |
| .ps1 | 2 | 1,952 |
| .sqlite3 | 1 | 106,496 |
| .sqlite3-shm | 1 | 32,768 |
| .sqlite3-wal | 1 | 32 |

### 批次文件类型观察值

V2 第一轮重复副本处理后、ignore/commit 批次开始前，观察到 6,753 个可见 untracked 文件。下表沿用那次分类采样；它和当前未跟踪表不是同一时点。

| 扩展名 | 文件数 | 字节 |
| --- | --- | --- |
| .json | 4263 | 180,511,162 |
| .npz | 1205 | 15,225,374,049 |
| .joblib | 394 | 4,635,492,155 |
| .csv | 220 | 9,953,166 |
| .py | 210 | 3,172,201 |
| .pt | 156 | 54,719,233 |
| .md | 117 | 605,218 |
| .txt | 60 | 263,492 |
| .png | 30 | 18,826,304 |
| .svg | 28 | 1,898,080 |
| .pdf | 28 | 1,101,271 |
| .lock | 12 | 235 |
| .jsonl | 7 | 183,819 |
| .sha256 | 6 | 1,510 |
| .sqlite | 4 | 495,616 |
| .db | 4 | 106,496 |
| .bin | 4 | 5,657 |
| .ps1 | 2 | 1,952 |
| .sqlite3 | 1 | 106,496 |
| .sqlite3-shm | 1 | 32,768 |
| .sqlite3-wal | 1 | 32 |

分类汇总另存于 `V2_CLASSIFICATION_SUMMARY.csv`。主要未跟踪组是 K6 剩余127队列 680 项（4,837,443 bytes，身份冲突保留），M2I runtime 133 项和其他 Coupling-ML 子线脚本 38 项（合计 V1 `OTHER_COUPLING_SUBLINE_ASSET` 171 项）。

## 已完成的 Git 归档

- 按精确路径提交 172 个分析脚本（2,400,165 bytes）、2,487 个正式报告/度量文件（75,411,865 bytes）、402 个科学身份/数据索引（10,299,318 bytes）。
- 提交 8 个明确标注的离线 Runner fixture（602,112 bytes）；fixture 数据库仅用于测试，不属于生产 SQLite。
- 提交 3 个 V1 SHA 清单已记录的只读原生数据导出（1,547,106 bytes）。
- 精确 unstage 原 4 项；内容留在工作区/冲突项中，index 变为 0。
- 清除 180 个 K6 queue `.partial` 临时副本（1,232,165 bytes）。删除前逐个确认与同目录最终文件字节相同、V1 清单大小相符；V1 外部快照保留原路径与 SHA。没有删除其他数据。
- `.gitignore` 仅增加 Coupling report tree 内的模型/数组扩展规则、两份含 Runner credential context 的快照精确文件规则，以及四个 `science_outputs/` 目录规则。报告、CSV、JSON、Python 元数据不被扩展规则屏蔽。

## 研究边界

- `NEW_FDTD=0`、模型训练=0、Runner 修改=0、sealed 数据访问=0。
- 仅重跑三项指定离线测试：18 passed（9.23 秒）。
- DOE56/H1/DIAG2 等科研结论与预算未改变。

详细证据见 `SCIENTIFIC_ASSET_INTEGRITY_REPORT.md` 和 `UNRESOLVED_ITEMS.md`。
