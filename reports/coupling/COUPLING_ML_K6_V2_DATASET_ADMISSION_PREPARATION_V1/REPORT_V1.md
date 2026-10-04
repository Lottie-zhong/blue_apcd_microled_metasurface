# COUPLING_ML_K6_V2_DATASET_ADMISSION_PREPARATION_V1

## Status
READY_FOR_GPU_AUTHORITY_OWNER_REVIEW. No new case is enrolled and this task authorizes no solver or training.

## Frozen V2 / protocol check
The active candidate table remains unchanged at full SHA256 596bcc8fd7011cb5ec0c2fc93b9dfe26653ef74720d1bcd4872d3b22e18727c4; Amendment 01 is 124f6a0ddd65a65b0b4499a6dbfd98f2105d40ee273bfaeba04b28a6591f8f8a; base protocol is 4a041dfc9b9fd8bbc79edfd792d698d0240163de157144029ad51a41c104f44a. New data are 12 local-axis plus 116 global development = 128, and 4 local combinations plus 28 global confirmation = 32. Existing32 remains development-only and outside the new budget. Candidate IDs/geometries are unique and disjoint from old32 by ID and geometry hash.

Four geometry-grouped outer folds and nested actual training sizes 32/64/128 remain frozen. Every wavelength stays grouped by geometry; final fits use all160 development geometries. Only RBF KRR and 6-32-32 Cartesian MLP (21,377 parameters including C_hat and independent positive P_scale) remain proposed. Frozen H2 and every original conjunctive H1 gate remain unchanged.

Report confirmation separately as local4, global core27, global stress1, and all global28. Stress remains in original all-confirmation gate accounting.

## Case registration package
CASE_REGISTRATION_PACKAGE_V1.json has 160 proposed attempt_001 records, ordered D1..D6, purpose, frozen point/protocol hashes, contract references, setup CLI/path templates, and source/Runner manifest requirements. CASE_SETUP_STATUS_V1.csv is the per-case ledger.

Current official Runner is codex/apcd-gpu-production-runner-v1 at 6d472a967815915f8e2a37b275af054b20f1354c; controlled authority contains zero K6 geometry authorities. Owner enrollment is required, and this task does not write that authority. Only ordered_D_nm is the permitted variant. Fresh official build/preflight must verify the remaining fixed contract for each case after enrollment.

Reproducible setup entrypoint, not invoked: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\build_pw_k6_5nm_full_period_prefsp_v1.py (SHA256 fbd3a3e73212568023c47d84223a41b32d5cb3cf8fd48a04d09bef7bb94eded1), options --spec-json <owner-approved case spec> --output-fsp <canonical source FSP>. Official validator: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\scripts\coupling_ml\validate_pw_k6_5nm_full_period_prefsp_v1.py (SHA256 b694ecf692376a33673b785774a8ea734c452f11009aad1cfe553f444817e2a8). Canonical templates are under D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\<case_id>\attempt_001\setup; staged path comes from the immutable Runner manifest. No case specs or FSPs were produced without owner enrollment.

## Setup / LOAD proof status
For new160: owner enrollment 0; Runner approval 0; canonical FSP 0; staged FSP 0; source manifest 0; fresh official LOAD proof 0; formal preflight 0. All 16 old local DOE task-private FSP/spec/proofs match their hashes and ordered geometries; task-private LOAD-only PASS 16/16. Their canonical and Runner enrollment counts are zero; old proofs are not promoted.

## Confirmation isolation
DEVELOPMENT_CASE_ALLOWLIST_V1.json is exactly old32 plus new development128. Training/model selection denies confirmation and unknown IDs. Separate development and sealed-confirmation access manifests were saved; distinct empty response roots D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\COUPLING_ML_K6_V2_DATASET_ADMISSION_PREPARATION_V1_TRUTH\development and D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\COUPLING_ML_K6_V2_DATASET_ADMISSION_PREPARATION_V1_TRUTH\sealed_confirmation currently hold zero responses. Confirmation reveal is not authorized. Before one preregistered reveal, both models, preprocessing/configs/seeds, evaluators, frozen-H2 outputs, and predictions must be frozen and hashed. Report core27, stress1, all28; no post-reveal changes.

## EXT02 / manufacturing dependencies
Latest Runner EXT02 closeout SHA256 c17d67d3110ac7f64797de9c3ab3c8c50b33ff5c13f5e152337c3192ba1bd1e1 reports BLOCKED: historical K6V1_EXT02/attempt_001 entry was consumed; current global hold is active. Archived H5 has four existing monitor groups and no second diagnostic plane. Coupling two-plane report SHA256 f7e77c323fac9798236a4e32c727b7b673b9e2417ec42095cb55ff5cd35951b5 has no numerical cross-height comparison. Launch dependency remains open; setup preflight does not close it. No EXT02 change or replay occurred here.

Manufacturing constraint authority remains unresolved. Numeric geometry feasibility is not manufacturing approval.

## Execution counts
Solver 0; training 0; P_scale fit 0; Runner invocation 0; new FSP 0; reserve launch 0. No truth responses were read or produced.

## Commit allowlist
Only this task directory's inventoried files are intended for commit. Existing unrelated worktree state remains untouched.
Runner worktree authority boundary: read-only status showed five tracked modifications, including the uncommitted controlled-admission authority and policy drafts. They are not formal authority. This package uses only committed Runner HEAD 6d472a967815915f8e2a37b275af054b20f1354c (route SHA256 e6043ff7bec4711d16d326ca3d8305b9693647250349dea11b59b57e0cd2d1ec; policy SHA256 e26c2f1e5b13743da455277f4562ccf2a6262567e4dabf1a2fae06735d624f5f). This task did not modify the Runner worktree.
Frozen H2 decoder authority SHA256: b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15. State schema: PW_COMPLEX_FLOQUET_STATE_V1 POSTNP +z, seven y=0 orders, TE/TM.
