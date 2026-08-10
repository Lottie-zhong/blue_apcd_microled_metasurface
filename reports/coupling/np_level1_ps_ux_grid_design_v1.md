# NP Level-1 P/S ux grid design v1

### 状态

PASS；this design task solver=0（NP/MDC/integrated FDTD/TMM/RCWA/FEM/training/ML 均为 0）。

### Cross-branch reuse

RUN3A-P: `REUSABLE_LEVEL1_NP_ANCHOR`；RUN3A-S: `REUSABLE_LEVEL1_NP_ANCHOR`。两者均只作为 ux=0 standalone NP central anchor，不扩展为 quantitative joint MDC-NP power。
formal source commit: `9128dfb85a268398d1fee56fcb7543982b075d84`；formal scope: `D:\project\worktrees\blue_apcd_np_k6_mdc_v1\outputs\np_k6_formal_source_scope_v1\formal_source_scope_v1.json`；M2 angular reuse count: `0`。

### MDC-weighted ux grid

P support 80/90/95/99%: `0.44322168`, `0.89945031`, `0.95547911`, `0.99651618`。
S support 80/90/95/99%: `0.24612309`, `0.30915462`, `0.37818915`, `0.59029526`。
P minimum nodes: `[-0.9549788465408765, -0.7413793103448276, -0.48275862068965514, -0.22413793103448276, 0.0, 0.22413793103448276, 0.48275862068965514, 0.7413793103448276, 0.9549788465408766]`；S minimum nodes: `[-0.3786893999886029, -0.22413793103448276, 0.0, 0.22413793103448276, 0.37868939998860307]`。
P recommended nodes: `[-0.9960139162372611, -0.9549788465408765, -0.8989500609319028, -0.7413793103448276, -0.48275862068965514, -0.4447224305454446, -0.22413793103448276, 0.0, 0.22413793103448276, 0.4447224305454448, 0.48275862068965514, 0.7413793103448276, 0.8989500609319028, 0.9549788465408766, 0.9960139162372612]`；S recommended nodes: `[-0.59079551125947, -0.48275862068965514, -0.3786893999886029, -0.30865436985072636, -0.24562284411253515, -0.22413793103448276, 0.0, 0.22413793103448276, 0.2456228441125353, 0.3086543698507264, 0.37868939998860307, 0.48275862068965514, 0.5907955112594703]`。
Order thresholds: `88` rows for m=-3..+3, lambda=445..455 nm; node selection uses deterministic 450 nm representatives and retains P/S separately.

### Exact future solver budget

MINIMUM_PILOT_GRID: P new=`8`, S new=`4`, total=`12`；P0/S0 rerun=`0`。
RECOMMENDED_PILOT_GRID: P new=`14`, S new=`12`, total=`26`；exact 445–455 nm 1 nm broadband per polarization×ux node。

### Tests / Git / 下一步

Test evidence: `80_passed`。FSP/raw arrays remain external; only paths/SHA/source commit/scope are recorded.
下一步：`REQUEST_NP_LEVEL1_MINIMUM_PS_UX_PILOT_SOLVER_AUTHORIZATION`。
