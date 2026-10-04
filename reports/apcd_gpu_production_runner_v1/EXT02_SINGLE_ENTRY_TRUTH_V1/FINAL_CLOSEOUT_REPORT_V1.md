# APCD_GPU_RUNNER_EXT02_SINGLE_ENTRY_TRUTH_V1 — Final Closeout

**Status: BLOCKED — historical entry already consumed; current official hold is active.**

Scope was limited to `K6V1_EXT02 / attempt_001`, at most one solver entry and zero automatic replays. This turn did not start a solver and did not create another attempt.

## Entry and control evidence

- The Shared V3 control database is `D:\apcd_runtime\global_fdtd_control_v3\control.sqlite3`, SHA256 `20c17bf1dd058db9117932465d7fa5bba8f888fd1c3453fa3fe70ccc9ee1c202`. Its live `admission_control` row is `new_entry_hold=1`, `control_generation=26`, `health_status=PASS`. All three slots read `FREE`. No hold-release API was called.
- Read-only `lease_events` history for this case and attempt contains exactly one `SCIENTIFIC_SOLVER_ENTERED` event: event 1680 at `2026-09-25T07:08:37.882954+00:00`, `GLOBAL_SLOT_3`, fencing generation 7. It is followed by owner quarantine, release pending, and lease released. The history also contains two child-process-start events; this report does not reinterpret those as two solver entries.
- The historical Coupling attempt ledger SHA256 is `691d5ae872d808a11776ac6fe2dd229e1a4eca04729feb419776edc38843ebeb`. It records `solver_entered=true`, `physical_solver_entry=true`, entry timestamp `2026-09-25T07:08:37.679019+00:00`, and a GPU `fdtd-engine-msmpi.exe -gpu -t 1` lineage (engine PID 34064; MPI PID 38548).
- Historical `terminal.json` SHA256 is `a75a081c75d1fa3ed5e483fe8dccfd5906fb1e7b2e065fc6810aea1580a87ded`. It records one solver entry/run, solver returned, `SCIENTIFIC_VALID`, durable archive, release `RELEASED`, recovery `RECOVERED_VALID_HF_TRUTH`, and replay 0. This is the pre-existing legacy run, not execution under the current monitor-overlay setup.
- The current GPU Runner repository was clean at HEAD `dc71f90d5836b6fab608ee322ff4889ea064b646` on `codex/apcd-gpu-production-runner-v1` (`0/0` upstream). Its registry SHA256 is `43784e6f5d97761daae6dfa088482c8f65f589aa29577e2ccd72dff10b62d36b`; it has no EXT02 record and no Runner attempt directory. The V3 lease history and Coupling ledger establish why absence from this newer registry is not evidence of zero historical entries.

## Setup and archived truth

- The current controlled setup remains at `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\APCD_GPU_RUNNER_CONTROLLED_ADMISSION_V1\K6V1_EXT02\attempt_001`. `setup/runtime.fsp` and `setup/source.fsp` are both SHA256 `5d76cb420cea8bd17ada3aac262886beccc9bd0e177d72aa8d70d8e10df1ae30`; the setup LOAD-only proof is `2e97596b983df1b11d3d0a06309df41cabff6c7076917a30ebf446459f3ce386`; source manifest is `77107310820f44f19aff32baa8bc2db5170775187025fa95cee76ef2ba6d7ffb`. These match the prior setup-preflight artifacts. A new final launch revalidation was not run because the historical attempt is already entered and the live hold is active.
- The old ledger's pre-FSP hash is `99248d02495d8a3124f712bdaf2291c5a058cfd4a6a85ace129b096381b98143`, different from the current controlled-overlay setup hash above. Its archive therefore cannot stand in for results from the controlled overlay.
- Existing archive restore FSP: `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_EXT02\attempt_001\archive_restore\K6V1_EXT02__attempt_001_runtime.fsp`, 170,552,876 bytes, SHA256 `65739584081c3ef0ba946d0be506c7847507dcabe6f3424c8d4dff4b9cb7d0d1`.
- Its sibling H5 is `D:\project\worktrees\blue_apcd_mdc_np_coupling_ml_v1\outputs\coupling_ml\PW_K6_SEED_DB_V1_PRODUCTION_V1\K6V1_EXT02\attempt_001\archive_restore\K6V1_EXT02__attempt_001_runtime\K6V1_EXT02__attempt_001_runtime_output.h5`, 76,596,458 bytes, SHA256 `838a9809a22c206df1f7f40f5d70ff3a404a07da4a329178ea9bf41c195017b8`.
- Historical `archive_restore_validation.json` SHA256 `23192c74d3a18d9c22dd1ca5f1b55d9e212eae39d504824cae3de03a507ac342` reports a passing FDTD LOAD-only check for `MON_IN`, `MON_PRENP`, `MON_POSTNP`, and `MON_REFLECTION`, with Ex/Ey/Ez/Hx/Hy/Hz. Read-only H5 inspection found four groups (`Monitor0`–`Monitor3`), each with those six field datasets plus x/y/z coordinate datasets. No evidence identifies `EXT02_POSTNP_DIAG_Z2000` in that archive. The second-plane extraction and its actual coordinates are therefore unavailable; no dual-plane extraction was claimed or run.

## Hidden-process and execution audit

- The eight previously noted `fdtd-solutions.exe -server -hide` processes were inspected read-only. Their owners were `DESKTOP-NNE313K\DELL`, parents were Python processes, and their two-second CPU samples did not increase; each had approximately 15–17 MB working set. No Lumerical `fdtd-engine-msmpi.exe` was present. The RTX 3080 reported 0% utilization; its compute-process list did not include those eight API processes. Visible `mpiexec.exe`/`smpd.exe` processes belonged to Fluent. No process was terminated or adopted.
- Counts for this turn: solver entry 0; FDTD run 0; replay 0; dual-plane extraction 0. The old attempt's historical entry count remains 1.

## Current code identity

- Runner HEAD: `dc71f90d5836b6fab608ee322ff4889ea064b646`; branch `codex/apcd-gpu-production-runner-v1`; clean, upstream `0/0` before this report.
- Controlled policy SHA256 `e26c2f1e5b13743da455277f4562ccf2a6262567e4dabf1a2fae06735d624f5f`; authority SHA256 `e6043ff7bec4711d16d326ca3d8305b9693647250349dea11b59b57e0cd2d1ec`; controlled admission module SHA256 `56dc7913f450ee76b50a5b6f474e53c3061cf6335dfd1215c1df386b0cdf6c03`.
- Coupling HEAD at audit: `f6ee5311a7aa10b5ad0d0787546ff638f5bd5bce`, one commit ahead of upstream and 332 untracked files. This task did not modify or clean that worktree.

## Decision

Do not invoke `run-one`, replay, or create `attempt_002`. The single-entry authorization for this case/attempt has already been consumed, the existing archived H5 lacks the newly authorized diagnostic plane, and the formal global hold is active. The setup-preparation proof is not a solver-result proof. No dual-plane scientific validation is claimed.
