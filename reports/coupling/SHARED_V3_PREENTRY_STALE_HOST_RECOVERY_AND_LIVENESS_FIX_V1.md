# SHARED_V3_PREENTRY_STALE_HOST_RECOVERY_AND_LIVENESS_FIX_V1

## STATUS

`BLOCKED_AFTER_RETRY_PREENTRY_CONTRACT_CONFIG`

The Shared V3 liveness/telemetry repair and zero-solver gates passed. The two
authorized controlled pre-entry retries were launched exactly once each, but
both stopped before scientific entry because the frozen PW contract was passed
through an incompatible configuration shape. Per the task hard gate, no further
retry or attempt_002 was created.

## ORIGINAL S35/S39 STATE

- `K6V1_S35` and `K6V1_S39` originally had `HOST_STARTED` with dead host PIDs
  `29948` and `5252`.
- No attempt ledger, heartbeat, solver log, H5, native truth, or scientific
  entry event existed.
- The original root-cause classification was
  `ROOT_CAUSE_NOT_OBSERVABLE_DUE_TO_MISSING_HOST_EXIT_TELEMETRY`.

## SCIENTIFIC ENTRY ACCOUNTING

- S35 scientific solver entry: `0`.
- S39 scientific solver entry: `0`.
- GPU engine entry: `0`.
- Duplicate scientific entries: `0`.
- Scientific replay count: `0`.
- Attempt_002/003: not created.
- Reserve entry count: `0`.
- Foreign mutation count: `0`.

The retry launches consumed control-plane launch epochs only; neither crossed
the scientific-entry barrier.

## ROOT CAUSE

The initial host exit code was not recoverable because `pythonw.exe` was
launched with no durable stdout/stderr binding and no early host telemetry.

After the repair, both retries produced the exact failure evidence:

`ValueError: PW_CONTRACT_MISSING:monitors,samples_nm,references_nm,materials,stack_layers`

The retry `host_config.json` contains the frozen PW data under
`pw_contract.contract.{monitors,samples_nm,references_nm,materials,stack_layers}`.
`pw_scientific_launcher.validate_config()` expects those fields directly under
`pw_contract`. This is a pre-entry configuration-interface mismatch. No FDTD
run was invoked and no solver process was observed.

## CONTROL-PLANE FIX

Patched the existing Shared V3 backend only:

- launch with `python.exe -u` instead of `pythonw.exe`;
- bind durable per-host stdout/stderr files;
- emit `HOST_PROCESS_CREATED` and enriched `HOST_PROCESS_STARTED`;
- add strict dead-host reconciliation with owner/fence and entry checks;
- record `preentry_host_exit.json` and
  `PRE_ENTRY_HOST_LAUNCH_FAILURE` without fabricating an attempt ledger;
- release owner through the allocator and clear queue owner references;
- add explicit `mark_preentry_retry_eligible()` gated by a PASS zero-solver
  validation manifest;
- add controller tick reconciliation for stale `HOST_STARTED` rows.

## HOST TELEMETRY FIX

The repaired host writes, before any solver call:

- `HOST_RUNTIME_ENTERED`;
- `PREENTRY_VALIDATION_STARTED`;
- `host_uncaught_exception.json` on uncaught startup failure;
- `HOST_EXIT_PREENTRY` with exception and traceback;
- captured `host_stdout.log` and `host_stderr.log`.

The real retry evidence confirms all of these startup paths were reached and
the stderr artifact contains the exact PW contract error.

## STALE-HOST DETECTION

Dead-host reconciliation requires:

- queue state `HOST_STARTED`;
- no scientific or GPU entry event;
- no truth/persistence blocker;
- host process family absent and no PID-reuse ambiguity;
- intact queue owner/fence identity;
- active owner release through Shared V3 allocator.

The resulting canonical state is `FAILED_PREENTRY`, with explicit retry
eligibility evidence. It never silently resets to pending.

## ZERO-SOLVER VALIDATION

All required zero-solver checks passed:

- global regression: `20/20 PASS`;
- branch regression: `20/20 PASS`;
- chaos regression: `12/12 PASS`;
- pre-entry recovery: `16/16 PASS`;
- same-launcher pre-entry handshake: `PASS`;
- host liveness/dead-owner test: `PASS`;
- dispatcher detach: `PASS`;
- Medium PW pre-entry: `8/8 PASS`;
- resource-aware: `PASS`.

Validated solver runs and scientific entries: `0`.

## S35/S39 RECONCILIATION

The original stale records were reconciled through Shared V3. Original PIDs,
timestamps, and the `PRE_ENTRY_HOST_LAUNCH_FAILURE` classification were
preserved. Both owners were released with zero duplicate side effects and both
were made temporarily retry-eligible only after the PASS validation manifest.

## S35/S39 RETRY STATUS

Each case received exactly one authorized controlled pre-entry retry. Both
reached the repaired host telemetry path and failed before scientific entry on
the PW contract-shape error above. Both are now `FAILED_PREENTRY`, with slots
released and `new_entry_hold=TRUE`. No automatic retry is permitted.

## REMAINING 10G STATUS

All remaining approved cases remain `WAIT_RESOURCE_CAPACITY` and were not
started.

## SHARED V3 CAPACITY STATUS

- S35/S39 slots released.
- No capacity leak remains from the two retries.
- New scientific entry hold is `TRUE`.
- No unrelated Traditional or FDTD process was terminated or mutated.

## RESERVE STATUS

`S22`, `S40`, `S24`, `S43`, `S44`, and `S46` remain untouched with zero solver
entry.

## FILES CHANGED

Tracked-worktree changes are uncommitted and existing dirty/untracked content
was preserved:

- `scripts/shared_fdtd/tools/v3_dispatcher_service.py`
- `scripts/shared_fdtd/tools/v3_g2_host.py`
- `scripts/shared_fdtd/engine/dispatcher.py`
- `scripts/shared_fdtd/tests/run_preentry_host_liveness_zero_solver_tests.py`
- `scripts/shared_fdtd/tests/run_same_launcher_preentry_handshake_zero_solver_test.py`
- this report

The production controller copy was updated separately at:
`D:\apcd_runtime\global_fdtd_control_v3\PW_K6_FIXED_MDC_12G_STAGE1_HF_EXECUTION_V1_controller.py`.

## TESTS

No scientific solver was launched by the repair tests. The real retries also
recorded `scientific_solver_entry_count=0`.

## GIT

Branch: `work/mdc-np-coupling-ml-v1`
HEAD before/after: `789ceac980368cd90d7fb812e78347f2b0059407`
No commit. No push. Existing dirty/untracked state preserved.

## NEXT

`CHART_REVIEW_SHARED_V3_PREENTRY_FAILURE`

Chart review must decide how to reconcile the frozen PW contract interface
(`pw_contract.contract` versus the validator's expected shape). Do not alter
physics, geometry, mesh, monitors, wavelength, or retry S35/S39 until that
review authorizes the next action.
