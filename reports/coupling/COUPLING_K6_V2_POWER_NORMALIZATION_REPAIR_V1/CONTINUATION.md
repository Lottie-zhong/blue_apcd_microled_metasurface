# CONTINUATION - COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1

Read this file first after context loss. Then read PROTOCOL_V1.md, REPORT_V1.md, POWER_MAPPING_AUDIT_V1.json, POWER_MAPPING_SUPPLEMENT_V1.json, FIRST_CASE_INGEST_RESULT_V1.json, TEST_RESULTS_V1.json, and SHA256_INVENTORY_V1.json. Recheck the current Coupling branch and the GPU Runner authority before any further work.

## Remote workspace and connection

- Host: DESKTOP-NNE313K; user: dell.
- Coupling worktree: D:\project\worktreeslue_apcd_mdc_np_coupling_ml_v1.
- Branch: work/mdc-np-coupling-ml-v1.
- Task-start HEAD: a50854f8425718d5d109b341a12b75dcbc328b43; upstream was 0/0.
- LAN SSH is preferred when reachable; NetBird SSH to 100.81.105.58 is the verified current fallback. Reuse the configured key without printing credentials.
- Use remote RCP_LCP Python at N:naconda_envs\RCP_LCP\python.exe for project Python. Do not run Git or edit the unrelated local working directory D:\projectlue plane wave meta-surface.
- GPU Runner owner worktree: D:\project\worktreeslue_apcd_gpu_production_runner_v1; read-only for this task.

## Scientific scope

Fixed MDC, fixed 237 nm spacer, ordered K6, 440-460 nm, Cartesian C_hat, independently predicted positive P_scale, frozen H2 and original H1. No truth, H1/H2, contract, Runner source, or production monitor change. No training, P_scale fit, confirmation response access, reserve, inverse search, or solver entry beyond the single historical first-case entry. Post-entry replay remains zero.

## Completed

- Verified the immutable first case K6LDA1_DEV_D1_M05/attempt_001: DONE, one historical solver invocation; no replay. Original FSP/H5/truth/raw/state/orders/provenance hashes are preserved.
- Recomputed POSTNP full-period E/H flux from actual coordinates with trapezoidal half endpoint weights and the frozen IN_REF normalization. Correct source-normalized order power is P_scale times the same seven-order monitor eta. The old orders JSON was not edited.
- Added an explicit case-scoped, hash-bound power supplement. The unchanged importer default still rejects the legacy incorrect source_fraction; only the exact first development-local case can opt in.
- Imported and persisted one derived development truth artifact with C_hat (21,7,2), P_scale (21), eta (21,7), and absolute_order (21,7).
- One-case truth-as-prediction H2/H1 consistency checks attained applicable numeric gates. These values are not model performance, dataset H1, or production admission.
- RCP_LCP pipeline tests: 47 passed; git diff --check passed with only LF/CRLF warnings.
- This task added solver entries=0, post-entry replay=0, training fits=0, P_scale fits=0, confirmation accesses=0.

## Frozen evidence

- Independent Runner physical report: reports/gpu_runner_v1_power_fraction_normalization_v1/INDEPENDENT_PHYSICAL_POWER_AUDIT.json, SHA 8302638ec31cf34f5fce370d5d6d3da47a681092c1e5303c5e5079ce21b19a11, result MEASURED. It has no frozen direct surface-vs-modal closure threshold; keep that residual unclassified.
- H1 authority SHA: 8cf71239757e70eb75fbbf858a82c12f8af8d03c0892b99ff4ffce6a959fcdbd.
- H2 decoder SHA: b6873c1fc9df447de16b62e60da9d0b4c978934d7d02db283ddb5713f2024d15.
- Runner code patch commit: 02ad6b4b5f47b247f384fc132af329cc05612327.
- Current Runner handoff SHA: 43b45008ce010fef62f9024d1be6cddb913fa147a806182fcf9209c6dd9f84e5.
- Current controlled_admission_authority SHA: a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35.
- Current linked development budget SHA: e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c.

## Current stop state and recovery

The first-case repair and ingestion are complete. Do not start the remaining 127 cases yet. The controlled admission authority currently says OWNER_ENROLLED_SETUP_ONLY_SOLVER_DENIED, solver_entry_authorized=false, max_solver_entries_per_case=0, and denies solver entry for all 160 K6 geometry authorities. The separate user-authorized budget lists 128 development cases with one entry each and says the remaining entries wait for Coupling ingestion PASS. These formal artifacts conflict. No fresh live owner/fence/startup check was run. Wait for the GPU authority owner to reconcile the official authority and return a fresh live Runner check. Then re-read this continuation and all changed authority hashes; proceed serially through Runner V1 only if the per-case authority, total budget, owner/fence, startup, and preflight all pass. Keep one slot, one entry per case, replay=0; stop immediately on any gate failure. Never rerun the pilot.
