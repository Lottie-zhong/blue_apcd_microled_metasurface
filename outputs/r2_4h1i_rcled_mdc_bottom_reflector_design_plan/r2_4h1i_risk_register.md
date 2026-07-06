# R2-4H1I risk register

| risk | impact | mitigation |
|---|---|---|
| Bottom DBR overlaps source or existing GaN/source region | invalid RCLED geometry | H1J must do no-run geometry audit before any solve |
| Existing y-span too small for ~1233 nm bottom DBR plus PML margin | PML/structure overlap or bad boundary behavior | expand y-min downward in derived FSP construction |
| Cavity length not tuned | bottom DBR can worsen angular emission | keep cavity length as follow-up variable, not a H1I sweep |
| Source validation center-only temptation | false positive risk | enforce three-position x-axis incoherent average |
| y-polarization unknown | incomplete unpolarized source evidence | defer y-dipole until structure is frozen and user explicitly approves |
| Existing top MDC filtering may not combine constructively with bottom DBR | RCLED-MDC may not improve near-normal emission | require future three-position FDTD validation before physics claims |
