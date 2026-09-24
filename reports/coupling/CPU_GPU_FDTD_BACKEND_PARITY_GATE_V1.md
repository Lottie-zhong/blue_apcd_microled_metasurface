# CPU/GPU FDTD Backend Parity Gate V1

Status: **PASS** for backend reproducibility; this gate does not by itself admit a production truth bundle.

Case: `W2H_15294_5NM_GPU_HIGH_FIDELITY_CANARY_V1`, `attempt_001`
CPU reference: 5 nm CPU FDTD
GPU backend: RTX 3080, 5 nm FDTD, actual solver entries: 1

The tolerances below are **project-defined backend reproducibility tolerances**, not universal Ansys tolerances.

| Gate | Measured | Frozen limit | Result |
|---|---:|---:|---|
| R max absolute difference | 3.460739091604159e-05 @ 446 nm | 1e-3 | PASS |
| T max absolute difference | 1.9109459025418163e-05 @ 454 nm | 1e-3 | PASS |
| Populated POSTNP order-power max difference | 7.435804839254351e-06 @ 454 nm, (0,0) | 1e-3 | PASS |
| Canonical complex state max `C_PW E_C` | 7.159181479348523e-03 @ POSTNP, 443 nm, (+1,0), -z, TE | 1e-2 | PASS |
| Topology/order mask | exact equality | exact | PASS |
| Wavelength grid | exactly 440..460 nm, 21 points | exact | PASS |
| Monitor schema | compatible | compatible | PASS |
| Missing wavelengths | 0 | 0 | PASS |
| Energy/accounting closure | CPU/GPU max and mean 0 | project contract | PASS |

Supporting maxima by plane: IN `1.3720356359652775e-04`; PRENP `1.1230068357328705e-03`; POSTNP `7.159181479348523e-03`.

Conclusion: the measured GPU backend reproduces the CPU backend within the frozen project gate. This is a backend validation result, not a declaration that the native GPU truth bundle is complete.

Evidence:

- GPU FSP: `outputs/coupling_ml/W2H_15294_5NM_GPU_HIGH_FIDELITY_CANARY_V1/attempt_001/preentry_recovery2/runtime.fsp`
- GPU runtime H5: `outputs/coupling_ml/W2H_15294_5NM_GPU_HIGH_FIDELITY_CANARY_V1/attempt_001/preentry_recovery2/runtime/runtime_output.h5`
- GPU FSP SHA256: `025cf68135ff4c2341f611b385abf181f26e294265c9b1c9486f4d37c0b46afd`
- GPU H5 SHA256: `89327c22f398f5f24984007779cf12defaf764ae65e7f0ad44a5e0ac789049f9`
- Raw measured parity source: `outputs/coupling_ml/W2H_15294_5NM_GPU_HIGH_FIDELITY_CANARY_V1/attempt_001/RECOVERY_POSTPROCESS_RESULT.json`
