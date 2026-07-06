# R2-FMM2A2 Next Solver Probe Plan

FMM2A found no importable FMM/RCWA package in the current server Python environment. Therefore FMM2B is not allowed yet.

Allowed next FMM path, after explicit user approval only:

1. Select an environment route: pure-Python RCWA/FMM package, MATLAB/Reticolo, S4, or fallback TMM + limited FDTD.
2. Install or expose exactly one solver environment outside this stage.
3. Run a tiny API smoke test in FMM2B, not a design sweep.
4. Bind the solver output to simple known stack behavior and then to H1H/H1L style metrics.

No heavy FMM sweep is allowed until a minimal solver probe succeeds and conventions are documented.
