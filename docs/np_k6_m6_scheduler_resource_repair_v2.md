# NP K6 M6 Scheduler/LumAPI context repair v2

This evidence records a zero-solver infrastructure repair for `APCD_GLOBAL_FDTD_PARALLEL_POLICY_V1`.

- Per formal job contract: `processes=4`, `threads=1`.
- The M6 runner now sets and reads back both values after shared-slot acquisition and before the immutable `entered=true` transition.
- A mismatch such as the historical `52` engine launch is rejected before solver entry.
- One interactive resource API smoke and five Scheduler-path constructor-only smokes passed. They opened the frozen G01-S source pre-FSP, queried simulation time/mesh, and closed without `run()`, `runanalysis()`, `runjobs()`, or `save()`.
- The historical G01-P attempt remains immutable: entered/run/engine/post/controller = `1/1/1/1`, but observed `mpiexec -n 52` violates the global resource contract. Its numerical extraction is not a formal label (`quality_gate_pass=false`, `training_label=false`).
- LP evidence is separate: its command line used `mpiexec -n 4` and referenced the LP worktree. The 52 NP engines are not relabeled as LP.
- No later M6 case was entered, no formal Scheduler task was started, no process was terminated, and the shared licensing service was not modified.

This repair does not authorize a replay or replacement of G01-P. A user decision is required for the consumed, resource-invalid G01-P before formal M6 acquisition can resume.
