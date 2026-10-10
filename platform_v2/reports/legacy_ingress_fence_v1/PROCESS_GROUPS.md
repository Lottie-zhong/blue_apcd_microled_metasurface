# Bounded owner evidence matrix

| 组 | PID/create_time（父 → 子） | 可核验证据 | V1 owner 关系判定 |
|---|---|---|---|
| 1 | 29236/1790605929.368212 → 33824/1790605930.765615 | CIM/psutil、谱系双快照一致；DELL/session 0；NP historical case directory；两成员 write_bytes Δ=0 | 无当前登记 owner；绝对排除未证明，保留风险 |
| 2 | 33316/1790606660.417523 → 17436/1790606661.694775 | CIM/psutil、谱系双快照一致；DELL/session 0；NP historical case directory；两成员 write_bytes Δ=0 | 无当前登记 owner；绝对排除未证明，保留风险 |
| 3 | 24800/1790607267.885326 → 29816/1790607268.680590 | CIM/psutil、谱系双快照一致；DELL/session 0；surrogate historical case directory；两成员 write_bytes Δ=0 | 无当前登记 owner；绝对排除未证明，保留风险 |
| 4 | 27248/1790607300.421158 → 26372/1790607301.221486 | CIM/psutil、谱系双快照一致；DELL/session 0；surrogate historical case directory；两成员 write_bytes Δ=0 | 无当前登记 owner；绝对排除未证明，保留风险 |
| 5 | 16572/1790607348.892628 → 32256/1790607349.837663 | CIM/psutil、谱系双快照一致；DELL/session 0；surrogate historical case directory；两成员 write_bytes Δ=0 | 无当前登记 owner；绝对排除未证明，保留风险 |
| 6 | 18080/1790607403.351985 → 31844/1790607404.225603 | CIM/psutil、谱系双快照一致；DELL/session 0；surrogate historical case directory；两成员 write_bytes Δ=0 | 无当前登记 owner；绝对排除未证明，保留风险 |
| 7 | 28420/1790607449.980155 → 17576/1790607450.810289 | CIM/psutil、谱系双快照一致；DELL/session 0；surrogate historical case directory；两成员 write_bytes Δ=0 | 无当前登记 owner；绝对排除未证明，保留风险 |
| 8 | 18936/1791386010.446251 → 40664/1791386010.758180 | CIM/psutil、谱系双快照一致；DELL/session 0；stdin parent plus SSH child; stdin body unavailable；两成员 write_bytes Δ=0 | 无当前登记 owner；绝对排除未证明，保留风险 |

所有组都排除了“当前已登记 V1 science owner 集合成员”：生产 root 活动标记/锁不存在，54 条 registry 记录均 terminal，Shared slots/resource/GPU active owner 行均为空。但未把这等同于绝对排除未登记的活动或未来入场关联；缺失 stdin、完整句柄、IPC 源使绝对排除未签发。历史目录和命令行用于支持来源，不单独作为 OTHER 分类依据。

原始快照只保存在隔离 runtime；SSH 参数不写入 Git。当前观察窗所有 16 个关联成员 write_count/write_bytes 增量均为 0，12 个历史 FSP/H5/日志等文件的 size/mtime 未变；不能推论窗口之外从未写入。
