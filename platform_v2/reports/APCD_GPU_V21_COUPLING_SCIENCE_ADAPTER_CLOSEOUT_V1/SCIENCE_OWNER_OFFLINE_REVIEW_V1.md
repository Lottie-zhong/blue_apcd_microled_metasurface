# APCD GPU V2.1 Coupling Science Adapter: offline review

Review status: SCIENCE_INTERFACE_PARTIAL. This is not a science-owner PASS, not an offline-ready decision, and not deployment approval.

## Scope and outcome

The Coupling worktree contains a generic-profile candidate at scripts/coupling_ml/k6_v2_pipeline/generic_profile.py with five focused offline tests. It introduces the coupling_609d_v1 role/profile adapter and reuses a source-equivalent copy of the frozen 609D truth extractor with the contract-pin check parameterized. The native GPU worktree was not changed by this review.

The targeted Coupling test command completed 5 passed. A GPU pre-entry hold fixture completed 1 passed. The latest GPU Owner update reports 231 full-suite tests passed, installed source SHA matching 134/134 files, an empty GPU slot, and no controller or solver process. Those platform results do not constitute Coupling Science Owner acceptance of the adapter.

The static DIAG2 evidence is limited to reused native LOAD/setup proofs: solver_entry_count=0, new_solver_runs=0. It contains no 3 ps versus 6 ps scientific output comparison and no 6 ps solver truth. No FDTD, RCWA, Lumerical solver, training, or production entry was run here.

## Blocking evidence

1. The 6 ps contract identity is unresolved. The candidate contract file has raw SHA-256 6d15721bb3d69342c1b24f4fae687efb10bc55c375b44624aec717c7b351524b; it declares semantic/canonical SHA-256 afc06d29802ddae02017f967a6e4e30088fc56281e9cc4dfc20e7f519a43546f. Recomputing its stated canonicalization (exclude the declared hash, sort keys, compact JSON) yields 5220e0f869bcd718e0e1caf807c7d75519ef424c3a600d3ad2f28d454018928d, which matches neither. No verified resolved-flat 6 ps contract is available. The candidate still assumes the contract-file pin equals the semantic contract SHA, so it cannot safely consume this unresolved identity.
2. Positive end-to-end synthetic acceptance is incomplete. Negative/no-authority checks and frozen numeric compatibility are covered, but a complete legal B (DIAG2) and C (previously unknown batch) path through manifest, admission, certification, FSP/H5 truth validation, labeling, and ledger reconciliation has not passed. Do not claim B/C generality or OFFLINE_READY.
3. Owner authority bindings are incomplete. Before independent acceptance, authorization and source checks must bind batch/case/attempt, role, ordered geometry, semantic physics SHA, profile ID, manifest/admission/certification file SHAs, plus source role, source-manifest SHA, and raw contract-file SHA. Consumer-supplied metadata cannot create science authority.

The latest task update reports the two separate budget-ledger SHA prefixes as 9e277f... and a25cb5...; this review does not alter either ledger.

## Evidence references

- Coupling candidate and tests are listed with SHA-256 in SHA256_INVENTORY.json.
- GPU static evidence: D:\project\worktrees\blue_apcd_gpu_v2_serial_production_v1\platform_v2\reports\APCD_GPU_V21_COUPLING_SCIENCE_ADAPTER_CLOSEOUT_V1\DIAG2_REUSED_SETUP_EVIDENCE.json.
- Candidate contract: D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\reports\coupling\APCD_GPU_V2_COUPLING_TIME_DIAG2_ADMISSION_RECOVERY_V1\TIME_DIAG2_PHYSICAL_CONTRACT_CANDIDATE.json.
- Frozen 3 ps parent contract: D:\apcd_runtime\gpu_v3_interface_audit_20261011_v1\source_setup\K6V3_NUM_REPEAT_A1\attempt_001\physical_contract.json.

## Git context

Review source branch: work/mdc-np-coupling-ml-v1; pre-review HEAD 09c4e97fe7dcf4fcf77b743a4c709173ae385dbe; upstream divergence before this review commit was 0/0. The other pre-existing worktree status records are preserved. The final review commit is reported separately in the task result.
