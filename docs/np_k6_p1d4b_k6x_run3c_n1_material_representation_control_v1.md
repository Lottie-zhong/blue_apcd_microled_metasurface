# NP K6-x RUN3C N1 material representation control v1

## Status

`HARD_GATE_MATERIAL_CONTROL_NOT_SINGLE_VARIABLE`

The sole authorized attempt completed with entered/engine/controller/post-save = `1/1/1/1`. The setup SHA was read from the formal checksum JSON and matched in full:

- setup/run-copy SHA256: `7d8f887bcc6260381c7576562f2b99eded817022afa31bc4d0e9c0123007650a`
- post-FSP SHA256: `f04ee40a3ac1a486a6f20105491266a228e562cc2a3689998ef71837bbaa95f7`

The preflight confirms geometry, fixed mesh, source, PML, boundary, conformal setting, and monitors are unchanged. However, the control FSP uses `Sampled 3D data` clones containing 101 native spectral samples, not nondispersive constant-complex-epsilon materials at the canonical 449 nm values. Therefore the material representation is not a valid single-variable control, and no physical classification is permitted.

Canonical loader values at 449 nm are recorded in `material_control_loader_readback_449nm.json`; extraction is read-only and diagnostic-only. No rerun, N2 run, candidate, DOE, or training label is authorized.
