# R2-FMM2A summary

Decision: `no_available_fmm_solver_protocol_only`.

Current worktree sanity:

- cwd ok: `True`
- branch: `work/rcled-mdc-source-module`
- git status short: `?? scripts/stage_r2_fmm2a_solver_inventory_and_validation_protocol.py`

Importable FMM/RCWA-like packages: none.

Recommended solver candidate for a later minimal API probe: `none`.

FMM is only a calibrated mid-fidelity screening layer between TMM and FDTD. It is not accepted as a full FDTD replacement. Candidate freeze requires TMM good + FMM good + FDTD top validation not failed.
