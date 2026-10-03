# CONTINUATION — COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1

恢复该任务先读本文件，再读 POSTNP_MONITOR_VALIDITY_AUDIT_REPORT_V1.md 与 EVIDENCE_INDEX_V1.json；不要依赖聊天上下文。

## Project / connection / authority
- Remote: DESKTOP-NNE313K, user desktop-nne313k\dell.
- Canonical project: D:\project\blue_apcd_microled_metasurface.
- Formal worktree: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1.
- Branch: work/mdc-np-coupling-ml-v1.
- Inspection input HEAD: ddda6b302d9282f416028386903ba8e7b39cbc50; upstream 0/0.
- Prior continuation read: reports/coupling/COUPLING_ML_FORWARD_TRAINABILITY_AUDIT_V1/CONTINUATION.md, SHA256 34ba24e61c3978fbaaada6a0830b94619b105654d4c956ddc02939aac596a7ed.
- 32G authority: reports/coupling/PW_K6_STAGE1_32G_FROZEN_FORWARD_H1_V1/PW_K6_32G_DATASET_AUTHORITY_V1.json.
- Monitor authority/contract: contracts/coupling/medium_pw/MONITOR_SAMPLE_AND_REFERENCE_PLANE_AUTHORITY_V1.json; contracts/coupling/medium_pw/MEDIUM_PW_MONITOR_CONTRACT_V1.json.

## Scope and progress
- Task: COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1.
- ZERO SOLVER, ZERO NEW TRAINING. No GPU Runner, new HF/reserve, inverse search, production monitor movement, truth/contract modification, or historical HF rerun.
- EXT02 setup/data/source read-only inspection completed.
- NP z=1212…1712 nm; saved POSTNP sample≈1802 nm and actual top clearance≈90 nm; reference=1722 nm, clearance=10 nm.
- Extraction is full x/y E/H Floquet least squares with ±z × TE/TM; evanescent coefficients retained. Air has seven propagating orders m=−3…+3,n=0 for all 21 wavelengths.
- Existing modal/native-grating comparison is 20G and same HF; it has power/routing results but no complex-phase comparison. No second independent POSTNP-height plane exists in the same uniform Air region in saved EXT02 data.
- POSTNP=1800 is frozen in 2026-09-24 authority; original selection derivation is not documented.
- Report SHA256: 7069c764e780f8e5a98f980a026e0cd497268705a211da596bab38c8bb05e71f.
- Status PARTIAL solely because the independent second-height field evidence is absent; proposal is one separately authorized solver-entered case. Do not execute it here.
- Full findings and source hashes are in the report and evidence index under reports/coupling/COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1/.

## Git / recovery
- Before this task, 332 pre-existing status entries were present; preserve them (porcelain SHA256 e26c3debc7523bb4d157ac679656032d99c544ea675d770887afa7b236d964bc).
- Exact task allowlist:
  1. reports/coupling/COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1/POSTNP_MONITOR_VALIDITY_AUDIT_REPORT_V1.md
  2. reports/coupling/COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1/EVIDENCE_INDEX_V1.json
  3. reports/coupling/COUPLING_ML_POSTNP_MONITOR_VALIDITY_AUDIT_V1/CONTINUATION.md
- This run commits only those exact files and normal-pushes. On recovery first verify host/user/worktree/branch/HEAD/status. Never reset, clean, force-push, or stage unrelated paths.
- Read report/index before follow-up. Any second-height solver validation is a separately authorized future task.