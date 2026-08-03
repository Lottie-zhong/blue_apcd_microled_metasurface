# NP K6 P0 simulation-time extension control v1

- case: RUN3C_P_PILOT_HF_SIMTIME_2PS_CONTROL_V1
- attempt: attempt_001
- setup-only preflight passed before the sole authorized run.
- only changed property: `FDTD.simulation time`, 1e-12 s to 2e-12 s.
- auto shutoff minimum remains 1e-5.
- Native-M1 sampled materials, geometry, mesh, source, PML, monitors, wavelength grid and normalization contracts are unchanged.
- old 1 ps case remains immutable and training_label=false.
- new case remains provisional_hf_label=true, training_label=false, candidate_performance_label=false.
- no formal dataset or partial promotion is allowed.

Runtime and quality classification are written only after the independent post-FSP reload and 11-point extraction complete.
