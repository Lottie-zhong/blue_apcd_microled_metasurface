# Scheduler authority

Current formal authority: `CURRENT_PRODUCTION_FDTD_SCHEDULING_CAP = 3`; `branch_local_cap = 3`.

`branch_new_slots = min(branch_local_cap, 3 - active_other_real_FDTD_jobs)`.

One real FDTD physics job is 4 MPI processes 脳 1 thread. RCWA does not consume an FDTD slot. Historical reports with global cap=2 or branch max=1 are retained as historical evidence and are superseded by the current cap=3 authority; they were not rewritten.

Closeout pre/post scheduler SHA256: `C69C3740BBC2F5E28F992CBF1CF01EBAD71C3BC64DCB947D32DA273B816D001F`.

