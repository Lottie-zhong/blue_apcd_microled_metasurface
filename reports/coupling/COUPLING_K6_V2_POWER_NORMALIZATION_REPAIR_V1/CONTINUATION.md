# CONTINUATION - COUPLING_K6_V2_POWER_NORMALIZATION_REPAIR_V1

Read this file first after context loss. Then read REPORT_V1.md, PROTOCOL_V1.md, POWER_MAPPING_AUDIT_V1.json, POWER_MAPPING_SUPPLEMENT_V1.json, FIRST_CASE_INGEST_RESULT_V1.json, TEST_RESULTS_V1.json, and SHA256_INVENTORY_V1.json. Recheck current branch and latest main-controller/Runner gate status before further work.

## Remote workspace and connection

- Host: DESKTOP-NNE313K; user: dell.
- Coupling worktree: D:\project\worktreeslue_apcd_mdc_np_coupling_ml_v1.
- Branch: work/mdc-np-coupling-ml-v1; task commit before this status correction: fb773a3f91845ea227d47f05afc38f2b522a7782.
- LAN SSH first when reachable; NetBird SSH to 100.81.105.58 is the verified fallback. Reuse configured authentication; never print credentials.
- Use N:naconda_envs\RCP_LCP\python.exe for remote project Python.
- GPU Runner owner worktree: D:\project\worktreeslue_apcd_gpu_production_runner_v1; do not modify Runner source or authority from this Coupling task.

## Scientific scope and counts

Fixed MDC, fixed 237 nm spacer, ordered K6, 440-460 nm, Cartesian C_hat, independent positive P_scale, frozen H2 and original H1. Do not change truth, H1/H2, contract, production monitor, or point set.

This repair added solver entries=0; the first case already has one historical entry and must never be replayed. Replay=0, training fits=0, P_scale fits=0, confirmation access=0, confirmation entries=0. Do not start any of the remaining 127 cases until the specific modal-closure scientific gate is explicitly decided by the main controller.

## Completed first-case repair

- K6LDA1_DEV_D1_M05/attempt_001 is DONE with one historical solver entry. Original FSP, H5, truth, raw/state/orders files remain unchanged.
- Correct source-normalized order power is P_scale times the existing seven-order monitor eta. The archived orders JSON was not edited.
- The case-scoped, hash-bound supplement and unchanged default-fail-closed importer successfully ingested C_hat (21,7,2), P_scale (21), eta (21,7), and absolute_order (21,7).
- One-case truth-as-prediction H2/H1 consistency attained applicable numeric checks. It is not model performance or production admission.
- Remote RCP_LCP tests: 47 passed; git diff --check passed.

## Frozen measured evidence

- Independent Runner physical report: reports/gpu_runner_v1_power_fraction_normalization_v1/INDEPENDENT_PHYSICAL_POWER_AUDIT.json, SHA 8302638ec31cf34f5fce370d5d6d3da47a681092c1e5303c5e5079ce21b19a11, result MEASURED.
- Raw full-period E/H flux vs transmission times sourcepower max relative difference: 1.2892487612961532e-14; raw E/H P_scale matched Runner independent P_scale; eta sums passed.
- Surface flux vs frozen 9x9 H2 modal sum max relative residual: 2.8956697877272297e-4.
- Runner per-order source fraction vs independent modal source fraction max relative residual: 1.499059534294761e-3; max absolute residual 8.22043613859097e-5.
- No frozen direct modal-closure acceptance threshold has been found. Main controller has not issued a physical PASS. This is the active scientific hold.

## Runner budget interpretation

The GPU owner and main controller confirmed that the SHA-pinned development budget overlay is the operative Runner admission basis, not a conflict with zero-entry geometry setup authorities.
- Budget ID: APCD_GPU_RUNNER_K6_V2_128_DEVELOPMENT_CASES_MAX1_20261005_V1.
- Budget SHA: e1709cc70c28401e2dbedf4566d775609490e0f9c455830fdc7774cc32b24d7c.
- 128 unique frozen development identities; attempt_001; max 1 entry each; total 128; replay=0; one slot serial.
- First case consumed 1, so 127 are nominally remaining.
- The 32 confirmation cases remain at zero entries; confirmation responses, training, and P_scale fits remain unauthorized.
- The 160 zero-entry geometry authorities are setup-identity controls and must not be rewritten.

The controlled admission authority SHA remains a78274be660abf9d112f9c4a516cb647a00ebbb65069253abf38cca2e65efa35; its static zero-entry setup identity values are not to be interpreted as overriding the SHA-pinned budget overlay.

## Resume rule

Do not perform more solver or new live startup checks while the scientific gate is unresolved. Wait for an explicit main-controller conclusion about the modal residual evidence. After that conclusion, perform fresh live Runner owner/fence/budget/startup checks and formal preflight. If all pass, use Runner V1 for the 127 remaining development cases serially, at most one entry per case, replay=0. Preserve queue and existing ledger; never rerun the pilot. Stop at any failed check. No confirmation, training, P_scale fitting, reserve, or contract changes.
