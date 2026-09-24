# 5NM GPU Production Schema V2 Failure Forensic V1

Status: **FAILED_AFTER_ENTRY / NO_REPLAY**

Forensic classification: `GPU_RESOURCE_NAME_RESOLUTION_FAILURE_BEFORE_ENGINE_ENTRY`

Separate evidence: `launcher_entry_recorded=YES`; `actual_fdtd_engine_entry=NO`; `maxwell_solver_iterations_started=NO`; `truth_generated=NO`. The historical ledger remains unchanged; this classification does not authorize replay.

Case: `W2H_15294_5NM_GPU_PRODUCTION_SCHEMA_V2`, `attempt_001`

Evidence:

- Entry ledger was written before launch with `solver_entered=true`, `actual_solver_entry_count=1`, `no_replay=true`, and `no_attempt_002=true`.
- Standalone launcher returned code `0` after `15.077999999979511 s`.
- `run_gpu.xml` reports: `in run: could not match resource name provided.` at LSF line 1.
- The LSF used `run("FDTD","GPU","GPU production schema V2")`; that third resource name is not installed on the host. The prior validated canary used the known resource name `GPU license audit`.
- No `fdtd-engine-msmpi.exe` or `mpiexec.exe` was observed after the launcher returned.
- Runtime FSP exists but its SHA256 is unchanged from setup: `36e5011b5e5c67a41e28dba296575356e6d7cefbbb1b4dd5e20ed0bfbffc08a5`.
- No sibling `runtime/runtime_output.h5` exists.
- stdout/stderr are empty; the XML error is the authoritative launcher evidence.

Interpretation: the new setup passed zero-solver structural validation, but the sole authorized GPU production-schema attempt did not reach an FDTD engine and did not produce native truth. Under the project entry ledger rule, the attempt is consumed conservatively. Do not replay, do not create `attempt_002`, and do not start `PW_K6_SEED_DB_V1`.
