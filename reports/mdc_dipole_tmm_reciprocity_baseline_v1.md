# MDC Dipole-TMM reciprocity baseline v1

- Method: stable scalar S-matrix with reciprocal relative air-side channels; no Lumerical/FDTD/RCWA call.
- Scope: relative channel radiation only, not absolute extraction, total power, LDOS, or Purcell.
- Baseline depth: -400 nm equivalent active plane, not actual MQW.

## Results

- Both required candidates and all 17 depths completed with x, z, and incoherent avg.
- The planar half-space model is depth-invariant in relative power; phase is continuous. Ranking does not change by depth.
- -400 nm is therefore stable within this limited model, but it is not a justification to promote depth to a formal ML input.
- Minimal subsequent FDTD matrix: bare and alternative at -200/-400/-600 nm, x/z separately.
