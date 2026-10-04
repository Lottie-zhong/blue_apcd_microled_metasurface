# GPU authority owner handoff: K6 V2 enrollment request

This package requests review and formal enrollment of the 160 frozen V2 Amendment 01 geometries. It does not modify Runner authority or authorize solver entry.

Package: reports/coupling/COUPLING_ML_K6_V2_DATASET_ADMISSION_PREPARATION_V1/CASE_REGISTRATION_PACKAGE_V1.json
Candidate SHA256 596bcc8fd7011cb5ec0c2fc93b9dfe26653ef74720d1bcd4872d3b22e18727c4; Amendment 01 SHA256 124f6a0ddd65a65b0b4499a6dbfd98f2105d40ee273bfaeba04b28a6591f8f8a; 160 rows; attempt_001 proposed (owner checks for collision).

Owner request:
1. Review exact ordered D1..D6 and purpose labels.
2. If accepted, enroll exact candidate/source hashes through the formal owner workflow. Preserve the contract; ordered_D_nm is the only case delta.
3. Return committed authority SHA, IDs/count, per-case authority/source-manifest paths, and setup/preflight requirements.
4. Preserve single-slot serial/no-replay limits. Enrollment alone is not solver authorization; no launch is requested.

Runner codex/apcd-gpu-production-runner-v1/6d472a967815915f8e2a37b275af054b20f1354c; handoff SHA b7884408f7273a161e39f082e5228cab41e91af68521b6ddbfa9fd56bed02761; route SHA e6043ff7bec4711d16d326ca3d8305b9693647250349dea11b59b57e0cd2d1ec; policy SHA e26c2f1e5b13743da455277f4562ccf2a6262567e4dabf1a2fae06735d624f5f. K6 authority count is zero. The old local16 LOAD-only proofs are task-private.

After enrollment use D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\build_pw_k6_5nm_full_period_prefsp_v1.py with --spec-json <owner-approved case spec> --output-fsp <canonical source FSP>, then the official validator, fresh LOAD-only proof, and exact source/staged SHA parity. This task generated no FSP.

EXT02 dual-plane numerical validation remains open; historical K6V1_EXT02/attempt_001 entry is consumed. Do not replay it or create attempt_002 under this request.
Runner worktree authority boundary: read-only status showed five tracked modifications, including the uncommitted controlled-admission authority and policy drafts. They are not formal authority. This package uses only committed Runner HEAD 6d472a967815915f8e2a37b275af054b20f1354c (route SHA256 e6043ff7bec4711d16d326ca3d8305b9693647250349dea11b59b57e0cd2d1ec; policy SHA256 e26c2f1e5b13743da455277f4562ccf2a6262567e4dabf1a2fae06735d624f5f). This task did not modify the Runner worktree.
