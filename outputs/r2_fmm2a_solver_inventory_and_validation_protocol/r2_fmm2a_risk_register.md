# R2-FMM2A risk register

| risk | impact | mitigation |
|---|---|---|
| No FMM/RCWA package importable | Cannot run FMM2B probe | Discuss environment/install options; do not simulate in FMM2A |
| Import works but API unsuitable | False confidence from package availability | FMM2B must be a tiny API probe before ranking |
| FMM fails to reproduce H1H qualitative trend | Ranking layer invalid | Stop FMM route or recalibrate before candidate ranking |
| Periodic FMM misses finite-mesa leakage | False positives | Keep FDTD finite-mesa validation mandatory |
| Source averaging proxy too crude | Bad source-position stability prediction | Keep x-axis three-position FDTD for top candidates |
