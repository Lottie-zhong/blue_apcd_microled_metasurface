# NP K6 HF P0 closure diagnostic v1

Read-only evidence from completed RUN3C-p attempt_001; no run or save was called.

- Formal max |1-T-R|: `0.0812666246641951` at `448 nm`.
- FDTD simulation time: `1e-12 s`; auto-shutoff threshold: `1e-05`; final logged auto-shutoff: `0.000261435`.
- At 448 nm lower transition jump: `-7.358196152196239e-05`; upper transition jump: `-4.314730135068778e-06`; upper PML-front jump: `0.0001134256553443347`.
- Structure interval delta (upper-inside minus lower-inside): `-0.08020762156035277`.
- Raw-Pz integration has a consistent factor of two relative to the monitor T convention; it is not used to force closure.

Minimal single-variable proposal (not executed): extend `FDTD/simulation time` from 1 ps to 2 ps, leave auto-shutoff and all physics unchanged, and require a newly authorized control run before any labels are reconsidered.
