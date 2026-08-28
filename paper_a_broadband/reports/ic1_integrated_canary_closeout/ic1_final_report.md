# IC1 integrated canary closeout

## Status

PASS — `IC1_MDC_I03_TOPWELL_X` completed one authorized FDTD entry and passed the completed-output Integrated V2 validity gate. This is a finite integrated canary truth result, not a production `W_emit` closure.

## Contract and provenance

- Canonical branch: `work/paper-a-lp-cp-broadband-v1`
- Pre-entry authority HEAD: `c41a7884d650f17defaa8b274536d104f638d8a3`
- Case: `IC1_MDC_I03_TOPWELL_X`, attempt `attempt_001`
- Native-M1 physics; source/monitor grid 400–500 nm, 101 points; 12 MPI × 1 thread
- Pre-FSP SHA-256: `72439a053e8d2c2d8f09df544096ff31922e10bc99c6bc7baa439762a64536a0`
- Post-FSP SHA-256: `1efec8ca55370270bb6faabca2dc156c352be2b1b0da69f19fd177c9ce2fe0b5`
- Physics fingerprint: `5f3a5cf319a270572d9acf33b7c1cba6495728bcb55caf350efe1d4aee12eb6b`
- Integrated instrumentation fingerprint: `ff0f40c8595b71d7bd1d5d16db898338b9dbfbb1f92fbe5978f6ab1beb163b86`

## V2 validity evidence

- Independent time probe: 10,267 finite, strictly increasing samples; late-window count 3,423; late proxy slope `-1485.193677131005 s^-1`; no positive late-window growth.
- Native Auto Shutoff trajectory was not persisted by the runner. Per the IC1 authority, it was not required when the independent V2 probe was retained; no missing native trajectory was fabricated.
- Sourcepower: finite and strictly positive at all 101 wavelengths; range `1.5122214660608366e-15` to `3.691946938625089e-15 W`.
- Six-face flux: finite at all 101 wavelengths; net outward range `-3.717817568511818e-16` to `-2.7237752054617993e-16 W`; signed powers were not transformed.
- Near-to-far Ex/Ey: finite complex data at all 101 wavelengths; 150 × 150 angular grid available. The 450 nm representative map is finite.
- Stokes: 101 finite samples using the project convention `S0=tr(C)`, `S1=Cxx-Cyy`, `S2=2 Re(Cxy)`, `S3=-2 Im(Cxy)`; DoLP range `0.17122021472628168` to `0.5867104293925933`.
- 450 nm near-to-far representative Stokes: `S0=1.1466459659250564e-14`, `DoLP=0.9943597511653182`, `DoCP=0.10605981926463316`, `psi=177.64289440598827 deg`.

## Classification

`VALID_FOR_IC1_INTEGRATED_CANARY_TRUTH`

Architecture verdict: `PAPER_A_IC1_FINITE_INTEGRATED_CANARY_PASS`
`W_emit`: `UNRESOLVED_FOR_PRODUCTION_CLOSURE`.

The result uses the completed post-FSP only. Raw solver data were not modified. No IC1-Y, IC2, IC3, IC4, other-well, CP, RCWA, or replay case was started.

## Solver accounting

`authorized=1`, `entered=1`, `returned=1`, `accepted=1`, `additional_replay=0`; postprocess `solver_run_called=false`, `solver_entered=0`. Peak observed global FDTD occupancy was 1 under capacity 3. The external Fluent process visible during admission was not modified.

## Artifacts

Machine-readable validity and postprocess outputs are in `paper_a_broadband/reports/ic1_integrated_canary_closeout/`. Runtime FSP, monitor, convergence evidence, and the 450 nm raw far-field probe remain runtime-only and are not staged.

No subsequent Paper A physics stage is started automatically.
