# PW_CONTRACT_CANONICAL_SCHEMA_ACCESSOR_FIX_V1

Date: 2026-09-29

## STATUS

PARTIAL / BLOCKED_BY_EXISTING_NEW_ENTRY_HOLD

The canonical-schema accessor fix, zero-solver regression, and real S35/S39
payload preflight all pass. The authorized control-plane retry did not launch a
solver because the existing Shared V3 admission state retains
`new_entry_hold=true`. No scientific entry was created.

## AUTHORITY

- Worktree: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1`
- Branch: `work/mdc-np-coupling-ml-v1`
- HEAD: `789ceac980368cd90d7fb812e78347f2b0059407`
- Runtime: `D:\apcd_runtime\global_fdtd_control_v3`
- Frozen physical contract hash:
  `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`

The task is zero-solver. No FDTD/GPU engine was launched by the final fix or
the final preflight.

## ROOT CAUSE

The production payload uses the canonical schema:

```text
cfg["pw_contract"]["contract"]
```

The consumer incorrectly searched for `monitors`, `samples_nm`,
`references_nm`, `materials`, `stack_layers`, and `wavelengths_nm` directly in
`cfg["pw_contract"]`. This produced the pre-entry error
`PW_CONTRACT_MISSING:monitors,samples_nm,references_nm,materials,stack_layers`
even though the frozen nested contract was present.

This is a consumer/accessor schema bug. It is not a monitor, geometry,
material, wavelength, solver, or scientific-contract change.

## FIX

Changed only:

- `scripts/shared_fdtd/tools/pw_scientific_launcher.py`
- `scripts/shared_fdtd/tests/run_pw_launcher_zero_solver_tests.py`
- `scripts/shared_fdtd/tests/run_pw_contract_schema_accessor_zero_solver_tests.py`

The accessor now:

1. Resolves the nested canonical contract first.
2. Allows a complete legacy top-level contract only when no nested contract is
   present.
3. Accepts the real production wrapper's identical overlapping metadata
   (`wavelengths_nm`) without merging schemas.
4. Raises `PW_CONTRACT_SCHEMA_CONFLICT` for conflicting overlap.
5. Distinguishes schema-path errors from missing scientific fields.
6. Supplies no scientific defaults.

Postprocessing now passes the resolved canonical contract to the state
extractor. The frozen contract object and its hash are not rewritten.

## REAL S35/S39 ZERO-SOLVER PREFLIGHT

Actual production payloads were read from:

```text
D:\apcd_runtime\global_fdtd_control_v3\cases\PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1\K6V1_S35\attempt_001\host_config.json
D:\apcd_runtime\global_fdtd_control_v3\cases\PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1\K6V1_S39\attempt_001\host_config.json
```

Results for both cases:

- validator: PASS
- resolved schema path: `pw_contract.contract`
- legacy overlap: `wavelengths_nm`, semantically identical
- resolved contract SHA256: `32e60a7830a449f2268356db5ffd41f4f22b297be9a1d82ebe97f97be995dea5`
- declared/physical hash equality: PASS
- previous missing-field error absent: PASS
- solver invocations: 0
- scientific entries: 0

## ZERO-SOLVER REGRESSION

All required zero-solver checks passed:

- `run_pw_contract_schema_accessor_zero_solver_tests.py`: 6/6 PASS,
  solver invocations 0.
- `run_pw_launcher_zero_solver_tests.py`: PASS, solver invocations 0.
- `run_medium_pw_preentry_zero_solver_tests.py`: 8/8 PASS,
  solver runs 0, scientific entries 0.
- `run_pw_k6_seed_manifest_zero_solver_tests.py`: PASS,
  solver invocations 0.
- `run_monitor_sample_reference_role_zero_solver_tests.py`: PASS,
  solver invocations 0, scientific entries 0.
- `run_medium_pw_mon_in_zero_solver_tests.py`: all A-L PASS,
  solver invocations 0, scientific entries 0.
- global regression: 20/20 PASS.
- branch regression: 20/20 PASS.
- chaos regression: 12/12 PASS.

## S35/S39 RETRY STATUS

The earlier preserved retry history used the old accessor and ended in
`PRE_ENTRY_HOST_LAUNCH_FAILURE` with the old `PW_CONTRACT_MISSING` error. It
remains preserved and is not a scientific entry.

After the final accessor fix and real preflight, the official control-plane
API marked S35 and S39 retry-eligible. The subsequent official dispatch
returned no launches for either case. The current admission evidence for both
cases is:

- queue state: `WAIT_RESOURCE_CAPACITY`
- slot: none
- lease: none
- active GPU owners: 0
- resource preflight: PASS
- health: PASS
- blocker: `NEW_ENTRY_HOLD`
- `new_entry_hold`: `true`
- exact launch permit: not requested/invalid

No bypass, direct SQLite edit, forced slot allocation, or solver launch was
performed.

## ENTRY ACCOUNTING

- S35 scientific entry count: 0
- S39 scientific entry count: 0
- new GPU entry count: 0
- replay count: 0
- duplicate scientific entry count: 0
- active solver/controller/engine processes: none observed

Remaining approved cases S21, S42, S36, S31, S45, S32, S47, S33, S37, and
S48 remain `WAIT_RESOURCE_CAPACITY`. Reserve IDs S22, S40, S24, S43, S44, and
S46 were not present in the coupling queue query and were not touched.

## GIT

No commit and no push were performed. The worktree contains pre-existing dirty
and untracked files from the broader project. The task-specific accessor and
test files remain uncommitted; no unrelated files were staged.

## NEXT

Chart/control-plane review must explicitly decide whether to release the
existing `NEW_ENTRY_HOLD`. Only after that release, and using the official
Shared V3 path, may S35 and S39 be retried as their existing `attempt_001`
control-plane retry. Do not create `attempt_002`, replay a scientific entry, or
start any other case.
