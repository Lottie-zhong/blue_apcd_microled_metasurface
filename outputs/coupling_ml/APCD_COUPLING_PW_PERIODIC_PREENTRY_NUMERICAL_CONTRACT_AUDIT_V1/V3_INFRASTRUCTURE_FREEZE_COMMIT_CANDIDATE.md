# V3 infrastructure freeze commit candidate

Proposed allowlist for a future user-authorized provenance commit:

- `scripts/shared_fdtd/engine/persistence.py`
- `scripts/shared_fdtd/tools/v3_g2_host.py`
- `scripts/shared_fdtd/tests/run_persistence_zero_solver_tests.py`
- the zero-solver regression test evidence required by the project policy

Do not include FSP files, monitor dumps, credentials, runtime databases, or scientific PW output artifacts unless separately authorized. This task did not commit, push, reset, clean, merge, or alter the canonical branch.
