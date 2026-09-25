# PW_K6 MON_IN extraction failure forensic

- Status: `ZERO_SOLVER_FORENSIC_COMPLETE`
- Root cause: `E_FDTD_SAVE_LOAD_PERSISTENCE_TIMING_RACE` with C-level missing-data manifestation.
- MONITOR_CONTRACT_HASH: `6c0c434f680302664ff752b8dfa9d6ec7669909c42c8f66f1cab2b2c2bd86e28`; S16=EXT01=EXT02.
- Static audit: monitor objects, geometry-independent monitor contract, wavelength grid, and field schema are equal; current failed FSPs load MON_IN Ex/Ey/Ez/Hx/Hy/Hz successfully.
- Runtime evidence: the retained forensic observation recorded `h5_exists=false` at the child-return/persistence boundary, while current `events.jsonl` does not preserve that watcher row; current H5 mtime is not treated as creation time. The confirmed class is a sidecar readiness/path-observation race in persistence, explaining the transient `getdata("MON_IN","Ex")` failure.
- Fix: wait for H5/sibling sidecars to appear and remain size/mtime stable before native bundle persistence and fresh-load validation.
- Zero-solver: targeted bundle PASS; global 20/20, branch 20/20, chaos 12/12; monitor and EXT manifest tests PASS; no solver/replay/EXT03.
- EXT03-EXT14 remain `WAIT_RESOURCE_CAPACITY`, entry count 0.

Full evidence is in the adjacent JSON report.
