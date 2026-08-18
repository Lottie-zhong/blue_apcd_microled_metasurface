# Paper A exclusive-idle FDTD resource authority v1

Effective 2026-08-19 for the canonical Paper A LP+CP broadband worktree.

Paper A may enter a future FDTD case only when Chart has explicitly authorized a concrete solver budget, the benchmark gate has been released, and the shared scheduler verifies zero active FDTD in NP, NP-ML, MDC–NP Coupling, and every other independent branch. The cross-branch active FDTD count must be zero. A global capacity slot by itself is not sufficient.

The current anisotropy-expanded stage remains `PLANNING_AND_SETUP_ONLY_BEFORE_BENCHMARK` with NEW_FDTD_BUDGET=0, Paper A active FDTD allowed=0, solver_run_called=false, solver_entered=0, and no READY/WAITING/pending auto-admission. This artifact records the resource rule only; it does not authorize a solver.

Future entered cases retain case-boundary yielding, entered=true no auto-replay, and no kill/pause/restart/replay. The global scheduler registry remains the sole admission authority. Frozen LP, CP, and MDC source worktrees remain read-only provenance/provider sources.
