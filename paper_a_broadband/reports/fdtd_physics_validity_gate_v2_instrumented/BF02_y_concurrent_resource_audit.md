# BF02_y concurrent resource audit

Classification: SAFE_CONCURRENT_ADMISSION

- Server logical processors: 104.
- Scheduler-observed Fluent MPI tree: -np 1; Fluent host tree: -t1, nprocs_string=1.
- Aggregate visible Fluent allocation: 2 configured rank-equivalents; conservative affinity-envelope headroom: 52 logical processors.
- Paper A requirement: 12 MPI ranks; safe headroom confirmed.
- ansysedt.exe was idle over the 3-second CPU check and was not treated as an active solver workload.
- Registered FDTD before admission: 0; registered RCWA before admission: 0; unresolved unknown solver jobs after positive Fluent classification: 0.
- BF02_y pre-entry authority: PASS.

Fluent was observed only. No process, priority, affinity, MPI configuration, or scheduler cap was modified.